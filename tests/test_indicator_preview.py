"""
tests/test_indicator_preview.py

the preview derivation and the hand check, without a server or a network.
fixtures write CSV caches so the tests need neither pyarrow nor the Census.
"""

import math
import textwrap

import pytest

from canopy import indicator_preview as ip
from canopy.indicators import IndicatorRegistry


# ── fixtures ──────────────────────────────────────────────────────────────
HEADER = ("GEOID,NAME,state,county,"
          "B28002_004E,B28002_001E,B28002_004M,B28002_001M,"
          "B25071_001E,B25071_001M,"
          "B08201_002E,B08201_001E,B08201_002M,B08201_001M")

ROWS = [
    "23005,Cumberland County Maine,23,005,1000,1200,50,60,29.4,1.2,90,1200,15,60",
    "23029,Washington County Maine,23,029,500,600,40,30,,,30,600,9,30",
    "23999,Nowhere County Maine,23,999,0,0,0,0,31.0,2.0,0,0,0,0",
]


def manifest(sources: dict) -> str:
    blocks = []
    for name, (cache, inds) in sources.items():
        blocks.append(textwrap.dedent(f"""\
          {name}:
            available: true
            semantic_type: indicator_source
            format: csv
            source:
              type: api
              provider: census_acs
              dataset: acs/acs5
              year: 2024
              geography: county
              within:
                state: "23"
              indicators: [{", ".join(inds)}]
            cache:
              path: {cache}
            provenance:
              authority: us_census_acs
        """))
    body = "".join(textwrap.indent(b, "  ") for b in blocks)
    return f"city:\n  name: Test\n  id: test\ndatasets:\n{body}"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """a tiny repo: the real indicator seeds, one test plot, a CSV cache."""
    from pathlib import Path
    real_seeds = Path(ip.__file__).resolve().parents[1] / "seeds" / "indicators"
    monkeypatch.setattr(ip, "REPO", tmp_path)
    monkeypatch.setattr(ip, "INDICATORS_DIR", real_seeds)
    monkeypatch.setattr(ip, "PLOTS_DIR", tmp_path / "plots")
    plot = tmp_path / "plots" / "test"
    (plot / ".data").mkdir(parents=True)
    (plot / ".data" / "acs.csv").write_text("\n".join([HEADER, *ROWS]) + "\n")
    (plot / "manifest.yml").write_text(manifest({
        "acs_county_2024": (".data/acs.csv",
                            ["cii_broadband", "cii_rent_burden", "cii_no_vehicle"]),
    }))
    return plot


def by_code(p):
    return {r["unit"]["code"]: r for r in p["values"]}


# ── the registry entries ──────────────────────────────────────────────────
def test_new_entries_declare_what_they_are():
    reg = IndicatorRegistry.load(ip.INDICATORS_DIR)
    rent = reg.get("cii_rent_burden")
    assert rent.derivation.kind == "passthrough"
    assert rent.aggregation == "none"
    assert rent.acquisition_variables() == ["B25071_001E", "B25071_001M"]
    car = reg.get("cii_no_vehicle")
    assert car.direction == "higher_is_worse"
    assert car.acquisition_variables() == [
        "B08201_002E", "B08201_001E", "B08201_002M", "B08201_001M"]


def test_replicates_marks_exactly_the_verified_entries():
    """verified 2026-10-07: broadband, rent burden, no-vehicle, 16 of 16 each.
    limited English has no replicates until its HDPulse table is named."""
    reg = IndicatorRegistry.load(ip.INDICATORS_DIR)
    for i in ("cii_broadband", "cii_rent_burden", "cii_no_vehicle"):
        assert reg.get(i).replicates is not None, i
    assert reg.get("limited_english_households").replicates is None


# ── derivation ────────────────────────────────────────────────────────────
def test_ratio_is_exact_at_full_precision(repo):
    p = ip.preview("test", "cii_broadband")
    row = by_code(p)["23005"]
    assert row["value"] == (1000 / 1200) * 100
    assert row["method"] == "preview:ratio"
    assert row["time"] == "2020-2024 (5-year estimates)"
    assert row["authority"] == "us_census_acs"
    assert row["unit"] == {"authority": "us_census_geoid", "code": "23005"}


def test_every_response_says_it_is_a_preview(repo):
    p = ip.preview("test", "cii_broadband")
    assert p["status"] == "preview"
    assert p["envelope"] is None
    assert all(r["method"].startswith("preview:") for r in p["values"])


def test_ratio_margin_is_not_derived(repo):
    row = by_code(ip.preview("test", "cii_broadband"))["23005"]
    assert row["moe"] is None
    assert row["moe_status"] == "not_derived"
    assert row["components"]["B28002_004E"] == {"estimate": 1000.0, "moe": 50.0}


def test_zero_denominator_rests_empty_with_its_reason(repo):
    row = by_code(ip.preview("test", "cii_broadband"))["23999"]
    assert row["value"] is None
    assert row["empty_reason"] == "zero denominator"


def test_passthrough_serves_the_published_margin(repo):
    row = by_code(ip.preview("test", "cii_rent_burden"))["23005"]
    assert row["value"] == 29.4
    assert row["moe"] == 1.2
    assert row["moe_status"] == "published"


def test_empty_source_value_is_named_never_zero(repo):
    p = ip.preview("test", "cii_rent_burden")
    row = by_code(p)["23029"]
    assert row["value"] is None
    assert row["empty_reason"] == "source value empty: B25071_001E"
    assert p["n_empty"] == 1
    assert any("ACS-5" in n for n in p["notes"])


def test_geoid_stays_a_string(repo):
    codes = [r["unit"]["code"] for r in ip.preview("test", "cii_broadband")["values"]]
    assert codes == ["23005", "23029", "23999"]


# ── refusals ──────────────────────────────────────────────────────────────
def test_an_acquisition_missing_a_column_is_refused(repo):
    (repo / ".data" / "acs.csv").write_text(
        "GEOID,NAME,B28002_004E\n23005,Cumberland,1000\n")
    with pytest.raises(ip.PreviewError) as e:
        ip.preview("test", "cii_broadband")
    assert e.value.kind == "malformed"
    assert "B28002_001E" in e.value.message


@pytest.mark.parametrize("bad", ["../etc", "Maine", "", "a/b", ".hidden"])
def test_a_plot_name_is_never_a_path(repo, bad):
    with pytest.raises(ip.PreviewError) as e:
        ip.preview(bad, "cii_broadband")
    assert e.value.kind == "malformed"


def test_unknown_indicator(repo):
    with pytest.raises(ip.PreviewError) as e:
        ip.preview("test", "no_such_thing")
    assert e.value.kind == "not_found"


def test_indicator_no_source_lists(repo):
    with pytest.raises(ip.PreviewError) as e:
        ip.preview("test", "limited_english_households")
    assert e.value.kind == "not_found"


def test_declared_but_not_acquired(repo):
    (repo / ".data" / "acs.csv").unlink()
    with pytest.raises(ip.PreviewError) as e:
        ip.preview("test", "cii_broadband")
    assert e.value.kind == "unavailable"
    assert "acquire test --type indicator_source --fetch" in e.value.message


def test_two_sources_is_a_choice_not_a_lookup(repo):
    (repo / "manifest.yml").write_text(manifest({
        "acs_county_2023": (".data/acs.csv", ["cii_broadband"]),
        "acs_county_2024": (".data/acs.csv", ["cii_broadband"]),
    }))
    with pytest.raises(ip.PreviewError) as e:
        ip.preview("test", "cii_broadband")
    assert e.value.kind == "ambiguous"
    p = ip.preview("test", "cii_broadband", dataset="acs_county_2024")
    assert p["source"]["dataset"] == "acs_county_2024"


# ── plot summary ──────────────────────────────────────────────────────────
def test_plot_summary_names_what_is_and_is_not_here(repo):
    s = ip.plot_summary("test", ip.load_registry())
    assert s["derivable"] == ["cii_broadband", "cii_no_vehicle", "cii_rent_burden"]
    assert s["in_registry_not_declared_here"] == ["limited_english_households"]
    assert "_path" not in s["sources"][0]


# ── the hand check ────────────────────────────────────────────────────────
@pytest.mark.parametrize("raw, code", [
    ("23005", "23005"), (23005, "23005"), ("23005.0", "23005"),
    ("1001", "01001"), (1001.0, "01001"), ("", None), ("ME", None), ("123456", None),
])
def test_fips_normalisation(raw, code):
    assert ip.normalise_fips(raw) == code


def test_compare_reports_exact_agreement(repo, tmp_path):
    published = tmp_path / "cii.csv"
    published.write_text(
        "FIPS,Percent of households with broadband\n"
        f"23005,{(1000 / 1200) * 100!r}\n"
        f"23029,{(500 / 600) * 100!r}\n"
        "23999,\n"
        "1001,77.0\n")
    c = ip.compare("test", "cii_broadband", published, "FIPS")
    s = c["summary"]
    assert s["max_abs_difference"] == 0
    assert s["n_compared"] == 2
    assert s["n_published_in_scope"] == 3
    assert s["only_published"] == [] and s["only_ours"] == []
    assert c["check"].startswith("hand check")


def test_compare_needs_a_column_when_nothing_is_replicated(repo, tmp_path):
    published = tmp_path / "cii.csv"
    published.write_text("FIPS,Rent\n23005,29.4\n")
    with pytest.raises(ip.PreviewError) as e:
        ip.compare("test", "limited_english_households", published, "FIPS")
    assert e.value.kind == "malformed" and "--column" in e.value.message


def test_an_explicit_column_overrides_replicates(repo, tmp_path):
    published = tmp_path / "cii.csv"
    published.write_text("FIPS,Rent\n23005,29.4\n")
    c = ip.compare("test", "cii_rent_burden", published, "FIPS", column="Rent")
    assert c["published_column"] == "Rent"
    assert c["summary"]["max_abs_difference"] == 0


def test_precision_belongs_to_the_column_not_the_row(repo, tmp_path):
    """PRV-3: a spreadsheet writes 30.0 as 30. judged at that row's zero
    decimals, 29.4 would agree with 29; judged at the column's one, it does not."""
    published = tmp_path / "cii.csv"
    published.write_text(
        "FIPS,Percent of income spent on rent\n"
        "23005,29\n"
        "23999,31.0\n")
    c = ip.compare("test", "cii_rent_burden", published, "FIPS")
    rows = {r["geoid"]: r for r in c["rows"]}
    assert c["summary"]["column_precision"] == 1
    assert c["summary"]["written_decimals_observed"] == [0, 1]
    assert not rows["23005"]["agrees_at_published_precision"]
    assert rows["23999"]["agrees_at_published_precision"]


def test_correlation_refuses_rather_than_returning_nan():
    assert ip._pearson([(1, 1), (2, 2)]) is None
    assert ip._pearson([(1, 5), (2, 5), (3, 5)]) is None
    assert math.isclose(ip._pearson([(1, 2), (2, 4), (3, 6)]), 1.0)


def test_agreement_is_judged_at_the_publisher_precision(repo, tmp_path):
    published = tmp_path / "cii.csv"
    published.write_text(
        "FIPS,Percent of households with broadband\n"
        "23005,83.3333333\n"
        "23029,83.3333\n"
        "23999,\n")
    c = ip.compare("test", "cii_broadband", published, "FIPS")
    rows = {r["geoid"]: r for r in c["rows"]}
    assert rows["23005"]["agrees_at_published_precision"]
    assert rows["23005"]["written_decimals"] == 7
    assert c["summary"]["column_precision"] == 7
    # written with four decimals in a seven-decimal column, so read as
    # 83.3333000, which ours (83.3333333...) is not. per-row precision called
    # this agreement; that was the PRV-3 looseness, encoded in this test.
    assert not rows["23029"]["agrees_at_published_precision"]
    assert c["summary"]["agree_at_published_precision"] == 1
    assert c["summary"]["max_abs_difference"] > 0


def test_a_real_difference_is_not_rounding(repo, tmp_path):
    published = tmp_path / "cii.csv"
    published.write_text(
        "FIPS,Percent of households with broadband\n"
        "23005,83.3334\n")
    row = ip.compare("test", "cii_broadband", published, "FIPS")["rows"][0]
    assert not row["agrees_at_published_precision"]


def test_the_registry_column_exists_in_the_published_header():
    """the replicates column must be a header the file actually has (L-69).

    skipped unless the published file is present at the path below.
    """
    from pathlib import Path
    f = Path(ip.REPO) / "garden" / "reference" / "cii_2026.csv"
    if not f.is_file():
        pytest.skip(f"no published file at {f}")
    import csv
    with open(f, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    reg = IndicatorRegistry.load(ip.INDICATORS_DIR)
    for i in reg.all():
        rep = reg.get(i).replicates
        if rep:
            assert rep["column"] in header, (i, rep["column"])  # exact, not substring


def test_a_missing_published_file_is_refused_by_name(repo, tmp_path):
    missing = tmp_path / "nowhere" / "cii.csv"
    with pytest.raises(ip.PreviewError) as e:
        ip.compare("test", "cii_broadband", missing, "FIPS")
    assert e.value.kind == "not_found"
    assert str(missing) in e.value.message