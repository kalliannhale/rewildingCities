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

  --to          a target the plot declares in plots/<plot>/publish/targets.yml;
                give it more than once to publish to several
  --adopt ID    with --write and one --to: take a hand-made web map whose layer
                reads this harvest into the record, moving its layer to the
                current version and keeping every style a person gave it
  --replace     with --write: a recorded item that is gone is made again
  --display N   a display copy by name, when it is not the default
                (web for points, web_25m for polygons)

exit codes: 0 every target published, updated, unchanged or a dry run read
through; 1 any target refused or failed; 2 asked wrongly. ~
"""

from __future__ import annotations

import sys

from ._common import find_root


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "publish", help="the publish door: make or move a web map item that reads a "
                        "display copy by URL (a dry run unless --write)")
    p.add_argument("plot", help="the plot name, e.g. maine")
    p.add_argument("artifact", help="the harvest's name, as the canonical command wrote it")
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
    p.set_defaults(func=run)


def _asked_wrongly(args) -> str | None:
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
    from canopy.expose.publish import publish
    from canopy.expose.targets import PublishRefusal
    try:
        outcomes = publish(args.plot, args.artifact, args.targets, root=find_root(),
                           write=args.write, by=(args.by or "").strip() or None,
                           reason=(args.reason or "").strip() or None, adopt=args.adopt,
                           replace=args.replace, display=args.display)
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
