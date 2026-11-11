"""
tests/test_standings_at_3129.py

Sprint 02, item 1: county rent burden ranks among exactly 3 129 counties, as
CII's does (CII-11). Open-ended medians rest empty (D-105), so they leave the
reference population, and Puerto Rico is outside it by declaration (D-44).

Runs only on a machine holding the national acquisition with Sprint 02's
variables (re-acquired after ACQ-4 marked it stale). Elsewhere it skips, by
name. If it fails with a number other than 3 129, CII-11's hypothesis (that
the 15 counties CII left blank are the open-ended ones) is refuted, and the
failure is a finding.
"""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
NATIONAL = REPO / "plots" / "maine" / ".data" / "acs_us_county_2024.parquet"


def test_county_rent_burden_ranks_among_exactly_3129_counties():
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    if not NATIONAL.is_file():
        pytest.skip(f"no national acquisition at {NATIONAL}")
    frame = pd.read_parquet(NATIONAL)
    if "B25070_001E" not in frame.columns:
        pytest.skip("the national acquisition predates Sprint 02; re-acquire it (ACQ-4)")

    from canopy.indicators import IndicatorRegistry
    from canopy.indicators import preview as ip
    GEOID = "us_census_geoid"
    ind = IndicatorRegistry.load(REPO / "seeds" / "indicators").get("cii_rent_burden")
    rows, _ = ip.derive(frame, ind, unit_authority=GEOID, authority=None, time=None)
    _, population = ip.standings(rows, ind, sd="sample", exclude_state_fips=("72",))
    assert population["n"] == 3129
