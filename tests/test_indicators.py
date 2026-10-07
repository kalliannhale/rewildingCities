"""
tests/test_indicators.py

durable invariants for the indicator registry: the shipped declarations
load, and every refusal the loader promises actually happens.
"""

from pathlib import Path

import pytest
import yaml

from canopy.indicators import IndicatorRegistry

REPO = Path(__file__).resolve().parents[1]
INDICATORS = REPO / "seeds" / "indicators"

GOOD = {
    "name": "x", "defined_by": "test", "measures": "thing", "unit": "percent",
    "derivation": {"kind": "ratio", "numerator": ["A_001E"],
                   "denominator": "A_002E", "scale": 100},
    "direction": "higher_is_better", "aggregation": "population_weighted_mean",
    "weight_by": "A_002E", "uncertainty": "acs_moe",
    "source": {"provider": "census_acs", "dataset": "acs/acs5"},
}


def _load(tmp_path, entries, name="t.yml"):
    (tmp_path / name).write_text(yaml.safe_dump({"indicators": entries}))
    return IndicatorRegistry.load(tmp_path)


def test_shipped_declarations_load():
    reg = IndicatorRegistry.load(INDICATORS)
    assert "cii_broadband" in reg.all()
    assert "limited_english_households" in reg.all()


def test_broadband_fetches_its_margins_of_error():
    ind = IndicatorRegistry.load(INDICATORS).get("cii_broadband")
    assert ind.acquisition_variables() == [
        "B28002_004E", "B28002_001E", "B28002_004M", "B28002_001M"]


def test_good_entry_loads(tmp_path):
    assert _load(tmp_path, {"ok": GOOD}).all() == ["ok"]


def test_empty_directory_refused(tmp_path):
    with pytest.raises(FileNotFoundError):
        IndicatorRegistry.load(tmp_path)


def test_collision_across_files_refused(tmp_path):
    (tmp_path / "a.yml").write_text(yaml.safe_dump({"indicators": {"dup": GOOD}}))
    (tmp_path / "b.yml").write_text(yaml.safe_dump({"indicators": {"dup": GOOD}}))
    with pytest.raises(ValueError, match="collision"):
        IndicatorRegistry.load(tmp_path)


@pytest.mark.parametrize("change, message", [
    ({"direction": None}, "missing required"),
    ({"rationle": "typo"}, "unknown field"),
    ({"direction": "up"}, "not one of"),
    ({"weight_by": None}, "mean of means"),
    ({"source": {"provider": "chr"}}, "only the ACS"),
    ({"derivation": {"kind": "ratio", "numerator": "A_001E",
                     "denominator": "A_002E", "scale": 100}}, "non-empty list"),
    ({"derivation": {"kind": "ratio", "numerator": ["A_001E"],
                     "denominator": "A_002E"}}, "positive numeric scale"),
    ({"derivation": {"kind": "ratio", "numerator": ["A_001"],
                     "denominator": "A_002E", "scale": 100}}, "ending in E"),
    ({"replicates": {"publisher": "cii"}}, "must say exactly which"),
])
def test_refusals(tmp_path, change, message):
    spec = {**GOOD, **change}
    spec = {k: v for k, v in spec.items() if v is not None}
    with pytest.raises(ValueError, match=message):
        _load(tmp_path, {"bad": spec})
