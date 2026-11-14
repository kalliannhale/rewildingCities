"""
soil/transform/build_located_in.py  |  rewildingCities

located_in edges (Contract 3, section 2): every point of a declared layer to
every area it falls in, weights 1 and 1. a point is never a place (D-103):
it is named only here, by its layer and feature id.

each level comes from what that level is defined on (Sprint 06, step 2):

  ~ state, county, town   the 2024 topological face the point falls in. a
                          face never straddles a boundary, so this is exact,
                          even inside a block a 2024 line split
  ~ sldl, sldu, aiannh    the face's 2020 block, through the spine. districts
                          and tribal areas are defined on whole blocks (the
                          equivalency files, the block assignment file), so
                          the block is exact for them, and a point can never
                          land in a district its block's overlaps edges deny
  ~ megis division        the block's division, as the graph assigns it (D-122)

a point whose face town differs from its block's spine town sits in a split
block (D-126): it is placed by its face and listed as split, so the rare
disagreement shows rather than hides. a point in no face, or in a block the
spine does not hold, is listed as unplaced and gets no edge; it is never
dropped silently and never placed by a guess.

a point on the line between faces that disagree on its block, town or
county is listed as unplaced, naming both: which side a point on a line is
on is a choice, not a lookup. a point with no coordinates is listed too.

the edges are their own artifact, of type located_in_edges, never written
into place_edges: loam makes the edges view from exactly one place_edges
artifact (D-163), and a second would leave every plot with no edges at all
(D-207). same columns, same key, read beside the graph's own edges.

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:
  points     the layer: csv or parquet with id, latitude and longitude
             columns, or geojson of points
  faces      2024 TIGER/Line faces, a county zip or a zip of county zips
  spine      the block spine (build_block_spine)
  places     the places table (build_places)
  divisions  optional: blocks assigned to civil divisions (GEOID, division)
Params:
  layer        required: the label every edge carries as its
               `from_authority` (Contract 3, section 2): whose points and
               which release (imls_pls_fy2024_outlets). a name the run
               gives its edges, never a dataset id or a type; the points'
               type is their own, and a carrier indicator names that
               (D-224)
  id_field     required: the column naming each feature
  lat_field, lon_field   required for a table; ignored for geojson
  points_crs   default EPSG:4326
  check_block_field  optional: a layer property naming each feature's block
               as its publisher placed it. compared with the face's block,
               never used to place; the receipt says how many agree and
               lists every one that does not
  state_fips   two digits, required
  vintages     required mapping: state, county, town, sldl, sldu, aiannh,
               division
Output: the located_in edges, parquet or csv by the output's extension.
Refuses: a feature id used twice in one layer; a placed point the spine
gives no House or Senate district; an edge whose `to` place is not in
places; two edges between one point and one place. ~
"""

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from dataclasses import dataclass, field

import pandas as pd

GEOID, SLDL, SLDU, AIANNH, MEGIS = ("us_census_geoid", "us_census_sldl",
                                    "us_census_sldu", "us_census_aiannh", "megis")
COLUMNS = ["from_authority", "from_code", "to_authority", "to_code", "kind",
           "weight_population", "weight_households", "weight_reason", "source", "vintage"]
KEY = ["from_authority", "from_code", "to_authority", "to_code"]
KIND = "located_in"
FACE_LEVELS = ("state", "county", "town")
BLOCK_LEVELS = ("sldl", "sldu", "aiannh", "division")
REQUIRED_VINTAGES = ("state", "county", "town", "sldl", "sldu", "aiannh", "division")


class LocatedInRefused(ValueError):
    """a placement the contract refuses, with why."""


@dataclass
class Placement:
    edges: pd.DataFrame
    unplaced: list[dict] = field(default_factory=list)
    split: list[dict] = field(default_factory=list)


def _text(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    t = str(x).strip()
    return t or None


def locate(points: pd.DataFrame, spine: pd.DataFrame, divisions: pd.DataFrame | None,
           places: pd.DataFrame, vintages: dict, source: str) -> Placement:
    """
    points     layer, feature_id, block, town, county: each point with the face
               it fell in, its face's 2020 block and 2024 town and county
               (block null when the point fell in no face)
    spine      block, town, sldl, sldu, aiannh: one row per 2020 block
    divisions  block, division (optional, D-122)
    places     authority, code: the places table
    vintages   state, county, town, sldl, sldu, aiannh, division
    """
    missing = [k for k in REQUIRED_VINTAGES if k not in (vintages or {})]
    if missing:
        raise LocatedInRefused(f"vintages must declare {', '.join(missing)}")

    dup = points[points.duplicated(["layer", "feature_id"], keep=False)]
    if len(dup):
        ids = sorted({f"{r.layer}:{r.feature_id}" for r in dup.itertuples()})
        raise LocatedInRefused(f"a feature id names one feature in its layer; used "
                               f"twice: {', '.join(ids[:10])}")

    by_block = spine.set_index("block")
    division_of = ({} if divisions is None
                   else dict(zip(divisions["block"].astype(str), divisions["division"].astype(str))))
    known = set(zip(places["authority"].astype(str), places["code"].astype(str)))

    rows, unplaced, split = [], [], []
    for p in points.itertuples(index=False):
        who = {"layer": p.layer, "feature_id": str(p.feature_id)}
        block = _text(p.block)
        if block is None:
            why = _text(getattr(p, "why_unplaced", None))
            unplaced.append({**who, "why": why or "the point falls in no 2024 face in this state"})
            continue
        if block not in by_block.index:
            unplaced.append({**who, "why": f"its face's block {block} is not in the spine"})
            continue
        b = by_block.loc[block]
        town, county = _text(p.town), _text(p.county)
        if _text(b["town"]) != town:
            split.append({**who, "block": block, "face_town": town,
                          "block_town": _text(b["town"])})
        sldl, sldu = _text(b["sldl"]), _text(b["sldu"])
        if not (sldl and sldu):
            raise LocatedInRefused(f"{p.layer}:{p.feature_id} lies in block {block}, which "
                                   f"the spine gives no House or Senate district")
        to = [(GEOID, county[:2], "state"), (GEOID, county, "county"), (GEOID, town, "town"),
              (SLDL, sldl, "sldl"), (SLDU, sldu, "sldu")]
        aiannh = _text(b.get("aiannh"))
        if aiannh:
            to.append((AIANNH, aiannh, "aiannh"))
        division = division_of.get(block)
        if division:
            to.append((MEGIS, division, "division"))
        for authority, code, level in to:
            rows.append({"from_authority": p.layer, "from_code": str(p.feature_id),
                         "to_authority": authority, "to_code": code, "kind": KIND,
                         "weight_population": 1.0, "weight_households": 1.0,
                         "weight_reason": None, "source": source,
                         "vintage": str(vintages[level])})

    edges = pd.DataFrame(rows, columns=COLUMNS)
    absent = sorted({f"{r.to_authority}:{r.to_code}" for r in edges.itertuples()
                     if (r.to_authority, r.to_code) not in known})
    if absent:
        raise LocatedInRefused(f"an edge's `to` end must be a place; not in places: "
                               f"{', '.join(absent[:10])}")
    if edges.duplicated(KEY).any():
        raise LocatedInRefused("one point has two edges to one place")
    return Placement(edges=edges, unplaced=unplaced, split=split)


def output_metadata(placement: Placement) -> dict:
    """what the receipt says: its key (KEYS-1), and every point it could not
    place or placed inside a split block, by name."""
    return {"data_category": "tabular", "crs": None, "row_count": len(placement.edges),
            "variables": COLUMNS, "id_fields": KEY, "spatial_unit": "edge",
            "unplaced": placement.unplaced, "split_block_points": placement.split}


# ── reading the inputs ──────────────────────────────────────────────────────

FACE_COLUMNS = ["STATEFP20", "COUNTYFP20", "TRACTCE20", "BLOCKCE20",
                "STATEFP", "COUNTYFP", "COUSUBFP"]


def read_table(path):
    if str(path).endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype=str)


def write_table(frame, path):
    if str(path).endswith(".parquet"):
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)


def spine_table(spine: pd.DataFrame) -> pd.DataFrame:
    """the spine in locate's words: a block's town is its 2024 cousub, and its
    tribal area is AIANNH plus its component, the place's code (D-125)."""
    has = spine["aiannh"].notna() & (spine["aiannh"].astype(str).str.strip() != "")
    aiannh = (spine["aiannh"].astype(str) + spine["aiannh_comptyp"].astype(str)).where(has)
    return pd.DataFrame({"block": spine["GEOID"].astype(str), "town": spine["cousub"].astype(str),
                         "sldl": spine["sldl"], "sldu": spine["sldu"], "aiannh": aiannh})


def division_table(divisions: pd.DataFrame | None) -> pd.DataFrame | None:
    if divisions is None:
        return None
    return pd.DataFrame({"block": divisions["GEOID"].astype(str),
                         "division": divisions["division"]}).dropna()


def read_points(path, id_field, lat_field=None, lon_field=None, crs="EPSG:4326",
                check_block_field=None):
    """the layer as points, one per feature; a feature with no usable
    coordinates keeps its row with no geometry, so it can be listed. a
    declared check field travels as declared_block."""
    import geopandas as gpd
    if str(path).lower().endswith((".geojson", ".json")):
        gdf = gpd.read_file(path)
        for col in (id_field, check_block_field):
            if col and col not in gdf.columns:
                raise LocatedInRefused(f"the layer has no field {col!r}")
        out = gpd.GeoDataFrame({"feature_id": gdf[id_field].astype(str)},
                               geometry=gdf.geometry, crs=gdf.crs or crs)
        if check_block_field:
            out["declared_block"] = gdf[check_block_field].astype("string")
        return out
    table = read_table(path)
    for col in (id_field, lat_field, lon_field):
        if not col or col not in table.columns:
            raise LocatedInRefused(f"the layer has no column {col!r}; a table needs "
                                   f"id_field, lat_field and lon_field")
    lat = pd.to_numeric(table[lat_field], errors="coerce")
    lon = pd.to_numeric(table[lon_field], errors="coerce")
    geom = gpd.points_from_xy(lon, lat)
    gdf = gpd.GeoDataFrame({"feature_id": table[id_field].astype(str)}, geometry=geom, crs=crs)
    gdf.loc[lat.isna() | lon.isna(), "geometry"] = None
    if check_block_field:
        if check_block_field not in table.columns:
            raise LocatedInRefused(f"the layer has no column {check_block_field!r}")
        gdf["declared_block"] = table[check_block_field].astype("string")
    return gdf


def read_face_polygons(path, state_fips):
    """every face polygon in a county zip, or a zip of county zips, with the
    fields that name its 2020 block and its 2024 town and county."""
    import geopandas as gpd
    frames = []

    def read_zip_bytes(raw, label):
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                shp = [n for n in z.namelist() if n.lower().endswith("_faces.shp")]
                if len(shp) != 1:
                    raise LocatedInRefused(f"{label}: expected one _faces.shp; found {shp}")
                z.extractall(tmp)
            frames.append(gpd.read_file(os.path.join(tmp, shp[0]), columns=FACE_COLUMNS))

    with open(path, "rb") as fh:
        raw = fh.read()
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        names = outer.namelist()
        if any(n.lower().endswith("_faces.shp") for n in names):
            read_zip_bytes(raw, str(path))
        for name in sorted(names):
            if name.lower().endswith(".zip"):
                read_zip_bytes(outer.read(name), name)
    if not frames:
        raise LocatedInRefused(f"no faces shapefile in {path}")
    faces = pd.concat(frames, ignore_index=True)
    faces = faces[faces["STATEFP20"] == state_fips]
    return gpd.GeoDataFrame({
        "block": faces["STATEFP20"] + faces["COUNTYFP20"] + faces["TRACTCE20"] + faces["BLOCKCE20"],
        "town": faces["STATEFP"] + faces["COUNTYFP"] + faces["COUSUBFP"],
        "county": faces["STATEFP"] + faces["COUNTYFP"]}, geometry=faces.geometry, crs=faces.crs)


def faces_for_points(points, faces, layer: str) -> pd.DataFrame:
    """each point with the face it falls in. a point touching faces that
    disagree on block, town or county is on a line, and is listed, naming
    what it touches; a point with no coordinates is listed too."""
    import geopandas as gpd
    rows = []
    has = points[points.geometry.notna()]
    for fid in points.loc[points.geometry.isna(), "feature_id"]:
        rows.append({"layer": layer, "feature_id": fid, "block": None, "town": None,
                     "county": None, "why_unplaced": "the feature has no usable coordinates"})
    if len(has):
        joined = gpd.sjoin(has.to_crs(faces.crs), faces, how="left", predicate="intersects")
        for fid, g in joined.groupby("feature_id", sort=False):
            hits = g.dropna(subset=["block"])[["block", "town", "county"]].drop_duplicates()
            if len(hits) == 1:
                h = hits.iloc[0]
                rows.append({"layer": layer, "feature_id": fid, "block": h["block"],
                             "town": h["town"], "county": h["county"], "why_unplaced": None})
            elif len(hits) == 0:
                rows.append({"layer": layer, "feature_id": fid, "block": None, "town": None,
                             "county": None, "why_unplaced": None})
            else:
                touched = "; ".join(f"block {r.block}, town {r.town}" for r in hits.itertuples())
                rows.append({"layer": layer, "feature_id": fid, "block": None, "town": None,
                             "county": None,
                             "why_unplaced": f"the point is on a line between faces ({touched})"})
    return pd.DataFrame(rows, columns=["layer", "feature_id", "block", "town", "county",
                                       "why_unplaced"])


def block_check(located: pd.DataFrame, points: pd.DataFrame, field: str) -> dict:
    """our face block against the publisher's, for every placed point that
    has both. a check only: it never moves a point."""
    declared = dict(zip(points["feature_id"].astype(str),
                        points["declared_block"].astype(object)))
    disagree, checked = [], 0
    for r in located.itertuples(index=False):
        ours, theirs = _text(r.block), _text(declared.get(str(r.feature_id)))
        if ours is None or theirs is None:
            continue
        checked += 1
        if ours != theirs:
            disagree.append({"feature_id": str(r.feature_id), "ours": ours, "theirs": theirs})
    return {"field": field, "checked": checked, "agree": checked - len(disagree),
            "disagree": disagree}


SOURCE = "2024 TIGER/Line faces (state, county, town); 2020 blocks through the spine (districts, tribal areas, divisions)"


def main():
    try:
        from canopy.pr_io import (parse_primitive_args, get_input, get_param, require_param,
                                  WarningsCollector, primitive_success, primitive_failure,
                                  primitive_error_handling)
    except ImportError:
        from pr_io import (parse_primitive_args, get_input, get_param, require_param,
                           WarningsCollector, primitive_success, primitive_failure,
                           primitive_error_handling)
    args = parse_primitive_args()
    w = WarningsCollector("build_located_in")
    with primitive_error_handling(w):
        i, p = args["inputs"], args["params"]
        layer = str(require_param(p, "layer"))
        state = str(require_param(p, "state_fips")).zfill(2)
        try:
            check_field = get_param(p, "check_block_field")
            points = read_points(get_input(i, "points"), require_param(p, "id_field"),
                                 get_param(p, "lat_field"), get_param(p, "lon_field"),
                                 get_param(p, "points_crs", "EPSG:4326"), check_field)
            located = faces_for_points(points, read_face_polygons(get_input(i, "faces"), state),
                                       layer)
            div_path = get_input(i, "divisions", required=False)
            placement = locate(located, spine_table(read_table(get_input(i, "spine"))),
                               division_table(read_table(div_path) if div_path else None),
                               read_table(get_input(i, "places")),
                               require_param(p, "vintages"), SOURCE)
        except LocatedInRefused as e:
            primitive_failure("located_in refused", str(e))
        w.info(f"{layer}: {len(points)} feature(s), {placement.edges['from_code'].nunique()} placed, "
               f"{len(placement.edges)} edge(s)")
        if placement.unplaced:
            w.warn(f"{len(placement.unplaced)} feature(s) not placed, each listed in the "
                   f"receipt with why")
        if placement.split:
            w.info(f"{len(placement.split)} feature(s) in a split block, placed by their "
                   f"face and listed (D-126)")
        meta = output_metadata(placement)
        if check_field:
            check = block_check(located, points, check_field)
            meta["block_check"] = check
            w.info(f"block check against {check_field}: {check['agree']} of "
                   f"{check['checked']} agree; every disagreement is listed")
        write_table(placement.edges, args["output"])
        primitive_success(meta, w)


if __name__ == "__main__":
    main()
