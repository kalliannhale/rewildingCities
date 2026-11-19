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

  opened          only where a coverage has pinches (COVER-1): two places
                  share one point where each has a hole (removed water)
                  touching its own edge, which GEOS's coverage check refuses
                  though every border matches. each such hole vertex is moved
                  OPEN_PINCH_M into its own hole, so the hole no longer touches
                  the edge; the shared border is not moved. the canonical
                  outline keeps the pinch; only the copy is opened

  marked          an outline drawn as markers (`--display --markers`, D-377): one
                  point on each place's own surface, named `markers`, for the
                  places map; nothing is simplified

a polygon copy's `rounded` record names every shape the rounding leaves
invalid, by id, or says every shape is valid; it is never refused for it
(ROUND-2, D-379), since the door refuses to send an invalid shape (D-368).

refused rather than drawn: a coverage that is not valid for any other reason
(its towns overlap or leave gaps before anything is simplified), a pinch that
opening does not make valid, a geometry left empty by simplification (a town
vanished from the map), mixed or unknown geometry.

a joined copy (D-331, zip 8b) is a long-form table drawn on an outline version:
one wide GeoJSON, every place of the outline and every indicator's columns
beside it, keyed by (authority, code) in canopy/choropleth.py. it lives under
the TABLE's version, named for the outline's version, so it has two parents
and says so: derived_from the table, joined_to the outline (its version, allow
record and lineage), both provenance chains under the branches `table` and
`outline`. polygons are simplified as one coverage, as above; markers are one
point on each place's own surface, simplifying nothing, so a broken coverage
never stops them.

  versions/<table sha>/display/<outline>_<outline sha12>_web_<n>m.geojson
  versions/<table sha>/display/<outline>_<outline sha12>_markers.geojson

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
OPEN_PINCH_M = 0.1       # COVER-1: how far a pinched hole vertex moves into its hole
GEOJSON_TYPE = "application/geo+json"
# a lens's copy (D-396) is sent as plain JSON, which it is, so CloudFront
# compresses it: CloudFront compresses a fixed list of types, application/json
# among them and application/geo+json not, and only files of 1,000 to
# 10,000,000 bytes (COMPRESS-1, D-397). copies already written keep their type.
COMPRESSED_TYPE = "application/json"


def only_key(only) -> str:
    """eight hex characters naming exactly which indicators a lens's copy holds,
    so a changed set is a new name and never new bytes under one (D-322)."""
    import hashlib
    return hashlib.sha256(",".join(sorted(only)).encode("utf-8")).hexdigest()[:8]

_POINTS = {"Point", "MultiPoint"}
_POLYGONS = {"Polygon", "MultiPolygon"}
# what a version's metadata says about its own geometry, which a copy redraws
_STALE_META = ("total_area_m2", "geometry_type_native")


def _refusal(reason: str, would_admit: str):
    from canopy.aws.s3 import CanonicalRefusal
    return CanonicalRefusal(reason, would_admit)


def display_name(kind: str, tolerance_m: int) -> str:
    """`web` for points, `web_<tolerance>m` for polygons, `markers` for an
    outline drawn as one point per place (D-377), so a copy drawn another way
    is another copy and never a second set of bytes under one name."""
    if kind == "points":
        return "web"
    if kind == "markers":
        return "markers"
    if not isinstance(tolerance_m, int) or isinstance(tolerance_m, bool) or tolerance_m <= 0:
        raise _refusal(f"a tolerance is a whole number of meters above zero; got {tolerance_m!r}",
                       "give --tolerance as meters, e.g. 25")
    return f"web_{tolerance_m}m"


def _read_frame(parquet_bytes: bytes):
    import geopandas
    with tempfile.TemporaryDirectory(prefix="display-") as tmp:
        path = Path(tmp) / "version.parquet"
        path.write_bytes(parquet_bytes)
        return geopandas.read_parquet(path)


def _kind_of(frame) -> tuple[str, set]:
    import numpy
    import shapely
    geoms = numpy.asarray(frame.geometry)
    if bool(numpy.any(shapely.is_missing(geoms) | shapely.is_empty(geoms))):
        raise _refusal("the version holds an empty geometry", "repair it upstream")
    names = set(frame.geom_type.tolist())
    if names <= _POINTS:
        return "points", names
    if names <= _POLYGONS:
        return "polygons", names
    raise _refusal(f"a display copy draws points or polygons, one kind; this holds "
                   f"{', '.join(sorted(names))}", "split it upstream")


def _on(line_coords, point, tol: float = 1e-6) -> bool:
    import shapely
    return shapely.LineString(line_coords).distance(shapely.Point(point)) < tol


def _nudged(ring_coords: list, k: int, distance: float) -> tuple | None:
    """vertex k of a closed ring moved `distance` along the bisector of its two
    neighbours, which for a hole's pinch points into the hole. None when the
    neighbours give no direction."""
    import math
    n = len(ring_coords) - 1                       # the last vertex repeats the first
    p = ring_coords[k % n]
    a, b = ring_coords[(k - 1) % n], ring_coords[(k + 1) % n]
    ux, uy = a[0] - p[0], a[1] - p[1]
    vx, vy = b[0] - p[0], b[1] - p[1]
    la, lb = math.hypot(ux, uy), math.hypot(vx, vy)
    if la == 0 or lb == 0:
        return None
    dx, dy = ux / la + vx / lb, uy / la + vy / lb
    norm = math.hypot(dx, dy)
    if norm == 0:
        return None
    return (p[0] + distance * dx / norm, p[1] + distance * dy / norm)


def _open_pinches(coverage, distance: float):
    """(coverage, record) with every pinch opened (COVER-1), or (coverage, None)
    when its invalid edges are not pinches. a pinch is a point two places' bad
    edges share, lying on each one's shell and on one of its holes. only hole
    vertices move; every shell, and so every shared border, is kept."""
    import numpy
    import shapely
    bad = shapely.coverage_invalid_edges(coverage)
    flagged = [i for i in range(len(coverage)) if not bool(shapely.is_empty(bad[i]))]
    owners: dict = {}
    for i in flagged:
        for c in shapely.get_coordinates(bad[i]):
            owners.setdefault((float(c[0]), float(c[1])), set()).add(i)
    kisses = {pt for pt, who in owners.items() if len(who) > 1}
    if not kisses:
        return coverage, None
    out, moved, places = list(coverage), 0, 0
    for i in flagged:
        parts, changed = [], False
        for part in shapely.get_parts(coverage[i]):
            shell = list(part.exterior.coords)
            holes = []
            for ring in part.interiors:
                coords = [tuple(c) for c in ring.coords]
                for k in range(len(coords) - 1):
                    pt = (float(coords[k][0]), float(coords[k][1]))
                    if pt in kisses and _on(shell, pt):
                        to = _nudged(coords, k, distance)
                        if to is None:
                            return coverage, None
                        coords[k] = to
                        if k == 0:
                            coords[-1] = to
                        moved, changed = moved + 1, True
                holes.append(coords)
            parts.append(shapely.Polygon(shell, holes))
        if changed:
            places += 1
            out[i] = parts[0] if len(parts) == 1 else shapely.MultiPolygon(parts)
    if not moved:
        return coverage, None
    out = numpy.asarray(out, dtype=object)
    if not bool(numpy.all(shapely.is_valid(out))) or not bool(shapely.coverage_is_valid(out)):
        return coverage, None
    return out, {"step": "opened", "count": places, "detail": (
        f"{moved} pinched hole vertices in {places} places moved {OPEN_PINCH_M} m into their "
        f"own holes (COVER-1): at each, two places' holes (removed water) touched one shared "
        f"point of their border, which GEOS's coverage check refuses though every border "
        f"matches; no border moved, and the canonical outline keeps the pinch")}


def _simplify_coverage(frame, tolerance_m: int, id_field: str | None, vertices_before: int):
    """polygons simplified as one coverage in PROJECTED, back in WEB, and the
    publication records that say so: `opened` first when a pinch had to be
    opened, then `simplified`."""
    import geopandas
    import numpy
    import shapely
    projected = frame.to_crs(PROJECTED)
    coverage = numpy.asarray(projected.geometry)
    steps: list[dict] = []
    if not bool(shapely.coverage_is_valid(coverage)):
        opened, record = _open_pinches(coverage, OPEN_PINCH_M)
        if record is None:
            bad = shapely.coverage_invalid_edges(coverage)
            n_bad = int((~shapely.is_empty(bad)).sum())
            raise _refusal(
                f"the polygons are not a valid coverage: {n_bad} of them overlap a "
                f"neighbour or leave a gap, so simplifying them as one would draw cracks",
                "repair the coverage upstream, then write a new version")
        coverage = opened
        steps.append(record)
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
    return frame, steps


def _markers(frame, id_field: str | None):
    """each polygon as one point on its own surface, found in PROJECTED, so a
    marker always stands inside its place. nothing is simplified."""
    import geopandas
    import numpy
    import shapely
    projected = frame.to_crs(PROJECTED)
    points = shapely.point_on_surface(numpy.asarray(projected.geometry))
    gone = shapely.is_empty(points)
    if bool(numpy.any(gone)):
        ids = (frame[id_field].astype(str)[gone].tolist() if id_field in frame.columns
               else [str(i) for i in frame.index[gone]])
        raise _refusal(f"{len(ids)} place(s) have no point on their surface "
                       f"({', '.join(ids[:5])})", "repair the outline upstream")
    projected = projected.set_geometry(
        geopandas.GeoSeries(points, index=projected.index, crs=PROJECTED))
    step = {"step": "marked", "count": int(len(frame)), "detail": (
        f"each place drawn as one marker, a point on its own surface (shapely "
        f"{shapely.__version__} point_on_surface in {PROJECTED}), so it stands inside its "
        f"place; its outline is not drawn and nothing is simplified")}
    return projected.to_crs(WEB), step


def _round(frame, id_field: str | None = None) -> tuple:
    """coordinates rounded to DECIMALS places of a degree. a polygon the
    rounding leaves invalid is named in the record, never refused here
    (ROUND-2, D-379): the door refuses to send one (D-368), and a dry run of
    the copy is where it is first seen."""
    import geopandas
    import numpy
    import shapely
    rounded = shapely.transform(numpy.asarray(frame.geometry),
                                lambda c: numpy.round(c, DECIMALS))
    frame = frame.set_geometry(geopandas.GeoSeries(rounded, index=frame.index, crs=WEB))
    detail = f"coordinates rounded to {DECIMALS} decimal places of a degree, about 10 cm"
    polygons = numpy.isin(shapely.get_type_id(rounded), (3, 6))
    if bool(numpy.any(polygons)):
        bad = polygons & ~shapely.is_valid(rounded)
        if bool(numpy.any(bad)):
            ids = (frame[id_field].astype(str)[bad].tolist() if id_field in frame.columns
                   else [str(i) for i in frame.index[bad]])
            detail += (f"; {len(ids)} shape(s) invalid after rounding "
                       f"({', '.join(ids[:10])}{' and more' if len(ids) > 10 else ''})")
        else:
            detail += "; every shape valid after rounding"
    return frame, {"step": "rounded", "count": int(len(frame)), "detail": detail}


def _dates_as_text(frame) -> list[str]:
    as_text = []
    for col in [c for c in frame.columns if c != frame.geometry.name]:
        if str(frame[col].dtype).startswith("datetime64"):
            frame[col] = [None if v is None or v != v else v.isoformat() for v in frame[col]]
            as_text.append(col)
        elif frame[col].dtype == object and any(hasattr(v, "isoformat") for v in frame[col]):
            frame[col] = [v.isoformat() if hasattr(v, "isoformat") else v for v in frame[col]]
            as_text.append(col)
    return as_text


def _format_step(frame, source_crs: str, as_text: list[str]) -> dict:
    import pyproj
    operation = ("no reprojection" if source_crs == WEB else
                 pyproj.Transformer.from_crs(source_crs, WEB, always_xy=True).description)
    if "unavailable" in operation:
        operation = (f"the operation pyproj {pyproj.__version__} chooses when it runs, "
                     f"which it does not name beforehand")
    dates = (f"; dates and times written as ISO 8601 text, a missing one as null "
             f"({', '.join(as_text)})" if as_text else "")
    return {"step": "format_changed", "count": int(len(frame)), "detail": (
        f"GeoParquet to GeoJSON (RFC 7946) in {WEB}, from {source_crs} by {operation}; "
        f"every property kept{dates}")}


def _stats(frame, kind: str, names: set, vertices_before: int, body: bytes,
           source_crs: str) -> dict:
    import numpy
    import shapely
    final = numpy.asarray(frame.geometry)
    return {
        "feature_count": int(len(frame)),
        "geometry_type": "Point" if kind in ("points", "markers") else "MultiPolygon"
        if "MultiPolygon" in names else "Polygon",
        "bbox": [round(float(v), DECIMALS) for v in frame.total_bounds],
        "vertex_count": int(shapely.get_num_coordinates(final).sum()),
        "vertices_before": vertices_before,
        "size_bytes": len(body),
        "attribute_fields": [c for c in frame.columns if c != frame.geometry.name],
        "source_crs": source_crs,
    }


def draw(parquet_bytes: bytes, *, tolerance_m: int = DEFAULT_TOLERANCE_M,
         id_field: str | None = None, markers: bool = False) -> dict:
    """a GeoParquet version drawn as a web GeoJSON. returns the bytes, the
    publication records (step, detail, count), the copy's kind and what its
    metadata should say. with markers, an outline is drawn as one point on
    each place's own surface (D-377), simplifying nothing."""
    import numpy
    import shapely

    frame = _read_frame(parquet_bytes)
    if frame.crs is None:
        raise _refusal("the version's GeoParquet declares no crs", "rewrite it with its crs")
    source_crs = frame.crs.to_string()
    kind, names = _kind_of(frame)
    if markers and kind != "polygons":
        raise _refusal(f"markers are drawn from an outline of polygons; this version holds "
                       f"{', '.join(sorted(names))}", "draw it without --markers")
    vertices_before = int(shapely.get_num_coordinates(numpy.asarray(frame.geometry)).sum())
    steps: list[dict] = []

    if markers:
        frame, step = _markers(frame, id_field)
        kind = "markers"
        steps.append(step)
    elif kind == "polygons":
        frame, drawn_steps = _simplify_coverage(frame, tolerance_m, id_field, vertices_before)
        steps.extend(drawn_steps)
    else:
        frame = frame.to_crs(WEB) if source_crs != WEB else frame
        steps.append({"step": "simplified", "count": 0,
                      "detail": "points: nothing to simplify"})

    frame, step = _round(frame, id_field)
    steps.append(step)
    as_text = _dates_as_text(frame)
    steps.append(_format_step(frame, source_crs, as_text))

    body = frame.to_json(drop_id=True).encode("utf-8")
    stats = _stats(frame, kind, names, vertices_before, body, source_crs)
    name = display_name(kind, tolerance_m)
    return {"bytes": body, "steps": steps, "kind": kind, "name": name, "stats": stats}


# -- joined copies (D-331) ----------------------------------------------------

def joined_name(outline_harvest: str, outline_sha256: str, *, markers: bool = False,
                tolerance_m: int = DEFAULT_TOLERANCE_M, only=None) -> str:
    """a joined copy is named for the outline version it is drawn on, so a new
    outline version is a new copy and never new bytes under one name (D-322).
    a copy holding only some indicators (only, D-396) says which by only_key."""
    stem = f"{outline_harvest}_{outline_sha256[:12]}"
    name = f"{stem}_markers" if markers else f"{stem}_{display_name('polygons', tolerance_m)}"
    return f"{name}_only_{only_key(only)}" if only else name


def draw_joined(table_bytes: bytes, outline_bytes: bytes, *, outline_harvest: str,
                outline_sha256: str, level: str, widths: dict, markers: bool = False,
                tolerance_m: int = DEFAULT_TOLERANCE_M, id_field: str | None = None,
                only=None) -> dict:
    """a long-form table joined onto an outline version and drawn as one wide
    web GeoJSON: every place of the outline, every indicator's columns beside
    it, keyed by (authority, code). polygons are simplified as one coverage,
    as any polygon copy is; markers are one point on each place's surface.
    with only, the copy keeps the columns of those indicators alone, every
    place's own fields with them, and says in its joined step which it left
    out (D-396): a lens draws one or two measures of a table that holds 26."""
    import io

    import geopandas
    import numpy
    import pandas
    import shapely

    from canopy import choropleth

    table = pandas.read_parquet(io.BytesIO(table_bytes))
    table_dates = [c for c in table.columns if str(table[c].dtype).startswith("datetime64")]
    frame = _read_frame(outline_bytes)
    if frame.crs is None:
        raise _refusal("the outline's GeoParquet declares no crs", "rewrite it with its crs")
    source_crs = frame.crs.to_string()
    kind, names = _kind_of(frame)
    if kind != "polygons":
        raise _refusal(f"a table is joined onto an outline of polygons; this one holds "
                       f"{', '.join(sorted(names))}", "join onto a place outline")
    vertices_before = int(shapely.get_num_coordinates(numpy.asarray(frame.geometry)).sum())
    steps: list[dict] = []
    if markers:
        frame, step = _markers(frame, id_field)
        kind = "markers"
        steps.append(step)
    else:
        frame, drawn_steps = _simplify_coverage(frame, tolerance_m, id_field, vertices_before)
        steps.extend(drawn_steps)
    frame, step = _round(frame, id_field)
    steps.append(step)
    as_text = _dates_as_text(frame)

    places = [{k: choropleth.plain(v) for k, v in row.items()}
              for row in frame.drop(columns=[frame.geometry.name]).to_dict(orient="records")]
    try:
        joined = choropleth.join(table, places, level=level, widths=widths)
    except choropleth.ChoroplethRefusal as e:
        raise _refusal(e.reason, e.would_admit) from None
    left_out: list = []
    if only:
        only = sorted(set(only))
        unheld = [i for i in only if i not in joined["indicators"]]
        if unheld:
            raise _refusal(f"the table holds no {', '.join(unheld)}",
                           f"name only indicators it holds: {', '.join(joined['indicators'])}")
        left_out = [i for i in joined["indicators"] if i not in only]
        gone = {c for i in left_out for c in joined["columns"].get(i) or []}
        joined["properties"] = [{k: v for k, v in row.items() if k not in gone}
                                for row in joined["properties"]]
        joined["indicators"] = [i for i in joined["indicators"] if i in only]
        joined["columns"] = {i: joined["columns"][i] for i in joined["indicators"]}
    props = pandas.DataFrame(joined["properties"])
    out = geopandas.GeoDataFrame(props, geometry=numpy.asarray(frame.geometry), crs=WEB)
    c = joined["counts"]
    steps.append({"step": "joined", "count": c["places"], "detail": (
        f"the table joined onto {outline_harvest} version {outline_sha256[:12]} on "
        f"(unit_authority, unit_code) to (authority, code), {joined['authority']} at level "
        f"{level}: {c['places'] - c['places_without_row']} of {c['places']} places with a row, "
        f"{c['places_without_row']} kept with empty columns; of the table's rows, "
        f"{c['rows_outside_outline']} belong to places outside this outline, "
        f"{c['rows_other_level']} to another level and {c['rows_other_authority']} to "
        f"another authority; each indicator's columns named <indicator>__<column>"
        + ((f"; only {', '.join(joined['indicators'])} kept, the columns of "
            f"{len(left_out)} other indicator(s) left out ({', '.join(left_out)}), for a "
            f"lens (D-396)" if left_out else
            f"; {', '.join(joined['indicators'])} is every indicator the table holds, so "
            f"nothing is left out (D-396)") if only else ""))})
    as_text += [choropleth.column_name(ind, col) for ind in joined["indicators"]
                for col in table_dates]
    steps.append(_format_step(out, source_crs, as_text))

    body = out.to_json(drop_id=True).encode("utf-8")
    stats = _stats(out, kind, names, vertices_before, body, source_crs)
    name = joined_name(outline_harvest, outline_sha256, markers=markers, tolerance_m=tolerance_m,
                       only=only)
    join_said = {"counts": c, "indicators": joined["indicators"],
                 "columns": joined["columns"], "authority": joined["authority"],
                 "level": level, "row_notes": choropleth.row_notes(joined["properties"])}
    if only:
        join_said.update(only=only, left_out=left_out)
    return {"bytes": body, "steps": steps, "kind": kind, "name": name, "stats": stats,
            "join": join_said}


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


def _branch(entries, name: str) -> list[dict]:
    out = []
    for entry in entries or []:
        e = dict(entry)
        if e.get("lineage_branch") is None:
            e["lineage_branch"] = name
        out.append(e)
    return out


# a table's own description of its rows, which a drawn copy of places no longer is
_TABULAR_META = ("row_count", "column_count", "variables", "id_fields", "data_quality",
                 "row_context_notes", "context_notes")


def joined_envelope(table_receipt: dict, outline_receipt: dict, *, display_key: str,
                    table_url: str, outline_url: str, table_sha256: str, table_allow: str,
                    outline_harvest: str, outline_sha256: str, outline_allow: str,
                    harvest: str, drawn: dict, params: dict, duration_seconds: float,
                    now: datetime | None = None) -> dict:
    """a joined copy's envelope: the table's metadata and lineage, the outline
    named whole in joined_to (its version, allow record and lineage, which the
    gate reads for rule 10), both provenance chains under the branches
    `table` and `outline`, and this drawing's entry. its rows are places, so
    row_context_notes are the notes the drawn features carry (D-156)."""
    at = (now or datetime.now(timezone.utc)).isoformat()
    tmeta = table_receipt.get("metadata") or {}
    ometa = outline_receipt.get("metadata") or {}
    meta = {k: v for k, v in tmeta.items() if k not in _STALE_META + _TABULAR_META}
    stats, join = drawn["stats"], drawn["join"]
    carried = sorted(set(join["row_notes"]) |
                     {n for n in (tmeta.get("context_notes") or []) if isinstance(n, str)})
    meta.update({
        "data_category": "vector", "crs": WEB,
        "feature_count": stats["feature_count"], "geometry_type": stats["geometry_type"],
        "bbox": stats["bbox"], "vertex_count": stats["vertex_count"],
        "size_bytes": stats["size_bytes"], "attribute_fields": stats["attribute_fields"],
        "id_field": ometa.get("id_field") or "code",
        "spatial_unit": ometa.get("spatial_unit") or join["level"],
        "derived_from": table_sha256, "allow": table_allow, "display_of": harvest,
        "display_name": drawn["name"], "display_kind": drawn["kind"],
        "joined_to": {"harvest": outline_harvest, "sha256": outline_sha256,
                      "allow": outline_allow, "semantic_type": ometa.get("semantic_type"),
                      "authority": join["authority"], "level": join["level"],
                      "lineage": ometa.get("lineage")},
        "join": {"counts": join["counts"], "indicators": join["indicators"],
                 "columns": join["columns"], "directions": dict(join.get("directions") or {}),
                 **({"only": join["only"], "left_out": join.get("left_out") or []}
                    if join.get("only") else {})},
        "row_context_notes": list(join["row_notes"]),
        "context_notes": carried,
    })
    own = {
        "primitive": PRIMITIVE, "version": VERSION, "timestamp": at, "params": params,
        "inputs": [
            {"name": "table", "semantic_type": tmeta.get("semantic_type"), "path": table_url,
             "hash": {"value": table_sha256, "method": "full_file", "algorithm": "sha256"}},
            {"name": "outline", "semantic_type": ometa.get("semantic_type"), "path": outline_url,
             "hash": {"value": outline_sha256, "method": "full_file", "algorithm": "sha256"}}],
        "duration_seconds": round(float(duration_seconds), 3), "lineage_branch": None,
        "publication": [dict(s, by=PRIMITIVE, at=at) for s in drawn["steps"]],
    }
    provenance = (_branch(table_receipt.get("provenance"), "table")
                  + _branch(outline_receipt.get("provenance"), "outline") + [own])
    return {"data": {"path": display_key, "format": "geojson", "secondary": {}},
            "metadata": meta, "provenance": provenance,
            "warnings": list(table_receipt.get("warnings") or [])
            + list(outline_receipt.get("warnings") or [])}


def timed(fn, *args, **kwargs):
    started = time.monotonic()
    result = fn(*args, **kwargs)
    return result, time.monotonic() - started


def envelope_bytes(envelope: dict) -> bytes:
    return (json.dumps(envelope, indent=2, allow_nan=False) + "\n").encode("utf-8")
