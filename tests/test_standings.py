"""
tests/test_standings.py

where a unit stands among a declared reference population: CII's percentile
(average rank over the largest rank), an oriented z-score, and the refusals.
"""

import math
from pathlib import Path

import pytest

from canopy.indicators import preview as ip
from canopy.indicators import IndicatorRegistry

SEEDS = Path(__file__).resolve().parents[1] / "seeds" / "indicators"
REG = IndicatorRegistry.load(SEEDS)


def rows(values, codes=None):
    codes = codes or [f"23{i:03d}" for i in range(len(values))]
    return [{"unit": {"code": c}, "name": c, "value": v} for c, v in zip(codes, values)]


def pct(out):
    return [r["percentile"] for r in out]


def test_ties_share_their_average_rank():
    assert ip._average_ranks([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]


def test_a_tied_top_still_reaches_100():
    """CII-8: divide by the largest rank, not n. ten counties at 0% without a
    vehicle all stand at 100, which rank / n would put at 99.86."""
    out, _ = ip.standings(rows([0.0, 0.0, 5.0, 9.0]), REG.get("cii_no_vehicle"), sd="sample")
    assert pct(out)[:2] == [100.0, 100.0]


def test_higher_is_worse_is_reversed():
    worse, _ = ip.standings(rows([10.0, 20.0, 30.0]), REG.get("cii_rent_burden"), sd="sample")
    better, _ = ip.standings(rows([10.0, 20.0, 30.0]), REG.get("cii_broadband"), sd="sample")
    # written in the rule's own order, rank / top * 100, because 2 / 3 * 100
    # and 200 / 3 differ in the last bit, and the rule is exact.
    assert pct(worse) == [3 / 3 * 100, 2 / 3 * 100, 1 / 3 * 100]
    assert pct(better) == [1 / 3 * 100, 2 / 3 * 100, 3 / 3 * 100]
    assert worse[0]["z"] > 0 and better[0]["z"] < 0


def test_z_is_standard_under_the_declared_convention():
    vals = [1.0, 2.0, 3.0, 4.0, 10.0]
    for sd, ddof in (("sample", 1), ("population", 0)):
        out, pop = ip.standings(rows(vals), REG.get("cii_broadband"), sd=sd)
        z = [r["z"] for r in out]
        assert abs(math.fsum(z)) < 1e-12
        var = math.fsum(v * v for v in z) / (len(z) - ddof)
        assert abs(var - 1) < 1e-12
        assert pop["sd"] == sd


def test_there_is_no_default_sd():
    with pytest.raises(ip.PreviewError):
        ip.standings(rows([1.0, 2.0]), REG.get("cii_broadband"), sd="")


def test_an_excluded_state_keeps_its_row_with_no_standing():
    out, pop = ip.standings(rows([50.0, 60.0, 70.0], ["23001", "23003", "72001"]),
                            REG.get("cii_broadband"), sd="sample", exclude_state_fips=("72",))
    assert pop["n"] == 2
    assert out[2]["percentile"] is None and out[2]["z"] is None
    assert "state 72 excluded" in out[2]["outside_reason"]
    assert pct(out)[:2] == [50.0, 100.0]


def test_an_empty_value_is_outside_the_population_not_ranked_last():
    out, pop = ip.standings(rows([50.0, None, 70.0]), REG.get("cii_broadband"), sd="sample")
    assert pop["n"] == 2
    assert out[1]["percentile"] is None and out[1]["outside_reason"] == "no value"


def test_no_variation_has_percentiles_but_no_z():
    out, _ = ip.standings(rows([34.9, 34.9, 34.9]), REG.get("cii_broadband"), sd="sample")
    assert all(r["z"] is None for r in out)
    assert all(r["percentile"] == 100.0 for r in out)
    assert out[0]["outside_reason"] == "no variation in the reference population"


def test_a_population_of_one_is_refused():
    with pytest.raises(ip.PreviewError):
        ip.standings(rows([50.0, None]), REG.get("cii_broadband"), sd="sample")


def test_cii_percentiles_reproduce_from_ciis_own_raw_values():
    """CII-8, guarded. runs only where the published file is present."""
    import pandas as pd
    f = Path(ip.REPO) / "garden" / "reference" / "cii_2026.csv"
    if not f.is_file():
        pytest.skip(f"no published file at {f}")
    d = pd.read_csv(f, dtype=str, keep_default_na=False)
    for iid in ("cii_broadband", "cii_rent_burden", "cii_no_vehicle"):
        ind = REG.get(iid)
        col = ind.replicates["column"]
        rs = [{"unit": {"code": ip.normalise_fips(c)}, "name": n, "value": ip._number(v)}
              for c, n, v in zip(d.FIPS, d.Name, d[col])]
        out, _ = ip.standings(rs, ind, sd="sample")
        pub = [ip._number(x) for x in d[f"{col} percentile"]]
        worst = max(abs(a["percentile"] - b) for a, b in zip(out, pub)
                    if a["percentile"] is not None and b is not None)
        assert worst < 1e-7, (iid, worst)


def test_restricting_to_the_publishers_units_leaves_the_rest_out_by_name():
    out, pop = ip.standings(rows([10.0, 20.0, 30.0], ["23001", "23003", "23005"]),
                            REG.get("cii_broadband"), sd="sample",
                            restrict_to={"23001", "23005"})
    assert pop["n"] == 2
    assert pop["left_out_by_restriction"] == ["23003"]
    assert out[1]["outside_reason"] == "outside the reference population (not ranked by the publisher)"
    assert pct(out) == [50.0, None, 100.0]