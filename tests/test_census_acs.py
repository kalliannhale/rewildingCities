"""
tests/test_census_acs.py

durable invariants for the ACS provider, with the Census API replaced by a
canned response so nothing touches the network.
"""

import pytest

from canopy.providers.census_acs import CensusACSProvider

SOURCE = {
    "type": "api", "provider": "census_acs", "dataset": "acs/acs5", "year": 2024,
    "geography": "county", "within": {"state": "23"},
    "indicators": ["cii_broadband"], "api_key": "SECRET-KEY",
}


class FakeResponse:
    def __init__(self, rows, url="https://api.census.gov/data/2024/acs/acs5"):
        self._rows, self.url, self.status_code = rows, url, 200
        self.text, self.headers = "[]", {"content-type": "application/json"}

    def json(self):
        return self._rows

    def raise_for_status(self):
        pass


def _fake_get(rows, seen):
    def get(url, params=None, timeout=None):
        seen["url"], seen["params"] = url, dict(params or {})
        return FakeResponse(rows)
    return get


ROWS = [
    ["NAME", "B28002_004E", "B28002_001E", "B28002_004M", "state", "county"],
    ["Cumberland County, Maine", "112000", "120826", "900", "23", "005"],
    ["Piscataquis County, Maine", "-666666666", "7500", "300", "23", "021"],
]


def test_indicators_resolve_to_estimates_and_margins():
    variables, problems = CensusACSProvider.resolve_variables(SOURCE)
    assert problems == []
    assert variables == ["B28002_004E", "B28002_001E", "B28002_004M", "B28002_001M"]


def test_dataset_mismatch_is_refused():
    _, problems = CensusACSProvider.resolve_variables({**SOURCE, "dataset": "acs/acs1"})
    assert problems and "different estimate" in problems[0]


def test_unknown_indicator_is_refused():
    _, problems = CensusACSProvider.resolve_variables({**SOURCE, "indicators": ["nope"]})
    assert problems and "unknown indicator" in problems[0]


def test_acquire_records_provenance_and_never_the_key(tmp_path, monkeypatch):
    import requests
    seen = {}
    monkeypatch.setattr(requests, "get", _fake_get(ROWS, seen))
    out = tmp_path / "acs.csv"
    result = CensusACSProvider().acquire(SOURCE, out, "acs_county_2024")

    assert result.success
    assert seen["params"]["key"] == "SECRET-KEY"
    prov = result.provenance
    assert "key" not in prov["request"]["params"]
    assert "SECRET-KEY" not in repr(prov)
    assert prov["vintage_window"] == "2020-2024 (5-year estimates)"
    assert prov["variables_not_returned"] == ["B28002_001M"]
    assert prov["annotations_emptied"] == {"-666666666": 1}
    assert any("absent from the response" in w["message"] for w in result.warnings)


def test_parquet_keeps_geoid_a_string_and_jams_null(tmp_path, monkeypatch):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    import requests
    monkeypatch.setattr(requests, "get", _fake_get(ROWS, {}))
    out = tmp_path / "acs.parquet"
    assert CensusACSProvider().acquire(SOURCE, out, "acs_county_2024").success

    frame = pd.read_parquet(out)
    assert frame["GEOID"].tolist() == ["23005", "23021"]
    assert str(frame["GEOID"].dtype) in ("string", "object")
    assert frame.loc[1, "B28002_004E"] is pd.NA or pd.isna(frame.loc[1, "B28002_004E"])
    assert frame.loc[0, "B28002_004E"] == 112000.0


def test_too_many_variables_is_refused():
    many = {**SOURCE, "indicators": [], "variables": [f"B01001_{i:03d}E" for i in range(1, 60)]}
    _, _, problems = CensusACSProvider().build_request(many)
    assert problems and "50 per request" in problems[0]
