#!/usr/bin/env python3
"""canopy/cli/experiment.py — Run a rewildingCities experiment.

Invoke as a module from the project root:

    python -m canopy.cli.experiment <experiment_path>
    python -m canopy.cli.experiment <experiment_path> --profile dev
    python -m canopy.cli.experiment <experiment_path> --dry-run
    python -m canopy.cli.experiment <experiment_path> --resolve-only

The four profile choices (full, dev, test, neighborhood) are defined in
seeds/profiles/profiles.yml. Each profile controls whether the orchestrator
injects sampling steps and (in future sprints) downsamples rasters or scopes
the study area. See section 5.1 of the Sprint 6/7 reference doc.

"We embody, we learn, we release the idea of failure, because it is all data."
    — adrienne maree brown
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone


def setup_logging(verbose: bool = False):
    """Configure stderr-bound logging. INFO by default, DEBUG with --verbose."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]
    )


def print_profile_details(orchestrator):
    """Surface what the active profile actually did (or didn't) to the experiment.

    Called once, after orchestrator construction, before the rest of the
    banner. Two distinct disclosures:

    1. Feature-sampling injection (Sprint 6). If the profile injected
       sampling steps, name the method and resolved parameters, then
       enumerate each injection so the user can see the DAG was reshaped.

    2. Unimplemented-feature stubs (the doc's "honest interim disclosure"
       commitment). The profile schema accepts study_area and resolution
       configurations that the orchestrator doesn't yet act on. When a
       profile requests one of these, we say so explicitly rather than
       silently using the default.

    Glyph convention: ⚙ = what happened. ⓘ = what was asked for but
    didn't happen. Different categories, different glyphs.
    """
    # ── Sprint 6: feature-sampling injection details ──
    # injection_log is populated by Orchestrator._inject_profile_steps;
    # if the profile disabled feature_sampling, the list is empty and we
    # print nothing in this block.
    if orchestrator.injection_log:
        fs = orchestrator.profile_config.get("feature_sampling", {})
        method = fs.get("method", "random")
        seed = fs.get("seed", "—")

        # The "detail" string describes the sampling configuration in
        # method-appropriate terms. Stratified uses n_per_stratum; first_n
        # is deterministic and has no seed; random and explicit use n.
        if method == "stratified":
            detail = f"{method}, {fs.get('n_per_stratum', '—')} per stratum"
        elif method == "first_n":
            detail = f"{method}, n={fs.get('n', '—')} (deterministic, no seed)"
        else:
            detail = f"{method}, n={fs.get('n', '—')}"

        # Append seed only for methods that actually use it. first_n,
        # filtered, and explicit are deterministic, so a seed value
        # would be misleading.
        if method in ("random", "stratified"):
            detail += f", seed={seed}"

        print(f"     feature sampling: {detail}")

        # One line per injection, with the rewired_count surfaced so the
        # user can see how many downstream references were redirected.
        # If this number changes between runs of the same profile on the
        # same experiment, something is wrong upstream.
        for entry in orchestrator.injection_log:
            print(
                f"     ⚙ injected '{entry['step_id']}' after "
                f"'{entry['after']}' (rewired {entry['rewired_count']} references)"
            )

    # ── Honest disclosure: profile fields we accept but don't yet act on ──
    # The profile YAML can declare study_area.type and resolution.mode,
    # but the orchestrator currently ignores both. Rather than silently
    # using defaults, we name what was asked for so the user isn't
    # misled by the resolved DAG.
    sa = orchestrator.profile_config.get("study_area", {})
    if sa.get("type", "full") != "full":
        print(
            f"   ⓘ study_area scoping ({sa.get('type')}) not yet implemented "
            f"— full study area will be used"
        )
    res = orchestrator.profile_config.get("resolution", {})
    if res.get("mode", "native") != "native":
        target = res.get("target_meters", "—")
        print(
            f"   ⓘ raster resolution downsampling not yet implemented "
            f"— native resolution will be used (asked: {target}m)"
        )


def print_resolution_report(report):
    """Print a human-readable data resolution report.

    Reads the ResolutionReport produced by ResolutionEngine.resolve().
    Each dataset gets one line with a status glyph, plus indented detail
    lines for orphaned-step impact, uncertainty notes, and remediation
    instructions.
    """
    print("\n─── Data Resolution ───")

    # Status glyphs match the resolution engine's status vocabulary.
    # ? is the fallback for any status the engine adds later without
    # updating this map.
    status_icons = {
        "available": "✓",
        "acquired": "↓",
        "failed": "✗",
        "manual_required": "✋",
        "auth_required": "🔑",
    }

    for r in report.resolutions:
        icon = status_icons.get(r.status, "?")
        print(f"  {icon} {r.dataset_name} ({r.semantic_type}): {r.message}")

        # If a missing dataset orphans downstream steps, show them so the
        # user understands the scope of impact. Truncate at 5 to keep
        # the report scannable.
        if r.orphaned_steps:
            print(f"      Blocks {len(r.orphaned_steps)} steps: {', '.join(r.orphaned_steps[:5])}")
            if len(r.orphaned_steps) > 5:
                print(f"      ... and {len(r.orphaned_steps) - 5} more")

        # Uncertainty_without comes from the method's requires_data field
        # (Sprint 7). It tells the user what the analysis loses by missing
        # this dataset — separate from the remediation instructions.
        if r.uncertainty_without:
            print(f"      Uncertainty: {r.uncertainty_without.strip()}")

        # Instructions are provider-specific remediation steps (e.g. how
        # to authenticate Earth Engine, how to download a manual dataset).
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
    """Print a human-readable experiment result after a full run.

    Two branches: success path enumerates completed steps and final
    envelope paths; failure path identifies the failed step and surfaces
    its error message so the user can debug without digging through logs.
    """
    if result.success:
        print(f"\n✓ Experiment complete: {len(result.completed_steps)} steps executed")
        print(f"  Steps: {' → '.join(result.completed_steps)}")

        if result.final_envelopes:
            print("\n  Final envelopes:")
            for step_id, envelope in result.final_envelopes.items():
                # Envelopes may or may not have a .data dict depending on
                # primitive output shape; defensive lookup.
                path = envelope.data.get("path", "n/a") if hasattr(envelope, 'data') else "n/a"
                print(f"    {step_id}: {path}")

        # Warnings can accumulate to high counts in long pipelines.
        # Truncate at 5 here too for the same scannability reason.
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
    """CLI entry point. Parses args, constructs the orchestrator, dispatches
    to one of three modes: dry run (validation only), resolve-only (data
    check), or full run (execute the experiment).
    """
    parser = argparse.ArgumentParser(
        description="Run a rewildingCities experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m canopy.cli.experiment plots/nyc/experiments/nyc_park_cooling_pedestrian.yml
  python -m canopy.cli.experiment plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --profile dev
  python -m canopy.cli.experiment plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --resolve-only
  python -m canopy.cli.experiment plots/nyc/experiments/nyc_park_cooling_pedestrian.yml --dry-run
        """
    )

    parser.add_argument("experiment", help="Path to experiment YAML file")
    parser.add_argument(
        "--profile", default="full",
        choices=["full", "dev", "test", "neighborhood"],
        help="Active profile (defined in seeds/profiles/profiles.yml)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate without executing or acquiring")
    parser.add_argument("--resolve-only", action="store_true",
                        help="Check/acquire data without running analysis")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--project-root", default=None,
                        help="Override project root (defaults to current working directory)")

    args = parser.parse_args()
    setup_logging(args.verbose)

    experiment_path = Path(args.experiment)
    if not experiment_path.exists():
        print(f"✗ Experiment file not found: {experiment_path}")
        sys.exit(1)

    # Import deferred until after arg parsing so --help works even if
    # the orchestrator can't be imported (e.g. wrong working directory).
    try:
        from canopy.orchestrator.orchestrator import Orchestrator
    except ImportError as e:
        print(f"✗ Could not import orchestrator: {e}")
        print("  Make sure you're running from the project root.")
        sys.exit(1)

    # ── Header (printed before orchestrator construction so the user
    # sees what's being attempted even if construction fails) ──
    print(f"🌳 rewildingCities experiment runner")
    print(f"   Experiment: {experiment_path.name}")
    print(f"   Profile: {args.profile}")

    # ── Orchestrator construction. This is where Sprint 6's step
    # injection happens — if the active profile enables feature_sampling,
    # sampling steps are appended to the experiment and downstream
    # references are rewired before __init__ returns. ──
    try:
        orchestrator = Orchestrator(
            experiment_path=args.experiment,
            profile=args.profile,
            project_root=args.project_root,
        )
    except Exception as e:
        print(f"\n✗ Failed to initialize: {e}")
        sys.exit(1)

    # Surface what the profile actually did, then the rest of the banner.
    # Ordering matters: profile details belong with the Profile line above,
    # not with the Time/City/Steps deployment info below.
    print_profile_details(orchestrator)

    print(f"   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"   City: {orchestrator.manifest.city_name}")
    print(f"   Steps: {len(orchestrator.experiment.steps)}")
    print(f"   Providers: {', '.join(orchestrator.provider_registry.registered_providers)}")

    # ── Dry run: validate but do not execute or acquire data ──
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

            # Manifest consistency: detects available-but-missing files
            # and unavailable-but-present files. Surfaced here because
            # dry-run is the natural "before you run anything" moment.
            issues = orchestrator.manifest.check_consistency()
            if issues:
                print(f"\n  Manifest consistency ({len(issues)} issue(s)):")
                for issue in issues:
                    print(f"    {issue.issue}: {issue.dataset_name}")
            sys.exit(0)

    # ── Resolve only: run Phases 1-2 (validate + data resolution) but
    # not Phase 3 (execute). Used to check what's runnable before
    # committing to a long execution. ──
    if args.resolve_only:
        report = orchestrator.resolve_data()
        print_resolution_report(report)
        sys.exit(0 if report.full_experiment_possible else 1)

    # ── Full run: all three phases ──
    print("\n─── Running experiment ───")
    result = orchestrator.run()
    print_result(result)
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()