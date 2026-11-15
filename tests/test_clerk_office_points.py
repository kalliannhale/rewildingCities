"""tests for soil/transform/prepare_clerk_office_points.py (Sprint 06, step
3, the fourth carrier; GEO-1). the clerk list read by declared position,
never a name or phone; an exact match on number, street and ZIP, the street
spelled through USPS Publication 28; one point per distinct office; every
unplaced row listed with its reason (D-234 to D-238). rows and points are
illustrative, shaped like the reads of 2026-11-14 and 15, not copied."""

import csv
import importlib.util
import io
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "prepare_clerk_office_points",
    ROOT / "soil" / "transform" / "prepare_clerk_office_points.py")
cp = importlib.util.module_from_spec(_spec)
sys.modules["prepare_clerk_office_points"] = cp
_spec.loader.exec_module(cp)

CROSSWALKS = ROOT / "seeds" / "crosswalks"
STREETS = yaml.safe_load((CROSSWALKS / "addresses" / "usps_pub28.yml").read_text())
CLERKS = yaml.safe_load((CROSSWALKS / "clerks" / "maine_sos_clerk_info.yml").read_text())
ADDRESSES = yaml.safe_load((CROSSWALKS / "addresses" / "maine_e911_fgdb.yml").read_text())
SPELLING = cp.build_spelling(STREETS)


def clerk(municipality, street="", note="", csz=None, geocode=""):
    return {"municipality": municipality, "street": street, "street_note": note,
            "city_state_zip": csz if csz is not None else f"{municipality}, ME  04406",
            "geocode": geocode}


def clerk_csv(rows, header=None):
    """the list as the state writes it: every column filled, the names and
    phones included, so a test can see they are never read."""
    header = header or CLERKS["header"]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(header)
    at = {spec["position"]: role for role, spec in CLERKS["columns"].items()}
    for r in rows:
        w.writerow([r[at[i]] if i in at else "Private Person 207-555-0100"
                    for i in range(len(header))])
    return out.getvalue().encode("utf-8")


def point(site, number, street_name, suffix="", zip_="04406", predir="", postdir="",
          number_suffix="", town="Abbot", place_type="Residential",
          placement="Structure - Rooftop", lon=-69.5, lat=45.2, unit=""):
    return {"site_uid": site, "number": str(number), "number_suffix": number_suffix,
            "predir": predir, "street_name": street_name, "suffix": suffix, "postdir": postdir,
            "zip": zip_, "town": town, "state": "ME", "place_type": place_type,
            "placement": placement, "landmark": "", "unit": unit, "building": "",
            "floor": "", "room": "", "longitude": lon, "latitude": lat}


MUNICIPAL = ADDRESSES["municipal_class"]


def placed(clerk_rows, point_rows, campus_ties="listed", reviewed=None):
    table = cp.read_clerks(clerk_csv(clerk_rows), "utf-8", CLERKS)
    return cp.place(table, pd.DataFrame(point_rows), "ME", SPELLING, "test",
                    campus_ties, MUNICIPAL, reviewed)


def review(street, zip_, site, **over):
    entry = {"street": street, "zip": zip_, "site_uid": site, "evidence": "read by a person",
             "read_on": "2026-11-15", "read_by": "Kalli A. Hale"}
    return {"reviewed": [{**entry, **over}]}


def reasons(meta):
    return {i["feature_id"]: i["reason"] for i in meta["listed_rows"]}


# ── Publication 28 ─────────────────────────────────────────────────────────
def test_c1_is_read_whole_and_every_double_is_resolved_by_name():
    assert len(STREETS["suffixes"]) == 206
    assert set(STREETS["resolved"]) == {"MDW", "PARK", "SPUR", "WALK", "PKWY"}
    assert SPELLING["suffix"]["PKWY"] == "PARKWAY"


def test_rd_and_road_are_one_word_and_only_the_last_word_is_a_suffix():
    n = cp.normalize_street
    assert n("Main Rd", SPELLING) == n("MAIN ROAD", SPELLING) == "MAIN ROAD"
    assert n("St George Rd", SPELLING) == "ST GEORGE ROAD"
    assert n("Pond Road", SPELLING) == "POND ROAD"


def test_a_one_word_street_has_no_suffix_and_none_is_guessed():
    assert cp.normalize_street("Minden", SPELLING) == "MINDEN"
    assert cp.normalize_street("Park", SPELLING) == "PARK"


def test_directional_words_are_their_abbreviations_wherever_they_stand():
    n = cp.normalize_street
    assert n("North Main Street", SPELLING) == n("N Main St", SPELLING) == "N MAIN STREET"
    assert n("Main St North", SPELLING) == "MAIN STREET N"


def test_a_double_the_crosswalk_does_not_resolve_refuses():
    streets = {**STREETS, "resolved": {k: v for k, v in STREETS["resolved"].items() if k != "PKWY"}}
    with pytest.raises(cp.ClerkOfficesRefused, match="PKWY"):
        cp.build_spelling(streets)


def test_a_resolution_for_a_form_in_one_group_refuses():
    streets = {**STREETS, "resolved": {**STREETS["resolved"], "RD": "ROAD"}}
    with pytest.raises(cp.ClerkOfficesRefused, match="RD"):
        cp.build_spelling(streets)


# ── the clerk list ──────────────────────────────────────────────────────────
def test_names_and_phones_are_never_read():
    table = cp.read_clerks(clerk_csv([clerk("Abbot", "133 Main Road")]), "utf-8", CLERKS)
    assert list(table.columns) == cp.CLERK_ROLES
    assert not table.apply(lambda c: c.str.contains("Private Person")).any().any()


def test_the_clerks_street_is_read_never_the_registrars():
    assert CLERKS["columns"]["street"]["position"] == 2
    assert CLERKS["header"][8] == CLERKS["header"][2] == "Address Line 1"


def test_a_header_that_moves_refuses():
    header = list(CLERKS["header"])
    header[2], header[8] = header[8], "Registrar Street"
    with pytest.raises(cp.ClerkOfficesRefused, match="header"):
        cp.read_clerks(clerk_csv([clerk("Abbot", "133 Main Road")], header), "utf-8", CLERKS)


def test_a_municipality_listed_twice_refuses():
    with pytest.raises(cp.ClerkOfficesRefused, match="twice"):
        cp.read_clerks(clerk_csv([clerk("Abbot", "1 A St"), clerk("Abbot", "2 B St")]),
                       "utf-8", CLERKS)


def test_the_declared_encoding_is_held():
    raw = clerk_csv([clerk("Abbot", "133 Main Road")]).replace(b"Abbot", "Abb\u00f6t".encode("cp1252"))
    with pytest.raises(cp.ClerkOfficesRefused, match="not utf-8"):
        cp.read_clerks(raw, "utf-8", CLERKS)


# ── matching ────────────────────────────────────────────────────────────────
def test_the_address_the_state_names_is_placed_whatever_its_class():
    collection, meta = placed(
        [clerk("Abbot", "133 Main Road", geocode="21010")],
        [point("U133", 133, "Main", "Rd", place_type="Residential"),
         point("U131", 131, "Main", "Rd", place_type="Government - Municipal",
               placement="Property Access")])
    props = collection["features"][0]["properties"]
    assert props["feature_id"] == "U133" and props["place_type"] == "Residential"
    assert props["geocodes"] == "21010" and meta["id_field"] == "feature_id"
    assert meta["crs"] == "EPSG:4326" and meta["spatial_unit"] == "municipal_clerk_office"


def test_the_street_decides_among_many_points_at_one_number():
    collection, _ = placed(
        [clerk("Acton", "35 H Road", csz="Acton, ME  04001")],
        [point("UH", 35, "H", "Rd", zip_="04001", place_type="Library"),
         point("UHK", 35, "Hickory", "Ln", zip_="04001"),
         point("UO", 35, "Oriole", "Rd", zip_="04001")])
    assert [f["properties"]["feature_id"] for f in collection["features"]] == ["UH"]


def test_two_bare_points_at_one_address_stay_a_tie_when_the_choice_is_listed():
    collection, meta = placed([clerk("Abbot", "133 Main Road")],
                              [point("U1", 133, "Main", "Rd"), point("U2", 133, "Main", "Rd")])
    assert collection["features"] == []
    assert meta["listed_rows"][0]["reason"] == "tie" and meta["listed_rows"][0]["candidates"] == 2


def test_a_street_with_no_suffix_matches_nothing_and_is_listed():
    _, meta = placed([clerk("Greenville", "7 Minden", csz="Greenville, ME  04441")],
                     [point("UM", 7, "Minden", "St", zip_="04441")])
    assert reasons(meta) == {"Greenville": "no_match"}


def test_a_zip_is_part_of_the_match():
    _, meta = placed([clerk("Abbot", "133 Main Road", csz="Abbot, ME  04407")],
                     [point("U133", 133, "Main", "Rd", zip_="04406")])
    assert reasons(meta) == {"Abbot": "no_match"}


def test_one_office_answering_for_many_rows_is_one_point():
    rows = [clerk(m, "369 Main Street", csz="Jackman, ME  04945", geocode=g)
            for m, g in (("Jackman", "25030"), ("Dennistown Plt", ""), ("Moose River", "25040"))]
    collection, meta = placed(rows, [point("UJ", 369, "Main", "St", zip_="04945")])
    assert len(collection["features"]) == 1
    props = collection["features"][0]["properties"]
    assert props["rows_served"] == 3 and props["municipalities"] == "Dennistown Plt; Jackman; Moose River"
    assert props["geocodes"] == "25030; 25040" and "shared_office" in props["flags"]
    assert meta["rows_placed"] == 3 and meta["shared_offices"] == 1


def test_every_row_that_cannot_be_matched_is_listed_with_its_reason():
    rows = [clerk("Cyr Plt", ""), clerk("Boxed", "PO Box 97"), clerk("Hall", "Town Hall, Main St"),
            clerk("Nozip", "1 Main St", csz="Nozip, ME"),
            clerk("Away", "1 Main St", csz="Away, NH  03301")]
    collection, meta = placed(rows, [point("U1", 1, "Main", "St")])
    assert collection["features"] == []
    assert reasons(meta) == {"Cyr Plt": "no_street_address", "Boxed": "po_box_only",
                             "Hall": "number_not_read", "Nozip": "no_zip",
                             "Away": "address_in_another_state"}


def test_a_street_note_rides_on_the_point_and_is_never_matched():
    collection, _ = placed([clerk("Cranberry Isles", "1 Main St", note="Islesford")],
                           [point("UC", 1, "Main", "St")])
    assert collection["features"][0]["properties"]["street_notes"] == "Islesford"


def test_no_name_or_phone_reaches_a_point_or_a_listed_row():
    collection, meta = placed([clerk("Abbot", "133 Main Road"), clerk("Cyr Plt", "")],
                              [point("U133", 133, "Main", "Rd")])
    text = str(collection) + str(meta["listed_rows"])
    assert "Private Person" not in text and "555" not in text


def test_a_matched_point_with_no_site_id_refuses():
    with pytest.raises(cp.ClerkOfficesRefused, match="site id"):
        placed([clerk("Abbot", "133 Main Road")], [point("", 133, "Main", "Rd")])


def test_the_address_crosswalk_never_reads_the_addressing_officer():
    assert "MAO_NAME" not in ADDRESSES["columns"].values()
    assert cp.check_addresses_reading(ADDRESSES)["crs"] == "EPSG:26919"


# ── ties (Kalli's choice C) ────────────────────────────────────────────────
def test_inside_one_building_the_bare_point_is_the_building():
    suites = [point(f"S{n}", 205, "Main", "St", zip_="04005", unit=f"Suite {n}") for n in (101, 102)]
    collection, meta = placed([clerk("Biddeford", "205 Main Street", csz="Biddeford, ME  04005")],
                              [point("B", 205, "Main", "St", zip_="04005")] + suites)
    props = collection["features"][0]["properties"]
    assert props["feature_id"] == "B" and props["placed_by"] == "building_point"
    assert props["tie_candidates"] == 3 and props["tie_spread_m"] == 0.0
    assert meta["offices_by_placed_by"] == {"building_point": 1}


def test_the_building_rule_holds_whatever_the_choice():
    rows = [point("B", 1, "Court", "St"), point("L", 1, "Court", "St", unit="LBBY",
                                                  place_type="Law Enforcement -Municipal")]
    collection, _ = placed([clerk("Auburn", "1 Court St")], rows, campus_ties="listed")
    assert collection["features"][0]["properties"]["placed_by"] == "building_point"


def test_a_campus_settles_on_its_one_municipal_point_when_the_choice_says_so():
    rows = [point("T", 1063, "Allagash", "Rd", place_type=MUNICIPAL, lon=-69.0000),
            point("F", 1063, "Allagash", "Rd", place_type="Fire Station", lon=-69.0003)]
    collection, meta = placed([clerk("Allagash", "1063 Allagash Road")], rows,
                              campus_ties="municipal_class")
    props = collection["features"][0]["properties"]
    assert props["feature_id"] == "T" and props["placed_by"] == "municipal_class"
    assert "tie_broken_by_class" in props["flags"] and 20 < props["tie_spread_m"] < 30
    assert meta["campus_ties"] == "municipal_class"


def test_a_campus_stays_a_tie_when_the_choice_is_listed():
    rows = [point("T", 1063, "Allagash", "Rd", place_type=MUNICIPAL),
            point("F", 1063, "Allagash", "Rd", place_type="Fire Station")]
    collection, meta = placed([clerk("Allagash", "1063 Allagash Road")], rows)
    assert collection["features"] == [] and reasons(meta) == {"Allagash": "tie"}


def test_a_campus_with_no_municipal_point_stays_a_tie():
    rows = [point("F", 63, "Broadway", "St", place_type="Fire Station"),
            point("P", 63, "Broadway", "St", place_type="Law Enforcement -Municipal")]
    _, meta = placed([clerk("Baileyville", "63 Broadway Street")], rows,
                     campus_ties="municipal_class")
    assert reasons(meta) == {"Baileyville": "tie"}


def test_a_campus_with_two_municipal_points_stays_a_tie():
    rows = [point("A", 16, "Cony", "St", place_type=MUNICIPAL),
            point("B", 16, "Cony", "St", place_type=MUNICIPAL)]
    _, meta = placed([clerk("Augusta", "16 Cony Street")], rows, campus_ties="municipal_class")
    assert reasons(meta) == {"Augusta": "tie"}


def test_a_choice_outside_its_options_refuses():
    with pytest.raises(cp.ClerkOfficesRefused, match="campus_ties"):
        placed([clerk("Abbot", "133 Main Road")], [point("U", 133, "Main", "Rd")],
               campus_ties="nearest")


def test_an_exact_match_says_it_was_exact():
    collection, _ = placed([clerk("Abbot", "133 Main Road")], [point("U", 133, "Main", "Rd")])
    props = collection["features"][0]["properties"]
    assert props["placed_by"] == "exact" and props["tie_candidates"] is None


# ── reviewed matches (GEO-4) ──────────────────────────────────────────────
KENNEBASIS = [point("UK", 8, "Kennebasis", "St", zip_="04668", town="Indian Township Reservation",
                    place_type=MUNICIPAL)]


def test_a_review_places_an_address_no_exact_match_can():
    collection, meta = placed([clerk("Indian Township", "8 Kennebasis Road", csz="Indian Township, ME  04668")],
                              KENNEBASIS, reviewed=review("8 Kennebasis Road", "04668", "UK"))
    props = collection["features"][0]["properties"]
    assert props["feature_id"] == "UK" and props["placed_by"] == "reviewed"
    assert props["review_read_by"] == "Kalli A. Hale" and "reviewed" in props["flags"]
    assert meta["reviews_applied"] == 1 and meta["listed_rows"] == []


def test_one_review_places_every_row_that_gives_its_address():
    rows = [clerk(m, "7 Minden", csz="Greenville, ME  04441") for m in ("Greenville", "Cove Point Twp")]
    collection, _ = placed(rows, [point("UG", 7, "Minden", "St", zip_="04441")],
                           reviewed=review("7 minden", "04441", "UG"))
    assert len(collection["features"]) == 1
    assert collection["features"][0]["properties"]["rows_served"] == 2


def test_a_review_the_run_no_longer_needs_refuses():
    with pytest.raises(cp.ClerkOfficesRefused, match="places it on its own"):
        placed([clerk("Abbot", "133 Main Road")], [point("U", 133, "Main", "Rd")],
               reviewed=review("133 Main Road", "04406", "U"))


def test_a_review_of_an_address_no_row_gives_refuses():
    with pytest.raises(cp.ClerkOfficesRefused, match="no row gives"):
        placed([clerk("Abbot", "133 Main Road")], [point("U", 133, "Main", "Rd")],
               reviewed=review("9 Elsewhere Lane", "04406", "U"))


def test_a_review_naming_no_point_in_the_file_refuses():
    with pytest.raises(cp.ClerkOfficesRefused, match="0 time"):
        placed([clerk("Indian Township", "8 Kennebasis Road", csz="Indian Township, ME  04668")],
               KENNEBASIS, reviewed=review("8 Kennebasis Road", "04668", "NOT-THERE"))


def test_a_review_never_leaves_its_zip():
    far = [point("UF", 8, "Kennebasis", "St", zip_="04667")]
    with pytest.raises(cp.ClerkOfficesRefused, match="never leaves"):
        placed([clerk("Indian Township", "8 Kennebasis Road", csz="Indian Township, ME  04668")],
               far, reviewed=review("8 Kennebasis Road", "04668", "UF"))


def test_a_review_with_no_evidence_refuses():
    with pytest.raises(cp.ClerkOfficesRefused, match="evidence"):
        placed([clerk("Indian Township", "8 Kennebasis Road", csz="Indian Township, ME  04668")],
               KENNEBASIS, reviewed=review("8 Kennebasis Road", "04668", "UK", evidence=" "))


def test_a_review_can_settle_a_tie_the_rules_leave():
    rows = [point("F", 63, "Broadway", "St", place_type="Fire Station"),
            point("P", 63, "Broadway", "St", place_type="Law Enforcement -Municipal")]
    collection, _ = placed([clerk("Baileyville", "63 Broadway Street")], rows,
                           campus_ties="municipal_class",
                           reviewed=review("63 Broadway Street", "04406", "P"))
    assert collection["features"][0]["properties"]["feature_id"] == "P"


def test_the_seeds_reviews_are_well_formed():
    seed = yaml.safe_load((CROSSWALKS / "clerks" / "maine_sos_reviewed.yml").read_text())
    assert len(cp.check_reviewed(seed)) == len(seed["reviewed"]) == 2
