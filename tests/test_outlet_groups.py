"""tests for soil/transform/group_outlet_records.py (Sprint 06, step 8)."""

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "group_outlet_records", ROOT / "soil" / "transform" / "group_outlet_records.py")
gor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gor)


def _stack(rows):
    cols = ["source", "source_line", "name", "url", "frequency", "town", "county"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows], columns=cols)


def test_url_key_drops_scheme_www_and_slash_but_keeps_the_path():
    assert gor.url_key("https://www.BangorDailyNews.com/") == "bangordailynews.com"
    assert gor.url_key("bangordailynews.com") == "bangordailynews.com"
    assert gor.url_key("https://www.sunjournal.com/weeklies/advertiser-democrat/") \
        == "sunjournal.com/weeklies/advertiser-democrat"
    assert gor.url_key(None) is None


def test_name_key_normalizes_without_guessing():
    assert gor.name_key("The Bangor Daily News (BPC)") == "bangor daily news"
    assert gor.name_key("Amjambo Africa!") == "amjambo africa"
    assert gor.name_key("Peaks Island News & Views") == "peaks island news and views"


def test_two_sources_sharing_a_url_are_one_group():
    g = gor.group_records(_stack([
        ("cision", 3, "Bangor Daily News", "https://bangordailynews.com", "daily", None, None),
        ("easton", 5, "BDN", "bangordailynews.com/", None, None, None)]))
    assert g["group_id"].nunique() == 1
    assert set(g["match_basis"]) == {"url_key"}


def test_one_source_twice_under_a_key_is_never_joined():
    g = gor.group_records(_stack([
        ("cision", 3, "Sun Journal", "sunjournal.com", None, None, None),
        ("cision", 9, "Advertiser Democrat", "sunjournal.com", None, None, None)]))
    assert g["group_id"].nunique() == 2
    assert "not joined" in g.loc[1, "match_note"]


def test_a_disagreement_is_listed_for_every_source():
    g = gor.group_records(_stack([
        ("cision", 3, "Amjambo Africa", "amjamboafrica.com", "monthly", "Portland", None),
        ("mme", 7, "Amjambo Africa", None, "weekly", "portland ", None)]))
    d = gor.disagreements(g)
    assert set(d["field"]) == {"frequency"}
    assert set(d["source"]) == {"cision", "mme"}


def test_an_empty_value_is_not_a_disagreement():
    g = gor.group_records(_stack([
        ("cision", 3, "Amjambo Africa", None, "monthly", None, None),
        ("easton", 4, "Amjambo Africa", None, None, None, None)]))
    assert gor.disagreements(g).empty


def test_a_lone_record_is_its_own_group():
    g = gor.group_records(_stack([
        ("lnc", 2, "Quoddy Tides", None, None, "Eastport", "Washington")]))
    assert g.loc[0, "group_id"] == "g0001"
    assert pd.isna(g.loc[0, "match_basis"]) or g.loc[0, "match_basis"] is None
