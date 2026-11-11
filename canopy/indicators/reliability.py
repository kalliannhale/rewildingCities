"""
canopy/indicators/reliability.py

the small-sample rule ~ when a value should say "read with care", declared once

a rule is a file in seeds/reliability/: a minimum household count and a maximum
coefficient of variation, each with the source that justifies it, or the plain
admission that none was found (D-106, D-108). a run cites it as
`$reliability.<id>`, and the full rule with the file's sha256 lands in the
step's provenance, so every note records which rule wrote it.

loud the way the indicator registry is:
  ~ a rule id declared twice                  -> refuse, naming both files
  ~ a threshold that is not a positive number  -> refuse
  ~ max_cv outside (0, 1)                      -> refuse: it is a fraction
  ~ a threshold with no `sources` entry        -> refuse: no threshold without
    its source, even when the source is "none found"
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

REQUIRED = ("id", "name", "declared_by", "max_cv", "min_households", "sources")
TESTS = ("max_cv", "min_households")


class ReliabilityRegistry:
    def __init__(self, rules: dict[str, dict], root: Path):
        self._rules = rules
        self._root = root

    @classmethod
    def load(cls, rules_dir: str | Path) -> "ReliabilityRegistry":
        root = Path(rules_dir)
        files = sorted(root.glob("*.yml")) if root.is_dir() else []
        if not files:
            raise FileNotFoundError(f"no reliability rules found at {root}")
        rules: dict[str, dict] = {}
        for f in files:
            doc = yaml.safe_load(f.read_text()) or {}
            where = f"{root.name}/{f.name}"
            missing = [k for k in REQUIRED if doc.get(k) in (None, "")]
            if missing:
                raise ValueError(f"{where} is missing required field(s): {', '.join(missing)}")
            rid = doc["id"]
            if rid in rules:
                raise ValueError(
                    f"reliability rule '{rid}' is declared in both "
                    f"'{rules[rid]['declared_in']}' and '{where}'")
            for t in TESTS:
                v = doc[t]
                if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
                    raise ValueError(f"{where}: {t} must be a positive number; got {v!r}")
            if doc["max_cv"] >= 1:
                raise ValueError(
                    f"{where}: max_cv is a fraction (0.30 for 30 percent); got {doc['max_cv']!r}")
            sourced = {s.get("test") for s in doc["sources"] if isinstance(s, dict)}
            unsourced = [t for t in TESTS if t not in sourced]
            if unsourced:
                raise ValueError(
                    f"{where}: no sources entry for {', '.join(unsourced)}. every "
                    f"threshold names its source, or says that none was found")
            rules[rid] = dict(doc, declared_in=where)
        return cls(rules, root)

    def get(self, rule_id: str) -> dict:
        if rule_id not in self._rules:
            raise KeyError(
                f"unknown reliability rule: '{rule_id}'. declared: "
                f"{', '.join(sorted(self._rules)) or '(none)'}")
        return self._rules[rule_id]

    def declaration(self, rule_id: str) -> dict:
        """the rule as a primitive receives it, with its file's sha256."""
        rule = self.get(rule_id)
        f = self._root / rule["declared_in"].split("/", 1)[-1]
        digest = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
        return {"id": rule["id"], "min_households": float(rule["min_households"]),
                "max_cv": float(rule["max_cv"]), "sources": rule["sources"],
                "declared_in": rule["declared_in"], "declaration_sha256": digest}
