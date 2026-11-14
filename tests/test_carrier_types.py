"""
tests/test_carrier_types.py

CMAP-1. Each carrier kind is its own semantic type, never one type with a
kind field (D-218). institutional_node is retired with no alias, and the
library points are library_outlet (D-219). That every live declaration names
a current type, anywhere, is tests/test_current_type_names.py's to hold.
"""

import pytest
import yaml

from canopy.paths import project_root
from canopy.vocabulary import Vocabulary

ROOT = project_root()


def _registry(layer: str) -> dict:
    doc = yaml.safe_load((ROOT / layer / "_registry.yml").read_text()) or {}
    return doc.get("primitives") or {}


@pytest.fixture(scope="module")
def vocab() -> Vocabulary:
    return Vocabulary.load(ROOT / "seeds" / "schemas")


# ── D-218, D-219: the library points and the retired name ───────────────────

def test_library_outlet_is_its_own_vector_type(vocab):
    t = vocab.get("library_outlet", follow_history=False)
    assert t.category == "vector"
    assert t.format == "geojson"
    assert t.domain == "information"
    assert t.extra.get("resolution_tier") == "public"
    assert t.aliases == ()


def test_institutional_node_is_retired_with_no_alias(vocab):
    assert not vocab.is_valid("institutional_node")
    assert "institutional_node" not in vocab.alias_map
    assert vocab.resolve("institutional_node").how == "unresolved"
    assert not vocab.knows_name("institutional_node")


def test_the_library_points_are_library_outlets():
    spec = _registry("soil")["prepare_library_points"]
    assert spec["outputs"]["semantic_type"] == "library_outlet"


def test_located_in_places_library_and_news_outlets_by_name():
    spec = _registry("soil")["build_located_in"]
    points = next(i for i in spec["inputs"] if i["name"] == "points")
    accepted = set(points["semantic_types"])
    assert {"library_outlet", "formal_outlet"} <= accepted
    assert "institutional_node" not in accepted


def test_maine_libraries_makes_library_outlets():
    doc = yaml.safe_load((ROOT / "plots" / "maine" / "preparations"
                          / "maine_libraries.yml").read_text())
    step = next(s for s in doc["steps"] if s["id"] == "libraries_points")
    assert step["primitive"] == "soil/prepare_library_points"
    assert step["outputs"] == {"points": "library_outlet"}
