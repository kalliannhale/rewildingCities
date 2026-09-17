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
        return 0
    for p in possibilities[:5]:
        print(p.say())
        print()
    return 0
