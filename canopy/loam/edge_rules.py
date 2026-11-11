"""
canopy/loam/edge_rules.py

edge rules ~ what may move along an edge, and what may only be read beside it

Contract 3 keeps Maine's geography as a graph: places, and weighted edges
between them. a value belongs to one place. this says what a reader may do
with a value when it looks across an edge, and it stores nothing: every
figure here is computed on read and returned, never written into the bed
(D-168). three questions, each answered from a declaration, never guessed:

  ~ which weight counts what this value rests on?
                  seeds/universes/universes.yml, keyed by the counts phrase
                  an indicator writes in rests_on (D-181). `equals` means the
                  weight is that universe's share; `contains` means the
                  weight's universe holds it. a phrase the seed does not
                  know has no weight, and the caller says so
  ~ does a town have none of it here?
                  zero_here (D-180): a weight of 0, or a null weight whose
                  reason says the town has none of that universe at all. a
                  `contains` weight answers this exactly, since none of the
                  larger universe means none of the smaller; it answers
                  nothing else
  ~ may a figure move?
                  may_allocate and allocate_count (D-179). only a measure
                  its seed declares `aggregation: sum` may be allocated,
                  and only by an `equals` weight, with a warning naming the
                  weight. a median, rate or percentage never moves

THE CONTRACT SITS ABOVE THE SEEDS. an indicator's `aggregation` says how its
publisher combines it upward: `population_weighted_mean` is how CII builds a
county from tracts. it never licenses building a district from its towns,
which Contract 3 rules 1 and 3 refuse outright: a district's value is the
ACS's own, and an overlaps edge yields a range, never a summed figure. so a
seed may forbid a move (`none`), and nothing in a seed grants one the
contract refuses. an allocated count is a fact about one edge, the part of
one town inside one place; nothing here adds edges up into a place. ~
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import yaml

UNIVERSES = Path("seeds") / "universes" / "universes.yml"
WEIGHTS = ("weight_households", "weight_population")
RELATIONS = ("equals", "contains")
EDGE_KINDS = ("contains", "overlaps")

# a null weight whose reason says the town has none of the universe at all
# means zero, by the weight's own definition (Contract 3 section 2)
NONE_AT_ALL = {"weight_households": "zero_households",
               "weight_population": "zero_population"}


class EdgeRuleRefused(ValueError):
    """a move along an edge that a declared rule refuses, with why."""


@dataclass(frozen=True)
class Universe:
    """what an indicator's value counts, and the edge weight that counts it."""
    counts: str
    weight: str
    relation: str
    reason: str = ""


@dataclass(frozen=True)
class Allocation:
    """an allocated count: a fact about one edge, never about a place."""
    figure: float
    weight_column: str
    weight: float
    warning: str


def _number(x) -> float | None:
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def load_universes(root: str | Path) -> dict[str, Universe]:
    """the declared universes, keyed by counts phrase. an empty dict when the
    seed is absent; a malformed entry is refused by name, never skipped."""
    path = Path(root) / UNIVERSES
    if not path.is_file():
        return {}
    doc = yaml.safe_load(path.read_text()) or {}
    out: dict[str, Universe] = {}
    for counts, spec in (doc.get("universes") or {}).items():
        spec = spec or {}
        weight, relation = spec.get("weight"), spec.get("relation")
        if weight not in WEIGHTS:
            raise ValueError(f"{UNIVERSES}: '{counts}' names weight {weight!r}; "
                             f"an edge carries {' and '.join(WEIGHTS)}")
        if relation not in RELATIONS:
            raise ValueError(f"{UNIVERSES}: '{counts}' says relation {relation!r}; "
                             f"a universe is {' or '.join(RELATIONS)} its weight's")
        out[str(counts)] = Universe(counts=str(counts), weight=weight, relation=relation,
                                    reason=" ".join(str(spec.get("reason") or "").split()))
    return out


def universe_for(counts, universes: dict[str, Universe]) -> Universe | None:
    """the declared universe for a counts phrase, matched exactly, or None."""
    if not counts or not isinstance(counts, str):
        return None
    return universes.get(counts)


def zero_here(edge: dict, universe: Universe | None) -> tuple[bool | None, str]:
    """
    does this edge's town have none of the universe in the other place (D-180)?
    True with why, False, or None with why it cannot be told. ~
    """
    if universe is None:
        return None, "no declared universe says which weight counts this value"
    w = _number(edge.get(universe.weight))
    if w is None:
        reason = edge.get("weight_reason") or ""
        if reason == NONE_AT_ALL.get(universe.weight):
            return True, f"the town has none at all ({reason})"
        return None, f"its {universe.weight} is empty ({reason or 'no reason given'})"
    if w == 0:
        return True, f"none of its {universe.counts} are here"
    return False, ""


def share_of(edge: dict, universe: Universe | None) -> tuple[float | None, str]:
    """the share to show beside a value, or None with why. only an `equals`
    weight is a universe's share (D-181)."""
    if universe is None:
        return None, "no declared universe says which weight counts this value"
    if universe.relation != "equals":
        return None, (f"the graph has no weight that counts {universe.counts}; "
                      f"{universe.weight} only contains it")
    w = _number(edge.get(universe.weight))
    if w is None:
        return None, f"its {universe.weight} is empty ({edge.get('weight_reason') or 'no reason given'})"
    return w, ""


def may_allocate(indicator: dict) -> tuple[bool, str]:
    """
    may this indicator's value be allocated along an edge (D-179)? only when
    its seed declares `aggregation: sum`. anything else is refused, quoting
    the declaration, because the contract sits above the seed. ~
    """
    name = indicator.get("id") or indicator.get("name") or "this indicator"
    declared = indicator.get("aggregation")
    if declared == "sum":
        return True, f"{name} declares aggregation: sum, so a count of it may be allocated"
    if declared == "population_weighted_mean":
        return False, (f"{name} declares aggregation: population_weighted_mean, how its "
                       f"publisher combines it upward. a share never moves along an edge: a "
                       f"district's value is the ACS's own and an overlaps edge yields a range, "
                       f"never a summed figure (Contract 3 rules 1 and 3, D-179)")
    return False, (f"{name} declares aggregation: {declared!r}, so it never moves along an "
                   f"edge; a median is never combined (D-27) and only a declared sum is "
                   f"allocated (D-179)")


def allocate_count(n, edge: dict, universe: Universe | None) -> Allocation:
    """
    allocate a raw count along one edge: about how much of the town's count
    lies inside the other place (D-179). refused unless the universe equals
    its weight and the weight is a number. the result is the part of one
    town in one place; it is never added to another edge's. ~
    """
    count = _number(n)
    if count is None:
        raise EdgeRuleRefused(f"{n!r} is not a count")
    if universe is None:
        raise EdgeRuleRefused("no declared universe says which weight counts this; "
                              "a count is never allocated by a guessed weight (D-181)")
    if universe.relation != "equals":
        raise EdgeRuleRefused(f"{universe.weight} only contains {universe.counts}, so it "
                              f"is not their share and allocates nothing (D-181)")
    kind = edge.get("kind")
    if kind not in EDGE_KINDS:
        raise EdgeRuleRefused(f"a count moves only along {' or '.join(EDGE_KINDS)} edges, "
                              f"not {kind!r}")
    w = _number(edge.get(universe.weight))
    if w is None:
        raise EdgeRuleRefused(f"its {universe.weight} is empty "
                              f"({edge.get('weight_reason') or 'no reason given'}), "
                              f"so nothing can be allocated")
    figure = count * w
    ends = (f"{edge.get('from_authority')} {edge.get('from_code')} to "
            f"{edge.get('to_authority')} {edge.get('to_code')}")
    warning = (f"allocated, not measured: {count:,.0f} {universe.counts} times "
               f"{universe.weight} {w:.4f} is about {figure:,.0f}, along {ends}. the weight "
               f"rests on {edge.get('source') or 'its source'} ({edge.get('vintage') or 'vintage unknown'}) "
               f"and the count on its own release, so their vintages may differ. computed on "
               f"read, never stored (D-168, D-179)")
    return Allocation(figure=figure, weight_column=universe.weight, weight=w, warning=warning)
