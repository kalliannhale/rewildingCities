"""
tests/test_geography_graph.py

Sprint 04, Part 2: the block spine and the edges built from it (Contract 3,
D-121, D-122). A tiny synthetic state: two counties, three towns, one town
split across two House districts, one township with no households, one block
on a reservation, and national equivalency zips that list another state first.
Runs without pyarrow or shapely: the primitives read and write csv here.
"""

import importlib.util
import zipfile
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "soil" / "transform" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


spine_mod, edges_mod = load("build_block_spine"), load("build_place_edges")


class W:
    def __init__(self): self.said = []
    def info(self, m): self.said.append(("info", m))
    def warn(self, m): self.said.append(("warning", m))
    def critical(self, m): self.said.append(("critical", m))


#        block            county  town   House Senate tribal  persons hu  hh
BLOCKS = [
    ("230010001001000", "001", "10000", "001", "001", "",     "R", 30, 12, 10),
    ("230010001001001", "001", "10000", "002", "001", "",     "",  10,  5,  5),
    ("230010001001002", "001", "20000", "002", "001", "2950", "R", 20,  8,  8),
    ("230150002001000", "015", "30000", "003", "002", "",     "",   0,  4,  0),
]


def fixture(tmp):
    counts = pd.DataFrame({"GEOID": [b[0] for b in BLOCKS],
                           "P1_001N": [b[7] for b in BLOCKS],
                           "H1_001N": [b[8] for b in BLOCKS],
                           "H1_002N": [b[9] for b in BLOCKS]})
    counts.to_csv(tmp / "counts.csv", index=False)
    with zipfile.ZipFile(tmp / "baf.zip", "w") as z:
        z.writestr("BlockAssign_ST23_ME_MCD.txt", "BLOCKID|COUNTYFP|COUSUBFP\n" +
                   "\n".join(f"{b[0]}|{b[1]}|{b[2]}" for b in BLOCKS))
        z.writestr("BlockAssign_ST23_ME_AIANNH.txt", "BLOCKID|AIANNHCE|COMPTYP\n" +
                   "\n".join(f"{b[0]}|{b[5]}|{b[6] if b[5] else ''}" for b in BLOCKS))
        # the 2020 SLDL: wrong lines on purpose, and never read
        z.writestr("BlockAssign_ST23_ME_SLDL.txt", "BLOCKID|DISTRICT\n" +
                   "\n".join(f"{b[0]}|099" for b in BLOCKS))
    for chamber, col, idx in (("sldl", "SLDLST", 3), ("sldu", "SLDUST", 4)):
        with zipfile.ZipFile(tmp / f"bef_{chamber}.zip", "w") as z:
            z.writestr(f"13_GA_{chamber.upper()}24.txt", f"GEOID,{col}\n130019501001000,157")
            z.writestr(f"National_{chamber.upper()}24.txt", f"GEOID,{col}\n130019501001000,157\n" +
                       "\n".join(f"{b[0]},{b[idx]}" for b in BLOCKS))
    return tmp


def spine(tmp):
    fixture(tmp)
    return spine_mod.build(spine_mod.read_table(tmp / "counts.csv"), tmp / "baf.zip",
                           tmp / "bef_sldl.zip", tmp / "bef_sldu.zip", "23", W())


VINTAGES = {"town": "2020", "sldl": "2024", "sldu": "2024", "aiannh": "2020", "division": "2024"}


# ── the spine ─────────────────────────────────────────────────────────────
def test_the_spine_takes_districts_from_2024_never_from_2020(tmp_path):
    s = spine(tmp_path)
    assert list(s["sldl"]) == ["23001", "23002", "23002", "23003"]
    assert "23099" not in set(s["sldl"])
    assert list(s["cousub"]) == ["2300110000", "2300110000", "2300120000", "2301530000"]
    assert s.loc[2, "aiannh"] == "2950" and pd.isna(s.loc[0, "aiannh"])


def test_a_block_without_an_assignment_is_refused(tmp_path):
    fixture(tmp_path)
    extra = pd.read_csv(tmp_path / "counts.csv", dtype=str)
    extra.loc[len(extra)] = ["230159999999999", "5", "2", "2"]
    extra.to_csv(tmp_path / "counts.csv", index=False)
    with pytest.raises(SystemExit):
        spine_mod.build(spine_mod.read_table(tmp_path / "counts.csv"), tmp_path / "baf.zip",
                        tmp_path / "bef_sldl.zip", tmp_path / "bef_sldu.zip", "23", W())


# ── the edges ─────────────────────────────────────────────────────────────
def edges(tmp, divisions=None):
    return edges_mod.build(spine(tmp), divisions, "23", VINTAGES, "megis", W())


def test_every_town_has_exactly_one_contains_edge_from_its_county(tmp_path):
    e = edges(tmp_path)
    c = e[(e["kind"] == "contains") & (e["from_code"].str.len() == 5)]
    assert c.groupby("to_code").size().to_dict() == {
        "2300110000": 1, "2300120000": 1, "2301530000": 1}
    assert dict(zip(c["to_code"], c["from_code"]))["2301530000"] == "23015"


def test_a_split_town_carries_both_shares_into_each_district(tmp_path):
    e = edges(tmp_path)
    h = e[(e["from_code"] == "2300110000") & (e["to_authority"] == "us_census_sldl")]
    by = dict(zip(h["to_code"], zip(h["weight_population"], h["weight_households"])))
    assert by["23001"] == (30 / 40, 10 / 15)      # population and households differ
    assert by["23002"] == (10 / 40, 5 / 15)


def test_a_towns_shares_across_a_chamber_sum_to_1_for_each_basis(tmp_path):
    e = edges(tmp_path)
    for chamber in ("us_census_sldl", "us_census_sldu"):
        fam = e[(e["from_authority"] == "us_census_geoid") & (e["to_authority"] == chamber)]
        for basis in ("weight_population", "weight_households"):
            sums = fam.dropna(subset=[basis]).groupby("from_code")[basis].sum()
            assert ((sums - 1).abs() < 1e-12).all(), (chamber, basis)


def test_a_township_with_no_households_has_null_shares_with_a_reason(tmp_path):
    e = edges(tmp_path)
    t = e[(e["from_code"] == "2301530000") & (e["kind"] == "overlaps")].iloc[0]
    assert pd.isna(t["weight_population"]) and pd.isna(t["weight_households"])
    assert t["weight_reason"] == "zero_population, zero_households"


def test_a_tribal_area_is_an_overlap_by_blocks_never_by_name(tmp_path):
    e = edges(tmp_path)
    t = e[e["to_authority"] == "us_census_aiannh"]
    assert list(zip(t["from_code"], t["to_code"], t["weight_population"])) == [
        ("2300120000", "2950R", 1.0)]


def test_a_reservation_and_its_trust_land_are_two_places(tmp_path):
    # D-125, TRIBE-1: one AIANNH code, two Census legal areas
    s = spine(tmp_path)
    s.loc[1, ["aiannh", "aiannh_comptyp"]] = ["2950", "T"]
    e = edges_mod.build(s, None, "23", VINTAGES, "megis", W())
    t = e[e["to_authority"] == "us_census_aiannh"]
    assert sorted(zip(t["from_code"], t["to_code"], t["weight_population"])) == [
        ("2300110000", "2950T", 10 / 40), ("2300120000", "2950R", 1.0)]


def test_a_tribal_block_without_its_component_is_refused(tmp_path):
    s = spine(tmp_path)
    s.loc[2, "aiannh_comptyp"] = None
    with pytest.raises(SystemExit):
        edges_mod.build(s, None, "23", VINTAGES, "megis", W())


def test_civil_divisions_join_towns_through_blocks(tmp_path):
    divisions = pd.DataFrame({"GEOID": [b[0] for b in BLOCKS],
                              "division": ["A", "A", "B", None]})
    e = edges(tmp_path, divisions)
    d = e[e["from_authority"] == "megis"]
    assert sorted(zip(d["from_code"], d["to_code"], d["weight_population"])) == [
        ("A", "2300110000", 1.0), ("B", "2300120000", 1.0)]


def test_every_edge_carries_its_source_and_vintage(tmp_path):
    e = edges(tmp_path)
    assert e["source"].notna().all() and e["vintage"].notna().all()
    assert set(e.loc[e["to_authority"] == "us_census_sldl", "vintage"]) == {"2024"}


def test_one_geoid_naming_three_places_stays_three_places(tmp_path):
    # GRAPH-1: 23001 is Androscoggin County, House District 1 and Senate
    # District 1. a Census GEOID is unique only within its level, so the
    # authority carries the level and (authority, code) names one place.
    e = edges(tmp_path)
    ones = e[e["to_code"] == "23001"]
    assert set(ones["to_authority"]) == {"us_census_geoid", "us_census_sldl", "us_census_sldu"}
    assert set(ones.loc[ones["to_authority"] == "us_census_geoid", "kind"]) == {"contains"}


# ── D-122: blocks into civil divisions by internal point ─────────────────
def test_blocks_are_assigned_by_internal_point_and_unplaced_ones_are_counted():
    pytest.importorskip("shapely")
    mod = load("assign_blocks_to_polygons")
    square = lambda x0, y0: {"type": "Polygon", "coordinates": [[[x0, y0], [x0 + 1, y0],
                             [x0 + 1, y0 + 1], [x0, y0 + 1], [x0, y0]]]}
    polygons = [{"properties": {"GEOCODE": "A"}, "geometry": square(0, 0)},
                {"properties": {"GEOCODE": "B"}, "geometry": square(1, 0)}]
    points = [{"properties": {"GEOID": g, "INTPTLAT": f"+{lat}", "INTPTLON": f"{lon}"},
               "geometry": None}
              for g, lon, lat in (("1", 0.5, 0.5), ("2", 1.5, 0.5), ("3", 5.0, 5.0))]
    w = W()
    out = mod.assign(points, polygons, "GEOCODE", "division", w)
    assert list(out["division"][:2]) == ["A", "B"] and pd.isna(out["division"][2])
    assert any("1 block point(s) fall in no unit" in m for _, m in w.said)


# ── D-126: 2024 towns from topological faces (TOWN-1) ────────────────────
def dbf(rows, fields):
    """a dBase III table with the fields a faces file carries: enough to test
    the reader against a layout the Census documents (Appendix R)."""
    import struct
    hdr_len = 32 + 32 * len(fields) + 1
    rec_len = 1 + sum(n for _, n, _ in fields)
    out = bytearray(32)
    out[4:8] = struct.pack("<I", len(rows))
    out[8:10] = struct.pack("<H", hdr_len)
    out[10:12] = struct.pack("<H", rec_len)
    for name, n, t in fields:
        d = bytearray(32)
        d[:len(name)] = name.encode()
        d[11] = ord(t)
        d[16] = n
        out += d
    out += b"\x0d"
    for r in rows:
        out += b" " + b"".join(
            (f"{v:>{n}}" if t == "N" else f"{v:<{n}}").encode()
            for v, (_, n, t) in zip(r, fields))
    return bytes(out)


FACE_SPEC = [("STATEFP20", 2, "C"), ("COUNTYFP20", 3, "C"), ("TRACTCE20", 6, "C"),
             ("BLOCKCE20", 4, "C"), ("STATEFP", 2, "C"), ("COUNTYFP", 3, "C"),
             ("COUSUBFP", 5, "C"), ("SLDLST", 3, "C"), ("SLDUST", 3, "C"),
             ("LWFLAG", 1, "C"), ("ATOTAL", 14, "N")]


def face(block, town, sldl, sldu, area, lw="L"):
    # the block's own county, and the town as a five-digit COUSUBFP within it
    return [block[:2], block[2:5], block[5:11], block[11:], "23", block[2:5], town,
            sldl, sldu, lw, str(area)]


def test_a_faces_table_reads_back_its_fields(tmp_path):
    import importlib.util as _u
    spec = _u.spec_from_file_location("bs", REPO / "soil" / "transform" / "build_block_spine.py")
    bs = _u.module_from_spec(spec); spec.loader.exec_module(bs)
    rows = [face(BLOCKS[0][0], "10000", "001", "001", 600),
            face(BLOCKS[0][0], "10001", "001", "001", 400)]
    with zipfile.ZipFile(tmp_path / "faces.zip", "w") as z:
        z.writestr("tl_2024_23001_faces.dbf", dbf(rows, FACE_SPEC))
    f = bs.read_faces(tmp_path / "faces.zip", W())
    assert list(f.columns) == bs.FACE_FIELDS and len(f) == 2
    assert list(f["COUSUBFP"]) == ["10000", "10001"] and list(f["ATOTAL"]) == ["600", "400"]


def test_a_block_split_by_a_2024_boundary_goes_whole_to_its_larger_piece(tmp_path):
    fixture(tmp_path)
    import importlib.util as _u
    spec = _u.spec_from_file_location("bs", REPO / "soil" / "transform" / "build_block_spine.py")
    bs = _u.module_from_spec(spec); spec.loader.exec_module(bs)
    faces = pd.DataFrame([
        face(BLOCKS[0][0], "10000", "001", "001", 600),
        face(BLOCKS[0][0], "10001", "001", "001", 400),
        face(BLOCKS[1][0], "10001", "001", "001", 100),
        face(BLOCKS[2][0], "20000", "001", "001", 100),
        face(BLOCKS[3][0], "30000", "002", "001", 100)],
        columns=bs.FACE_FIELDS)
    s = bs.build(bs.read_table(tmp_path / "counts.csv"), tmp_path / "baf.zip",
                 tmp_path / "bef_sldl.zip", tmp_path / "bef_sldu.zip", "23", W(), faces=faces)
    assert s.loc[0, "cousub"] == "2300110000" and bool(s.loc[0, "cousub_split"])
    assert s.loc[1, "cousub"] == "2300110001" and s.loc[1, "cousub_2020"] == "2300110000"
    assert not bool(s.loc[2, "cousub_split"])


def test_a_counted_block_with_no_2024_face_is_refused(tmp_path):
    fixture(tmp_path)
    import importlib.util as _u
    spec = _u.spec_from_file_location("bs", REPO / "soil" / "transform" / "build_block_spine.py")
    bs = _u.module_from_spec(spec); spec.loader.exec_module(bs)
    faces = pd.DataFrame([face(BLOCKS[0][0], "10000", "001", "001", 1)], columns=bs.FACE_FIELDS)
    with pytest.raises(SystemExit):
        bs.build(bs.read_table(tmp_path / "counts.csv"), tmp_path / "baf.zip",
                 tmp_path / "bef_sldl.zip", tmp_path / "bef_sldu.zip", "23", W(), faces=faces)


# ── D-127: a block's county follows its 2024 town (BOUND-1) ──────────────
def test_a_block_whose_2024_town_is_in_another_county_follows_the_town(tmp_path):
    fixture(tmp_path)
    import importlib.util as _u
    spec = _u.spec_from_file_location("bs", REPO / "soil" / "transform" / "build_block_spine.py")
    bs = _u.module_from_spec(spec); spec.loader.exec_module(bs)
    faces = pd.DataFrame([
        face(BLOCKS[0][0], "10000", "001", "001", 600),
        face(BLOCKS[1][0], "10001", "001", "001", 100),
        face(BLOCKS[2][0], "20000", "001", "001", 100),
        face(BLOCKS[3][0], "30000", "002", "001", 100)], columns=bs.FACE_FIELDS)
    # block 0 was in county 001 in 2020; in 2024 its land lies in county 015's town 30000
    faces.loc[0] = ["23", "001", "000100", "1000", "23", "015", "30000", "002", "001", "L", "600"]
    s = bs.build(bs.read_table(tmp_path / "counts.csv"), tmp_path / "baf.zip",
                 tmp_path / "bef_sldl.zip", tmp_path / "bef_sldu.zip", "23", W(), faces=faces)
    assert s.loc[0, "county"] == "23015" and s.loc[0, "county_2020"] == "23001"
    assert s.loc[0, "cousub"] == "2301530000"
    assert s.loc[1, "county"] == s.loc[1, "county_2020"] == "23001"


def test_a_block_whose_faces_are_all_perennial_water_has_no_land_and_takes_the_largest_piece(tmp_path):
    import importlib.util as _u
    spec = _u.spec_from_file_location("bs", REPO / "soil" / "transform" / "build_block_spine.py")
    bs = _u.module_from_spec(spec); spec.loader.exec_module(bs)
    faces = pd.DataFrame([
        face(BLOCKS[0][0], "10000", "001", "001", 300, lw="P"),
        face(BLOCKS[0][0], "10001", "001", "001", 900, lw="P")], columns=bs.FACE_FIELDS)
    by = bs.faces_by_block(faces, "23", W())
    assert by.loc[by["GEOID"] == BLOCKS[0][0], "cousub_2024"].iloc[0] == "2300110001"


def test_intermittent_water_counts_as_land_as_the_census_does(tmp_path):
    import importlib.util as _u
    spec = _u.spec_from_file_location("bs", REPO / "soil" / "transform" / "build_block_spine.py")
    bs = _u.module_from_spec(spec); spec.loader.exec_module(bs)
    faces = pd.DataFrame([
        face(BLOCKS[0][0], "10000", "001", "001", 500, lw="I"),
        face(BLOCKS[0][0], "10001", "001", "001", 400, lw="L")], columns=bs.FACE_FIELDS)
    by = bs.faces_by_block(faces, "23", W())
    assert by.loc[by["GEOID"] == BLOCKS[0][0], "cousub_2024"].iloc[0] == "2300110000"
