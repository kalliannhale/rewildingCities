"""
tests/test_index_r_oracle.py

impute_nearest_neighbor.R and weighted_index.R against canopy/index_oracle,
chained as the experiment chains them: impute, then pillars, then composite.
values and percentiles must agree exactly; donors must be the same county.
params pass as files, as the orchestrator passes them. skipped without R.

every index row carries its unit_authority and an id of index:authority:code
(D-132), and an index across units of more than one authority, or of none,
is refused by name (SEAM-1, D-190).
"""

import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from canopy.indicators import oracle as ox

ROOT = Path(__file__).resolve().parents[1]
IMPUTE = ROOT / "roots" / "indicators" / "impute_nearest_neighbor.R"
INDEX = ROOT / "roots" / "indicators" / "weighted_index.R"


def _r_ready() -> bool:
    if shutil.which("Rscript") is None:
        return False
    return subprocess.run(
        ["Rscript", "-e", "quit(status = as.integer(!requireNamespace('rewildr', quietly = TRUE)))"],
        capture_output=True).returncode == 0


pytestmark = pytest.mark.skipif(not _r_ready(), reason="Rscript with rewildr not available")

IDS = ["ind_a", "ind_b", "ind_c", "ind_d"]
WEIGHTS = {"id": "test_weights", "is_publishers_weighting": False, "declared_in": "test",
           "declaration_sha256": "0" * 64,
           "pillars": {"p1": {"name": "Pillar one", "chips": 30, "components": {"ind_a": 10, "ind_b": 30}},
                       "p2": {"name": "Pillar two", "chips": 20, "components": {"ind_c": 20, "ind_d": 20}}}}


GEOID = "us_census_geoid"


def _fixture():
    rng = random.Random(7)
    units = [f"23{n:03d}" for n in range(1, 61, 2)] + [f"33{n:03d}" for n in range(1, 21, 2)]
    rows, locs = [], {}
    for k, u in enumerate(units):
        locs[u] = (42 + rng.random() * 5, -72 + rng.random() * 5)
        gaps = {5: ["ind_c"], 11: ["ind_a"], 17: ["ind_b", "ind_d"], 23: ["ind_d"]}.get(k, [])
        for i in IDS:
            z = None if i in gaps else round(rng.gauss(0, 1), 6)
            rows.append({"measurement_id": f"{i}:{GEOID}:{u}", "unit_authority": GEOID,
                         "unit_code": u, "name": u, "indicator": i,
                         "z": z, "outside_reason": None if z is not None else "no value"})
    return rows, locs


def _respond(script, inputs, params, out, tmp):
    ij, pj = tmp / f"{out.stem}_in.json", tmp / f"{out.stem}_params.json"
    ij.write_text(json.dumps(inputs)); pj.write_text(json.dumps(params))
    proc = subprocess.run(["Rscript", str(script), str(ij), str(out), str(pj)],
                          capture_output=True, text=True, cwd=ROOT)
    lines = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
    assert lines, f"no protocol response.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    return json.loads(lines[-1]), proc


def _run(script, inputs, params, out, tmp):
    resp, proc = _respond(script, inputs, params, out, tmp)
    assert resp["status"] == "success", (resp, proc.stderr)
    return resp


def _f(v):
    import pandas as pd
    return None if v is None or pd.isna(v) else float(v)


def test_the_chain_agrees_with_the_oracle(tmp_path):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    rows, locs = _fixture()
    sp = tmp_path / "standings.parquet"
    df = pd.DataFrame(rows); df["z"] = df["z"].astype("Float64"); df.to_parquet(sp, index=False)
    lp = tmp_path / "locations.parquet"
    pd.DataFrame([{"GEOID": u, "latitude": a, "longitude": b} for u, (a, b) in locs.items()]) \
        .astype({"GEOID": "string"}).to_parquet(lp, index=False)
    decls = [{"id": i, "direction": "higher_is_better"} for i in IDS]

    ip_out = tmp_path / "imputed.parquet"
    resp = _run(IMPUTE, {"standings": str(sp), "locations": str(lp)},
                {"indicators": decls, "k": 5, "missing_exactly": 1}, ip_out, tmp_path)
    py_imp, recs = ox.impute(rows, IDS, locs, k=5)
    r_imp = pd.read_parquet(ip_out)
    assert resp["imputation"]["n_imputed"] == sum(1 for r in recs if r["donor"]) == 3
    py_by = {(r["unit_code"], r["indicator"]): r for r in py_imp}
    for _, r in r_imp.iterrows():
        p = py_by[(r["unit_code"], r["indicator"])]
        assert _f(r["z"]) == p["z"], (r["unit_code"], r["indicator"])
        assert bool(r["imputed"]) == p["imputed"]
        assert (None if pd.isna(r["imputed_from"]) else r["imputed_from"]) == p["imputed_from"]

    pil_out = tmp_path / "pillars.parquet"
    _run(INDEX, {"components": str(ip_out)}, {"weights": WEIGHTS, "level": "pillars"}, pil_out, tmp_path)
    py_pil = ox.weighted_index(py_imp, WEIGHTS, "pillars")
    r_pil = pd.read_parquet(pil_out)
    assert set(r_pil["unit_authority"]) == {GEOID}
    assert list(r_pil["measurement_id"]) == [
        f"{i}:{GEOID}:{u}" for i, u in zip(r_pil["index"], r_pil["unit_code"])]
    by = {(r["unit_code"], r["index"]): r for r in py_pil}
    for _, r in r_pil.iterrows():
        p = by[(r["unit_code"], r["index"])]
        assert _f(r["score"]) == p["score"], (r["unit_code"], r["index"])
        assert _f(r["percentile"]) == p["percentile"], (r["unit_code"], r["index"])
        assert int(r["n_imputed_components"]) == p["n_imputed_components"]

    comp_out = tmp_path / "overall.parquet"
    _run(INDEX, {"components": str(pil_out)}, {"weights": WEIGHTS, "level": "composite"}, comp_out, tmp_path)
    py_comp = {r["unit_code"]: r for r in ox.weighted_index(py_pil, WEIGHTS, "composite")}
    r_comp = pd.read_parquet(comp_out)
    assert set(r_comp["unit_authority"]) == {GEOID}
    assert set(r_comp["measurement_id"]) == {f"overall:{GEOID}:{u}" for u in r_comp["unit_code"]}
    for _, r in r_comp.iterrows():
        p = py_comp[r["unit_code"]]
        assert _f(r["percentile"]) == p["percentile"], r["unit_code"]
    missing_two = [u for u in py_comp if py_comp[u]["percentile"] is None]
    assert len(missing_two) == 1, "the unit missing two indicators gets no overall index"


def test_a_numeric_geoid_is_refused(tmp_path):
    pd = pytest.importorskip("pandas")
    rows, locs = _fixture()
    sp = tmp_path / "standings.parquet"
    df = pd.DataFrame(rows); df["z"] = df["z"].astype("Float64"); df.to_parquet(sp, index=False)
    lp = tmp_path / "locations.parquet"
    pd.DataFrame([{"GEOID": int(u), "latitude": a, "longitude": b} for u, (a, b) in locs.items()]).to_parquet(lp, index=False)
    ij, pj, out = tmp_path / "i.json", tmp_path / "p.json", tmp_path / "o.parquet"
    ij.write_text(json.dumps({"standings": str(sp), "locations": str(lp)}))
    pj.write_text(json.dumps({"indicators": [{"id": i} for i in IDS]}))
    proc = subprocess.run(["Rscript", str(IMPUTE), str(ij), str(out), str(pj)],
                          capture_output=True, text=True, cwd=ROOT)
    resp = json.loads([l for l in proc.stdout.splitlines() if l.startswith("{")][-1])
    assert resp["status"] == "failure"
    assert "GEOID arrived as a number" in resp["message"]


def _standings(tmp_path, rows):
    pd = pytest.importorskip("pandas")
    sp = tmp_path / "standings.parquet"
    df = pd.DataFrame(rows); df["z"] = df["z"].astype("Float64"); df.to_parquet(sp, index=False)
    return sp


def test_standings_without_a_unit_authority_are_refused(tmp_path):
    rows, _ = _fixture()
    sp = _standings(tmp_path, [{k: v for k, v in r.items() if k != "unit_authority"} for r in rows])
    resp, _ = _respond(INDEX, {"components": str(sp)}, {"weights": WEIGHTS, "level": "pillars"},
                       tmp_path / "pillars.parquet", tmp_path)
    assert resp["status"] == "failure"
    assert "unit_authority" in json.dumps(resp)


def test_an_index_across_authorities_is_refused_by_name(tmp_path):
    rows, _ = _fixture()
    for r in rows:
        if r["unit_code"].startswith("33"):
            r["unit_authority"] = "us_census_sldl"
    sp = _standings(tmp_path, rows)
    resp, _ = _respond(INDEX, {"components": str(sp)}, {"weights": WEIGHTS, "level": "pillars"},
                       tmp_path / "pillars.parquet", tmp_path)
    said = json.dumps(resp)
    assert resp["status"] == "failure"
    assert "us_census_geoid" in said and "us_census_sldl" in said and "D-190" in said
