"""
tests/test_seats.py

The seats table (Contract 3, section 6) and the Maine Legislature provider.

Fixtures are synthetic, in the exact shapes fetched on 2026-11-11 (LEG-5,
LEG-7): the real House export carries members' phone numbers, and a committed
fixture would republish them (D-138, D-139).
"""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from canopy.providers.maine_legislature import (
    COLUMNS as ROSTER_COLUMNS, HOUSE_HEADER, parse_house_csv, parse_senate_html)

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "build_seats", ROOT / "soil" / "transform" / "build_seats.py")
build_seats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_seats)

AS_OF = "2026-12-03T15:00:00+00:00"
SWORN_IN = "2026-12-02"
HOUSE_URL = "https://legislature.maine.gov/house/Home/ExportActiveMembers?format=csv"
SENATE_URL = "https://legislature.maine.gov/senate/district-listing/9526"
TRIBAL = [{"name": "Passamaquoddy Tribe"},
          {"name": "Penobscot Nation", "statute_wording": "Penobscot Indian Nation"},
          {"name": "Houlton Band of Maliseet Indians"}, {"name": "Mi'kmaq Nation"}]

HOUSE_CSV = (",".join(HOUSE_HEADER) + "\n"
             "Ada Example,Democrat,1,Aroostook,17,Ada.Example@legislature.maine.gov,"
             "2070000000,Fort Kent,,,,Taxation\n"
             "Ben Sample,Republican,2,\"Knox, Lincoln\",0,Ben.Sample@legislature.maine.gov,"
             "2070000001,Union,,,Ex Officio,\"Labor|Agriculture, Conservation and Forestry\"\n")

SENATE_HTML = """<html><body><h1>Senate Districts</h1><ul>
<li>District 1 (<a href="/map/1">Map</a>) - <a href="/senate/sen-one/1">Senator Cara Placeholder (R-Aroostook)</a></li>
<li>District 2 (<a href="/map/2">Map</a>) - <a href="/senate/sen-two/2">Senator Harold "Dee" L. Testcase, III (D-York)</a></li>
</ul></body></html>"""


def places(house=(1, 2, 3), senate=(1, 2)):
    rows = [{"authority": "us_census_sldl", "code": f"23{n:03d}", "level": "sldl"} for n in house]
    rows += [{"authority": "us_census_sldu", "code": f"23{n:03d}", "level": "sldu"} for n in senate]
    rows += [{"authority": "us_census_geoid", "code": "23", "level": "state"}]
    return pd.DataFrame(rows)


def roster(rows):
    frame = pd.DataFrame(rows, columns=ROSTER_COLUMNS)
    return frame.astype(object).where(frame.notna(), None)


def house_roster(as_of=AS_OF):
    return roster(parse_house_csv(HOUSE_CSV, HOUSE_URL, as_of))


def senate_roster(as_of=AS_OF):
    return roster(parse_senate_html(SENATE_HTML, SENATE_URL, as_of)[0])


class W:
    def info(self, message): pass


def build(p=None, house=None, senate=None, tribal=TRIBAL, sworn_in=SWORN_IN):
    return build_seats.build(places() if p is None else p,
                             house_roster() if house is None else house,
                             senate_roster() if senate is None else senate,
                             "133", sworn_in, tribal, "23", W())


# the provider

def test_house_export_read_without_phones():
    rows = parse_house_csv(HOUSE_CSV, HOUSE_URL, AS_OF)
    assert [r["name"] for r in rows] == ["Ada Example", "Ben Sample"]
    assert all("2070000000" not in str(v) for r in rows for v in r.values())
    assert rows[1]["seat_number"] == "0" and rows[1]["position"] == "Ex Officio"
    assert list(rows[0]) == ROSTER_COLUMNS


def test_house_header_change_is_refused():
    changed = HOUSE_CSV.replace("Email,Phone", "Phone,Email", 1)
    with pytest.raises(ValueError, match="header changed"):
        parse_house_csv(changed, HOUSE_URL, AS_OF)


def test_senate_listing_read_with_profile_links():
    rows, vacant = parse_senate_html(SENATE_HTML, SENATE_URL, AS_OF)
    assert vacant == 0
    assert [(r["district"], r["name"], r["party"]) for r in rows] == [
        ("1", "Cara Placeholder", "R"), ("2", 'Harold "Dee" L. Testcase, III', "D")]
    assert rows[0]["profile_url"] == "https://legislature.maine.gov/senate/sen-one/1"


def test_senate_vacancy_is_counted_not_a_row():
    html = SENATE_HTML.replace("</ul>", "<li>District 3 (Map) - Vacant</li></ul>")
    rows, vacant = parse_senate_html(html, SENATE_URL, AS_OF)
    assert len(rows) == 2 and vacant == 1


def test_senate_line_in_unknown_shape_is_refused():
    html = SENATE_HTML.replace("</ul>", "<li>District 3 (Map) - Someone Unexpected</li></ul>")
    with pytest.raises(ValueError, match="unknown shape"):
        parse_senate_html(html, SENATE_URL, AS_OF)


# the table

def test_every_district_place_is_a_seat_and_tribal_seats_have_no_district():
    seats = build()
    assert list(seats.columns) == build_seats.COLUMNS
    assert len(seats) == 3 + 2 + 4
    assert not seats.duplicated(build_seats.KEY).any()
    tribal = seats[seats["seat_kind"] == "tribal"]
    assert set(tribal["chamber"]) == {"house"}
    assert tribal["district_code"].isna().all()
    assert set(tribal["seat_ref"]) == {t["name"] for t in TRIBAL}
    penobscot = tribal[tribal["seat_ref"] == "Penobscot Nation"].iloc[0]
    assert penobscot["statute_wording"] == "Penobscot Indian Nation"


def test_a_seat_the_record_names_no_one_for_is_vacant():
    seats = build().set_index(["chamber", "seat_ref"])
    assert seats.loc[("house", "23003"), "vacant"]
    assert seats.loc[("house", "23001"), "holder_name"] == "Ada Example"
    assert not seats.loc[("senate", "23002"), "vacant"]


def test_legiscan_never_fills_a_field():
    seats = build()
    assert seats[["legiscan_people_id", "legiscan_district", "legiscan_agreement"]].isna().all().all()


def refused(**kwargs):
    with pytest.raises(SystemExit):
        build(**kwargs)


def test_refuses_a_holder_whose_district_has_no_place():
    refused(p=places(house=(1, 3)))


def test_refuses_two_holders_for_one_seat():
    h = house_roster()
    h.loc[1, "district"] = "1"
    refused(house=h)


def test_refuses_a_house_holder_with_no_district():
    h = house_roster()
    h.loc[1, "district"] = None
    refused(house=h)


def test_refuses_a_roster_fetched_before_the_swearing_in():
    refused(house=house_roster(as_of="2026-11-11T05:00:00+00:00"))


def test_refuses_an_empty_roster():
    refused(senate=roster([]))


def test_refuses_a_tribal_name_declared_twice():
    refused(tribal=TRIBAL + [{"name": "Mi'kmaq Nation"}])
