"""
tests/test_graph_keys.py  |  rewildingCities, Sprint 05 change 5 (KEYS-1)

The three graph tables say in their receipts what one row is and the key that
names it, so loam, and later the grove, join on a declared key rather than a
guess: places by (authority, code), edges by their two ends, seats by
(legislature, chamber, seat_kind, seat_ref). An edge key used twice is
refused, since a declared key must name one row.
"""

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


places_mod = load("build_places", "soil/transform/build_places.py")
edges_mod = load("build_place_edges", "soil/transform/build_place_edges.py")
seats_mod = load("build_seats", "soil/transform/build_seats.py")
places_tests = load("places_tests", "tests/test_places.py")
seats_tests = load("seats_tests", "tests/test_seats.py")


def test_places_declare_their_key_and_keep_their_notes():
    frame = places_tests.build()
    meta = places_mod.output_metadata(frame)
    assert meta["id_fields"] == ["authority", "code"]
    assert meta["spatial_unit"] == "place"
    assert meta["row_count"] == len(frame)
    assert meta["context_notes"] == places_mod.context_metadata(frame)["context_notes"]


def test_edges_declare_their_two_ends_as_their_key():
    meta = edges_mod.output_metadata(pd.DataFrame(columns=edges_mod.COLUMNS))
    assert meta["id_fields"] == ["from_authority", "from_code", "to_authority", "to_code"]
    assert meta["spatial_unit"] == "edge"


def test_an_edge_key_used_twice_is_refused():
    row = {"from_authority": "us_census_geoid", "from_code": "2300560825",
           "to_authority": "us_census_sldl", "to_code": "23042", "kind": "overlaps",
           "weight_population": 0.5, "weight_households": 0.5, "weight_reason": None,
           "source": "test", "vintage": "2024"}
    edges_mod.check_key(pd.DataFrame([row]))
    with pytest.raises(SystemExit):
        edges_mod.check_key(pd.DataFrame([row, dict(row, weight_population=0.4)]))


def test_seats_declare_their_key():
    meta = seats_mod.output_metadata(seats_tests.build())
    assert meta["id_fields"] == ["legislature", "chamber", "seat_kind", "seat_ref"]
    assert meta["spatial_unit"] == "seat"


def test_loam_projects_the_declared_key(tmp_path):
    from canopy.loam.envelope_reader import read_envelope
    from canopy.loam.loam import Loam
    from canopy.vocabulary import Vocabulary

    receipt = tmp_path / "graph_places_places.envelope.json"
    receipt.write_text(json.dumps({
        "data": {"path": str(tmp_path / "places.parquet"), "format": "parquet"},
        "metadata": {"semantic_type": "places",
                     **places_mod.output_metadata(places_tests.build())},
        "provenance": [], "warnings": []}))
    vocab = Vocabulary.load(ROOT / "seeds" / "schemas")
    fields = read_envelope(str(receipt), vocab, "demo")
    assert fields["id_fields"] == ["authority", "code"]
    assert fields["unit_key"] == "place"

    fields.pop("tier")
    row, _ = Loam(vocab, str(tmp_path / "loam.duckdb")).till(**fields)
    assert row.id_fields == "authority|code"
