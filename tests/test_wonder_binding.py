"""
tests/test_wonder_binding.py

how a curiosity finds its methods, and how compose drafts a tabular method.
WON-1: an empty list is a claim, not an absence. WON-2: the object form binds.
WON-5: an index is not a curiosity. WON-6: a table is never reprojected, and a
string primitive reference is used as written.
"""

from canopy.wonder import possibility as P
from canopy.wonder import wondering as W

METHODS = {
    "hot_cold_spot_analysis": {"id": "hot_cold_spot_analysis", "domain": "thermal"},
    "buffer_gradient_analysis": {"id": "buffer_gradient_analysis", "domain": "thermal"},
    "ownership_concentration_analysis": {"id": "ownership_concentration_analysis", "domain": "information"},
    "cii_full_method": {"id": "cii_full_method", "domain": "information"},
}


def ids(ms):
    return [m["id"] for m in ms]


def test_the_object_form_binds():
    c = {"domain": "thermal", "compatible_methods": [
        {"ref": "$methods/thermal/hot_cold_spot_analysis", "fit": "direct"}]}
    assert ids(P._candidate_methods(c, METHODS)) == ["hot_cold_spot_analysis"]


def test_the_string_form_still_binds():
    c = {"domain": "information", "compatible_methods": ["information/ownership_concentration_analysis"]}
    assert ids(P._candidate_methods(c, METHODS)) == ["ownership_concentration_analysis"]


def test_an_empty_list_means_no_method_yet():
    assert P._candidate_methods({"domain": "information", "compatible_methods": []}, METHODS) == []


def test_an_absent_field_falls_back_to_the_domain():
    assert ids(P._candidate_methods({"domain": "information"}, METHODS)) == [
        "ownership_concentration_analysis", "cii_full_method"]


def test_a_file_name_is_not_a_method_id():
    c = {"domain": "thermal", "compatible_methods": [
        {"ref": "$methods/thermal/thermal_gradient_analysis", "fit": "complementary"}]}
    assert P._candidate_methods(c, METHODS) == []


def test_a_method_named_twice_appears_once():
    c = {"domain": "information", "compatible_methods": [
        {"ref": "$methods/information/cii_full_method", "fit": "direct"},
        "information/cii_full_method"]}
    assert ids(P._candidate_methods(c, METHODS)) == ["cii_full_method"]


def test_method_id_of_handles_both_shapes_and_junk():
    assert P.method_id_of({"ref": "$methods/information/cii_full_method"}) == "cii_full_method"
    assert P.method_id_of("information/cii_full_method") == "cii_full_method"
    assert P.method_id_of({"fit": "direct"}) is None
    assert P.method_id_of("") is None


def test_an_index_is_not_loaded_as_a_curiosity(tmp_path):
    (tmp_path / "index.yml").write_text("curiosities: [a]\n")
    (tmp_path / "a.yml").write_text("id: a\nquestion: q\n")
    assert list(P._load_dir(tmp_path)) == ["a"]
    assert list(W._load_by_id(tmp_path)) == ["a"]


def test_a_tabular_method_composes_without_a_vector_chain():
    m = {"requires_data": [{"name": "source", "type": "tabular", "semantic_types": ["indicator_source"]}],
         "requires_primitives": ["roots/derive_indicator"],
         "produces": {"semantic_type": "indicator_values"}}
    steps = W._compose_steps(m, {"indicator_source": "acs_county_2024"}, "EPSG:4326")
    assert [s["primitive"] for s in steps] == ["roots/derive_indicator"]
    assert steps[0]["inputs"] == {"source": "$manifest.acs_county_2024"}


def test_a_vector_method_still_gets_its_conform_chain():
    m = {"requires_data": [{"name": "parks", "type": "vector", "semantic_types": ["park_boundaries"]}],
         "requires_primitives": [{"calculate_pci": {"from": "roots"}}]}
    steps = W._compose_steps(m, {"park_boundaries": "parks"}, "EPSG:2263")
    assert [s["primitive"] for s in steps] == ["soil/validate_vector", "soil/reproject_vector", "roots/calculate_pci"]
