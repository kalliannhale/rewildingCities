"""the maine_outlets preparation agrees with its declaration, its registry
entries, its manifest datasets and its vocabulary (Sprint 06, step 8)."""

from pathlib import Path

import yaml

from canopy.orchestrator.parsing import parse_experiment, parse_manifest

ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "plots" / "maine" / "preparations" / "maine_outlets.yml"
SEED = ROOT / "seeds" / "crosswalks" / "outlets" / "outlet_sources.yml"


def _steps():
    return {s.id: s for s in parse_experiment(PREP).steps}


def test_it_is_a_preparation_reading_the_declaration_as_a_param():
    prep = parse_experiment(PREP)
    assert prep.lineage.kind == "preparation"
    assert _steps()["outlets_stack"].params == {"declaration": "$crosswalks.outlet_sources"}


def test_its_inputs_are_exactly_the_declared_sources():
    declared = set(yaml.safe_load(SEED.read_text())["sources"])
    assert set(_steps()["outlets_stack"].inputs) == declared


def test_the_registry_entry_names_the_same_inputs():
    reg = yaml.safe_load((ROOT / "soil" / "_registry.yml").read_text())["primitives"]
    names = {i["name"] for i in reg["stack_outlet_sources"]["inputs"]}
    assert names == set(_steps()["outlets_stack"].inputs)
    for name in ("group_outlet_records", "list_outlet_disagreements"):
        assert reg[name]["path"].startswith("transform/")


def test_every_listing_is_a_usable_outlet_listing_in_garden_reference():
    manifest = parse_manifest(ROOT / "plots" / "maine" / "manifest.yml")
    for ref in _steps()["outlets_stack"].inputs.values():
        ds = manifest.datasets[ref.removeprefix("$manifest.")]
        assert ds.is_usable, ds.underspecified
        assert ds.semantic_type == "outlet_listing"
        assert ds.format == "csv"
        assert ds.path.startswith("../../garden/reference/")


def test_the_outlet_types_are_declared_and_the_listing_never_leaves():
    types = yaml.safe_load((ROOT / "seeds" / "schemas" / "domains" / "information.yml")
                           .read_text())["types"]
    for name in ("outlet_listing", "outlet_stack", "outlet_groups", "outlet_disagreements"):
        assert types[name]["category"] == "tabular"
        assert types[name]["format"] == "csv"
    assert types["outlet_listing"]["resolution_tier"] == "excluded"


def test_each_step_writes_its_own_type():
    outs = {sid: list(s.outputs.values()) for sid, s in _steps().items()}
    assert outs == {"outlets_stack": ["outlet_stack"], "outlets_groups": ["outlet_groups"],
                    "outlets_disagreements": ["outlet_disagreements"]}
