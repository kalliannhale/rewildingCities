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
  ~ the layer the edges come from must be the indicator's declared layer
  ~ a Census tribal area is never a declared level here (TRIBE-7)

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  edges (located_in_edges), spine (block_spine), places (places)
Params:
  indicator     required: the declaration, via $indicators.<id>; its
                derivation must be located_count
  levels        required: the place levels to count, e.g. [state, county,
                cousub, sldl, sldu]
  time          required: what `time` the values carry
  published_by  required: who made the values (rewildingcities)
Output: value rows, parquet or csv, in indicator_values' columns, keyed
(unit_authority, unit_code, indicator, time). ~
"""

from __future__ import annotations

import pandas as pd

LEVEL_COLUMN = {"county": "county", "cousub": "cousub", "sldl": "sldl", "sldu": "sldu"}
KEY = ["unit_authority", "unit_code", "indicator", "time"]
COLUMNS = ["measurement_id", "unit_authority", "unit_code", "name", "indicator", "value",
           "moe", "moe_status", "bound", "empty_reason", "households", "households_counts",
           "households_reason", "cv", "reliability_note", "published_by", "method", "time",
           "count"]


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
    return counts.groupby(spine[col].astype(str)).sum().to_dict()


def count(edges: pd.DataFrame, spine: pd.DataFrame, places: pd.DataFrame,
          indicator: dict, levels, time: str, published_by: str) -> pd.DataFrame:
    d = indicator.get("derivation") or {}
    if d.get("kind") != "located_count":
        raise CountRefused(f"{indicator.get('id')} is a {d.get('kind')}, not a located_count")
    if "aiannh" in levels:
        raise CountRefused("a Census tribal area is never counted here: the survey does "
                           "not see reservation libraries, so a zero would be false (TRIBE-7)")
    layer, basis, scale = d["layer"], d["denominator"], float(d["scale"])
    layers = set(edges["from_authority"].astype(str))
    if layers != {layer}:
        raise CountRefused(f"the edges come from {sorted(layers)}; {indicator['id']} "
                           f"counts {layer} only")
    if (edges["kind"] != "located_in").any():
        raise CountRefused("a count reads located_in edges only")

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
                "time": time, "count": k})
    out = pd.DataFrame(rows, columns=COLUMNS)
    if out.duplicated(KEY).any():
        raise CountRefused("one place and indicator twice")
    if not set(n) <= set(zip(places["authority"], places["code"].astype(str))):
        raise CountRefused("an edge's `to` end is not a place")
    return out


def output_metadata(out: pd.DataFrame) -> dict:
    return {"data_category": "tabular", "crs": None, "row_count": len(out),
            "variables": COLUMNS, "id_fields": KEY, "spatial_unit": "place_value"}


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
        try:
            out = count(read(get_input(i, "edges")), read(get_input(i, "spine")),
                        read(get_input(i, "places")), require_param(p, "indicator"),
                        require_param(p, "levels"), str(require_param(p, "time")),
                        require_param(p, "published_by"))
        except CountRefused as e:
            primitive_failure("Count refused", str(e))
        zero = int((out["count"] == 0).sum())
        w.info(f"{len(out)} place value(s); {zero} place(s) with none of the layer here; "
               f"{int(out['empty_reason'].notna().sum())} with no persons and so no rate")
        if str(args["output"]).endswith(".parquet"):
            out.to_parquet(args["output"], index=False)
        else:
            out.to_csv(args["output"], index=False)
        primitive_success(output_metadata(out), w)


if __name__ == "__main__":
    main()
