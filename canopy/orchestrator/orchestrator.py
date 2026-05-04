"""
canopy/orchestrator/orchestrator.py

Experiment-based orchestrator for the rewildingCities pipeline.
"""

from __future__ import annotations

import yaml
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any
from collections import defaultdict
from datetime import datetime, timezone

from .references import ReferenceResolver
from .dependencies import DependencyResolver, ExecutionPlan
from .registry import RegistryManager
from .semantic_types import SemanticTypeRegistry

from ..envelope import (
    EnvelopeBuilder,
    EnvelopeInput,
    Envelope,
    BuildResult,
    read_envelope,
    write_envelope
)


# === Convenience Functions ===

def run_experiment(
    experiment_path: str | Path,
    profile: str = "full",
    project_root: str | Path | None = None
) -> OrchestrationResult:
    """
    Convenience function to run an experiment.
    
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
    """
    Generate ASCII visualization of an experiment's execution plan.
    
    Example:
        print(visualize_experiment("garden/experiments/nyc_park_cooling_pedestrian.yml"))
    """
    experiment = parse_experiment(experiment_path)
    resolver = DependencyResolver(experiment)
    return resolver.visualize()


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ManifestDataset:
    """A dataset declared in a manifest."""
    name: str
    path: str
    semantic_type: str
    format: str
    available: bool = False
    source: dict | None = None
    cache: dict | None = None
    description: str = ""
    temporal: dict | None = None
    quality: dict | None = None
    provenance: dict | None = None

    @property
    def source_type(self) -> str | None:
        if self.source is None:
            return None
        return self.source.get("type")
    
    @property
    def provider_name(self) -> str | None:
        if self.source is None:
            return None
        return self.source.get("provider")
    
    @property
    def is_auto_acquirable(self) -> bool:
        if self.source is None:
            return False
        return self.source_type in ("api", "url", "local", "stac", "s3")
    
    @property
    def requires_auth(self) -> bool:
        if self.source is None:
            return False
        auth = self.source.get("auth", {})
        return auth.get("type", "none") != "none" or self.source_type == "earthengine"
    
    @property 
    def requires_manual_action(self) -> bool:
        return self.source_type in ("manual",)


@dataclass
class ManifestInconsistency:
    """A detected inconsistency in the manifest's state."""
    dataset_name: str
    issue: str
    path: str
    suggestion: str


@dataclass
class Manifest:
    """A parsed city manifest."""
    city_name: str
    city_id: str
    datasets: dict[str, ManifestDataset]
    data_dir: Path
    manifest_path: Path | None = None
    crs_working: str = ""
    gee_project: str | None = None
    raw: dict = field(default_factory=dict)

    def available_datasets(self) -> dict[str, ManifestDataset]:
        return {k: v for k, v in self.datasets.items() if v.available}
    
    def unavailable_datasets(self) -> dict[str, ManifestDataset]:
        return {k: v for k, v in self.datasets.items() if not v.available}
    
    def acquirable_datasets(self) -> dict[str, ManifestDataset]:
        return {k: v for k, v in self.datasets.items() 
                if not v.available and v.is_auto_acquirable}
    
    def datasets_by_semantic_type(self, semantic_type: str) -> list[ManifestDataset]:
        return [ds for ds in self.datasets.values() 
                if ds.semantic_type == semantic_type]
    
    def check_consistency(self) -> list[ManifestInconsistency]:
        issues = []
        for name, ds in self.datasets.items():
            full_path = self.data_dir / ds.path
            if ds.available and not full_path.exists():
                issues.append(ManifestInconsistency(
                    dataset_name=name, issue="available_but_missing",
                    path=str(full_path),
                    suggestion=f"File not found at {ds.path}. Either acquire the data or set available: false."
                ))
            if not ds.available and full_path.exists():
                issues.append(ManifestInconsistency(
                    dataset_name=name, issue="file_exists_but_unavailable",
                    path=str(full_path),
                    suggestion=f"File exists at {ds.path} but manifest says unavailable. Set available: true if ready."
                ))
        return issues


@dataclass
class StepDefinition:
    """A step in an experiment."""
    id: str
    primitive: str
    version: str
    description: str
    inputs: dict[str, str]
    outputs: dict[str, str]
    params: dict[str, Any]


@dataclass
class Lineage:
    """Scientific lineage — where this experiment comes from."""
    curiosity_ref: str
    sub_question: str | None
    method_ref: str
    choices: dict[str, Any]


@dataclass
class Experiment:
    """A parsed experiment."""
    id: str
    name: str
    description: str
    lineage: Lineage
    city: str
    manifest_path: str
    choices: dict[str, Any]
    parameters: dict[str, Any]
    steps: list[StepDefinition]


@dataclass
class PrimitiveSpec:
    """A primitive's specification from a registry."""
    name: str
    path: str
    version: str
    inputs: list[dict]
    outputs: dict
    params: dict
    passthrough: bool = False


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_id: str
    success: bool
    envelope: Envelope | None
    output_paths: dict[str, str]
    error: str | None = None
    message: str | None = None


@dataclass
class OrchestrationResult:
    """Result of executing a full experiment."""
    success: bool
    completed_steps: list[str]
    failed_step: str | None
    step_results: dict[str, StepResult]
    final_envelopes: dict[str, Envelope]
    lineage: Lineage | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class MethodChoice:
    """A choice declared in a method file."""
    name: str
    options: list[Any]
    description: str = ""


@dataclass
class Method:
    """A parsed method file."""
    id: str
    name: str
    choices: dict[str, MethodChoice]


# ═══════════════════════════════════════════════════════════════════════════════
# PARSING
# ═══════════════════════════════════════════════════════════════════════════════

def parse_manifest(path: str | Path) -> Manifest:
    """Parse a city manifest YAML file. Loads ALL datasets."""
    path = Path(path)
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    datasets = {}
    for name, ds_data in data.get("datasets", {}).items():
        cache_config = ds_data.get("cache", {})
        cache_path = cache_config.get("path", f".data/{name}.geojson")
        datasets[name] = ManifestDataset(
            name=name, path=cache_path,
            semantic_type=ds_data.get("semantic_type", name),
            format=ds_data.get("format", "geojson"),
            available=ds_data.get("available", False),
            source=ds_data.get("source"),
            cache=cache_config if cache_config else None,
            description=ds_data.get("description", ""),
            temporal=ds_data.get("temporal"),
            quality=ds_data.get("quality"),
            provenance=ds_data.get("provenance"),
        )
    
    crs_data = data.get("crs", {})
    gee_data = data.get("gee", {})
    return Manifest(
        city_name=data["city"]["name"], city_id=data["city"]["id"],
        datasets=datasets, data_dir=path.parent, manifest_path=path,
        crs_working=crs_data.get("working", ""),
        gee_project=gee_data.get("project"), raw=data,
    )


def parse_experiment(path: str | Path) -> Experiment:
    """Parse an experiment YAML file."""
    path = Path(path)
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    curiosity_data = data.get("curiosity", {})
    method_data = data.get("method", {})
    lineage = Lineage(
        curiosity_ref=curiosity_data.get("ref", ""),
        sub_question=curiosity_data.get("sub_question"),
        method_ref=method_data.get("ref", ""),
        choices=data.get("choices", {})
    )
    
    steps = []
    for step_data in data.get("steps", []):
        steps.append(StepDefinition(
            id=step_data["id"], primitive=step_data["primitive"],
            version=step_data.get("version", "1.0.0"),
            description=step_data.get("description", ""),
            inputs=step_data.get("inputs", {}),
            outputs=step_data.get("outputs", {}),
            params=step_data.get("params", {})
        ))
    
    return Experiment(
        id=data["id"], name=data["name"],
        description=data.get("description", ""),
        lineage=lineage, city=data["city"],
        manifest_path=data["manifest"],
        choices=data.get("choices", {}),
        parameters=data.get("parameters", {}),
        steps=steps
    )


def parse_method(path: str | Path) -> Method:
    """Parse a method YAML file."""
    path = Path(path)
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    choices = {}
    for name, choice_data in data.get("choices", {}).items():
        choices[name] = MethodChoice(
            name=name,
            options=choice_data.get("options", []),
            description=choice_data.get("description", "")
        )
    
    return Method(
        id=data.get("id", path.stem),
        name=data.get("name", path.stem),
        choices=choices
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class Orchestrator:
    """
    Executes experiments against city manifests.
    
    Three-phase execution: validate → resolve data → execute steps.
    """
    
    def __init__(
        self,
        experiment_path: str | Path,
        profile: str = "full",
        project_root: str | Path | None = None,
        output_dir: str | Path | None = None
    ):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.experiment_path = Path(experiment_path)
        self.profile = profile
        
        # Parse experiment
        self.experiment = parse_experiment(experiment_path)
        
        # Parse manifest
        manifest_path = self.experiment_path.parent / self.experiment.manifest_path
        self.manifest = parse_manifest(manifest_path)
        
        # Output directories
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.manifest.data_dir / ".data"
        self.envelope_dir = self.manifest.data_dir / ".envelopes"
        
        # Initialize managers
        self.registry = RegistryManager(project_root=self.project_root)
        self.semantic_types = SemanticTypeRegistry(
            path=self.project_root / "seeds/schemas/semantic_types.yml"
        )
        
        # Build execution plan
        self._dependency_resolver = DependencyResolver(self.experiment)
        self.plan = self._dependency_resolver.create_execution_plan()
        
        # Reference resolver
        self.reference_resolver = ReferenceResolver(
            manifest=self.manifest,
            experiment=self.experiment
        )
        
        # Envelope builder
        self.envelope_builder = EnvelopeBuilder(
            profile=profile,
            project_root=self.project_root
        )
        
        # Provider registry
        from canopy.providers import create_default_registry
        self.provider_registry = create_default_registry()
        
        # Track timing and resolution
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
            elif choice_value not in method.choices[choice_name].options:
                warnings.append(f"Choice '{choice_name}: {choice_value}' not in method options {method.choices[choice_name].options}.")
        
        for choice_name in method.choices:
            if choice_name not in self.experiment.choices:
                warnings.append(f"Method '{method.name}' declares choice '{choice_name}', but experiment does not provide it.")
    
    def _resolve_method_path(self, method_ref: str) -> Path:
        if method_ref.startswith("$methods/"):
            method_ref = method_ref[9:]
        if not method_ref.endswith(".yml"):
            method_ref = f"{method_ref}.yml"
        return self.project_root / "garden" / "methods" / method_ref
    
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
    # PHASE 2: DATA RESOLUTION
    # ═══════════════════════════════════════════════════════════════════════
    
    def resolve_data(self):
        """Check data availability, acquire missing, produce advisory report.
        
        Delegates to the Resolution Engine, which composes answers from
        the manifest, DAG, method, and provider registry.
        
        Returns:
            ResolutionReport
        """
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
        
        # Commit manifest transaction if there were successful acquisitions
        if report.transaction and report.transaction.has_changes:
            tx_result = report.transaction.commit()
            if not tx_result.success:
                report.summary += f" (Warning: manifest update had failures: {tx_result.changes_failed})"
        
        return report
    
    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3: EXECUTION
    # ═══════════════════════════════════════════════════════════════════════
    
    def run(self) -> OrchestrationResult:
        """Execute the experiment in three phases: validate → resolve → execute."""
        self._run_started = datetime.now(timezone.utc)
        
        # ── Phase 1: Validate ──
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
        
        # ── Phase 2: Resolve data ──
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
        
        # Log acquisitions
        for r in data_report.acquired:
            validation_warnings.append(f"Acquired '{r.dataset_name}': {r.message}")
        
        # ── Phase 3: Execute steps ──
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
        
        # Success
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
        write_envelope(build_result.envelope, envelope_path)
        
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
        
        # Add resolution context if available
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