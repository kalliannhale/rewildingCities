"""
canopy/orchestrator/orchestrator.py

Experiment-based orchestrator for the rewildingCities pipeline.
"""

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
) -> "OrchestrationResult":
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


# === Data Structures ===

@dataclass
class ManifestDataset:
    """A dataset declared in a manifest."""
    name: str
    path: str
    semantic_type: str
    format: str


@dataclass
class Manifest:
    """A parsed city manifest."""
    city_name: str
    city_id: str
    datasets: dict[str, ManifestDataset]
    data_dir: Path


@dataclass
class StepDefinition:
    """A step in an experiment."""
    id: str
    primitive: str  # e.g., "soil/validate_boundaries" or "roots/generate_buffers"
    version: str
    description: str
    inputs: dict[str, str]   # input_name -> reference string
    outputs: dict[str, str]  # output_name -> semantic_type
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
    path: str  # relative path within layer
    version: str
    inputs: list[dict]
    outputs: dict
    params: dict
    passthrough: bool = False  # ← add this


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
    warnings: list[str] = field(default_factory=list)  # Orchestration-level warnings
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


# === Parsing ===

def parse_manifest(path: str | Path) -> Manifest:
    """Parse a city manifest YAML file."""
    path = Path(path)
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    datasets = {}
    for name, ds_data in data.get("datasets", {}).items():
        if ds_data.get("available", True):
            cache_path = ds_data.get("cache", {}).get("path", f".data/{name}.geojson")
            datasets[name] = ManifestDataset(
                name=name,
                path=cache_path,
                semantic_type=ds_data.get("semantic_type", name),
                format=ds_data.get("format", "geojson")
            )
    
    return Manifest(
        city_name=data["city"]["name"],
        city_id=data["city"]["id"],
        datasets=datasets,
        data_dir=path.parent
    )


def parse_experiment(path: str | Path) -> Experiment:
    """Parse an experiment YAML file."""
    path = Path(path)
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    # Parse lineage from curiosity/method refs
    curiosity_data = data.get("curiosity", {})
    method_data = data.get("method", {})
    
    lineage = Lineage(
        curiosity_ref=curiosity_data.get("ref", ""),
        sub_question=curiosity_data.get("sub_question"),
        method_ref=method_data.get("ref", ""),
        choices=data.get("choices", {})
    )
    
    # Parse steps
    steps = []
    for step_data in data.get("steps", []):
        steps.append(StepDefinition(
            id=step_data["id"],
            primitive=step_data["primitive"],
            version=step_data.get("version", "1.0.0"),
            description=step_data.get("description", ""),
            inputs=step_data.get("inputs", {}),
            outputs=step_data.get("outputs", {}),
            params=step_data.get("params", {})
        ))
    
    return Experiment(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        lineage=lineage,
        city=data["city"],
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


# === Orchestrator ===

class Orchestrator:
    """
    Executes experiments against city manifests.
    
    Example:
        orchestrator = Orchestrator(
            experiment_path="garden/experiments/nyc_park_cooling_pedestrian.yml",
            profile="dev"
        )
        
        result = orchestrator.run()
        
        if result.success:
            print(f"Completed {len(result.completed_steps)} steps")
            for step_id, envelope in result.final_envelopes.items():
                print(f"  {step_id}: {envelope.data['path']}")
        else:
            print(f"Failed at step: {result.failed_step}")
            print(f"Error: {result.error}")
    """
    
    def __init__(
        self,
        experiment_path: str | Path,
        profile: str = "full",
        project_root: str | Path | None = None,
        output_dir: str | Path | None = None
    ):
        """
        Initialize the orchestrator.
        
        Args:
            experiment_path: Path to experiment YAML file
            profile: Execution profile ("full", "dev", "test")
            project_root: Project root directory (defaults to cwd)
            output_dir: Override output directory (defaults to plot's .data/)
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.experiment_path = Path(experiment_path)
        self.profile = profile
        
        # Parse experiment
        self.experiment = parse_experiment(experiment_path)
        
        # Parse manifest (path is relative to project root)
        manifest_path = self.project_root / self.experiment.manifest_path
        self.manifest = parse_manifest(manifest_path)
        
        # Set up output directories
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
        dependency_resolver = DependencyResolver(self.experiment)
        self.plan = dependency_resolver.create_execution_plan()
        
        # Reference resolver (populated as steps complete)
        self.reference_resolver = ReferenceResolver(
            manifest=self.manifest,
            experiment=self.experiment
        )
        
        # Envelope builder
        self.envelope_builder = EnvelopeBuilder(
            profile=profile,
            project_root=self.project_root
            )
        
        # Track timing
        self._run_started: datetime | None = None
    
    def validate(self) -> tuple[list[str], list[str]]:
        """
        Validate the experiment before running.
        
        Returns:
            Tuple of (errors, warnings). Errors are fatal; warnings are informational.
        """
        errors = []
        warnings = []
        
        # Validate all primitives exist
        primitive_errors = self.registry.validate_all_primitives(self.experiment)
        errors.extend(primitive_errors)
        
        # Validate manifest has required datasets
        for step in self.experiment.steps:
            for input_name, ref in step.inputs.items():
                if ref.startswith("$manifest."):
                    dataset_name = ref.replace("$manifest.", "")
                    if dataset_name not in self.manifest.datasets:
                        errors.append(
                            f"Step '{step.id}' references $manifest.{dataset_name}, "
                            f"but manifest has no dataset '{dataset_name}'"
                        )
        
        # Validate choices exist for all $choices references
        for step in self.experiment.steps:
            self._validate_param_references(step, errors)
        
        # Validate choices against method (warnings, not errors)
        self._validate_method_choices(warnings)
        
        return errors, warnings
    
    def _validate_param_references(
        self, 
        step: StepDefinition, 
        errors: list[str]
    ) -> None:
        """Check that all $choices and $parameters references are valid."""
        
        def check_value(value: Any, path: str) -> None:
            if isinstance(value, str):
                if value.startswith("$choices."):
                    choice_name = value.replace("$choices.", "")
                    if choice_name not in self.experiment.choices:
                        errors.append(
                            f"Step '{step.id}' param {path} references "
                            f"$choices.{choice_name}, but no such choice exists"
                        )
                elif value.startswith("$parameters."):
                    param_name = value.replace("$parameters.", "")
                    if param_name not in self.experiment.parameters:
                        errors.append(
                            f"Step '{step.id}' param {path} references "
                            f"$parameters.{param_name}, but no such parameter exists"
                        )
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    check_value(item, f"{path}[{i}]")
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_value(v, f"{path}.{k}")
        
        for param_name, param_value in step.params.items():
            check_value(param_value, param_name)
    
    def _validate_method_choices(self, warnings: list[str]) -> None:
        """Check experiment choices against method's declared options."""
        method_ref = self.experiment.lineage.method_ref
        
        if not method_ref:
            return
        
        # Resolve method path from reference
        # Reference format: $methods/thermal/buffer_gradient_analysis
        method_path = self._resolve_method_path(method_ref)
        
        if not method_path.exists():
            warnings.append(
                f"Method file not found: {method_path}. "
                f"Choice validation skipped."
            )
            return
        
        try:
            method = parse_method(method_path)
        except Exception as e:
            warnings.append(
                f"Could not parse method file {method_path}: {e}. "
                f"Choice validation skipped."
            )
            return
        
        # Check each experiment choice against method options
        for choice_name, choice_value in self.experiment.choices.items():
            if choice_name not in method.choices:
                warnings.append(
                    f"Choice '{choice_name}' not declared in method '{method.name}'. "
                    f"This may be intentional experimentation."
                )
            elif choice_value not in method.choices[choice_name].options:
                warnings.append(
                    f"Choice '{choice_name}: {choice_value}' not in method options "
                    f"{method.choices[choice_name].options}. "
                    f"Proceeding anyway."
                )
        
        # Check for required method choices not provided
        for choice_name in method.choices:
            if choice_name not in self.experiment.choices:
                warnings.append(
                    f"Method '{method.name}' declares choice '{choice_name}', "
                    f"but experiment does not provide it. Default may be used."
                )
    
    def _resolve_method_path(self, method_ref: str) -> Path:
        """Resolve a method reference to a file path."""
        # Strip $methods/ prefix if present
        if method_ref.startswith("$methods/"):
            method_ref = method_ref[9:]
        
        # Add .yml extension if not present
        if not method_ref.endswith(".yml"):
            method_ref = f"{method_ref}.yml"
        
        return self.project_root / "garden" / "methods" / method_ref
    
    def run(self) -> OrchestrationResult:
        """
        Execute the experiment.
        
        Returns:
            OrchestrationResult with success status, completed steps, 
            and final envelopes (or error information if failed)
        """
        self._run_started = datetime.now(timezone.utc)
        
        # Validate first
        validation_errors, validation_warnings = self.validate()
        
        if validation_errors:
            result = OrchestrationResult(
                success=False,
                completed_steps=[],
                failed_step=None,
                step_results={},
                final_envelopes={},
                lineage=self.experiment.lineage,
                warnings=validation_warnings,
                error="Validation failed:\n" + "\n".join(f"  - {e}" for e in validation_errors)
            )
            self._write_run_log(result)
            return result
        
        # Ensure output directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.envelope_dir.mkdir(parents=True, exist_ok=True)
        
        # Execute steps in order
        step_results: dict[str, StepResult] = {}
        completed_steps: list[str] = []
        
        for step_id in self.plan.steps_in_order:
            step = self._get_step(step_id)
            
            step_result = self._execute_step(step)
            step_results[step_id] = step_result
            
            if not step_result.success:
                result = OrchestrationResult(
                    success=False,
                    completed_steps=completed_steps,
                    failed_step=step_id,
                    step_results=step_results,
                    final_envelopes=self._collect_final_envelopes(step_results),
                    lineage=self.experiment.lineage,
                    warnings=validation_warnings,
                    error=step_result.error
                )
                self._write_run_log(result)
                return result
            
            completed_steps.append(step_id)
        
        # Success — enrich final envelopes with lineage
        final_envelopes = self._collect_final_envelopes(step_results)
        self._enrich_with_lineage(final_envelopes)
        
        result = OrchestrationResult(
            success=True,
            completed_steps=completed_steps,
            failed_step=None,
            step_results=step_results,
            final_envelopes=final_envelopes,
            lineage=self.experiment.lineage,
            warnings=validation_warnings,
            error=None
        )
        self._write_run_log(result)
        return result
    
    def _get_step(self, step_id: str) -> StepDefinition:
        """Get step definition by ID."""
        for step in self.experiment.steps:
            if step.id == step_id:
                return step
        raise ValueError(f"Unknown step: {step_id}")
    
    def _execute_step(self, step: StepDefinition) -> StepResult:
        """Execute a single step."""
        
        # Resolve primitive path
        try:
            primitive_path, primitive_spec = self.registry.resolve_primitive(step.primitive)
        except (ValueError, FileNotFoundError) as e:
            return StepResult(
                step_id=step.id,
                success=False,
                envelope=None,
                output_paths={},
                error="Primitive resolution failed",
                message=str(e)
            )
        
        # Resolve inputs
        try:
            resolved_inputs = self.reference_resolver.resolve_step_inputs(step)
        except (ValueError, FileNotFoundError) as e:
            return StepResult(
                step_id=step.id,
                success=False,
                envelope=None,
                output_paths={},
                error="Input resolution failed",
                message=str(e)
            )
        
        # Build EnvelopeInputs
        envelope_inputs = []
        for input_name, (path, semantic_type, envelope) in resolved_inputs.items():
            envelope_inputs.append(EnvelopeInput(
                name=input_name,
                envelope=envelope,
                path=path if envelope is None else None,
                semantic_type=semantic_type if envelope is None else None
            ))
        
        # Resolve params
        try:
            resolved_params = self.reference_resolver.resolve_step_params(step)
        except ValueError as e:
            return StepResult(
                step_id=step.id,
                success=False,
                envelope=None,
                output_paths={},
                error="Parameter resolution failed",
                message=str(e)
            )
        
        # Determine output path and format
        if len(step.outputs) != 1:
            return StepResult(
                step_id=step.id,
                success=False,
                envelope=None,
                output_paths={},
                error="Invalid step definition",
                message=f"Currently only single-output steps supported. "
                        f"Step '{step.id}' has {len(step.outputs)} outputs."
            )
        
        output_name, output_semantic_type = list(step.outputs.items())[0]
        output_format = self._infer_format(output_semantic_type)
        output_path = self.output_dir / f"{step.id}_{output_name}.{output_format}"
        
        # Run the primitive via EnvelopeBuilder
        build_result = self.envelope_builder.run(
            primitive=primitive_path,
            version=step.version,
            inputs=envelope_inputs,
            output_path=output_path,
            output_format=output_format,
            output_semantic_type=output_semantic_type,
            output_data_category=self._infer_category(output_semantic_type),
            params=resolved_params,
            passthrough=primitive_spec.passthrough  # ← add this
        )
        
        if not build_result.success:
            return StepResult(
                step_id=step.id,
                success=False,
                envelope=None,
                output_paths={},
                error=build_result.error,
                message=build_result.message
            )
        
        # Register output for future steps
        self.reference_resolver.register_step_output(
            step_id=step.id,
            output_name=output_name,
            path=str(output_path),
            envelope=build_result.envelope
        )
        
        # Write envelope
        envelope_path = self.envelope_dir / f"{step.id}_{output_name}.envelope.json"
        write_envelope(build_result.envelope, envelope_path)
        
        return StepResult(
            step_id=step.id,
            success=True,
            envelope=build_result.envelope,
            output_paths={output_name: str(output_path)}
        )
    
    def _infer_format(self, semantic_type: str) -> str:
        """Get output format from semantic type registry."""
        return self.semantic_types.get_format(semantic_type)
    
    def _infer_category(self, semantic_type: str) -> str:
        """Get data category from semantic type registry."""
        return self.semantic_types.get_category(semantic_type)
    
    def _collect_final_envelopes(
        self,
        step_results: dict[str, StepResult]
    ) -> dict[str, Envelope]:
        """Collect all successfully produced envelopes."""
        envelopes = {}
        for step_id, result in step_results.items():
            if result.success and result.envelope:
                envelopes[step_id] = result.envelope
        return envelopes
    
    def _enrich_with_lineage(self, envelopes: dict[str, Envelope]) -> None:
        """Add scientific lineage to final envelopes' metadata."""
        lineage_dict = {
            "curiosity": self.experiment.lineage.curiosity_ref,
            "sub_question": self.experiment.lineage.sub_question,
            "method": self.experiment.lineage.method_ref,
            "choices": self.experiment.lineage.choices,
            "parameters": self.experiment.parameters
        }
        
        for envelope in envelopes.values():
            envelope.metadata["lineage"] = lineage_dict
    
    def _write_run_log(self, result: OrchestrationResult) -> None:
        """Write run log to compost/logs/."""
        timestamp_str = self._run_started.strftime("%Y%m%d_%H%M%S")
        
        # Build step summaries
        step_summaries = []
        for step_id in self.plan.steps_in_order:
            if step_id not in result.step_results:
                continue
            
            step_result = result.step_results[step_id]
            
            # Extract duration from envelope provenance if available
            duration = None
            warning_count = 0
            if step_result.envelope:
                if step_result.envelope.provenance:
                    duration = step_result.envelope.provenance[-1].duration_seconds
                warning_count = len(step_result.envelope.warnings)
            
            step_summaries.append({
                "id": step_id,
                "success": step_result.success,
                "duration_seconds": duration,
                "warning_count": warning_count,
                "error": step_result.error
            })
        
        log = {
            "run_id": f"{self.experiment.id}_{timestamp_str}",
            "experiment": {
                "id": self.experiment.id,
                "name": self.experiment.name,
                "path": str(self.experiment_path)
            },
            "city": self.experiment.city,
            "profile": self.profile,
            "timing": {
                "started": self._run_started.isoformat(),
                "completed": datetime.now(timezone.utc).isoformat()
            },
            "result": {
                "success": result.success,
                "failed_step": result.failed_step,
                "error": result.error
            },
            "validation_warnings": result.warnings,
            "steps": step_summaries,
            "summary": {
                "total_steps": len(self.plan.steps_in_order),
                "completed_steps": len(result.completed_steps),
                "total_warnings": sum(s["warning_count"] for s in step_summaries)
            }
        }
        
        # Write to compost/logs/
        log_dir = self.project_root / "compost" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{log['run_id']}.yml"
        
        with open(log_path, 'w') as f:
            yaml.dump(log, f, default_flow_style=False, sort_keys=False)