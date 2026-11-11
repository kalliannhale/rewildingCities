"""build_located_in is registered, and its output type is declared and is
not place_edges (D-207)."""

from pathlib import Path

import yaml

from canopy.vocabulary import Vocabulary

ROOT = Path(__file__).resolve().parents[1]


def test_the_primitive_is_registered_with_its_inputs():
    reg = yaml.safe_load((ROOT / "soil" / "_registry.yml").read_text())["primitives"]
    entry = reg["build_located_in"]
    assert entry["path"] == "transform/build_located_in.py"
    names = {i["name"] for i in entry["inputs"]}
    assert names == {"points", "faces", "spine", "places", "divisions"}
    assert entry["outputs"]["semantic_type"] == "located_in_edges"


def test_located_in_edges_is_a_type_of_its_own():
    vocab = Vocabulary.load(ROOT / "seeds" / "schemas")
    assert vocab.resolve("located_in_edges").canonical == "located_in_edges"
    assert vocab.resolve("located_in_edges").canonical != vocab.resolve("place_edges").canonical
