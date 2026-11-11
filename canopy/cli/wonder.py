"""canopy/cli/wonder.py ~ `rewilding wonder`: what can this ground wonder about?"""

from __future__ import annotations

import sys

from ._common import find_root

# the graph's views, in the order a reader meets them (D-168 to D-175)
GRAPH_ORDER = ("places", "edges", "indicator_values", "place_values", "plot_places")


def register(subparsers) -> None:
    p = subparsers.add_parser("wonder", help="what can this ground wonder about?")
    p.add_argument("plot", help="the plot name, e.g. nyc")
    p.add_argument("question", nargs="?", default="",
                   help="a plain question about this community")
    p.set_defaults(func=run)


def run(args) -> int:
    root = find_root()
    from canopy.wonder.session import open_plot, PlotNotFound
    from canopy.wonder.possibility import explore

    plot, question = args.plot, args.question

    # one way to open a plot for every reader (session.py): a fresh bed,
    # the manifest planted, the receipts tilled, and the graph's views made
    # over them. the CLI used to do the first four by hand and never made
    # the views, so it could not see a single place (D-178).
    try:
        _vocab, loam, report = open_plot(plot, root=root)
    except PlotNotFound:
        print(f"no plot at plots/{plot} ~ found one with:  python -m canopy.cli init {plot}",
              file=sys.stderr)
        return 2

    print((f'🌍  wondering about {plot}: "{question}"' if question
           else f"🌍  wondering about {plot}") + "\n")

    # plant first: the manifest is the bronze registry, and a declared-but-
    # unacquired holding is invisible to everything downstream until it is
    # planted. that gap between declared and acquired is exactly what the
    # backward read calls the seed still missing. S-04.
    line = f"planted {report['planted']} declared holding(s) from the manifest"
    if report["planted_refused"]:
        line += f", {len(report['planted_refused'])} refused"
    print(line)

    if (root / "plots" / plot / ".envelopes").is_dir():
        line = f"tilled {report['tilled']} envelope(s) from plots/{plot}/.envelopes"
        if report["tilled_refused"]:
            line += f", {len(report['tilled_refused'])} refused"
        print(line)
    else:
        print(f"(no plots/{plot}/.envelopes yet ~ this ground holds no conformed data)")

    _say_graph(report.get("graph") or {})
    print()

    possibilities = explore(loam, plot, question, root=root)
    if not possibilities:
        print("nothing to wonder about yet ~ once this ground holds conformed data, ask again. ~")
    for p in possibilities[:5]:
        print(p.say())
        print()
    _say_exposure(plot, root)
    return 0


def _rows(entry: dict) -> int | None:
    """a made view's size: its rows, or for place_values the sum of its
    statuses, since that report counts by status rather than in total."""
    if entry.get("rows") is not None:
        return entry["rows"]
    by_status = entry.get("by_status")
    return sum(by_status.values()) if by_status else None


def _say_graph(graph: dict) -> None:
    """
    what the plot's part of the graph made, and every view it did not make,
    with why (D-178). a plot with no places has no graph, said once rather
    than five times. a view that was not made is the reason a reading
    through it would come back empty, so it is never left unsaid. the whole
    report stays in open_plot's return for any reader that wants more. ~
    """
    places = graph.get("places") or {}
    if not places.get("made"):
        print(f"(no graph in this plot ~ {places.get('why', 'no run has made places')})")
        return

    made, unmade = [], []
    for view in GRAPH_ORDER:
        entry = graph.get(view)
        if entry is None:
            continue
        if entry.get("made"):
            rows = _rows(entry)
            made.append(f"{view} ({rows:,})" if rows is not None else view)
        else:
            unmade.append((view, entry.get("why", "no reason was given")))

    print(f"🕸  graph: {', '.join(made)}")
    for view, why in unmade:
        print(f"   ~ no {view}: {why}")
    for left in (graph.get("indicator_values") or {}).get("left_out") or []:
        print(f"   ~ a value receipt left out: {left}")


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
