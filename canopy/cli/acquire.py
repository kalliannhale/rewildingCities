"""canopy/cli/acquire.py ~ `rewilding acquire`: what would it take to ask this?

the ring, closed and made usable. readiness reads the mart backward to name
the seed still missing; the resolution engine says what it would take to get
each one HERE. both halves existed and never spoke. this is the verb that
lets a person ask. ~

    rewilding acquire nyc garden/methods/thermal/land_cover_cooling_differential.yml
    rewilding acquire nyc <method> --enriching     # also what would merely improve it
    rewilding acquire nyc <method> --fetch          # actually acquire what can be
"""

from __future__ import annotations

import sys

from ._common import find_root


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "acquire", help="what would it take to answer this here?")
    p.add_argument("plot", help="the plot name, e.g. nyc")
    p.add_argument("method", help="path to a method .yml")
    p.add_argument("--enriching", action="store_true",
                   help="include data that would improve, not just unblock")
    p.add_argument("--fetch", action="store_true",
                   help="acquire what can be acquired (default senses only)")
    p.set_defaults(func=run)


def run(args) -> int:
    root = find_root()

    from canopy.vocabulary import Vocabulary
    from canopy.loam.loam import Loam
    from canopy.loam.manifest_reader import plant_manifest
    from canopy.loam.envelope_reader import till_envelopes
    from canopy.loam.readiness import acquisition_gap
    from canopy.orchestrator.parsing import parse_manifest
    from canopy.orchestrator.resolution import ResolutionEngine
    from canopy.providers import create_default_registry

    plot = args.plot
    plot_dir = root / "plots" / plot
    manifest_path = plot_dir / "manifest.yml"
    method_path = root / args.method if not str(args.method).startswith("/") \
        else args.method

    if not manifest_path.is_file():
        print(f"no manifest at plots/{plot}/manifest.yml", file=sys.stderr)
        return 2
    if not str(method_path):
        print(f"no method at {args.method}", file=sys.stderr)
        return 2

    bed = plot_dir / ".loam" / "loam.duckdb"
    bed.parent.mkdir(parents=True, exist_ok=True)
    if bed.exists():
        bed.unlink()

    vocab = Vocabulary.load(root / "seeds" / "schemas")
    loam = Loam(vocab, str(bed))
    plant_manifest(loam, str(manifest_path))
    if (plot_dir / ".envelopes").is_dir():
        till_envelopes(loam, str(plot_dir / ".envelopes"), vocab, plot)

    gap = acquisition_gap(loam, plot, str(method_path),
                          include_enriching=args.enriching)

    print(f"\n🌾  what {plot} would need for {method_path.name}\n")

    if not gap:
        print("   nothing missing ~ this ground can answer as it stands.\n")
        return 0

    manifest = parse_manifest(manifest_path)
    engine = ResolutionEngine(manifest=manifest,
                              provider_registry=create_default_registry())
    report = engine.acquire_types(gap, dry=not args.fetch,
                                  loam=loam, plot=plot)

    headings = {
        "acquired_unconformed": "you already have this ~ it has never been run",
        "acquirable": ("acquired" if args.fetch else "this machine could fetch"),
        "blocked": "needs a person",
        "undeclared": "nothing here provides this yet",
        "ambiguous": "more than one holding offers this",
        "present": "present and conformed",
    }

    for bucket, heading in headings.items():
        items = report.get(bucket) or []
        if not items:
            continue
        print(f"   {heading}:")
        for item in items:
            line = f"     ~ {item.get('semantic_type')}"
            if item.get("dataset"):
                line += f"  ({item['dataset']})"
            print(line)
            for key in ("next_step", "detail", "message"):
                if item.get(key):
                    print(f"         {item[key]}")
            if item.get("datasets"):
                print(f"         {', '.join(item['datasets'])}")
        print()

    if not args.fetch and report.get("acquirable"):
        print("   run again with --fetch to acquire what can be acquired.\n")
    return 0
