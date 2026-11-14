"""canopy/cli/sows.py ~ `rewilding sows`: run a composed experiment.

Calls the same run path as `python -m canopy.cli.experiment` (canopy/cli/_run.py),
so the two cannot disagree about output, flags, or exit codes. ~
"""

from __future__ import annotations

from canopy.cli._run import PROFILES, run_experiment


def register(subparsers) -> None:
    p = subparsers.add_parser("sows", help="run a composed experiment")
    p.add_argument("experiment", help="path to an experiment .yml")
    p.add_argument("--profile", default="full", choices=PROFILES)
    p.add_argument("--dry-run", action="store_true", help="validate without running")
    p.add_argument("--resolve-only", action="store_true", help="check data without running")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--project-root", default=None,
                   help="override project root (defaults to the nearest garden)")
    p.set_defaults(func=run)


def run(args) -> int:
    return run_experiment(
        args.experiment, args.profile, dry_run=args.dry_run,
        resolve_only=args.resolve_only, project_root=args.project_root,
        verbose=args.verbose,
    )
