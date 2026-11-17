"""
canopy/aws/display.py ~ display copies (Contract 2, section 4)

a display copy is a GeoJSON drawn for a web map from one canonical version,
read back from the bucket by its sha256, never from a laptop's copy. it lives
under that version and cannot outlive or be confused with it:

  versions/<sha256>/display/<name>.geojson          the copy
  versions/<sha256>/display/<name>.envelope.json    derived_from <sha256>, and every change

what drawing changes, each a rule 11 record in the copy's own provenance entry:

  simplified      polygons as one coverage (shapely's coverage_simplify), so
                  neighbours keep one shared edge and no crack opens between
                  towns; in meters, in UTM zone 19N. points: nothing to
                  simplify, said with count 0
  rounded         coordinates to 6 decimal places of a degree, about 10 cm
  format_changed  GeoParquet to GeoJSON (RFC 7946) in EPSG:4326, naming the
                  transformation pyproj chose; every property kept. GeoJSON
                  has no date type, so a date or time is written as ISO 8601
                  text and a missing one as null, each such field named

refused rather than drawn: a coverage that is not valid (its towns overlap or
leave gaps before anything is simplified), a geometry left empty by
simplification (a town vanished from the map), mixed or unknown geometry.

the copy carries no note text inside it. its envelope keeps the version's
lineage and notes, so the gate judges it as it judged the version, and it
names the allow record current when it was drawn; a note settled later moves
the allow record (D-320) without a new copy. ~
"""

from __future__ import annotations

import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

PRIMITIVE = "make_display_copy"
VERSION = "1.0.0"
DEFAULT_TOLERANCE_M = 25
PROJECTED = "EPSG:26919"
WEB = "EPSG:4326"
DECIMALS = 6
GEOJSON_TYPE = "application/geo+json"

_POINTS = {"Point", "MultiPoint"}
_POLYGONS = {"Polygon", "MultiPolygon"}
# what a version's metadata says about its own geometry, which a copy redraws
_STALE_META = ("total_area_m2", "geometry_type_native")


def _refusal(reason: str, would_admit: str):
    from canopy.aws.s3 import CanonicalRefusal
    return CanonicalRefusal(reason, would_admit)


def display_name(kind: str, tolerance_m: int) -> str:
    """`web` for points, `web_<tolerance>m` for polygons, so a copy drawn at
    another tolerance is another copy and never a second set of bytes under
    one name."""
    if kind == "points":
        return "web"
    if not isinstance(tolerance_m, int) or isinstance(tolerance_m, bool) or tolerance_m <= 0:
        raise _refusal(f"a tolerance is a whole number of meters above zero; got {tolerance_m!r}",
                       "give --tolerance as meters, e.g. 25")
    return f"web_{tolerance_m}m"


def draw(parquet_bytes: bytes, *, tolerance_m: int = DEFAULT_TOLERANCE_M,
         id_field: str | None = None) -> dict:
    """a GeoParquet version drawn as a web GeoJSON. returns the bytes, the
    publication records (step, detail, count), the copy's kind and what its
    metadata should say."""
    import geopandas
    import numpy
    import pyproj
    import shapely

    with tempfile.TemporaryDirectory(prefix="display-") as tmp:
        path = Path(tmp) / "version.parquet"
        path.write_bytes(parquet_bytes)
        frame = geopandas.read_parquet(path)
    if frame.crs is None:
        raise _refusal("the version's GeoParquet declares no crs", "rewrite it with its crs")
    source_crs = frame.crs.to_string()
    geoms = numpy.asarray(frame.geometry)
    if bool(numpy.any(shapely.is_missing(geoms) | shapely.is_empty(geoms))):
        raise _refusal("the version holds an empty geometry", "repair it upstream")
    names = set(frame.geom_type.tolist())
    if names <= _POINTS:
        kind = "points"
    elif names <= _POLYGONS:
        kind = "polygons"
    else:
        raise _refusal(f"a display copy draws points or polygons, one kind; this holds "
                       f"{', '.join(sorted(names))}", "split it upstream")
    name = display_name(kind, tolerance_m)
    vertices_before = int(shapely.get_num_coordinates(geoms).sum())
    steps: list[dict] = []

    if kind == "polygons":
        projected = frame.to_crs(PROJECTED)
        coverage = numpy.asarray(projected.geometry)
        if not bool(shapely.coverage_is_valid(coverage)):
            bad = shapely.coverage_invalid_edges(coverage)
            n_bad = int((~shapely.is_empty(bad)).sum())
            raise _refusal(
                f"the polygons are not a valid coverage: {n_bad} of them overlap a "
                f"neighbour or leave a gap, so simplifying them as one would draw cracks",
                "repair the coverage upstream, then write a new version")
        simple = shapely.coverage_simplify(coverage, tolerance_m)
        gone = shapely.is_empty(simple)
        if bool(numpy.any(gone)):
            ids = (frame[id_field].astype(str)[gone].tolist() if id_field in frame.columns
                   else [str(i) for i in frame.index[gone]])
            raise _refusal(
                f"simplifying at {tolerance_m} m left {len(ids)} geometry empty "
                f"({', '.join(ids[:5])}): it would vanish from the map",
                "a smaller --tolerance")
        projected = projected.set_geometry(
            geopandas.GeoSeries(simple, index=projected.index, crs=PROJECTED))
        frame = projected.to_crs(WEB)
        vertices_simple = int(shapely.get_num_coordinates(numpy.asarray(frame.geometry)).sum())
        steps.append({"step": "simplified", "count": int(len(frame)), "detail": (
            f"polygons simplified as one coverage (shapely {shapely.__version__} "
            f"coverage_simplify, GEOS {shapely.geos_version_string}), so neighbours keep "
            f"one shared edge; tolerance {tolerance_m} m in {PROJECTED}, roughly the square "
            f"root of the area of each triangle removed; vertices {vertices_before:,} to "
            f"{vertices_simple:,}")})
    else:
        frame = frame.to_crs(WEB) if source_crs != WEB else frame
        steps.append({"step": "simplified", "count": 0,
                      "detail": "points: nothing to simplify"})

    rounded = shapely.transform(numpy.asarray(frame.geometry),
                                lambda c: numpy.round(c, DECIMALS))
    frame = frame.set_geometry(geopandas.GeoSeries(rounded, index=frame.index, crs=WEB))
    steps.append({"step": "rounded", "count": int(len(frame)), "detail": (
        f"coordinates rounded to {DECIMALS} decimal places of a degree, about 10 cm")})

    as_text = []
    for col in [c for c in frame.columns if c != frame.geometry.name]:
        if str(frame[col].dtype).startswith("datetime64"):
            frame[col] = [None if v is None or v != v else v.isoformat() for v in frame[col]]
            as_text.append(col)
        elif frame[col].dtype == object and any(hasattr(v, "isoformat") for v in frame[col]):
            frame[col] = [v.isoformat() if hasattr(v, "isoformat") else v for v in frame[col]]
            as_text.append(col)
    operation = ("no reprojection" if source_crs == WEB else
                 pyproj.Transformer.from_crs(source_crs, WEB, always_xy=True).description)
    dates = (f"; dates and times written as ISO 8601 text, a missing one as null "
             f"({', '.join(as_text)})" if as_text else "")
    steps.append({"step": "format_changed", "count": int(len(frame)), "detail": (
        f"GeoParquet to GeoJSON (RFC 7946) in {WEB}, from {source_crs} by {operation}; "
        f"every property kept{dates}")})

    body = frame.to_json(drop_id=True).encode("utf-8")
    final = numpy.asarray(frame.geometry)
    stats = {
        "feature_count": int(len(frame)),
        "geometry_type": "Point" if kind == "points" else "MultiPolygon"
        if "MultiPolygon" in names else "Polygon",
        "bbox": [round(float(v), DECIMALS) for v in frame.total_bounds],
        "vertex_count": int(shapely.get_num_coordinates(final).sum()),
        "vertices_before": vertices_before,
        "size_bytes": len(body),
        "attribute_fields": [c for c in frame.columns if c != frame.geometry.name],
        "source_crs": source_crs,
    }
    return {"bytes": body, "steps": steps, "kind": kind, "name": name, "stats": stats}


def display_envelope(receipt: dict, *, display_key: str, data_url: str, sha256: str,
                     allow_sha256: str, harvest: str, drawn: dict, params: dict,
                     duration_seconds: float, now: datetime | None = None) -> dict:
    """the copy's own envelope: the version's lineage, notes and provenance,
    inherited under the branch `version`, then this drawing's entry, whose
    publication list holds every change it made."""
    at = (now or datetime.now(timezone.utc)).isoformat()
    meta = {k: v for k, v in (receipt.get("metadata") or {}).items() if k not in _STALE_META}
    stats = drawn["stats"]
    meta.update({
        "data_category": "vector", "crs": WEB,
        "feature_count": stats["feature_count"], "geometry_type": stats["geometry_type"],
        "bbox": stats["bbox"], "vertex_count": stats["vertex_count"],
        "size_bytes": stats["size_bytes"], "attribute_fields": stats["attribute_fields"],
        "derived_from": sha256, "allow": allow_sha256, "display_of": harvest,
        "display_name": drawn["name"],
    })
    inherited = []
    for entry in receipt.get("provenance") or []:
        e = dict(entry)
        if e.get("lineage_branch") is None:
            e["lineage_branch"] = "version"
        inherited.append(e)
    own = {
        "primitive": PRIMITIVE, "version": VERSION, "timestamp": at, "params": params,
        "inputs": [{"name": "version", "semantic_type": meta.get("semantic_type"),
                    "path": data_url,
                    "hash": {"value": sha256, "method": "full_file", "algorithm": "sha256"}}],
        "duration_seconds": round(float(duration_seconds), 3), "lineage_branch": None,
        "publication": [dict(s, by=PRIMITIVE, at=at) for s in drawn["steps"]],
    }
    return {"data": {"path": display_key, "format": "geojson", "secondary": {}},
            "metadata": meta, "provenance": inherited + [own],
            "warnings": list(receipt.get("warnings") or [])}


def timed(fn, *args, **kwargs):
    started = time.monotonic()
    result = fn(*args, **kwargs)
    return result, time.monotonic() - started


def envelope_bytes(envelope: dict) -> bytes:
    return (json.dumps(envelope, indent=2, allow_nan=False) + "\n").encode("utf-8")
