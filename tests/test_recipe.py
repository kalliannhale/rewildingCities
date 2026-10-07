"""
tests/test_recipe.py

a method's recipe, filled at compose time from the question and the ground
(D-67). binding refuses a choice it would otherwise make; an indicator the
source cannot serve becomes a note naming who can; nothing compose-time leaks
into the experiment the orchestrator will run.
"""

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from canopy.wonder import recipe as R

ROOT = Path(__file__).resolve().parents[1]


class Reg:
    def __init__(self, inds): self.inds = inds
    def get(self, i):
        if i not in self.inds: raise KeyError(i)
        return self.inds[i]


def ind(iid, dataset=None, by="x"):
    return SimpleNamespace(id=iid, source={"dataset": dataset} if dataset else {}, defined_by=by)


REG = Reg({"a_acs": ind("a_acs"), "a_pub": ind("a_pub", dataset="pub")})
DATASETS = {
    "acs": {"semantic_type": "indicator_source", "source": {"indicators": ["a_acs"]},
            "provenance": {"authority": "us_census_acs"}},
    "pub": {"semantic_type": "indicator_source", "source": {"unit_column": "FIPS", "unit_pad": 5},
            "temporal": {"label": "2026 edition"}, "provenance": {"authority": "publisher"}},
    "pts": {"semantic_type": "unit_locations"},
}
METHOD = {"id": "m",
          "requires_data": [{"name": "source", "semantic_types": ["indicator_source"]},
                            {"name": "locations", "semantic_types": ["unit_locations"]}],
          "recipe": [{"id": "derive", "primitive": "roots/derive_indicator",
                      "inputs": {"source": "$requires.source", "where": "$requires.locations"},
                      "outputs": {"values": "indicator_values"},
                      "params": {"indicators": "$curiosity.indicated_by", "sd": "$choices.sd",
                                 "time": "$source.vintage", "pad": "$source.unit_pad",
                                 "list": ["$curiosity.indicated_by", "$indicators.extra"]}}]}
CUR = {"id": "c", "sub_questions": {"q": {"question": "?", "indicated_by": ["a_acs", "a_pub"]},
                                    "r": {"question": "?", "indicated_by": ["a_pub"]}}}


def test_one_candidate_binds_and_none_is_left_visibly_missing():
    b = R.bind_requirements(METHOD, {"acs": DATASETS["acs"]})
    assert b == {"source": "acs", "locations": None}


def test_two_candidates_are_a_choice():
    with pytest.raises(R.ComposeRefusal, match="choice, not a lookup"):
        R.bind_requirements(METHOD, DATASETS)
    assert R.bind_requirements(METHOD, DATASETS, {"source": "pub"})["source"] == "pub"


def test_a_chosen_dataset_must_be_able_to_serve():
    with pytest.raises(R.ComposeRefusal, match="cannot serve"):
        R.bind_requirements(METHOD, DATASETS, {"source": "pts"})


def test_the_source_filters_what_it_can_serve_and_names_the_rest():
    r = R.compose_recipe(METHOD, CUR, "q", DATASETS, REG, chosen_datasets={"source": "acs"})
    p = r.steps[0]["params"]
    assert p["indicators"] == ["$indicators.a_acs"]
    assert any("a_pub" in n and "served by pub" in n for n in r.notes)


def test_compose_time_references_resolve_and_runtime_ones_pass_through():
    r = R.compose_recipe(METHOD, CUR, "q", DATASETS, REG, chosen_datasets={"source": "pub"})
    s = r.steps[0]
    assert s["inputs"] == {"source": "$manifest.pub", "where": "$manifest.pts"}
    assert s["params"]["sd"] == "$choices.sd"
    assert s["params"]["time"] == "2026 edition" and s["params"]["pad"] == 5
    assert s["params"]["list"] == ["$indicators.a_pub", "$indicators.extra"]


def test_a_null_source_fact_is_left_out_not_written_as_null():
    r = R.compose_recipe(METHOD, CUR, "q", DATASETS, REG, chosen_datasets={"source": "acs"})
    assert "pad" not in r.steps[0]["params"]


def test_no_sub_question_takes_every_indicator_in_order():
    assert R.indicated(CUR, None) == ["a_acs", "a_pub"]
    with pytest.raises(R.ComposeRefusal, match="no sub-question"):
        R.indicated(CUR, "nope")


def test_nothing_servable_is_refused_with_who_could():
    with pytest.raises(R.ComposeRefusal, match="served by pub"):
        R.compose_recipe(METHOD, CUR, "r", DATASETS, REG, chosen_datasets={"source": "acs"})


def test_an_unknown_compose_reference_is_refused():
    m = dict(METHOD, recipe=[{"id": "x", "params": {"a": "$source.colour"}}])
    with pytest.raises(R.ComposeRefusal, match="known source facts"):
        R.compose_recipe(m, CUR, "q", DATASETS, REG, chosen_datasets={"source": "acs"})


def test_a_weighting_expands_to_its_components_in_order():
    m = dict(METHOD, recipe=[{"id": "x", "params": {"i": "$weighting.w.components"}}])
    w = {"pillars": {"p1": {"components": {"a_acs": 10, "a_pub": 10}},
                     "p2": {"components": {"a_pub": 10, "z": 10}}}}
    r = R.compose_recipe(m, {"id": "c", "sub_questions": {}}, None, DATASETS, REG,
                         weights_loader=lambda wid: w, chosen_datasets={"source": "acs"})
    assert r.steps[0]["params"]["i"] == ["$indicators.a_acs", "$indicators.a_pub", "$indicators.z"]


@pytest.fixture
def garden(tmp_path):
    """a copy of the real seeds, curiosities and methods, and a plot whose
    manifest holds two indicator sources."""
    for d in ("seeds/indicators", "seeds/weights", "garden/curiosity-space", "garden/methods"):
        shutil.copytree(ROOT / d, tmp_path / d)
    (tmp_path / "plots" / "maine").mkdir(parents=True)
    (tmp_path / "plots" / "maine" / "manifest.yml").write_text(yaml.safe_dump({"datasets": {
        "acs_county_2024": {"semantic_type": "indicator_source", "provenance": {"authority": "us_census_acs"},
                            "source": {"provider": "census_acs", "dataset": "acs/acs5", "year": 2024,
                                       "indicators": ["cii_broadband"]}},
        "cii_2026_published": {"semantic_type": "indicator_source", "temporal": {"label": "CII 2026 edition"},
                               "provenance": {"authority": "civic_information_index"},
                               "source": {"type": "manual", "unit_column": "FIPS", "unit_pad": 5, "name_column": "Name"}},
    }}))
    return tmp_path


class Loam:
    def find(self, **k): return []


def test_compose_writes_a_complete_experiment_for_each_authority(garden):
    from canopy.wonder.wondering import compose
    with pytest.raises(R.ComposeRefusal):
        compose(Loam(), "maine", "broadband_access", "cii_indicator_values",
                sub_question="subscription", root=garden, write=False)
    acs = compose(Loam(), "maine", "broadband_access", "cii_indicator_values", sub_question="subscription",
                  chosen={"datasets": {"source": "acs_county_2024"}}, root=garden, write=False)
    pub = compose(Loam(), "maine", "broadband_access", "cii_indicator_values", sub_question="subscription",
                  chosen={"datasets": {"source": "cii_2026_published"}}, root=garden, write=False)
    assert acs.experiment["steps"][0]["params"]["indicators"] == ["$indicators.cii_broadband"]
    assert pub.experiment["steps"][0]["params"]["indicators"] == ["$indicators.cii_pub_broadband"]
    assert pub.experiment["steps"][0]["params"]["unit_column"] == "FIPS"
    assert acs.experiment["curiosity"]["ref"] == "$curiosity-space/information/broadband_access"
    assert any("cii_pub_broadband" in d for d in acs.guidance.decisions)
    text = yaml.safe_dump(acs.experiment) + yaml.safe_dump(pub.experiment)
    for ref in ("$requires.", "$curiosity.", "$source.", "$weighting."):
        assert ref not in text
