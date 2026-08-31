"""

readiness ~ what will grow here, and what seed is still missing

the mart, read from both sides. forward: given what a plot holds, which
methods can answer a curiosity, and where would each be uncertain?
backward: which critical requirements are absent ~ that gap is the
acquisition list the resolution engine reads. one query, two directions,
closing the ring. ♡

a curiosity is a question and declares no data; the method that answers it
declares `requires_data`, each entry naming the semantic_types that satisfy
it (a list ~ alternatives allowed), whether it is critical, and the
uncertainty that follows its absence. a requirement is met when the mart
holds ANY of its types, conformed (tended or gathered); a merely-arrived
holding is declared, not yet analysable, so it counts as a gap ~ which is
exactly what tells acquisition there is work to do. no silent gaps. ~

"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFORMED_TIERS = ("tended", "gathered")


@dataclass
class Requirement:
    semantic_type: object            # a str or a list of acceptable types
    role: str = "critical"           # critical ~ enriching
    uncertainty_without: str = ""


@dataclass
class Readiness:
    curiosity: str
    verdict: str
    present: list[str] = field(default_factory=list)
    missing_critical: list[str] = field(default_factory=list)
    missing_enriching: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)

    def say(self) -> str:
        lines = [f"{self.curiosity} ~ {self.verdict}"]
        if self.present:
            lines.append(f"  present: {', '.join(self.present)}")
        if self.missing_critical:
            lines.append(f"  missing (critical): {', '.join(self.missing_critical)}")
        if self.missing_enriching:
            lines.append(f"  missing (enriching): {', '.join(self.missing_enriching)}")
        for u in self.uncertainties:
            lines.append(f"  ~ {u}")
        return "\n".join(lines)


def _present_types(loam, plot: str) -> set[str]:
    have = set()
    for tier in CONFORMED_TIERS:
        for row in loam.find(plot=plot, tier=tier):
            if row.get("semantic_type"):
                have.add(row["semantic_type"])
    return have


def _as_list(x) -> list[str]:
    return list(x) if isinstance(x, (list, tuple)) else [x]


def _met(req_types, have: set[str]) -> str | None:
    for t in _as_list(req_types):
        if t in have:
            return t
    return None


def load_method_requirements(method_path: str) -> list[Requirement]:
    """

    read a method's data needs from its real seed ~ the honest source of
    requirements. each requires_data entry names the semantic_types that
    satisfy it, whether it is critical, and the uncertainty without it.
    role prose is human-facing and ignored. reads what is there. ~

    """
    doc = yaml.safe_load(Path(method_path).read_text()) or {}
    reqs: list[Requirement] = []
    for item in doc.get("requires_data", []) or []:
        types = item.get("semantic_types") or ([item["type"]] if item.get("type") else [])
        if not types:
            continue
        reqs.append(Requirement(
            semantic_type=types,
            role="critical" if item.get("critical", True) else "enriching",
            uncertainty_without=(item.get("uncertainty_without") or "").strip()))
    return reqs


def wonder_method(loam, plot: str, curiosity_name: str, method_path: str) -> Readiness:
    """

    rewilding wonders (forward) ~ can this plot answer this curiosity by
    this method, and where would it be unsure? reads the method's real
    requires_data. ~

    """
    reqs = load_method_requirements(method_path)
    have = _present_types(loam, plot)
    present, missing_c, missing_e, unc = [], [], [], []

    for req in reqs:
        hit = _met(req.semantic_type, have)
        label = hit or " / ".join(_as_list(req.semantic_type))
        if hit:
            present.append(hit)
        elif req.role == "critical":
            missing_c.append(label)
            if req.uncertainty_without:
                unc.append(f"missing {label}: {req.uncertainty_without}")
        else:
            missing_e.append(label)
            if req.uncertainty_without:
                unc.append(f"without {label}: {req.uncertainty_without}")

    if missing_c:
        verdict = "blocked"
    elif missing_e or unc:
        verdict = "runnable_with_uncertainty"
    else:
        verdict = "runnable"
    return Readiness(curiosity_name, verdict, present, missing_c, missing_e, unc)


def acquisition_gap(loam, plot: str, method_path: str) -> list[str]:
    """

    rewilding wonders (backward) ~ the acquisition list: each critical
    requirement the mart cannot yet satisfy, named by its first acceptable
    type. what the resolution engine reads to close the ring. ~

    """
    reqs = load_method_requirements(method_path)
    have = _present_types(loam, plot)
    return [_as_list(req.semantic_type)[0]
            for req in reqs
            if req.role == "critical" and _met(req.semantic_type, have) is None]
