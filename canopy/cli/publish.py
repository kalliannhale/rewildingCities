"""canopy/cli/publish.py ~ `rewilding publish`: the publish door (Sprint 08)

  python -m canopy.cli publish maine clerk_offices_points_points --to test
      a dry run: reads the harvest's current version, its allow record and
      its display copy by public URL, asks the gate at the target's sharing
      level, and says what the door owes the target. signs in nowhere and
      writes nothing. needs REWILDING_CANONICAL_DOMAIN, and no AWS at all

  python -m canopy.cli publish maine clerk_offices_points_points --to test \\
      --write --by "Kalli A. Hale" --reason "the door's first item"
      does it: asks for the owner's password once per portal (typed, never
      stored), checks who the portal says that is, reads the item as it
      stands, makes or moves it, then writes plots/maine/publish/published.yml

  python -m canopy.cli publish maine broadband_standardize_standings --to test \\
      --join outline_counties_outline --indicator cii_broadband
      a choropleth: the table drawn on the outline's current version, one
      indicator coloured by the door's own classBreaks renderer (D-331). a new
      version or allow record of either parent is owed

  python -m canopy.cli publish maine --check
      signs in and reads every recorded item against the record, writing
      nothing (DOORCHECK-1); --to narrows it to those targets

  --to          a target the plot declares in plots/<plot>/publish/targets.yml;
                give it more than once to publish to several
  --adopt ID    with --write and one --to: take a hand-made web map whose layer
                reads this harvest into the record, moving its layer to the
                current version and keeping every style a person gave it
  --replace     with --write: a recorded item that is gone is made again
  --display N   a display copy by name, when it is not the default
                (web for points, web_25m for polygons)
  --join O      with --indicator: draw the table on outline harvest O
  --indicator I the one indicator a choropleth colours
  --markers     with --join: the copy drawn as one marker per place
  --check       read every recorded item, write nothing

exit codes: 0 every target published, updated, unchanged or a dry run read
through (with --check: every item as recorded); 1 any target refused or
failed, or an item that differs; 2 asked wrongly. ~
"""

from __future__ import annotations

import sys

from ._common import find_root


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "publish", help="the publish door: make or move a web map item that reads a "
                        "display copy by URL (a dry run unless --write)")
    p.add_argument("plot", help="the plot name, e.g. maine")
    p.add_argument("artifact", nargs="?", default=None,
                   help="the harvest's name, as the canonical command wrote it")
    p.add_argument("--to", action="append", default=[], dest="targets",
                   help="a target from the plot's publish/targets.yml; repeatable")
    p.add_argument("--write", action="store_true", help="sign in and write")
    p.add_argument("--by", default=None, help="who publishes, by name (with --write)")
    p.add_argument("--reason", default=None, help="why, in plain words (with --write)")
    p.add_argument("--adopt", default=None, metavar="ITEM_ID",
                   help="take a hand-made web map into the record (with --write, one --to)")
    p.add_argument("--replace", action="store_true",
                   help="make a recorded item again if it is gone (with --write)")
    p.add_argument("--display", default=None, help="the display copy's name, if not the default")
    p.add_argument("--join", default=None, metavar="OUTLINE",
                   help="draw the table on this outline harvest (with --indicator)")
    p.add_argument("--indicator", default=None, help="the one indicator a choropleth colours")
    p.add_argument("--markers", action="store_true",
                   help="with --join: the copy drawn as one marker per place")
    p.add_argument("--check", action="store_true",
                   help="read every recorded item against the record; writes nothing")
    p.set_defaults(func=run)


def _asked_wrongly(args) -> str | None:
    if getattr(args, "check", False):
        if args.artifact:
            return "--check reads every recorded item; it takes no artifact"
        if args.write or args.adopt or args.replace or getattr(args, "join", None):
            return "--check only reads; it takes no --write, --adopt, --replace or --join"
        return None
    if not args.artifact:
        return "name the harvest to publish, or --check"
    if getattr(args, "join", None) and not getattr(args, "indicator", None):
        return "--join draws one indicator; name it with --indicator"
    if (getattr(args, "indicator", None) or getattr(args, "markers", False)) \
            and not getattr(args, "join", None):
        return "--indicator and --markers go with --join"
    if not args.targets:
        return "name at least one target with --to"
    if len(set(args.targets)) != len(args.targets):
        return "a target is named twice"
    if args.write and not ((args.by or "").strip() and (args.reason or "").strip()):
        return "--write needs --by and --reason: the record says who published and why"
    if args.adopt and not args.write:
        return "--adopt writes, so it goes with --write"
    if args.adopt and len(args.targets) != 1:
        return "--adopt names one item, in one target"
    if args.replace and not args.write:
        return "--replace goes with --write"
    return None


def run(args) -> int:
    problem = _asked_wrongly(args)
    if problem:
        print(f"asked wrongly: {problem}", file=sys.stderr)
        return 2
    from canopy.aws.s3 import CanonicalRefusal
    from canopy.expose.publish import check, publish
    from canopy.expose.targets import PublishRefusal
    if getattr(args, "check", False):
        try:
            outcomes = check(args.plot, args.targets, root=find_root())
        except PublishRefusal as e:
            print(f"check refused: {e.reason}", file=sys.stderr)
            print(f"   would admit it: {e.would_admit}", file=sys.stderr)
            return 1
        if not outcomes:
            print("the record holds no items")
            return 0
        bad = 0
        for o in outcomes:
            print(f"{o.target}: {o.outcome}")
            for line in o.lines:
                print(f"   {line}")
            bad += o.outcome != "as recorded"
        print(f"\n{len(outcomes) - bad} of {len(outcomes)} items as recorded; "
              f"nothing was written")
        return 1 if bad else 0
    try:
        outcomes = publish(args.plot, args.artifact, args.targets, root=find_root(),
                           write=args.write, by=(args.by or "").strip() or None,
                           reason=(args.reason or "").strip() or None, adopt=args.adopt,
                           replace=args.replace, display=args.display,
                           join=getattr(args, "join", None),
                           indicator=getattr(args, "indicator", None),
                           markers=getattr(args, "markers", False))
    except (PublishRefusal, CanonicalRefusal) as e:
        print(f"{args.artifact}  refused: {e.reason}", file=sys.stderr)
        print(f"   would admit it: {e.would_admit}", file=sys.stderr)
        return 1
    bad = 0
    for o in outcomes:
        print(f"{args.artifact} to {o.target}: {o.outcome}")
        for line in o.lines:
            print(f"   {line}")
        bad += o.outcome in ("refused", "failed")
    if len(outcomes) > 1:
        print(f"\n{len(outcomes) - bad} of {len(outcomes)} targets went through; "
              f"{bad} refused or failed")
    return 1 if bad else 0
