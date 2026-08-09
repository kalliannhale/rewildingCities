#!/usr/bin/env python3
"""Targeted test for Orchestrator._find_injection_points.

Verifies the function against two cases:
  1. The live park cooling experiment → must return ["filter_parks"].
  2. A constructed raster-only experiment → must return [].

Run from project root:
    python tests/test_injection_points.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def find_park_cooling_experiment():
    direct = project_root / "plots" / "nyc" / "experiments" / "nyc_park_cooling_pedestrian.yml"
    if direct.exists():
        return direct
    for p in project_root.rglob("nyc_park_cooling_pedestrian.yml"):
        return p
    return None


def test_park_cooling_injection_point():
    """The live park cooling experiment fans out from filter_parks.
    
    crop_lst, generate_buffers, and park_baseline_temperature all
    consume $steps.filter_parks.filtered — so filter_parks is where
    a sampling step should be injected.
    """
    from canopy.orchestrator.orchestrator import Orchestrator
    
    exp_path = find_park_cooling_experiment()
    if exp_path is None:
        print("  SKIP — park cooling experiment not found on disk")
        return
    
    orch = Orchestrator(experiment_path=str(exp_path), profile="dev")
    points = orch._find_injection_points()
    
    print(f"  Injection points found: {points}")
    
    assert points == ["filter_parks"], (
        f"FAIL: expected ['filter_parks'], got {points}. "
        f"Park cooling experiment fans out from filter_parks into "
        f"crop_lst, generate_buffers, and park_baseline_temperature."
    )
    print("  ✓ filter_parks correctly identified as the injection point")


def test_raster_only_no_injection():
    """A raster-only experiment has no vector chains, so no injection.
    
    Construct an in-memory experiment whose only $manifest reference is
    a raster (LST). The injection point list should be empty.
    """
    from canopy.orchestrator.orchestrator import (
        Experiment, Lineage, StepDefinition, Manifest, ManifestDataset,
    )
    from canopy.orchestrator.dependencies import DependencyResolver
    from canopy.orchestrator.references import ReferenceResolver
    from canopy.orchestrator.registry import RegistryManager
    from canopy.orchestrator.semantic_types import SemanticTypeRegistry
    
    # Minimal raster-only experiment: one step consuming LST, producing
    # a classified raster.
    exp = Experiment(
        id="raster_only_test",
        name="Raster-only test",
        description="",
        lineage=Lineage(curiosity_ref="", sub_question=None, method_ref="", choices={}),
        city="test",
        manifest_path="manifest.yml",
        choices={},
        parameters={},
        steps=[
            StepDefinition(
                id="validate_lst",
                primitive="soil/validate_raster",
                version="1.0.0",
                description="",
                inputs={"raster": "$manifest.land_surface_temperature"},
                outputs={"checked": "land_surface_temperature"},
                params={},
            ),
            StepDefinition(
                id="classify",
                primitive="roots/classify_clusters",
                version="1.0.0",
                description="",
                inputs={"raster": "$steps.validate_lst.checked"},
                outputs={"classified": "thermal_hotspot_classification"},
                params={},
            ),
        ],
    )


    
    # Minimal manifest with one raster dataset.
    manifest = Manifest(
        city_name="Test City",
        city_id="test",
        datasets={
            "land_surface_temperature": ManifestDataset(
                name="land_surface_temperature",
                path=".data/lst.tif",
                semantic_type="land_surface_temperature",
                format="tiff",
                available=False,
                source=None,
            ),
        },
        data_dir=Path("/tmp/test"),
    )
    
    # Build a minimal orchestrator-like object that has just the
    # attributes _find_injection_points reads.
    class FakeOrch:
        pass
    
    fake = FakeOrch()
    fake.experiment = exp
    fake.manifest = manifest
    fake.semantic_types = SemanticTypeRegistry(
        path=project_root / "seeds/schemas/semantic_types.yml"
    )
    
    # Call the actual method, bound to fake.
    from canopy.orchestrator.orchestrator import Orchestrator
    result = Orchestrator._find_injection_points(fake)
    
    print(f"  Raster-only injection points: {result}")
    assert result == [], f"FAIL: expected [], got {result}"
    print("  ✓ No injection for raster-only experiment")


def test_park_cooling_injection_point():
    """The live park cooling experiment fans out from filter_parks.
    
    crop_lst, generate_buffers, and park_baseline_temperature all
    consume $steps.filter_parks.filtered — so filter_parks is where
    a sampling step should be injected. We verify by checking the
    injection_log after dev-profile initialization.
    """
    from canopy.orchestrator.orchestrator import Orchestrator
    
    exp_path = find_park_cooling_experiment()
    if exp_path is None:
        print("  SKIP — park cooling experiment not found on disk")
        return
    
    orch = Orchestrator(experiment_path=str(exp_path), profile="dev")
    
    print(f"  Injection log: {orch.injection_log}")
    
    assert len(orch.injection_log) == 1, (
        f"FAIL: expected exactly 1 injection, got {len(orch.injection_log)}"
    )
    
    entry = orch.injection_log[0]
    assert entry["after"] == "filter_parks", (
        f"FAIL: expected injection after 'filter_parks', got '{entry['after']}'"
    )
    assert entry["step_id"] == "sample_after_filter_parks", (
        f"FAIL: expected step_id 'sample_after_filter_parks', got '{entry['step_id']}'"
    )
    assert entry["method"] == "stratified", (
        f"FAIL: expected dev-profile method 'stratified', got '{entry['method']}'"
    )
    assert entry["rewired_count"] == 3, (
        f"FAIL: expected 3 rewired references (crop_lst.boundary, "
        f"generate_buffers.features, park_baseline_temperature.zones), "
        f"got {entry['rewired_count']}"
    )
    print("  ✓ Injection correctly placed after filter_parks")
    print(f"  ✓ Rewired {entry['rewired_count']} downstream references")


if __name__ == "__main__":
    print("\n=== _find_injection_points Targeted Test ===\n")
    
    for name, fn in [
        ("Park cooling experiment → filter_parks", test_park_cooling_injection_point),
        ("Raster-only experiment → no injection", test_raster_only_no_injection),
    ]:
        print(name)
        try:
            fn()
            print("  PASSED\n")
        except Exception as e:
            print(f"  FAILED: {e}\n")
            import traceback
            traceback.print_exc()
            print()
    
    print("=== Done ===")


