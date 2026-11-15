"""tests for soil/transform/prepare_health_center_points.py (Sprint 06, step
3, the third carrier; HRSA's columns and codes read from one crosswalk, the
snapshot held to its declared day, every unplaced site listed with its
reason; D-232)."""

import csv
import importlib.util
import io
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "prepare_health_center_points",
    ROOT / "soil" / "transform" / "prepare_health_center_points.py")
hp = importlib.util.module_from_spec(_spec)
sys.modules["prepare_health_center_points"] = hp
_spec.loader.exec_module(hp)

READING = yaml.safe_load((ROOT / "seeds" / "crosswalks" / "health_centers"
                          / "hrsa_health_center_sites.yml").read_text())
C = READING["columns"]
EXTRA = "U.S. Congressional Representative Name"   # a column the crosswalk never reads


def site(key, **over):
    """one row, a Maine permanent service site unless told otherwise. names,
    keys and coordinates are illustrative, not HRSA's."""
    row = {"site_key": key, "health_center_number": "H80CS00001", "name": f"Site {key}",
           "health_center": "EXAMPLE HEALTH CENTER", "street": "1 Main St", "city": "Bangor",
           "site_state": "ME", "zip": "04401", "hours": "40", "setting": "All Other Clinic Types",
           "status": "Active", "location_type": "Permanent", "site_type": "Service Delivery Site",
           "center_type": "Federally Qualified Health Center (FQHC)",
           "operator": "Health Center/Applicant", "organization_state": "ME",
           "longitude": "-68.77", "latitude": "44.80", "county_fips": "23019",
           "state_fips": "23", "record_date": "11/14/2026"}
    row.update(over)
    return row


def csv_bytes(rows, drop=None):
    headers = [C[r] for r in hp.ROLES if r != drop] + [EXTRA]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(headers)
    for r in rows:
        w.writerow([r[role] for role in hp.ROLES if role != drop] + ["Someone"])
    return out.getvalue().encode("utf-8")


def placed(rows, state="ME", fips="23"):
    table = hp.read_sites(csv_bytes(rows), "utf-8", READING)
    return hp.points_from(table, state, fips, READING)


def ids(collection):
    return [f["properties"]["feature_id"] for f in collection["features"]]


def reasons(meta):
    return {i["feature_id"]: i["reason"] for i in meta["listed_sites"]}


# ── what is placed ────────────────────────────────────────────────────────
def test_a_service_site_is_placed_with_x_as_longitude():
    collection, meta = placed([site("A")])
    assert ids(collection) == ["A"]
    assert collection["features"][0]["geometry"]["coordinates"] == [-68.77, 44.80]
    assert meta["id_field"] == "feature_id" and meta["spatial_unit"] == "health_center_site"


def test_an_administrative_and_service_site_is_placed():
    collection, _ = placed([site("A", site_type="Administrative/Service Delivery Site")])
    assert ids(collection) == ["A"]


def test_seasonal_and_look_alike_sites_are_placed_as_adjectives():
    rows = [site("S", location_type="Seasonal", setting="School"),
            site("L", center_type="Federally Qualified Health Center (FQHC) Look-Alike")]
    collection, meta = placed(rows)
    props = {f["properties"]["feature_id"]: f["properties"] for f in collection["features"]}
    assert props["S"]["seasonal"] is True and props["S"]["look_alike"] is False
    assert props["L"]["look_alike"] is True and props["L"]["seasonal"] is False
    assert "seasonal" in props["S"]["flags"] and "setting:School" in props["S"]["flags"]
    assert meta["seasonal_sites"] == 1 and meta["look_alike_sites"] == 1


def test_every_setting_is_placed_and_kept():
    collection, _ = placed([site("N", setting="Nursing Home"), site("K", setting="School")])
    assert sorted(ids(collection)) == ["K", "N"]


def test_a_subrecipients_site_is_placed_where_it_stands():
    collection, _ = placed([site("A", operator="Subrecipient")])
    assert collection["features"][0]["properties"]["operator"] == "Subrecipient"


# ── listed, never placed: rules ───────────────────────────────────────────
def test_an_administrative_site_is_listed():
    collection, meta = placed([site("A", site_type="Administrative", setting="Unknown")])
    assert ids(collection) == [] and reasons(meta) == {"A": "administrative_site"}


def test_a_mobile_van_is_listed():
    collection, meta = placed([site("V", location_type="Mobile Van")])
    assert ids(collection) == [] and reasons(meta) == {"V": "mobile_unit"}


def test_a_site_with_no_point_is_listed_and_never_given_one():
    row = site("X", site_state="XX", state_fips="XX", longitude="", latitude="",
               street="", city="")
    collection, meta = placed([row])
    assert ids(collection) == [] and reasons(meta) == {"X": "no_point_given"}


def test_a_withheld_address_is_never_placed_even_with_a_point():
    collection, meta = placed([site("D", setting="Domestic Violence")])
    assert ids(collection) == [] and reasons(meta) == {"D": "address_withheld"}


def test_a_site_whose_own_fields_disagree_on_its_state_is_listed():
    row = site("N", state_fips="33", longitude="-70.9", latitude="43.1")
    collection, meta = placed([row])
    assert ids(collection) == [] and reasons(meta) == {"N": "located_in_another_state"}


def test_a_maine_grantees_site_in_another_state_is_not_maines():
    rows = [site("A"), site("N", site_state="NH", state_fips="33")]
    collection, meta = placed(rows)
    assert ids(collection) == ["A"] and reasons(meta) == {}


def test_a_grantee_elsewhere_does_not_move_a_maine_site():
    collection, _ = placed([site("A", organization_state="NH")])
    assert ids(collection) == ["A"]


def test_a_site_not_open_is_listed():
    reading = {**READING, "statuses": {**READING["statuses"], "Inactive": {"group": "closed"}}}
    table = hp.read_sites(csv_bytes([site("I", status="Inactive")]), "utf-8", reading)
    collection, meta = hp.points_from(table, "ME", "23", reading)
    assert ids(collection) == [] and reasons(meta) == {"I": "not_open"}


# ── refused ───────────────────────────────────────────────────────────────
def test_an_undeclared_code_refuses_the_run():
    with pytest.raises(hp.HealthCenterPointsRefused, match="Intermittent"):
        placed([site("A", location_type="Intermittent")])


def test_a_site_key_used_twice_or_blank_is_refused():
    with pytest.raises(hp.HealthCenterPointsRefused, match="used twice"):
        placed([site("A"), site("A")])
    with pytest.raises(hp.HealthCenterPointsRefused, match="no BPHC Assigned Number"):
        placed([site("")])


def test_a_declared_column_the_file_lacks_is_refused():
    with pytest.raises(hp.HealthCenterPointsRefused, match="lacks the declared column"):
        hp.read_sites(csv_bytes([site("A")], drop="hours"), "utf-8", READING)


def test_a_column_the_crosswalk_does_not_name_is_never_read():
    table = hp.read_sites(csv_bytes([site("A")]), "utf-8", READING)
    assert EXTRA not in table.columns and set(table.columns) == set(hp.ROLES)


def test_coordinates_that_are_not_a_place_on_earth_are_refused():
    with pytest.raises(hp.HealthCenterPointsRefused, match="not a longitude"):
        placed([site("A", longitude="44.8", latitude="-268.7")])


def test_a_file_in_another_encoding_is_refused():
    with pytest.raises(hp.HealthCenterPointsRefused, match="not utf-8"):
        hp.read_sites(b"\xff\xfe" + csv_bytes([site("A")]), "utf-8", READING)


# ── the snapshot is the copy declared ─────────────────────────────────────
def test_the_snapshot_matches_its_declared_day():
    table = hp.read_sites(csv_bytes([site("A"), site("B")]), "utf-8", READING)
    hp.check_snapshot(table, "2026-11-14", READING)


def test_another_days_copy_is_refused():
    table = hp.read_sites(csv_bytes([site("A"), site("B", record_date="11/15/2026")]),
                          "utf-8", READING)
    with pytest.raises(hp.HealthCenterPointsRefused, match="not the copy declared"):
        hp.check_snapshot(table, "2026-11-14", READING)
    with pytest.raises(hp.HealthCenterPointsRefused, match="YYYY-MM-DD"):
        hp.check_snapshot(table, "11/14/2026", READING)


# ── the crosswalk ─────────────────────────────────────────────────────────
def test_the_crosswalk_declares_every_role_and_code_map():
    assert hp.check_reading(READING) is READING
    assert READING["site_types"]["Administrative"]["group"] == "administrative"
    assert READING["location_types"]["Mobile Van"]["group"] == "mobile"
    assert "Domestic Violence" in READING["withheld_settings"]


def test_a_code_with_no_meaning_is_refused():
    bad = {**READING, "site_types": {"Administrative": {}}}
    with pytest.raises(hp.HealthCenterPointsRefused, match="declares no group"):
        hp.check_reading(bad)
