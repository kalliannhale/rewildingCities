"""
canopy/loam/graph.py

graph ~ the plot's part of the weighted graph, readable in its own bed

Contract 3 keeps the graph as two tables a preparation writes, places and
edges. loam does not copy them (D-168): it holds no truth of its own, and a
copied value would leave through Loam.snapshot() without ever meeting the
gate. so loam makes two VIEWS over the files its receipts point at, and a
reader asks the bed `SELECT ... FROM places` as if the table lived there.

a view is made only when it can be trusted:

  ~ exactly one tended or gathered artifact of the type, as $loam. asks (D-163)
  ~ its receipt declares the key that names a row (KEYS-1)
  ~ the file is on disk and carries every declared key column

otherwise there is no view, and the report says why. a plot with no graph
(nyc, delton) still opens; it simply has no places to read. nothing here
writes a file, and a rebuilt bed makes the same views from the same
receipts, because there is nothing stored to drift. ~

values join the graph the same way (plan build 2):

  ~ indicator_values  every tended indicator_values receipt whose file carries
                  the key (unit_authority, unit_code, indicator, time), D-169.
                  several are expected (towns, counties, districts), so D-163's
                  one-artifact rule does not apply; a receipt missing a key
                  column is left out by name. a key two tables both give is one
                  fact when they agree (value, moe and households within 1e-9),
                  kept once with every receipt that says it; when they disagree
                  there is no view, naming the receipts that do (D-172). every
                  row names the receipt it was read from
  ~ place_values      values joined to places by (unit_authority, unit_code), so a
                  value's level is its place's, never its own (D-169). every
                  row says whether it attached and, if not, why: no place, no
                  declared rule for its publisher, a Census tribal area (D-171),
                  boundaries that differ (D-170), or attached but unchecked, for
                  a statistical area whose vintage the rule cannot confirm

the rule for boundaries is a seed, seeds/vintages/boundaries.yml (D-170),
read here and written into the view, so the view says the rule it applied. ~

and the plot's own places (plan build 3, D-174):

  ~ plot_places   the places this plot answers for, each with the reason it
                  is included. a manifest that declares none answers for every
                  place in its graph. a declared entry is one place, or one
                  place `with: contained` (and all it contains, followed down
                  contains edges), or `with: touching` (and all it overlaps).
                  a key that is not a place, or an entry of any other shape,
                  means no view, naming it: a plot never claims a place the
                  graph does not hold

and where carriers stand (CMAP-1, D-225):

  ~ located_in    every located_in_edges receipt whose file carries the edge
                  key, unioned, every row naming its receipt (LOC-VIEW-1).
                  one receipt per layer is expected; a layer label two
                  receipts both give means no view, naming them, since which
                  one is a choice, not a lookup (D-163)
  ~ carriers      one row per placed point of every carrier indicator whose
                  derivation is located_count (D-223): the indicator, the
                  type it counts, the layer, the point's id, name and
                  coordinates. the points are found the way the orchestrator
                  checks them before a run (D-224): the edges receipt's own
                  record reads exactly one input of the counted type, and its
                  path is the points file. a point's places are its rows in
                  located_in. an indicator whose points cannot be found this
                  way is left out by name, and the view is made from the rest
"""

from __future__ import annotations

from pathlib import Path

import yaml

CONFORMED_TIERS = ("tended", "gathered")

# the view's name in the bed, and the semantic type that fills it
GRAPH_VIEWS = {"places": "places", "edges": "place_edges"}

EDGE_KEY = ["from_authority", "from_code", "to_authority", "to_code"]
LOCATED_TYPE = "located_in_edges"
INDICATORS = Path("seeds") / "indicators"

VALUE_TYPE = "indicator_values"
VALUE_KEY = ["unit_authority", "unit_code", "indicator", "time"]
BOUNDARY_RULES = Path("seeds") / "vintages" / "boundaries.yml"


def _quoted(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def _reader(path: Path) -> str:
    if path.suffix == ".parquet":
        return f"read_parquet({_quoted(path)})"
    return f"read_csv_auto({_quoted(path)}, all_varchar=true)"


def _sql_text(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _sql_list(values) -> str:
    return "(" + ", ".join(_sql_text(v) for v in values) + ")" if values else "(NULL)"


def _boundary_rules(root: Path) -> dict:
    path = root / BOUNDARY_RULES
    if not path.is_file():
        return {}
    return (yaml.safe_load(path.read_text()) or {}).get("publishers") or {}


def _plant_values(loam, plot: str, root: Path, report: dict) -> None:
    loam.con.execute("DROP VIEW IF EXISTS place_values")
    loam.con.execute("DROP VIEW IF EXISTS indicator_values")
    loam.con.execute("DROP VIEW IF EXISTS indicator_value_rows")
    rows = [r for tier in CONFORMED_TIERS
            for r in loam.find(semantic_type=VALUE_TYPE, plot=plot, tier=tier)]
    if not rows:
        report["indicator_values"] = {"made": False, "why": f"no run in plot '{plot}' has made {VALUE_TYPE}"}
        report["place_values"] = {"made": False, "why": "there are no values to attach"}
        return

    included, left_out = [], []
    for row in sorted(rows, key=lambda r: r["receipt_path"] or ""):
        receipt = Path(row["receipt_path"] or "?").name
        path = Path(row["data_path"])
        path = path if path.is_absolute() else root / path
        if not path.is_file():
            left_out.append(f"{receipt}: {row['data_path']} is not on disk")
            continue
        columns = [d[0] for d in loam.con.execute(
            f"SELECT * FROM {_reader(path)} LIMIT 0").description]
        missing = [k for k in VALUE_KEY if k not in columns]
        if missing:
            left_out.append(f"{receipt}: its file has no {', '.join(missing)} (D-169)")
            continue
        included.append((receipt, path))

    if not included:
        report["indicator_values"] = {"made": False, "left_out": left_out,
                            "why": "no value receipt carries the key (D-169)"}
        report["place_values"] = {"made": False, "why": "there are no values to attach"}
        return

    union = " UNION ALL BY NAME ".join(
        f"SELECT * REPLACE (CAST(unit_code AS VARCHAR) AS unit_code, CAST(time AS VARCHAR) AS time), "
        f"{_sql_text(receipt)} AS value_receipt FROM {_reader(path)}" for receipt, path in included)
    loam.con.execute(f"CREATE VIEW indicator_value_rows AS {union}")
    row_columns = [d[0] for d in loam.con.execute(
        "SELECT * FROM indicator_value_rows LIMIT 0").description]
    key = ", ".join(VALUE_KEY)

    # D-172: two receipts agree on a key when every compared field matches
    def same(column: str) -> str:
        a, b = f"TRY_CAST(a.{column} AS DOUBLE)", f"TRY_CAST(b.{column} AS DOUBLE)"
        # a missing number may be null or NaN depending on who wrote the file;
        # both mean "none", and two nones agree
        none_a, none_b = f"({a} IS NULL OR isnan({a}))", f"({b} IS NULL OR isnan({b}))"
        return f"(({none_a} AND {none_b}) OR abs({a} - {b}) <= 1e-9)"
    compared = [c for c in ("value", "moe", "households") if c in row_columns]
    agree = " AND ".join(same(c) for c in compared) or "TRUE"
    disagreeing = loam.con.execute(
        f"SELECT a.value_receipt, b.value_receipt, {', '.join('a.' + k for k in VALUE_KEY)} "
        f"FROM indicator_value_rows a JOIN indicator_value_rows b USING ({key}) "
        f"WHERE a.value_receipt < b.value_receipt AND NOT ({agree})").fetchall()
    if disagreeing:
        loam.con.execute("DROP VIEW indicator_value_rows")
        pairs = sorted({(r[0], r[1]) for r in disagreeing})
        example = disagreeing[0][2:]
        report["indicator_values"] = {
            "made": False, "left_out": left_out,
            "why": (f"{len(disagreeing)} key(s) carry different values in "
                    f"{'; '.join(f'{a} and {b}' for a, b in pairs)}, e.g. "
                    f"{', '.join(str(v) for v in example)}; which value stands is a "
                    f"choice, not a lookup (D-172)")}
        report["place_values"] = {"made": False, "why": "there are no values to attach"}
        return

    loam.con.execute(f"""
        CREATE VIEW indicator_values AS
        SELECT * EXCLUDE (kept) FROM (
            SELECT r.*,
                row_number() OVER (PARTITION BY {key} ORDER BY value_receipt) AS kept,
                array_to_string(list_sort(list(value_receipt) OVER (PARTITION BY {key})), ', ')
                    AS recorded_in
            FROM indicator_value_rows r)
        WHERE kept = 1""")
    count = loam.con.execute("SELECT COUNT(*) FROM indicator_values").fetchone()[0]
    read = loam.con.execute("SELECT COUNT(*) FROM indicator_value_rows").fetchone()[0]
    agreed = sorted({r[0] for r in loam.con.execute(
        "SELECT recorded_in FROM indicator_values WHERE recorded_in LIKE '%, %'").fetchall()})
    report["indicator_values"] = {"made": True, "receipts": [r for r, _ in included],
                                  "left_out": left_out, "key": VALUE_KEY, "rows": count,
                                  "collapsed": read - count, "agreeing": agreed}

    if not (report.get("places") or {}).get("made"):
        report["place_values"] = {"made": False, "why": "there are no places to attach values to"}
        return
    _plant_place_values(loam, root, report)


def _plant_place_values(loam, root: Path, report: dict) -> None:
    rules = _boundary_rules(root)
    acs = rules.get("us_census_acs") or {}
    levels = acs.get("levels") or {}
    publishers = [name for name, rule in rules.items()
                  if (rule or {}).get("boundary_year") == "final_year_of_time"]
    ruled_levels = list(levels)
    statistical = acs.get("statistical_funcstat") or []
    decennial = str(acs.get("decennial_year") or "")
    # an empty list must never read as "no objection": with no publisher or
    # level declared, every value is unruled, said as plainly as SQL allows
    value_columns = [d[0] for d in loam.con.execute(
        "SELECT * FROM indicator_values LIMIT 0").description]
    unruled = ("TRUE" if not publishers or not ruled_levels
               or "published_by" not in value_columns else
               f"COALESCE(v.published_by, '') NOT IN {_sql_list(publishers)} "
               f"OR p.level NOT IN {_sql_list(ruled_levels)}")
    # the statistical class is the ACS's own rule (its decennial boundaries), so
    # it judges only the ACS's values: a count made over the graph's own places
    # sits on the place's boundaries by construction (D-209)
    acs_only = ("COALESCE(v.published_by, '') = 'us_census_acs' AND "
                if "published_by" in value_columns else "")
    is_statistical = ("FALSE" if not statistical else
                      f"{acs_only}p.level = 'cousub' AND COALESCE(p.census_funcstat, '') "
                      f"IN {_sql_list(statistical)}")
    final_year = "regexp_extract(v.time, '.*([0-9]{4})', 1)"

    loam.con.execute(f"""
        CREATE VIEW place_values AS
        SELECT *,
            status IN ('attached', 'unchecked_statistical') AS attached,
            CASE status
                WHEN 'no_place' THEN 'no place in the graph has this key'
                WHEN 'no_rule' THEN 'no declared rule says which boundaries this '
                    || 'publisher''s values sit on at this level (D-170)'
                WHEN 'tribal_area' THEN 'ACS estimates for this tribal area are on '
                    || boundary_year || ' boundaries; the graph holds the Census '
                    || place_vintage || ' legal area, so they are not shown (D-171, TRIBE-6)'
                WHEN 'unchecked_statistical' THEN 'a statistical area: the ACS uses the '
                    || {_sql_text(decennial)} || ' Census boundaries, which the '
                    || place_vintage || ' layer is expected to carry unchanged; not yet '
                    || 'verified (D-170)'
                WHEN 'vintage_mismatch' THEN 'the value is on ' || boundary_year
                    || ' boundaries and the place on ' || place_vintage || ' (D-170)'
            END AS why
        FROM (
            SELECT v.*, p.level, p.kind AS place_kind, p.name AS place_name,
                p.vintage AS place_vintage, p.census_funcstat,
                {final_year} AS boundary_year,
                CASE
                    WHEN p.code IS NULL THEN 'no_place'
                    WHEN p.level = 'aiannh' THEN 'tribal_area'
                    WHEN {unruled} THEN 'no_rule'
                    WHEN {is_statistical} THEN 'unchecked_statistical'
                    WHEN {final_year} = CAST(p.vintage AS VARCHAR) THEN 'attached'
                    ELSE 'vintage_mismatch'
                END AS status
            FROM indicator_values v
            LEFT JOIN places p
                ON p.authority = v.unit_authority AND CAST(p.code AS VARCHAR) = v.unit_code
        )""")
    counts = dict(loam.con.execute(
        "SELECT status, COUNT(*) FROM place_values GROUP BY status ORDER BY status").fetchall())
    report["place_values"] = {"made": True, "by_status": counts,
                              "rule": str(BOUNDARY_RULES) if rules else None}


PLACE_RULES = ("contained", "touching")


def _declared_entries(declared) -> tuple[list[tuple[str, str, str]], list[str]]:
    """the declaration's entries as (authority, code, rule), and every way it
    is malformed. rule is self, contained or touching."""
    if not isinstance(declared, list) or not declared:
        return [], ["places: must be a non-empty list of place keys (D-174)"]
    entries, problems = [], []
    for i, entry in enumerate(declared):
        if not isinstance(entry, dict):
            problems.append(f"places[{i}] is not a place key: {entry!r}")
            continue
        extra = sorted(set(entry) - {"authority", "code", "with"})
        rule = entry.get("with", "self")
        if not entry.get("authority") or entry.get("code") in (None, ""):
            problems.append(f"places[{i}] names no authority and code: {entry!r}")
        elif extra:
            problems.append(f"places[{i}] carries {', '.join(extra)}, which a place key does not")
        elif rule != "self" and rule not in PLACE_RULES:
            problems.append(f"places[{i}] says with: {rule!r}; a place is taken with "
                            f"{' or '.join(PLACE_RULES)}, or alone")
        else:
            entries.append((str(entry["authority"]), str(entry["code"]), rule))
    return entries, problems


def _plant_plot_places(loam, declared, report: dict) -> None:
    loam.con.execute("DROP VIEW IF EXISTS plot_places")
    if not (report.get("places") or {}).get("made"):
        report["plot_places"] = {"made": False, "why": "there are no places to choose from"}
        return
    if declared is None:
        loam.con.execute("CREATE VIEW plot_places AS SELECT *, "
                         "'every place in the graph; the manifest declares none' AS included_by "
                         "FROM places")
        count = loam.con.execute("SELECT COUNT(*) FROM plot_places").fetchone()[0]
        report["plot_places"] = {"made": True, "declared": False, "rows": count}
        return

    entries, problems = _declared_entries(declared)
    if entries:
        known = {(a, c) for a, c in loam.con.execute(
            "SELECT authority, CAST(code AS VARCHAR) FROM places").fetchall()}
        problems += [f"{a} {c} is not a place in this plot's graph"
                     for a, c, _ in entries if (a, c) not in known]
    if problems:
        report["plot_places"] = {"made": False, "why": "; ".join(problems)}
        return

    rows = ", ".join(f"({_sql_text(a)}, {_sql_text(c)}, {_sql_text(r)})" for a, c, r in entries)
    edges_made = (report.get("edges") or {}).get("made")
    follow_contains = ("" if not edges_made else """
            UNION
            SELECT CAST(e.to_authority AS VARCHAR), CAST(e.to_code AS VARCHAR), c.root
            FROM edges e JOIN contained c
                ON e.from_authority = c.authority AND CAST(e.from_code AS VARCHAR) = c.code
            WHERE e.kind = 'contains'""")
    touching = ("" if not edges_made else """
        UNION ALL
        SELECT CAST(e.from_authority AS VARCHAR), CAST(e.from_code AS VARCHAR),
            'touching ' || d.authority || ' ' || d.code
        FROM edges e JOIN declared d
            ON e.to_authority = d.authority AND CAST(e.to_code AS VARCHAR) = d.code
        WHERE d.rule = 'touching' AND e.kind = 'overlaps'
        UNION ALL
        SELECT CAST(e.to_authority AS VARCHAR), CAST(e.to_code AS VARCHAR),
            'touching ' || d.authority || ' ' || d.code
        FROM edges e JOIN declared d
            ON e.from_authority = d.authority AND CAST(e.from_code AS VARCHAR) = d.code
        WHERE d.rule = 'touching' AND e.kind = 'overlaps'""")
    loam.con.execute(f"""
        CREATE VIEW plot_places AS
        WITH RECURSIVE
        declared(authority, code, rule) AS (VALUES {rows}),
        contained(authority, code, root) AS (
            SELECT authority, code, authority || ' ' || code FROM declared
            WHERE rule = 'contained'{follow_contains}
        ),
        reasons(authority, code, why) AS (
            SELECT authority, code, 'declared' FROM declared WHERE rule = 'self'
            UNION ALL
            SELECT authority, code, 'declared, with what it overlaps' FROM declared
            WHERE rule = 'touching'
            UNION ALL
            SELECT authority, code,
                CASE WHEN authority || ' ' || code = root THEN 'declared, with what it contains'
                     ELSE 'contained in ' || root END
            FROM contained{touching}
        ),
        included AS (
            SELECT authority, code,
                array_to_string(list_sort(list(DISTINCT why)), '; ') AS included_by
            FROM reasons GROUP BY authority, code
        )
        SELECT p.*, i.included_by
        FROM places p JOIN included i
            ON p.authority = i.authority AND CAST(p.code AS VARCHAR) = i.code""")
    count = loam.con.execute("SELECT COUNT(*) FROM plot_places").fetchone()[0]
    report["plot_places"] = {"made": True, "declared": True, "entries": len(entries),
                             "rows": count,
                             **({} if edges_made or all(r == "self" for *_, r in entries)
                                else {"note": "there are no edges, so contained and touching "
                                              "reach only the declared places themselves"})}


def _on_disk(root: Path, path: str | None) -> Path:
    p = Path(path or "")
    return p if p.is_absolute() else root / p


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return False


def _own_record(receipt: Path) -> dict | None:
    """a receipt's own provenance record: the newest one that is not
    inherited from an input (inherited records carry lineage_branch)."""
    import json
    try:
        chain = json.loads(receipt.read_text()).get("provenance") or []
    except (OSError, ValueError):
        return None
    own = [r for r in chain if isinstance(r, dict) and not r.get("lineage_branch")]
    return own[-1] if own else None


def _plant_located_in(loam, plot: str, root: Path, report: dict) -> list[dict]:
    """the located_in view; returns the receipts it was made from, each with
    its file, its layer labels and its own provenance record."""
    loam.con.execute("DROP VIEW IF EXISTS located_in")
    rows = [r for tier in CONFORMED_TIERS
            for r in loam.find(semantic_type=LOCATED_TYPE, plot=plot, tier=tier)]
    if not rows:
        report["located_in"] = {"made": False,
                                "why": f"no run in plot '{plot}' has made {LOCATED_TYPE}"}
        return []

    included, left_out = [], []
    for row in sorted(rows, key=lambda r: r["receipt_path"] or ""):
        receipt = Path(row["receipt_path"] or "?").name
        path = _on_disk(root, row["data_path"])
        if not path.is_file():
            left_out.append(f"{receipt}: {row['data_path']} is not on disk")
            continue
        columns = [d[0] for d in loam.con.execute(
            f"SELECT * FROM {_reader(path)} LIMIT 0").description]
        missing = [k for k in EDGE_KEY if k not in columns]
        if missing:
            left_out.append(f"{receipt}: its file has no {', '.join(missing)}")
            continue
        layers = sorted(str(x[0]) for x in loam.con.execute(
            f"SELECT DISTINCT from_authority FROM {_reader(path)}").fetchall())
        included.append({"receipt": receipt, "path": path, "layers": layers,
                         "record": _own_record(_on_disk(root, row["receipt_path"]))})

    if not included:
        report["located_in"] = {"made": False, "left_out": left_out,
                                "why": "no located_in_edges receipt carries the edge key"}
        return []

    by_layer: dict[str, list[str]] = {}
    for item in included:
        for layer in item["layers"]:
            by_layer.setdefault(layer, []).append(item["receipt"])
    twice = {layer: names for layer, names in by_layer.items() if len(names) > 1}
    if twice:
        said = "; ".join(f"{layer} in {', '.join(names)}" for layer, names in sorted(twice.items()))
        report["located_in"] = {"made": False, "left_out": left_out,
                                "why": f"one layer's edges in two receipts ({said}); which "
                                       f"one is a choice, not a lookup (D-163)"}
        return []

    union = " UNION ALL BY NAME ".join(
        f"SELECT * REPLACE (CAST(from_code AS VARCHAR) AS from_code, "
        f"CAST(to_code AS VARCHAR) AS to_code), {_sql_text(item['receipt'])} AS edges_receipt "
        f"FROM {_reader(item['path'])}" for item in included)
    loam.con.execute(f"CREATE VIEW located_in AS {union}")
    count = loam.con.execute("SELECT COUNT(*) FROM located_in").fetchone()[0]
    report["located_in"] = {"made": True, "rows": count, "layers": sorted(by_layer),
                            "receipts": [i["receipt"] for i in included],
                            **({"left_out": left_out} if left_out else {})}
    return included


def _points_sql(path: Path, id_field: str) -> str:
    return (f"SELECT CAST(f.properties.\"{id_field}\" AS VARCHAR) AS feature_id, "
            f"CAST(f.properties.\"name\" AS VARCHAR) AS name, "
            f"f.geometry.coordinates[1] AS longitude, f.geometry.coordinates[2] AS latitude "
            f"FROM (SELECT unnest(features) AS f FROM read_json_auto({_quoted(path)}, "
            f"maximum_object_size = 536870912))")


def _plant_carriers(loam, plot: str, root: Path, edges: list[dict], report: dict) -> None:
    """the carriers view: every placed point of every located_count carrier,
    found through its edges receipt's own record (D-224, D-225)."""
    loam.con.execute("DROP VIEW IF EXISTS carriers")
    from canopy.indicators import IndicatorRegistry
    try:
        registry = IndicatorRegistry.load(root / INDICATORS)
    except (FileNotFoundError, ValueError) as e:
        report["carriers"] = {"made": False, "why": f"the indicator registry did not load: {e}"}
        return
    carriers = [registry.get(i) for i in registry.with_role("carrier")
                if registry.get(i).derivation.kind == "located_count"]
    if not carriers:
        report["carriers"] = {"made": False, "why": "no carrier indicator is a located_count, "
                                                    "so there are no points to draw (D-223)"}
        return
    if not edges:
        report["carriers"] = {"made": False, "why": "there is no located_in view to place "
                                                    "points through"}
        return

    from canopy.vocabulary import Vocabulary
    vocab = Vocabulary.load(root / "seeds" / "schemas")

    def meaning(name: str) -> str:
        # a receipt may predate a rename, so its types are read forward
        return getattr(vocab.resolve(name), "canonical", None) or name

    selects, made, left_out = [], {}, {}
    for ind in carriers:
        counted = meaning(ind.derivation.counts)
        found = []
        for item in edges:
            inputs = (item["record"] or {}).get("inputs") or []
            of_type = [i for i in inputs if meaning(str(i.get("semantic_type"))) == counted]
            if len(of_type) > 1:
                found.append((item, None, f"{item['receipt']} reads {len(of_type)} inputs of "
                                          f"type {counted}, so which are the points is a choice"))
            elif of_type:
                found.append((item, of_type[0], None))
        if not found:
            left_out[ind.id] = f"no located_in_edges receipt was made from {counted} points"
            continue
        if len(found) > 1:
            left_out[ind.id] = (f"{len(found)} edges receipts were made from {counted} points ("
                                f"{', '.join(f[0]['receipt'] for f in found)}); which this "
                                f"count drew on is a choice, not a lookup (D-163)")
            continue
        item, points_input, problem = found[0]
        if problem:
            left_out[ind.id] = problem
            continue
        path = _on_disk(root, points_input.get("path"))
        if not path.is_file():
            left_out[ind.id] = f"{item['receipt']} read its points from {path}, not on disk"
            continue
        points = [r for tier in CONFORMED_TIERS
                  for r in loam.find(semantic_type=counted, plot=plot, tier=tier)
                  if _same_file(_on_disk(root, r["data_path"]), path)]
        if len(points) != 1:
            left_out[ind.id] = (f"{len(points)} receipts of type {counted} point at {path}; "
                                f"the view needs exactly one to read its id field")
            continue
        id_field = points[0].get("id_field")
        receipt = Path(points[0]["receipt_path"] or "?").name
        if not id_field:
            left_out[ind.id] = f"{receipt} declares no id_field, so a point cannot be named"
            continue
        try:
            loam.con.execute(f"SELECT * FROM ({_points_sql(path, id_field)}) LIMIT 0")
        except Exception as e:
            left_out[ind.id] = (f"{receipt}'s points carry no {id_field!r} or 'name' property "
                                f"a carrier point must have: {str(e).splitlines()[0]}")
            continue
        layer = item["layers"][0] if len(item["layers"]) == 1 else None
        if layer is None:
            left_out[ind.id] = f"{item['receipt']} holds {len(item['layers'])} layers, not one"
            continue
        selects.append(
            f"SELECT {_sql_text(ind.id)} AS indicator, {_sql_text(counted)} AS counts, "
            f"{_sql_text(layer)} AS layer, p.feature_id, p.name, p.longitude, p.latitude, "
            f"{_sql_text(receipt)} AS points_receipt, {_sql_text(item['receipt'])} AS edges_receipt "
            f"FROM ({_points_sql(path, id_field)}) p "
            f"WHERE p.feature_id IN (SELECT from_code FROM located_in "
            f"WHERE from_authority = {_sql_text(layer)})")
        made[ind.id] = {"counts": counted, "layer": layer, "points_receipt": receipt,
                        "edges_receipt": item["receipt"]}

    if not selects:
        report["carriers"] = {"made": False, "left_out": left_out,
                              "why": "no carrier's points could be found through its edges"}
        return
    loam.con.execute(f"CREATE VIEW carriers AS {' UNION ALL BY NAME '.join(selects)}")
    count = loam.con.execute("SELECT COUNT(*) FROM carriers").fetchone()[0]
    report["carriers"] = {"made": True, "rows": count, "indicators": made,
                          **({"left_out": left_out} if left_out else {})}


def plant_graph(loam, plot: str, root: str | Path, declared_places=None) -> dict:
    """make the plot's graph views in its bed; returns, per view, whether it
    was made and from what, or why not. `declared_places` is the manifest's
    places: list as written, None when it declares none (D-174). ~"""
    root = Path(root)
    report = {}
    for view, semantic_type in GRAPH_VIEWS.items():
        loam.con.execute(f"DROP VIEW IF EXISTS {view}")
        rows = [r for tier in CONFORMED_TIERS
                for r in loam.find(semantic_type=semantic_type, plot=plot, tier=tier)]

        def refused(why: str) -> None:
            report[view] = {"made": False, "semantic_type": semantic_type, "why": why}

        if not rows:
            refused(f"no run in plot '{plot}' has made {semantic_type}")
            continue
        if len(rows) > 1:
            receipts = sorted(Path(r["receipt_path"] or "?").name for r in rows)
            refused(f"{len(rows)} artifacts are {semantic_type}: {', '.join(receipts)}; "
                    f"which one is a choice, not a lookup (D-163)")
            continue

        row = rows[0]
        receipt = Path(row["receipt_path"] or "?").name
        key = [k for k in (row.get("id_fields") or "").split("|") if k]
        if not key:
            refused(f"{receipt} declares no key, so a row cannot be named (KEYS-1); "
                    f"rerun the preparation that made it")
            continue
        path = Path(row["data_path"])
        path = path if path.is_absolute() else root / path
        if not path.is_file():
            refused(f"{receipt} points at {row['data_path']}, which is not on disk")
            continue
        columns = [d[0] for d in loam.con.execute(
            f"SELECT * FROM {_reader(path)} LIMIT 0").description]
        missing = [k for k in key if k not in columns]
        if missing:
            refused(f"{receipt} declares the key {', '.join(key)}, but its file has no "
                    f"{', '.join(missing)}")
            continue

        loam.con.execute(f"CREATE VIEW {view} AS SELECT * FROM {_reader(path)}")
        count = loam.con.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
        report[view] = {"made": True, "semantic_type": semantic_type, "receipt": receipt,
                        "key": key, "rows": count}

    _plant_values(loam, plot, root, report)
    _plant_plot_places(loam, declared_places, report)
    edges = _plant_located_in(loam, plot, root, report)
    _plant_carriers(loam, plot, root, edges, report)
    return report
