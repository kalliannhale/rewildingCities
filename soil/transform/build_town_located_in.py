"""
soil/transform/build_town_located_in.py  |  rewildingCities

located_in edges for a layer placed by town (Contract 3, section 2; D-246):
every feature to the town its row names, and through that town's code to
its county and state, weights 1 and 1. a feature here has no point, so it
is placed only where its town decides: never in a House or Senate district,
a Census tribal area or a civil division, since a town can lie across
several, and which one a feature is in is not something its town can say.

  ~ the town is a county subdivision code, ten digits: its first five are
    its county and its first two its state, exact by construction
  ~ each edge carries its place's own vintage from the places table, so a
    count's boundary_vintage is the places' own and never a second guess
    (D-231)
  ~ a feature with no town, a town that is not one of the state's places,
    or a feature id used twice is refused, never dropped

the edges are their own artifact, of type located_in_edges, beside
build_located_in's, in the same columns and key (D-207). ~

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  features (a layer placed by town, e.g. news_outlet), places (places)
Params:
  layer       required: the layer's label, every edge's from_authority
  id_field    required: the column naming each feature
  town_field  required: the column holding each feature's town code
  state_fips  required: two digits
Output: the located_in edges, parquet or csv by the output's extension. ~
"""

from __future__ import annotations

import pandas as pd

GEOID = "us_census_geoid"
COLUMNS = ["from_authority", "from_code", "to_authority", "to_code", "kind",
           "weight_population", "weight_households", "weight_reason", "source", "vintage"]
KEY = ["from_authority", "from_code", "to_authority", "to_code"]
KIND = "located_in"
PLACED_AT = ("state", "county", "cousub")
NOT_PLACED_AT = {
    "sldl": "a town can lie across House districts, and a feature placed by town has no point",
    "sldu": "a town can lie across Senate districts, and a feature placed by town has no point",
    "aiannh": "a Census tribal area is made of blocks, and a feature placed by town has no block",
    "division": "a civil division is made of blocks, and a feature placed by town has no block",
}
SOURCE = "the town each feature names, through the places table's codes (D-246)"


class TownLocatedRefused(ValueError):
    """a placement the contract refuses, with why."""


def _text(x) -> str | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    t = str(x).strip()
    return t or None


def locate_by_town(features: pd.DataFrame, places: pd.DataFrame, layer: str,
                   id_field: str, town_field: str, state_fips: str) -> pd.DataFrame:
    for col in (id_field, town_field):
        if col not in features.columns:
            raise TownLocatedRefused(f"the layer has no column {col!r}")
    for col in ("authority", "code", "level", "vintage"):
        if col not in places.columns:
            raise TownLocatedRefused(f"the places table has no {col!r} column")
    ids = features[id_field].map(_text)
    if ids.isna().any():
        raise TownLocatedRefused(f"{int(ids.isna().sum())} feature(s) carry no {id_field}")
    dup = sorted(set(ids[ids.duplicated()]))
    if dup:
        raise TownLocatedRefused(f"a feature id names one feature in its layer; used twice: "
                                 f"{', '.join(dup[:10])}")
    here = places[places["authority"].astype(str) == GEOID]
    level_of = dict(zip(here["code"].astype(str), here["level"].astype(str)))
    vintage_of = dict(zip(here["code"].astype(str), here["vintage"].map(_text)))

    rows = []
    for fid, town in zip(ids, features[town_field].map(_text)):
        if town is None:
            raise TownLocatedRefused(f"{layer}:{fid} names no town")
        if not town.startswith(state_fips) or level_of.get(town) != "cousub":
            raise TownLocatedRefused(f"{layer}:{fid} names {town}, which is not a town "
                                     f"(county subdivision) of state {state_fips} in places")
        for code, level in ((town[:2], "state"), (town[:5], "county"), (town, "cousub")):
            if level_of.get(code) != level:
                raise TownLocatedRefused(f"{layer}:{fid}: its {level}, {code}, is not in places")
            vintage = vintage_of.get(code)
            if vintage is None:
                raise TownLocatedRefused(f"the place {code} carries no vintage, so which "
                                         f"boundaries an edge to it sits on is unknown (D-231)")
            rows.append({"from_authority": layer, "from_code": fid, "to_authority": GEOID,
                         "to_code": code, "kind": KIND, "weight_population": 1.0,
                         "weight_households": 1.0, "weight_reason": None,
                         "source": SOURCE, "vintage": vintage})
    edges = pd.DataFrame(rows, columns=COLUMNS)
    if edges.duplicated(KEY).any():
        raise TownLocatedRefused("one feature has two edges to one place")
    return edges


def output_metadata(edges: pd.DataFrame) -> dict:
    """what the receipt says: its key (KEYS-1), the levels it places at, and
    the levels it never does, each with why."""
    return {"data_category": "tabular", "crs": None, "row_count": len(edges),
            "variables": COLUMNS, "id_fields": KEY, "spatial_unit": "edge",
            "placed_at": list(PLACED_AT), "not_placed_at": NOT_PLACED_AT}


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
    w = WarningsCollector("build_town_located_in")
    with primitive_error_handling(w):
        i, p = args["inputs"], args["params"]
        layer = str(require_param(p, "layer"))
        try:
            features = read(get_input(i, "features"))
            edges = locate_by_town(features, read(get_input(i, "places")), layer,
                                   str(require_param(p, "id_field")),
                                   str(require_param(p, "town_field")),
                                   str(require_param(p, "state_fips")).zfill(2))
        except TownLocatedRefused as e:
            primitive_failure("located_in refused", str(e))
        w.info(f"{layer}: {len(features)} feature(s), {len(edges)} edge(s), at "
               f"{', '.join(PLACED_AT)} only")
        if str(args["output"]).endswith(".parquet"):
            edges.to_parquet(args["output"], index=False)
        else:
            edges.to_csv(args["output"], index=False)
        primitive_success(output_metadata(edges), w)


if __name__ == "__main__":
    main()
