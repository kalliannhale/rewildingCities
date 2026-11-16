"""
tests/test_section203.py
the Section 203 public use file read as published (D-263, D-264).
fixtures are written in the release's own shape: a zip holding a cp1252 CSV.
"""
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "prepare_section203", ROOT / "soil" / "transform" / "prepare_section203.py")
s203 = importlib.util.module_from_spec(spec)
sys.modules["prepare_section203"] = s203
spec.loader.exec_module(s203)

READING = yaml.safe_load(
    (ROOT / "seeds" / "crosswalks" / "voting" / "section203_puf_2021.yml").read_text())
COLS = READING["columns"]


def _row(**k):
    base = {c: "" for c in COLS}
    base.update({"AIAN": "0000", "ANRC": "00000", "CNTY": "000", "MCD": "NNNNN"})
    base.update(k)
    return base


ROWS = [
    _row(SUMLVL="010", LEVEL="Nation", ST="00", LANCOUNT="01", LANGUAGE="Total Population", ILLRAT="1.3200"),
    _row(SUMLVL="040", LEVEL="State", ST="23", NAMELSAD="Maine", LANCOUNT="02", LANGUAGE="Hispanic",
         VACLEP="900", MVACLEP="120", LEPPCT="0.0900", FLAG5="0", FLAG_EDU="0", FLAG_COV="0"),
    _row(SUMLVL="060", LEVEL="MCD", ST="23", MCD="02060", NAMELSAD="Augusta city", LANCOUNT="02",
         LANGUAGE="Hispanic", FLAG10="0", FLAG5="0", FLAG_COV="0"),
    _row(SUMLVL="271", LEVEL="AIAN/MCD", ST="23", MCD="61525", AIAN="2760",
         NAMELSAD="Penobscot Reservation and Off-Reservation Trust Land", LANCOUNT="45",
         LANGUAGE="All other American Indian Tribes alone or in combination", VACLEP="40"),
    _row(SUMLVL="250", LEVEL="AIAN", ST="00", AIAN="2760",
         NAMELSAD="Penobscot Reservation and Off-Reservation Trust Land", LANCOUNT="03",
         LANGUAGE="American Indian alone or in combination", VACIT="472", MVACIT="0"),
    _row(SUMLVL="060", LEVEL="MCD", ST="06", MCD="99999", NAMELSAD="Espa\u00f1ola", LANCOUNT="02",
         LANGUAGE="Hispanic"),
]
TOWNS = pd.DataFrame({"GEOID": ["2301102060", "2301961525", "2302999999"],
                      "NAME": ["Augusta city", "Indian Island", "Elsewhere"]})


def _zip(tmp_path, rows=ROWS, header=COLS, encoding="cp1252"):
    buf = io.StringIO()
    buf.write(",".join(header) + "\n")
    for r in rows:
        buf.write(",".join(f'"{r[c]}"' if r[c] else "" for c in header) + "\n")
    path = tmp_path / "puf.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("sect203_All_Areas.csv", buf.getvalue().encode(encoding))
    return path


def _read(tmp_path, **kw):
    rows = s203.read_member(str(_zip(tmp_path, **kw)), "sect203_All_Areas.csv", "cp1252")
    s203.check_header(rows, READING)
    return s203.records_from(rows, s203.town_codes(TOWNS, "23"), "23", READING)


def test_the_release_is_read_in_its_declared_encoding(tmp_path):
    with pytest.raises(s203.Section203Refused, match="not utf-8"):
        s203.read_member(str(_zip(tmp_path)), "sect203_All_Areas.csv", "utf-8")


def test_a_town_row_is_named_by_our_town_code(tmp_path):
    records, meta = _read(tmp_path)
    towns = [r for r in records if r["level"] == "town"]
    assert [t["unit_code"] for t in towns] == ["2301102060"]
    assert meta["towns_matched"] == 1


def test_our_towns_without_a_record_are_listed_by_name(tmp_path):
    _, meta = _read(tmp_path)
    assert {t["geoid"] for t in meta["towns_without_record"]} == {"2301961525", "2302999999"}


def test_an_aian_mcd_row_is_never_a_towns_value(tmp_path):
    records, meta = _read(tmp_path)
    assert not [r for r in records if r["unit_code"] == "2301961525"]
    assert meta["tribal_area_town_overlaps"] == [{"aian": "2760", "town": "2301961525"}]


def test_an_aian_area_keeps_its_own_code_under_its_own_authority(tmp_path):
    records, _ = _read(tmp_path)
    area = [r for r in records if r["level"] == "tribal_area"]
    assert [(a["unit_authority"], a["unit_code"]) for a in area] == [("census_s203_aian_area", "2760")]


def test_flags_are_copied_and_both_illiteracy_rates_are_kept(tmp_path):
    records, meta = _read(tmp_path)
    state = [r for r in records if r["level"] == "state"][0]
    assert (state["flag5"], state["flag_cov"], state["flag10"]) == ("0", "0", None)
    assert meta["national_illiteracy_rate_in_file"] == 1.32
    assert meta["national_illiteracy_rate_documented"] == 1.31


def test_a_town_split_at_a_county_line_is_held_whole_and_attached_to_no_piece(tmp_path):
    """D-267: Census writes Penobscot Indian Island Reservation (57936) once;
    we hold it in two county pieces. its row is the whole town's."""
    rows = ROWS + [_row(SUMLVL="060", LEVEL="MCD", ST="23", MCD="57936",
                        NAMELSAD="Penobscot Indian Island Reservation", LANCOUNT="02",
                        LANGUAGE="Hispanic")]
    towns = pd.concat([TOWNS, pd.DataFrame({"GEOID": ["2300357936", "2301957936"],
                                            "NAME": ["piece a", "piece b"]})])
    raw = s203.read_member(str(_zip(tmp_path, rows=rows)), "sect203_All_Areas.csv", "cp1252")
    records, meta = s203.records_from(raw, s203.town_codes(towns, "23"), "23", READING)
    held = [r for r in records if r["level"] == "split_town"]
    assert [(h["unit_authority"], h["unit_code"]) for h in held] == [("census_s203_mcd", "2357936")]
    assert not [r for r in records if r["unit_code"] in ("2300357936", "2301957936")]
    assert meta["split_towns_held_whole"] == [
        {"census_code": "2357936", "pieces": ["2300357936", "2301957936"]}]


def test_a_census_town_matching_none_of_ours_is_held_whole_and_listed(tmp_path):
    """D-267: the file's towns are of an older vintage; one since
    deorganized is held under its Census code, attached to none of ours."""
    rows = ROWS + [_row(SUMLVL="060", LEVEL="MCD", ST="23", MCD="01920", NAMELSAD="Atkinson town",
                        LANCOUNT="02", LANGUAGE="Hispanic")]
    records, meta = _read(tmp_path, rows=rows)
    held = [r for r in records if r["level"] == "census_town_not_ours"]
    assert [(h["unit_authority"], h["unit_code"]) for h in held] == [("census_s203_mcd", "2301920")]
    assert meta["census_towns_not_ours"] == [{"census_code": "2301920", "name": "Atkinson town"}]


def test_an_undeclared_lancount_is_refused(tmp_path):
    rows = ROWS + [_row(SUMLVL="040", LEVEL="State", ST="23", LANCOUNT="55", LANGUAGE="x")]
    with pytest.raises(s203.Section203Refused, match="not declared"):
        _read(tmp_path, rows=rows)


def test_a_header_unlike_the_declared_one_is_refused(tmp_path):
    with pytest.raises(s203.Section203Refused, match="header"):
        _read(tmp_path, header=COLS[:-1])
