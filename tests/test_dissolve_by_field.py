"""
tests/test_dissolve_by_field.py

GEO-1: dissolve_by_field gave every unit the whole layer's geometry. Sixteen
Maine counties, each the whole state, under the right names, with no warning.
Nothing checked that sixteen features were sixteen different places, only that
there were sixteen. These do. Runs the real R primitive; skipped without R.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DISSOLVE = ROOT / "soil" / "transform" / "dissolve_by_field.R"


def _r_ready() -> bool:
    if shutil.which("Rscript") is None:
        return False
    return subprocess.run(
        ["Rscript", "-e", "quit(status = as.integer(!(requireNamespace('rewildr', quietly = TRUE) && requireNamespace('sf', quietly = TRUE))))"],
        capture_output=True).returncode == 0


pytestmark = pytest.mark.skipif(not _r_ready(), reason="Rscript with rewildr and sf not available")


def square(x0, y0, size, county):
    x1, y1 = x0 + size, y0 + size
    return {"type": "Feature", "properties": {"COUNTY": county, "CODE": county[:2]},
            "geometry": {"type": "Polygon",
                         "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}}


def run(tmp_path, features, params):
    src = tmp_path / "in.geojson"
    src.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    inputs, pfile, out = tmp_path / "i.json", tmp_path / "p.json", tmp_path / "out.geojson"
    inputs.write_text(json.dumps({"features": str(src)}))
    pfile.write_text(json.dumps(params))
    proc = subprocess.run(["Rscript", str(DISSOLVE), str(inputs), str(out), str(pfile)],
                          capture_output=True, text=True, cwd=ROOT)
    lines = [l for l in proc.stdout.splitlines() if l.startswith("{")]
    assert lines, f"no protocol response.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    return json.loads(lines[-1]), out


def bbox(geom):
    pts = []
    def walk(c):
        if isinstance(c[0], (int, float)):
            pts.append(c)
        else:
            for x in c:
                walk(x)
    walk(geom["coordinates"])
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def test_each_unit_keeps_its_own_shape(tmp_path):
    feats = [square(0, 0, 1, "Alpha"), square(1, 0, 1, "Alpha"),   # Alpha: x 0..2
             square(5, 5, 1, "Beta"), square(5, 6, 1, "Beta")]     # Beta:  y 5..7
    resp, out = run(tmp_path, feats, {"field": "COUNTY", "keep_fields": ["CODE"]})
    assert resp["status"] == "success", resp
    got = {f["properties"]["COUNTY"]: f for f in json.loads(out.read_text())["features"]}
    assert set(got) == {"Alpha", "Beta"}
    assert bbox(got["Alpha"]["geometry"]) == (0, 0, 2, 1)
    assert bbox(got["Beta"]["geometry"]) == (5, 5, 6, 7)
    assert got["Alpha"]["properties"]["CODE"] == "Al"


def test_two_units_with_one_shape_are_refused(tmp_path):
    feats = [square(0, 0, 1, "Alpha"), square(0, 0, 1, "Beta")]
    resp, _ = run(tmp_path, feats, {"field": "COUNTY"})
    assert resp["status"] == "failure"
    assert "share one geometry" in resp.get("message", "") or "identical" in resp.get("message", "")
