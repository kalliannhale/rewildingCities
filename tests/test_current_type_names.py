"""
tests/test_current_type_names.py

Every semantic type a live declaration names is a current name in the
vocabulary (D-220). resolve() reads history forward, so a retired spelling
or a state-suffixed one (park_boundaries_checked) would still run; that is
right for a receipt and wrong for a declaration, which says what a thing is
today. Validating, repairing or reprojecting changes a dataset's state, never
what it is: state is provenance, kept in the receipt.

These walk every registry entry, method, manifest, preparation and
experiment, every plot, not only Maine's, and the composer that drafts new
experiments (D-222). An empty walk is a failure, never a pass.
"""

from pathlib import Path

import pytest
import yaml

from canopy.orchestrator.parsing import load_method_data
from canopy.paths import project_root
from canopy.vocabulary import Vocabulary
from canopy.wonder.wondering import _compose_steps

ROOT = project_root()
METHOD_FILES = sorted(p for p in (ROOT / "garden" / "methods").rglob("*.yml")
                      if p.name != "index.yml")
MANIFEST_FILES = sorted((ROOT / "plots").rglob("manifest.yml"))
PREPARATION_FILES = sorted((ROOT / "plots").rglob("preparations/*.yml"))
EXPERIMENT_FILES = sorted(p for p in [*(ROOT / "plots").rglob("experiments/*.yml"),
                                      *(ROOT / "garden" / "experiments").glob("*.yml")]
                          if p.name != "index.yml")


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def _registry(layer: str) -> dict:
    doc = yaml.safe_load((ROOT / layer / "_registry.yml").read_text()) or {}
    return doc.get("primitives") or {}


REGISTRY_ENTRIES = [(layer, name, spec)
                    for layer in ("soil", "roots")
                    for name, spec in sorted(_registry(layer).items())]


@pytest.fixture(scope="module")
def vocab() -> Vocabulary:
    return Vocabulary.load(ROOT / "seeds" / "schemas")


def named_types(node) -> list[str]:
    """every value under a semantic_type or semantic_types key, at any depth."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "semantic_type" and isinstance(value, str):
                found.append(value)
            elif key == "semantic_types" and isinstance(value, list):
                found.extend(v for v in value if isinstance(v, str))
            else:
                found.extend(named_types(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(named_types(item))
    return found


def step_outputs(doc: dict) -> list[str]:
    """the types a run's steps say they make: outputs map a name to a type."""
    made = []
    for step in doc.get("steps") or []:
        outputs = step.get("outputs") if isinstance(step, dict) else None
        if isinstance(outputs, dict):
            made.extend(t for t in outputs.values() if isinstance(t, str))
    return made


def not_current(vocab: Vocabulary, names: list[str]) -> list[str]:
    problems = []
    for name in sorted(set(names)):
        if vocab.is_valid(name):
            continue
        res = vocab.resolve(name)
        if res.canonical:
            problems.append(f"{name}: not a current name; resolve() reads it as "
                            f"{res.canonical} by {res.how}")
        else:
            problems.append(f"{name}: not in the vocabulary")
    return problems


def _say(where: str, problems: list[str]) -> str:
    return "\n  ".join([where + ":"] + problems)


# ── the walks find something to check ───────────────────────────────────────

def test_every_walk_has_files_to_read():
    assert len(REGISTRY_ENTRIES) >= 40
    assert len(METHOD_FILES) >= 14
    assert len(MANIFEST_FILES) >= 3
    assert len(PREPARATION_FILES) >= 9
    assert len(EXPERIMENT_FILES) >= 6


def test_the_walk_reads_both_spellings_and_skips_null():
    node = {"inputs": [{"semantic_types": ["a", "b"]}],
            "outputs": {"semantic_type": None},
            "deep": {"x": [{"semantic_type": "c"}]}}
    assert sorted(named_types(node)) == ["a", "b", "c"]


def test_the_walk_reads_step_outputs_as_types():
    doc = {"steps": [{"outputs": {"points": "library_outlet"}},
                     {"outputs": "not a mapping"}, "not a step"]}
    assert step_outputs(doc) == ["library_outlet"]


# ── D-220: state is provenance, never a type ────────────────────────────────

def test_sample_features_lists_no_state_spelling():
    spec = _registry("soil")["sample_features"]
    accepted = next(i for i in spec["inputs"] if "park_boundaries" in i["semantic_types"])
    assert not [t for t in accepted["semantic_types"] if t.startswith("park_boundaries_")]


def test_assign_feature_id_makes_park_boundaries():
    assert _registry("soil")["assign_feature_id"]["outputs"]["semantic_type"] == "park_boundaries"


# ── every live declaration uses a current name ──────────────────────────────

@pytest.mark.parametrize("layer, name, spec", REGISTRY_ENTRIES,
                         ids=[f"{layer}/{name}" for layer, name, _ in REGISTRY_ENTRIES])
def test_every_type_a_registry_entry_names_is_current(vocab, layer, name, spec):
    problems = not_current(vocab, named_types(spec))
    assert not problems, _say(f"{layer}/{name}", problems)


@pytest.mark.parametrize("path", METHOD_FILES, ids=_rel)
def test_every_type_a_method_names_is_current(vocab, path):
    problems = not_current(vocab, named_types(load_method_data(path)))
    assert not problems, _say(_rel(path), problems)


@pytest.mark.parametrize("path", MANIFEST_FILES, ids=_rel)
def test_every_type_a_manifest_declares_is_current(vocab, path):
    doc = yaml.safe_load(path.read_text()) or {}
    problems = not_current(vocab, named_types(doc))
    assert not problems, _say(_rel(path), problems)


@pytest.mark.parametrize("path", PREPARATION_FILES, ids=_rel)
def test_every_type_a_preparation_step_makes_is_current(vocab, path):
    doc = yaml.safe_load(path.read_text()) or {}
    problems = not_current(vocab, step_outputs(doc) + named_types(doc))
    assert not problems, _say(_rel(path), problems)


@pytest.mark.parametrize("path", EXPERIMENT_FILES, ids=_rel)
def test_every_type_an_experiment_step_makes_is_current(vocab, path):
    doc = yaml.safe_load(path.read_text()) or {}
    problems = not_current(vocab, step_outputs(doc) + named_types(doc))
    assert not problems, _say(_rel(path), problems)


# ── D-222: the composer drafts current names ────────────────────────────────

def test_a_conformed_output_keeps_its_requirements_type():
    method = {
        "requires_data": [
            {"name": "feature_boundaries", "type": "vector", "semantic_types": ["park_boundaries"]},
            {"name": "surface_temperature", "type": "raster",
             "semantic_types": ["land_surface_temperature"]},
        ],
        "requires_primitives": ["roots/geometry/generate_buffers"],
        "produces": [{"name": "cooling", "semantic_type": "pci_results"}],
    }
    steps = {s["id"]: s["outputs"] for s in _compose_steps(method, {}, "EPSG:4326")}
    assert steps["conform_feature_boundaries"] == {"validated": "park_boundaries"}
    assert steps["conform_feature_boundaries_frame"] == {"reprojected": "park_boundaries"}
    assert steps["conform_surface_temperature"] == {"validated": "land_surface_temperature"}
    assert steps["analyze"] == {"cooling": "pci_results"}


@pytest.mark.parametrize("path", METHOD_FILES, ids=_rel)
def test_a_draft_composed_from_any_method_names_current_types(vocab, path):
    steps = _compose_steps(load_method_data(path), {}, "EPSG:4326")
    problems = not_current(vocab, step_outputs({"steps": steps}))
    assert not problems, _say(f"composed from {_rel(path)}", problems)
