"""
canopy/standards.py

standards ~ what every person in a place is owed, read once

a standard (D-270) names barriers, the measures of each, and each barrier's
sides: universal, trigger or none (D-199). its shape is one file,
seeds/schemas/standard.schema.yml; this module reads a standard through it
and then checks what a schema cannot say:

  ~ every measure a barrier or a side names is declared under measures
  ~ every measure belongs to exactly one barrier: membership has one home,
    here, and the registry keeps only role (D-270)
  ~ every indicator a measure names is registered, and every registered
    indicator whose role is barrier is a measure of this standard
  ~ a universal side judges one count: an indicator derived as a count, or
    an artifact measure, whose people are counted against zero (D-272)
  ~ a trigger's groups name measures of their own barrier, and its tiers
    use only the quantities the groups name; as_published names an artifact
  ~ a measure not acquired says where it would come from and what it needs
  ~ a measure's estimate kind is inferred from its indicator where the
    registry says it (acs_moe is a survey, located_count is administrative),
    and declared everywhere else, so no kind is ever guessed

every problem is named at once, and nothing is read from a standard that
fails. load_standard reads; it decides nothing about any place. ~
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

STANDARD_SCHEMA = Path("seeds") / "schemas" / "standard.schema.yml"
STANDARDS = Path("seeds") / "standards"

SIDE_KINDS = ("universal", "trigger", "none")
STATUSES = ("acquired", "acquirable", "needs_our_model", "needs_consent")


class StandardShapeError(ValueError):
    """a standard the standard schema does not describe, or whose names do
    not resolve. ~"""


@dataclass(frozen=True)
class Measure:
    id: str
    status: str
    indicator: str | None = None
    artifact: str | None = None
    measure: str | None = None
    estimate_kind: str | None = None
    method: str | None = None
    source: str | None = None
    needs: str | None = None
    unit: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class Side:
    id: str
    kind: str
    statement: str
    source: dict
    declared_by: str
    judges: str | None = None
    groups: tuple = ()
    tiers: tuple = ()
    below_every_tier: str | None = None
    as_published: str | None = None
    limits: str | None = None

    def as_dict(self) -> dict:
        out = {"id": self.id, "kind": self.kind, "statement": self.statement.strip(),
               "source": dict(self.source), "declared_by": self.declared_by}
        for key in ("judges", "below_every_tier", "as_published"):
            if getattr(self, key):
                out[key] = getattr(self, key)
        if self.limits:
            out["limits"] = self.limits.strip()
        if self.groups:
            out["groups"] = [dict(g) for g in self.groups]
        if self.tiers:
            out["tiers"] = [dict(t) for t in self.tiers]
        return out


@dataclass(frozen=True)
class Barrier:
    id: str
    words: str
    measures: tuple
    sides: tuple


@dataclass(frozen=True)
class Standard:
    id: str
    version: str
    name: str
    declared_by: str
    framework: dict
    decided_in: tuple
    measures: dict = field(default_factory=dict)       # id -> Measure
    barriers: tuple = ()                                # Barrier, in file order
    path: str = ""
    sha256: str = ""

    def barrier_of(self, measure_id: str) -> Barrier:
        return next(b for b in self.barriers if measure_id in b.measures)

    def header(self) -> dict:
        """what a profile says about the standard it was judged against."""
        return {"id": self.id, "version": self.version, "name": self.name,
                "declared_by": self.declared_by, "framework": dict(self.framework),
                "file": self.path, "sha256": self.sha256}


@lru_cache(maxsize=None)
def _validator(project_root: str):
    import jsonschema
    with open(Path(project_root) / STANDARD_SCHEMA, "r") as f:
        schema = yaml.safe_load(f)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def shape_problems(data, project_root: str | Path) -> list[str]:
    """every way a standard departs from its schema, one line each."""
    if not isinstance(data, dict):
        return [f"a standard is a mapping; this file holds {type(data).__name__}"]
    validator = _validator(str(project_root))
    return [f"{'.'.join(str(p) for p in e.absolute_path) or '(top level)'}: {e.message}"
            for e in sorted(validator.iter_errors(data),
                            key=lambda e: list(map(str, e.absolute_path)))]


def _inferred_kind(indicator) -> str | None:
    """what the registry already says about how an indicator was estimated.
    anything else must be declared in the standard, never guessed."""
    if indicator.derivation.kind == "located_count":
        return "administrative"
    if indicator.uncertainty == "acs_moe":
        return "survey"
    return None


def name_problems(data: dict, registry) -> list[str]:
    """every name in a well-shaped standard that does not resolve, and
    every barrier indicator without its one home (D-270)."""
    problems: list[str] = []
    measures = data["measures"]
    barriers = data["barriers"]

    homes: dict[str, list[str]] = {}
    for b_id, barrier in barriers.items():
        for m in barrier["measures"]:
            homes.setdefault(m, []).append(b_id)
            if m not in measures:
                problems.append(f"barriers.{b_id}.measures: '{m}' is not declared under measures")
    for m, where in homes.items():
        if len(where) > 1:
            problems.append(f"measures.{m}: named by {len(where)} barriers ({', '.join(where)}); "
                            f"a measure belongs to one barrier (D-270)")
    for m in measures:
        if m not in homes:
            problems.append(f"measures.{m}: no barrier names it")

    known = set(registry.all())
    for m_id, m in measures.items():
        where = f"measures.{m_id}"
        if m.get("indicator") and m.get("artifact"):
            problems.append(f"{where}: names both an indicator and an artifact; a measure is one")
        if m["status"] == "acquired" and not (m.get("indicator") or m.get("artifact")):
            problems.append(f"{where}: acquired, yet names no indicator or artifact to read")
        if m["status"] != "acquired" and not (m.get("source") and m.get("needs")):
            problems.append(f"{where}: {m['status']} needs both source and needs, so part 5 "
                            f"can say where it would come from and what acquiring it takes")
        ind = m.get("indicator")
        if ind:
            if ind not in known:
                problems.append(f"{where}: indicator '{ind}' is not registered")
                continue
            if not m.get("estimate_kind") and _inferred_kind(registry.get(ind)) is None:
                problems.append(f"{where}: the registry cannot say how '{ind}' was estimated; "
                                f"declare estimate_kind")
        elif m.get("artifact") and not m.get("estimate_kind"):
            problems.append(f"{where}: an artifact measure declares its estimate_kind")

    named = {m.get("indicator") for m in measures.values() if m.get("indicator")}
    for ind in registry.with_role("barrier"):
        if ind not in named:
            problems.append(f"indicator '{ind}' has role barrier but no barrier of this standard "
                            f"names it; barrier membership lives here (D-270)")

    for b_id, barrier in barriers.items():
        own = set(barrier["measures"])
        for i, side in enumerate(barrier["sides"]):
            where = f"barriers.{b_id}.sides[{i}] ({side['id']})"
            problems += _side_problems(where, side, own, measures, registry)
        ids = [s["id"] for s in barrier["sides"]]
        if len(ids) != len(set(ids)):
            problems.append(f"barriers.{b_id}.sides: a side id is written twice")
        kinds = {s["kind"] for s in barrier["sides"]}
        if "none" in kinds and len(kinds) > 1:
            problems.append(f"barriers.{b_id}.sides: a side of kind none stands alone")
    return problems


def _side_problems(where: str, side: dict, own: set, measures: dict, registry) -> list[str]:
    kind = side["kind"]
    problems = []
    allowed = {"universal": {"judges"}, "trigger": {"groups", "tiers", "below_every_tier",
               "as_published"}, "none": set()}[kind]
    for key in ("judges", "groups", "tiers", "below_every_tier", "as_published"):
        if key in side and key not in allowed:
            problems.append(f"{where}: a {kind} side does not carry {key}")

    def in_barrier(m: str, label: str) -> None:
        if m not in own:
            problems.append(f"{where}: {label} '{m}' is not a measure of this barrier")

    if kind == "universal":
        judged = side.get("judges")
        if not judged:
            problems.append(f"{where}: a universal side judges one count (D-272)")
        else:
            in_barrier(judged, "judges")
            m = measures.get(judged) or {}
            ind = m.get("indicator")
            if ind and ind in set(registry.all()) and registry.get(ind).derivation.kind != "count":
                problems.append(f"{where}: judges '{judged}', which is not a count; a universal "
                                f"side counts the people short of its line (D-272)")
    if kind == "trigger":
        published = side.get("as_published")
        if published:
            if side.get("groups") or side.get("tiers"):
                problems.append(f"{where}: as_published reports a determination; it carries no "
                                f"groups or tiers of ours (D-273)")
            in_barrier(published, "as_published")
            if not (measures.get(published) or {}).get("artifact"):
                problems.append(f"{where}: as_published names '{published}', which is not an "
                                f"artifact measure")
        else:
            if not (side.get("groups") and side.get("tiers") and side.get("below_every_tier")):
                problems.append(f"{where}: a trigger of ours needs groups, tiers and "
                                f"below_every_tier")
            quantities = set()
            for g in side.get("groups") or []:
                quantities |= set(g["quantities"])
                for q, m in g["quantities"].items():
                    in_barrier(m, f"group {g['group']!r}, {q}")
            for t in side.get("tiers") or []:
                for cond in t["when_any"]:
                    for q in cond:
                        if q not in quantities:
                            problems.append(f"{where}: tier '{t['id']}' names '{q}', which no "
                                            f"group's quantities declare")
            tier_ids = [t["id"] for t in side.get("tiers") or []]
            if len(tier_ids) != len(set(tier_ids)):
                problems.append(f"{where}: a tier id is written twice")
    return problems


def _measure(m_id: str, m: dict, registry) -> Measure:
    kind = m.get("estimate_kind")
    if not kind and m.get("indicator") in set(registry.all()):
        kind = _inferred_kind(registry.get(m["indicator"]))
    return Measure(id=m_id, status=m["status"], indicator=m.get("indicator"),
                   artifact=m.get("artifact"), measure=m.get("measure"), estimate_kind=kind,
                   method=m.get("method"), source=m.get("source"), needs=m.get("needs"),
                   unit=m.get("unit"), note=m.get("note"))


def _side(s: dict) -> Side:
    return Side(id=s["id"], kind=s["kind"], statement=s["statement"], source=s["source"],
                declared_by=s["declared_by"], judges=s.get("judges"),
                groups=tuple(s.get("groups") or ()), tiers=tuple(s.get("tiers") or ()),
                below_every_tier=s.get("below_every_tier"),
                as_published=s.get("as_published"), limits=s.get("limits"))


def load_standard(standard_id: str, *, root: str | Path, registry=None) -> Standard:
    """read seeds/standards/<id>.yml, or refuse it naming every problem."""
    from canopy.orchestrator.registry import UniqueKeyLoader
    root = Path(root)
    path = root / STANDARDS / f"{standard_id}.yml"
    if not path.is_file():
        raise StandardShapeError(f"no standard at {path.relative_to(root)}")
    raw = path.read_bytes()
    data = yaml.load(raw.decode("utf-8"), Loader=UniqueKeyLoader)
    problems = shape_problems(data, root)
    if not problems:
        if registry is None:
            from canopy.indicators import IndicatorRegistry
            registry = IndicatorRegistry.load(root / "seeds" / "indicators")
        problems = name_problems(data, registry)
        if not problems and data["standard"]["id"] != standard_id:
            problems = [f"standard.id: '{data['standard']['id']}' is not its file's name "
                        f"'{standard_id}'"]
    if problems:
        raise StandardShapeError(
            f"{path.relative_to(root)} does not hold as a standard (D-270):\n  - "
            + "\n  - ".join(problems))

    head = data["standard"]
    return Standard(
        id=head["id"], version=str(head["version"]), name=head["name"],
        declared_by=head["declared_by"], framework=dict(head["framework"]),
        decided_in=tuple(head.get("decided_in") or ()),
        measures={m_id: _measure(m_id, m, registry) for m_id, m in data["measures"].items()},
        barriers=tuple(Barrier(id=b_id, words=b["words"], measures=tuple(b["measures"]),
                               sides=tuple(_side(s) for s in b["sides"]))
                       for b_id, b in data["barriers"].items()),
        path=str(path.relative_to(root)), sha256=hashlib.sha256(raw).hexdigest())
