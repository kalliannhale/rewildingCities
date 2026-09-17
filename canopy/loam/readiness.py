"""
canopy/loam/readiness.py

readiness ~ what will grow here, what seed is still missing, and how full
the ground already is

the mart, read from both sides. forward: given what a plot holds, which
methods can answer a curiosity, and where would each be uncertain?
backward: which critical requirements are absent ~ that gap is the
acquisition list. one query, two directions, closing the ring. ♡

a curiosity is a question and declares no data; the method that answers it
declares `requires_data`, each entry naming the semantic_types that satisfy
it (a list ~ alternatives allowed), whether it is critical, and the
uncertainty that follows its absence. a requirement is met when the mart
holds ANY of its types, conformed (tended or gathered); a merely-arrived
holding is declared, not yet analysable, so it counts as a gap ~ which is
exactly what tells acquisition there is work to do. no silent gaps. ~

presence is not the same as sufficiency. a type can be held and still be
too thin to answer anything: a raster that is 99% nodata is present by
name and empty in fact. so a met requirement is also weighed by coverage,
and when the FULLEST artifact of a type falls below the mart's floor, the
verdict steps down from runnable to runnable_with_uncertainty, naming the
thinness. it never blocks on thinness ~ the door does not lock; it only
refuses to call thin ground ready. ~

readiness reports the RANGE it found rather than electing one artifact as
the winner. it does not choose what runs (the experiment's references do
that), so naming a best artifact would describe something the run may
never touch. an honest range beats a comfortable pick. ~
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .loam import COVERAGE_FLOOR

CONFORMED_TIERS = ("tended", "gathered")


@dataclass
class Requirement:
    semantic_type: object            # a str or a list of acceptable types
    role: str = "critical"           # critical ~ enriching
    uncertainty_without: str = ""


@dataclass
class Holding:
    """

    what the mart holds for one canonical type ~ how many artifacts wear
    that name, and how full the fullest and the thinnest of them are. a
    coverage of None is unknown, which is not the same as thin. ~

    """
    semantic_type: str
    count: int
    best_coverage: float | None
    worst_coverage: float | None

    def is_thin(self, floor: float) -> bool:
        """thin only when we KNOW it is thin; unknown is never assumed empty."""
        return self.best_coverage is not None and self.best_coverage < floor


@dataclass
class Readiness:
    curiosity: str
    verdict: str
    present: list[str] = field(default_factory=list)
    missing_critical: list[str] = field(default_factory=list)
    missing_enriching: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    thin: list[str] = field(default_factory=list)

    def say(self) -> str:
        lines = [f"{self.curiosity} ~ {self.verdict}"]
        if self.present:
            lines.append(f"  present: {', '.join(self.present)}")
        if self.thin:
            lines.append(f"  present but thin: {', '.join(self.thin)}")
        if self.missing_critical:
            lines.append(f"  missing (critical): {', '.join(self.missing_critical)}")
        if self.missing_enriching:
            lines.append(f"  missing (enriching): {', '.join(self.missing_enriching)}")
        for u in self.uncertainties:
            lines.append(f"  ~ {u}")
        return "\n".join(lines)


def _present_holdings(loam, plot: str) -> dict[str, Holding]:
    """

    what the mart holds, conformed, gathered per canonical type ~ keeping
    how many artifacts share the name and the span of their coverage, so a
    requirement can be judged on the fullest evidence available and still
    report the range honestly. ~

    """
    rows_by_type: dict[str, list[dict]] = {}
    for tier in CONFORMED_TIERS:
        for row in loam.find(plot=plot, tier=tier):
            sem = row.get("semantic_type")
            if sem:
                rows_by_type.setdefault(sem, []).append(row)

    holdings: dict[str, Holding] = {}
    for sem, rows in rows_by_type.items():
        known = [r["coverage"] for r in rows if r.get("coverage") is not None]
        holdings[sem] = Holding(
            semantic_type=sem,
            count=len(rows),
            best_coverage=max(known) if known else None,
            worst_coverage=min(known) if known else None,
        )
    return holdings


def _as_list(x) -> list[str]:
    return list(x) if isinstance(x, (list, tuple)) else [x]


def _met(req_types, have) -> str | None:
    for t in _as_list(req_types):
        if t in have:
            return t
    return None


def _thin_note(h: Holding, floor: float) -> str:
    note = (f"{h.semantic_type} is present but thin: the fullest of "
            f"{h.count} artifact(s) covers only {h.best_coverage:.0%}, "
            f"below the mart's floor of {floor:.0%}.")
    if (h.count > 1 and h.worst_coverage is not None
            and h.worst_coverage != h.best_coverage):
        note += (f" across them coverage ranges {h.worst_coverage:.0%} "
                 f"to {h.best_coverage:.0%}.")
    note += (" anything grown here will be uncertain; look upstream before"
             " believing a result.")
    return note


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


def wonder_method(loam, plot: str, curiosity_name: str, method_path: str,
                  coverage_floor: float | None = None) -> Readiness:
    """

    rewilding wonders (forward) ~ can this plot answer this curiosity by
    this method, and where would it be unsure? reads the method's real
    requires_data, and weighs a met requirement by how full the ground
    actually is. the floor comes from the mart itself unless overridden. ~

    """
    floor = (coverage_floor if coverage_floor is not None
             else getattr(loam, "coverage_floor", COVERAGE_FLOOR))

    reqs = load_method_requirements(method_path)
    have = _present_holdings(loam, plot)
    present, missing_c, missing_e, unc, thin = [], [], [], [], []

    for req in reqs:
        hit = _met(req.semantic_type, have)
        label = hit or " / ".join(_as_list(req.semantic_type))
        if hit:
            present.append(hit)
            holding = have[hit]
            if holding.is_thin(floor):
                thin.append(hit)
                unc.append(_thin_note(holding, floor))
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
    return Readiness(curiosity_name, verdict, present, missing_c, missing_e, unc, thin)


def acquisition_gap(loam, plot: str, method_path: str) -> list[str]:
    """

    rewilding wonders (backward) ~ the acquisition list: each critical
    requirement the mart cannot yet satisfy, named by its first acceptable
    type. what the resolution engine reads to close the ring. ~

    absence only. a held-but-thin type is a quality problem the forward
    read names, not an absence ~ whether thin critical ground should also
    ask for re-acquisition is a live question, deliberately left alone
    until the ring is actually wired. ~

    """
    reqs = load_method_requirements(method_path)
    have = _present_holdings(loam, plot)
    return [_as_list(req.semantic_type)[0]
            for req in reqs
            if req.role == "critical" and _met(req.semantic_type, have) is None]


# the measurement, named publicly ~ possibility renders it warmly and the
# read-model will render it structurally, but both weigh the same ground.
# one measurement, many renderings. ~
holdings_by_type = _present_holdings
