"""canopy/cli/sows.py ~ `rewilding sows`: run a composed experiment.

Delegates to the orchestrator and reuses experiment.py's rich printers, so the
branded command and the standalone `python -m canopy.cli.experiment` share one
implementation of the output. ~
"""

from __future__ import annotations

import sys
from pathlib import Path


def register(subparsers) -> None:
    p = subparsers.add_parser("sows", help="run a composed experiment")
    p.add_argument("experiment", help="path to an experiment .yml")
    p.add_argument("--profile", default="full",
                   choices=["full", "dev", "test", "neighborhood"])
    p.add_argument("--dry-run", action="store_true", help="validate without running")
    p.add_argument("--resolve-only", action="store_true", help="check data without running")
    p.set_defaults(func=run)


def run(args) -> int:
    if not Path(args.experiment).exists():
        print(f"no experiment at {args.experiment}", file=sys.stderr)
        return 1

    from canopy.orchestrator.orchestrator import Orchestrator
    from canopy.cli.experiment import (
        print_result, print_resolution_report, print_profile_details,
    )

    orch = Orchestrator(experiment_path=args.experiment, profile=args.profile)
    print_profile_details(orch)

    if args.dry_run:
        errors, warnings = orch.validate()
        for w in warnings:
            print(f"  ⚠ {w}")
        for e in errors:
            print(f"  ✗ {e}")
        return 1 if errors else 0

    if args.resolve_only:
        report = orch.resolve_data()
        print_resolution_report(report)
        return 0 if report.full_experiment_possible else 1

    result = orch.run()
    print_result(result)
    return 0 if result.success else 1
