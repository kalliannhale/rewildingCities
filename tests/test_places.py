"""
tests/test_places.py

Sprint 04, step 2: the places table (Contract 3, D-128 to D-130). A tiny
synthetic state: a town split by a district and partly in trust land, a city
(FUNCSTAT F, as Maine's 23 are), and one reservation in two Census
subdivisions in two counties, the shape of Penobscot Indian Island (PEN-1).
Step 6 (D-156, D-158): which places carry which note, and what the table tells
the gate. Runs without pyarrow or shapely: everything is built in memory.
"""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "soil" / "transform" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


places_mod, edges_mod = load("build_places"), load("build_place_edges")


class W:
    def __init__(self): self.said = []
    def info(self, m): self.said.append(("info", m))
    def warn(self, m): self.said.append(("warning", m))
    def critical(self, m): self.said.append(("critical", m))


COLS = ["GEOID", "county", "county_2020", "cousub", "cousub_2020", "cousub_split", "sldl",
        "sldu", "aiannh", "aiannh_comptyp", "persons", "housing_units", "households"]
#        block              county   town          House    Senate   tribal  comp  p   hu  hh
BLOCKS = [("230010001001000", "23001", "2300110000", "23001", "23001", None,   None, 30, 12, 10),
          ("230010001001001", "23001", "2300110000", "23002", "23001", "2950", "T",  10,  5,  5),
          ("230010001001002", "23001", "2300120000", "23002", "23001", None,   None, 20,  8,  8),
          ("230150002001000", "23015", "2301530000", "23002", "23001", "2950", "R",   0,  0,  0),
          ("230190003001000", "23019", "2301930000", "23002", "23001", "2950", "R",   5,  2,  2)]
DIVISION = {"230010001001000": "A", "230010001001001": "A", "230010001001002": "B"}
VINTAGES = {"state": "2024", "county": "2024", "town": "2024", "sldl": "2024", "sldu": "2024",
            "aiannh": "2020", "division": "MEGIS METWP24P"}


def spine():
    return pd.DataFrame([(b[0], b[1], b[1], b[2], b[2], False, b[3], b[4], b[5], b[6],
                          b[7], b[8], b[9]) for b in BLOCKS], columns=COLS)


def subdivisions(**change):
    rows = {"2300110000": ("Androscoggin town", "43", "A"),
            "2300120000": ("Lewiston city", "25", "F"),
            "2301530000": ("Riverbend Reservation", "86", "F"),
            "2301930000": ("Riverbend Reservation", "86", "F")}
    rows.update(change)
    return pd.DataFrame([(g, n, l, f) for g, (n, l, f) in rows.items()],
                        columns=["GEOID", "NAMELSAD", "LSAD", "FUNCSTAT"])


def inputs(sp=None, sub=None):
    sp = spine() if sp is None else sp
    blocks = pd.DataFrame({"GEOID": sp["GEOID"], "division": sp["GEOID"].map(DIVISION)})
    edges = edges_mod.build(sp, blocks, "23", {"town": "2024", "sldl": "2024", "sldu": "2024",
                                               "aiannh": "2020", "division": "M"}, "megis", W())
    return dict(
        spine=sp, edges=edges, subdivisions=subdivisions() if sub is None else sub,
        counties=pd.DataFrame({"GEOID": ["23001", "23015", "23019"],
                               "NAME": ["Androscoggin County, Maine", "Oxford County, Maine",
                                        "Penobscot County, Maine"]}),
        house=pd.DataFrame({"GEOID": ["23001", "23002"],
                            "NAME": ["State House District 1", "State House District 2"]}),
        senate=pd.DataFrame({"GEOID": ["23001"], "NAME": ["State Senate District 1"]}),
        reservations=pd.DataFrame({"GEOID": ["2950R"], "NAME": ["Riverbend Reservation"]}),
        trust_lands=pd.DataFrame({"GEOID": ["2950T"], "NAME": ["Riverbend Trust Land"]}),
        divisions=pd.DataFrame({"GEOCODE": ["A", "B", "C"], "TOWN": ["Andro", "Lew", "Kineo"]}),
        division_polygons=pd.DataFrame({"GEOCODE": ["A", "B", "B", "C"],
                                        "LURC": ["y", "n", "Y", "n"]}),
        division_blocks=blocks)


def build(**kw):
    i = inputs(**kw)
    return places_mod.build(i["spine"], i["edges"], i["subdivisions"], i["counties"],
                            i["house"], i["senate"], i["reservations"], i["trust_lands"],
                            i["divisions"], i["division_polygons"], i["division_blocks"],
                            "23", "Maine", VINTAGES, W())


def place(p, authority, code):
    return p[(p["authority"] == authority) & (p["code"] == code)].iloc[0]


def test_every_level_is_present_with_one_row_per_place():
    p = build()
    assert p.groupby("level").size().to_dict() == {
        "aiannh": 2, "county": 3, "cousub": 4, "megis_division": 3, "sldl": 2, "sldu": 1,
        "state": 1}
    assert not p.duplicated(["authority", "code"]).any()


def test_a_city_is_a_city_and_its_census_status_is_kept_not_shown_as_a_word():
    # D-128, FUNC-2: Maine's cities are FUNCSTAT F; "fictitious" is never a flag
    city = place(build(), "us_census_geoid", "2300120000")
    assert city["kind"] == "city" and city["census_funcstat"] == "F"
    assert not any(f in city["flags"] for f in ("fictitious", "active", "statistical"))


def test_a_reservation_subdivision_is_found_by_geometry_and_carries_its_note():
    p = build()
    for code in ("2301530000", "2301930000"):
        r = place(p, "us_census_geoid", code)
        assert r["kind"] == "reservation_subdivision" and r["context_note"] == "census_tribal_area"
        assert (r["part_of_authority"], r["part_of_code"]) == ("us_census_aiannh", "2950R")


def test_one_reservation_in_two_counties_reads_as_one_place_through_its_tribal_area():
    # PEN-1, D-129: two Census codes stay two rows; both name the same tribal area
    p = build()
    pieces = p[p["part_of_code"] == "2950R"]
    assert sorted(pieces["code"]) == ["2301530000", "2301930000"]
    assert place(p, "us_census_aiannh", "2950R")["context_note"] == "census_tribal_area"


def test_every_tribal_area_carries_the_context_note():
    p = build()
    assert (p.loc[p["level"] == "aiannh", "context_note"] == "census_tribal_area").all()


def test_a_reservation_by_lsad_that_geometry_does_not_confirm_is_refused():
    with pytest.raises(SystemExit):
        build(sub=subdivisions(**{"2300110000": ("Androscoggin Reservation", "86", "F")}))


def test_a_town_wholly_in_a_reservation_but_not_coded_one_is_refused():
    with pytest.raises(SystemExit):
        build(sub=subdivisions(**{"2301530000": ("Riverbend town", "43", "A")}))


def test_an_lsad_with_no_kind_is_refused():
    with pytest.raises(SystemExit):
        build(sub=subdivisions(**{"2300110000": ("Androscoggin village", "47", "A")}))


def test_towns_that_differ_from_the_2024_layer_are_refused():
    sub = subdivisions()
    with pytest.raises(SystemExit):
        build(sub=sub[sub["GEOID"] != "2300110000"])


def test_lurc_divisions_and_the_towns_they_touch():
    # D-130: any polygon y makes a division lurc; disagreeing polygons add lurc_mixed
    p = build()
    assert place(p, "megis", "A")["flags"] == ["lurc"]
    assert place(p, "megis", "B")["flags"] == ["lurc", "lurc_mixed"]
    town = place(p, "us_census_geoid", "2300110000")
    assert "lurc" in town["flags"] and town["lurc_share_population"] == 1.0
    assert pd.isna(place(p, "us_census_geoid", "2301930000")["lurc_share_population"])


def test_a_division_no_block_point_falls_in_is_kept_and_flagged():
    assert place(build(), "megis", "C")["flags"] == ["no_block_points"]


def test_a_place_with_nobody_says_so():
    r = place(build(), "us_census_geoid", "2301530000")
    assert {"zero_population", "zero_households"} <= set(r["flags"])


def test_an_edge_end_with_no_place_is_refused():
    # division A has edges to a town; drop it from the divisions, and an edge
    # names a place the table does not hold (Contract 3's ends invariant)
    i = inputs()
    i["divisions"] = i["divisions"][i["divisions"]["GEOCODE"] != "A"]
    with pytest.raises(SystemExit):
        places_mod.build(i["spine"], i["edges"], i["subdivisions"], i["counties"],
                         i["house"], i["senate"], i["reservations"], i["trust_lands"],
                         i["divisions"], i["division_polygons"], i["division_blocks"],
                         "23", "Maine", VINTAGES, W())


# ── step 6: notes by row (D-156, D-158) ──────────────────────────────────
CONTAINS = "contains_census_tribal_area"


def test_a_place_holding_any_tribal_block_carries_the_contains_note():
    # the town holds one trust-land block of three; its county, the state, the
    # House district and Senate district it lies in, and its civil division
    # all hold that block or the reservation's
    p = build()
    for authority, code in (("us_census_geoid", "23"), ("us_census_geoid", "23001"),
                            ("us_census_geoid", "23015"), ("us_census_geoid", "23019"),
                            ("us_census_geoid", "2300110000"), ("us_census_sldl", "23002"),
                            ("us_census_sldu", "23001"), ("megis", "A")):
        assert place(p, authority, code)["context_note"] == CONTAINS, (authority, code)


def test_a_place_with_no_tribal_block_carries_no_note():
    p = build()
    for authority, code in (("us_census_geoid", "2300120000"), ("us_census_sldl", "23001"),
                            ("megis", "B"), ("megis", "C")):
        assert pd.isna(place(p, authority, code)["context_note"]), (authority, code)


def test_the_tribal_note_stays_on_tribal_boundaries():
    p = build()
    tribal = (p["level"] == "aiannh") | (p["kind"] == "reservation_subdivision")
    assert (p.loc[tribal, "context_note"] == "census_tribal_area").all()
    assert not (p.loc[~tribal, "context_note"] == "census_tribal_area").any()


def test_the_table_tells_the_gate_which_notes_its_rows_carry():
    # NOTE-1: before step 6 the table listed none and rule 9 refused it
    meta = places_mod.context_metadata(build())
    assert meta["row_context_notes"] == ["census_tribal_area", CONTAINS]
    assert meta["context_notes"] == ["census_tribal_area", "census_tribal_places", CONTAINS]


def test_the_notes_the_primitive_names_are_the_notes_file_s():
    # two homes for one mapping, held equal (D-157, D-158)
    notes = yaml.safe_load((REPO / "seeds" / "notes" / "notes.yml").read_text())["notes"]
    assert notes[places_mod.TRIBAL_NOTE]["when_merged"] == places_mod.CONTAINS_NOTE
    assert places_mod.CONTAINS_NOTE in notes and places_mod.TABLE_NOTE in notes
    types = yaml.safe_load((REPO / "seeds" / "schemas" / "semantic_types.yml").read_text())["types"]
    assert [n["id"] for n in types["places"]["required_context"]] == [places_mod.TABLE_NOTE]
