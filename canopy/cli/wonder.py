"""canopy/cli/wonder.py ~ `rewilding wonder`: what can this ground wonder about?"""

from __future__ import annotations

import sys

from ._common import find_root


def register(subparsers) -> None:
    p = subparsers.add_parser("wonder", help="what can this ground wonder about?")
    p.add_argument("plot", help="the plot name, e.g. nyc")
    p.add_argument("question", nargs="?", default="",
                   help="a plain question about this community")
    p.set_defaults(func=run)


def run(args) -> int:
    root = find_root()
    from canopy.vocabulary import Vocabulary
    from canopy.loam.loam import Loam
    from canopy.loam.envelope_reader import till_envelopes
    from canopy.loam.manifest_reader import plant_manifest
    from canopy.wonder.possibility import explore

    plot, question = args.plot, args.question
    schemas = root / "seeds" / "schemas"
    plot_dir = root / "plots" / plot
    envelopes_dir = plot_dir / ".envelopes"
    bed = plot_dir / ".loam" / "loam.duckdb"

    if not plot_dir.is_dir():
        print(f"no plot at plots/{plot} ~ found one with:  python -m canopy.cli init {plot}",
              file=sys.stderr)
        return 2

    print((f'🌍  wondering about {plot}: "{question}"' if question
           else f"🌍  wondering about {plot}") + "\n")

    # a fresh, re-derivable bed each time, so a schema change never collides
    # with a stale one; loam re-tills from the receipts.
    bed.parent.mkdir(parents=True, exist_ok=True)
    if bed.exists():
        bed.unlink()

    vocab = Vocabulary.load(str(schemas))
    loam = Loam(vocab, str(bed))

    # plant first: the manifest is the bronze registry, and a declared-but-
    # unacquired holding is invisible to everything downstream until it is
    # planted. that gap between declared and acquired is exactly what the
    # backward read calls the seed still missing. S-04.
    manifest_path = plot_dir / "manifest.yml"
    if manifest_path.is_file():
        planted = plant_manifest(loam, str(manifest_path))
        line = f"planted {len(planted['planted'])} declared holding(s) from the manifest"
        if planted["refused"]:
            line += f", {len(planted['refused'])} refused"
        print(line)

    if envelopes_dir.is_dir():
        report = till_envelopes(loam, str(envelopes_dir), vocab, plot)
        line = f"tilled {len(report['tilled'])} envelope(s) from plots/{plot}/.envelopes"
        if report["refused"]:
            line += f", {len(report['refused'])} refused"
        print(line + "\n")
    else:
        print(f"(no plots/{plot}/.envelopes yet ~ this ground holds no conformed data)\n")

    possibilities = explore(loam, plot, question, root=root)
    if not possibilities:
        print("nothing to wonder about yet ~ once this ground holds conformed data, ask again. ~")
    for p in possibilities[:5]:
        print(p.say())
        print()
    _say_exposure(plot, root)
    return 0


def _say_exposure(plot: str, root) -> None:
    """what may leave this ground, judged by the one gate at `public`, and for
    everything withheld, why and what would admit it (Contract 1, rules 7
    and 8). the same reading PlotReading.exposure carries. ~"""
    from canopy.expose.check import read_exposure
    exposure = read_exposure(plot, root=root)
    if not exposure:
        return
    free = [e for e in exposure if e["may_leave"]]
    held = [e for e in exposure if not e["may_leave"]]
    print(f"🚪  what may leave {plot}, at public: {len(free)} of {len(exposure)} receipt(s)")
    for e in free:
        print(f"   ~ {e['artifact']} ({e['semantic_type']})")
        for c in e["caveats"]:
            print(f"       caveat: {c}")
    if held:
        print(f"\n   withheld, and why:")
        for e in held:
            print(f"   ~ {e['artifact']} ({e['semantic_type']})")
            seen = set()
            for w in e["withheld"]:
                key = (w["rule"], w["reason"])
                if key in seen:
                    continue
                seen.add(key)
                print(f"       rule {w['rule']}: {w['reason']}")
                print(f"         would admit it: {w['would_admit']}")
    print()
