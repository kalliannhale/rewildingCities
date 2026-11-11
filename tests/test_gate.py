"""
tests/test_gate.py

Sprint 03: the one exposure gate (Contract 1). Every test from the tab:
an excluded type is refused, an undeclared type fails closed, a misspelled
tier is an error, every tier in the lineage binds (D-101), aggregate-only
never leaves as named points, custom needs a consent record, a missing
context note is refused, a license that forbids redistribution is refused at
public, and every refusal names its type, tier, ancestor and what would
admit it. Plus D-102's caveat and the loaders. No network, no R.
"""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from canopy.expose import decide, exposure_tier
from canopy.expose.records import load_consents, load_licenses

REPO = Path(__file__).resolve().parents[1]
LICENSES = load_licenses(REPO / "seeds" / "licenses")


class Vocab:
    """a stand-in vocabulary: name -> extra fields, as Vocabulary exposes them."""
    def __init__(self, types):
        self.types = types
    def knows_name(self, name):
        return name in self.types
    def get(self, name):
        return SimpleNamespace(extra=self.types[name])


VOCAB = Vocab({
    "indicator_source": {"resolution_tier": "public"},
    "indicator_values": {"resolution_tier": "public"},
    "relational_hub": {"resolution_tier": "aggregate-only"},
    "hub_counts": {"resolution_tier": "public", "aggregates": True},
    "sovereign_boundary": {"resolution_tier": "custom"},
    "flow_edges": {"resolution_tier": "excluded"},
    "tribal_area": {"resolution_tier": "public",
                    "required_context": [{"id": "census_tribal_area",
                                          "text": "The boundary is the Census Bureau's."}]},
    "untiered": {},
    "typo": {"resolution_tier": "publc"},
})

DATASETS = {
    "acs": {"semantic_type": "indicator_source", "license": "us_government_work",
            "cache": {"path": ".data/acs.parquet"}},
    "cii": {"semantic_type": "indicator_source", "license": "terms_unknown",
            "cache": {"path": ".data/cii.csv"}},
    "hubs": {"semantic_type": "relational_hub", "license": "us_government_work",
             "cache": {"path": ".data/hubs.geojson"}},
    "nolicense": {"semantic_type": "indicator_source", "cache": {"path": ".data/x.csv"}},
}


def envelope(own, inputs, *, datasets=("acs",), lineage=True, curiosity="$c", notes=()):
    lin = None
    if lineage:
        lin = {"kind": "experiment", "run": "r", "method": "$methods/m", "choices": {},
               "curiosity": curiosity,
               "data_resolution": {"datasets_available": list(datasets)}}
    return {"metadata": {"semantic_type": own, "data_category": "tabular",
                         "lineage": lin, "context_notes": list(notes)},
            "provenance": [{"primitive": "p", "lineage_branch": None,
                            "inputs": [{"name": n, "semantic_type": t, "path": f".data/{n}"}
                                       for n, t in inputs]}]}


def gate(env, *, level="public", consents=(), today=date(2026, 11, 10)):
    return decide(env, target="northeastern_agol", sharing_level=level, vocabulary=VOCAB,
                  plot="maine", manifest_datasets=DATASETS, licenses=LICENSES,
                  consents=list(consents), today=today)


def rules(result):
    return sorted(r["rule"] for r in result.get("refusals", []))


# ── the tab's tests ──────────────────────────────────────────────────────
def test_a_public_lineage_with_a_permitted_license_is_allowed():
    res = gate(envelope("indicator_values", [("source", "indicator_source")]))
    assert res["decision"] == "allow"
    rec = res["record"]
    assert [t["tier"] for t in rec["tiers"]] == ["public", "public"]
    assert rec["license"] == [{"dataset": "acs", "term": "us_government_work"}]
    assert rec["caveats"] == []


def test_an_excluded_type_is_refused_and_stops_everything():
    res = gate(envelope("indicator_values", [("edges", "flow_edges")]))
    assert res["decision"] == "refuse" and rules(res) == [3]
    assert "exists here and is withheld" in res["refusals"][0]["reason"]


def test_an_undeclared_type_fails_closed():
    res = gate(envelope("indicator_values", [("x", "untiered")]))
    assert rules(res) == [2]


def test_an_unknown_type_fails_closed():
    res = gate(envelope("indicator_values", [("x", "never_heard_of_it")]))
    assert rules(res) == [2]


def test_a_misspelled_tier_is_an_error_not_a_refusal():
    with pytest.raises(ValueError, match="publc.*rule 1"):
        gate(envelope("indicator_values", [("x", "typo")]))


def test_every_tier_in_the_lineage_binds():
    # an aggregate-only ancestor and a custom ancestor: both bind (D-101)
    env = envelope("hub_counts", [("hubs", "relational_hub"), ("land", "sovereign_boundary")])
    res = gate(env)
    assert rules(res) == [6]                      # counts satisfy rule 5; consent is missing
    consent = {"id": "c1", "plot": "maine", "target": "northeastern_agol",
               "sharing_level": "public", "covers": ["sovereign_boundary"],
               "status": "active", "expires_on": None}
    assert gate(env, consents=[consent])["decision"] == "allow"
    # the same consent cannot carry the aggregate-only ancestor out as points
    env_points = envelope("relational_hub", [("land", "sovereign_boundary")])
    assert 5 in rules(gate(env_points, consents=[consent]))


def test_an_aggregate_only_type_never_leaves_as_named_points():
    assert rules(gate(envelope("relational_hub", [("hubs", "relational_hub")]))) == [5]
    assert rules(gate(envelope("indicator_values", [("hubs", "relational_hub")]))) == [5]
    assert gate(envelope("hub_counts", [("hubs", "relational_hub")]))["decision"] == "allow"


def test_a_custom_type_without_a_consent_record_is_refused():
    res = gate(envelope("indicator_values", [("land", "sovereign_boundary")]))
    assert rules(res) == [6]
    assert "plots/maine/consent/" in res["refusals"][0]["would_admit"]


@pytest.mark.parametrize("change", [
    {"status": "withdrawn"}, {"target": "someone_else"}, {"plot": "nyc"},
    {"covers": ["other_type"]}, {"sharing_level": "organization"},
    {"expires_on": date(2026, 1, 1)},
])
def test_a_consent_record_opens_exactly_what_it_names(change):
    consent = {"id": "c1", "plot": "maine", "target": "northeastern_agol",
               "sharing_level": "public", "covers": ["sovereign_boundary"],
               "status": "active", "expires_on": None, **change}
    res = gate(envelope("indicator_values", [("land", "sovereign_boundary")]), consents=[consent])
    assert rules(res) == [6]


def test_a_reservation_subdivision_without_its_context_note_is_refused():
    assert rules(gate(envelope("tribal_area", [("s", "indicator_source")]))) == [9]
    ok = gate(envelope("tribal_area", [("s", "indicator_source")], notes=["census_tribal_area"]))
    assert ok["decision"] == "allow" and ok["record"]["context_notes"] == ["census_tribal_area"]


def test_a_license_that_forbids_redistribution_is_refused_at_public():
    env = envelope("indicator_values", [("s", "indicator_source")], datasets=("cii",))
    res = gate(env, level="public")
    assert rules(res) == [10] and "terms_unknown" in res["refusals"][0]["reason"]
    assert gate(env, level="private")["decision"] == "allow"


def test_a_dataset_without_a_license_is_refused():
    env = envelope("indicator_values", [("s", "indicator_source")], datasets=("nolicense",))
    assert rules(gate(env)) == [10]


def test_no_lineage_no_publication():
    assert 4 in rules(gate(envelope("indicator_values", [("s", "indicator_source")], lineage=False)))


def test_an_empty_curiosity_passes_with_its_caveat():
    res = gate(envelope("indicator_values", [("s", "indicator_source")], curiosity=""))
    assert res["decision"] == "allow"
    assert any("names no curiosity" in c for c in res["record"]["caveats"])


def test_every_refusal_names_type_tier_ancestor_and_what_would_admit_it():
    env = envelope("indicator_values", [("edges", "flow_edges"), ("land", "sovereign_boundary")],
                   datasets=("cii",))
    res = gate(env)
    assert rules(res) == [3, 6, 10]
    for r in res["refusals"]:
        for field in ("rule", "semantic_type", "tier", "ancestor", "reason",
                      "would_admit", "target", "sharing_level", "gate_version", "checked_at"):
            assert field in r, field
        assert r["ancestor"] and r["would_admit"]


def test_an_unknown_sharing_level_is_an_error():
    with pytest.raises(ValueError, match="sharing level"):
        gate(envelope("indicator_values", [("s", "indicator_source")]), level="world")


# ── the readers ──────────────────────────────────────────────────────────
def test_the_gate_reads_resolution_tier_not_the_loam_tier():
    v = Vocab({"t": {"resolution_tier": "public", "tier": "gathered"}})
    assert exposure_tier(v, "t") == "public"


def test_the_license_list_loads_and_unverified_terms_permit_private_only():
    assert LICENSES["us_government_work"]["permits"] == ["private", "organization", "public"]
    for tid, t in LICENSES.items():
        if not t["verified"]:
            assert t["permits"] == ["private"], tid


def test_an_unverified_term_that_permits_public_is_refused_at_load(tmp_path):
    (tmp_path / "licenses.yml").write_text(
        "terms:\n  t:\n    permits: [private, public]\n    verified: false\n")
    with pytest.raises(ValueError, match="unverified"):
        load_licenses(tmp_path)


def test_consent_records_load_one_file_each_and_refuse_a_missing_field(tmp_path):
    (tmp_path / "consent").mkdir()
    (tmp_path / "consent" / "c1.yml").write_text("""
id: c1
plot: maine
target: northeastern_agol
sharing_level: public
covers: [sovereign_boundary]
granted_by: a named person
on_behalf_of: a named nation
granted_on: "2026-11-01"
terms: in the grantor's words
status: active
""")
    recs = load_consents(tmp_path)
    assert recs[0]["id"] == "c1" and recs[0]["granted_on"] == date(2026, 11, 1)
    (tmp_path / "consent" / "c2.yml").write_text("id: c2\nplot: maine\n")
    with pytest.raises(ValueError, match="c2.yml is missing"):
        load_consents(tmp_path)


def test_a_plot_with_no_consent_folder_has_no_consents(tmp_path):
    assert load_consents(tmp_path) == []
