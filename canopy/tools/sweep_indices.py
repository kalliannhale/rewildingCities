#!/usr/bin/env python3
"""Coherence sweep: verify every path declared in any index file points
to a real file on disk.

Walks:
  - garden/methods/index.yml         (methods: <domain>: [{path}, ...])
  - garden/curiosity-space/index.yml (curiosities: <domain>: [{path}, ...])

Exits 0 if all paths resolve; exits 1 with a list of broken paths
otherwise. Safe to wire into pre-commit.

Run from project root:
    python canopy/tools/sweep_indices.py
"""

import sys
from pathlib import Path
import yaml


def sweep_methods_index(project_root: Path) -> list[str]:
    """Return a list of broken-path messages for the methods index."""
    index_path = project_root / "garden" / "methods" / "index.yml"
    if not index_path.exists():
        return [f"missing: {index_path}"]
    
    broken = []
    with open(index_path) as f:
        data = yaml.safe_load(f) or {}
    
    for domain, entries in (data.get("methods") or {}).items():
        for entry in entries or []:
            rel = entry.get("path")
            if not rel:
                broken.append(f"  methods/{domain}/{entry.get('id', '?')}: missing 'path' field")
                continue
            full = project_root / "garden" / "methods" / rel
            if not full.exists():
                broken.append(f"  methods/{domain}/{entry.get('id')}: path '{rel}' → {full} (not found)")
    return broken


def sweep_curiosity_index(project_root: Path) -> list[str]:
    """Return a list of broken-path messages for the curiosity index."""
    index_path = project_root / "garden" / "curiosity-space" / "index.yml"
    if not index_path.exists():
        return [f"missing: {index_path}"]
    
    broken = []
    with open(index_path) as f:
        data = yaml.safe_load(f) or {}
    
    for domain, entries in (data.get("curiosities") or {}).items():
        for entry in entries or []:
            rel = entry.get("path")
            if not rel:
                broken.append(f"  curiosity/{domain}/{entry.get('id', '?')}: missing 'path' field")
                continue
            full = project_root / "garden" / "curiosity-space" / rel
            if not full.exists():
                broken.append(f"  curiosity/{domain}/{entry.get('id')}: path '{rel}' → {full} (not found)")
    return broken


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    broken = sweep_methods_index(project_root) + sweep_curiosity_index(project_root)
    if broken:
        print("✗ Coherence sweep found broken paths:")
        for msg in broken:
            print(msg)
        sys.exit(1)
    print("✓ All index paths resolve.")
    sys.exit(0)
