"""tests for $crosswalks.<name> (D-206): a declared crosswalk resolved into
params, so a run's receipt records what it read and freshness sees an edit."""

from pathlib import Path

import pytest

from canopy.orchestrator import references
from canopy.orchestrator.references import ReferenceResolver, load_crosswalk


def _plant(root: Path, rel: str, text: str) -> Path:
    path = root / "seeds" / "crosswalks" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_a_crosswalk_is_found_by_name_at_any_depth(tmp_path):
    _plant(tmp_path, "outlets/outlet_sources.yml", "sources: {a: {columns: {name: N}}}\n")
    doc = load_crosswalk("outlet_sources", tmp_path / "seeds" / "crosswalks")
    assert doc == {"sources": {"a": {"columns": {"name": "N"}}}}


def test_a_missing_crosswalk_names_what_is_declared(tmp_path):
    _plant(tmp_path, "land_cover/esa.yml", "a: 1\n")
    with pytest.raises(FileNotFoundError, match="declared: esa"):
        load_crosswalk("outlet_sources", tmp_path / "seeds" / "crosswalks")


def test_two_crosswalks_of_one_name_are_refused(tmp_path):
    _plant(tmp_path, "one/x.yml", "a: 1\n")
    _plant(tmp_path, "two/x.yml", "a: 2\n")
    with pytest.raises(ValueError, match="2 crosswalks are named x.yml"):
        load_crosswalk("x", tmp_path / "seeds" / "crosswalks")


def test_a_crosswalk_must_hold_a_mapping(tmp_path):
    _plant(tmp_path, "x.yml", "- a\n- b\n")
    with pytest.raises(ValueError, match="must hold a mapping"):
        load_crosswalk("x", tmp_path / "seeds" / "crosswalks")


def test_the_resolver_puts_the_declaration_in_params(tmp_path, monkeypatch):
    _plant(tmp_path, "outlets/outlet_sources.yml", "counties: [York]\n")
    import canopy.paths
    monkeypatch.setattr(canopy.paths, "project_root", lambda: tmp_path)
    r = ReferenceResolver(manifest=None, experiment=None)
    assert r.resolve_param_value({"declaration": "$crosswalks.outlet_sources"}) == \
        {"declaration": {"counties": ["York"]}}


def test_a_crosswalk_is_never_an_input():
    r = ReferenceResolver(manifest=None, experiment=None)
    with pytest.raises(ValueError, match="for params, not inputs"):
        r.resolve_input("$crosswalks.outlet_sources")


def test_the_prefix_is_listed_with_the_others():
    assert "$crosswalks." in references.ReferenceResolver.VALID_PREFIXES
