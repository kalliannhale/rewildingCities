"""
tests/test_method_schema.py

seeds/schemas/method.schema.yml is the one home of a method's shape (D-213).
these hold every method in garden/methods/ to it, the index to the methods
(D-216), every primitive a method names to its registry (D-214), and a run
on a method the schema refuses to an error, never a warning.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from canopy.orchestrator.orchestrator import Orchestrator
from canopy.orchestrator.parsing import (
    MethodShapeError, load_method_data, method_shape_problems, parse_method,
)
from canopy.orchestrator.registry import RegistryManager
from canopy.paths import project_root

ROOT = project_root()
METHODS = ROOT / "garden" / "methods"
METHOD_FILES = sorted(p for p in METHODS.rglob("*.yml") if p.name != "index.yml")


def _rel(p: Path) -> str:
    return p.relative_to(METHODS).as_posix()


def test_the_garden_has_methods_to_check():
    assert len(METHOD_FILES) >= 14


@pytest.mark.parametrize("path", METHOD_FILES, ids=_rel)
def test_every_method_matches_the_schema(path):
    load_method_data(path)


@pytest.mark.parametrize("path", METHOD_FILES, ids=_rel)
def test_every_primitive_a_method_names_resolves(path):
    data = load_method_data(path)
    named = list(data["requires_primitives"])
    named += [step["primitive"] for step in data.get("recipe") or []]
    registry = RegistryManager(ROOT)
    for ref in named:
        registry.resolve_primitive(ref, validate_exists=True)


@pytest.mark.parametrize("path", METHOD_FILES, ids=_rel)
def test_a_recipe_uses_only_primitives_its_method_declares(path):
    data = load_method_data(path)
    declared = set(data["requires_primitives"])
    used = {step["primitive"] for step in data.get("recipe") or []}
    assert used <= declared, f"recipe uses undeclared {sorted(used - declared)}"


def test_the_index_routes_every_method_once_by_its_own_id_and_domain():
    index = yaml.safe_load((METHODS / "index.yml").read_text())["methods"]
    routes = [(domain, e) for domain, entries in index.items() for e in entries]
    for _, entry in routes:
        assert set(entry) == {"id", "path"}, f"the index only routes (D-216): {entry}"
    paths = [e["path"] for _, e in routes]
    assert sorted(paths) == sorted(_rel(p) for p in METHOD_FILES)
    ids = [e["id"] for _, e in routes]
    assert len(ids) == len(set(ids))
    for domain, entry in routes:
        data = load_method_data(METHODS / entry["path"])
        assert data["id"] == entry["id"], entry["path"]
        assert data.get("domain") == domain, entry["path"]


def test_options_are_read_as_their_ids_in_order():
    method = parse_method(METHODS / "information" / "library_carriers.yml")
    assert method.choices["temporarily_closed"].options == ["listed", "placed"]


def test_a_parametric_choice_has_no_options():
    method = parse_method(METHODS / "thermal" / "thermal_gradient_analysis.yml")
    assert method.choices["buffer_interval"].options == []


# ── the retired shapes are refused, each by name ─────────────────────────────

def _base():
    return {
        "id": "m", "name": "M", "description": "d",
        "choices": {"c": {"description": "d", "options": {"a": None, "b": None}, "default": "a"}},
        "requires_primitives": ["soil/derive_indicator"],
        "requires_data": [{"name": "source", "type": "tabular", "semantic_types": ["x"]}],
        "produces": [{"semantic_type": "y", "data_category": "tabular"}],
    }


def test_the_base_method_holds():
    assert method_shape_problems(_base()) == []


@pytest.mark.parametrize("change, where", [
    (lambda m: m["choices"]["c"].update(options=["a", "b"]), "choices.c"),
    (lambda m: m["choices"]["c"]["options"].update(a={"id": "aa"}), "choices.c.options.a"),
    (lambda m: m.update(produces={"semantic_type": "y", "data_category": "tabular"}), "produces"),
    (lambda m: m.update(requires_primitives={"derive_indicator": {"from": "soil"}}), "requires_primitives"),
    (lambda m: m.update(requires_primitives=["derive_indicator"]), "requires_primitives.0"),
    (lambda m: m.update(intrepretation="a typo"), "(top level)"),
    (lambda m: m["choices"]["c"].update(default="z"), "choices.c.default"),
    (lambda m: m["choices"]["c"].update(type="string"), "choices.c"),
])
def test_a_retired_or_mistaken_shape_is_refused_where_it_is(change, where):
    m = _base()
    change(m)
    problems = method_shape_problems(m)
    assert any(p.startswith(where) for p in problems), problems


def test_a_key_written_twice_is_refused(tmp_path):
    p = tmp_path / "m.yml"
    p.write_text(yaml.safe_dump(_base()) + "name: Again\n")
    with pytest.raises(ValueError, match="duplicate key 'name'"):
        load_method_data(p)


def test_a_run_on_a_refused_method_is_an_error_not_a_warning(tmp_path):
    bad = _base()
    bad["choices"]["c"]["options"] = ["a", "b"]
    p = tmp_path / "m.yml"
    p.write_text(yaml.safe_dump(bad))
    orch = SimpleNamespace(
        experiment=SimpleNamespace(lineage=SimpleNamespace(method_ref="m"), choices={"c": "a"}),
        _resolve_method_path=lambda ref: p,
    )
    errors, warnings = [], []
    Orchestrator._validate_method_choices(orch, errors, warnings)
    assert errors and "does not match" in errors[0]
    assert warnings == []
    with pytest.raises(MethodShapeError):
        load_method_data(p)
