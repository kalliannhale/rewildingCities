"""canopy/cli/init.py ~ `rewilding init`: found a plot for a new community."""

from __future__ import annotations

import sys

from ._common import find_root


def register(subparsers) -> None:
    p = subparsers.add_parser("init", help="found a plot for a new community")
    p.add_argument("plot", help="the plot name, e.g. maine")
    p.add_argument("name", nargs="?", default="", help="display name, e.g. Maine")
    p.set_defaults(func=run)


def run(args) -> int:
    root = find_root()
    plot = args.plot
    plot_dir = root / "plots" / plot
    if plot_dir.exists():
        print(f"a plot already lives at plots/{plot} ~ nothing changed.", file=sys.stderr)
        return 2

    for sub in (".envelopes", ".data", ".loam"):
        (plot_dir / sub).mkdir(parents=True, exist_ok=True)

    display = args.name or plot.replace("_", " ").title()
    (plot_dir / "manifest.yml").write_text(
        "# " + "=" * 68 + "\n"
        f"# plots/{plot}/manifest.yml ~ {display}'s bronze registry\n"
        "# declare each dataset this community holds or seeks. a declared-but-\n"
        f"# absent dataset is honest: `wonder {plot}` names it and what its\n"
        "# absence costs. nothing here is acquired until you ask.\n"
        "# " + "=" * 68 + "\n\n"
        "city:\n"
        f"  name: {display}\n"
        f"  id: {plot}\n\n"
        "crs:\n"
        '  working: "EPSG:4326"   # interchange frame; reproject to a local projected CRS for metric work\n\n'
        "datasets: {}\n"
    )

    print(f"🌱 founded plots/{plot} ~ a new plot for {display}")
    print(f"   plots/{plot}/manifest.yml   (declare data here)")
    print(f"   plots/{plot}/.envelopes/    (conformed artifacts land here)")
    print(f"   plots/{plot}/.data/         (raw inputs)")
    print(f'\n   next: declare a dataset, then  python -m canopy.cli wonder {plot} "..."')
    return 0
