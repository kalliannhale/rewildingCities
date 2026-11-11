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
"""

from __future__ import annotations

from pathlib import Path

import yaml

CONFORMED_TIERS = ("tended", "gathered")

# the view's name in the bed, and the semantic type that fills it
GRAPH_VIEWS = {"places": "places", "edges": "place_edges"}

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
    return report
