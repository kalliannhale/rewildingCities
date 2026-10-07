"""
tests/test_weights.py

a weighting is a declared, hashed claim about what matters, refused when it
does not say whose it is or spends CII's chip budget wrongly.
"""

from pathlib import Path

import pytest

from canopy.indicators import IndicatorRegistry
from canopy.indicators.weights import WeightsRegistry

ROOT = Path(__file__).resolve().parents[1]
IDS = IndicatorRegistry.load(ROOT / "seeds" / "indicators").all()


def test_the_equal_chips_weighting_loads_and_covers_all_27_once():
    w = WeightsRegistry.load(ROOT / "seeds" / "weights", IDS).declaration("cii_2026_equal_chips")
    used = [c for p in w["pillars"].values() for c in p["components"]]
    assert len(used) == 27 and len(set(used)) == 27
    assert w["is_publishers_weighting"] is False
    assert len(w["pillars"]["environmental_resilience"]["components"]) == 3
    assert len(w["declaration_sha256"]) == 64


def write(tmp_path, body):
    (tmp_path / "w.yml").write_text(body)
    return tmp_path


BASE = """id: x
name: x
defined_by: someone
is_publishers_weighting: false
budget: {budget}
pillars:
{pillars}
"""


def five(chips="10", comp="10"):
    return "".join(f"  p{i}:\n    name: P{i}\n    chips: {chips}\n    components:\n"
                   f"      cii_pub_news_outlets: {comp}\n" for i in range(5))


def test_cii_budget_is_enforced(tmp_path):
    with pytest.raises(ValueError, match="10 x 1"):
        WeightsRegistry.load(write(tmp_path, BASE.format(budget="cii_advisory_rule",
                                                           pillars=five(comp="12"))), IDS)


def test_fifty_chips_across_five_pillars(tmp_path):
    with pytest.raises(ValueError, match="50 chips"):
        WeightsRegistry.load(write(tmp_path, BASE.format(budget="cii_advisory_rule",
                                                           pillars=five(chips="11"))), IDS)


def test_a_free_budget_allows_any_positive_chips(tmp_path):
    WeightsRegistry.load(write(tmp_path, BASE.format(budget="free", pillars=five(chips="3", comp="7"))), IDS)


def test_an_undeclared_indicator_is_refused(tmp_path):
    body = BASE.format(budget="free", pillars="  p:\n    name: P\n    chips: 1\n    components:\n      nope: 1\n")
    with pytest.raises(ValueError, match="undeclared"):
        WeightsRegistry.load(write(tmp_path, body), IDS)


def test_whose_weighting_it_is_must_be_said(tmp_path):
    body = BASE.format(budget="free", pillars=five()).replace("is_publishers_weighting: false\n", "")
    with pytest.raises(ValueError, match="is_publishers_weighting"):
        WeightsRegistry.load(write(tmp_path, body), IDS)
