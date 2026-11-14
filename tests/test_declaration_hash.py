"""
tests/test_declaration_hash.py

an indicator's declaration_sha256 is taken over its own mapping, canonical,
without its rationale (D-227). a receipt hashes what its run read, so:

  ~ unchanged   a comment, a sibling's edit, a key order, a rationale edit
  ~ changed     anything that says what the numbers mean: a source, a
                weight, a derivation's scale

the hash belongs to the indicator, not its file, and every declaration has
one, a registry built in memory included.
"""

import copy
from pathlib import Path

import pytest
import yaml

from canopy.indicators import IndicatorRegistry

SEEDS = Path(__file__).resolve().parents[1] / "seeds" / "indicators"

A = {
    "name": "a", "defined_by": "test", "measures": "thing", "unit": "percent",
    "derivation": {"kind": "ratio", "numerator": ["A_001E"],
                   "denominator": "A_002E", "scale": 100},
    "direction": "higher_is_better", "aggregation": "population_weighted_mean",
    "weight_by": "A_002E", "uncertainty": "acs_moe",
    "source": {"provider": "census_acs", "dataset": "acs/acs5"},
    "role": "barrier",
    "rests_on": {"add": ["A_002E"], "counts": "households"},
    "rationale": "why a is read this way",
}
B = {**A, "name": "b", "measures": "other thing"}
BASE = {"a": A, "b": B}


def _hash(tmp_path, entries, tail="", name="t.yml"):
    for old in tmp_path.glob("*.yml"):
        old.unlink()
    text = yaml.safe_dump({"indicators": entries}, sort_keys=False) + tail
    (tmp_path / name).write_text(text)
    return IndicatorRegistry.load(tmp_path).declaration("a")["declaration_sha256"]


def _edited(change):
    entries = copy.deepcopy(BASE)
    tail = change(entries) or ""
    return entries, tail


def _comment(e):
    return "\n# an edit\n"


def _sibling(e):
    e["b"]["unit"] = "count"


def _rationale(e):
    e["a"]["rationale"] = "said another way"


def _key_order(e):
    e["a"] = dict(reversed(list(e["a"].items())))


def _source(e):
    e["a"]["source"]["dataset"] = "acs/acs1"


def _weight(e):
    e["a"]["weight_by"] = "A_003E"


def _scale(e):
    e["a"]["derivation"]["scale"] = 1


@pytest.mark.parametrize("change", [_comment, _sibling, _rationale, _key_order],
                         ids=["comment", "sibling", "rationale", "key_order"])
def test_what_says_nothing_about_the_numbers_leaves_the_hash_alone(tmp_path, change):
    before = _hash(tmp_path, BASE)
    entries, tail = _edited(change)
    assert _hash(tmp_path, entries, tail) == before


@pytest.mark.parametrize("change", [_source, _weight, _scale],
                         ids=["source", "weight_by", "scale"])
def test_what_says_what_the_numbers_mean_moves_the_hash(tmp_path, change):
    before = _hash(tmp_path, BASE)
    entries, tail = _edited(change)
    assert _hash(tmp_path, entries, tail) != before


def test_the_hash_is_the_indicators_not_its_files(tmp_path):
    here = _hash(tmp_path, BASE, name="x.yml")
    there = _hash(tmp_path, BASE, name="y.yml")
    assert here == there


def test_a_registry_built_in_memory_still_hashes(tmp_path):
    loaded = IndicatorRegistry.load(_write(tmp_path))
    in_memory = IndicatorRegistry({"a": loaded.get("a")})
    assert in_memory.declaration("a")["declaration_sha256"] == \
        loaded.declaration("a")["declaration_sha256"]


def _write(tmp_path):
    (tmp_path / "t.yml").write_text(yaml.safe_dump({"indicators": BASE}))
    return tmp_path


def test_every_shipped_indicator_carries_a_hash():
    reg = IndicatorRegistry.load(SEEDS)
    for ind_id in reg.all():
        digest = reg.declaration(ind_id)["declaration_sha256"]
        assert isinstance(digest, str) and len(digest) == 64, ind_id
