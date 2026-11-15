"""the maine_outlet_carriers preparation agrees with its method, registry,
crosswalks and indicator (Sprint 06, step 3, the fifth carrier; D-241 to
D-246). an outlet is placed by town, so it is counted at town, county and
state only, and loam's carriers view leaves its table out by name."""

from pathlib import Path

import yaml

from canopy.loam.graph import _drawable
from canopy.orchestrator.parsing import parse_experiment

ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "plots" / "maine" / "preparations" / "maine_outlet_carriers.yml"
METHOD = ROOT / "garden" / "methods" / "information" / "outlet_carriers.yml"
REGISTRY = ROOT / "soil" / "_registry.yml"
CROSSWALKS = ROOT / "seeds" / "crosswalks"


def _steps():
    return {s.id: s for s in parse_experiment(PREP).steps}


def _reg():
    return yaml.safe_load(REGISTRY.read_text())["primitives"]


def test_the_steps_run_in_order_under_their_own_ids():
    assert list(_steps()) == ["carriers_stack", "carriers_groups", "carriers_outlets",
                              "carriers_located_in", "carriers_counts"]
    other = yaml.safe_load((ROOT / "plots" / "maine" / "preparations" / "maine_outlets.yml")
                           .read_text())["steps"]
    assert not {s["id"] for s in other} & set(_steps())


def test_both_choices_are_declared_in_the_method_and_made_in_the_run():
    method = yaml.safe_load(METHOD.read_text())
    assert set(method["choices"]["town_fallback"]["options"]) == {"none", "office_town"}
    assert method["choices"]["town_fallback"]["default"] == "none"
    assert set(method["choices"]["ceased_outlets"]["options"]) == {"listed", "counted"}
    assert yaml.safe_load(PREP.read_text())["choices"] == {
        "town_fallback": "office_town", "ceased_outlets": "listed"}
    p = _steps()["carriers_outlets"].params
    assert p["town_fallback"] == "$choices.town_fallback"
    assert p["ceased_outlets"] == "$choices.ceased_outlets"


def test_every_reading_comes_from_a_shared_crosswalk():
    p = _steps()["carriers_outlets"].params
    assert p["sources"] == "$crosswalks.outlet_sources"
    assert p["names"] == "$crosswalks.census_name_suffixes"
    assert p["reviews"] == "$crosswalks.outlet_reviews"
    assert _steps()["carriers_stack"].params["declaration"] == "$crosswalks.outlet_sources"
    for name in ("outlet_sources", "census_name_suffixes", "outlet_reviews"):
        assert len(list(CROSSWALKS.rglob(f"{name}.yml"))) == 1, name


def test_the_declaration_orders_every_source_and_says_what_a_status_means():
    doc = yaml.safe_load((CROSSWALKS / "outlets" / "outlet_sources.yml").read_text())
    assert set(doc["source_order"]) == set(doc["sources"])
    assert doc["source_order"][:2] == ["local_news_catalyst", "maine_media_ecosystem"]
    v = doc["operating_vocabulary"]
    assert v["operating"] == ["yes"] and v["ceased"] == ["Ceased Operations"]
    assert v["last_post_prefix"] == "Last post"


def test_reviews_start_empty_and_keyed_by_the_words():
    doc = yaml.safe_load((CROSSWALKS / "outlets" / "outlet_reviews.yml").read_text())
    assert doc["merges"] == [] and doc["towns"] == []


def test_an_outlet_is_counted_at_town_county_and_state_only():
    p = _steps()["carriers_counts"].params
    assert p["levels"] == ["state", "county", "cousub"]
    assert "tribal_note" not in p
    assert p["indicator"] == "$indicators.news_outlets_per_1000"


def test_the_indicator_counts_the_outlets_type():
    doc = yaml.safe_load((ROOT / "seeds" / "indicators" / "news_outlets.yml").read_text())
    d = doc["indicators"]["news_outlets_per_1000"]["derivation"]
    assert d == {"kind": "located_count", "counts": "news_outlet",
                 "denominator": "persons", "scale": 1000}
    assert _steps()["carriers_outlets"].outputs == {"outlets": "news_outlet"}
    reg = _reg()["build_town_located_in"]
    (features,) = [i for i in reg["inputs"] if i["name"] == "features"]
    assert features["semantic_types"] == ["news_outlet"]


def test_the_graph_is_read_through_loam():
    for sid in ("carriers_outlets", "carriers_located_in"):
        assert _steps()[sid].inputs["places"] == "$loam.places"
    assert _steps()["carriers_counts"].inputs["spine"] == "$loam.block_spine"


def test_the_registry_declares_every_param_the_steps_write():
    reg = _reg()
    for sid, name in (("carriers_stack", "stack_outlet_sources"),
                      ("carriers_groups", "group_outlet_records"),
                      ("carriers_outlets", "prepare_news_outlets"),
                      ("carriers_located_in", "build_town_located_in"),
                      ("carriers_counts", "count_located")):
        assert set(_steps()[sid].params) <= set(reg[name]["params"]), name


def test_the_method_is_routed_and_the_type_declared():
    index = yaml.safe_load((ROOT / "garden" / "methods" / "index.yml").read_text())
    routes = {m["id"]: m["path"] for m in index["methods"]["information"]}
    assert routes["outlet_carriers"] == "information/outlet_carriers.yml"
    types = yaml.safe_load((ROOT / "seeds" / "schemas" / "domains" / "information.yml")
                           .read_text())["types"]
    assert types["news_outlet"]["category"] == "tabular"


def test_loam_draws_points_and_leaves_tables_out():
    assert _drawable(Path("x/clerk_offices_points_points.geojson"))
    assert not _drawable(Path("x/carriers_outlets_outlets.csv"))
    assert not _drawable(Path("x/layer.parquet"))
