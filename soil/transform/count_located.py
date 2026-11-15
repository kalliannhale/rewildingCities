"""
soil/transform/count_located.py  |  rewildingCities

a carrier indicator's values (D-209): for every place at the declared levels,
how many of one layer's points stand in it, and that count per its own
persons (or households). read from located_in edges, so a point counts in
every area it falls in: its town, its county, its House and its Senate
district (Contract 3, section 2).

  ~ every place at a declared level gets a row, a zero included: absence is
    a value, not a missing row
  ~ a place with no persons has no rate: null, empty_reason zero_population,
    never 0 or infinity
  ~ the count travels with the rate, in `count`, and the persons in
    `households` with households_counts naming what is counted, as every
    value row says what it rests on
  ~ the edges come from one layer, named in the receipt: which points, by
    whom and of which release, is the preparation's to say (D-224). that
    they are the type the indicator counts is checked before the run, by
    the orchestrator
  ~ a Census tribal area is counted only beside a note (D-233): its step
    names a tribal_note, a seeds/notes id, and every tribal-area row
    carries it in context_note. a federal source may not see the nations'
    own institutions (TRIBE-7), so a tribal count never travels without
    the words that say how far it can be trusted. a tribal area's code is
    AIANNH plus its component (R, T), as located_in writes it (D-125), and
    its persons are its own blocks'
  ~ every row says which boundaries it was counted on, in boundary_vintage:
    the one vintage of the edges that reach its level's places (D-231). a
    level no edge reaches (no point stands in any of its places) takes its
    places' own vintage, and the run says so. a level whose edges carry two
    vintages, or a blank one, is refused, never guessed. so `time` says only when the points were
    observed, and loam compares boundary_vintage with the place's own

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  edges (located_in_edges), spine (block_spine), places (places)
Params:
  indicator     required: the declaration, via $indicators.<id>; its
                derivation must be located_count
  levels        required: the place levels to count, e.g. [state, county,
                cousub, sldl, sldu]
  time          required: what `time` the values carry
  published_by  required: who made the values (rewildingcities)
  tribal_note   required when levels holds aiannh, never otherwise: the
                seeds/notes id every tribal-area row carries (D-233)
Output: value rows, parquet or csv, in indicator_values' columns plus
boundary_vintage, keyed (unit_authority, unit_code, indicator, time). ~
"""

from __future__ import annotations

import pandas as pd

LEVEL_COLUMN = {"county": "county", "cousub": "cousub", "sldl": "sldl", "sldu": "sldu",
                "aiannh": "aiannh"}
KEY = ["unit_authority", "unit_code", "indicator", "time"]
COLUMNS = ["measurement_id", "unit_authority", "unit_code", "name", "indicator", "value",
           "moe", "moe_status", "bound", "empty_reason", "households", "households_counts",
           "households_reason", "cv", "reliability_note", "published_by", "method", "time",
           "boundary_vintage", "context_note", "count"]


class CountRefused(ValueError):
    """a count the declaration refuses, with why."""


def _persons_by_level(spine: pd.DataFrame, level: str, basis: str) -> dict:
    counts = pd.to_numeric(spine[basis], errors="coerce").fillna(0)
    if level == "state":
        return {"__state__": float(counts.sum())}
    col = LEVEL_COLUMN.get(level)
    if col is None:
        raise CountRefused(f"level {level!r} has no column in the spine; countable "
                           f"levels are state, {', '.join(LEVEL_COLUMN)}")
    if level == "aiannh":
        # the place's code is AIANNH plus its component, as located_in's
        # spine_table writes it (D-125): a reservation and its nation's trust
        # land are two places, never one denominator
        if "aiannh_comptyp" not in spine.columns:
            raise CountRefused("the spine carries no aiannh_comptyp, so a tribal area's "
                               "code cannot be made (D-125)")
        has = spine["aiannh"].notna() & (spine["aiannh"].astype(str).str.strip() != "")
        codes = (spine["aiannh"].astype(str) + spine["aiannh_comptyp"].astype(str)).where(has)
        return counts[has].groupby(codes[has]).sum().to_dict()
    return counts.groupby(spine[col].astype(str)).sum().to_dict()


def vintage_by_level(edges: pd.DataFrame, places: pd.DataFrame, levels) -> dict:
    """the one boundary vintage each level was counted on (D-231), read from
    the edges that reach its places: build_located_in writes each edge's
    vintage from the preparation's `vintages`. an edge's level is its `to`
    place's, since one authority holds state, county and town."""
    if "vintage" not in edges.columns:
        raise CountRefused("the edges carry no vintage, so which boundaries were counted "
                           "on is unknown (D-231)")
    level_of = {(str(a), str(c)): str(lv) for a, c, lv in
                zip(places["authority"], places["code"].astype(str), places["level"])}
    seen: dict = {}
    for a, c, v in zip(edges["to_authority"].astype(str), edges["to_code"].astype(str),
                       edges["vintage"]):
        level = level_of.get((a, c))
        if level in levels:
            seen.setdefault(level, set()).add("" if pd.isna(v) else str(v).strip())
    out = {}
    for level in levels:
        vintages = seen.get(level, set())
        if not vintages:
            # no point stands in any place at this level: its zeros are said of
            # those places, on their own boundaries
            here = places[places["level"] == level]
            own = (set(here["vintage"].dropna().astype(str).str.strip()) - {""}
                   if "vintage" in here.columns else set())
            if len(own) != 1:
                raise CountRefused(f"no edge reaches a {level} place and its places carry "
                                   f"{'no vintage' if not own else 'vintages ' + ', '.join(sorted(own))}, "
                                   f"so which {level} boundaries were counted on is unknown (D-231)")
            out[level] = own.pop()
            continue
        if "" in vintages:
            raise CountRefused(f"an edge reaching a {level} place carries no vintage (D-231)")
        if len(vintages) > 1:
            raise CountRefused(f"the edges reaching {level} places carry vintages "
                               f"{', '.join(sorted(vintages))}; a level is counted on one "
                               f"set of boundaries (D-231)")
        out[level] = vintages.pop()
    return out


def levels_without_edges(edges: pd.DataFrame, places: pd.DataFrame, levels) -> list:
    """the declared levels no edge reaches, whose vintage is their places'."""
    ends = set(zip(edges["to_authority"].astype(str), edges["to_code"].astype(str)))
    reached = {str(lv) for a, c, lv in zip(places["authority"].astype(str),
                                           places["code"].astype(str), places["level"])
               if (a, c) in ends}
    return [lv for lv in levels if lv not in reached]


def count(edges: pd.DataFrame, spine: pd.DataFrame, places: pd.DataFrame,
          indicator: dict, levels, time: str, published_by: str,
          tribal_note: str | None = None) -> pd.DataFrame:
    d = indicator.get("derivation") or {}
    if d.get("kind") != "located_count":
        raise CountRefused(f"{indicator.get('id')} is a {d.get('kind')}, not a located_count")
    if "aiannh" in levels and not tribal_note:
        raise CountRefused("a Census tribal area is counted only beside a note: name its "
                           "seeds/notes id as tribal_note, since a source may not see the "
                           "nations' own institutions and a bare zero would mislead "
                           "(TRIBE-7, D-233)")
    if tribal_note and "aiannh" not in levels:
        raise CountRefused("tribal_note is named but no tribal level is counted (D-233)")
    basis, scale = d["denominator"], float(d["scale"])
    layers = set(edges["from_authority"].astype(str))
    if len(layers) != 1:
        raise CountRefused(f"the edges come from {sorted(layers) or 'no layer'}; a "
                           f"count reads one layer's edges")
    if (edges["kind"] != "located_in").any():
        raise CountRefused("a count reads located_in edges only")

    counted_on = vintage_by_level(edges, places, levels)
    n = edges.groupby(["to_authority", "to_code"]).size().to_dict()
    rows = []
    for level in levels:
        here = places[places["level"] == level]
        if here.empty:
            raise CountRefused(f"the places table holds no {level} places")
        persons = _persons_by_level(spine, level, basis)
        for p in here.itertuples(index=False):
            code = str(p.code)
            people = persons.get("__state__" if level == "state" else code, 0.0)
            k = int(n.get((p.authority, code), 0))
            value, reason = ((None, f"zero_{'population' if basis == 'persons' else basis}")
                             if people == 0 else (k / people * scale, None))
            rows.append({
                "measurement_id": f"{indicator['id']}:{p.authority}:{code}",
                "unit_authority": p.authority, "unit_code": code, "name": p.name,
                "indicator": indicator["id"], "value": value, "moe": None,
                "moe_status": "not_applicable", "bound": None, "empty_reason": reason,
                "households": people, "households_counts": basis,
                "households_reason": None, "cv": None, "reliability_note": None,
                "published_by": published_by, "method": "count_located:located_count",
                "time": time, "boundary_vintage": counted_on[level],
                "context_note": tribal_note if level == "aiannh" else None, "count": k})
    out = pd.DataFrame(rows, columns=COLUMNS)
    if out.duplicated(KEY).any():
        raise CountRefused("one place and indicator twice")
    if not set(n) <= set(zip(places["authority"], places["code"].astype(str))):
        raise CountRefused("an edge's `to` end is not a place")
    return out


def counted_layer(edges: pd.DataFrame) -> str:
    """the one layer the edges come from; count() has refused any other."""
    return str(edges["from_authority"].astype(str).iloc[0])


def output_metadata(out: pd.DataFrame, layer: str | None = None) -> dict:
    meta = {"data_category": "tabular", "crs": None, "row_count": len(out),
            "variables": COLUMNS, "id_fields": KEY, "spatial_unit": "place_value"}
    if layer is not None:
        meta["counted_layer"] = layer
    return meta


def main():
    try:
        from canopy.pr_io import (parse_primitive_args, get_input, require_param,
                                  WarningsCollector, primitive_success, primitive_failure,
                                  primitive_error_handling)
    except ImportError:
        from pr_io import (parse_primitive_args, get_input, require_param,
                           WarningsCollector, primitive_success, primitive_failure,
                           primitive_error_handling)

    def read(path):
        return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path, dtype=str)

    args = parse_primitive_args()
    w = WarningsCollector("count_located")
    with primitive_error_handling(w):
        i, p = args["inputs"], args["params"]
        edges = read(get_input(i, "edges"))
        try:
            places = read(get_input(i, "places"))
            levels = require_param(p, "levels")
            out = count(edges, read(get_input(i, "spine")), places,
                        require_param(p, "indicator"), levels,
                        str(require_param(p, "time")), require_param(p, "published_by"),
                        p.get("tribal_note"))
        except CountRefused as e:
            primitive_failure("Count refused", str(e))
        empty = levels_without_edges(edges, places, levels)
        if empty:
            w.info(f"no point stands in any {', '.join(empty)} place; those zeros sit on "
                   f"the places' own vintage (D-231)")
        zero = int((out["count"] == 0).sum())
        w.info(f"{len(out)} place value(s); {zero} place(s) with none of the layer here; "
               f"{int(out['empty_reason'].notna().sum())} with no persons and so no rate")
        if str(args["output"]).endswith(".parquet"):
            out.to_parquet(args["output"], index=False)
        else:
            out.to_csv(args["output"], index=False)
        primitive_success(output_metadata(out, counted_layer(edges)), w)


if __name__ == "__main__":
    main()
