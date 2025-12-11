"""
canopy/orchestrator

Experiment-based orchestration for the rewildingCities pipeline.

Example:
    from canopy.orchestrator import run_experiment, visualize_experiment
    
    # Quick run
    result = run_experiment(
        "garden/experiments/nyc_park_cooling_pedestrian.yml",
        profile="dev"
    )
    
    # Or with more control
    from canopy.orchestrator import Orchestrator
    
    orch = Orchestrator(
        experiment_path="garden/experiments/nyc_park_cooling_pedestrian.yml",
        profile="full"
    )
    
    errors = orch.validate()
    if not errors:
        result = orch.run()
"""

from .orchestrator import (
    # Data structures
    Manifest,
    ManifestDataset,
    Experiment,
    Lineage,
    StepDefinition,
    PrimitiveSpec,
    StepResult,
    OrchestrationResult,
    
    # Parsing
    parse_manifest,
    parse_experiment,
    
    # Runner
    Orchestrator,
    run_experiment,
    visualize_experiment,
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
    # Data structures
    "Manifest",
    "ManifestDataset", 
    "Experiment",
    "Lineage",
    "StepDefinition",
    "PrimitiveSpec",
    "StepResult",
    "OrchestrationResult",
    "ExecutionPlan",
    
    # Parsing
    "parse_manifest",
    "parse_experiment",
    "load_registry",
    
    # Core classes
    "Orchestrator",
    "DependencyResolver",
    "ReferenceResolver",
    "RegistryManager",
    
    # Convenience functions
    "run_experiment",
    "visualize_experiment",
]