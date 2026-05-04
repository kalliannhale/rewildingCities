#!/usr/bin/env python3
"""
canopy/cli/experiment.py — Run a rewildingCities experiment.

Usage:
    python experiment.py plots/nyc/experiments/nyc_park_cooling_pedestrian.yml
    python experiment.py plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --profile dev
    python experiment.py plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --dry-run
    python experiment.py plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --resolve-only

"We embody, we learn, we release the idea of failure, because it is all data."
    — adrienne maree brown
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]
    )


def print_resolution_report(report):
    """Print a human-readable data resolution report."""
    print("\n─── Data Resolution ───")
    
    for r in report.resolutions:
        icon = {
            "available": "✓", "acquired": "↓", "failed": "✗",
            "manual_required": "✋", "auth_required": "🔑",
        }.get(r.status, "?")
        
        print(f"  {icon} {r.dataset_name} ({r.semantic_type}): {r.message}")
        
        if r.orphaned_steps:
            print(f"      Blocks {len(r.orphaned_steps)} steps: {', '.join(r.orphaned_steps[:5])}")
            if len(r.orphaned_steps) > 5:
                print(f"      ... and {len(r.orphaned_steps) - 5} more")
        
        if r.uncertainty_without:
            print(f"      Uncertainty: {r.uncertainty_without.strip()}")
        
        if r.instructions:
            print(f"      How to fix:")
            for line in r.instructions.strip().split("\n"):
                print(f"        {line}")
    
    print(f"\n  {report.summary}")
    
    if report.runnable_steps:
        print(f"  Runnable: {', '.join(report.runnable_steps)}")
    if report.blocked_steps:
        print(f"  Blocked:  {', '.join(report.blocked_steps)}")
    
    print()


def print_result(result):
    """Print a human-readable experiment result."""
    if result.success:
        print(f"\n✓ Experiment complete: {len(result.completed_steps)} steps executed")
        print(f"  Steps: {' → '.join(result.completed_steps)}")
        
        if result.final_envelopes:
            print("\n  Final envelopes:")
            for step_id, envelope in result.final_envelopes.items():
                path = envelope.data.get("path", "n/a") if hasattr(envelope, 'data') else "n/a"
                print(f"    {step_id}: {path}")
        
        if result.warnings:
            print(f"\n  ⚠ {len(result.warnings)} warnings:")
            for w in result.warnings[:5]:
                print(f"    - {w}")
            if len(result.warnings) > 5:
                print(f"    ... and {len(result.warnings) - 5} more")
    else:
        print(f"\n✗ Experiment failed")
        if result.failed_step:
            print(f"  Failed at step: {result.failed_step}")
        if result.error:
            print(f"\n{result.error}")
        if result.completed_steps:
            print(f"\n  Completed before failure: {' → '.join(result.completed_steps)}")


def main():
    parser = argparse.ArgumentParser(
        description="Run a rewildingCities experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python experiment.py plots/nyc/experiments/nyc_park_cooling_pedestrian.yml
  python experiment.py plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --profile dev
  python experiment.py plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --resolve-only
  python experiment.py plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --dry-run
        """
    )
    
    parser.add_argument("experiment", help="Path to experiment YAML file")
    parser.add_argument("--profile", default="full", choices=["full", "dev", "test", "neighborhood"])
    parser.add_argument("--dry-run", action="store_true", help="Validate without executing or acquiring")
    parser.add_argument("--resolve-only", action="store_true", help="Check/acquire data without running analysis")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--project-root", default=None)
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    experiment_path = Path(args.experiment)
    if not experiment_path.exists():
        print(f"✗ Experiment file not found: {experiment_path}")
        sys.exit(1)
    
    try:
        from canopy.orchestrator.orchestrator import Orchestrator
    except ImportError as e:
        print(f"✗ Could not import orchestrator: {e}")
        print("  Make sure you're running from the project root.")
        sys.exit(1)
    
    print(f"🌳 rewildingCities experiment runner")
    print(f"   Experiment: {experiment_path.name}")
    print(f"   Profile: {args.profile}")
    print(f"   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    
    try:
        orchestrator = Orchestrator(
            experiment_path=args.experiment,
            profile=args.profile,
            project_root=args.project_root,
        )
    except Exception as e:
        print(f"\n✗ Failed to initialize: {e}")
        sys.exit(1)
    
    print(f"   City: {orchestrator.manifest.city_name}")
    print(f"   Steps: {len(orchestrator.experiment.steps)}")
    print(f"   Providers: {', '.join(orchestrator.provider_registry.registered_providers)}")
    
    # ── Dry run ──
    if args.dry_run:
        print("\n─── Validation (dry run) ───")
        errors, warnings = orchestrator.validate()
        for w in warnings:
            print(f"  ⚠ {w}")
        if errors:
            for e in errors:
                print(f"  ✗ {e}")
            print(f"\n✗ Validation failed with {len(errors)} error(s).")
            sys.exit(1)
        else:
            print(f"  ✓ Validation passed.")
            
            # Also show consistency check
            issues = orchestrator.manifest.check_consistency()
            if issues:
                print(f"\n  Manifest consistency ({len(issues)} issue(s)):")
                for issue in issues:
                    print(f"    {issue.issue}: {issue.dataset_name}")
            sys.exit(0)
    
    # ── Resolve only ──
    if args.resolve_only:
        report = orchestrator.resolve_data()
        print_resolution_report(report)
        sys.exit(0 if report.full_experiment_possible else 1)
    
    # ── Full run ──
    print("\n─── Running experiment ───")
    result = orchestrator.run()
    print_result(result)
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
