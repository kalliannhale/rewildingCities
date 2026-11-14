"""canopy/cli/_run.py ~ the one run path for an experiment.

experiment.py and `rewilding sows` both call run_experiment(), so the banner,
dry run, resolve-only, full run, and exit codes cannot drift apart. ~
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

PROFILES = ["full", "dev", "test", "neighborhood"]


def setup_logging(verbose: bool = False) -> None:
    """stderr-bound logging. INFO by default, DEBUG with --verbose."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s",
                        handlers=[logging.StreamHandler(sys.stderr)])


def run_experiment(experiment: str, profile: str = "full", *, dry_run: bool = False,
                   resolve_only: bool = False, project_root: str | None = None,
                   verbose: bool = False) -> int:
    """validate, resolve, or run one experiment. returns an exit code. ~"""
    setup_logging(verbose)

    experiment_path = Path(experiment)
    if not experiment_path.exists():
        print(f"✗ Experiment file not found: {experiment_path}", file=sys.stderr)
        return 1

    # deferred so --help works even if the orchestrator can't be imported
    try:
        from canopy.orchestrator.orchestrator import Orchestrator
    except ImportError as e:
        print(f"✗ Could not import orchestrator: {e}", file=sys.stderr)
        print("  Make sure you're running from the project root.", file=sys.stderr)
        return 1

    from canopy.cli.experiment import (
        print_profile_details, print_resolution_report, print_result,
    )

    # header before construction, so you see what was attempted even if it fails
    print("🌳 rewildingCities experiment runner")
    print(f"   Experiment: {experiment_path.name}")
    print(f"   Profile: {profile}")

    try:
        orchestrator = Orchestrator(experiment_path=experiment, profile=profile,
                                    project_root=project_root)
    except Exception as e:
        print(f"\n✗ Failed to initialize: {e}", file=sys.stderr)
        return 1

    print_profile_details(orchestrator)
    print(f"   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"   City: {orchestrator.manifest.city_name}")
    print(f"   Steps: {len(orchestrator.experiment.steps)}")
    print(f"   Providers: {', '.join(orchestrator.provider_registry.registered_providers)}")

    if dry_run:
        print("\n─── Validation (dry run) ───")
        errors, warnings = orchestrator.validate()
        for w in warnings:
            print(f"  ⚠ {w}")
        if errors:
            for e in errors:
                print(f"  ✗ {e}")
            print(f"\n✗ Validation failed with {len(errors)} error(s).")
            return 1
        print("  ✓ Validation passed.")
        # available-but-missing and unavailable-but-present files
        issues = orchestrator.manifest.check_consistency()
        if issues:
            print(f"\n  Manifest consistency ({len(issues)} issue(s)):")
            for issue in issues:
                print(f"    {issue.issue}: {issue.dataset_name}")
        return 0

    if resolve_only:
        report = orchestrator.resolve_data()
        print_resolution_report(report)
        return 0 if report.full_experiment_possible else 1

    print("\n─── Running experiment ───")
    result = orchestrator.run()
    print_result(result)
    return 0 if result.success else 1
