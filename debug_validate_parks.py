#!/usr/bin/env python3
"""Standalone diagnostic: invoke validate_vector.R on parks.geojson and
surface R's actual stderr.

Run from project root:
    python debug_validate_parks.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.resolve()

# The orchestrator step's input is $manifest.park_boundaries — which resolves
# to plots/nyc/.data/parks.geojson per the manifest.
features_path = project_root / "plots" / "nyc" / ".data" / "parks.geojson"

if not features_path.exists():
    print(f"ERROR: features file not found at {features_path}")
    sys.exit(1)

inputs = {"features": str(features_path)}
params = {}  # validate_vector.R takes no params

with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
    json.dump(inputs, f)
    inputs_file = f.name

with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
    json.dump(params, f)
    params_file = f.name

# Passthrough primitive — output path is required by the contract but ignored
with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as out:
    output_path = out.name

primitive_path = project_root / "soil" / "validate" / "validate_vector.R"
if not primitive_path.exists():
    candidates = list(project_root.rglob("validate_vector.R"))
    if candidates:
        primitive_path = candidates[0]
        print(f"Found primitive at: {primitive_path}")
    else:
        print("ERROR: validate_vector.R not found anywhere in project")
        sys.exit(1)

print(f"Invoking Rscript on:")
print(f"  primitive: {primitive_path}")
print(f"  features:  {features_path} ({features_path.stat().st_size:,} bytes)")
print()
print("=" * 70)

result = subprocess.run(
    [
        "Rscript", "--no-save", "--no-restore",
        str(primitive_path),
        inputs_file,
        output_path,
        params_file,
    ],
    capture_output=True,
    text=True,
    cwd=str(project_root),
)

print("---STDOUT---")
print(result.stdout)
print("---STDERR---")
print(result.stderr)
print()
print(f"Exit code: {result.returncode}")

# If R succeeded, also do a minimal sf-only smoke test to confirm
# the file can be read without any rewildr involvement.
if result.returncode != 0:
    print()
    print("=" * 70)
    print("FALLBACK: trying a plain sf::st_read to see if it's a basic read failure")
    print("=" * 70)
    smoke = subprocess.run(
        [
            "Rscript", "--no-save", "--no-restore", "-e",
            f'library(sf); sf_use_s2(FALSE); '
            f'x <- st_read("{features_path}", quiet=TRUE); '
            f'cat("rows:", nrow(x), "\\ncrs:", st_crs(x)$input, "\\n")'
        ],
        capture_output=True, text=True, cwd=str(project_root),
    )
    print("---STDOUT---")
    print(smoke.stdout)
    print("---STDERR---")
    print(smoke.stderr)
    print(f"Exit code: {smoke.returncode}")
