"""canopy/cli/map.py ~ `rewilding map`: render a result to a map.

A vector result draws its own geometry. A tabular result (like pci_results) has
no geometry ~ it declares that it joins to a vector layer. So map performs that
join: it loads the layer's geometry, reads the result, joins on the shared id,
and colors each feature by the result's value ~ parks colored by cooling. When it
cannot (no geometry, no shared key), it falls back to a descriptor via visuals.
The door does not lock on seeing. ~
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ._common import find_root

_KEY_CANDIDATES = ("feature_id", "park_id", "id", "OBJECTID", "gid")


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "map", help="render a result to a map (parks colored by the result; geojson + ArcGIS)")
    p.add_argument("plot", help="the plot name, e.g. nyc")
    p.add_argument("semantic_type", nargs="?", default="",
                   help="the result type to map, e.g. pci_results")
    p.set_defaults(func=run)


def _hex(rgb) -> str:
    return "#" + "".join(f"{int(round(c)):02x}" for c in rgb)


def _color_ramp(values):
    """a simple sequential ramp (light -> deep blue) over the values, so the
    geojson renders colored in any viewer that reads simplestyle 'fill'. ~"""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    c0, c1 = (247, 251, 255), (8, 48, 107)
    return [_hex(tuple(c0[i] + ((v - lo) / span) * (c1[i] - c0[i]) for i in range(3)))
            for v in values]


def _join_and_color(df, features, meta, layer, plot) -> dict:
    """join a tabular result (DataFrame) onto vector geometry on a shared id
    column, color each joined feature by the dependent-ish numeric column, and
    return a self-describing choropleth FeatureCollection. ~"""
    import pandas as pd

    geo_props = set(features[0].get("properties", {}).keys()) if features else set()
    shared = [c for c in df.columns if c in geo_props] or \
             [c for c in _KEY_CANDIDATES if c in df.columns and c in geo_props]
    key = shared[0] if shared else None
    if key is None:
        return {}

    numeric = [c for c in df.columns
               if c != key and pd.api.types.is_numeric_dtype(df[c])]
    declared = (meta.get("statistical_context") or {}).get("dependent_variable")
    color_by = declared if declared in df.columns else (
        next((c for c in numeric if "pci" in c.lower()), None) or (numeric[0] if numeric else None))

    lookup = {str(r[key]): r for _, r in df.iterrows()}
    joined = []
    for f in features:
        row = lookup.get(str(f.get("properties", {}).get(key)))
        if row is None:
            continue
        props = dict(f.get("properties", {}))
        for c in df.columns:
            v = row[c]
            props[c] = v.item() if hasattr(v, "item") else v
        joined.append({"type": "Feature", "properties": props, "geometry": f.get("geometry")})

    if color_by and joined:
        vals = [f["properties"].get(color_by) for f in joined]
        if all(isinstance(v, (int, float)) for v in vals):
            for f, col in zip(joined, _color_ramp(vals)):
                f["properties"]["fill"] = col
                f["properties"]["fill-opacity"] = 0.7

    return {
        "type": "FeatureCollection",
        "features": joined,
        "rewilding:map": {
            "layer": layer, "join_on": key, "color_by": color_by,
            "semantic_type": meta.get("semantic_type"),
            "caption": " ".join(meta.get("interpretation_notes") or []).strip(),
        },
        "rewilding:provenance": {
            "result_semantic_type": meta.get("semantic_type"),
            "joined_to": layer, "lineage": meta.get("lineage"), "plot": plot,
        },
    }


def _choropleth(result_env, envelopes, out_dir, plot):
    """find the vector layer this tabular result draws on, read the result, join
    and color. returns (path, key, color_by, layer, n) or None if it cannot. ~"""
    meta = result_env.get("metadata") or {}
    layer = meta.get("joins_to")
    if not layer or layer not in envelopes:
        layer = next((st for st, e in envelopes.items()
                      if (e.get("metadata") or {}).get("data_category") == "vector"
                      and (e.get("data") or {}).get("format") == "geojson"), None)
    if not layer or layer not in envelopes:
        return None

    geo_path = (envelopes[layer].get("data") or {}).get("path")
    res_path = (result_env.get("data") or {}).get("path")
    if not (geo_path and Path(geo_path).exists() and res_path and Path(res_path).exists()):
        return None

    try:
        import pandas as pd
        df = pd.read_parquet(res_path)
        features = json.loads(Path(geo_path).read_text()).get("features", [])
    except Exception as e:
        print(f"   (could not read data for a choropleth: {e})", file=sys.stderr)
        return None

    fc = _join_and_color(df, features, meta, layer, plot)
    if not fc.get("features"):
        return None

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    path = Path(out_dir) / "map.geojson"
    path.write_text(json.dumps(fc, indent=2))
    m = fc["rewilding:map"]
    return str(path), m["join_on"], m["color_by"], layer, len(fc["features"])


def run(args) -> int:
    root = find_root()
    plot = args.plot
    envelopes_dir = root / "plots" / plot / ".envelopes"
    if not envelopes_dir.is_dir():
        print(f"no plots/{plot}/.envelopes ~ nothing to map.", file=sys.stderr)
        return 2

    envelopes: dict[str, dict] = {}
    for ep in sorted(envelopes_dir.glob("*.envelope.json")):
        try:
            doc = json.loads(ep.read_text())
        except Exception:
            continue
        st = (doc.get("metadata") or {}).get("semantic_type")
        if st and st not in envelopes:
            envelopes[st] = doc

    if not args.semantic_type:
        print("which result to map? available in this plot:")
        for st in sorted(envelopes):
            cat = (envelopes[st].get("metadata") or {}).get("data_category", "?")
            print(f"   {st}  ({cat})")
        return 1

    target = args.semantic_type
    if target not in envelopes:
        print(f"no envelope of type '{target}' in plots/{plot}/.envelopes.", file=sys.stderr)
        print("available: " + ", ".join(sorted(envelopes)), file=sys.stderr)
        return 1

    out_dir = root / "plots" / plot / "harvest"
    env = envelopes[target]
    cat = (env.get("metadata") or {}).get("data_category")

    if cat == "tabular":
        cho = _choropleth(env, envelopes, out_dir, plot)
        if cho:
            path, key, color_by, layer, n = cho
            print(f"🗺  mapped {target} as a choropleth")
            print(f"   {n} {layer} colored by {color_by}, joined on {key}")
            print(f"   {path}")
            return 0
        print(f"   (no geometry to join {target} to ~ writing a descriptor instead)")

    from canopy.visuals import render
    result = render(env, out_dir, plot=plot)
    spec = result.spec
    try:
        n = len(json.loads(Path(result.geojson_path).read_text()).get("features", []))
    except Exception:
        n = 0
    bits = []
    if spec.color_by:
        bits.append(f"colored by {spec.color_by}")
    if spec.layer:
        bits.append(f"joins to {spec.layer}")
    bits.append(f"{n} feature(s)")
    print(f"🗺  mapped {target}")
    print("   " + ", ".join(bits))
    print(f"   {result.geojson_path}")
    if result.arcgis_url:
        print(f"   published: {result.arcgis_url}")
    return 0
