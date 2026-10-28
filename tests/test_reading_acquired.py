"""
tests/test_reading_acquired.py

WON-9: a requirement read `as_acquired` is met by a source the manifest
declares available AND that is on disk, and says so. declared-but-unfetched
is still a gap. WON-11: a curiosity no method answers is said, not dropped.
"""

import shutil
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class Loam:
    """the two calls reading makes: find rows by tier, count them."""
    def __init__(self, arrived): self.arrived = arrived
    def find(self, plot=None, tier=None, **k):
        return [{"semantic_type": t} for t in self.arrived] if tier == "arrived" else []
    def count(self, plot=None, tier=None):
        return len(self.find(plot=plot, tier=tier))


@pytest.fixture
def garden(tmp_path):
    for d in ("garden/curiosity-space", "garden/methods"):
        shutil.copytree(ROOT / d, tmp_path / d)
    plot = tmp_path / "plots" / "maine"
    (plot / ".data").mkdir(parents=True)
    (plot / ".data" / "acs_us.parquet").write_text("x")
    (plot / "manifest.yml").write_text(yaml.safe_dump({"datasets": {
        "acs_us_county_2024": {"available": True, "semantic_type": "indicator_source",
                               "cache": {"path": ".data/acs_us.parquet"}},
        "county_locations_2024": {"available": False, "semantic_type": "unit_locations",
                                  "cache": {"path": ".data/never.parquet"}}}}))
    return tmp_path


def by_id(reading, cid):
    return next(c for c in reading.curiosities if c.curiosity_id == cid)


def test_an_acquired_source_meets_an_as_acquired_requirement_and_says_so(garden):
    from canopy.wonder.reading import read_plot
    r = read_plot(Loam(["indicator_source"]), "maine", root=garden)
    m = next(m for m in by_id(r, "broadband_access").methods if m.method_id == "cii_indicator_values")
    assert m.verdict == "runnable"
    req = m.requirements[0]
    assert req.satisfied_by == "indicator_source" and req.as_acquired is True


def test_declared_but_never_fetched_is_still_a_gap(garden):
    from canopy.wonder.reading import read_plot
    r = read_plot(Loam(["indicator_source", "unit_locations"]), "maine", root=garden)
    full = by_id(r, "civic_health_overall").methods[0]
    assert full.verdict == "blocked" and full.missing_critical == ["unit_locations"]


def test_a_file_on_disk_without_available_true_does_not_count(garden):
    from canopy.wonder.reading import read_plot
    m = garden / "plots" / "maine" / "manifest.yml"
    doc = yaml.safe_load(m.read_text())
    doc["datasets"]["acs_us_county_2024"]["available"] = False
    m.write_text(yaml.safe_dump(doc))
    r = read_plot(Loam(["indicator_source"]), "maine", root=garden)
    m0 = next(m for m in by_id(r, "broadband_access").methods if m.method_id == "cii_indicator_values")
    assert m0.verdict == "blocked"


def test_curiosities_with_no_method_are_said_as_the_research_agenda(garden):
    from canopy.wonder.possibility import explore
    ps = explore(Loam(["indicator_source"]), "maine", root=garden)
    unanswered = sorted(p.curiosity_id for p in ps if p.verdict == "unanswered")
    assert unanswered == ["data_fragility", "health_information",
                          "information_flow", "within_county_disparities"]
    said = next(p for p in ps if p.curiosity_id == "information_flow").say()
    assert "no method answers this yet" in said
    assert ps[-1].verdict == "unanswered"
