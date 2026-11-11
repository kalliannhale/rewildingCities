"""
tests/test_place_outlines.py

Sprint 04 step 5b (D-144 to D-148): display outlines from the 2024 faces.
The declaration tests run everywhere. The primitive tests run the real R
primitive on a three-face Maine of our own making, and are skipped without R.
"""

import ast
import json
import re
import shutil
import subprocess
import zipfile
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUTLINES = ROOT / "soil" / "transform" / "build_place_outlines.R"
SPINE_PY = ROOT / "soil" / "transform" / "build_block_spine.py"
OUTLINE_TYPES = {"place_outline", "census_tribal_outline"}
NOTE = "census_tribal_area"
TABLE_NOTE = "census_tribal_places"


# ── declarations ─────────────────────────────────────────────────────────
def test_land_flags_match_the_spine():
    """the land rule has two homes, Python and R; they must say the same (D-144)"""
    tree = ast.parse(SPINE_PY.read_text())
    py = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              and any(getattr(t, "id", None) == "LAND_FLAGS" for t in n.targets))
    m = re.search(r"LAND_FLAGS <- c\(([^)]*)\)", OUTLINES.read_text())
    assert m, "build_place_outlines.R declares no LAND_FLAGS"
    assert tuple(re.findall(r'"(\w)"', m.group(1))) == tuple(py)


def _input_types(path):
    doc = yaml.safe_load(path.read_text()) or {}
    for name, entry in (doc.get("primitives") or {}).items():
        for inp in (entry or {}).get("inputs") or []:
            if isinstance(inp, dict):
                for t in inp.get("semantic_types") or []:
                    yield name, t


def test_no_primitive_takes_an_outline():
    """outlines are for publication, never an input to analysis (D-142, D-146)"""
    soil = list(_input_types(ROOT / "soil" / "_registry.yml"))
    assert soil, "read no input types from soil/_registry.yml"
    found = [(n, t) for n, t in soil + list(_input_types(ROOT / "roots" / "_registry.yml"))
             if t in OUTLINE_TYPES]
    assert not found, f"these primitives take an outline type: {found}"


def _types():
    return yaml.safe_load((ROOT / "seeds" / "schemas" / "semantic_types.yml").read_text())["types"]


def test_every_required_note_has_one_text():
    """a note's text lives in one place; a type may require it by id alone (D-146)"""
    texts, required = Counter(), set()
    for t in _types().values():
        for note in (t or {}).get("required_context") or []:
            required.add(note["id"])
            if note.get("text"):
                texts[note["id"]] += 1
    bad = {i: texts[i] for i in required if texts[i] != 1}
    assert not bad, f"notes required without exactly one text: {bad}"


def test_outline_types_are_declared():
    types = _types()
    assert types["place_outline"]["resolution_tier"] == "public"
    assert not types["place_outline"].get("required_context")
    assert types["census_tribal_outline"]["resolution_tier"] == "public"
    assert [n["id"] for n in types["census_tribal_outline"]["required_context"]] == [NOTE]


def test_the_places_table_has_its_own_note():
    """one id, one note: places describes a table, census_tribal_area a boundary (D-149)"""
    types = _types()
    assert [n["id"] for n in types["places"]["required_context"]] == [TABLE_NOTE]
    assert [n["id"] for n in types["census_tribal_area"]["required_context"]] == [NOTE]


def test_one_outline_step_per_level():
    prep = yaml.safe_load((ROOT / "plots" / "maine" / "preparations"
                           / "maine_geography_graph.yml").read_text())
    steps = [s for s in prep["steps"] if s["id"].startswith("outline_")]
    assert sorted(s["params"]["level"] for s in steps) == sorted(
        ["state", "county", "cousub", "sldl", "sldu", "aiannh"])
    for s in steps:
        tribal = s["params"]["level"] == "aiannh"
        assert s["primitive"] == ("soil/build_tribal_outlines" if tribal
                                  else "soil/build_place_outlines")
        assert list(s["outputs"].values()) == [
            "census_tribal_outline" if tribal else "place_outline"]


# ── the primitive ────────────────────────────────────────────────────────
def _r_ready() -> bool:
    if shutil.which("Rscript") is None:
        return False
    return subprocess.run(
        ["Rscript", "-e", "quit(status = as.integer(!(requireNamespace('rewildr', quietly = TRUE) && requireNamespace('sf', quietly = TRUE))))"],
        capture_output=True).returncode == 0


needs_r = pytest.mark.skipif(not _r_ready(), reason="Rscript with rewildr and sf not available")

# town 00100 is a land square and a water square in block 1001; town 00200,
# block 1002, is land and lies in tribal area 1950R
FIXTURE_R = r'''
library(sf)
a <- commandArgs(trailingOnly = TRUE)
sq <- function(x0, y0, s = 0.01) st_polygon(list(rbind(c(x0, y0), c(x0 + s, y0),
  c(x0 + s, y0 + s), c(x0, y0 + s), c(x0, y0))))
x0 <- -69; y0 <- 45
faces <- st_sf(
  STATEFP20 = "23", COUNTYFP20 = "001", TRACTCE20 = "000100",
  BLOCKCE20 = c("1001", "1001", "1002"),
  STATEFP = "23", COUNTYFP = "001", COUSUBFP = c("00100", "00100", "00200"),
  SLDLST = c("001", "001", "002"), SLDUST = "001",
  LWFLAG = c("L", "P", "L"), ATOTAL = c(1000, 1000, 1000),
  geometry = st_sfc(sq(x0, y0), sq(x0 + 0.01, y0), sq(x0, y0 + 0.01), crs = 4269))
st_write(faces, file.path(a[1], "tl_2024_23001_faces.shp"), quiet = TRUE)
st_write(st_sf(GEOID = "1950R", NAME = "Test Reservation",
               geometry = st_sfc(sq(x0, y0 + 0.01), crs = 4269)), a[2], quiet = TRUE)
st_write(st_sf(GEOID = "5550T", NAME = "Elsewhere Trust Land",
               geometry = st_sfc(sq(x0 + 1, y0 + 1), crs = 4269)), a[3], quiet = TRUE)
'''

PLACES = [
    ("us_census_geoid", "23", "state", "Maine", ""),
    ("us_census_geoid", "23001", "county", "Androscoggin County", ""),
    ("us_census_geoid", "2300100100", "cousub", "Alpha town", ""),
    ("us_census_geoid", "2300100200", "cousub", "Beta Reservation", NOTE),
    ("us_census_sldl", "23001", "sldl", "State House District 1", ""),
    ("us_census_sldl", "23002", "sldl", "State House District 2", ""),
    ("us_census_sldu", "23001", "sldu", "State Senate District 1", ""),
    ("us_census_aiannh", "1950R", "aiannh", "Test Reservation", NOTE),
]


@pytest.fixture
def maine(tmp_path):
    shp = tmp_path / "shp"
    shp.mkdir()
    script = tmp_path / "fixture.R"
    script.write_text(FIXTURE_R)
    res, trust = tmp_path / "reservations.geojson", tmp_path / "trust.geojson"
    proc = subprocess.run(["Rscript", str(script), str(shp), str(res), str(trust)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    inner = tmp_path / "tl_2024_23001_faces.zip"
    with zipfile.ZipFile(inner, "w") as z:
        for f in shp.iterdir():
            z.write(f, f.name)
    outer = tmp_path / "maine_faces_2024.zip"
    with zipfile.ZipFile(outer, "w") as z:
        z.write(inner, inner.name)
    spine = tmp_path / "spine.csv"
    spine.write_text("GEOID,aiannh,aiannh_comptyp\n"
                     "230010001001001,,\n230010001001002,1950,R\n")
    return {"dir": tmp_path, "faces": outer, "spine": spine,
            "reservations": res, "trust_lands": trust}


def write_places(m, rows):
    p = m["dir"] / "places.csv"
    p.write_text("authority,code,level,name,context_note\n"
                 + "".join(",".join(r) + "\n" for r in rows))
    return p


def run(m, inputs, params):
    d = m["dir"]
    i, p, out = d / "i.json", d / "p.json", d / "out.geojson"
    i.write_text(json.dumps({k: str(v) for k, v in inputs.items()}))
    p.write_text(json.dumps(params))
    proc = subprocess.run(["Rscript", str(OUTLINES), str(i), str(out), str(p)],
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


@needs_r
def test_towns_are_land_only_and_carry_their_notes(maine):
    places = write_places(maine, PLACES)
    resp, out = run(maine, {"faces": maine["faces"], "places": places},
                    {"level": "cousub", "state_fips": "23"})
    assert resp["status"] == "success", resp
    got = {f["properties"]["code"]: f for f in json.loads(out.read_text())["features"]}
    assert set(got) == {"2300100100", "2300100200"}
    alpha, beta = got["2300100100"], got["2300100200"]
    assert alpha["properties"]["water_clipped"] is True
    assert beta["properties"]["water_clipped"] is False
    assert pytest.approx(bbox(alpha["geometry"])) == (-69, 45, -68.99, 45.01)
    assert alpha["properties"]["context_note"] is None
    assert beta["properties"]["context_note"] == NOTE
    assert resp["context_notes"] == [NOTE, TABLE_NOTE]
    assert [(r["step"], r["count"]) for r in resp["publication"]] == [("clipped", 1)]
    assert not any(k in r for r in resp["publication"] for k in ("by", "at"))
    assert resp["size_bytes"] > 0 and resp["vertex_count"] > 0


@needs_r
def test_district_keys_are_derived(maine):
    places = write_places(maine, PLACES)
    resp, out = run(maine, {"faces": maine["faces"], "places": places},
                    {"level": "sldl", "state_fips": "23"})
    assert resp["status"] == "success", resp
    codes = {f["properties"]["code"] for f in json.loads(out.read_text())["features"]}
    assert codes == {"23001", "23002"}


@needs_r
def test_a_place_with_no_land_faces_is_refused_by_name(maine):
    places = write_places(maine, PLACES + [
        ("us_census_geoid", "2300100300", "cousub", "Gamma plantation", "")])
    resp, _ = run(maine, {"faces": maine["faces"], "places": places},
                  {"level": "cousub", "state_fips": "23"})
    assert resp["status"] == "failure"
    assert "no land face" in resp["message"] and "Gamma plantation" in resp["message"]


@needs_r
def test_an_outline_without_a_place_is_refused(maine):
    places = write_places(maine, [r for r in PLACES if r[1] != "2300100200"])
    resp, _ = run(maine, {"faces": maine["faces"], "places": places},
                  {"level": "cousub", "state_fips": "23"})
    assert resp["status"] == "failure"
    assert "not in places" in resp["message"] and "2300100200" in resp["message"]


@needs_r
def test_tribal_outlines_nest_and_are_compared(maine):
    places = write_places(maine, PLACES)
    resp, out = run(maine, {k: maine[k] for k in ("faces", "spine", "reservations", "trust_lands")}
                    | {"places": places},
                    {"level": "aiannh", "state_fips": "23", "tribe_tolerance_m2": 0})
    assert resp["status"] == "success", resp
    feats = json.loads(out.read_text())["features"]
    assert [(f["properties"]["code"], f["properties"]["context_note"]) for f in feats] == [
        ("1950R", NOTE)]
    msgs = [x["message"] for x in resp["warnings"]]
    assert any(m.startswith("TRIBE-5 1950R") for m in msgs)
    assert not any("more than water" in x["message"] for x in resp["warnings"]
                   if x["level"] == "warning")
    assert "publication" not in resp
