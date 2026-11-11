"""tests for soil/transform/stack_outlet_sources.py (Sprint 06, step 8, P-9)."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "stack_outlet_sources", ROOT / "soil" / "transform" / "stack_outlet_sources.py")
sos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sos)

VOCAB = {"daily": ["Daily", "Daily (Mon-Fri)"], "weekly": ["Weekly"],
         "monthly": ["Monthly"]}


def _plant(tmp_path, sources, files, vocabulary=VOCAB):
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    seed = tmp_path / "seed.yml"
    seed.write_text(yaml.safe_dump({"frequency_vocabulary": vocabulary,
                                    "sources": sources}))
    return seed


EASTON = ',"Caveat -- for my personal use",,,\n,,,,\nName,Link,Format,Contact,Ownership\n' \
         'Amjambo Africa,https://www.amjamboafrica.com/,Monthly,Kit kit@example.org,Independent\n' \
         ',,,,\n'
MME = 'Publication,Medium,Print\nThe Weekly Paper,Newspaper,Weekly\nWXYZ,Radio,Country\n' \
      'Twice Times,Newspaper,2 Monthly\n'


def test_header_found_below_a_caveat_and_a_blank_line(tmp_path):
    seed = _plant(tmp_path, {"easton": {"file": "e.csv", "columns": {
        "name": "Name", "url": "Link", "frequency_raw": "Format"}}}, {"e.csv": EASTON})
    out = sos.stack_sources(seed, tmp_path)
    assert list(out["name"]) == ["Amjambo Africa"]
    assert out.loc[0, "source_line"] == 4
    assert out.loc[0, "frequency"] == "monthly"


def test_an_undeclared_column_is_never_read(tmp_path):
    seed = _plant(tmp_path, {"easton": {"file": "e.csv", "columns": {
        "name": "Name", "ownership_raw": "Ownership"}}}, {"e.csv": EASTON})
    out = sos.stack_sources(seed, tmp_path)
    assert not out.astype(str).apply(lambda c: c.str.contains("kit@example.org")).any().any()


def test_a_never_read_column_cannot_be_declared(tmp_path):
    seed = _plant(tmp_path, {"easton": {"file": "e.csv", "never_read": ["Contact"],
                                        "columns": {"name": "Name", "url": "Contact"}}},
                  {"e.csv": EASTON})
    with pytest.raises(sos.SourceRefused, match="never_read"):
        sos.stack_sources(seed, tmp_path)


def test_a_missing_declared_column_refuses_its_source(tmp_path):
    seed = _plant(tmp_path, {"mme": {"file": "m.csv", "columns": {
        "name": "Publication", "business_model_raw": "Biz Model"}}}, {"m.csv": MME})
    with pytest.raises(sos.SourceRefused, match="Biz Model"):
        sos.stack_sources(seed, tmp_path)


def test_a_radio_format_is_never_read_as_frequency(tmp_path):
    seed = _plant(tmp_path, {"mme": {"file": "m.csv", "columns": {
        "name": "Publication", "medium_raw": "Medium", "frequency_raw": "Print"},
        "frequency_when": {"medium_raw": ["Newspaper"]}}}, {"m.csv": MME})
    out = sos.stack_sources(seed, tmp_path).set_index("name")
    assert out.loc["The Weekly Paper", "frequency"] == "weekly"
    assert pd.isna(out.loc["WXYZ", "frequency"])
    assert pd.isna(out.loc["WXYZ", "frequency_raw"])
    assert "Country" in out.loc["WXYZ", "frequency_note"]


def test_an_unlisted_frequency_stays_unmapped_and_says_so(tmp_path):
    seed = _plant(tmp_path, {"mme": {"file": "m.csv", "columns": {
        "name": "Publication", "frequency_raw": "Print"}}}, {"m.csv": MME})
    out = sos.stack_sources(seed, tmp_path).set_index("name")
    assert "in no cycle" in out.loc["Twice Times", "frequency_note"]
    assert out.loc["Twice Times", "frequency_raw"] == "2 Monthly"


def test_language_is_never_defaulted(tmp_path):
    seed = _plant(tmp_path, {"mme": {"file": "m.csv", "columns": {"name": "Publication"}}},
                  {"m.csv": MME})
    out = sos.stack_sources(seed, tmp_path)
    assert out["language_raw"].isna().all()


def test_one_raw_value_in_two_cycles_refuses_the_seed(tmp_path):
    seed = _plant(tmp_path, {"mme": {"file": "m.csv", "columns": {"name": "Publication"}}},
                  {"m.csv": MME}, vocabulary={"daily": ["Daily"], "weekly": ["Daily"]})
    with pytest.raises(sos.SourceRefused, match="both"):
        sos.load_seed(seed)


def test_every_row_names_its_source_and_line(tmp_path):
    seed = _plant(tmp_path, {
        "easton": {"file": "e.csv", "columns": {"name": "Name"}},
        "mme": {"file": "m.csv", "columns": {"name": "Publication"}}},
        {"e.csv": EASTON, "m.csv": MME})
    out = sos.stack_sources(seed, tmp_path)
    assert set(out["source"]) == {"easton", "mme"}
    assert out["source_line"].notna().all()


def test_the_repo_seed_loads_and_names_no_aggregated_signals():
    declared = sos.load_seed(ROOT / sos.SEED)
    assert "aggregated_signals" not in declared["sources"]
    assert declared["sources"]["easton"]["never_read"]


def test_a_county_outside_the_list_is_flagged_and_kept(tmp_path):
    (tmp_path / "c.csv").write_text("Outlet Name,Outlet County\nBoothbay Register,Cook\n"
                                    "Lincoln News,Penobscot County\n")
    seed = tmp_path / "seed.yml"
    seed.write_text(yaml.safe_dump({"counties": ["Penobscot"], "sources": {"cision": {
        "file": "c.csv", "columns": {"name": "Outlet Name",
                                     "office_county": "Outlet County"}}}}))
    out = sos.stack_sources(seed, tmp_path).set_index("name")
    assert out.loc["Boothbay Register", "office_county"] == "Cook"
    assert "not a county" in out.loc["Boothbay Register", "location_note"]
    assert pd.isna(out.loc["Lincoln News", "location_note"])


def test_the_repo_seed_never_reads_coverage_as_a_town():
    declared = sos.load_seed(ROOT / sos.SEED)
    assert declared["sources"]["easton"]["columns"]["served_raw"] == "Communities served"
    assert len(declared["counties"]) == 16


def test_the_runs_inputs_must_match_the_declaration(tmp_path):
    (tmp_path / "m.csv").write_text(MME)
    declared = sos.check_declaration({"sources": {
        "mme": {"columns": {"name": "Publication"}},
        "lnc": {"columns": {"name": "Publication"}}}})
    with pytest.raises(sos.SourceRefused, match="declared with no input: lnc"):
        sos.stack_from(declared, {"mme": tmp_path / "m.csv"})
    with pytest.raises(sos.SourceRefused, match="input with no declaration: extra"):
        sos.stack_from(declared, {"mme": tmp_path / "m.csv", "lnc": tmp_path / "m.csv",
                                  "extra": tmp_path / "m.csv"})


def test_the_receipt_names_its_key():
    meta = sos.output_metadata(sos.pd.DataFrame(columns=list(sos.COLUMNS)))
    assert meta["id_fields"] == ["source", "source_line"]
    assert meta["spatial_unit"] == "outlet_record"
