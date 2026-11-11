"""
tests/test_district_geographies.py

Sprint 04, Part 1: the ACS provider builds requests and GEOIDs for both
legislative chambers, nested within a state, so a district's values join its
TIGER boundary by code, never by name. No network.
"""

from canopy.providers.census_acs import GEOGRAPHY, CensusACSProvider

CHAMBERS = ["state legislative district (upper chamber)",
            "state legislative district (lower chamber)"]


def source(geography, **extra):
    return {"provider": "census_acs", "dataset": "acs/acs5", "year": 2024,
            "geography": geography, "within": {"state": "23"},
            "indicators": ["cii_broadband"], **extra}


def test_both_chambers_are_known_geographies_nested_in_a_state():
    for g in CHAMBERS:
        assert GEOGRAPHY[g]["parents"] == ["state"]
        assert GEOGRAPHY[g]["width"] == {"state": 2, g: 3}


def test_a_chamber_request_asks_for_every_district_in_the_state():
    url, params, problems = CensusACSProvider().build_request(
        source("state legislative district (lower chamber)"))
    assert problems == []
    assert url.endswith("/2024/acs/acs5")
    assert params["for"] == "state legislative district (lower chamber):*"
    assert params["in"] == "state:23"


def test_a_chamber_without_its_state_is_refused():
    cfg = source("state legislative district (upper chamber)")
    cfg["within"] = {}
    _, _, problems = CensusACSProvider().build_request(cfg)
    assert any("must be nested within state" in p for p in problems)


# ── 2020 blocks, county by county (Sprint 04, Part 1b) ───────────────────
import csv
import sys
import types


def _fake_requests(monkeypatch, calls):
    """a stand-in for requests: two Maine counties, two blocks in each."""
    class Resp:
        def __init__(self, url, body):
            self.url, self._body, self.status_code = url, body, 200
            self.text, self.headers = "ok", {"content-type": "application/json"}
        def json(self):
            return self._body
        def raise_for_status(self):
            pass

    def get(url, params=None, timeout=None):
        calls.append(dict(params or {}))
        if params.get("for") == "county:*":
            return Resp(url, [["NAME", "state", "county"], ["A", "23", "001"], ["B", "23", "015"]])
        county = params["in"].split("county:")[1].split()[0]
        assert county != "*", "blocks were requested across every county at once"
        return Resp(url, [["P1_001N", "H1_001N", "H1_002N", "state", "county", "tract", "block"],
                          ["10", "6", "4", "23", county, "000100", "1000"],
                          ["0", "0", "0", "23", county, "000100", "1001"]])
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(get=get))


def test_blocks_are_fetched_one_county_at_a_time_and_keyed_by_geoid(tmp_path, monkeypatch):
    calls = []
    _fake_requests(monkeypatch, calls)
    cfg = {"provider": "census_acs", "dataset": "dec/pl", "year": 2020, "geography": "block",
           "within": {"state": "23", "county": "*", "tract": "*"},
           "variables": ["P1_001N", "H1_001N", "H1_002N"]}
    out = tmp_path / "blocks.csv"
    res = CensusACSProvider().acquire(cfg, out, "blocks_2020")
    assert res.success, res.message
    rows = list(csv.DictReader(open(out)))
    assert [r["GEOID"] for r in rows] == ["230010001001000", "230010001001001",
                                          "230150001001000", "230150001001001"]
    assert rows[0]["H1_002N"] == "4"
    # one county list, then one request per county; never county:* for blocks
    assert len(calls) == 3 and all("county:*" not in c.get("in", "") for c in calls[1:])


def test_a_decennial_release_is_labelled_as_a_count_not_an_estimate():
    assert CensusACSProvider.vintage_window("dec/pl", 2020) == "2020 Census (decennial count)"
