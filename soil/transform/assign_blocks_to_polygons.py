"""
soil/transform/assign_blocks_to_polygons.py  |  rewildingCities

Assigns each 2020 Census block to the polygon containing its internal point
(D-122): how Maine's civil divisions join the geography graph, through blocks,
like every other overlap. A block whose point falls in no polygon (open water,
a gap between layers) gets none and is counted; one whose point falls in two
(an overlap between polygons) is refused by name rather than assigned to
whichever came first.

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:
  points    blocks as features whose attributes carry GEOID, INTPTLAT,
            INTPTLON (the Census 2020 block layer; geometry may be null)
  polygons  the units to assign to, one feature per unit, carrying key_field
Params:
  key_field    the polygons' unit code, required (e.g. GEOCODE)
  output_name  the output column for the code (default "division")
Output: GEOID, <output_name>, csv or parquet by the output's extension.
"""

from __future__ import annotations

import json

try:
    from canopy.pr_io import (parse_primitive_args, get_input, get_param, require_param,
                              WarningsCollector, primitive_success, primitive_failure,
                              primitive_error_handling)
except ImportError:
    from pr_io import (parse_primitive_args, get_input, get_param, require_param,
                       WarningsCollector, primitive_success, primitive_failure,
                       primitive_error_handling)


def assign(points, polygons, key_field, output_name, w):
    import pandas as pd
    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree

    geoms, codes = [], []
    for f in polygons:
        code = (f.get("properties") or {}).get(key_field)
        if f.get("geometry") is None or code in (None, ""):
            continue
        geoms.append(shape(f["geometry"]))
        codes.append(str(code))
    if not geoms:
        primitive_failure("No polygons", f"no polygon carries '{key_field}' and a geometry")
    if len(set(codes)) != len(codes):
        primitive_failure("Polygons not one per unit",
                          f"'{key_field}' repeats; dissolve to one feature per unit first")
    tree = STRtree(geoms)

    rows, unplaced, twice = [], 0, []
    for f in points:
        p = f.get("properties") or {}
        gid = str(p.get("GEOID"))
        pt = Point(float(p["INTPTLON"]), float(p["INTPTLAT"]))
        hits = [i for i in tree.query(pt) if geoms[i].contains(pt)]
        if len(hits) > 1:
            twice.append(gid)
        code = codes[hits[0]] if len(hits) == 1 else None
        unplaced += code is None and not hits
        rows.append({"GEOID": gid, output_name: code})
    if twice:
        primitive_failure("Block in two polygons",
                          f"{len(twice)} block point(s) fall in more than one unit, e.g. {twice[0]}")
    if unplaced:
        w.info(f"{unplaced} block point(s) fall in no unit (water or a gap); they are left unassigned")
    w.info(f"assigned {len(rows) - unplaced} of {len(rows)} block(s) to {len(set(codes))} unit(s)")
    return pd.DataFrame(rows)


def main():
    args = parse_primitive_args()
    w = WarningsCollector("assign_blocks_to_polygons")
    with primitive_error_handling(w):
        points = json.load(open(get_input(args["inputs"], "points")))["features"]
        polygons = json.load(open(get_input(args["inputs"], "polygons")))["features"]
        out_name = get_param(args["params"], "output_name", "division")
        frame = assign(points, polygons, require_param(args["params"], "key_field"), out_name, w)
        if str(args["output"]).endswith(".parquet"):
            frame.to_parquet(args["output"], index=False)
        else:
            frame.to_csv(args["output"], index=False)
        primitive_success({"data_category": "tabular", "crs": None, "row_count": len(frame),
                           "id_field": "GEOID", "variables": list(frame.columns)}, w)


if __name__ == "__main__":
    main()
