"""
tests/debug/probe_envelope.py

Run one primitive in isolation and validate the envelope it would produce.

The orchestrator wraps a primitive in a great deal of machinery; when a step
fails on its contract, this asks the primitive and the validator directly, so
the diagnosis comes from the system rather than from a hypothesis.

    python tests/debug/probe_envelope.py <script> <semantic_type> \
        --input name=path [--input name=path ...] \
        [--params '{"k": v}'] [--format geojson]

Example:
    python tests/debug/probe_envelope.py soil/validate/validate_vector.R \
        park_boundaries --input features=plots/nyc/.data/parks.geojson
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from canopy.vocabulary import Vocabulary
from canopy import envelope as E

_EXT = {"geojson": ".geojson", "tiff": ".tif", "parquet": ".parquet",
        "csv": ".csv", "json": ".json", "gpkg": ".gpkg", "arrow": ".arrow"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("semantic_type")
    ap.add_argument("--input", action="append", default=[],
                    help="name=path, repeatable")
    ap.add_argument("--params", default="{}")
    ap.add_argument("--format", default=None,
                    help="override; default comes from the vocabulary")
    args = ap.parse_args()

    vocab = Vocabulary.load("seeds/schemas")
    st = vocab.get(args.semantic_type)
    fmt = args.format or st.format
    category = st.category
    if args.semantic_type in vocab.history_reads:
        res = vocab.history_reads[args.semantic_type]
        print(f"note: '{args.semantic_type}' is retired; read forward to "
              f"'{res.canonical}' ({res.how})")

    inputs = {}
    for pair in args.input:
        if "=" not in pair:
            print(f"--input expects name=path, got {pair!r}")
            return 2
        name, path = pair.split("=", 1)
        inputs[name] = path
        if not Path(path).exists():
            print(f"warning: input path does not exist: {path}")

    out = tempfile.mktemp(suffix=_EXT.get(fmt, ".out"))
    runner = ["Rscript"] if args.script.endswith(".R") else [sys.executable]
    proc = subprocess.run(runner + [args.script, json.dumps(inputs), out, args.params],
                          capture_output=True, text=True)

    print(f"\n{args.script}  ->  {args.semantic_type} "
          f"({category}, {fmt})   rc={proc.returncode}")

    if "{" not in proc.stdout:
        print("no JSON on stdout. stderr tail:")
        print(proc.stderr[-1200:])
        return 1

    doc = json.loads(proc.stdout[proc.stdout.index("{"):])
    if doc.get("status") == "failure":
        print(f"primitive failed: {doc.get('error')}: {doc.get('message')}")
        return 1

    meta = {k: v for k, v in doc.items() if k not in ("warnings", "status")}
    meta["semantic_type"] = args.semantic_type
    meta["data_category"] = category

    print("metadata keys:", ", ".join(sorted(meta)))
    dupes = [k for k in meta if k.endswith(".1")]
    if dupes:
        print(f"DUPLICATE KEYS (c() instead of modifyList?): {dupes}")

    errors = E.validate_envelope({
        "data": {"path": out, "format": fmt, "secondary": {}},
        "metadata": meta,
        "provenance": [],
        "warnings": doc.get("warnings", []),
    })
    if errors:
        print("\nVALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nvalidation: PASSES")
    levels = {}
    for w in doc.get("warnings", []):
        levels[w.get("level")] = levels.get(w.get("level"), 0) + 1
    if levels:
        print("warnings:", levels)
    return 0


if __name__ == "__main__":
    sys.exit(main())
