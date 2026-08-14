#!/usr/bin/env python3
"""
Sprint 4 Verification — run from project root:
    python tests/test_sprint4.py

Tests DAG impact tracing and the Resolution Engine.
Assertions are structural, not hardcoded to specific step counts —
they verify trace_impact against an independent manual calculation.
"""

import sys
import re
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def find_experiment_path():
    """Find the park cooling experiment YAML."""
    direct = project_root / "plots" / "nyc" / "experiments" / "nyc_park_cooling_pedestrian.yml"
    if direct.exists():
        return direct
    for p in project_root.rglob("nyc_park_cooling_pedestrian.yml"):
        return p
    return None


def steps_that_transitively_need(experiment, dataset_name: str) -> set[str]:
    """Independently compute which steps transitively depend on a dataset.
    
    This is the ground-truth we verify trace_impact against.
    Built from scratch — doesn't use trace_impact at all.
    """
    steps_pattern = re.compile(r'\$steps\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)')
    
    # Steps directly referencing $manifest.{dataset_name}
    direct = set()
    for step in experiment.steps:
        for input_name, ref in step.inputs.items():
            if ref == f"$manifest.{dataset_name}":
                direct.add(step.id)
    
    # Step-to-step dependencies
    step_deps: dict[str, set[str]] = {}
    for step in experiment.steps:
        deps = set()
        for input_name, ref in step.inputs.items():
            match = steps_pattern.match(ref)
            if match:
                deps.add(match.group(1))
        step_deps[step.id] = deps
    
    # Walk forward
    all_needed = set(direct)
    changed = True
    while changed:
        changed = False
        for step_id, deps in step_deps.items():
            if step_id not in all_needed and deps & all_needed:
                all_needed.add(step_id)
                changed = True
    
    return all_needed


def test_trace_impact():
    """Test trace_impact against independent manual calculation."""
    from canopy.orchestrator.orchestrator import parse_experiment
    from canopy.orchestrator.dependencies import DependencyResolver

    exp_path = find_experiment_path()
    if not exp_path:
        print("  SKIP — experiment file not found")
        return

    exp = parse_experiment(exp_path)
    resolver = DependencyResolver(exp)
    all_step_ids = {s.id for s in exp.steps}

    # Collect manifest refs
    refs = resolver.collect_manifest_refs()
    print(f"  Manifest references found:")
    for dataset, steps in refs.items():
        print(f"    $manifest.{dataset} → {steps}")
    assert "park_boundaries" in refs, "FAIL: should find park_boundaries ref"
    assert "land_surface_temperature" in refs, "FAIL: should find LST ref"
    print("  ✓ Manifest references collected correctly")

    # === Test each dataset independently ===
    for dataset_name in refs.keys():
        impact = resolver.trace_impact({dataset_name})
        traced = set(impact.get(dataset_name, []))
        expected = steps_that_transitively_need(exp, dataset_name)
        
        assert traced == expected, (
            f"FAIL: trace_impact for '{dataset_name}' doesn't match.\n"
            f"  Extra in trace: {traced - expected}\n"
            f"  Missing from trace: {expected - traced}"
        )
        print(f"  ✓ {dataset_name}: {len(traced)} orphaned, matches manual calculation")
    
    # === Verify runnable + orphaned = all steps (no gaps, no overlaps) ===
    for dataset_name in refs.keys():
        impact = resolver.trace_impact({dataset_name})
        orphaned = set(impact.get(dataset_name, []))
        runnable = set(resolver.runnable_steps({dataset_name}))
        
        assert runnable | orphaned == all_step_ids, (
            f"FAIL: gap for '{dataset_name}': "
            f"missing {all_step_ids - (runnable | orphaned)}"
        )
        assert runnable & orphaned == set(), (
            f"FAIL: overlap for '{dataset_name}': {runnable & orphaned}"
        )
    print("  ✓ For each dataset: runnable ∪ orphaned = all steps (no gaps, no overlaps)")

    # === Verify survivors are genuinely independent ===
    for dataset_name in refs.keys():
        impact = resolver.trace_impact({dataset_name})
        orphaned = set(impact.get(dataset_name, []))
        survivors = all_step_ids - orphaned
        
        for survivor in survivors:
            step = resolver.steps_by_id[survivor]
            for input_name, ref in step.inputs.items():
                assert ref != f"$manifest.{dataset_name}", (
                    f"FAIL: {survivor} directly references $manifest.{dataset_name} "
                    f"but wasn't orphaned"
                )
    print("  ✓ All survivors are genuinely independent of their missing dataset")

    # === Both missing → all orphaned ===
    all_datasets = set(refs.keys())
    impact_all = resolver.trace_impact(all_datasets)
    all_orphaned = set()
    for steps in impact_all.values():
        all_orphaned.update(steps)
    
    assert all_orphaned == all_step_ids, (
        f"FAIL: missing ALL manifest datasets should orphan ALL steps.\n"
        f"  Survivors: {all_step_ids - all_orphaned}"
    )
    print(f"  ✓ All datasets missing → all {len(all_step_ids)} steps orphaned")

    # === Print readable summary ===
    print(f"\n  Summary for {exp.name}:")
    for dataset_name in refs.keys():
        orphaned = set(resolver.trace_impact({dataset_name}).get(dataset_name, []))
        runnable = all_step_ids - orphaned
        print(f"    Without {dataset_name}: {len(runnable)} runnable, {len(orphaned)} blocked")


def test_resolution_engine():
    """Test the full Resolution Engine against the NYC manifest + experiment."""
    from canopy.orchestrator.orchestrator import parse_manifest, parse_experiment
    from canopy.orchestrator.dependencies import DependencyResolver
    from canopy.orchestrator.resolution import ResolutionEngine
    from canopy.providers import create_default_registry
    import yaml

    manifest_path = project_root / "plots" / "nyc" / "manifest.yml"
    if not manifest_path.exists():
        print("  SKIP — manifest not found")
        return

    exp_path = find_experiment_path()
    if not exp_path:
        print("  SKIP — experiment not found")
        return

    manifest = parse_manifest(manifest_path)
    experiment = parse_experiment(exp_path)
    registry = create_default_registry()
    dag = DependencyResolver(experiment)

    # Load method data
    method_ref = experiment.lineage.method_ref
    method_data = {}
    if method_ref:
        method_path_str = method_ref
        if method_path_str.startswith("$methods/"):
            method_path_str = method_path_str[9:]
        if not method_path_str.endswith(".yml"):
            method_path_str += ".yml"
        method_path = project_root / "garden" / "methods" / method_path_str
        if method_path.exists():
            with open(method_path) as f:
                method_data = yaml.safe_load(f)
            print(f"  Loaded method: {method_data.get('name', method_path.stem)}")

    engine = ResolutionEngine(
        manifest=manifest,
        experiment=experiment,
        provider_registry=registry,
        dependency_resolver=dag,
        method_data=method_data,
    )

    report = engine.resolve()

    print(f"\n  Resolution Report:")
    print(f"    Summary: {report.summary}")
    print(f"    Full experiment possible: {report.full_experiment_possible}")
    print(f"    Can proceed: {report.can_proceed}")
    print(f"    Runnable steps: {len(report.runnable_steps)}")
    print(f"    Blocked steps: {len(report.blocked_steps)}")

    print(f"\n  Dataset resolutions:")
    for r in report.resolutions:
        icon = {"available": "✓", "acquired": "↓", "failed": "✗",
                "manual_required": "✋", "auth_required": "🔑"}.get(r.status, "?")
        print(f"    {icon} {r.dataset_name} ({r.status}): {r.message[:60]}...")
        if r.orphaned_steps:
            print(f"      Orphans {len(r.orphaned_steps)} steps: {r.orphaned_steps[:5]}...")
        if r.uncertainty_without:
            print(f"      Uncertainty: {r.uncertainty_without[:60]}...")
        if r.instructions:
            print(f"      Instructions: {r.instructions[:60]}...")

    if report.uncertainty_summary and "No uncertainty notes" not in report.uncertainty_summary:
        print(f"\n  Uncertainty summary:")
        for line in report.uncertainty_summary.split("\n"):
            print(f"    {line}")

    # Structural assertions
    assert isinstance(report.resolutions, list)
    assert isinstance(report.runnable_steps, list)
    assert isinstance(report.blocked_steps, list)
    assert isinstance(report.summary, str)
    print("\n  ✓ Report structure valid")

    # Runnable + blocked = total
    total = len(experiment.steps)
    assert len(report.runnable_steps) + len(report.blocked_steps) == total, (
        f"FAIL: {len(report.runnable_steps)} + {len(report.blocked_steps)} != {total}"
    )
    print("  ✓ Runnable + blocked = total steps")

    # No overlap
    assert set(report.runnable_steps) & set(report.blocked_steps) == set(), (
        "FAIL: runnable and blocked overlap"
    )
    print("  ✓ No overlap between runnable and blocked")

    # Envelope context
    ctx = report.to_envelope_context()
    for key in ["full_experiment_possible", "datasets_available", "runnable_steps", "uncertainty_summary"]:
        assert key in ctx, f"FAIL: '{key}' missing from envelope context"
    print("  ✓ Envelope context serialization works")

    if report.transaction:
        print(f"  Transaction: {len(report.transaction.pending_changes)} pending changes")
    else:
        print("  No transaction (no acquisitions needed)")


if __name__ == "__main__":
    print("\n=== Sprint 4 Verification ===\n")

    for name, fn in [
        ("Test 1: DAG impact tracing", test_trace_impact),
        ("Test 2: Resolution Engine", test_resolution_engine),
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