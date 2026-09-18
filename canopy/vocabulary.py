"""
canopy/vocabulary.py

vocabulary ~ the garden's single spine of meaning

one loader, where there were two. the base vocabulary in
seeds/schemas/semantic_types.yml, merged with every per-domain vocabulary in
seeds/schemas/domains/*.yml, each type stamped with the domain it came from.

it is loud four ways, because a vocabulary that resolves a contradiction
quietly hands every downstream reader a wrong answer with no trace:

  ~ a type name declared twice        -> refuse, naming both sources
  ~ an alias claimed by two types     -> refuse, naming both claimants
  ~ a type missing category or format -> refuse, naming the file
  ~ the domains directory absent      -> refuse, because a moved directory
                                         and an empty one look identical, and
                                         half a vocabulary is worse than none

and it reads history forward: a receipt may carry a name we have since
retired, and resolve() says what it means today, always reporting how it
knew. nothing is ever refused for being old. ♡
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_STATE_SUFFIXES = ("_checked", "_repaired", "_reprojected", "_clipped", "_validated")


@dataclass(frozen=True)
class Resolution:
    """what a declared name means today, and how we knew."""
    declared: str
    canonical: str | None
    how: str            # "canonical" | "alias" | "suffix_fallback" | "unresolved"


@dataclass
class SemanticType:
    """one declared type, stamped with the domain it came from."""
    name: str
    category: str                                   # vector | raster | tabular | image
    format: str                                     # geojson | tiff | parquet | ...
    description: str = ""
    domain: str = "base"                            # "base" or a domain stem
    aliases: tuple[str, ...] = ()
    extra: dict = field(default_factory=dict)       # typical_units, value_range, tier, ...


class Vocabulary:
    """
    the merged garden vocabulary ~ base + domains.

    the loam-facing surface (.canonical, .alias_map, .category, .resolve) and
    the orchestrator-facing surface (get, get_format, get_category, get_domain,
    is_valid, all_types, domains, by_domain) are both preserved here, so every
    existing call site keeps working.
    """

    DOMAINS_DIRNAME = "domains"

    def __init__(self, types: dict[str, SemanticType],
                 alias_map: dict[str, str],
                 source: dict[str, str]):
        self._types = types
        self._source = source
        # retired names answered through history, kept so a caller can
        # report that an old spelling was read forward rather than matched.
        self.history_reads: dict[str, Resolution] = {}
        self.canonical: set[str] = set(types.keys())
        self.alias_map: dict[str, str] = alias_map
        self.category: dict[str, str] = {n: t.category for n, t in types.items()}

    @classmethod
    def load(cls, schemas_dir: str | Path, *, require_domains: bool = True) -> "Vocabulary":
        schemas = Path(schemas_dir)
        base = schemas / "semantic_types.yml"
        if not base.exists():
            raise FileNotFoundError(
                f"base vocabulary not found: {base}\n"
                f"  expected at <schemas_dir>/semantic_types.yml"
            )

        types: dict[str, SemanticType] = {}
        alias_map: dict[str, str] = {}
        source: dict[str, str] = {}

        cls._ingest(base, domain="base", label="base",
                    types=types, alias_map=alias_map, source=source)
        base_count = len(types)

        domains_dir = schemas / cls.DOMAINS_DIRNAME
        domain_files = sorted(domains_dir.glob("*.yml")) if domains_dir.is_dir() else []

        if require_domains and not domain_files:
            raise FileNotFoundError(
                f"no domain vocabularies found at {domains_dir}\n"
                f"  the base file alone carries {base_count} types; every domain type\n"
                f"  would be silently missing. a moved directory and an absent one look\n"
                f"  identical from here, so this refuses rather than load half a\n"
                f"  vocabulary. pass require_domains=False for a genuine base-only install."
            )

        for f in domain_files:
            cls._ingest(f, domain=f.stem, label=f"{cls.DOMAINS_DIRNAME}/{f.name}",
                        types=types, alias_map=alias_map, source=source)

        return cls(types, alias_map, source)

    @staticmethod
    def _ingest(path: Path, *, domain: str, label: str,
                types: dict, alias_map: dict, source: dict) -> None:
        doc = yaml.safe_load(path.read_text()) or {}

        for name, spec in (doc.get("types") or {}).items():
            spec = spec or {}

            category = spec.get("category")
            fmt = spec.get("format")
            if not category:
                raise ValueError(
                    f"semantic type '{name}' ({label}) is missing required field 'category'")
            if not fmt:
                raise ValueError(
                    f"semantic type '{name}' ({label}) is missing required field 'format'")

            if name in types:
                raise ValueError(
                    f"semantic type name collision: '{name}' is declared in both "
                    f"'{source[name]}' and '{label}'. names are flat and global across "
                    f"base + domains; rename one of them."
                )

            aliases = tuple(spec.get("aliases") or ())
            for a in aliases:
                if a in alias_map and alias_map[a] != name:
                    raise ValueError(
                        f"alias collision: '{a}' is claimed by both '{alias_map[a]}' "
                        f"and '{name}' ({label}). an alias may name only one type."
                    )
                alias_map[a] = name

            extra = {k: v for k, v in spec.items()
                     if k not in ("category", "format", "description", "aliases", "domain")}

            types[name] = SemanticType(
                name=name,
                category=category,
                format=fmt,
                description=spec.get("description", ""),
                domain=domain,
                aliases=aliases,
                extra=extra,
            )
            source[name] = label

    def resolve(self, declared: str) -> Resolution:
        if declared in self.canonical:
            return Resolution(declared, declared, "canonical")
        if declared in self.alias_map:
            return Resolution(declared, self.alias_map[declared], "alias")
        for suffix in _STATE_SUFFIXES:
            if declared.endswith(suffix):
                stem = declared[: -len(suffix)]
                if stem in self.canonical:
                    return Resolution(declared, stem, "suffix_fallback")
        return Resolution(declared, None, "unresolved")

    def get(self, name: str, *, follow_history: bool = True) -> SemanticType:
        """
        the type this name means. a canonical name answers directly; a
        retired name answers through what it resolves to, because history
        is read forward here as everywhere else. the resolution is recorded
        in `history_reads` so a caller can tell a current name from an old
        one, and nudge a live experiment toward the canonical spelling
        rather than freezing a retired name in place. ~
        """
        if name in self._types:
            return self._types[name]

        if follow_history:
            res = self.resolve(name)
            if res.canonical and res.canonical in self._types:
                self.history_reads.setdefault(name, res)
                return self._types[res.canonical]

        suggestions = self._find_similar(name)
        msg = f"unknown semantic type: '{name}'"
        if suggestions:
            msg += f"\n  did you mean: {', '.join(suggestions)}?"
        msg += f"\n  {len(self._types)} types are registered across domains: {', '.join(self.domains())}"
        raise KeyError(msg)

    def get_format(self, name: str) -> str:
        return self.get(name).format

    def get_category(self, name: str) -> str:
        return self.get(name).category

    def get_domain(self, name: str) -> str:
        return self.get(name).domain

    def get_tier(self, name: str) -> str | None:
        """a declared tier ('gathered') if the seed carries one, else None."""
        return self.get(name).extra.get("tier")

    def get_aliases(self, name: str) -> tuple[str, ...]:
        return self.get(name).aliases

    def is_valid(self, name: str) -> bool:
        """canonical only ~ ask knows_name() to include retired spellings."""
        return name in self._types

    def knows_name(self, name: str) -> bool:
        """canonical OR resolvable through history."""
        if name in self._types:
            return True
        res = self.resolve(name)
        return bool(res.canonical and res.canonical in self._types)

    def all_types(self) -> list[str]:
        return sorted(self._types.keys())

    def domains(self) -> list[str]:
        found = sorted({t.domain for t in self._types.values()})
        if "base" in found:
            found.remove("base")
            found = ["base"] + found
        return found

    def by_domain(self, domain: str) -> list[str]:
        return sorted(n for n, t in self._types.items() if t.domain == domain)

    def source_of(self, name: str) -> str:
        return self._source[name]

    def summary(self) -> dict[str, int]:
        """how many types came from each domain ~ for verifying a load."""
        counts: dict[str, int] = {}
        for t in self._types.values():
            counts[t.domain] = counts.get(t.domain, 0) + 1
        return dict(sorted(counts.items()))

    def _find_similar(self, name: str, max_distance: int = 2) -> list[str]:
        return [k for k in self._types
                if self._levenshtein(name.lower(), k.lower()) <= max_distance]

    @staticmethod
    def _levenshtein(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return Vocabulary._levenshtein(s2, s1)
        if not s2:
            return len(s1)
        previous = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current = [i + 1]
            for j, c2 in enumerate(s2):
                current.append(min(previous[j + 1] + 1, current[j] + 1, previous[j] + (c1 != c2)))
            previous = current
        return previous[-1]
