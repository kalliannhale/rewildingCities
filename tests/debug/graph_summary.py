"""
tests/debug/graph_summary.py  |  rewildingCities

A read-only look at Maine's geography graph after it runs (Sprint 04, step 1).
It writes nothing. Each section prints what it found beside what Contract 3
expects, so a surprise reads as a surprise rather than a number.

    python tests/debug/graph_summary.py
    python tests/debug/graph_summary.py --data plots/maine/.data

Sections:
  1 spine totals      2 edges        3 split towns     4 null shares
  5 tribal areas, and whether the edges' keys match the two Census layers
  6 Penobscot Indian Island (PEN-1)  7 MEGIS civil divisions (D-122, MEGIS-1)
"""

import argparse
import json
from pathlib import Path

import pandas as pd

EXPECT = {"blocks": 47138, "persons": 1362359, "counties": 16, "towns": 529,
          "sldl": 151, "sldu": 35, "divisions": 923}
PENOBSCOT = ["2301957936", "2300357936"]


def header(n, title):
    print(f"\n== {n}. {title} " + "=" * max(0, 60 - len(title)))


def check(label, found, expected):
    mark = "ok " if found == expected else "OFF"
    print(f"  [{mark}] {label}: {found} (expected {expected})")


def features(path):
    """the properties of every feature in a geojson; geometry is not read."""
    with open(path) as f:
        return pd.DataFrame([feat["properties"] for feat in json.load(f)["features"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="plots/maine/.data")
    data = Path(ap.parse_args().data)

    spine = pd.read_parquet(data / "graph_spine_spine.parquet")
    edges = pd.read_parquet(data / "graph_edges_edges.parquet")
    assigned = pd.read_parquet(data / "graph_divisions_assignment.parquet")
    divisions = features(data / "graph_dissolve_towns_dissolved.geojson")

    header(1, "spine totals")
    check("blocks", len(spine), EXPECT["blocks"])
    check("persons", int(spine["persons"].sum()), EXPECT["persons"])
    print(f"        households {int(spine['households'].sum())}, "
          f"housing units {int(spine['housing_units'].sum())}")
    check("counties", spine["county"].nunique(), EXPECT["counties"])
    check("towns", spine["cousub"].nunique(), EXPECT["towns"])
    acs = pd.read_parquet(data / "acs_cousub_2024.parquet")[["GEOID", "NAME"]]
    spine_towns, acs_towns = set(spine["cousub"]), set(acs["GEOID"].astype(str))
    print(f"        ACS 2024 has {len(acs_towns)} town(s)")
    for code in sorted(spine_towns - acs_towns):
        rows = spine[spine["cousub"] == code]
        print(f"        in the spine, not in ACS: {code}, {len(rows)} block(s), "
              f"{int(rows['persons'].sum())} persons, {int(rows['housing_units'].sum())} "
              f"housing units, tribal codes {sorted(rows['aiannh'].dropna().unique())}")
    for code in sorted(acs_towns - spine_towns):
        print(f"        in ACS, not in the spine: {code} "
              f"{acs.loc[acs['GEOID'].astype(str) == code, 'NAME'].iloc[0]}")
    check("House districts", spine["sldl"].nunique(), EXPECT["sldl"])
    check("Senate districts", spine["sldu"].nunique(), EXPECT["sldu"])

    header(2, "edges")
    print(edges.groupby(["kind", "from_authority", "to_authority"]).size()
               .rename("edges").to_string())
    check("contains edges", int((edges["kind"] == "contains").sum()),
          EXPECT["counties"] + EXPECT["towns"])
    for auth, key in (("us_census_sldl", "sldl"), ("us_census_sldu", "sldu")):
        touched = edges.loc[edges["to_authority"] == auth, "to_code"].nunique()
        check(f"{auth} districts touched by a town", touched, EXPECT[key])
    zero = edges[(edges["kind"] == "overlaps") & (edges["weight_population"] == 0)]
    print("  overlaps with a population share of exactly 0 (land, no people):")
    print(zero.groupby("to_authority").size().rename("edges").to_string()
          if len(zero) else "  none")
    print("  vintages by target:")
    print(edges.groupby("to_authority")["vintage"].unique().to_string())

    header(3, "split towns")
    for auth, label in (("us_census_sldl", "House"), ("us_census_sldu", "Senate")):
        per_town = edges[edges["to_authority"] == auth].groupby("from_code").size()
        print(f"  {label}: {int((per_town > 1).sum())} town(s) touch more than one "
              f"district; most is {int(per_town.max())}")

    header(4, "null shares")
    nulls = edges[edges["weight_reason"].notna()]
    print(nulls.groupby(["to_authority", "weight_reason"]).size()
               .rename("edges").to_string() if len(nulls) else "  none")
    town_hh = spine.groupby("cousub")[["persons", "households"]].sum()
    empty = town_hh[town_hh["households"] == 0]
    print(f"  {len(empty)} town(s) with zero households "
          f"({int((empty['persons'] > 0).sum())} of them with persons):")
    print("  " + ", ".join(empty.index) if len(empty) else "  none")

    header(5, "tribal areas")
    ai = spine.dropna(subset=["aiannh"])
    print(ai.groupby(["aiannh", "aiannh_comptyp"], dropna=False)
            .agg(blocks=("GEOID", "size"), persons=("persons", "sum"),
                 towns=("cousub", "nunique")).to_string())
    tribal = edges[edges["to_authority"] == "us_census_aiannh"]
    print("\n  town overlaps (share of the town inside the area):")
    print(tribal[["from_code", "to_code", "weight_population", "weight_households",
                  "weight_reason"]].sort_values(["to_code", "from_code"])
                 .to_string(index=False))
    print("\n  do the edges' keys match the layers' keys?")
    layer_keys = set()
    for name in ("tribal_reservations_2020", "tribal_trust_lands_2020"):
        layer = features(data / f"{name}.geojson")
        print(f"  {name}: {len(layer)} feature(s), properties {list(layer.columns)}")
        show = [c for c in ("GEOID", "AIANNH", "AIANNHCE", "COMPTYP", "NAME", "BASENAME")
                if c in layer.columns]
        print(layer[show].to_string(index=False))
        if "GEOID" in layer.columns:
            layer_keys |= set(layer["GEOID"].astype(str))
    edge_keys = set(tribal["to_code"].astype(str))
    print(f"  edge keys {sorted(edge_keys)}")
    print(f"  layer GEOIDs {sorted(layer_keys)}")
    print(f"  in edges, not in layers: {sorted(edge_keys - layer_keys) or 'none'}")
    print(f"  in layers, not in edges: {sorted(layer_keys - edge_keys) or 'none'}")

    header(6, "Penobscot Indian Island (PEN-1)")
    for code in PENOBSCOT:
        rows = spine[spine["cousub"] == code]
        print(f"  {code}: {len(rows)} block(s), {int(rows['persons'].sum())} persons, "
              f"county {sorted(rows['county'].unique())}, "
              f"tribal codes {sorted(rows['aiannh'].dropna().unique())}")
    print(tribal[tribal["from_code"].isin(PENOBSCOT)].to_string(index=False))

    header(7, "MEGIS civil divisions")
    codes = divisions["GEOCODE"].astype(str)
    check("divisions after dissolve", len(divisions), EXPECT["divisions"])
    short = divisions[codes.str.len() == 1]
    print(f"  one-character GEOCODEs (MEGIS-1): {len(short)}")
    if len(short):
        print(short.drop(columns=[c for c in short.columns if c.startswith("Shape")])
                   .to_string(index=False))
    div = edges[edges["from_authority"] == "megis"]
    print(f"  divisions with an edge: {div['from_code'].nunique()} of {len(divisions)}")
    unplaced = spine[~spine["GEOID"].isin(assigned.dropna(subset=["division"])["GEOID"])]
    print(f"  unplaced blocks: {len(unplaced)} ({int(unplaced['persons'].sum())} persons)")
    reached = set(div["to_code"])
    missed = sorted(set(spine["cousub"]) - reached)
    print(f"  Census towns no division reaches: {len(missed)} {missed[:10]}")
    many = div.groupby("from_code").agg(towns=("to_code", "nunique"),
                                         top_share=("weight_population", "max"))
    many = many[many["towns"] > 1].sort_values("top_share")
    print(f"  divisions in more than one Census town: {len(many)}, smallest top share first:")
    wanted = ["TOWN", "COUNTY", "CNTYCODE", "LURC"]
    kept = [c for c in wanted if c in divisions.columns]
    print(f"  keep_fields that survived the dissolve: {kept}; missing "
          f"{[c for c in wanted if c not in kept]}")
    source = features(data / "graph_repair_towns_repaired.geojson")
    if "LURC" in source.columns:
        per = source.groupby(source["GEOCODE"].astype(str))["LURC"].nunique(dropna=False)
        print(f"  LURC is in the source layer: values {sorted(source['LURC'].astype(str).unique())}; "
              f"{int((per > 1).sum())} GEOCODE(s) carry more than one value")
    else:
        print(f"  LURC is not in the source layer either; its fields are {list(source.columns)}")
    edgeless = sorted(set(codes) - set(div["from_code"]))
    print("  divisions with no edge:")
    print(divisions[codes.isin(edgeless)][kept + ["GEOCODE"]].to_string(index=False))
    print("  unplaced blocks:")
    print(unplaced[["GEOID", "cousub", "persons", "households"]].to_string(index=False))
    names = divisions.set_index(codes)[kept]
    print(many.join(names).head(25).to_string())


if __name__ == "__main__":
    main()
