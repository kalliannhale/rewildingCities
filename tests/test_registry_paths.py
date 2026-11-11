"""
tests/test_registry_paths.py

REG-6. The orchestrator checks a primitive's path only when a step
references it, so an entry pointing at a file that does not exist stays
silent until something runs it. validate_boundaries pointed at an .R file
that was never written, and fetch_dataset at .R when the file is .py. This
reads every entry in both layers and checks its file, so the next broken path
fails here instead of in a run.
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
