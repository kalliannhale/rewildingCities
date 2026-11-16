"""
tests/test_tiers_and_terms.py  |  rewildingCities, Sprint 06 zip 3a (D-294 to D-300)

What may leave about Maine's outlets and clerks' offices, judged by the real
gate against the repo's own vocabulary, license list, notes and manifest:

  ~ outlet counts leave: a list is aggregate-only and its term holds for
    counts (D-295, D-296, D-299); the profile carries them too (D-296)
  ~ a named outlet does not, until OUTCONF-1 and a change of tier (D-297)
  ~ anything with Cision in its lineage never leaves (D-294)
  ~ a clerk's office leaves as a point: the list is a directory of every
    clerk, the 911 points came through the GeoLibrary (D-297 to D-299)

Each envelope is the smallest one that says what a real receipt says: its
own type, its inputs' types and the datasets its run resolved. No network,
no data, no R.
"""

from pathlib import Path

from canopy.expose import decide
from canopy.expose.check import _context

REPO = Path(__file__).resolve().parents[1]
VOCAB, DATASETS, CONSENTS, LICENSES, NOTES = _context(REPO / "plots" / "maine", REPO)

LISTS = ("outlets_easton", "outlets_lnc", "outlets_mme")
CISION = ("outlets_cision", "outlets_cision_raw")
CLERKS = ("maine_sos_clerk_info_20261114", "maine_e911_addresses_20260827")


def _required(st):
    extra = VOCAB.get(st).extra if VOCAB.knows_name(st) else {}
    return [r["id"] for r in extra.get("required_context") or []]


def receipt(own, inputs, datasets):
    """an envelope as a preparation's receipt writes it, its rows carrying no
    note, so only its own type's notes bind (D-156)."""
    lineage = {"kind": "preparation", "run": "r", "method": "$methods/m", "choices": {},
               "data_resolution": {"datasets_available": list(datasets)}}
    meta = {"semantic_type": own, "data_category": "tabular", "lineage": lineage,
            "context_notes": _required(own), "row_context_notes": []}
    return {"metadata": meta, "provenance": [{
        "primitive": "p", "lineage_branch": None,
        "inputs": [{"name": t, "semantic_type": t, "path": f".data/{t}"} for t in inputs]}]}


def judge(env):
    return decide(env, target="public", sharing_level="public", vocabulary=VOCAB, plot="maine",
                  manifest_datasets=DATASETS, licenses=LICENSES, notes=NOTES,
                  consents=CONSENTS)


def rules(res):
    return sorted(r["rule"] for r in res.get("refusals", []))


OUTLET_LINEAGE = ["outlet_listing", "outlet_stack", "outlet_groups", "news_outlet"]


def test_the_session_16_tiers_are_declared_as_decided():
    tiers = {t: VOCAB.get(t).extra.get("resolution_tier") for t in (
        "outlet_listing", "commercial_outlet_listing", "outlet_stack", "outlet_groups",
        "news_outlet", "municipal_clerk_office", "municipal_clerk_list",
        "address_point_release")}
    assert tiers == {
        "outlet_listing": "aggregate-only", "commercial_outlet_listing": "excluded",
        "outlet_stack": "aggregate-only", "outlet_groups": "aggregate-only",
        "news_outlet": "aggregate-only", "municipal_clerk_office": "public",
        "municipal_clerk_list": "public", "address_point_release": "public"}
    for t in ("indicator_values", "place_profile"):
        assert VOCAB.get(t).extra.get("aggregates") is True, t


def test_each_listing_names_the_term_read_for_it():
    terms = {n: DATASETS[n]["license"] for n in LISTS + CISION + CLERKS}
    assert terms == {
        "outlets_easton": "factual_compilation_counts", "outlets_lnc": "factual_compilation_counts",
        "outlets_mme": "project_own_work",
        "outlets_cision": "terms_unknown", "outlets_cision_raw": "terms_unknown",
        "maine_sos_clerk_info_20261114": "factual_directory",
        "maine_e911_addresses_20260827": "maine_geolibrary_public"}
    assert LICENSES["factual_compilation_counts"]["requires_tier"] == "aggregate-only"
    for tid in ("factual_directory", "factual_compilation_counts", "project_own_work"):
        assert "D-29" in LICENSES[tid]["basis"] or "D-300" in LICENSES[tid]["basis"], tid
    assert "Feist" in LICENSES["factual_directory"]["basis"]


def test_outlet_counts_leave_from_the_three_lists():
    res = judge(receipt("indicator_values", OUTLET_LINEAGE, LISTS))
    assert res["decision"] == "allow", res.get("refusals")
    assert {c["term"] for c in res["record"]["license"]} == {
        "factual_compilation_counts", "project_own_work"}


def test_a_profile_carrying_outlet_counts_leaves():
    res = judge(receipt("place_profile", ["indicator_values"] + OUTLET_LINEAGE, LISTS))
    assert res["decision"] == "allow", res.get("refusals")


def test_named_outlets_wait_for_outconf_1():
    # every outlet type in the lineage binds, so naming outlets takes more
    # than news_outlet's tier: the lists' own tiers and terms move too, on
    # their makers' word (D-297, D-299)
    res = judge(receipt("news_outlet", ["outlet_listing", "outlet_stack", "outlet_groups"], LISTS))
    assert set(rules(res)) == {5}
    assert {r["semantic_type"] for r in res["refusals"]} == {
        "news_outlet", "outlet_listing", "outlet_stack", "outlet_groups"}


def test_nothing_with_cision_in_its_lineage_leaves():
    res = judge(receipt("indicator_values", ["commercial_outlet_listing"] + OUTLET_LINEAGE,
                        LISTS + CISION))
    assert 3 in rules(res) and 10 in rules(res)


def test_a_clerk_office_leaves_as_a_point():
    res = judge(receipt("municipal_clerk_office",
                        ["municipal_clerk_list", "address_point_release"], CLERKS))
    assert res["decision"] == "allow", res.get("refusals")
    assert {c["term"] for c in res["record"]["license"]} == {
        "factual_directory", "maine_geolibrary_public"}
