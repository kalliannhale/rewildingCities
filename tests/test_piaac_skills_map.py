"""
tests/test_piaac_skills_map.py
literacy from the PIAAC Skills Map workbook (D-265).
"""
import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "prepare_piaac_skills_map", ROOT / "soil" / "transform" / "prepare_piaac_skills_map.py")
pm = importlib.util.module_from_spec(spec)
sys.modules["prepare_piaac_skills_map"] = pm
spec.loader.exec_module(pm)

READING = yaml.safe_load(
    (ROOT / "seeds" / "crosswalks" / "literacy" / "piaac_skills_map.yml").read_text())


def _sheets(**county_over):
    county = pd.DataFrame({
        "FIPS_code": [23001, 23001, 6037], "State": ["Maine", "Maine", "California"],
        "County": ["Androscoggin County", "Androscoggin County", "Los Angeles County"],
        "grpName": ["all", "16_24", "all"], "Lit_P1": [0.164, 0.2, 0.343],
        "Lit_P1_CI_L": [0.125, 0.1, 0.311], "Lit_P1_CI_U": [0.205, 0.3, 0.376],
        "Lit_P1_CV": [0.12, 0.2, 0.05], "Lit_P1_indicator": [None, None, None],
        "Lit_P1_CI_L_indicator": [None, None, None], "Lit_P1_CI_U_indicator": [None, None, None],
        "Lit_P1_CV_indicator": [None, None, None], "POP_DOMAIN": [78820.0, 9000.0, 7548080.0]})
    for k, v in county_over.items():
        county[k] = v
    state = pd.DataFrame({
        "FIPS_code": [23], "State": ["Maine"], "grpName": ["all"], "Lit_P1": [0.14],
        "Lit_P1_CI_L": [0.11], "Lit_P1_CI_U": [0.17], "Lit_P1_CV": [0.1],
        "Lit_P1_CI_L_indicator": [None], "Lit_P1_CV_indicator": [None], "POP_DOMAIN": [990000.0]})
    return {"County": county, "State": state}


def test_only_the_state_and_its_counties_for_the_declared_group():
    rows = pm.rows_from(_sheets(), "23", READING)
    assert [(r["level"], r["unit_code"]) for r in rows] == [("county", "23001"), ("state", "23")]


def test_left_out_follows_the_user_guides_recipe():
    """population times the share and each bound (NCES SAE user guide)."""
    r = pm.rows_from(_sheets(), "23", READING)[0]
    assert r["left_out"] == 78820.0 * 0.164
    assert (r["left_out_lower"], r["left_out_upper"]) == (78820.0 * 0.125, 78820.0 * 0.205)
    assert r["confidence"] == 0.95


def test_flags_are_decoded_in_the_variable_lists_words():
    rows = pm.rows_from(_sheets(Lit_P1_CV_indicator=[1.0, None, None]), "23", READING)
    assert rows[0]["cv_flag"] == "coefficient of variation 0.3 to 0.5"


def test_an_undefined_flag_code_is_refused():
    with pytest.raises(pm.SkillsMapRefused, match="does not define"):
        pm.rows_from(_sheets(Lit_P1_indicator=[7.0, None, None]), "23", READING)


def test_a_share_without_both_bounds_is_refused():
    with pytest.raises(pm.SkillsMapRefused, match="without both bounds"):
        pm.rows_from(_sheets(Lit_P1_CI_U=[None, 0.3, 0.376]), "23", READING)


def test_a_declared_column_the_sheet_lacks_is_refused_by_name():
    s = _sheets()
    s["State"] = s["State"].drop(columns=["POP_DOMAIN"])
    with pytest.raises(pm.SkillsMapRefused, match="POP_DOMAIN"):
        pm.rows_from(s, "23", READING)


def test_no_index_or_model_takes_literacy_as_an_input():
    """D-265: never combined with its own predictors. no roots primitive
    accepts literacy_estimates and no weighting names it."""
    texts = [(ROOT / "roots" / "_registry.yml").read_text()]
    texts += [p.read_text() for p in (ROOT / "seeds" / "weights").glob("*.yml")]
    assert not any("literacy_estimates" in t for t in texts)


def test_the_estimates_say_what_they_are_modelled_from():
    assert any("Black and of Hispanic" in n for n in pm.NOTES)
