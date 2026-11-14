"""canopy/cli/init.py ~ `rewilding init`: found a plot for a new community."""

from __future__ import annotations

import json
import re
import sys

from ._common import find_root

# a plot's name becomes a directory name and a manifest id, so it must be a
# plain slug: lowercase letters, digits, underscores, starting with a letter.
# no path separators, no dots, no spaces. ~
_PLOT_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")


def register(subparsers) -> None:
    p = subparsers.add_parser("init", help="found a plot for a new community")
    p.add_argument("plot", help="the plot name, e.g. maine")
    p.add_argument("name", nargs="?", default="", help="display name, e.g. Maine")
    p.set_defaults(func=run)


def run(args) -> int:
    plot = args.plot
    if not _PLOT_NAME.fullmatch(plot):
        print(f"'{plot}' is not a plot name. use lowercase letters, digits, and "
              f"underscores, starting with a letter (e.g. maine, nyc_2026).",
              file=sys.stderr)
        return 2

    root = find_root()
    plot_dir = root / "plots" / plot
    if plot_dir.exists():
        print(f"a plot already lives at plots/{plot} ~ nothing changed.", file=sys.stderr)
        return 2

    for sub in (".envelopes", ".data", ".loam"):
        (plot_dir / sub).mkdir(parents=True, exist_ok=True)

    # written as a JSON string, which is also a valid YAML double-quoted scalar,
    # so a colon or quote in the display name cannot break the manifest.
    display = args.name.strip() or plot.replace("_", " ").title()
    (plot_dir / "manifest.yml").write_text(
        "# " + "=" * 68 + "\n"
        f"# plots/{plot}/manifest.yml ~ {plot}'s bronze registry\n"
        "# declare each dataset this community holds or seeks. a declared-but-\n"
        f"# absent dataset is honest: `wonder {plot}` names it and what its\n"
        "# absence costs. nothing here is acquired until you ask.\n"
        "# " + "=" * 68 + "\n\n"
        "city:\n"
        f"  name: {json.dumps(display)}\n"
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
