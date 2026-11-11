"""
tests/debug/places_probe.py  |  rewildingCities

A read-only look at the facts the places table's flags rest on (Sprint 04,
step 2). It writes nothing. Every flag rule is decided from what this prints,
never from what a seed or a guess says the files hold.

    python tests/debug/places_probe.py
    python tests/debug/places_probe.py --data plots/maine/.data

Reads:
  tl_2024_23_cousub.zip              2024 TIGER/Line county subdivisions (.dbf only)
  graph_spine_spine.parquet          the 2024 spine (D-126, D-127)
  graph_repair_towns_repaired.geojson  MEGIS, undissolved, with LURC
  graph_edges_edges.parquet          MEGIS division to Census town edges

Sections:
  1 the 2024 layer against the spine's towns (vintage check)
  2 functional status, legal/statistical area description, class codes
  3 names a flag might rest on (plantation, UT, Baxter, township, reservation)
  4 reservation subdivisions by geometry: towns whose every block is in an R area
  5 LURC: divisions all y, all n, or mixed, and the Census towns they touch
"""

import argparse
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

# the spine's dBase reader imports canopy, so the repo root goes on the path,
# as probe_envelope.py does
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

COUSUB_FIELDS = ["GEOID", "NAME", "NAMELSAD", "LSAD", "CLASSFP", "MTFCC", "FUNCSTAT",
                 "ALAND", "AWATER"]


def header(n, title):
    print(f"\n== {n}. {title} " + "=" * max(0, 60 - len(title)))


def spine_module():
    spec = importlib.util.spec_from_file_location(
        "bs", Path(__file__).resolve().parents[2] / "soil" / "transform" / "build_block_spine.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_cousub(path, bs):
    with zipfile.ZipFile(path) as z:
        dbf = [n for n in z.namelist() if n.lower().endswith("_cousub.dbf")]
        if len(dbf) != 1:
            raise SystemExit(f"expected one _cousub.dbf in {path}; found {dbf}")
        return bs.read_dbf(z.read(dbf[0]), COUSUB_FIELDS, dbf[0])


def features(path):
    with open(path) as f:
        return pd.DataFrame([feat["properties"] for feat in json.load(f)["features"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="plots/maine/.data")
    data = Path(ap.parse_args().data)
    bs = spine_module()

    layer = read_cousub(data / "tl_2024_23_cousub.zip", bs)
    spine = pd.read_parquet(data / "graph_spine_spine.parquet")
    edges = pd.read_parquet(data / "graph_edges_edges.parquet")
    megis = features(data / "graph_repair_towns_repaired.geojson")

    header(1, "the 2024 layer against the spine")
    layer_towns, spine_towns = set(layer["GEOID"]), set(spine["cousub"])
    print(f"  2024 layer: {len(layer)} feature(s), {len(layer_towns)} GEOID(s)")
    print(f"  spine: {len(spine_towns)} town(s)")
    print(f"  in the layer, not the spine: {sorted(layer_towns - spine_towns) or 'none'}")
    print(f"  in the spine, not the layer: {sorted(spine_towns - layer_towns) or 'none'}")

    header(2, "functional status, LSAD, class")
    print(layer.groupby(["FUNCSTAT", "LSAD", "CLASSFP"]).size().rename("towns").to_string())
    print("\n  one example name for each LSAD:")
    ex = layer.groupby("LSAD").agg(example=("NAMELSAD", "first"), towns=("GEOID", "size"))
    print(ex.to_string())
    unknown = sorted(set(layer["FUNCSTAT"]) - set("ASFNE"))
    print(f"\n  FUNCSTAT values outside A S F N E: {unknown or 'none'}")

    header(3, "names a flag might rest on")
    for word in ("Plantation", "Plt", "UT", "Unorganized", "Township", "Twp", "Baxter",
                 "Reservation", "Indian", "Island", "Gore", "Grant", "Purchase", "Academy"):
        hit = layer[layer["NAMELSAD"].str.contains(word, case=False, regex=False)]
        if len(hit):
            print(f"  {word}: {len(hit)}, e.g. "
                  + "; ".join(f"{g} {n} [{f}/{l}]" for g, n, f, l in
                              hit[["GEOID", "NAMELSAD", "FUNCSTAT", "LSAD"]].head(4)
                              .itertuples(index=False)))

    header(4, "reservation subdivisions by geometry")
    per = spine.groupby("cousub").agg(
        blocks=("GEOID", "size"),
        in_r=("aiannh_comptyp", lambda c: int((c == "R").sum())),
        persons=("persons", "sum"))
    whole = per[per["blocks"] == per["in_r"]].join(
        layer.set_index("GEOID")[["NAMELSAD", "FUNCSTAT", "LSAD"]])
    print(f"  towns whose every block is in an R area: {len(whole)}")
    print(whole.to_string())
    part = per[(per["in_r"] > 0) & (per["in_r"] < per["blocks"])].join(
        layer.set_index("GEOID")[["NAMELSAD", "FUNCSTAT"]])
    print(f"\n  towns partly in an R area (not reservation subdivisions): {len(part)}")
    print(part.to_string())

    header(5, "LURC")
    lurc = megis.assign(GEOCODE=megis["GEOCODE"].astype(str),
                        LURC=megis["LURC"].astype(str).str.lower())
    per_div = lurc.groupby("GEOCODE")["LURC"].agg(lambda v: "".join(sorted(set(v))))
    kinds = per_div.map({"y": "all y", "n": "all n"}).fillna("mixed")
    print(kinds.value_counts().rename("divisions").to_string())
    mixed = lurc[lurc["GEOCODE"].isin(kinds[kinds == "mixed"].index)]
    print("\n  the mixed divisions, with polygons by value:")
    print(mixed.groupby(["GEOCODE", "TOWN", "LURC"]).size().unstack(fill_value=0).to_string())
    div = edges[edges["from_authority"] == "megis"].assign(kind=lambda e: e["from_code"].map(kinds))
    towns = div.groupby("to_code")["kind"].agg(lambda k: ",".join(sorted(set(k.dropna()))))
    print("\n  Census towns by the LURC kinds of the divisions they touch:")
    print(towns.value_counts().rename("towns").to_string())


if __name__ == "__main__":
    main()
