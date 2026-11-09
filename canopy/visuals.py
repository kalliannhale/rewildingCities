"""
canopy/visuals.py

visuals ~ the last reader of the spine: a map derived from a result's own metadata

a gathered result already carries, in its metadata, everything a map needs ~ where
it sits (bbox, geometry_type), what each row IS and which layer it draws on
(spatial_unit, joins_to, id_field), what to color by (the dependent variable), and
what it MEANS (analysis_type, interpretation_notes). so visuals does not author a
map; it derives one ~ the same rule as loam and wonder: the metadata is the source
of truth.

the door does not lock on seeing. a map.geojson is written every time (openable
anywhere, offline). publishing is a latch, not a default (EXP-1): the same result
goes to a hosted ArcGIS layer only when the caller asks (publish=True), and only
when introspect says ArcGIS is reachable (online + credentialed). a publish that
was asked for and cannot happen says why, out loud; it never falls back in
silence. always some way to view your result, never a publish nobody chose.

a map is a claim, so the view records which result envelope produced it and the
lineage that led there ~ its provenance travels with it. ~
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


# --- what to draw, derived from metadata -------------------------------------

@dataclass
class MapSpec:
    """what a map of this result should show, read from the result's metadata. ~"""
    data_category: str
    layer: str | None        # the vector semantic_type this (tabular) result draws on (joins_to)
    join_on: str | None      # the key linking rows to that layer (id_field)
    color_by: str | None     # the variable to symbolize ~ the dependent variable
    geometry_type: str | list[str] | None   # a mixed layer reports every type it holds
    bbox: list | None
    analysis_type: str | None
    title: str
    caption: str


def derive_map_spec(metadata: dict) -> MapSpec:
    """derive the map from the result's metadata ~ never authored, always read. a
    field the metadata does not carry is left None (honest); the map shows what it
    can and says what it means. ~"""
    # what to color by: the dependent variable, declared in statistical_context or
    # in variable_details[].role == "dependent"
    color_by = (metadata.get("statistical_context") or {}).get("dependent_variable")
    if not color_by:
        for name, det in (metadata.get("variable_details") or {}).items():
            if (det or {}).get("role") == "dependent":
                color_by = name
                break

    caption = " ".join(metadata.get("interpretation_notes") or []).strip()
    st = metadata.get("semantic_type", "result")
    return MapSpec(
        data_category=metadata.get("data_category", "tabular"),
        layer=metadata.get("joins_to"),
        join_on=metadata.get("id_field"),
        color_by=color_by,
        geometry_type=metadata.get("geometry_type"),
        bbox=metadata.get("bbox"),
        analysis_type=metadata.get("analysis_type"),
        title=st + (f" by {color_by}" if color_by else ""),
        caption=caption,
    )


# --- viewing: always a geojson, plus ArcGIS when reachable -------------------

@dataclass
class ViewResult:
    mode: str                # "arcgis+geojson" | "geojson"
    geojson_path: str
    arcgis_url: str | None
    spec: MapSpec
    provenance: dict


class PublishError(Exception):
    """a publish was asked for and did not happen, with the reason. the local
    map.geojson is already written when this is raised; geojson_path names it. ~"""

    def __init__(self, message: str, geojson_path: str | None = None):
        super().__init__(message)
        self.geojson_path = geojson_path


def _arcgis_unreachable() -> str | None:
    """why ArcGIS cannot be reached here and now, or None when it can.
    introspect's job; the reason is named so a refused publish can say it. ~"""
    from canopy.introspect import is_online, has_credentials
    if not is_online():
        return "this machine is offline"
    if not has_credentials("arcgis"):
        return "no ArcGIS credentials were found (ARCGIS_API_KEY or ARCGIS_USERNAME)"
    return None


def _read_features(envelope: dict) -> list:
    """the result's own geometry, if it carries any inline geojson we can read
    without a heavy dependency. a tabular result carries none ~ it draws on the
    layer named in joins_to, a join ArcGIS performs on publish and a person can
    perform locally from the spec. ~"""
    data = envelope.get("data") or {}
    if data.get("format") != "geojson":
        return []
    path = data.get("path")
    if not path or not Path(path).exists():
        return []
    try:
        doc = json.loads(Path(path).read_text())
    except Exception:
        return []
    if isinstance(doc, dict) and doc.get("type") == "FeatureCollection":
        return doc.get("features") or []
    return []


def _write_map_geojson(spec: MapSpec, provenance: dict, out_dir,
                       features: list) -> Path:
    """write a self-describing map.geojson ~ valid GeoJSON any viewer opens, with
    the derived spec and the view's provenance carried as foreign members. ~"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fc: dict = {
        "type": "FeatureCollection",
        "features": features,
        "rewilding:map": asdict(spec),
        "rewilding:provenance": provenance,
    }
    if spec.bbox:
        fc["bbox"] = spec.bbox
    path = out_dir / "map.geojson"
    path.write_text(json.dumps(fc, indent=2))
    return path


def _publish_arcgis(geojson_path: Path, spec: MapSpec, metadata: dict) -> str:
    """publish the map.geojson as a hosted feature layer. new code beside the
    read-only provider; uses the arcgis python api. only called when the caller
    asked to publish and introspect says ArcGIS is reachable. every failure is
    raised as a PublishError naming what happened, including an upload that went
    up but did not publish, which would otherwise sit on ArcGIS unseen. ~"""
    try:
        from arcgis.gis import GIS
    except ImportError as e:
        raise PublishError(
            "the arcgis package is not installed, so nothing was published") from e

    try:
        gis = GIS("home")  # active profile / stored credentials
        item = gis.content.add(
            {"title": spec.title or metadata.get("semantic_type", "rewilding result"),
             "type": "GeoJson", "tags": "rewildingCities"},
            data=str(geojson_path),
        )
    except Exception as e:
        raise PublishError(f"could not upload to ArcGIS: {e}") from e

    try:
        published = item.publish()
    except Exception as e:
        raise PublishError(
            f"uploaded item {getattr(item, 'id', '(unknown id)')} to ArcGIS, but "
            f"publishing it failed: {e}. the uploaded item is still on ArcGIS; "
            f"delete it there if it should not stay") from e
    return published.homepage


def render(envelope: dict, out_dir, *, plot: str | None = None,
           publish: bool = False) -> ViewResult:
    """derive the map from the result's metadata and always write map.geojson.
    publish to ArcGIS only when publish=True; if it was asked for and cannot
    happen, raise PublishError after the geojson is written. the view carries
    its own provenance back to the result envelope and its lineage. ~"""
    metadata = envelope.get("metadata") or {}
    spec = derive_map_spec(metadata)
    provenance = {
        "result_semantic_type": metadata.get("semantic_type"),
        "data_path": (envelope.get("data") or {}).get("path"),
        "lineage": metadata.get("lineage"),   # curiosity / method / data_resolution
        "plot": plot,
    }

    features = _read_features(envelope)
    geojson_path = _write_map_geojson(spec, provenance, out_dir, features)

    arcgis_url = None
    if publish:
        reason = _arcgis_unreachable()
        if reason:
            raise PublishError(f"publish was asked for, but {reason}",
                               str(geojson_path))
        try:
            arcgis_url = _publish_arcgis(geojson_path, spec, metadata)
        except PublishError as e:
            e.geojson_path = str(geojson_path)
            raise

    return ViewResult(
        mode="arcgis+geojson" if arcgis_url else "geojson",
        geojson_path=str(geojson_path),
        arcgis_url=arcgis_url,
        spec=spec,
        provenance=provenance,
    )
