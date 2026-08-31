"""
canopy/loam/canonical.py

canonical ~ reading old names forward

the garden's vocabulary evolves; its history must not be refused. a receipt
may carry a name we have since retired (park_boundaries_reprojected), and
this resolves it to what it means today (park_boundaries), so the mart stays
answerable across every version of itself. ♡

the source of truth is your vocabulary: seeds/schemas/semantic_types.yml
merged with its modules, where each canonical type may list the retired
`aliases` it supersedes, right beside its `parent_type`. resolution is:
  ~ already canonical      -> keep it
  ~ listed as an alias     -> resolve it (explicit, auditable)
  ~ a known state-suffix   -> resolve to base, only as a declared fallback
  ~ none of these          -> unresolved; kept, named null, and flagged

nothing is refused. an unresolved name is honest history we cannot yet read,
never a reason to forget a receipt. ~

"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

# processing states retired from type names by the 8/24 sprint. used ONLY as a
# last-resort fallback, and every use is reported, never silent.
_STATE_SUFFIXES = ("_checked", "_repaired", "_reprojected", "_clipped", "_validated")


@dataclass(frozen=True)
class Resolution:
    declared: str
    canonical: str | None
    how: str            # "canonical" | "alias" | "suffix_fallback" | "unresolved"


class Vocabulary:
    """

    the merged garden vocabulary ~ base + modules, with each type's aliases
    and its category, so the mart can frame spatial data and let tabular
    results be frameless. ~

    """
    def __init__(self, canonical: set[str], alias_map: dict[str, str],
                 category: dict[str, str]):
        self.canonical = canonical
        self.alias_map = alias_map
        self.category = category

    @classmethod
    def load(cls, schemas_dir: str) -> "Vocabulary":
        base = Path(schemas_dir) / "semantic_types.yml"
        modules = sorted((Path(schemas_dir) / "modules").glob("*.yml"))
        canonical: set[str] = set()
        alias_map: dict[str, str] = {}
        category: dict[str, str] = {}
        for f in [base, *modules]:
            doc = yaml.safe_load(f.read_text()) or {}
            for type_name, spec in (doc.get("types") or {}).items():
                spec = spec or {}
                canonical.add(type_name)
                if spec.get("category"):
                    category[type_name] = spec["category"]
                for a in spec.get("aliases", []) or []:
                    if a in alias_map and alias_map[a] != type_name:
                        raise ValueError(
                            f"alias '{a}' claimed by both {alias_map[a]} and {type_name}")
                    alias_map[a] = type_name
        return cls(canonical, alias_map, category)

    def resolve(self, declared: str) -> Resolution:
        if declared in self.canonical:
            return Resolution(declared, declared, "canonical")
        if declared in self.alias_map:
            return Resolution(declared, self.alias_map[declared], "alias")
        for suffix in _STATE_SUFFIXES:
            if declared.endswith(suffix):
                base = declared[: -len(suffix)]
                if base in self.canonical:
                    return Resolution(declared, base, "suffix_fallback")
        return Resolution(declared, None, "unresolved")