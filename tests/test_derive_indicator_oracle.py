"""
tests/test_derive_indicator_oracle.py

derive_indicator.R and canopy/indicator_preview.py implement one declaration
twice, in two languages. they must agree exactly: value, margin, margin
status and empty reason, row for row. a disagreement is a finding about one
of them (D-16).

the primitive is invoked the way the orchestrator invokes it, params as a JSON
file, so ARG-1's list-versus-vector difference is exercised rather than
avoided. skipped where Rscript or rewildr is not installed.
"""

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from canopy.indicators import preview as ip
from canopy.indicators import IndicatorRegistry

ROOT = Path(__file__).resolve().parents[1]
PRIMITIVE = ROOT / "soil" / "transform" / "derive_indicator.R"
SEEDS = ROOT / "seeds" / "indicators"
IDS = ["cii_broadband", "cii_rent_burden", "cii_no_vehicle"]
# a small-sample rule both halves apply (D-106); its numbers are a fixture,
# not the declared rule
RULE = {"min_households": 1000, "max_cv": 0.02}


def _r_ready() -> bool:
    if shutil.which("Rscript") is None:
        return False
    probe = subprocess.run(
        ["Rscript", "-e", "quit(status = as.integer(!requireNamespace('rewildr', quietly = TRUE)))"],
        capture_output=True)
    return probe.returncode == 0


pytestmark = pytest.mark.skipif(not _r_ready(), reason="Rscript with rewildr not available")


@pytest.fixture
def fixture_source(tmp_path):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    frame = pd.DataFrame({
        "GEOID": ["23005", "23029", "23999"],
        "NAME": ["Cumberland County, Maine", "Washington County, Maine", "Nowhere County, Maine"],
        "B28002_004E": [1000.0, 500.0, 0.0], "B28002_001E": [1200.0, 600.0, 0.0],
        "B28002_004M": [50.0, 40.0, 0.0], "B28002_001M": [60.0, 30.0, 0.0],
        "B25071_001E": [29.4, None, 51.0], "B25071_001M": [1.2, None, None],
        "B08201_002E": [90.0, 30.0, 0.0], "B08201_001E": [1200.0, 600.0, 0.0],
        "B08201_002M": [15.0, 9.0, 0.0], "B08201_001M": [60.0, 30.0, 0.0],
        # what rent burden rests on (Sprint 02); the third is left empty
        "B25070_001E": [30000.0, 9000.0, None], "B25070_011E": [1500.0, 300.0, 10.0],
        "B25070_001M": [400.0, 200.0, None], "B25070_011M": [90.0, 40.0, 5.0],
    })
    for c in frame.columns[2:]:
        frame[c] = frame[c].astype("Float64")
    frame["GEOID"] = frame["GEOID"].astype("string")
    # ACS-7: an open-ended median, shaped as the provider writes it. 51 with
    # -333333333 on its margin is how the Census reports "50.0 or more".
    frame["B25071_001M_annotation"] = pd.array([None, None, "-333333333"], dtype="string")
    path = tmp_path / "source.parquet"
    frame.to_parquet(path, index=False)
    return path, frame


def _run_primitive(tmp_path, source_path, declarations, reliability=None):
    inputs = tmp_path / "inputs.json"
    params = tmp_path / "params.json"
    out = tmp_path / "derive_values.parquet"
    inputs.write_text(json.dumps({"source": str(source_path)}))
    params.write_text(json.dumps({
        "indicators": declarations, "spatial_unit": "county",
        "time": "2020-2024 (5-year estimates)", "authority": "us_census_acs",
        "joins_to": "governance_unit",
        **({"reliability": reliability} if reliability else {})}))
    proc = subprocess.run(
        ["Rscript", str(PRIMITIVE), str(inputs), str(out), str(params)],
        capture_output=True, text=True, cwd=ROOT)
    lines = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
    assert lines, f"no protocol response.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    return json.loads(lines[-1]), out, proc


def _same(a, b) -> bool:
    if a is None or (isinstance(a, float) and math.isnan(a)):
        return b is None or (isinstance(b, float) and math.isnan(b))
    return a == b


def test_r_agrees_with_the_preview_exactly(tmp_path, fixture_source):
    import pandas as pd
    source_path, frame = fixture_source
    reg = IndicatorRegistry.load(SEEDS)
    decls = [reg.declaration(i) for i in IDS]

    response, out, proc = _run_primitive(tmp_path, source_path, decls, reliability=RULE)
    assert response["status"] == "success", (response, proc.stderr)
    r_rows = pd.read_parquet(out)

    for ind_id in IDS:
        py_rows, _ = ip.derive(frame, reg.get(ind_id), authority=None, time=None,
                               reliability=RULE)
        mine = r_rows[r_rows["indicator"] == ind_id].reset_index(drop=True)
        assert len(mine) == len(py_rows), ind_id
        for i, py in enumerate(py_rows):
            r = mine.iloc[i]
            assert r["unit_code"] == py["unit"]["code"]
            for field in ("value", "moe", "moe_status", "bound", "empty_reason",
                          "households", "households_counts", "households_reason",
                          "cv", "reliability_note"):
                rv = r[field]
                rv = None if pd.isna(rv) else (rv.item() if hasattr(rv, "item") else rv)
                assert _same(py[field], rv), (ind_id, py["unit"]["code"], field, py[field], rv)


def test_an_open_ended_median_is_a_bound_in_both_languages(tmp_path, fixture_source):
    import pandas as pd
    source_path, frame = fixture_source
    reg = IndicatorRegistry.load(SEEDS)
    response, out, proc = _run_primitive(tmp_path, source_path, [reg.declaration("cii_rent_burden")])
    assert response["status"] == "success", (response, proc.stderr)
    r = pd.read_parquet(out).set_index("unit_code").loc["23999"]
    assert r["moe_status"] == "open_ended"
    assert r["bound"] == "50.0 or more"
    # D-105: the encoding is not a measurement, so the value rests empty
    assert pd.isna(r["value"])
    assert r["empty_reason"] == "open-ended median: 50.0 or more"


def test_every_value_says_what_it_rests_on_in_r(tmp_path, fixture_source):
    import pandas as pd
    source_path, _ = fixture_source
    reg = IndicatorRegistry.load(SEEDS)
    response, out, proc = _run_primitive(tmp_path, source_path, [reg.declaration(i) for i in IDS])
    assert response["status"] == "success", (response, proc.stderr)
    rows = pd.read_parquet(out).set_index(["indicator", "unit_code"])
    assert rows.loc[("cii_broadband", "23005"), "households"] == 1200.0
    assert rows.loc[("cii_rent_burden", "23005"), "households"] == 28500.0
    assert pd.isna(rows.loc[("cii_rent_burden", "23999"), "households"])
    assert rows.loc[("cii_rent_burden", "23999"), "households_reason"] == \
        "source count empty: B25070_001E"


def test_the_envelope_metadata_is_what_the_schema_expects(tmp_path, fixture_source):
    source_path, _ = fixture_source
    reg = IndicatorRegistry.load(SEEDS)
    response, _, proc = _run_primitive(tmp_path, source_path, [reg.declaration(i) for i in IDS])
    assert response["status"] == "success", (response, proc.stderr)
    assert "crs" in response and response["crs"] is None
    for field in ("row_count", "variables", "id_field", "spatial_unit"):
        assert field in response, field
    assert response["row_count"] == 9
    assert response["id_field"] == "measurement_id"
    assert response["joins_to"] == "governance_unit"
    assert response["indicators"] == IDS


def test_a_source_missing_a_variable_is_refused_by_name(tmp_path, fixture_source):
    source_path, frame = fixture_source
    frame.drop(columns=["B25071_001E"]).to_parquet(source_path, index=False)
    reg = IndicatorRegistry.load(SEEDS)
    response, _, _ = _run_primitive(tmp_path, source_path, [reg.declaration("cii_rent_burden")])
    assert response["status"] == "failure"
    assert "B25071_001E" in response["message"]