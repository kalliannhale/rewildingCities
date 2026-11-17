"""
tests/test_webmap_json.py ~ what the arcgis_webmap kind writes (D-333)

the web map follows Esri's web map specification 2.38: a GeoJSON layer that
keeps a reference to a public file. field types come from the values the
layer reads, never guessed; the description comes from the bucket's records
alone, so the same records always write the same words. ~
"""

from __future__ import annotations

import math

from canopy.expose.targets.arcgis_webmap import (
    ArcGISWebMap, OBJECTID, description_of, extent_of, fields_of, webmap_of)
from canopy.expose.targets.base import Target


def copy(**over):
    c = {
        "plot": "maine", "artifact": "clerks_points", "title": "clerks_points (maine)",
        "sha256": "a" * 64, "allow": "1" * 64,
        "url": "https://cdn.invalid/harvests/maine/clerks_points/versions/" + "a" * 64
               + "/display/web.geojson",
        "version_url": "https://cdn.invalid/harvests/maine/clerks_points/versions/" + "a" * 64,
        "geojson": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": None,
             "properties": {"name": "Gray", "rows_served": 3, "tie_spread_m": 12.5,
                            "review_read_on": "2026-11-01", "flags": None}},
            {"type": "Feature", "geometry": None,
             "properties": {"name": "Windham", "rows_served": 1, "tie_spread_m": 0,
                            "review_read_on": None, "flags": None}}]},
        "display_env": {"metadata": {"semantic_type": "clerk_office_points", "feature_count": 2,
                                     "bbox": [-71.0, 43.0, -67.0, 47.5],
                                     "lineage": {"kind": "preparation", "run": "clerks"}},
                        "provenance": [{"publication": [{"step": "rounded",
                                                         "detail": "6 decimal places"}]}],
                        "warnings": []},
        "allow_doc": {"gate": {"context_text": {"census_tribal_area": "the Census's boundary"},
                               "caveats": [],
                               "license": [{"dataset": "towns", "term": "geo"}],
                               "publication_steps": []}},
        "licenses": {"geo": {"name": "Maine GeoLibrary data", "attribution": "required"}},
    }
    c.update(over)
    return c


def test_fields_are_typed_from_the_values_the_layer_reads():
    types = {f["name"]: f["type"] for f in fields_of(copy()["geojson"])}
    assert types[OBJECTID] == "esriFieldTypeOID"
    assert types["rows_served"] == "esriFieldTypeInteger"
    assert types["tie_spread_m"] == "esriFieldTypeDouble"
    assert types["review_read_on"] == "esriFieldTypeString"     # text, as D-324 wrote it
    assert types["name"] == "esriFieldTypeString"
    assert types["flags"] == "esriFieldTypeString"              # always empty: text, said so


def test_a_text_field_is_never_shorter_than_its_longest_value():
    gj = {"features": [{"properties": {"note": "x" * 900}}]}
    [_, note] = fields_of(gj)
    assert note["length"] >= 900


def test_the_layer_is_the_specifications_geojson_layer():
    doc = webmap_of(copy(), "rewilding-clerks_points", "1.0.0")
    [layer] = doc["operationalLayers"]
    assert layer["layerType"] == "GeoJSON" and layer["url"] == copy()["url"]
    assert layer["layerDefinition"]["objectIdField"] == OBJECTID
    assert layer["popupInfo"]["title"] == "{name}"
    assert layer["popupInfo"]["showAttachments"] is False
    assert doc["version"] == "2.38" and doc["authoringApp"] == "rewildingCities"
    assert doc["spatialReference"]["wkid"] == 102100


def test_the_extent_comes_from_the_copys_own_bbox():
    e = extent_of([-71.0, 43.0, -67.0, 47.5])
    x = 6378137.0 * math.radians(-71.0)
    assert e["xmin"] < x < e["xmax"] and e["spatialReference"]["latestWkid"] == 3857
    assert extent_of(None) is None


def test_the_description_carries_the_notes_the_sharing_line_and_the_hashes():
    d, license_info, access = description_of(copy(), "1.0.0")
    assert "the Census&#x27;s boundary" in d                # escaped, as HTML
    assert "This layer reads a public URL" in d
    assert "a" * 64 in d and "1" * 64 in d
    assert "Maine GeoLibrary data" in license_info
    assert access.startswith("Maine GeoLibrary data")           # attribution: required


def test_the_same_records_write_the_same_words():
    assert description_of(copy(), "1.0.0") == description_of(copy(), "1.0.0")


def test_build_names_the_layer_by_its_harvest():
    t = Target(id="test", kind="arcgis_webmap", portal="https://p.invalid", owner="RDS_NU",
               owner_kind="institutional", folder="f", sharing="private")
    built = ArcGISWebMap().build(t, copy())
    assert built.layer_id == "rewilding-clerks_points"
    assert built.data["operationalLayers"][0]["id"] == built.layer_id
    assert "rewildingCities" in built.tags and len(built.snippet) <= 250
