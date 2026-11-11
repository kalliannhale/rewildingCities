"""
canopy/manifest/staleness.py

ACQ-4 ~ a source declared differently than it was acquired is stale.

the manifest is the declaration; the changelog is the record of what was
fetched. an indicator source declares its indicators, the registry says which
variables those need (each value, its margin, and since Sprint 02 the count it
rests on), and the acquisition recorded `variables_requested`. when the
declaration now needs a variable the acquisition never asked for, the holding
on disk cannot answer what the manifest says it can, and "you already have
this" would be the wrong thing to say. this says which variables are missing.

only providers that record `variables_requested` can be judged; for any other
source this answers None, meaning "cannot tell", never "fresh". ~
"""

from __future__ import annotations

from pathlib import Path

import yaml


def last_acquisition(changelog_path: Path, dataset_name: str) -> dict | None:
    """the provenance of the most recent recorded acquisition of a dataset."""
    if not changelog_path.is_file():
        return None
    entries = yaml.safe_load(changelog_path.read_text()) or []
    for entry in reversed(entries if isinstance(entries, list) else []):
        for change in reversed(entry.get("changes") or []):
            prov = change.get("provenance") or {}
            if change.get("dataset") == dataset_name and "variables_requested" in prov:
                return prov
    return None


def staleness(dataset, changelog_path: Path) -> dict | None:
    """None when staleness cannot be judged for this source. otherwise
    {"stale": bool, "missing": [...], "message": str}."""
    source = dataset.source or {}
    if source.get("provider") != "census_acs":
        return None
    from canopy.providers.census_acs import CensusACSProvider
    needed, problems = CensusACSProvider.resolve_variables(source)
    if problems:
        return {"stale": True, "missing": [],
                "message": "the declaration cannot be resolved: " + "; ".join(problems)}
    acquired = last_acquisition(changelog_path, dataset.name)
    if acquired is None:
        return {"stale": True, "missing": list(needed),
                "message": ("no recorded acquisition says which variables were "
                            "fetched, so the holding cannot be shown to match its "
                            "declaration")}
    requested = set(acquired.get("variables_requested") or [])
    missing = [v for v in needed if v not in requested]
    if not missing:
        return {"stale": False, "missing": [], "message": "acquired as declared"}
    return {"stale": True, "missing": missing,
            "message": (f"declared differently than acquired: the declaration now "
                        f"needs {', '.join(missing)}, which the last acquisition "
                        f"({acquired.get('vintage_window', 'unknown vintage')}) did "
                        f"not request. re-acquire with --fetch")}
