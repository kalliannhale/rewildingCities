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
    cols = ["source", "source_line", "name", "url", "frequency", "named_town", "office_town"]
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
    assert "not used to join" in g.loc[1, "match_note"]
    assert "not used to join" in g.loc[0, "match_note"]


def test_a_key_one_source_holds_twice_joins_nothing_whatever_the_order():
    rows = [("cision", 3, "Press Herald Sports", "pressherald.com", None, None, None),
            ("cision", 4, "Press Herald", "pressherald.com", None, None, None),
            ("cision_raw", 8, "Press Herald", "pressherald.com", None, None, None)]
    for order in (rows, rows[::-1]):
        g = gor.group_records(_stack(order)).set_index("source_line")
        assert g.loc[4, "group_id"] == g.loc[8, "group_id"]
        assert g.loc[3, "group_id"] != g.loc[8, "group_id"]
        assert g.loc[8, "match_basis"] == "name_key"


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


def test_an_office_address_is_never_compared_with_a_named_town():
    g = gor.group_records(_stack([
        ("cision", 3, "Advertiser Democrat", None, None, None, "South Portland"),
        ("mme", 7, "Advertiser Democrat", None, None, "Norway", None)]))
    assert gor.disagreements(g).empty


def test_the_disagreements_primitive_uses_the_same_comparison():
    spec = importlib.util.spec_from_file_location(
        "list_outlet_disagreements",
        ROOT / "soil" / "transform" / "list_outlet_disagreements.py")
    lod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lod)
    assert lod.COMPARED == gor.COMPARED
    assert lod.KEY == ["group_id", "field", "source", "source_line"]


# ── a name written inverted, and one record written twice (D-253, D-254) ──

def _stack_at(rows):
    cols = ["source", "source_line", "name", "url", "frequency", "named_town", "office_town",
            "address_raw", "zip_raw"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows], columns=cols)


def test_a_name_written_inverted_is_the_same_name():
    assert gor.name_key("Star-Herald, The") == "star herald"
    assert gor.name_key("Lincoln County News, The") == gor.name_key("The Lincoln County News")
    assert gor.name_key("Bangor Daily News, The (BPC)") == "bangor daily news"
    assert gor.name_key("Theater News") == "theater news"


LCN = "https://lcnme.com/"
MILLS = ("116 Mills Road", "04553-3408")


def test_one_record_written_twice_joins_itself_and_its_key_joins_the_rest():
    # the shape the real export holds (session 12's read): Cision lists one
    # paper under two spellings, Cision's raw pull twice alike, and the lists
    # once each; before D-254 the name key went dark for everyone
    g = gor.group_records(_stack_at([
        ("cision", 86, "Lincoln County News", LCN, None, None, "Newcastle", *MILLS),
        ("cision", 87, "Lincoln County News, The", LCN, None, None, "Newcastle", *MILLS),
        ("cision_raw", 347, "Lincoln County News", LCN, None, None, "Newcastle", *MILLS),
        ("cision_raw", 348, "Lincoln County News", LCN, None, None, "Newcastle", "116 Mills Road.", "4553"),
        ("easton", 18, "Lincoln County News", LCN, None, None, None, None, None),
        ("local_news_catalyst", 20, "The Lincoln County News", None, None, "Newcastle", None, None, None)]))
    assert g["group_id"].nunique() == 1
    by = g.set_index("source_line")
    assert by.loc[87, "same_record_as"] == "86" and by.loc[348, "same_record_as"] == "347"
    assert pd.isna(by.loc[86, "same_record_as"]) or by.loc[86, "same_record_as"] is None
    assert "same_record" in by.loc[87, "match_basis"]
    assert "not used to join" not in (gor._text(by.loc[20, "match_note"]) or "")


def test_one_name_at_two_addresses_stays_two_outlets():
    g = gor.group_records(_stack_at([
        ("cision", 3, "Town Crier", "towncrier.com", None, None, None, "1 Main St", "04101"),
        ("cision", 4, "Town Crier", "towncrier.com", None, None, None, "9 Elm St", "04901")]))
    assert g["group_id"].nunique() == 2
    assert g["same_record_as"].isna().all()
    assert all("not used to join" in n for n in g["match_note"])


def test_a_record_with_no_address_or_url_is_never_read_as_written_twice():
    g = gor.group_records(_stack_at([
        ("easton", 3, "Quoddy Tides", None, None, None, None, None, None),
        ("easton", 4, "Quoddy Tides", None, None, None, None, None, None),
        ("cision", 5, "Free Press", "fp.com", None, None, None, None, "04843"),
        ("cision", 6, "Free Press", "fp.com", None, None, None, None, "04843")]))
    assert g["group_id"].nunique() == 4
    assert g["same_record_as"].isna().all()


def test_written_twice_survives_the_csv_between_steps():
    import tempfile
    rows = [("cision", 1, "Weekly", "weekly.com", None, None, None, "5 Fern Street", "4282"),
            ("cision", 2, "Weekly", "weekly.com", None, None, None, "5 Fern street", "04282"),
            ("cision", 3, "Other", None, None, None, None, None, None)]
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "stack.csv"
        _stack_at(rows).to_csv(path, index=False)
        back = pd.read_csv(path, dtype=str)
    g = gor.group_records(back).set_index("source_line")
    assert g.loc["2", "same_record_as"] == "1"
    assert g.loc["1", "group_id"] != g.loc["3", "group_id"]


def test_an_office_key_has_one_home():
    assert gor.office_key("116 Mills Rd.", "4553") == gor.office_key("116 mills rd", "04553-3408")
    assert gor.office_key("116 Mills Rd", None) is None
    assert gor.office_key(None, "04553") is None
    assert gor.zip5("041061234") == "04106" and gor.zip5("12") is None
