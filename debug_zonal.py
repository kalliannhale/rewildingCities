#!/usr/bin/env python3
"""Standalone diagnostic: invoke zonal_statistics.R with the same inputs
and params the orchestrator would have used for the buffer_temperatures
step, but pipe stderr straight to terminal so we can see R's error.

rewildr contract (corrected): three positional args
    primitive.R <inputs_json> <output_path> <params_json>

Run from project root:
    python debug_zonal.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.resolve()

raster_path = project_root / "plots" / "nyc" / ".data" / "crop_lst_cropped.tiff"
zones_path  = project_root / "plots" / "nyc" / ".data" / "generate_buffers_buffers.geojson"

if not raster_path.exists():
    print(f"ERROR: raster not found at {raster_path}")
    sys.exit(1)
if not zones_path.exists():
    print(f"ERROR: zones not found at {zones_path}")
    sys.exit(1)

# Output goes to a tempfile so we don't pollute .data
with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as out:
    output_path = out.name

inputs = {
    "raster": str(raster_path),
    "zones":  str(zones_path),
}
params = {
    "statistic": "median",
    "id_fields": ["feature_id", "distance_m"],
    "band": 1,
}

with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
    json.dump(inputs, f)
    inputs_file = f.name

with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
    json.dump(params, f)
    params_file = f.name

# Locate the primitive
primitive_path = project_root / "roots" / "metrics" / "zonal_statistics.R"
if not primitive_path.exists():
    candidates = list(project_root.rglob("zonal_statistics.R"))
    if candidates:
        primitive_path = candidates[0]
        print(f"Found primitive at: {primitive_path}")
    else:
        print("ERROR: zonal_statistics.R not found anywhere in project")
        sys.exit(1)

print(f"Invoking Rscript on:")
print(f"  primitive:   {primitive_path}")
print(f"  inputs json: {inputs_file}")
print(f"  output:      {output_path}")
print(f"  params json: {params_file}")
print(f"  raster:      {raster_path} ({raster_path.stat().st_size} bytes)")
print(f"  zones:       {zones_path} ({zones_path.stat().st_size} bytes)")
print()
print("=" * 70)
print("R STDOUT/STDERR:")
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

if result.returncode == 0:
    print(f"\nSuccess — output written to {output_path}")
    print("First lines of output:")
    with open(output_path) as f:
        for i, line in enumerate(f):
            print(f"  {line.rstrip()}")
            if i >= 5:
                break