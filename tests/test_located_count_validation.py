"""
tests/test_located_count_validation.py

A located_count counts the type its indicator names (D-224). The indicator
says what is counted; the run says whose points and which release. So before
anything runs, the orchestrator walks back from the count to its points:
the count step reads exactly one located_in_edges input made in this run,
and the step that made those edges reads exactly one input of the counted
type. These read the real maine_libraries preparation, and copies of it
broken one way at a time.
"""

from pathlib import Path

import pytest

from canopy.orchestrator.orchestrator import Orchestrator, _indicator_refs
from canopy.paths import project_root

ROOT = project_root()
LIBRARIES = ROOT / "plots" / "maine" / "preparations" / "maine_libraries.yml"


def _about_counts(errors: list[str]) -> list[str]:
    return [e for e in errors if "D-224" in e or "$indicators." in e]


def _validate(path: Path) -> list[str]:
    errors, _ = Orchestrator(path, project_root=ROOT).validate()
    return errors


def _broken(tmp_path: Path, old: str, new: str) -> Path:
    """maine_libraries with one line changed, its manifest named from the
    project root so the copy can live anywhere."""
    text = LIBRARIES.read_text()
    for a, b in (("manifest: ../manifest.yml", "manifest: plots/maine/manifest.yml"),
                 (old, new)):
        assert text.count(a) == 1, f"the preparation no longer holds {a!r} once"
        text = text.replace(a, b)
    path = tmp_path / "maine_libraries.yml"
    path.write_text(text)
    return path


def test_the_params_walk_finds_every_indicator_reference():
    params = {"indicator": "$indicators.a", "levels": ["state"],
              "deep": {"x": ["$indicators.b", "$choices.c"]}}
    assert _indicator_refs(params) == ["a", "b"]


def test_the_libraries_preparation_counts_what_its_indicator_names():
    assert _about_counts(_validate(LIBRARIES)) == []


def test_points_of_another_type_are_refused(tmp_path):
    path = _broken(tmp_path, "      points: library_outlet\n", "      points: governance_unit\n")
    problems = _about_counts(_validate(path))
    assert len(problems) == 1
    assert "library_outlet" in problems[0] and "libraries_located_in" in problems[0]


def test_edges_this_run_does_not_make_are_refused(tmp_path):
    path = _broken(tmp_path, "      edges: $steps.libraries_located_in.edges\n",
                   "      edges: $loam.located_in_edges\n")
    problems = _about_counts(_validate(path))
    assert len(problems) == 1 and "does not make" in problems[0]


def test_an_undeclared_indicator_is_refused(tmp_path):
    path = _broken(tmp_path, "$indicators.library_outlets_per_1000",
                   "$indicators.no_such_indicator")
    problems = _about_counts(_validate(path))
    assert len(problems) == 1 and "no_such_indicator" in problems[0]
