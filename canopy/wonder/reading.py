"""
canopy/wonder/reading.py

reading ~ one structured account of what a plot can ask

the read-model. everything wonder knows about a place, computed once and
returned as an object rather than printed as prose.

this exists because the answer used to be the printing. `wonder` computed
what a plot could ask, said it beautifully, and the knowledge evaporated ~
nothing else could use it. a CLI, an API, a web view, and a statewide
rollup all want that same answer, and if each computes it separately they
will drift and tell different stories about the same ground. so: one
measurement, many renderings. the warmth is a view over this, never a
substitute for it. ♡

it is a READ. it acquires nothing, composes nothing, writes nothing. asking
what a place could ask must never change the place. composing an experiment
(wondering.compose) and acquiring data (ResolutionEngine.acquire_types) are
capabilities that ACT, and they stay separate for that reason.

the shape mirrors the science: a plot holds data, a curiosity is a question,
a method is a way of answering it, and a verdict is what falls out of
comparing what the method needs against what the ground holds. P-03. ~
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path

from ..loam.readiness import holdings_by_type, _met
from .possibility import _load_dir, _candidate_methods, _choices_of, _root

CONFORMED_TIERS = ("tended", "gathered")
ALL_TIERS = ("arrived", "tended", "gathered")


@dataclass
class HoldingReading:
    """what this ground holds of one canonical type, and how full it is."""
    semantic_type: str
    count: int
    best_coverage: float | None
    worst_coverage: float | None
    thin: bool
    tiers: list[str] = field(default_factory=list)

    @property
    def conformed(self) -> bool:
        return any(t in CONFORMED_TIERS for t in self.tiers)


@dataclass
class RequirementReading:
    """one thing a method needs, and whether this ground offers it."""
    name: str
    accepts: list[str]          # alternatives ~ ANY of these satisfies it
    satisfied_by: str | None
    critical: bool
    uncertainty_without: str = ""
    thin: bool = False


@dataclass
class MethodReading:
    """a way of answering, weighed against what is here."""
    method_id: str
    method_name: str
    verdict: str                # runnable ~ runnable_with_uncertainty ~ blocked
    requirements: list[RequirementReading] = field(default_factory=list)
    choices: list[dict] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)

    @property
    def present(self) -> list[str]:
        return [r.satisfied_by for r in self.requirements if r.satisfied_by]

    @property
    def missing_critical(self) -> list[str]:
        return [r.accepts[0] for r in self.requirements
                if r.critical and not r.satisfied_by]

    @property
    def missing_enriching(self) -> list[str]:
        return [r.accepts[0] for r in self.requirements
                if not r.critical and not r.satisfied_by]


@dataclass
class CuriosityReading:
    """a question, and every way this ground could approach it."""
    curiosity_id: str
    question: str
    domain: str = ""
    significance: str = ""
    sub_questions: list[str] = field(default_factory=list)
    methods: list[MethodReading] = field(default_factory=list)

    @property
    def best_verdict(self) -> str:
        order = {"runnable": 0, "runnable_with_uncertainty": 1, "blocked": 2}
        if not self.methods:
            return "blocked"
        return min((m.verdict for m in self.methods), key=lambda v: order.get(v, 3))


@dataclass
class PlotReading:
    """
    everything wonder knows about one plot, at one moment.

    serializable by design: to_dict() is what an API returns and what a
    rollup aggregates. the CLI renders the same object warmly. neither is
    more authoritative than the other, because both read this. ~
    """
    plot: str
    plot_name: str = ""
    tiers: dict[str, int] = field(default_factory=dict)
    holdings: list[HoldingReading] = field(default_factory=list)
    curiosities: list[CuriosityReading] = field(default_factory=list)
    declared_unconformed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        # derived properties are part of the answer, not an implementation
        # detail of the renderer ~ an API consumer should not have to
        # recompute a verdict rollup.
        for cur, cur_d in zip(self.curiosities, d["curiosities"]):
            cur_d["best_verdict"] = cur.best_verdict
            for m, m_d in zip(cur.methods, cur_d["methods"]):
                m_d["present"] = m.present
                m_d["missing_critical"] = m.missing_critical
                m_d["missing_enriching"] = m.missing_enriching
        for h, h_d in zip(self.holdings, d["holdings"]):
            h_d["conformed"] = h.conformed
        return d

    @property
    def answerable_now(self) -> list[str]:
        return [c.curiosity_id for c in self.curiosities
                if c.best_verdict == "runnable"]


def _tier_counts(loam, plot: str) -> dict[str, int]:
    return {tier: loam.count(plot=plot, tier=tier) for tier in ALL_TIERS}


def _tiers_of(loam, plot: str, semantic_type: str) -> list[str]:
    return [tier for tier in ALL_TIERS
            if any(row.get("semantic_type") == semantic_type
                   for row in loam.find(plot=plot, tier=tier))]


def _read_holdings(loam, plot: str, floor: float) -> list[HoldingReading]:
    """
    every type this ground holds, conformed or merely arrived.

    holdings_by_type reads the conformed tiers only, because that is what
    satisfies a requirement. this also walks the bronze tier, so a holding
    that is declared and acquired but never run is visible ~ a state the
    system could not describe until the manifest was planted. ~
    """
    conformed = holdings_by_type(loam, plot)
    readings: list[HoldingReading] = []

    for sem, h in sorted(conformed.items()):
        readings.append(HoldingReading(
            semantic_type=sem, count=h.count,
            best_coverage=h.best_coverage, worst_coverage=h.worst_coverage,
            thin=h.is_thin(floor), tiers=_tiers_of(loam, plot, sem)))

    arrived_only = {row.get("semantic_type") for row in loam.find(plot=plot, tier="arrived")}
    arrived_only -= set(conformed)
    for sem in sorted(t for t in arrived_only if t):
        readings.append(HoldingReading(
            semantic_type=sem, count=1,
            best_coverage=None, worst_coverage=None,
            thin=False, tiers=["arrived"]))

    return readings


def _read_method(method: dict, conformed, floor: float) -> MethodReading:
    requirements: list[RequirementReading] = []
    uncertainties: list[str] = []

    for item in method.get("requires_data") or []:
        accepts = item.get("semantic_types") or ([item["type"]] if item.get("type") else [])
        if not accepts:
            continue
        hit = _met(accepts, conformed)
        critical = bool(item.get("critical", True))
        uncertainty = (item.get("uncertainty_without") or "").strip()
        thin = bool(hit and conformed[hit].is_thin(floor))

        requirements.append(RequirementReading(
            name=item.get("name", accepts[0]), accepts=list(accepts),
            satisfied_by=hit, critical=critical,
            uncertainty_without=uncertainty, thin=thin))

        if not hit and uncertainty:
            uncertainties.append(
                f"{'missing' if critical else 'without'} "
                f"{' / '.join(accepts)}: {uncertainty}")
        if thin:
            h = conformed[hit]
            uncertainties.append(
                f"{hit} is present but thin: the fullest of {h.count} "
                f"artifact(s) covers only {h.best_coverage:.0%}, below the "
                f"floor of {floor:.0%}.")

    if any(r.critical and not r.satisfied_by for r in requirements):
        verdict = "blocked"
    elif uncertainties or any(not r.satisfied_by for r in requirements):
        verdict = "runnable_with_uncertainty"
    else:
        verdict = "runnable"

    return MethodReading(
        method_id=method.get("id", "?"),
        method_name=method.get("name", method.get("id", "?")),
        verdict=verdict, requirements=requirements,
        choices=[{"name": n, "description": d} for n, d in _choices_of(method)],
        uncertainties=uncertainties)


def read_plot(loam, plot: str, *, plot_name: str = "",
              root: str | Path | None = None,
              coverage_floor: float | None = None) -> PlotReading:
    """
    read one plot ~ what it holds, and every question it could ask of that.

    the single computation behind every telling of this answer. ~
    """
    base = Path(root) if root else _root()
    floor = (coverage_floor if coverage_floor is not None
             else getattr(loam, "coverage_floor", 0.5))

    curiosities = _load_dir(base / "garden" / "curiosity-space")
    methods = _load_dir(base / "garden" / "methods")
    conformed = holdings_by_type(loam, plot)

    holdings = _read_holdings(loam, plot, floor)
    declared_unconformed = [h.semantic_type for h in holdings if not h.conformed]

    readings: list[CuriosityReading] = []
    for cur in curiosities.values():
        # a real curiosity is defined by its question; index files and
        # malformed docs are not questions and are not read as such.
        if not cur.get("question"):
            continue
        subs = [(s or {}).get("question", n)
                for n, s in (cur.get("sub_questions") or {}).items()]
        readings.append(CuriosityReading(
            curiosity_id=cur.get("id", "?"),
            question=cur["question"],
            domain=cur.get("domain", ""),
            significance=cur.get("significance", ""),
            sub_questions=subs,
            methods=[_read_method(m, conformed, floor)
                     for m in _candidate_methods(cur, methods)]))

    order = {"runnable": 0, "runnable_with_uncertainty": 1, "blocked": 2}
    readings.sort(key=lambda c: (order.get(c.best_verdict, 3), c.curiosity_id))

    return PlotReading(
        plot=plot, plot_name=plot_name or plot,
        tiers=_tier_counts(loam, plot),
        holdings=holdings,
        curiosities=readings,
        declared_unconformed=declared_unconformed)
