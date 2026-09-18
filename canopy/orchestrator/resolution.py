"""
canopy/orchestrator/resolution.py

The Resolution Engine — thin coordinator that composes answers
from systems that each own one domain of knowledge.

- The Manifest checks its own consistency
- The DependencyResolver traces DAG impact
- The Method declares uncertainty for missing data
- The ProviderRegistry handles acquisition
- This engine asks the right questions in the right order
"""

from __future__ import annotations

import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from canopy.introspect import (
    disk_headroom,
    has_credentials,
    is_online,
    provider_reachable,
)

logger = logging.getLogger("resolution")


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DatasetResolution:
    """Resolution status for a single dataset."""
    dataset_name: str
    semantic_type: str
    status: str  # available, acquired, failed, manual_required, auth_required
    message: str
    path: str | None = None
    dependent_steps: list[str] = field(default_factory=list)
    orphaned_steps: list[str] = field(default_factory=list)
    analytical_role: str | None = None
    uncertainty_without: str | None = None
    critical: bool = True
    instructions: str | None = None


@dataclass
class ResolutionReport:
    """Complete resolution report for an experiment."""
    resolutions: list[DatasetResolution]
    runnable_steps: list[str]
    blocked_steps: list[str]
    can_proceed: bool
    full_experiment_possible: bool
    summary: str
    uncertainty_summary: str
    transaction: Any = None  # ManifestTransaction, if changes were made

    @property
    def available(self) -> list[DatasetResolution]:
        return [r for r in self.resolutions if r.status == "available"]

    @property
    def acquired(self) -> list[DatasetResolution]:
        return [r for r in self.resolutions if r.status == "acquired"]

    @property
    def failed(self) -> list[DatasetResolution]:
        return [r for r in self.resolutions
                if r.status in ("failed", "manual_required", "auth_required")]

    def to_envelope_context(self) -> dict:
        """Produce a dict suitable for embedding in envelope lineage."""
        return {
            "full_experiment_possible": self.full_experiment_possible,
            "datasets_available": [r.dataset_name for r in self.available],
            "datasets_acquired": [r.dataset_name for r in self.acquired],
            "datasets_missing": [
                {
                    "name": r.dataset_name,
                    "status": r.status,
                    "uncertainty": r.uncertainty_without,
                }
                for r in self.failed
            ],
            "runnable_steps": self.runnable_steps,
            "blocked_steps": self.blocked_steps,
            "uncertainty_summary": self.uncertainty_summary,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DRY-RESOLUTION RESULT TYPES (non-acquiring: sense, do not act)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DatasetGap(DatasetResolution):
    """A non-acquiring read of one dataset: is it present, and if not, what
    would it take to fill it HERE? Extends DatasetResolution with feasibility
    sensed from THIS environment (introspect), never acquiring. The person
    decides; a later, explicit resolve() acts.

    status is one of: present / declared_absent / undeclared.
    """
    acquirable: bool = False          # auto-acquirable in principle (from the source block)
    requires_auth: bool = False
    requires_manual: bool = False
    feasible_now: bool = False        # acquisition could even be ATTEMPTED in this environment
    feasibility_note: str = ""
    options: list[str] = field(default_factory=list)  # subset of {acquire, upload_manual, run_anyway}


@dataclass
class DryResolutionReport:
    """What a plot can and cannot run right now, sensed without acquiring. The
    read wonder shows a person before anything is fetched; a separate resolve()
    is the deliberate act."""
    gaps: list[DatasetGap]
    runnable_steps: list[str]
    blocked_steps: list[str]
    can_proceed: bool
    full_experiment_possible: bool
    summary: str
    uncertainty_summary: str

    @property
    def present(self) -> list[DatasetGap]:
        return [g for g in self.gaps if g.status == "present"]

    @property
    def missing(self) -> list[DatasetGap]:
        return [g for g in self.gaps if g.status != "present"]

    @property
    def critical_missing(self) -> list[DatasetGap]:
        return [g for g in self.missing if g.critical]

    def to_envelope_context(self) -> dict:
        """A dict suitable for embedding in envelope lineage, or for wonder to
        read aloud. Mirrors ResolutionReport.to_envelope_context, plus the
        feasibility and options a person needs to choose."""
        return {
            "full_experiment_possible": self.full_experiment_possible,
            "datasets_present": [g.dataset_name for g in self.present],
            "datasets_missing": [
                {
                    "name": g.dataset_name,
                    "status": g.status,
                    "critical": g.critical,
                    "acquirable": g.acquirable,
                    "feasible_now": g.feasible_now,
                    "feasibility_note": g.feasibility_note,
                    "options": g.options,
                    "uncertainty": g.uncertainty_without,
                }
                for g in self.missing
            ],
            "runnable_steps": self.runnable_steps,
            "blocked_steps": self.blocked_steps,
            "uncertainty_summary": self.uncertainty_summary,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# RESOLUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ResolutionEngine:
    """Composes answers from manifest, DAG, method, and providers.
    
    Thin coordinator — each component owns its own intelligence.
    """

    def __init__(
        self,
        manifest,           # Manifest (from orchestrator)
        experiment=None,    # Experiment ~ absent for a gap-driven acquire
        provider_registry=None,  # ProviderRegistry
        dependency_resolver=None,  # DependencyResolver ~ absent likewise
        method_data: dict | None = None,  # parsed method YAML (raw dict)
    ):
        # experiment and dag are optional because acquisition can precede
        # composition. resolve() and dry_resolve() answer "this experiment
        # names these datasets, are they here?" and need both. acquire_types()
        # answers "a method requires these semantic types, can this plot get
        # them?", which is asked BEFORE an experiment exists ~ that is the
        # whole point of reading the mart backward. S-01.
        self.manifest = manifest
        self.experiment = experiment
        self.providers = provider_registry
        self.dag = dependency_resolver
        self.method_data = method_data or {}

    def resolve(self) -> ResolutionReport:
        """Run full resolution: check → acquire → trace → advise."""

        # 1. Collect $manifest.* references from experiment
        manifest_refs = self.dag.collect_manifest_refs()

        # 2. Import transaction (lazy to avoid circular imports)
        from canopy.manifest.transaction import ManifestTransaction
        transaction = ManifestTransaction(self.manifest.manifest_path) \
            if self.manifest.manifest_path else None

        # 3. Resolve each referenced dataset
        resolutions: list[DatasetResolution] = []
        missing_datasets: set[str] = set()

        for dataset_name, dependent_steps in manifest_refs.items():
            resolution = self._resolve_dataset(
                dataset_name, dependent_steps, transaction
            )
            resolutions.append(resolution)

            if resolution.status not in ("available", "acquired"):
                missing_datasets.add(dataset_name)

        # 4. Trace DAG impact for missing datasets
        if missing_datasets:
            impact = self.dag.trace_impact(missing_datasets)
            for resolution in resolutions:
                if resolution.dataset_name in impact:
                    resolution.orphaned_steps = impact[resolution.dataset_name]
        
        # 5. Look up method uncertainty context
        for resolution in resolutions:
            if resolution.status not in ("available", "acquired"):
                role, uncertainty, critical = self._lookup_method_context(
                    resolution.semantic_type
                )
                resolution.analytical_role = role
                resolution.uncertainty_without = uncertainty
                resolution.critical = critical

        # 6. Compute runnable/blocked steps
        all_orphaned: set[str] = set()
        for r in resolutions:
            if r.status not in ("available", "acquired"):
                all_orphaned.update(r.orphaned_steps)

        plan = self.dag.create_execution_plan()
        runnable = [s for s in plan.steps_in_order if s not in all_orphaned]
        blocked = [s for s in plan.steps_in_order if s in all_orphaned]

        # 7. Determine if we can proceed
        full_possible = len(missing_datasets) == 0
        # Can proceed if at least some runnable steps exist,
        # OR if all missing datasets are non-critical
        can_proceed = (
            full_possible
            or len(runnable) > 0
            or all(not r.critical for r in resolutions
                   if r.status not in ("available", "acquired"))
        )

        # 8. Build summaries
        summary = self._build_summary(resolutions, runnable, blocked)
        uncertainty_summary = self._build_uncertainty_summary(resolutions)

        return ResolutionReport(
            resolutions=resolutions,
            runnable_steps=runnable,
            blocked_steps=blocked,
            can_proceed=can_proceed,
            full_experiment_possible=full_possible,
            summary=summary,
            uncertainty_summary=uncertainty_summary,
            transaction=transaction if (transaction and transaction.has_changes) else None,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # TYPE-DRIVEN ACQUISITION — closing the ring
    # ─────────────────────────────────────────────────────────────────────────

    def datasets_providing(self, semantic_type: str) -> list:
        """

        which declared datasets provide this semantic type ~ a LIST, because a
        plot may legitimately declare more than one (lst_summer_2023 and
        lst_summer_2019 are both land_surface_temperature). when several
        answer, that is a choice for a person, not something to resolve
        silently by picking the first. ~

        the manifest is keyed by dataset NAME and readiness speaks in
        semantic TYPES; in the nyc manifest those happen to coincide for
        every dataset, which is why the two keyspaces went unnoticed. this is
        the translation between them. ~

        """
        return [d for d in self.manifest.datasets.values()
                if d.semantic_type == semantic_type]

    def acquire_types(self, semantic_types, *, dry: bool = True,
                      loam=None, plot: str | None = None) -> dict:
        """

        rewilding closes the ring ~ given the semantic types a method needs
        and the mart cannot satisfy (readiness.acquisition_gap), say what it
        would take to get each one HERE, and optionally get it.

        readiness computed this list and nothing ever read it: the backward
        reader and the acquirer were both built and never joined. this is the
        join. four honest outcomes per type:

          ~ present     the manifest declares it and the file is here
          ~ acquirable  declared, and a provider on this machine can fetch it
          ~ blocked     declared, but it needs credentials or a human hand
          ~ undeclared  nothing in this manifest provides this type at all,
                        which is the case discover(bbox) exists to answer:
                        propose a source rather than report a dead end

        dry=True senses only and moves no bytes, the same courtesy
        dry_resolve() extends. dry=False acquires what it can. ~

        """
        from canopy.manifest.transaction import ManifestTransaction

        transaction = None
        if not dry and self.manifest.manifest_path:
            transaction = ManifestTransaction(self.manifest.manifest_path)

        present, acquirable, blocked, undeclared, ambiguous = [], [], [], [], []
        acquired_unconformed = []

        for semantic_type in semantic_types:
            candidates = self.datasets_providing(semantic_type)

            if not candidates:
                undeclared.append({
                    "semantic_type": semantic_type,
                    "message": (f"no dataset in the {self.manifest.city_name} "
                                f"manifest provides '{semantic_type}'."),
                    "next_step": ("declare one, or ask the providers to discover "
                                  "a source for this bbox"),
                })
                continue

            if len(candidates) > 1:
                ambiguous.append({
                    "semantic_type": semantic_type,
                    "datasets": [d.name for d in candidates],
                    "message": (f"{len(candidates)} datasets provide "
                                f"'{semantic_type}'; which one is a choice for "
                                f"you, not for the engine."),
                })

            for dataset in candidates:
                if not dataset.is_usable:
                    blocked.append({
                        "semantic_type": semantic_type,
                        "dataset": dataset.name,
                        "reason": "underspecified declaration",
                        "detail": "; ".join(dataset.underspecified),
                    })
                    continue

                full_path = self.manifest.data_dir / dataset.path
                if dataset.available and full_path.exists():
                    # present is not the same as ANALYSABLE. a holding can be
                    # declared, acquired, and sitting on disk while never
                    # having been through the pipeline ~ arrived but never
                    # tended. readiness reads the conformed tiers and calls
                    # that a gap; acquisition reads the manifest and calls it
                    # present. both are right, and the instruction they imply
                    # is completely different: "go fetch this" versus "you
                    # already have this, run something on it". when a mart is
                    # offered, say which. S-01.
                    conformed = None
                    if loam is not None and plot is not None:
                        conformed = any(
                            row.get("semantic_type") == semantic_type
                            for tier in ("tended", "gathered")
                            for row in loam.find(plot=plot, tier=tier))

                    record = {
                        "semantic_type": semantic_type,
                        "dataset": dataset.name,
                        "path": str(dataset.path),
                    }
                    if conformed is False:
                        record["next_step"] = (
                            "acquired but never conformed ~ this needs an "
                            "experiment run on it, not acquisition")
                        acquired_unconformed.append(record)
                    else:
                        present.append(record)
                    continue

                if dataset.requires_manual_action:
                    blocked.append({
                        "semantic_type": semantic_type,
                        "dataset": dataset.name,
                        "reason": "manual",
                        "detail": ((dataset.source or {}).get("notes")
                                   or "this source must be placed by hand."),
                    })
                    continue

                if dataset.requires_auth:
                    blocked.append({
                        "semantic_type": semantic_type,
                        "dataset": dataset.name,
                        "reason": "credentials",
                        "detail": (f"source type '{dataset.source_type}' needs "
                                   f"credentials this machine does not carry."),
                    })
                    continue

                if not dataset.is_auto_acquirable:
                    blocked.append({
                        "semantic_type": semantic_type,
                        "dataset": dataset.name,
                        "reason": "not auto-acquirable",
                        "detail": (f"source type '{dataset.source_type}' is not "
                                   f"fetched without a person asking."),
                    })
                    continue

                entry = {
                    "semantic_type": semantic_type,
                    "dataset": dataset.name,
                    "source_type": dataset.source_type,
                    "provider": dataset.provider_name,
                    "path": str(dataset.path),
                }

                if dry:
                    acquirable.append(entry)
                else:
                    resolution = self._resolve_dataset(dataset.name, [], transaction)
                    entry["status"] = resolution.status
                    entry["message"] = resolution.message
                    if resolution.status in ("available", "acquired"):
                        acquirable.append(entry)
                    else:
                        blocked.append({**entry, "reason": resolution.status,
                                        "detail": resolution.message})

        if transaction and transaction.has_changes:
            transaction.commit()

        return {
            "plot": self.manifest.city_id,
            "dry": dry,
            "requested": list(semantic_types),
            "present": present,
            "acquired_unconformed": acquired_unconformed,
            "acquirable": acquirable,
            "blocked": blocked,
            "undeclared": undeclared,
            "ambiguous": ambiguous,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # DRY RESOLUTION — sense feasibility without acquiring
    # ─────────────────────────────────────────────────────────────────────────

    def dry_resolve(self) -> DryResolutionReport:
        """Sense what is present and, for each gap, what it would take to fill
        it HERE ~ without acquiring anything. resolve() acts; this only reads,
        so discovery stays side-effect-free and a person can weigh real options
        before a single byte is fetched. ~"""
        manifest_refs = self.dag.collect_manifest_refs()

        gaps: list[DatasetGap] = []
        missing: set[str] = set()
        for dataset_name, dependent_steps in manifest_refs.items():
            gap = self._sense_dataset(dataset_name, dependent_steps)
            gaps.append(gap)
            if gap.status != "present":
                missing.add(dataset_name)

        # trace DAG impact for missing datasets (same walk resolve() uses)
        if missing:
            impact = self.dag.trace_impact(missing)
            for gap in gaps:
                if gap.dataset_name in impact:
                    gap.orphaned_steps = impact[gap.dataset_name]

        # method context (role / uncertainty / critical) for each gap, then the
        # options that follow from it
        for gap in gaps:
            if gap.status != "present":
                role, uncertainty, critical = self._lookup_method_context(gap.semantic_type)
                gap.analytical_role = role
                gap.uncertainty_without = uncertainty
                gap.critical = critical
            gap.options = self._gap_options(gap)

        # runnable / blocked steps (same DAG logic as resolve)
        all_orphaned: set[str] = set()
        for g in gaps:
            if g.status != "present":
                all_orphaned.update(g.orphaned_steps)
        plan = self.dag.create_execution_plan()
        runnable = [s for s in plan.steps_in_order if s not in all_orphaned]
        blocked = [s for s in plan.steps_in_order if s in all_orphaned]

        full_possible = len(missing) == 0
        # a critical gap blocks the FULL experiment; the door still opens for a
        # caveated or teaching run (that reconciliation lives in the orchestrator).
        has_critical_gap = any(g.critical for g in gaps if g.status != "present")
        can_proceed = full_possible or (not has_critical_gap) or len(runnable) > 0

        return DryResolutionReport(
            gaps=gaps,
            runnable_steps=runnable,
            blocked_steps=blocked,
            can_proceed=can_proceed,
            full_experiment_possible=full_possible,
            summary=self._build_dry_summary(gaps, runnable, blocked),
            uncertainty_summary=self._build_dry_uncertainty(gaps),
        )

    def _sense_dataset(self, dataset_name: str, dependent_steps: list[str]) -> DatasetGap:
        """Presence and feasibility for one dataset, without acquiring. ~"""
        dataset = self.manifest.datasets.get(dataset_name)

        if dataset is None:
            return DatasetGap(
                dataset_name=dataset_name, semantic_type="unknown",
                status="undeclared",
                message=(f"'{dataset_name}' is referenced by a step but not declared "
                         f"in the {self.manifest.city_name} manifest."),
                dependent_steps=list(dependent_steps),
            )

        full_path = self.manifest.data_dir / dataset.path
        if dataset.available and full_path.exists():
            return DatasetGap(
                dataset_name=dataset_name, semantic_type=dataset.semantic_type,
                status="present",
                message=f"Present at {dataset.path}.",
                path=str(full_path), dependent_steps=list(dependent_steps),
            )

        requires_manual = dataset.requires_manual_action
        requires_auth = dataset.requires_auth
        # acquirable == a registered provider can actually fetch this source, and
        # it is not a manual-only one. Grounded in the real ProviderRegistry
        # (find_provider is side-effect-free), so a source no provider handles
        # reads honestly as not-acquirable. feasibility (below) then checks
        # network, reachability, and credentials.
        acquirable = (not requires_manual) and self._provider_can_handle(dataset.source)
        feasible_now, note = self._sense_feasibility(
            dataset, acquirable, requires_auth, requires_manual
        )
        return DatasetGap(
            dataset_name=dataset_name, semantic_type=dataset.semantic_type,
            status="declared_absent",
            message=f"Declared but not present at {dataset.path}.",
            dependent_steps=list(dependent_steps),
            acquirable=acquirable, requires_auth=requires_auth,
            requires_manual=requires_manual,
            feasible_now=feasible_now, feasibility_note=note,
        )

    def _sense_feasibility(self, dataset, acquirable: bool, requires_auth: bool,
                           requires_manual: bool) -> tuple[bool, str]:
        """Can acquisition even be ATTEMPTED in this environment? Senses via
        introspect; never acquires. Returns (feasible_now, note). ~"""
        if requires_manual:
            return False, "needs manual acquisition; it cannot be fetched automatically."
        if not acquirable:
            if dataset.source is None:
                return False, "no source is declared; upload it, or add a source."
            return False, (f"no registered provider can handle source type "
                           f"'{dataset.source_type}'; upload it manually.")

        reasons: list[str] = []
        if not is_online():
            reasons.append("offline")
        elif not provider_reachable(dataset.source or {}):
            reasons.append("the provider is not reachable from here")
        if requires_auth:
            kind = self._credential_kind(dataset)
            if kind and not has_credentials(kind):
                reasons.append(f"missing {kind} credentials")
        room = disk_headroom(str(self.manifest.data_dir))
        if room.free_gib < 0.5:
            reasons.append(f"low disk ({room.free_gib:.1f} GiB free)")

        if reasons:
            return False, "cannot acquire here: " + ", ".join(reasons) + "."
        return True, "acquisition looks feasible from here right now."

    def _provider_can_handle(self, source: dict | None) -> bool:
        """Does a registered provider know how to acquire this source? Consults
        the registry's can_handle (side-effect-free). If no registry is wired, a
        declared source is assumed acquirable, as before. ~"""
        if source is None:
            return False
        if self.providers is None:
            return True
        return self.providers.find_provider(source) is not None

    @staticmethod
    def _credential_kind(dataset) -> str | None:
        """Best-effort: which credential kind this source would need. Named, not
        guessed silently; extend as providers are added. ~"""
        source = dataset.source or {}
        st = dataset.source_type
        provider = str(source.get("provider", "")).lower()
        if st == "earthengine" or provider == "earthengine":
            return "earthengine"
        if st == "s3":
            return "aws"
        if "arcgis" in provider:
            return "arcgis"
        return None

    def _gap_options(self, gap: DatasetGap) -> list[str]:
        """The real choices a person has for this gap. The door does not lock:
        run_anyway is always offered ~ for a non-critical gap it yields a
        caveated result, for a critical one it teaches, through honest
        provenance, exactly where and why it cannot proceed. ~"""
        if gap.status == "present":
            return []
        options: list[str] = []
        if gap.acquirable and gap.feasible_now:
            options.append("acquire")
        options.append("upload_manual")
        options.append("run_anyway")
        return options

    def _build_dry_summary(self, gaps, runnable, blocked) -> str:
        present = len([g for g in gaps if g.status == "present"])
        missing = [g for g in gaps if g.status != "present"]
        parts = [f"{present} present"]
        if missing:
            crit = len([g for g in missing if g.critical])
            parts.append(f"{len(missing)} missing" + (f" ({crit} critical)" if crit else ""))
        s = "Data check: " + ", ".join(parts) + "."
        s += f" {len(runnable)} of {len(runnable) + len(blocked)} steps can run."
        if blocked:
            s += f" {len(blocked)} blocked."
        return s

    def _build_dry_uncertainty(self, gaps) -> str:
        lines = [f"[{g.dataset_name}] {g.uncertainty_without.strip()}"
                 for g in gaps
                 if g.status != "present" and g.uncertainty_without]
        return "\n".join(lines) if lines else "No uncertainty notes ~ all present, or no method context."

    def _resolve_dataset(
        self,
        dataset_name: str,
        dependent_steps: list[str],
        transaction,
    ) -> DatasetResolution:
        """Resolve a single dataset: check availability, attempt acquisition."""

        dataset = self.manifest.datasets.get(dataset_name)

        # Not declared in manifest
        if dataset is None:
            return DatasetResolution(
                dataset_name=dataset_name,
                semantic_type="unknown",
                status="failed",
                message=(
                    f"Dataset '{dataset_name}' is not declared in the "
                    f"{self.manifest.city_name} manifest."
                ),
                dependent_steps=dependent_steps,
            )

        full_path = self.manifest.data_dir / dataset.path

        # Available and file exists
        if dataset.available and full_path.exists():
            return DatasetResolution(
                dataset_name=dataset_name,
                semantic_type=dataset.semantic_type,
                status="available",
                message=f"Available at {dataset.path}",
                path=str(full_path),
                dependent_steps=dependent_steps,
            )

        # Try to acquire (whether marked available-but-missing, or unavailable)
        if dataset.source is not None:
            result = self.providers.acquire(
                source_config=dataset.source,
                cache_path=full_path,
                dataset_name=dataset_name,
                gee_project=self.manifest.gee_project,
                plot_dir=self.manifest.data_dir,
            )

            if result.success:
                # Queue manifest update
                if transaction:
                    reason = f"Acquired via {result.message}"
                    transaction.set_available(dataset_name, True, reason)
                    transaction.update_cache_timestamp(dataset_name)

                # Update in-memory
                dataset.available = True

                return DatasetResolution(
                    dataset_name=dataset_name,
                    semantic_type=dataset.semantic_type,
                    status="acquired",
                    message=result.message,
                    path=result.path,
                    dependent_steps=dependent_steps,
                )

            # Acquisition failed — determine status from result
            if result.requires_auth:
                return DatasetResolution(
                    dataset_name=dataset_name,
                    semantic_type=dataset.semantic_type,
                    status="auth_required",
                    message=result.message,
                    dependent_steps=dependent_steps,
                    instructions=result.auth_instructions,
                )

            if result.requires_manual:
                return DatasetResolution(
                    dataset_name=dataset_name,
                    semantic_type=dataset.semantic_type,
                    status="manual_required",
                    message=result.message,
                    dependent_steps=dependent_steps,
                    instructions=result.manual_instructions,
                )

            return DatasetResolution(
                dataset_name=dataset_name,
                semantic_type=dataset.semantic_type,
                status="failed",
                message=result.message,
                dependent_steps=dependent_steps,
            )

        # No source config
        return DatasetResolution(
            dataset_name=dataset_name,
            semantic_type=dataset.semantic_type,
            status="failed",
            message=(
                f"Dataset '{dataset_name}' is not available and has no "
                f"source configuration for acquisition."
            ),
            dependent_steps=dependent_steps,
        )

    def _lookup_method_context(
        self, semantic_type: str
    ) -> tuple[str | None, str | None, bool]:
        """Look up role, uncertainty, and criticality from method's requires_data.
        
        Returns (role, uncertainty_without, critical).
        """
        requires_data = self.method_data.get("requires_data", [])

        for req in requires_data:
            if semantic_type in req.get("semantic_types", []):
                return (
                    req.get("role"),
                    req.get("uncertainty_without"),
                    req.get("critical", True),
                )

        # Not found in method — assume critical by default
        return None, None, True

    def _build_summary(
        self,
        resolutions: list[DatasetResolution],
        runnable: list[str],
        blocked: list[str],
    ) -> str:
        counts = {
            "available": len([r for r in resolutions if r.status == "available"]),
            "acquired": len([r for r in resolutions if r.status == "acquired"]),
            "failed": len([r for r in resolutions if r.status == "failed"]),
            "manual": len([r for r in resolutions if r.status == "manual_required"]),
            "auth": len([r for r in resolutions if r.status == "auth_required"]),
        }

        parts = []
        if counts["available"]:
            parts.append(f"{counts['available']} available")
        if counts["acquired"]:
            parts.append(f"{counts['acquired']} newly acquired")
        if counts["failed"]:
            parts.append(f"{counts['failed']} failed")
        if counts["manual"]:
            parts.append(f"{counts['manual']} need manual acquisition")
        if counts["auth"]:
            parts.append(f"{counts['auth']} need authentication")

        summary = f"Data resolution: {', '.join(parts)}."
        summary += f" {len(runnable)} of {len(runnable) + len(blocked)} steps can run."

        if blocked:
            summary += f" {len(blocked)} steps blocked."

        return summary

    def _build_uncertainty_summary(
        self, resolutions: list[DatasetResolution]
    ) -> str:
        """Combine uncertainty_without from all missing datasets."""
        uncertainties = []
        for r in resolutions:
            if r.uncertainty_without and r.status not in ("available", "acquired"):
                uncertainties.append(
                    f"[{r.dataset_name}] {r.uncertainty_without.strip()}"
                )

        if not uncertainties:
            return "No uncertainty notes — all data available or no method context."

        return "\n".join(uncertainties)