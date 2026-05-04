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
# RESOLUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ResolutionEngine:
    """Composes answers from manifest, DAG, method, and providers.
    
    Thin coordinator — each component owns its own intelligence.
    """

    def __init__(
        self,
        manifest,           # Manifest (from orchestrator)
        experiment,         # Experiment
        provider_registry,  # ProviderRegistry
        dependency_resolver,  # DependencyResolver
        method_data: dict | None = None,  # parsed method YAML (raw dict)
    ):
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
