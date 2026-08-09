"""canopy/orchestrator/orchestrator.py

Experiment-based orchestrator for the rewildingCities pipeline.

TODO(refactor, post-sprint-8): Consider further splits — validation.py
(the _validate_* methods), execution.py (the _execute_step / _write_run_log
methods). Deferred because they're tightly coupled to Orchestrator internals
and Sprint 8 will inform what actually needs to be reusable.

Sprint 8 changes (2026-05):
  - _validate_method_choices now distinguishes enumerated choices (with
    options) from parametric choices (with type/range). Numeric/parametric
    choices like `buffer_interval: 30` no longer trip the spurious
    "not in options []" warning.
  - _resolve_method_path is now strict by default: if a method id is not
    in garden/methods/index.yml the orchestrator raises rather than
    falling back to a legacy path transform. Sprint 6's fallback served
    its purpose during the index's first-write phase; Sprint 8 closes
    the door so future contributors can't accidentally skip indexing.
    A `strict_method_path=False` kwarg preserves the legacy behavior for
    deliberate use (e.g. third-party method files outside the commons).
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from .references import ReferenceResolver
from .dependencies import DependencyResolver, ExecutionPlan
from .registry import RegistryManager
from .semantic_types import SemanticTypeRegistry
from .models import (
    Manifest,
    ManifestDataset,
    ManifestInconsistency,
    Experiment,
    Lineage,
    StepDefinition,
    PrimitiveSpec,
    StepResult,
    OrchestrationResult,
    Method,
    MethodChoice,
    MethodIndexEntry,
)
from .parsing import parse_manifest, parse_experiment, parse_method

from ..envelope import (
    EnvelopeBuilder,
    EnvelopeInput,
    Envelope,
    BuildResult,
    read_envelope,
    write_envelope,
)


def run_experiment(
    experiment_path: str | Path,
    profile: str = "full",
    project_root: str | Path | None = None
) -> OrchestrationResult:
    """Convenience function to run an experiment.

    Example:
        result = run_experiment(
            "garden/experiments/nyc_park_cooling_pedestrian.yml",
            profile="dev"
        )
    """
    orchestrator = Orchestrator(
        experiment_path=experiment_path,
        profile=profile,
        project_root=project_root
    )
    return orchestrator.run()


def visualize_experiment(experiment_path: str | Path) -> str:
    """Generate ASCII visualization of an experiment's execution plan."""
    experiment = parse_experiment(experiment_path)
    resolver = DependencyResolver(experiment)
    return resolver.visualize()


def load_methods_index(project_root: Path) -> dict[str, MethodIndexEntry]:
    """Load garden/methods/index.yml as a flat id -> MethodIndexEntry map.

    Public API. Called by Orchestrator._resolve_method_path at experiment
    time and by the future catalog/discover layer (Sprint 10's GET /methods).

    Returns an empty dict if the index doesn't exist — the orchestrator's
    fallback path will then handle resolution via string transform.

    Raises ValueError only if the index file exists but is structurally
    invalid (e.g. duplicate ids across domains).
    """
    index_path = project_root / "garden" / "methods" / "index.yml"
    if not index_path.exists():
        return {}

    with open(index_path, 'r') as f:
        data = yaml.safe_load(f) or {}

    flat: dict[str, MethodIndexEntry] = {}
    for domain, entries in (data.get("methods") or {}).items():
        for entry in entries or []:
            method_id = entry.get("id")
            if not method_id:
                continue
            if method_id in flat:
                raise ValueError(
                    f"Duplicate method id '{method_id}' in {index_path}: "
                    f"appears in domain '{flat[method_id].domain}' and '{domain}'. "
                    f"Method ids must be globally unique."
                )
            flat[method_id] = MethodIndexEntry(
                id=method_id,
                domain=domain,
                path=entry.get("path", ""),
                name=entry.get("name", method_id),
                answers=entry.get("answers", []),
                raw=entry,
            )
    return flat


def _is_parametric_choice(method: Method, choice_name: str) -> bool:
    """True if the named choice is parametric (numeric/string/boolean with a type)
    rather than enumerated (with named options).

    Sprint 8: the method schema accepts both shapes. Enumerated choices declare
    `options:` keyed by option id (e.g. intensity_measure → TPM-M / TPM-A).
    Parametric choices declare `type:` and optionally `range:` / `default:`
    (e.g. buffer_interval → integer in meters, default 30). The validator
    must treat them differently or it warns spuriously on every parametric
    choice — see the Sprint 6/7 reference doc, section 3.6.

    Note: this is a temporary heuristic. The proper fix is for parse_method
    to model parametric choices distinctly (separate dataclass, or a Choice
    type discriminator). That refactor is post-sprint-8 — for now we read
    the empty options list as a signal.
    """
    if choice_name not in method.choices:
        return False
    choice = method.choices[choice_name]
    # Enumerated choices populate options with at least one entry.
    # Parametric choices have options == [] (empty after parse_method).
    return len(choice.options) == 0


class Orchestrator:
    """Executes experiments against city manifests.

    Three-phase execution: validate -> resolve data -> execute steps.
    Sprint 6 adds a Phase 1.5 that injects profile-driven sampling steps
    between validation and resolution.
    """

    def __init__(
        self,
        experiment_path: str | Path,
        profile: str = "full",
        project_root: str | Path | None = None,
        output_dir: str | Path | None = None,
        strict_method_path: bool = True,
    ):
        """Construct an Orchestrator.

        Args:
            experiment_path: Path to the experiment YAML file.
            profile: Active profile (full, dev, test, neighborhood).
            project_root: Project root override. Defaults to cwd.
            output_dir: Output directory override. Defaults to manifest's .data/.
            strict_method_path: If True (Sprint 8 default), method references
                must resolve through garden/methods/index.yml or
                _resolve_method_path raises FileNotFoundError. If False,
                falls back to the legacy string transform with a warning
                (Sprint 6/7 behavior). Set False only when working with
                method files outside the commons index.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.experiment_path = Path(experiment_path)
        self.profile = profile
        self.strict_method_path = strict_method_path

        self.experiment = parse_experiment(experiment_path)

        manifest_path = self.experiment_path.parent / self.experiment.manifest_path
        self.manifest = parse_manifest(manifest_path)

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.manifest.data_dir / ".data"
        self.envelope_dir = self.manifest.data_dir / ".envelopes"

        self.registry = RegistryManager(project_root=self.project_root)
        self.semantic_types = SemanticTypeRegistry(
            path=self.project_root / "seeds/schemas/semantic_types.yml"
        )

        self._dependency_resolver = DependencyResolver(self.experiment)
        self.plan = self._dependency_resolver.create_execution_plan()

        self.profile_config = self._load_profile_config()
        self.injection_log: list[dict] = []
        self._steps_injected = False
        self._inject_profile_steps()

        if self._steps_injected:
            self._dependency_resolver = DependencyResolver(self.experiment)
            self.plan = self._dependency_resolver.create_execution_plan()

        self.reference_resolver = ReferenceResolver(
            manifest=self.manifest,
            experiment=self.experiment
        )

        self.envelope_builder = EnvelopeBuilder(
            profile=profile,
            project_root=self.project_root
        )

        from canopy.providers import create_default_registry
        self.provider_registry = create_default_registry()

        self._run_started: datetime | None = None
        self._resolution_report = None

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 1: VALIDATION
    # ═══════════════════════════════════════════════════════════════════════

    def validate(self) -> tuple[list[str], list[str]]:
        """Validate the experiment before running."""
        errors = []
        warnings = []

        primitive_errors = self.registry.validate_all_primitives(self.experiment)
        errors.extend(primitive_errors)

        for step in self.experiment.steps:
            for input_name, ref in step.inputs.items():
                if ref.startswith("$manifest."):
                    dataset_name = ref.replace("$manifest.", "")
                    if dataset_name not in self.manifest.datasets:
                        errors.append(
                            f"Step '{step.id}' references $manifest.{dataset_name}, "
                            f"but manifest has no dataset '{dataset_name}'"
                        )

        for step in self.experiment.steps:
            self._validate_param_references(step, errors)

        self._validate_method_choices(warnings)

        return errors, warnings

    def _validate_param_references(self, step: StepDefinition, errors: list[str]) -> None:
        def check_value(value: Any, path: str) -> None:
            if isinstance(value, str):
                if value.startswith("$choices."):
                    choice_name = value.replace("$choices.", "")
                    if choice_name not in self.experiment.choices:
                        errors.append(f"Step '{step.id}' param {path} references $choices.{choice_name}, but no such choice exists")
                elif value.startswith("$parameters."):
                    param_name = value.replace("$parameters.", "")
                    if param_name not in self.experiment.parameters:
                        errors.append(f"Step '{step.id}' param {path} references $parameters.{param_name}, but no such parameter exists")
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    check_value(item, f"{path}[{i}]")
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_value(v, f"{path}.{k}")

        for param_name, param_value in step.params.items():
            check_value(param_value, param_name)

    def _validate_method_choices(self, warnings: list[str]) -> None:
        """Validate experiment.choices against the method's declared choices.

        Sprint 8: distinguishes enumerated choices (must match a named option)
        from parametric choices (type/range, no enumerated options). For
        parametric choices the validator only confirms the choice is declared
        — value validation against `range` and `type` is a future schema-level
        check (TODO: post-sprint-8).
        """
        method_ref = self.experiment.lineage.method_ref
        if not method_ref:
            return

        method_path = self._resolve_method_path(method_ref)
        if not method_path.exists():
            warnings.append(f"Method file not found: {method_path}. Choice validation skipped.")
            return

        try:
            method = parse_method(method_path)
        except Exception as e:
            warnings.append(f"Could not parse method file {method_path}: {e}. Choice validation skipped.")
            return

        for choice_name, choice_value in self.experiment.choices.items():
            if choice_name not in method.choices:
                warnings.append(f"Choice '{choice_name}' not declared in method '{method.name}'.")
                continue

            # Parametric choice (no enumerated options): accept any value.
            # Range/type validation is a separate concern (see method.schema.yml
            # $defs.choice properties `type`, `range`, `units`).
            if _is_parametric_choice(method, choice_name):
                continue

            # Enumerated choice: value must match a declared option id.
            if choice_value not in method.choices[choice_name].options:
                warnings.append(
                    f"Choice '{choice_name}: {choice_value}' not in method options "
                    f"{method.choices[choice_name].options}."
                )

        for choice_name in method.choices:
            if choice_name not in self.experiment.choices:
                # Parametric choices with a default in the method file are
                # acceptable to omit. Enumerated choices without an experiment
                # value are still flagged — they're epistemological commitments
                # that should be made deliberately.
                if _is_parametric_choice(method, choice_name):
                    continue
                warnings.append(f"Method '{method.name}' declares choice '{choice_name}', but experiment does not provide it.")

        # Sprint 8: in strict mode (the default) _resolve_method_path raises
        # when a method id is not indexed, so this branch is dead code there.
        # Kept live for strict_method_path=False users.
        if getattr(self, "_method_path_fallback_used", False):
            warnings.append(
                f"Method '{method_ref}' was not found in garden/methods/index.yml; "
                f"resolved via legacy path transform. Add it to the index for clarity "
                f"and future catalog support."
            )

    def _resolve_method_path(self, method_ref: str) -> Path:
        """Resolve a method reference to its file path via the methods index.

        Sprint 8 default behavior: strict. If the method id is not in
        garden/methods/index.yml, raises FileNotFoundError with a message
        pointing the contributor at the index. This makes the index
        load-bearing for real, not just by convention.

        Pre-Sprint-8 behavior (when constructed with strict_method_path=False):
        falls back to legacy string transform with a warning surfaced through
        _validate_method_choices. Preserved for deliberate out-of-commons use.
        """
        ref_clean = method_ref[len("$methods/"):] if method_ref.startswith("$methods/") else method_ref
        method_id = ref_clean.rsplit("/", 1)[-1].removesuffix(".yml")

        if not hasattr(self, "_methods_index"):
            try:
                self._methods_index = load_methods_index(self.project_root)
            except ValueError as e:
                self._methods_index = {}
                self._methods_index_error = str(e)

        if method_id in self._methods_index:
            entry = self._methods_index[method_id]
            return self.project_root / "garden" / "methods" / entry.path

        # Method id is not indexed.
        if self.strict_method_path:
            available = ", ".join(sorted(self._methods_index.keys())) or "(none)"
            index_path = self.project_root / "garden" / "methods" / "index.yml"
            raise FileNotFoundError(
                f"Method '{method_ref}' (id: '{method_id}') is not in {index_path}. "
                f"Sprint 8+ requires every method reference to be indexed.\n"
                f"  Indexed methods: {available}\n"
                f"  Fix: add this method's id, path, and name to "
                f"garden/methods/index.yml. See existing entries for the schema.\n"
                f"  Workaround (not recommended): construct the Orchestrator "
                f"with strict_method_path=False to restore the Sprint 6/7 fallback."
            )

        fallback_ref = ref_clean if ref_clean.endswith(".yml") else f"{ref_clean}.yml"
        self._method_path_fallback_used = True
        return self.project_root / "garden" / "methods" / fallback_ref

    def _load_method_data(self) -> dict:
        """Load raw method YAML for the Resolution Engine."""
        method_ref = self.experiment.lineage.method_ref
        if not method_ref:
            return {}
        method_path = self._resolve_method_path(method_ref)
        if not method_path.exists():
            return {}
        try:
            with open(method_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 1.5: STEP INJECTION (Sprint 6)
    # ═══════════════════════════════════════════════════════════════════════

    def _load_profile_config(self) -> dict:
        """Load the active profile's configuration from seeds/profiles/profiles.yml."""
        profiles_path = self.project_root / "seeds" / "profiles" / "profiles.yml"
        if not profiles_path.exists():
            raise FileNotFoundError(
                f"Profile configuration not found: {profiles_path}\n"
                f"Expected seeds/profiles/profiles.yml with at least 'full', "
                f"'dev', 'test', 'neighborhood' profiles defined."
            )

        with open(profiles_path, 'r') as f:
            data = yaml.safe_load(f) or {}

        profiles = data.get("profiles", {})
        if self.profile not in profiles:
            available = ", ".join(sorted(profiles.keys()))
            raise ValueError(
                f"Profile '{self.profile}' not found in {profiles_path}. "
                f"Available: {available}"
            )

        return profiles[self.profile]

    def _find_injection_points(self) -> list[str]:
        """Find step IDs after which a sampling step should be injected.

        Walks forward from each $manifest.<name> vector reference along its
        linear preparation chain. Stops at the last step whose output is
        consumed by 2 or more downstream steps — that's the injection point.

        Returns an empty list if no vector chains fan out.
        """
        consumers: dict[str, list[str]] = {step.id: [] for step in self.experiment.steps}
        for step in self.experiment.steps:
            for ref in step.inputs.values():
                if ref.startswith("$steps."):
                    producer = ref[len("$steps."):].split(".", 1)[0]
                    if producer in consumers:
                        consumers[producer].append(step.id)

        manifest_chain_heads: dict[str, str] = {}
        for step in self.experiment.steps:
            for ref in step.inputs.values():
                if not ref.startswith("$manifest."):
                    continue
                dataset_name = ref[len("$manifest."):]
                dataset = self.manifest.datasets.get(dataset_name)
                if dataset is None:
                    continue
                category = self.semantic_types.get_category(dataset.semantic_type)
                if category != "vector":
                    continue
                manifest_chain_heads.setdefault(dataset_name, step.id)

        steps_by_id = {s.id: s for s in self.experiment.steps}
        injection_points: list[str] = []

        for dataset_name, head_id in manifest_chain_heads.items():
            current_id = head_id
            while True:
                downstream = consumers[current_id]
                if len(downstream) >= 2:
                    injection_points.append(current_id)
                    break
                if len(downstream) == 0:
                    break
                next_step = steps_by_id[downstream[0]]
                step_refs = [
                    ref for ref in next_step.inputs.values()
                    if ref.startswith("$steps.")
                ]
                if len(step_refs) > 1:
                    injection_points.append(current_id)
                    break
                current_id = next_step.id

        seen = set()
        deduped = []
        for step_id in injection_points:
            if step_id not in seen:
                seen.add(step_id)
                deduped.append(step_id)
        return deduped

    def _create_sampling_step(
        self,
        after_step_id: str,
        sampling_config: dict,
    ) -> StepDefinition:
        """Build a StepDefinition for a sampling step injected after after_step_id."""
        after_step = self._get_step(after_step_id)
        if len(after_step.outputs) != 1:
            raise ValueError(
                f"Cannot inject sampling after step '{after_step_id}': "
                f"step has {len(after_step.outputs)} outputs, expected exactly 1."
            )
        output_name, output_semantic_type = list(after_step.outputs.items())[0]

        sampling_params = {
            "method": sampling_config.get("method", "random"),
            "n": sampling_config.get("n", 50),
            "n_per_stratum": sampling_config.get("n_per_stratum", 5),
            "stratify_by": sampling_config.get("stratify_by", "auto"),
            "seed": sampling_config.get("seed", 42),
            "filter": sampling_config.get("filter"),
            "feature_ids": sampling_config.get("feature_ids"),
        }

        return StepDefinition(
            id=f"sample_after_{after_step_id}",
            primitive="soil/sample_features",
            version="1.0.0",
            description=(
                f"[Profile-injected: {self.profile}] Subsample features from "
                f"{after_step_id} for faster iteration. "
                f"Method: {sampling_params['method']}."
            ),
            inputs={"features": f"$steps.{after_step_id}.{output_name}"},
            outputs={"sampled": output_semantic_type},
            params=sampling_params,
        )

    def _rewire_references(
        self,
        old_step_id: str,
        old_output_name: str,
        new_step_id: str,
        new_output_name: str,
    ) -> int:
        """Rewire downstream consumers of $steps.<old>.<old_output> to <new>.<new_output>.

        The new step itself is NOT rewired — its input still legitimately
        points at the old reference.
        """
        old_ref = f"$steps.{old_step_id}.{old_output_name}"
        new_ref = f"$steps.{new_step_id}.{new_output_name}"

        count = 0
        for step in self.experiment.steps:
            if step.id == new_step_id:
                continue
            for input_name, ref in list(step.inputs.items()):
                if ref == old_ref:
                    step.inputs[input_name] = new_ref
                    count += 1
        return count

    def _inject_profile_steps(self) -> None:
        """Inject sampling steps into the experiment based on the active profile.

        No-op if feature_sampling is disabled. Otherwise, for each injection
        point: build the step, append to self.experiment.steps, rewire
        downstream consumers, record in self.injection_log.
        """
        feature_sampling = self.profile_config.get("feature_sampling", {})
        if not feature_sampling.get("enabled", False):
            return

        injection_points = self._find_injection_points()
        if not injection_points:
            return

        for after_step_id in injection_points:
            new_step = self._create_sampling_step(after_step_id, feature_sampling)
            after_step = self._get_step(after_step_id)
            old_output_name = list(after_step.outputs.keys())[0]

            self.experiment.steps.append(new_step)

            rewired_count = self._rewire_references(
                old_step_id=after_step_id,
                old_output_name=old_output_name,
                new_step_id=new_step.id,
                new_output_name="sampled",
            )

            self.injection_log.append({
                "step_id": new_step.id,
                "after": after_step_id,
                "method": new_step.params.get("method"),
                "rewired_count": rewired_count,
            })
            self._steps_injected = True

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 2: DATA RESOLUTION
    # ═══════════════════════════════════════════════════════════════════════

    def resolve_data(self):
        """Check data availability, acquire missing, produce advisory report."""
        from .resolution import ResolutionEngine

        engine = ResolutionEngine(
            manifest=self.manifest,
            experiment=self.experiment,
            provider_registry=self.provider_registry,
            dependency_resolver=self._dependency_resolver,
            method_data=self._load_method_data(),
        )

        report = engine.resolve()
        self._resolution_report = report

        if report.transaction and report.transaction.has_changes:
            tx_result = report.transaction.commit()
            if not tx_result.success:
                report.summary += f" (Warning: manifest update had failures: {tx_result.changes_failed})"

        return report

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3: EXECUTION
    # ═══════════════════════════════════════════════════════════════════════

    def run(self) -> OrchestrationResult:
        """Execute the experiment in three phases: validate -> resolve -> execute."""
        self._run_started = datetime.now(timezone.utc)

        validation_errors, validation_warnings = self.validate()

        if validation_errors:
            result = OrchestrationResult(
                success=False, completed_steps=[], failed_step=None,
                step_results={}, final_envelopes={},
                lineage=self.experiment.lineage,
                warnings=validation_warnings,
                error="Validation failed:\n" + "\n".join(f"  - {e}" for e in validation_errors)
            )
            self._write_run_log(result)
            return result

        data_report = self.resolve_data()

        if not data_report.can_proceed:
            error_lines = [data_report.summary, ""]
            for r in data_report.failed:
                error_lines.append(f"  ✗ {r.dataset_name} ({r.semantic_type}): {r.message}")
                if r.instructions:
                    for line in r.instructions.strip().split("\n"):
                        error_lines.append(f"    {line}")
                if r.orphaned_steps:
                    error_lines.append(f"    Blocks steps: {', '.join(r.orphaned_steps)}")
                error_lines.append("")

            result = OrchestrationResult(
                success=False, completed_steps=[], failed_step=None,
                step_results={}, final_envelopes={},
                lineage=self.experiment.lineage,
                warnings=validation_warnings + [data_report.summary],
                error="\n".join(error_lines)
            )
            self._write_run_log(result)
            return result

        for r in data_report.acquired:
            validation_warnings.append(f"Acquired '{r.dataset_name}': {r.message}")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.envelope_dir.mkdir(parents=True, exist_ok=True)

        step_results: dict[str, StepResult] = {}
        completed_steps: list[str] = []

        for step_id in self.plan.steps_in_order:
            step = self._get_step(step_id)
            step_result = self._execute_step(step)
            step_results[step_id] = step_result

            if not step_result.success:
                result = OrchestrationResult(
                    success=False, completed_steps=completed_steps,
                    failed_step=step_id, step_results=step_results,
                    final_envelopes=self._collect_final_envelopes(step_results),
                    lineage=self.experiment.lineage,
                    warnings=validation_warnings,
                    error=step_result.error
                )
                self._write_run_log(result)
                return result

            completed_steps.append(step_id)

        final_envelopes = self._collect_final_envelopes(step_results)
        self._enrich_with_lineage(final_envelopes)

        result = OrchestrationResult(
            success=True, completed_steps=completed_steps,
            failed_step=None, step_results=step_results,
            final_envelopes=final_envelopes,
            lineage=self.experiment.lineage,
            warnings=validation_warnings, error=None
        )
        self._write_run_log(result)
        return result

    # ═══════════════════════════════════════════════════════════════════════
    # STEP EXECUTION
    # ═══════════════════════════════════════════════════════════════════════

    def _get_step(self, step_id: str) -> StepDefinition:
        for step in self.experiment.steps:
            if step.id == step_id:
                return step
        raise ValueError(f"Unknown step: {step_id}")

    def _execute_step(self, step: StepDefinition) -> StepResult:
        try:
            primitive_path, primitive_spec = self.registry.resolve_primitive(step.primitive)
        except (ValueError, FileNotFoundError) as e:
            return StepResult(step_id=step.id, success=False, envelope=None, output_paths={}, error="Primitive resolution failed", message=str(e))

        try:
            resolved_inputs = self.reference_resolver.resolve_step_inputs(step)
        except (ValueError, FileNotFoundError) as e:
            return StepResult(step_id=step.id, success=False, envelope=None, output_paths={}, error="Input resolution failed", message=str(e))

        envelope_inputs = []
        for input_name, (path, semantic_type, envelope) in resolved_inputs.items():
            envelope_inputs.append(EnvelopeInput(
                name=input_name, envelope=envelope,
                path=path if envelope is None else None,
                semantic_type=semantic_type if envelope is None else None
            ))

        try:
            resolved_params = self.reference_resolver.resolve_step_params(step)
        except ValueError as e:
            return StepResult(step_id=step.id, success=False, envelope=None, output_paths={}, error="Parameter resolution failed", message=str(e))

        if len(step.outputs) != 1:
            return StepResult(step_id=step.id, success=False, envelope=None, output_paths={}, error="Invalid step definition", message=f"Currently only single-output steps supported. Step '{step.id}' has {len(step.outputs)} outputs.")

        output_name, output_semantic_type = list(step.outputs.items())[0]
        output_format = self._infer_format(output_semantic_type)
        output_path = self.output_dir / f"{step.id}_{output_name}.{output_format}"

        build_result = self.envelope_builder.run(
            primitive=primitive_path, version=step.version,
            inputs=envelope_inputs, output_path=output_path,
            output_format=output_format, output_semantic_type=output_semantic_type,
            output_data_category=self._infer_category(output_semantic_type),
            params=resolved_params, passthrough=primitive_spec.passthrough
        )

        if not build_result.success:
            return StepResult(step_id=step.id, success=False, envelope=None, output_paths={}, error=build_result.error, message=build_result.message)

        self.reference_resolver.register_step_output(
            step_id=step.id, output_name=output_name,
            path=str(output_path), envelope=build_result.envelope
        )

        envelope_path = self.envelope_dir / f"{step.id}_{output_name}.envelope.json"

        # Sprint 8: wrap envelope-write so schema-validation failures fail
        # the step gracefully with a clear error rather than crashing the
        # orchestrator with a traceback. Import is lazy so this catch
        # remains specific even if envelope.py changes its exception hierarchy.
        try:
            write_envelope(build_result.envelope, envelope_path)
        except Exception as e:
            # We catch broadly here because EnvelopeValidationError is
            # defined in canopy.envelope and we don't want to add a top-
            # level import dependency; the exception class name is in the
            # message via the f-string below for diagnosis.
            error_class = type(e).__name__
            return StepResult(
                step_id=step.id,
                success=False,
                envelope=None,
                output_paths={},
                error="Envelope validation failed",
                message=(
                    f"Step '{step.id}' produced output that did not satisfy "
                    f"the envelope schema ({error_class}): {e}\n"
                    f"The primitive's metadata is missing or malformed for "
                    f"a field the schema requires. Inspect the primitive's "
                    f"primitive_success() call against the envelope schema "
                    f"in seeds/schemas/envelope.schema.json."
                ),
            )

        return StepResult(step_id=step.id, success=True, envelope=build_result.envelope, output_paths={output_name: str(output_path)})

    # ═══════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    def _infer_format(self, semantic_type: str) -> str:
        return self.semantic_types.get_format(semantic_type)

    def _infer_category(self, semantic_type: str) -> str:
        return self.semantic_types.get_category(semantic_type)

    def _collect_final_envelopes(self, step_results: dict[str, StepResult]) -> dict[str, Envelope]:
        envelopes = {}
        for step_id, result in step_results.items():
            if result.success and result.envelope:
                envelopes[step_id] = result.envelope
        return envelopes

    def _enrich_with_lineage(self, envelopes: dict[str, Envelope]) -> None:
        """Add scientific lineage and resolution context to final envelopes."""
        lineage_dict = {
            "curiosity": self.experiment.lineage.curiosity_ref,
            "sub_question": self.experiment.lineage.sub_question,
            "method": self.experiment.lineage.method_ref,
            "choices": self.experiment.lineage.choices,
            "parameters": self.experiment.parameters
        }

        if self._resolution_report:
            lineage_dict["data_resolution"] = self._resolution_report.to_envelope_context()

        for envelope in envelopes.values():
            envelope.metadata["lineage"] = lineage_dict

    def _write_run_log(self, result: OrchestrationResult) -> None:
        timestamp_str = self._run_started.strftime("%Y%m%d_%H%M%S")

        step_summaries = []
        for step_id in self.plan.steps_in_order:
            if step_id not in result.step_results:
                continue
            step_result = result.step_results[step_id]
            duration = None
            warning_count = 0
            if step_result.envelope:
                if step_result.envelope.provenance:
                    duration = step_result.envelope.provenance[-1].duration_seconds
                warning_count = len(step_result.envelope.warnings)
            step_summaries.append({
                "id": step_id, "success": step_result.success,
                "duration_seconds": duration, "warning_count": warning_count,
                "error": step_result.error
            })

        log = {
            "run_id": f"{self.experiment.id}_{timestamp_str}",
            "experiment": {"id": self.experiment.id, "name": self.experiment.name, "path": str(self.experiment_path)},
            "city": self.experiment.city,
            "profile": self.profile,
            "timing": {"started": self._run_started.isoformat(), "completed": datetime.now(timezone.utc).isoformat()},
            "result": {"success": result.success, "failed_step": result.failed_step, "error": result.error},
            "validation_warnings": result.warnings,
            "steps": step_summaries,
            "summary": {
                "total_steps": len(self.plan.steps_in_order),
                "completed_steps": len(result.completed_steps),
                "total_warnings": sum(s["warning_count"] for s in step_summaries)
            }
        }

        log_dir = self.project_root / "compost" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{log['run_id']}.yml"
        with open(log_path, 'w') as f:
            yaml.dump(log, f, default_flow_style=False, sort_keys=False)