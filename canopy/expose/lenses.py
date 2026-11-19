"""
canopy/expose/lenses.py ~ the lenses: one map of one lane (zip 9b2, D-383 to D-386, D-390)

a lens is a web map the door owns whole, like the places map (D-380), whose
layers read joined display copies by URL, so it holds no features and none of
the places map's headroom (LIMIT-1). this module reads what a lens draws;
canopy/expose/targets/arcgis_lens.py builds it; canopy/expose/publish.py
publishes it.

  load_indicators(root)        every indicator seeds/indicators/ declares, by id
  pillar_chain(root, weights)  {indicator: pillar} for every CII indicator whose
                               replicates.column is a published measure's
                               derivation.column, placed by the weights seed
                               (D-383): CII's membership, read, never typed
  load_lanes(root)             the lanes of seeds/crosswalks/pillars/, each with
                               its members and how each was placed
  load_plan(plot_dir)          plots/<plot>/publish/lenses.yml: each level's
                               outline, values tables and tolerance, and the
                               orientation copy
  read_lens(plot, lane, ...)   every layer a lens draws, read through CloudFront
                               and checked as the door checks any copy; what is
                               not yet drawn is named with the command that draws it

a lens reads, for each table, the copy holding its lane's columns alone
(D-396), sent compressed (D-397); the table's full copy is read only as the
index of which indicators it holds. a lens never draws a count and never a standing (D-365, D-75, D-385): a
pillar's count (CII's own total of news outlets) is named and kept in the
profile, and a lane of ours may hold no count at all. an empty lens holds the
orientation copy and says so. ~
"""

from __future__ import annotations

from pathlib import Path

import yaml

from canopy.expose.targets import PublishRefusal

LANES_DIR = ("seeds", "crosswalks", "pillars")
LANES_FILE = "cii_2026_lanes.yml"
PLAN_FILE = "lenses.yml"
KINDS = ("pillar", "ours")
COUNT_UNITS = ("count", "persons", "households")
LEVEL_WORDS = {"state": "State", "county": "Counties", "sldu": "Senate districts",
               "sldl": "House districts", "cousub": "Towns", "aiannh": "Census tribal areas"}


# ── the seeds ────────────────────────────────────────────────────────────────
def load_indicators(root: str | Path) -> dict:
    """every indicator in seeds/indicators/*.yml, by id. an id declared twice is
    refused, since a lens could not say which one it draws."""
    out, where = {}, {}
    for path in sorted((Path(root) / "seeds" / "indicators").glob("*.yml")):
        doc = yaml.safe_load(path.read_text()) or {}
        for ind, body in (doc.get("indicators") or {}).items():
            if ind in out:
                raise PublishRefusal(f"indicator '{ind}' is declared in both {where[ind]} "
                                     f"and {path.name}", "declare it once")
            out[ind], where[ind] = dict(body or {}), path.name
    return out


def is_count(unit: str | None) -> bool:
    """a count of people, households or things: coloured on a map, it mostly
    shows where people live, so a lens never draws one (D-385). a share, a
    rate, a score, a number of years or of days is drawn."""
    u = str(unit or "")
    return not u or u in COUNT_UNITS or u.startswith("count")


def load_weights(root: str | Path, weights_id: str) -> dict:
    path = Path(root) / "seeds" / "weights" / f"{weights_id}.yml"
    if not path.is_file():
        raise PublishRefusal(f"the weights seed '{weights_id}' is not in seeds/weights",
                             "name a weights seed that holds CII's pillars")
    return yaml.safe_load(path.read_text()) or {}


def pillar_chain(root: str | Path, weights_id: str, indicators: dict | None = None) -> dict:
    """{indicator: pillar} for every indicator that replicates a published
    measure the weights seed places in a pillar (D-383). an indicator whose
    column matches measures in two pillars is refused: CII places each of its
    measures in one."""
    indicators = indicators if indicators is not None else load_indicators(root)
    weights = load_weights(root, weights_id)
    pillar_of = {}
    for pillar, body in (weights.get("pillars") or {}).items():
        for measure in (body or {}).get("components") or {}:
            pillar_of[measure] = pillar
    by_column: dict = {}
    for ind, body in indicators.items():
        column = ((body.get("derivation") or {}).get("column"))
        if ind in pillar_of and column:
            by_column.setdefault(column, set()).add(pillar_of[ind])
    chain = {}
    for ind, body in indicators.items():
        column = (body.get("replicates") or {}).get("column")
        if not column or column not in by_column:
            continue
        pillars = by_column[column]
        if len(pillars) != 1:
            raise PublishRefusal(f"'{ind}' replicates a column placed in {len(pillars)} pillars "
                                 f"({', '.join(sorted(pillars))})",
                                 "read CII's own file: it places each measure in one")
        chain[ind] = next(iter(pillars))
    return chain


def load_lanes(root: str | Path) -> dict:
    """{lane: {kind, name, role, members: {indicator: {placed_by, reason}}}}.
    a pillar's members come from the chain; ours are the seed's own rows."""
    path = Path(root).joinpath(*LANES_DIR) / LANES_FILE
    if not path.is_file():
        raise PublishRefusal(f"{'/'.join(LANES_DIR)}/{LANES_FILE} is missing",
                             "run this from the rewildingCities repo root")
    doc = yaml.safe_load(path.read_text()) or {}
    indicators = load_indicators(root)
    weights = load_weights(root, doc["weights"])
    chain = pillar_chain(root, doc["weights"], indicators)
    lanes = {}
    for lane, body in (doc.get("lanes") or {}).items():
        body = body or {}
        kind = body.get("kind")
        if kind not in KINDS:
            raise PublishRefusal(f"lane '{lane}' is of kind {kind!r}", f"one of {', '.join(KINDS)}")
        if kind == "pillar":
            pillar = (weights.get("pillars") or {}).get(lane)
            if pillar is None:
                raise PublishRefusal(f"lane '{lane}' is no pillar of {doc['weights']}",
                                     "name a pillar the weights seed holds")
            members = {ind: {"placed_by": "replicates",
                             "reason": f"CII places the measure it replicates in {pillar['name']}"}
                       for ind, p in sorted(chain.items()) if p == lane}
            lanes[lane] = {"kind": kind, "name": pillar["name"], "role": None,
                           "defined_by": "cii_2026", "members": members}
        else:
            members = {ind: {"placed_by": "rewildingcities",
                             "reason": " ".join(str((row or {}).get("reason") or "").split())}
                       for ind, row in (body.get("members") or {}).items()}
            lanes[lane] = {"kind": kind, "name": body.get("name") or lane,
                           "role": body.get("role"), "defined_by": "rewildingcities",
                           "members": members}
    return lanes


def load_plan(plot_dir: str | Path) -> dict:
    path = Path(plot_dir) / "publish" / PLAN_FILE
    if not path.is_file():
        raise PublishRefusal(f"the plot declares no lenses ({path.name} is missing)",
                             f"write plots/<plot>/publish/{PLAN_FILE}")
    doc = yaml.safe_load(path.read_text()) or {}
    if not doc.get("levels") or not doc.get("orientation"):
        raise PublishRefusal(f"{path.name} names no levels or no orientation copy",
                             "name each level's outline and tables, and the orientation outline")
    return doc


# ── the bucket ───────────────────────────────────────────────────────────────
def _cached(fetch):
    """one fetch per URL for a whole lens: a joined copy holds every indicator of
    its table, and a lens draws several from one copy."""
    seen: dict = {}

    def get(url):
        if url not in seen:
            seen[url] = fetch(url)
        return seen[url]
    return get


def read_lens(plot: str, lane: str, *, domain: str, root: str | Path, fetch) -> dict:
    """every layer the lens draws, by level in the plan's order: for each table
    the plan lists, the members of this lane its joined copy holds. a table not
    yet written, or written but not yet drawn on its outline's current version,
    is named in `missing` with the command that draws it; a lens with any
    missing is never written (LENS-1)."""
    from canopy.aws import display, s3
    from canopy.choropleth import column_name
    from canopy.expose import publish as door
    s3.validate_plot(plot)
    lanes = load_lanes(root)
    if lane not in lanes:
        raise PublishRefusal(f"no lane '{lane}' in {LANES_FILE}", f"one of {', '.join(lanes)}")
    the = lanes[lane]
    indicators = load_indicators(root)
    counts = [ind for ind in the["members"] if is_count((indicators.get(ind) or {}).get("unit"))]
    if counts and the["kind"] == "ours":
        raise PublishRefusal(f"{', '.join(counts)} {'is a count' if len(counts) == 1 else 'are counts'}"
                             f", and a lane of ours holds none (D-385)",
                             "name a share or a rate in the lanes seed; keep counts in the profile")
    plot_dir = Path(root) / "plots" / plot
    plan = load_plan(plot_dir)
    base = f"https://{domain}"
    get = _cached(fetch)
    levels, parents, missing, judged = [], [], [], []
    for level, spec in plan["levels"].items():
        outline = spec["outline"]
        try:
            o = door._current(get, base, plot, outline)
        except PublishRefusal:
            missing.append(f"{outline} is not written: canonical {plot} {outline} --write")
            continue
        tol = int(spec.get("tolerance") or plan.get("tolerance") or display.DEFAULT_TOLERANCE_M)
        name = display.joined_name(outline, o["sha256"], tolerance_m=tol)
        layers = []
        for table in spec.get("tables") or []:
            at = f" --tolerance {tol}" if tol != display.DEFAULT_TOLERANCE_M else ""
            draw = f"canonical {plot} {table} --display --join {outline}{at} --write"
            try:
                t = door._current(get, base, plot, table)
            except PublishRefusal:
                missing.append(f"{table} is not written: canonical {plot} {table} --write, "
                               f"then {draw}")
                continue
            env = door._json(get, f"{base}/{s3.display_keys(plot, table, t['sha256'], name)['envelope']}")
            if env is None:
                missing.append(f"{table} is not drawn on {outline}'s current version "
                               f"{o['sha256'][:12]}: {draw}")
                continue
            held = ((env.get("metadata") or {}).get("join") or {}).get("indicators") or []
            only = sorted(i for i in the["members"] if i in held and i not in counts)
            if not only:
                continue
            # the full copy is the index of what the table holds; the lens reads
            # its lane's slim copy, which carries those columns alone (D-396)
            slim = display.joined_name(outline, o["sha256"], tolerance_m=tol, only=only)
            if door._json(get, f"{base}/{s3.display_keys(plot, table, t['sha256'], slim)['envelope']}") is None:
                missing.append(f"{table}'s lens copy for {', '.join(only)} is not drawn on "
                               f"{outline}: canonical {plot} {table} --display --join {outline}"
                               f"{at} --only {','.join(only)} --write")
                continue
            drawn = []
            for ind in the["members"]:
                if ind not in only:
                    continue
                copy = door.read_copy(plot, table, domain=domain, fetch=get, join=outline,
                                      indicator=ind, display=slim)
                columns = ((copy["display_env"].get("metadata") or {}).get("join") or {}) \
                    .get("columns") or {}
                if column_name(ind, "percentile") in (columns.get(ind) or []):
                    raise PublishRefusal(f"{table} holds a standing of {ind}, and a lens "
                                         f"never draws a standing (D-365, D-75)",
                                         f"take {table} out of {PLAN_FILE}")
                copy["level"] = level
                drawn.append(copy)
            if drawn:
                layers.extend(drawn)
                judged.append(drawn[0])
                parents.append({"role": f"{level} {table}", "harvest": table,
                                "sha256": t["sha256"], "allow": t["allow"], "copy": slim,
                                "url": drawn[0]["url"], "allow_doc": t["allow_doc"],
                                "env": drawn[0]["display_env"],
                                "outline": {"harvest": outline, "sha256": o["sha256"],
                                            "allow": o["allow"]}})
        if layers:
            levels.append({"level": level, "label": LEVEL_WORDS.get(level, level),
                           "layers": layers})
    orientation = None
    if not levels and not missing:
        orientation = door.read_copy(plot, plan["orientation"], domain=domain, fetch=get,
                                     display="markers")
        judged.append(orientation)
        parents.append({"role": "orientation", "harvest": plan["orientation"],
                        "sha256": orientation["sha256"], "allow": orientation["allow"],
                        "copy": "markers", "url": orientation["url"],
                        "allow_doc": orientation["allow_doc"], "env": orientation["display_env"],
                        "outline": None})
    return {"plot": plot, "lane": lane, "name": the["name"], "kind": the["kind"],
            "defined_by": the["defined_by"], "members": the["members"],
            "title": f"{the['name']}: a lens on the {plot} plot ({plot})",
            "levels": levels, "orientation": orientation, "parents": parents,
            "judged": judged, "missing": missing, "counts": counts, "domain": domain}


def lens_key(lane: str) -> str:
    """the record's key for a lens (D-385)."""
    return f"lens/{lane}"


def describe_members(lens: dict) -> list[str]:
    """each member in plain words: how it was placed and why."""
    out = []
    for ind, m in lens["members"].items():
        who = ("placed by CII's own file" if m["placed_by"] == "replicates"
               else "placed by rewildingCities")
        out.append(f"{ind}: {who}. {m['reason']}")
    return out
