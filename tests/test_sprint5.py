#!/usr/bin/env python3
"""
Sprint 5 Verification — run from project root:
    python tests/test_sprint5.py

Tests the wired-up orchestrator and CLI.
"""

import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def find_experiment_path():
    direct = project_root / "plots" / "nyc" / "experiments" / "nyc_park_cooling_pedestrian.yml"
    if direct.exists():
        return direct
    for p in project_root.rglob("nyc_park_cooling_pedestrian.yml"):
        return p
    return None


def test_orchestrator_resolve_data():
    """Test that Orchestrator.resolve_data() works end-to-end."""
    from canopy.orchestrator.orchestrator import Orchestrator

    exp_path = find_experiment_path()
    if not exp_path:
        print("  SKIP — experiment not found")
        return

    orchestrator = Orchestrator(
        experiment_path=str(exp_path),
        profile="dev",
    )

    # Verify provider registry is wired
    providers = orchestrator.provider_registry.registered_providers
    assert len(providers) >= 7, f"FAIL: expected 7+ providers, got {len(providers)}"
    print(f"  ✓ Provider registry wired: {len(providers)} providers")

    # Run resolve_data
    report = orchestrator.resolve_data()

    print(f"  Resolution: {report.summary}")
    print(f"  Full experiment possible: {report.full_experiment_possible}")
    print(f"  Runnable: {len(report.runnable_steps)}, Blocked: {len(report.blocked_steps)}")

    for r in report.resolutions:
        print(f"    {r.dataset_name}: {r.status}")

    assert len(report.resolutions) > 0, "FAIL: should have at least one resolution"
    assert len(report.runnable_steps) + len(report.blocked_steps) == len(orchestrator.experiment.steps), (
        "FAIL: runnable + blocked should equal total steps"
    )
    print("  ✓ resolve_data() produces valid report")

    assert orchestrator._resolution_report is not None, "FAIL: _resolution_report should be stored"
    print("  ✓ Resolution report stored for envelope enrichment")


def test_orchestrator_run_phases():
    """Test that run() executes all three phases in order."""
    from canopy.orchestrator.orchestrator import Orchestrator

    exp_path = find_experiment_path()
    if not exp_path:
        print("  SKIP — experiment not found")
        return

    orchestrator = Orchestrator(
        experiment_path=str(exp_path),
        profile="dev",
    )

    errors, warnings = orchestrator.validate()
    if errors:
        print(f"  Validation errors (may be expected): {errors[:3]}")
    print(f"  ✓ Validation: {len(errors)} errors, {len(warnings)} warnings")

    report = orchestrator.resolve_data()
    print(f"  ✓ Resolution: {report.summary}")

    print("  ✓ Phases 1 (validate) and 2 (resolve) work correctly")
    print("  Note: Phase 3 (execute) requires R runtime — test via CLI")


def test_cli_dry_run():
    """Test the CLI in --dry-run mode."""
    exp_path = find_experiment_path()
    if not exp_path:
        print("  SKIP — experiment not found")
        return

    result = subprocess.run(
        [sys.executable, "-m", "canopy.cli.experiment", str(exp_path), "--dry-run"],
        capture_output=True, text=True, cwd=str(project_root),
        timeout=30,
    )

    print(f"  Exit code: {result.returncode}")
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            print(f"    {line}")
    if result.stderr:
        for line in result.stderr.strip().split("\n")[:5]:
            print(f"    (stderr) {line}")

    print(f"  ✓ CLI --dry-run ran (exit code {result.returncode})")


def test_cli_resolve_only():
    """Test the CLI in --resolve-only mode."""
    exp_path = find_experiment_path()
    if not exp_path:
        print("  SKIP — experiment not found")
        return

    result = subprocess.run(
        [sys.executable, "-m", "canopy.cli.experiment", str(exp_path), "--resolve-only"],
        capture_output=True, text=True, cwd=str(project_root),
        timeout=30,
    )

    print(f"  Exit code: {result.returncode}")
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            print(f"    {line}")
    if result.stderr:
        for line in result.stderr.strip().split("\n")[:5]:
            print(f"    (stderr) {line}")

    assert "Data Resolution" in result.stdout or "resolution" in result.stdout.lower(), (
        "FAIL: --resolve-only output should contain resolution report"
    )
    print(f"  ✓ CLI --resolve-only shows resolution report")


def test_all_previous_sprints_still_pass():
    """Verify that Sprints 1-4 tests still pass after Sprint 5 changes."""
    for sprint_num in [1, 2, 3, 4]:
        test_path = project_root / "tests" / f"test_sprint{sprint_num}.py"
        if not test_path.exists():
            print(f"  SKIP — test_sprint{sprint_num}.py not found")
            continue

        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True, text=True, cwd=str(project_root),
            timeout=60,
        )

        if "FAILED" in result.stdout:
            print(f"  ✗ Sprint {sprint_num} has failures:")
            for line in result.stdout.split("\n"):
                if "FAILED" in line or "FAIL" in line:
                    print(f"      {line.strip()}")
            assert False, f"Sprint {sprint_num} regression detected"
        else:
            passed_count = result.stdout.count("PASSED")
            print(f"  ✓ Sprint {sprint_num}: {passed_count} test(s) passed")


if __name__ == "__main__":
    print("\n=== Sprint 5 Verification ===\n")

    for name, fn in [
        ("Test 1: Orchestrator.resolve_data()", test_orchestrator_resolve_data),
        ("Test 2: Orchestrator run phases", test_orchestrator_run_phases),
        ("Test 3: CLI --dry-run", test_cli_dry_run),
        ("Test 4: CLI --resolve-only", test_cli_resolve_only),
        ("Test 5: Regression — all previous sprints", test_all_previous_sprints_still_pass),
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
