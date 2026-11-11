"""
soil/transform/build_place_edges.py  |  rewildingCities

The edges of the geography graph (Contract 3), from the block spine.

  contains   state to county, county to town: clean nesting, weights 1 and 1
  overlaps   town to House district, town to Senate district, town to Census
             tribal area, and (D-122) Maine civil division to Census town:
             each with weight_population and weight_households (D-121), the
             share of the `from` place's persons and households inside the
             `to` place, summed over whole 2020 blocks

A share whose denominator is zero is null with a reason (zero_population,
zero_households), never 0: a township with no households has no household
share, which is not the same as a share of nothing.

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:
  spine      the block spine (build_block_spine)
  divisions  optional: blocks assigned to civil divisions (GEOID, division),
             from assign_blocks_to_polygons, for D-122's edges
Params:
  state_fips       two digits, required
  vintages         required mapping: town, sldl, sldu, aiannh, and division
                   if divisions are given; written on every edge
  division_authority  default "megis"
Output: the edges table, parquet or csv by the output's extension.
Checks (refuses if broken): every town has exactly one county; a town's
shares across one chamber sum to 1 for each basis.
"""

from __future__ import annotations

try:
    from canopy.pr_io import (parse_primitive_args, get_input, get_param, require_param,
                              WarningsCollector, primitive_success, primitive_failure,
                              primitive_error_handling)
except ImportError:
    from pr_io import (parse_primitive_args, get_input, get_param, require_param,
                       WarningsCollector, primitive_success, primitive_failure,
                       primitive_error_handling)

GEOID = "us_census_geoid"
# a Census GEOID is unique only within its level: House District 1 and Senate
# District 1 are both 23001. so each chamber has its own authority, and every
# place keeps a two-part key, (authority, code), that names one place (GRAPH-1)
SLDL, SLDU, AIANNH = "us_census_sldl", "us_census_sldu", "us_census_aiannh"
COLUMNS = ["from_authority", "from_code", "to_authority", "to_code", "kind",
           "weight_population", "weight_households", "weight_reason", "source", "vintage"]
TOLERANCE = 1e-9


def read_table(path):
    import pandas as pd
    if str(path).endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype={"GEOID": str, "county": str, "cousub": str,
                                    "sldl": str, "sldu": str, "aiannh": str,
                                    "division": str})


def write_table(frame, path):
    if str(path).endswith(".parquet"):
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)


def overlaps(spine, from_col, to_col, from_auth, to_auth, source, vintage):
    """shares of each `from` place's persons and households inside each `to`."""
    import pandas as pd
    rows = spine.dropna(subset=[from_col, to_col])
    part = rows.groupby([from_col, to_col], as_index=False)[["persons", "households"]].sum()
    whole = spine.dropna(subset=[from_col]).groupby(from_col)[["persons", "households"]].sum()
    part = part.join(whole, on=from_col, rsuffix="_whole")
    reasons = []
    wp, wh = [], []
    for _, r in part.iterrows():
        why = []
        if r["persons_whole"] == 0:
            wp.append(None); why.append("zero_population")
        else:
            wp.append(r["persons"] / r["persons_whole"])
        if r["households_whole"] == 0:
            wh.append(None); why.append("zero_households")
        else:
            wh.append(r["households"] / r["households_whole"])
        reasons.append(", ".join(why) or None)
    return pd.DataFrame({
        "from_authority": from_auth, "from_code": part[from_col].astype(str),
        "to_authority": to_auth, "to_code": part[to_col].astype(str), "kind": "overlaps",
        "weight_population": wp, "weight_households": wh, "weight_reason": reasons,
        "source": source, "vintage": vintage})


def contains(pairs, source, vintage):
    import pandas as pd
    return pd.DataFrame({
        "from_authority": GEOID, "from_code": [p for p, _ in pairs],
        "to_authority": GEOID, "to_code": [c for _, c in pairs], "kind": "contains",
        "weight_population": 1.0, "weight_households": 1.0, "weight_reason": None,
        "source": source, "vintage": vintage})


def check_shares(edges, to_prefix_filter, label):
    """a place's shares across one family of `to` places sum to 1, per basis."""
    fam = edges[(edges["kind"] == "overlaps") & to_prefix_filter(edges)]
    for basis in ("weight_population", "weight_households"):
        sums = fam.dropna(subset=[basis]).groupby("from_code")[basis].sum()
        off = sums[(sums - 1).abs() > TOLERANCE]
        if len(off):
            primitive_failure("Shares do not sum to 1",
                              f"{label}, {basis}: {len(off)} place(s), e.g. "
                              f"{off.index[0]} sums to {off.iloc[0]:.12f}")


def build(spine, divisions, state_fips, vintages, division_authority, w):
    import pandas as pd
    for need in ("town", "sldl", "sldu", "aiannh"):
        if not vintages.get(need):
            primitive_failure("Missing vintage", f"vintages.{need} is required")

    county_of = spine.groupby("cousub")["county"].nunique()
    split = county_of[county_of != 1]
    if len(split):
        primitive_failure("Town in more than one county",
                          f"{len(split)} town(s), e.g. {split.index[0]}")
    counties = sorted(spine["county"].unique())
    towns = spine[["county", "cousub"]].drop_duplicates().sort_values("cousub")

    parts = [
        contains([(state_fips, c) for c in counties], "GEOID nesting", vintages["town"]),
        contains(list(towns.itertuples(index=False, name=None)), "GEOID nesting",
                 vintages["town"]),
        overlaps(spine, "cousub", "sldl", GEOID, SLDL, "2024 SLDL block equivalency, "
                 "2020 blocks", vintages["sldl"]),
        overlaps(spine, "cousub", "sldu", GEOID, SLDU, "2024 SLDU block equivalency, "
                 "2020 blocks", vintages["sldu"]),
        overlaps(spine, "cousub", "aiannh", GEOID, AIANNH,
                 "2020 AIANNH block assignment", vintages["aiannh"]),
    ]
    if divisions is not None:
        if not vintages.get("division"):
            primitive_failure("Missing vintage", "vintages.division is required with divisions")
        joined = spine.merge(divisions[["GEOID", "division"]], on="GEOID", how="left")
        unplaced = joined["division"].isna()
        if unplaced.any():
            w.info(f"{int(unplaced.sum())} block(s) fall in no civil division "
                   f"({int(joined.loc[unplaced, 'persons'].sum())} persons); they carry "
                   f"no division edge")
        parts.append(overlaps(joined, "division", "cousub", division_authority, GEOID,
                              "2020 block internal points in civil divisions (D-122)",
                              vintages["division"]))
    edges = pd.concat(parts, ignore_index=True)[COLUMNS]

    is_town = edges["from_authority"] == GEOID
    check_shares(edges, lambda e: is_town & (e["to_authority"] == SLDL), "town to House")
    check_shares(edges, lambda e: is_town & (e["to_authority"] == SLDU), "town to Senate")
    if divisions is not None:
        check_shares(edges, lambda e: e["from_authority"] == division_authority,
                     "civil division to town")

    zero = edges["weight_reason"].notna().sum()
    if zero:
        w.info(f"{zero} edge(s) carry a null share with its reason (zero_population or "
               f"zero_households), never 0")
    w.info(f"edges: " + ", ".join(f"{k} {v}" for k, v in edges["kind"].value_counts().items()))
    return edges


def main():
    args = parse_primitive_args()
    w = WarningsCollector("build_place_edges")
    with primitive_error_handling(w):
        state = str(require_param(args["params"], "state_fips")).zfill(2)
        vintages = require_param(args["params"], "vintages")
        div_path = get_input(args["inputs"], "divisions", required=False)
        edges = build(read_table(get_input(args["inputs"], "spine")),
                      read_table(div_path) if div_path else None, state, vintages,
                      get_param(args["params"], "division_authority", "megis"), w)
        write_table(edges, args["output"])
        primitive_success({"data_category": "tabular", "crs": None,
                           "row_count": len(edges), "variables": COLUMNS}, w)


if __name__ == "__main__":
    main()
