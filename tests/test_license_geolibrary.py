"""
tests/test_license_geolibrary.py  |  rewildingCities, Sprint 06 zip 2b (D-290)

Maine's town and county boundaries come through the Maine GeoLibrary, on
which no copyright or licensing restriction may be fixed (5 M.R.S.A. section
2005). The term says so, with attribution as a condition, and it is the one
the boundaries' manifest entries name, so the graph built on them may leave.
"""

from pathlib import Path

import yaml

from canopy.expose.records import load_licenses

REPO = Path(__file__).resolve().parents[1]


def test_the_geolibrary_term_permits_public_with_credit():
    term = load_licenses(REPO / "seeds" / "licenses")["maine_geolibrary_public"]
    assert term["permits"] == ["private", "organization", "public"]
    assert term["attribution"] == "required" and term["verified"] is True
    for cited in ("2005", "2004", "1995", "D-290"):
        assert cited in term["basis"], cited


def test_the_boundaries_name_the_geolibrary_term():
    datasets = yaml.safe_load((REPO / "plots" / "maine" / "manifest.yml").read_text())["datasets"]
    for name in ("governance_unit_town", "governance_unit_county"):
        assert datasets[name]["license"] == "maine_geolibrary_public", name
