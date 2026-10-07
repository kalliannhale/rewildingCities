"""
tests/test_standardize_oracle.py

standardize_indicator.R and canopy/indicator_preview.standings() must agree:
percentile exactly, z within 1e-12 (R's mean() and Python's fsum accumulate
differently in the last bits; the percentile involves no sum and must be
exact). params pass as a file, as the orchestrator passes them. skipped where
Rscript or rewildr is unavailable.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from canopy.indicators import preview as ip
from canopy.indicators import IndicatorRegistry

ROOT = Path(__file__).resolve().parents[1]
PRIMITIVE = ROOT / "roots" / "indicators" / "standardize_indicator.R"
REG = IndicatorRegistry.load(ROOT / "seeds" / "indicators")
IDS = ["cii_broadband", "cii_no_vehicle"]


def _r_ready() -> bool:
    if shutil.which("Rscript") is None:
        return False
    probe = subprocess.run(
        ["Rscript", "-e", "quit(status = as.integer(!requireNamespace('rewildr', quietly = TRUE)))"],
        capture_output=True)
    return probe.returncode == 0


pytestmark = pytest.mark.skipif(not _r_ready(), reason="Rscript with rewildr not available")

CODES = ["23001", "23003", "23005", "23007", "72001"]
VALUES = {"cii_broadband": [90.0, 85.0, 92.5, None, 70.0],
          "cii_no_vehicle": [0.0, 0.0, 6.9, 9.2, 12.0]}


@pytest.fixture
def values_file(tmp_path):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    recs = []
    for ind, vals in VALUES.items():
        for c, v in zip(CODES, vals):
            recs.append({"measurement_id": f"{ind}:{c}", "unit_authority": "us_census_geoid",
                         "unit_code": c, "name": c, "indicator": ind, "value": v,
                         "time": "2020-2024 (5-year estimates)"})
    df = pd.DataFrame(recs)
    df["value"] = df["value"].astype("Float64")
    path = tmp_path / "values.parquet"
    df.to_parquet(path, index=False)
    return path


def _run(tmp_path, values_path, params):
    inputs = tmp_path / "inputs.json"
    pfile = tmp_path / "params.json"
    out = tmp_path / "standings.parquet"
    inputs.write_text(json.dumps({"values": str(values_path)}))
    pfile.write_text(json.dumps(params))
    proc = subprocess.run(["Rscript", str(PRIMITIVE), str(inputs), str(out), str(pfile)],
                          capture_output=True, text=True, cwd=ROOT)
    lines = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
    assert lines, f"no protocol response.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    return json.loads(lines[-1]), out, proc


@pytest.mark.parametrize("sd", ["sample", "population"])
def test_r_agrees_with_the_preview(tmp_path, values_file, sd):
    import pandas as pd
    params = {"indicators": [REG.declaration(i) for i in IDS], "sd": sd,
              "exclude_state_fips": ["72"]}
    resp, out, proc = _run(tmp_path, values_file, params)
    assert resp["status"] == "success", (resp, proc.stderr)
    got = pd.read_parquet(out)
    for ind_id in IDS:
        rows = [{"unit": {"code": c}, "name": c, "value": v}
                for c, v in zip(CODES, VALUES[ind_id])]
        py, pop = ip.standings(rows, REG.get(ind_id), sd=sd, exclude_state_fips=("72",))
        mine = got[got["indicator"] == ind_id].reset_index(drop=True)
        assert int(mine["reference_n"].iloc[0]) == pop["n"]
        for i, p in enumerate(py):
            r = mine.iloc[i]
            rp = None if pd.isna(r["percentile"]) else float(r["percentile"])
            rz = None if pd.isna(r["z"]) else float(r["z"])
            assert rp == p["percentile"], (ind_id, CODES[i], rp, p["percentile"])
            if p["z"] is None:
                assert rz is None
            else:
                assert abs(rz - p["z"]) <= 1e-12, (ind_id, CODES[i], rz, p["z"])
            ro = None if pd.isna(r["outside_reason"]) else r["outside_reason"]
            assert ro == p["outside_reason"]


def test_there_is_no_default_sd(tmp_path, values_file):
    params = {"indicators": [REG.declaration(i) for i in IDS], "sd": "whatever"}
    resp, _, _ = _run(tmp_path, values_file, params)
    assert resp["status"] == "failure" and "no default" in resp["message"]


def test_every_indicator_in_the_table_needs_a_direction(tmp_path, values_file):
    params = {"indicators": [REG.declaration("cii_broadband")], "sd": "sample"}
    resp, _, _ = _run(tmp_path, values_file, params)
    assert resp["status"] == "failure" and "cii_no_vehicle" in resp["message"]