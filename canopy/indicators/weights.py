"""
canopy/indicators/weights.py

weights ~ how much each part counts, declared once, hashed, never assumed

an index is a weighted mean, and the weights are a claim about what matters.
CII's come from an advisory group's chip allocation and are not published, so
every weighting here is a file of its own: whose it is, whether it is the
publisher's, and exactly how it spends its budget. two allocations of the same
indicators are two files, and every index records which one produced it.

loud the way the indicator registry is:
  ~ a weighting id declared twice           -> refuse, naming both files
  ~ a component that is not a declared indicator -> refuse
  ~ a chip count that is not a positive number   -> refuse
  ~ budget cii_advisory_rule, spent wrongly  -> refuse: 10 x n within each
    pillar, 50 across five
  ~ is_publishers_weighting missing          -> refuse: whether a weighting
    is the publisher's is the first thing a reader needs to know
♡
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

REQUIRED = ("id", "name", "defined_by", "is_publishers_weighting", "pillars")
BUDGETS = ("cii_advisory_rule", "free")


class WeightsRegistry:
    def __init__(self, weightings: dict[str, dict], root: Path):
        self._w = weightings
        self._root = root

    @classmethod
    def load(cls, weights_dir: str | Path, indicator_ids: list[str] | None = None) -> "WeightsRegistry":
        root = Path(weights_dir)
        files = sorted(root.glob("*.yml")) if root.is_dir() else []
        if not files:
            raise FileNotFoundError(f"no weightings found at {root}; expected *.yml files")
        out: dict[str, dict] = {}
        for f in files:
            doc = yaml.safe_load(f.read_text()) or {}
            label = f"{root.name}/{f.name}"
            where = f"weighting in {label}"
            missing = [k for k in REQUIRED if k not in doc]
            if missing:
                raise ValueError(f"{where} is missing {', '.join(missing)}")
            wid = doc["id"]
            if wid in out:
                raise ValueError(f"weighting id '{wid}' declared in both {out[wid]['_file']} and {label}")
            budget = doc.get("budget", "free")
            if budget not in BUDGETS:
                raise ValueError(f"{where}: budget '{budget}' is not one of {', '.join(BUDGETS)}")
            pillars = doc["pillars"] or {}
            if not pillars:
                raise ValueError(f"{where}: no pillars")
            for pid, p in pillars.items():
                comps = (p or {}).get("components") or {}
                if not comps:
                    raise ValueError(f"{where}: pillar '{pid}' has no components")
                for name, chips in [(f"pillar '{pid}'", p.get("chips"))] + \
                                   [(f"component '{c}'", v) for c, v in comps.items()]:
                    if not isinstance(chips, (int, float)) or isinstance(chips, bool) or chips <= 0:
                        raise ValueError(f"{where}: {name} needs positive chips, got {chips!r}")
                if indicator_ids is not None:
                    unknown = [c for c in comps if c not in indicator_ids]
                    if unknown:
                        raise ValueError(f"{where}: pillar '{pid}' names undeclared indicator(s): "
                                         f"{', '.join(unknown)}")
                if budget == "cii_advisory_rule":
                    spent, allowed = sum(comps.values()), 10 * len(comps)
                    if spent != allowed:
                        raise ValueError(f"{where}: pillar '{pid}' spends {spent} chips; CII's rule "
                                         f"gives 10 x {len(comps)} = {allowed}")
            if budget == "cii_advisory_rule":
                across = sum(p["chips"] for p in pillars.values())
                if len(pillars) != 5 or across != 50:
                    raise ValueError(f"{where}: CII's rule spends 50 chips across 5 pillars; this "
                                     f"spends {across} across {len(pillars)}")
            doc["_file"] = label
            doc["_sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
            out[wid] = doc
        return cls(out, root)

    def all(self) -> list[str]:
        return sorted(self._w)

    def declaration(self, wid: str) -> dict:
        """a weighting as a primitive receives it: plain JSON, with its hash."""
        if wid not in self._w:
            raise KeyError(f"unknown weighting '{wid}'. declared: {', '.join(self.all())}")
        w = self._w[wid]
        return {
            "id": w["id"], "name": w["name"], "defined_by": w["defined_by"],
            "is_publishers_weighting": bool(w["is_publishers_weighting"]),
            "budget": w.get("budget", "free"),
            "pillars": {pid: {"name": p["name"], "chips": p["chips"],
                              "components": dict(p["components"])}
                        for pid, p in w["pillars"].items()},
            "declared_in": w["_file"], "declaration_sha256": w["_sha256"],
        }