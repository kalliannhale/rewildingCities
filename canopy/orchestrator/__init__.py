"""canopy/orchestrator

Experiment-based orchestration for the rewildingCities pipeline.

Example:
    from canopy.orchestrator import run_experiment, visualize_experiment

    result = run_experiment(
        "garden/experiments/nyc_park_cooling_pedestrian.yml",
        profile="dev"
    )

    from canopy.orchestrator import Orchestrator
    orch = Orchestrator(
        experiment_path="garden/experiments/nyc_park_cooling_pedestrian.yml",
        profile="full"
    )
    errors, warnings = orch.validate()
    if not errors:
        result = orch.run()
"""

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

from .parsing import (
    parse_manifest,
    parse_experiment,
    parse_method,
)

from .orchestrator import (
    Orchestrator,
    run_experiment,
    visualize_experiment,
    load_methods_index,
)

from .dependencies import (
    DependencyResolver,
    ExecutionPlan,
)

from .references import (
    ReferenceResolver,
)

from .registry import (
    load_registry,
    RegistryManager,
)

__all__ = [
    "Manifest",
    "ManifestDataset",
    "ManifestInconsistency",
    "Experiment",
    "Lineage",
    "StepDefinition",
    "PrimitiveSpec",
    "StepResult",
    "OrchestrationResult",
    "ExecutionPlan",
    "Method",
    "MethodChoice",
    "MethodIndexEntry",
    "parse_manifest",
    "parse_experiment",
    "parse_method",
    "load_registry",
    "Orchestrator",
    "DependencyResolver",
    "ReferenceResolver",
    "RegistryManager",
    "run_experiment",
    "visualize_experiment",
    "load_methods_index",
]