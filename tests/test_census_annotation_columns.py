"""
tests/test_census_annotation_columns.py

ACS-7. The provider empties every Census annotation so no very negative
number is ever read as a value. Emptying used to throw the meaning away with
it: -333333333 on a median's margin says the median sits in an open-ended
interval ("50.0 or more"), which is a claim about the unit, not an absence.
The provider now keeps the code it emptied in a column beside the variable,
named <variable>_annotation, and only for variables where one occurred.

These tests stub the Census response, so they need no network and no key.
The rows are shaped like the real 2024 response for Hancock County, Georgia,
checked by hand on 2026-10-28: B25071_001E "51.0", B25071_001M "-333333333.0".
"""

import json

import pandas as pd
import pytest

from canopy.providers.census_acs import CensusACSProvider


ROWS = [
    ["NAME", "B25071_001E", "B25071_001M", "B28002_001E", "state", "county"],
    ["Hancock County, Georgia", "51.0", "-333333333.0", "3000", "13", "141"],
    ["Somewhere County, Georgia", "30.2", "1.5", "-666666666", "13", "999"],
    ["Elsewhere County, Georgia", "28.4", "2.1", "4100", "13", "998"],
]


class _FakeResponse:
    status_code = 200
    url = "https://api.census.gov/data/2024/acs/acs5"
    headers = {"content-type": "application/json"}

    def __init__(self, rows):
        self._rows = rows
        self.text = json.dumps(rows)

    def json(self):
        return self._rows

    def raise_for_status(self):
        return None


SOURCE = {
    "type": "api",
    "provider": "census_acs",
    "dataset": "acs/acs5",
    "year": 2024,
    "geography": "county",
    "within": {"state": "13"},
    "variables": ["B25071_001E", "B25071_001M", "B28002_001E"],
    "api_key": "test-key-not-real",
}


@pytest.fixture
def stub_census(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResponse(ROWS))


@pytest.mark.parametrize("ext", [".parquet", ".csv"])
def test_emptied_annotation_is_kept_beside_its_variable(stub_census, tmp_path, ext):
    path = tmp_path / f"acs{ext}"
    result = CensusACSProvider().acquire(SOURCE, path, "acs_test")
    assert result.success, result.message

    frame = (pd.read_parquet(path) if ext == ".parquet"
             else pd.read_csv(path, dtype=str, keep_default_na=False))
    by_geoid = frame.set_index("GEOID")

    # the value is still emptied: no very negative number survives
    assert pd.isna(by_geoid.loc["13141", "B25071_001M"]) or by_geoid.loc["13141", "B25071_001M"] == ""

    # and the receipt is kept, in canonical spelling whatever decimals arrived
    assert by_geoid.loc["13141", "B25071_001M_annotation"] == "-333333333"
    assert by_geoid.loc["13999", "B28002_001E_annotation"] == "-666666666"

    # a unit with an ordinary value carries no annotation
    for geoid in ("13999", "13998"):
        cell = by_geoid.loc[geoid, "B25071_001M_annotation"]
        assert pd.isna(cell) or cell == ""


def test_annotation_column_only_where_an_annotation_occurred(stub_census, tmp_path):
    path = tmp_path / "acs.parquet"
    result = CensusACSProvider().acquire(SOURCE, path, "acs_test")
    frame = pd.read_parquet(path)

    assert "B25071_001E_annotation" not in frame.columns
    assert set(c for c in frame.columns if c.endswith("_annotation")) == {
        "B25071_001M_annotation", "B28002_001E_annotation"}
    assert result.provenance["annotation_columns"] == [
        "B25071_001M_annotation", "B28002_001E_annotation"]


def test_annotation_columns_are_text_not_numbers(stub_census, tmp_path):
    path = tmp_path / "acs.parquet"
    CensusACSProvider().acquire(SOURCE, path, "acs_test")
    frame = pd.read_parquet(path)

    # a code read as a number is the exact failure ACS-6 fixed; it must not
    # come back through the side door
    assert pd.api.types.is_string_dtype(frame["B25071_001M_annotation"])
    assert pd.api.types.is_float_dtype(frame["B25071_001E"])
