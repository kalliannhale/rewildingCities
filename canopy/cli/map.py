"""canopy/cli/map.py ~ `rewilding map`: render a result to a map.

A vector result draws its own geometry. A tabular result (like pci_results) has
no geometry ~ it declares that it joins to a vector layer. So map performs that
join: it loads the layer's geometry, reads the result, joins on the shared id,
and colors each feature by the result's value ~ parks colored by cooling. When it
cannot (no geometry, no shared key), it falls back to a descriptor via visuals.
The door does not lock on seeing.

Two refusals, added in Civic Sprint 2b. When more than one envelope could be the
result or the layer, map refuses and names them rather than taking the first by
filename; --result and --layer choose (MAP-1). And a long-form indicator_values
table holds many indicators in one `value` column, so --indicator picks one, and
it joins on its declared key: `unit_code`, a Census GEOID, to the layer's GEOID.
A layer without a GEOID is refused by name, never matched on a county name. ~
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ._common import find_root

_KEY_CANDIDATES = ("feature_id", "park_id", "id", "OBJECTID", "gid")

# a long-form indicator_values table names its unit by (unit_authority,
# unit_code). for us_census_geoid the layer must carry the same code as GEOID.
_LONG_FORM_COLUMNS = {"indicator", "unit_code", "value"}
_UNIT_KEYS = {"us_census_geoid": "GEOID"}
_EMPTY_FILL = "#d9d9d9"


class MapRefusal(Exception):
    """map declines, with the reason and what would let it proceed."""


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "map", help="render a result to a map (parks colored by the result; geojson + ArcGIS)")
    p.add_argument("plot", help="the plot name, e.g. nyc")
    p.add_argument("semantic_type", nargs="?", default="",
                   help="the result type to map, e.g. pci_results")
    p.add_argument("--indicator", default=None,
                   help="for indicator_values: which indicator to map, e.g. cii_broadband")
    p.add_argument("--layer", default=None,
                   help="the envelope to draw on, by name, when more than one could be")
    p.add_argument("--result", default=None,
                   help="the result envelope, by name, when more than one has this type")
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


def _plain(v):
    """a cell as JSON can hold it: numpy scalars unwrapped, NaN as None. ~"""
    v = v.item() if hasattr(v, "item") else v
    if isinstance(v, float) and v != v:
        return None
    return v


def is_long_form(df) -> bool:
    return _LONG_FORM_COLUMNS.issubset(set(df.columns))


def long_form_view(df, indicator):
    """one indicator out of a long-form table, keyed for its layer.

    returns (frame, key, color_by). refuses when no indicator is named, when it
    is not in the table, or when the unit authority has no known layer key. ~"""
    available = sorted(df["indicator"].dropna().unique().tolist())
    if not indicator:
        raise MapRefusal(
            "this table holds several indicators in one `value` column, so one "
            "must be chosen. available: " + ", ".join(available) +
            "\n   add --indicator <id>")
    if indicator not in available:
        raise MapRefusal(
            f"no indicator '{indicator}' in this table. available: " + ", ".join(available))
    one = df[df["indicator"] == indicator].copy()
    authorities = sorted(one["unit_authority"].dropna().unique().tolist()) \
        if "unit_authority" in one.columns else []
    if len(authorities) != 1 or authorities[0] not in _UNIT_KEYS:
        raise MapRefusal(
            f"units are named by {authorities or 'no declared authority'}; map knows "
            f"how to join {', '.join(_UNIT_KEYS)} only.")
    key = _UNIT_KEYS[authorities[0]]
    one = one.rename(columns={"unit_code": key})
    # a standings table carries the raw value beside the percentile; it is the
    # standing that table exists to show, so it is what the map colors by.
    color_by = "percentile" if "percentile" in one.columns else "value"
    return one, key, color_by


def _join_and_color(df, features, meta, layer, plot, key=None, color_by=None) -> dict:
    """join a tabular result (DataFrame) onto vector geometry on a shared id
    column, color each joined feature by the dependent-ish numeric column, and
    return a self-describing choropleth FeatureCollection. a caller that knows
    the key and the value column passes them, rather than letting a column
    name that happens to be shared decide. ~"""
    import pandas as pd

    geo_props = set(features[0].get("properties", {}).keys()) if features else set()
    if key is None:
        shared = [c for c in df.columns if c in geo_props] or \
                 [c for c in _KEY_CANDIDATES if c in df.columns and c in geo_props]
        key = shared[0] if shared else None
    elif key not in geo_props:
        raise MapRefusal(
            f"the layer has no '{key}' property to join on. its properties: "
            f"{', '.join(sorted(geo_props)) or '(none)'}. the join must be derivable: "
            f"give the layer a {key} upstream rather than matching on names.")
    if key is None:
        return {}

    if color_by is None:
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
            props[c] = _plain(row[c])
        joined.append({"type": "Feature", "properties": props, "geometry": f.get("geometry")})

    n_empty = 0
    if color_by and joined:
        vals = [f["properties"].get(color_by) for f in joined]
        present = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if present:
            ramp = iter(_color_ramp(present))
            for f, v in zip(joined, vals):
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    f["properties"]["fill"] = next(ramp)
                    f["properties"]["fill-opacity"] = 0.7
                else:
                    # an empty value is drawn as empty, never as the low end
                    # of the ramp. it is a gap, and a gap is not a zero.
                    f["properties"]["fill"] = _EMPTY_FILL
                    f["properties"]["fill-opacity"] = 0.4
                    n_empty += 1

    return {
        "type": "FeatureCollection",
        "features": joined,
        "rewilding:map": {
            "layer": layer, "join_on": key, "color_by": color_by,
            "semantic_type": meta.get("semantic_type"),
            "caption": " ".join(meta.get("interpretation_notes") or []).strip(),
            "unjoined_rows": len(df) - len(joined),
            "empty_values": n_empty,
        },
        "rewilding:provenance": {
            "result_semantic_type": meta.get("semantic_type"),
            "joined_to": layer, "lineage": meta.get("lineage"), "plot": plot,
        },
    }


def _vector_layers(by_name: dict) -> dict:
    return {n: e for n, e in by_name.items()
            if (e.get("metadata") or {}).get("data_category") == "vector"
            and (e.get("data") or {}).get("format") == "geojson"}


def resolve_layer(meta: dict, by_name: dict, layer_arg: str | None = None):
    """which vector envelope a tabular result draws on.

    named with --layer, it must exist. otherwise the result's joins_to narrows
    the candidates to that semantic type. one candidate is the answer; none
    means there is nothing to draw on; more than one is a choice, refused with
    the names to choose from. it used to be the first by filename (MAP-1). ~"""
    vectors = _vector_layers(by_name)
    if layer_arg:
        if layer_arg not in vectors:
            raise MapRefusal(
                f"no vector layer named '{layer_arg}'. vector layers here: "
                f"{', '.join(sorted(vectors)) or '(none)'}")
        return layer_arg, vectors[layer_arg]
    wanted = meta.get("joins_to")
    candidates = {n: e for n, e in vectors.items()
                  if (e.get("metadata") or {}).get("semantic_type") == wanted} \
        if wanted else vectors
    if not candidates:
        return None
    if len(candidates) > 1:
        what = f" of type {wanted}" if wanted else ""
        raise MapRefusal(
            f"{len(candidates)} layers{what} could be drawn on: "
            f"{', '.join(sorted(candidates))}. choose one with --layer <name>.")
    return next(iter(candidates.items()))


def _choropleth(result_env, by_name, out_dir, plot, indicator=None, layer_arg=None):
    """find the vector layer this tabular result draws on, read the result, join
    and color. returns a summary dict, or None when there is nothing to draw on. ~"""
    meta = result_env.get("metadata") or {}
    resolved = resolve_layer(meta, by_name, layer_arg)
    if resolved is None:
        return None
    layer_name, layer_env = resolved

    geo_path = (layer_env.get("data") or {}).get("path")
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

    key = color_by = None
    if is_long_form(df):
        df, key, color_by = long_form_view(df, indicator)
    elif indicator:
        raise MapRefusal("--indicator applies to long-form indicator tables only.")

    fc = _join_and_color(df, features, meta, layer_name, plot, key=key, color_by=color_by)
    if not fc.get("features"):
        return None
    if indicator:
        fc["rewilding:map"]["indicator"] = indicator

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    name = f"map_{indicator}.geojson" if indicator else "map.geojson"
    path = Path(out_dir) / name
    path.write_text(json.dumps(fc, indent=2))
    m = fc["rewilding:map"]
    return {"path": str(path), "key": m["join_on"], "color_by": m["color_by"],
            "layer": layer_name, "n": len(fc["features"]),
            "empty": m["empty_values"], "unjoined": m["unjoined_rows"]}


def _load_envelopes(envelopes_dir: Path) -> dict:
    by_name: dict[str, dict] = {}
    for ep in sorted(envelopes_dir.glob("*.envelope.json")):
        try:
            by_name[ep.name[: -len(".envelope.json")]] = json.loads(ep.read_text())
        except Exception:
            continue
    return by_name


def _type_of(doc: dict) -> str | None:
    return (doc.get("metadata") or {}).get("semantic_type")


def resolve_result(by_name: dict, target: str, result_arg: str | None = None):
    matches = {n: d for n, d in by_name.items() if _type_of(d) == target}
    if result_arg:
        if result_arg not in matches:
            raise MapRefusal(
                f"no {target} envelope named '{result_arg}'. {target} here: "
                f"{', '.join(sorted(matches)) or '(none)'}")
        return result_arg, matches[result_arg]
    if not matches:
        types = sorted({t for t in map(_type_of, by_name.values()) if t})
        raise MapRefusal(f"no envelope of type '{target}'. available: {', '.join(types)}")
    if len(matches) > 1:
        raise MapRefusal(
            f"{len(matches)} envelopes are {target}: {', '.join(sorted(matches))}. "
            f"choose one with --result <name>.")
    return next(iter(matches.items()))


def run(args) -> int:
    root = find_root()
    plot = args.plot
    envelopes_dir = root / "plots" / plot / ".envelopes"
    if not envelopes_dir.is_dir():
        print(f"no plots/{plot}/.envelopes ~ nothing to map.", file=sys.stderr)
        return 2

    by_name = _load_envelopes(envelopes_dir)

    if not args.semantic_type:
        print("which result to map? available in this plot:")
        by_type: dict[str, list[str]] = {}
        for n, d in by_name.items():
            t = _type_of(d)
            if t:
                by_type.setdefault(t, []).append(n)
        for st in sorted(by_type):
            cat = (by_name[by_type[st][0]].get("metadata") or {}).get("data_category", "?")
            names = f"  [{', '.join(by_type[st])}]" if len(by_type[st]) > 1 else ""
            print(f"   {st}  ({cat}){names}")
        return 1

    target = args.semantic_type
    indicator = getattr(args, "indicator", None)
    try:
        result_name, env = resolve_result(by_name, target, getattr(args, "result", None))
        out_dir = root / "plots" / plot / "harvest"
        cat = (env.get("metadata") or {}).get("data_category")

        if cat == "tabular":
            cho = _choropleth(env, by_name, out_dir, plot,
                              indicator=indicator, layer_arg=getattr(args, "layer", None))
            if cho:
                what = indicator or target
                print(f"🗺  mapped {what} as a choropleth")
                print(f"   {cho['n']} features of {cho['layer']} colored by "
                      f"{cho['color_by']}, joined on {cho['key']}")
                if cho["empty"]:
                    print(f"   {cho['empty']} drawn as empty: no value, not zero")
                if cho["unjoined"]:
                    print(f"   {cho['unjoined']} row(s) of the result matched no feature")
                print(f"   {cho['path']}")
                return 0
            print(f"   (no geometry to join {target} to ~ writing a descriptor instead)")
    except MapRefusal as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1

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