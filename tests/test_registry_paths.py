"""
tests/test_registry_paths.py

REG-6. The orchestrator checks a primitive's path only when a step
references it, so an entry pointing at a file that does not exist stays
silent until something runs it. validate_boundaries pointed at an .R file
that was never written, and fetch_dataset at .R when the file is .py. This
reads every entry in both layers and checks its file, so the next broken path
fails here instead of in a run.

An empty file passed that check: check_alignment was registered over a
0-byte check_alignment.R, a promise with no code behind it, and its output
type was declared nowhere. So a registered file must also hold something.
"""

from pathlib import Path

import pytest

from canopy.orchestrator.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("layer", ["soil", "roots"])
def test_every_registry_entry_points_at_a_file_that_exists(layer):
    specs = load_registry(layer, ROOT)
    missing = sorted(f"{name}: {layer}/{spec.path}" for name, spec in specs.items()
                     if not (ROOT / layer / spec.path).is_file())
    assert not missing, "registry entries with no file:\n  " + "\n  ".join(missing)


@pytest.mark.parametrize("layer", ["soil", "roots"])
def test_every_registry_entry_points_at_a_file_with_code_in_it(layer):
    specs = load_registry(layer, ROOT)
    empty = sorted(f"{name}: {layer}/{spec.path}" for name, spec in specs.items()
                   if (ROOT / layer / spec.path).is_file()
                   and not (ROOT / layer / spec.path).read_text().strip())
    assert not empty, "registry entries over an empty file:\n  " + "\n  ".join(empty)
