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
anywhere, offline), and additionally, when introspect says ArcGIS is reachable
(online + credentialed), the same result is published to a hosted layer. never a
locked door, always some way to view your result.

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


def _arcgis_reachable() -> bool:
    """can we reach ArcGIS to publish, here and now? introspect's job. ~"""
    from canopy.introspect import is_online, has_credentials
    return is_online() and has_credentials("arcgis")


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
    read-only provider; uses the arcgis python api. only called when introspect
    says ArcGIS is reachable, and any failure falls back to the geojson already
    written ~ the door stays open. ~"""
    from arcgis.gis import GIS
    gis = GIS("home")  # active profile / stored credentials
    item = gis.content.add(
        {"title": spec.title or metadata.get("semantic_type", "rewilding result"),
         "type": "GeoJson", "tags": "rewildingCities"},
        data=str(geojson_path),
    )
    published = item.publish()
    return published.homepage


def render(envelope: dict, out_dir, *, plot: str | None = None) -> ViewResult:
    """derive the map from the result's metadata, always write map.geojson, and
    additionally publish to ArcGIS when reachable. the view carries its own
    provenance back to the result envelope and its lineage. ~"""
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
    if _arcgis_reachable():
        try:
            arcgis_url = _publish_arcgis(geojson_path, spec, metadata)
        except Exception:
            arcgis_url = None  # fall back to the geojson already written

    return ViewResult(
        mode="arcgis+geojson" if arcgis_url else "geojson",
        geojson_path=str(geojson_path),
        arcgis_url=arcgis_url,
        spec=spec,
        provenance=provenance,
    )
