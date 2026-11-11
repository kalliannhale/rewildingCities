"""
tests/test_open_ended_medians.py

ACS-7, the declaration and the Python half. A median the Census places in an
open-ended category arrives as 9 or 51 with -333333333 on its margin. The
registry declares where the end categories begin; preview.derive writes the
bound in words, marks the margin open_ended, and since D-105 leaves the value
empty, so the encoding is never ranked as a measurement. The R half is held to the same
strings by tests/test_derive_indicator_oracle.py.

Runs without R, pyarrow or network.
"""

from pathlib import Path

import pandas as pd
import pytest

from canopy.indicators import IndicatorRegistry
from canopy.indicators import preview as ip

GEOID = "us_census_geoid"

SEEDS = Path(__file__).resolve().parents[1] / "seeds" / "indicators"

MINIMAL = """
indicators:
  test_median:
    name: test median
    defined_by: test
    measures: test_median
    role: barrier
    rests_on: {{not_published: a test fixture}}
    unit: percent
    derivation:
      kind: passthrough
      column: B25071_001E
{extra}
    direction: higher_is_worse
    aggregation: none
    uncertainty: acs_moe
    source: {{provider: census_acs, dataset: acs/acs5}}
"""


def _registry(tmp_path, extra: str) -> IndicatorRegistry:
    (tmp_path / "t.yml").write_text(MINIMAL.format(extra=extra))
    return IndicatorRegistry.load(tmp_path)


def test_rent_burden_declares_its_edges():
    reg = IndicatorRegistry.load(SEEDS)
    assert reg.get("cii_rent_burden").derivation.open_ended == (10.0, 50.0)
    assert reg.declaration("cii_rent_burden")["derivation"]["open_ended"] == {
        "lower": 10.0, "upper": 50.0}


def test_no_edges_means_no_open_ended_key(tmp_path):
    reg = _registry(tmp_path, "")
    assert reg.get("test_median").derivation.open_ended is None
    assert "open_ended" not in reg.declaration("test_median")["derivation"]


@pytest.mark.parametrize("extra", [
    "      open_ended: {lower: 50, upper: 10}",
    "      open_ended: {lower: 10}",
    "      open_ended: {lower: 10, upper: 50, middle: 30}",
    "      open_ended: [10, 50]",
    "      open_ended: {lower: ten, upper: 50}",
])
def test_malformed_edges_are_refused(tmp_path, extra):
    with pytest.raises(ValueError, match="open_ended"):
        _registry(tmp_path, extra)


def test_a_ratio_cannot_declare_edges(tmp_path):
    ratio = MINIMAL.replace(
        "      kind: passthrough\n      column: B25071_001E\n",
        "      kind: ratio\n      numerator: [B25071_001E]\n"
        "      denominator: B25071_002E\n      scale: 100\n")
    (tmp_path / "t.yml").write_text(ratio.format(extra="      open_ended: {lower: 10, upper: 50}"))
    with pytest.raises(ValueError, match="unknown derivation field"):
        IndicatorRegistry.load(tmp_path)


def _frame(with_annotation=True):
    f = pd.DataFrame({
        "GEOID": ["13141", "48033", "23005", "99001", "99002"],
        "NAME": ["Hancock GA", "Borden TX", "Cumberland ME", "inside", "empty"],
        "B25071_001E": [51.0, 9.0, 29.4, 30.0, None],
        "B25071_001M": [None, None, 1.2, None, None],
        # what rent burden rests on (Sprint 02): B25070 total less not computed
        "B25070_001E": [120.0, 40.0, 30000.0, 500.0, 0.0],
        "B25070_011E": [20.0, 4.0, 1500.0, 0.0, 0.0],
    })
    if with_annotation:
        # stored the ways the code can arrive: text, text with a decimal, and none
        f["B25071_001M_annotation"] = ["-333333333", "-333333333.0", None,
                                       "-333333333", "-666666666"]
    return f


def test_open_ended_medians_become_bounds():
    ind = IndicatorRegistry.load(SEEDS).get("cii_rent_burden")
    rows, notes = ip.derive(_frame(), ind, unit_authority=GEOID, published_by=None, time=None)
    by = {r["unit"]["code"]: r for r in rows}

    assert by["13141"]["bound"] == "50.0 or more"
    assert by["48033"]["bound"] == "less than 10.0"
    for code in ("13141", "48033"):
        assert by[code]["moe_status"] == "open_ended"
        # D-105: the encoding is not a measurement, so the value rests empty
        # and says why, with the bound in the reason
        assert by[code]["value"] is None
        assert by[code]["empty_reason"] == f"open-ended median: {by[code]['bound']}"

    # an ordinary median is untouched
    assert by["23005"]["bound"] is None and by["23005"]["moe_status"] == "published"

    # an empty value stays empty, whatever its annotation
    assert by["99002"]["value"] is None and by["99002"]["bound"] is None
    assert by["99002"]["moe_status"] == "absent"

    # a code that contradicts the declared edges is labelled and reported, not hidden
    assert by["99001"]["bound"].startswith("open-ended interval")
    assert any("could not be placed" in n for n in notes)


def test_without_the_annotation_column_the_edges_cannot_be_used():
    ind = IndicatorRegistry.load(SEEDS).get("cii_rent_burden")
    rows, notes = ip.derive(_frame(with_annotation=False), ind, unit_authority=GEOID, published_by=None, time=None)
    assert all(r["bound"] is None for r in rows)
    assert all(r["moe_status"] != "open_ended" for r in rows)
    assert any("re-acquire" in n for n in notes)
