"""canopy/cli/profile.py ~ `rewilding profile`: every place's profile (Contract 4)

  python -m canopy.cli profile maine
      builds every place's profile and writes the one place_profile artifact
      and its receipt (D-274): plots/maine/.data/place_profile_profiles.json

  python -m canopy.cli profile maine --place us_census_geoid:23003
      builds one place's profile and prints it; writes nothing

the profile is never a sows run: its values live in many receipts, and a
run's $loam names one artifact (D-163, D-274). ~
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter

from ._common import find_root


def register(subparsers) -> None:
    p = subparsers.add_parser("profile", help="every place's profile, in six parts")
    p.add_argument("plot", help="the plot name, e.g. maine")
    p.add_argument("--place", default=None, metavar="AUTHORITY:CODE",
                   help="build one place's profile and print it, writing nothing")
    p.set_defaults(func=run)


def run(args) -> int:
    root = find_root()
    from canopy.wonder.session import PlotNotFound, open_plot
    from canopy.wonder.profile import (ProfileContext, ProfileUnavailable, build_profile,
                                       build_profiles, write_profiles)
    started = time.monotonic()
    try:
        _vocab, loam, _report = open_plot(args.plot, root=root)
    except PlotNotFound:
        print(f"no plot at plots/{args.plot}", file=sys.stderr)
        return 2

    try:
        if args.place is not None:
            authority, _, code = args.place.partition(":")
            if not authority or not code:
                print(f"--place takes authority:code, e.g. us_census_geoid:23003; "
                      f"got {args.place!r}", file=sys.stderr)
                return 2
            ctx = ProfileContext.open(loam, args.plot, root)
            try:
                profile = build_profile(loam, authority, code, context=ctx)
            except KeyError as e:
                print(e.args[0], file=sys.stderr)
                return 1
            print(json.dumps(profile, indent=2, allow_nan=False))
            return 0
        profiles, ctx = build_profiles(loam, args.plot, root, progress=_progress(started))
        written = write_profiles(profiles, ctx, started=started)
    except ProfileUnavailable as e:
        print(f"no profiles: {e}", file=sys.stderr)
        return 1

    _say(profiles, written)
    return 0


def _progress(started: float, every: int = 50):
    """a line every `every` places and at the last, to stderr, so the
    summary on stdout stays the summary."""
    def say(done: int, total: int) -> None:
        if done % every == 0 or done == total:
            print(f"   ~ {done:,} of {total:,} places, {time.monotonic() - started:,.0f}s",
                  file=sys.stderr, flush=True)
    return say


def _say(profiles: list[dict], written: dict) -> None:
    """what was built, plainly: places by level, verdicts by kind, and
    every receipt the gate kept back."""
    levels = Counter(p["header"]["place"]["level"] for p in profiles)
    verdicts = Counter(e["verdict"]["verdict"] for p in profiles for b in p["barriers"]
                       for e in b["indicators"] if e.get("verdict"))
    print(f"🪞  profiled {written['places']} place(s): "
          + ", ".join(f"{n} {lvl}" for lvl, n in levels.items()))
    print("   verdicts: " + ", ".join(f"{n} {v}" for v, n in sorted(verdicts.items())))
    print(f"   read {len(written['read'])} receipt(s); withheld {len(written['withheld'])} "
          f"at public, whose values never entered:")
    for name in written["withheld"]:
        print(f"     ~ {name}")
    if written["structure_withheld"]:
        print("   the profile's own structure rests on receipts the gate withholds, so the "
              "door will refuse the whole file until they may leave (D-293):")
        for name in written["structure_withheld"]:
            print(f"     ~ {name}")
    print(f"   wrote {written['data']}")
    print(f"   and   {written['receipt']}, in {written['seconds']:,}s")
