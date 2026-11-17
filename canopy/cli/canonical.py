"""canopy/cli/canonical.py ~ `rewilding canonical`: the canonical write (Contract 2)

  python -m canopy.cli canonical maine --all
      asks the gate about every receipt in the plot and says, for each, whether
      it may leave, why not, and the keys it would be written to. writes
      nothing and needs no AWS: a dry run is the default (EXP-1)

  python -m canopy.cli canonical maine clerk_offices_points_points
      the same, for one receipt

  python -m canopy.cli canonical maine clerk_offices_points_points --write \\
      --by "Kalli A. Hale" --reason "the first canonical write"
      writes it: one artifact at a time, never --all, because a version stays
      readable forever. needs REWILDING_CANONICAL_BUCKET and
      REWILDING_CANONICAL_DOMAIN set in the environment (the bucket's name
      holds the account id, which stays out of the repo, D-301), and the
      rewilding-writer profile in ~/.aws/config (REWILDING_CANONICAL_PROFILE
      names another)

  python -m canopy.cli canonical maine outline_towns_outline --display
      draws the current version's display copy for web maps (Contract 2,
      section 4) from the version's own bytes in the bucket, and asks the gate;
      sends nothing. --write sends it; --tolerance sets the polygons'
      simplification in meters (25 by default). needs the same environment as
      a write, since it reads the bucket

  python -m canopy.cli canonical maine broadband_standardize_standings --display \\
      --join outline_counties_outline
      draws the table's current version on the outline's current version: one
      wide copy, every indicator's columns, keyed by (authority, code), living
      under the table's version and named for the outline's (D-331). --markers
      draws each place as a point on its surface instead of its outline, which
      simplifies nothing. a dry run unless --write

  python -m canopy.cli canonical maine outline_counties_outline --display --local
      draws a copy from the exact bytes a write would send, from the plot's own
      files: needs no AWS and can never write. its sha256 is the one the copy
      drawn from the bucket must print, so nothing permanent happens before the
      whole copy has been drawn, joined and judged once

exit codes: 0 written, already current, or a dry run read through; 1 refused,
or a dry run with a receipt it could not judge; 2 asked wrongly. ~
"""

from __future__ import annotations

import os
import sys

from ._common import find_root


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "canonical", help="write a receipt as a canonical object (a dry run unless --write)")
    p.add_argument("plot", help="the plot name, e.g. maine")
    p.add_argument("artifact", nargs="?", default=None,
                   help="the receipt's name, less .envelope.json")
    p.add_argument("--all", action="store_true",
                   help="a dry run over every receipt in the plot; never writes")
    p.add_argument("--write", action="store_true",
                   help="write it to the canonical bucket; one artifact only")
    p.add_argument("--by", default=None, help="who moves the pointer, by name (with --write)")
    p.add_argument("--reason", default=None,
                   help="why, in plain words: a new vintage, a correction (with --write)")
    p.add_argument("--display", action="store_true",
                   help="draw the current version's display copy for web maps")
    p.add_argument("--tolerance", type=int, default=None,
                   help="with --display: polygon simplification in meters (default 25)")
    p.add_argument("--join", default=None, metavar="OUTLINE",
                   help="with --display: draw this table on an outline harvest (D-331)")
    p.add_argument("--markers", action="store_true",
                   help="with --join: each place as one point on its surface")
    p.add_argument("--local", action="store_true",
                   help="with --display: draw from the plot's own files; a dry run, no AWS")
    p.set_defaults(func=run)


def _asked_wrongly(args) -> str | None:
    if args.all and args.artifact:
        return "give one artifact or --all, not both"
    if not args.all and not args.artifact:
        return "give an artifact's name, or --all for a dry run over every receipt"
    if args.write and args.all:
        return "--write takes one artifact at a time; --all is a dry run only"
    if getattr(args, "display", False) and args.all:
        return "--display takes one artifact at a time"
    if getattr(args, "tolerance", None) is not None and not getattr(args, "display", False):
        return "--tolerance goes with --display"
    display = getattr(args, "display", False)
    if (getattr(args, "join", None) or getattr(args, "local", False)) and not display:
        return "--join and --local go with --display"
    if getattr(args, "markers", False) and not getattr(args, "join", None):
        return "--markers goes with --join"
    if getattr(args, "markers", False) and getattr(args, "tolerance", None) is not None:
        return "--markers simplifies nothing, so it takes no --tolerance"
    if getattr(args, "local", False) and args.write:
        return "--local draws from your own files and never writes; drop --write"
    if getattr(args, "display", False):
        return None                      # a display copy moves no pointer: no --by or --reason
    if args.write and not ((args.by or "").strip() and (args.reason or "").strip()):
        return "--write needs --by and --reason: the pointer says who moved it and why"
    return None


def run(args) -> int:
    problem = _asked_wrongly(args)
    if problem:
        print(f"asked wrongly: {problem}", file=sys.stderr)
        return 2
    from canopy.aws import s3
    try:
        s3.validate_plot(args.plot)
    except s3.CanonicalRefusal as e:
        print(f"refused: {e.reason}", file=sys.stderr)
        return 2
    bucket = os.environ.get(s3.BUCKET_ENV)
    domain = os.environ.get(s3.DOMAIN_ENV)
    local = getattr(args, "local", False)
    if (args.write or getattr(args, "display", False)) and not local and not (bucket and domain):
        print(f"refused: set {s3.BUCKET_ENV} and {s3.DOMAIN_ENV} first "
              f"(conda env config vars set, then reactivate the env)", file=sys.stderr)
        return 2
    root = find_root()

    if args.all:
        return _dry_run_all(s3, root, args.plot)

    if getattr(args, "display", False):
        return _display(s3, root, args, bucket, domain)

    if not args.write:
        ok = _say_one(s3, root, args.plot, args.artifact)
        return 0 if ok else 1

    profile = os.environ.get(s3.PROFILE_ENV) or s3.DEFAULT_PROFILE
    try:
        prepared = s3.prepare(args.plot, args.artifact, root=root)
        result = s3.write(prepared, client=s3.make_client(profile), bucket=bucket,
                          by=args.by, reason=args.reason)
    except s3.CanonicalRefusal as e:
        _say_refusal(args.artifact, e)
        return 1
    _say_written(prepared, result, domain)
    return 0


def _say_refusal(artifact: str, e) -> None:
    print(f"{artifact}  withheld: {e.reason}")
    for r in e.refusals:
        print(f"   rule {r.get('rule')}: {r.get('reason')}")
        print(f"     would admit it: {r.get('would_admit')}")
    if not e.refusals:
        print(f"     would admit it: {e.would_admit}")


def _say_one(s3, root, plot: str, artifact: str) -> bool:
    try:
        p = s3.prepare(plot, artifact, root=root)
    except s3.CanonicalRefusal as e:
        _say_refusal(artifact, e)
        return False
    fmt = p.allow_doc["source"]["format"]
    shown = f"{fmt} to {p.canonical_format}" if fmt != p.canonical_format else fmt
    count = f", {p.features:,} features" if p.features is not None else ""
    print(f"{artifact}  may leave: {shown}{count}, sha256 {p.sha256[:12]}, "
          f"allow record {p.allow_sha256[:12]}")
    print(f"   would write {p.keys['data']}")
    print(f"   and move    {p.keys['current']}")
    return True


def _dry_run_all(s3, root, plot: str) -> int:
    names = s3.list_receipts(root, plot)
    if not names:
        print(f"plots/{plot}/.envelopes holds no receipts", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)   # a saved read keeps its true order
    print(f"a dry run over {len(names)} receipts in {plot}: nothing is written\n")
    may = unjudged = 0
    for name in names:
        try:
            may += _say_one(s3, root, plot, name)
        except Exception as e:           # one receipt's surprise never hides the rest
            unjudged += 1
            said = (str(e).splitlines() or [""])[0][:300]
            print(f"{name}  could not be judged: {type(e).__name__}: {said}")
    withheld = len(names) - may - unjudged
    print(f"\n{may} of {len(names)} may leave; {withheld} withheld; "
          f"{unjudged} could not be judged")
    return 1 if unjudged else 0


def _say_written(p, result, domain: str) -> None:
    base = f"https://{domain}"
    if result["pointer"] == "unchanged" and not result["written"]:
        print(f"{p.harvest}: already current at {p.sha256[:12]}, allow record "
              f"{p.allow_sha256[:12]}; nothing written")
    else:
        print(f"{p.harvest}: version {result['version']}, allow record {result['allow']}, "
              f"pointer {result['pointer']}"
              + (f" (previous {result['previous'][:12]})" if result["previous"] else ""))
        for key in result["written"]:
            print(f"   wrote {key}")
    print(f"\n   read the pointer:  curl -s {base}/{p.keys['current']}")
    if p.data_name.endswith(".parquet"):
        print(f"   read the data:     python -c \"import duckdb; print(duckdb.sql("
              f"\\\"SELECT count(*) AS n FROM read_parquet('{base}/{p.keys['data']}')\\\"))\"")
    else:
        print(f"   read the data:     curl -sI {base}/{p.keys['data']}")


def _display(s3, root, args, bucket: str, domain: str) -> int:
    local = getattr(args, "local", False)
    client = None
    if not local:
        profile = os.environ.get(s3.PROFILE_ENV) or s3.DEFAULT_PROFILE
        client = s3.make_client(profile)
    try:
        p = s3.prepare_display(args.plot, args.artifact, client=client, bucket=bucket,
                               domain=domain, root=root, tolerance_m=args.tolerance,
                               join=getattr(args, "join", None),
                               markers=getattr(args, "markers", False), local=local)
        result = s3.write_display(p, client=client, bucket=bucket) if args.write else None
    except s3.CanonicalRefusal as e:
        _say_refusal(args.artifact, e)
        return 1
    st = p.stats
    print(f"{p.harvest}: display copy '{p.name}' of version {p.sha256[:12]}, "
          f"allow record {p.allow_sha256[:12]}")
    print(f"   {st['feature_count']:,} features, {st['vertices_before']:,} vertices to "
          f"{st['vertex_count']:,}, {st['size_bytes'] / 1_000_000:.1f} MB of GeoJSON")
    if p.joined_to:
        print(f"   drawn on {p.joined_to['harvest']} version {p.joined_to['sha256'][:12]}, "
              f"allow record {p.joined_to['allow'][:12]}")
    for step in p.envelope["provenance"][-1]["publication"]:
        print(f"   {step['step']}: {step['detail']}")
    notes = p.envelope["metadata"].get("context_notes") or []
    print(f"   gate: may leave at public; carries {', '.join(notes) if notes else 'no notes'}")
    print(f"   copy sha256 {p.copy_sha256}")
    if p.local:
        print(f"\n   a local dry run, from your own files: nothing sent, and nothing can be. "
              f"the copy drawn from the bucket must print this same sha256 before its write. "
              f"it would be {p.keys['geojson']}")
        return 0
    url = f"https://{domain}/{p.keys['geojson']}"
    if result is None:
        print(f"\n   a dry run: nothing sent. would write {p.keys['geojson']}")
        return 0
    if result["copy"] == "exists":
        print("\n   already there with these bytes; nothing written")
    else:
        for key in result["written"]:
            print(f"   wrote {key}")
    print(f"\n   add to a web map by URL:  {url}")
    print(f"   check it is served:       curl -sI {url}")
    return 0
