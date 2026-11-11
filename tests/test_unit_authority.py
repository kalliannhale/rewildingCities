"""
tests/test_unit_authority.py

D-131 and D-133, the Python half. A Census GEOID is unique only within its
level: 23001 is Androscoggin County, House District 1 and Senate District 1
(GRAPH-1). So every derivation says whose codes name its units, from
Contract 3's five, and nothing assumes one. The R half is held to the same
refusals by tests/test_derive_indicator_oracle.py.

TWIN-2 rides along: the preview reads the unit column, its padding and the
name column as derive_indicator.R does, instead of GEOID and NAME by luck.

Runs without R, pyarrow or network.
"""

from pathlib import Path

import pandas as pd
import pytest

from canopy.indicators import IndicatorRegistry
from canopy.indicators import preview as ip

SEEDS = Path(__file__).resolve().parents[1] / "seeds" / "indicators"


def broadband():
    return IndicatorRegistry.load(SEEDS).get("cii_broadband")


def frame(**rename):
    f = pd.DataFrame({
        "GEOID": ["23001", "23003"],
        "NAME": ["one", "three"],
        "B28002_004E": [900.0, 20.0], "B28002_001E": [1000.0, 30.0],
        "B28002_004M": [40.0, 9.0], "B28002_001M": [30.0, 8.0],
    })
    return f.rename(columns=rename)


@pytest.mark.parametrize("ua", ["us_census_geoid", "us_census_sldl", "us_census_sldu",
                                "us_census_aiannh", "megis"])
def test_each_of_contract_3s_authorities_is_written_on_every_row(ua):
    rows, _ = ip.derive(frame(), broadband(), unit_authority=ua, authority=None, time=None)
    assert {r["unit"]["authority"] for r in rows} == {ua}


@pytest.mark.parametrize("ua", [None, "", "   "])
def test_an_empty_unit_authority_is_refused_by_name(ua):
    with pytest.raises(ip.PreviewError, match="unit_authority"):
        ip.derive(frame(), broadband(), unit_authority=ua, authority=None, time=None)


def test_an_unknown_unit_authority_is_refused_by_name():
    with pytest.raises(ip.PreviewError, match="us_census_sdll"):
        ip.derive(frame(), broadband(), unit_authority="us_census_sdll",
                  authority=None, time=None)


def test_derive_and_preview_have_no_default():
    with pytest.raises(TypeError, match="unit_authority"):
        ip.derive(frame(), broadband(), authority=None, time=None)
    with pytest.raises(TypeError, match="unit_authority"):
        ip.preview("test", "cii_broadband")


def test_the_unit_and_name_columns_are_read_as_declared():
    rows, _ = ip.derive(frame(GEOID="DISTRICT", NAME="LABEL"), broadband(),
                        unit_authority="us_census_sldl", authority=None, time=None,
                        unit_column="DISTRICT", name_column="LABEL")
    assert [r["unit"]["code"] for r in rows] == ["23001", "23003"]
    assert [r["name"] for r in rows] == ["one", "three"]


def test_a_missing_unit_column_is_refused_by_name():
    with pytest.raises(ip.PreviewError, match="DISTRICT"):
        ip.derive(frame(), broadband(), unit_authority="us_census_sldl",
                  authority=None, time=None, unit_column="DISTRICT")


def test_padding_restores_lost_zeros_and_refuses_what_it_would_invent():
    f = frame()
    f["GEOID"] = ["3001", "3003"]
    rows, _ = ip.derive(f, broadband(), unit_authority="us_census_geoid",
                        authority=None, time=None, unit_pad=5)
    assert [r["unit"]["code"] for r in rows] == ["03001", "03003"]
    f["GEOID"] = ["3001", "230031"]
    with pytest.raises(ip.PreviewError, match="wider than 5"):
        ip.derive(f, broadband(), unit_authority="us_census_geoid",
                  authority=None, time=None, unit_pad=5)


def test_a_repeated_unit_code_is_refused_as_the_r_refuses_it():
    f = frame()
    f["GEOID"] = ["23001", "23001"]
    with pytest.raises(ip.PreviewError, match="more than once"):
        ip.derive(f, broadband(), unit_authority="us_census_geoid", authority=None, time=None)


def test_the_cli_requires_the_flag(capsys):
    with pytest.raises(SystemExit):
        ip.main(["show", "test", "cii_broadband"])
    assert "--unit-authority" in capsys.readouterr().err


def test_the_api_refuses_a_preview_without_a_unit_authority():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from canopy.api.indicators import router
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/plots/test/indicators/cii_broadband")
    assert response.status_code == 422
    assert "unit_authority" in response.text
