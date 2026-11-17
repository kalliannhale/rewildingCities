"""
canopy/wonder/verdicts.py

verdicts ~ a place's own value, held against a stated line

every rule a profile judges with lives here, as plain functions of numbers,
so each can be read and tested without a bed. they decide; profile.py only
gathers what they decide on and writes it down.

  ~ a universal side (D-272) is judged once, on its count of people short
    of the line, against zero: `below` when the count less its margin is
    above zero, so someone is short at the margin's confidence;
    `within_margin` otherwise. `meets` is never reached by an estimate: a
    margin can show that someone is left out, never that no one is, and
    every universal verdict says so. a model's count is judged by its
    credible bounds the same way (literacy, D-272)
  ~ a trigger of ours (D-273) is judged per group, over every value its
    margins allow. its tiers use only at-least conditions, so a tier can
    change only where a quantity passes one of the tiers' own numbers:
    judging the margins' ends and every such number between them finds
    every tier a value inside could be in. one tier, and the group
    `crosses` it (or `does_not_cross`, below every tier); several, and it
    is `within_margin`, naming each tier it could truly be in
  ~ a publisher's own determination is reported `as_published`; no margin
    of ours touches it (D-263, D-273)
  ~ `cannot_judge` always says why, in plain words, and `no_threshold`
    belongs to a barrier whose side is of kind none

every verdict carries `says`: one sentence a reader who is not a
statistician can act on, written so that `within_margin` never reads as a
pass. ~
"""

from __future__ import annotations

import math
from dataclasses import dataclass

VERDICTS = ("meets", "below", "within_margin", "cannot_judge", "no_threshold",
            "crosses", "does_not_cross", "as_published")

MEETS_UNREACHABLE = ("an estimate can show that someone is left out, never that no one "
                     "is, so this standard never says a place meets it (D-272)")


@dataclass(frozen=True)
class Verdict:
    verdict: str
    says: str
    reason: str = ""
    tier: str | None = None
    tiers_possible: tuple = ()
    left_out: dict | None = None

    def as_dict(self) -> dict:
        out = {"verdict": self.verdict, "says": self.says}
        if self.reason:
            out["reason"] = self.reason
        if self.tier is not None:
            out["tier"] = self.tier
        if self.tiers_possible:
            out["tiers_possible"] = list(self.tiers_possible)
        if self.left_out is not None:
            out["left_out"] = dict(self.left_out)
        return out


def number(x) -> float | None:
    """a number, or None for anything that is not one (NaN included)."""
    if x is None or isinstance(x, bool):
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def cannot_judge(reason: str) -> Verdict:
    return Verdict("cannot_judge", f"this cannot be judged here: {reason}", reason=reason)


def no_threshold(shown: bool = True, why: str = "") -> Verdict:
    """a barrier with no threshold: its value is shown, never judged. when the
    entry holds no value (not acquired, withheld, absent), it says that, never
    that a value is shown (NOTHR-1)."""
    if shown:
        return Verdict("no_threshold", "no threshold is declared for this barrier, so this "
                                       "value is shown and never judged")
    said = f": {why}" if why else ""
    return Verdict("no_threshold", f"no threshold is declared for this barrier, and there "
                                   f"is no value here to show{said}", reason=why)


def _people(n: float) -> str:
    return f"{n:,.0f}"


def universal_on_count(estimate, moe, *, counts: str, confidence: float | None) -> Verdict:
    """D-272: the count of people short of a universal line, against zero."""
    estimate, moe = number(estimate), number(moe)
    if estimate is None:
        return cannot_judge("there is no estimate of this count here")
    if moe is None:
        return cannot_judge("the count carries no margin to judge it with")
    if estimate < 0 or moe < 0:
        return cannot_judge("the count or its margin is negative, which no count can be")
    low, high = max(estimate - moe, 0.0), estimate + moe
    left_out = {"count": estimate, "lower": low, "upper": high, "counts": counts,
                "confidence": confidence, "bounds": "estimate less and plus its margin"}
    if estimate - moe > 0:
        return Verdict("below", f"at least {_people(low)} {counts} here fall short of this "
                                f"line, at the margin's confidence; the estimate is "
                                f"{_people(estimate)}", left_out=left_out)
    return Verdict("within_margin", f"the data cannot say whether any {counts} here fall "
                                    f"short; this does not show that everyone is reached",
                   left_out=left_out)


def universal_on_interval(estimate, lower, upper, *, counts: str,
                          confidence: float | None) -> Verdict:
    """D-272 for a model's count with credible bounds (literacy)."""
    estimate, lower, upper = number(estimate), number(lower), number(upper)
    if estimate is None:
        return cannot_judge("there is no estimate of this count here")
    if lower is None or upper is None:
        return cannot_judge("the count carries no interval to judge it with")
    if not lower <= estimate <= upper:
        return cannot_judge("the estimate lies outside its own interval")
    left_out = {"count": estimate, "lower": lower, "upper": upper, "counts": counts,
                "confidence": confidence, "bounds": "credible interval"}
    if lower > 0:
        return Verdict("below", f"at least {_people(lower)} {counts} here fall short of this "
                                f"line, at the interval's confidence; the estimate is "
                                f"{_people(estimate)}", left_out=left_out)
    return Verdict("within_margin", f"the data cannot say whether any {counts} here fall "
                                    f"short; this does not show that everyone is reached",
                   left_out=left_out)


def tier_of(values: dict, tiers) -> str | None:
    """the first tier, highest first, any of whose conditions holds; None
    below every tier. a condition holds when every quantity it names is at
    least its number."""
    for tier in tiers:
        for cond in tier["when_any"]:
            if all(values[q] >= floor for q, floor in cond.items()):
                return tier["id"]
    return None


def tiers_within(low: dict, high: dict, tiers) -> set:
    """every tier some value inside the margins could be in. a tier changes
    only where a quantity passes one of the tiers' own numbers, so judging
    each margin's two ends and every number between them, in every
    combination, finds every tier the box holds, and no tier it does not:
    two ends alone would count the tiers between them, reachable or not."""
    from itertools import product
    floors: dict = {q: set() for q in low}
    for tier in tiers:
        for cond in tier["when_any"]:
            for q, floor in cond.items():
                floors[q].add(floor)
    axes = [sorted({low[q], high[q]} | {f for f in floors[q] if low[q] <= f <= high[q]})
            for q in low]
    names = list(low)
    return {tier_of(dict(zip(names, point)), tiers) for point in product(*axes)}


def trigger_on_group(quantities: dict, tiers, *, below_every_tier: str) -> Verdict:
    """D-273, one group: `quantities` maps each quantity the tiers name to
    (estimate, margin), judged over every value its margins allow."""
    low, high = {}, {}
    for q, (estimate, moe) in quantities.items():
        estimate, moe = number(estimate), number(moe)
        if estimate is None:
            return cannot_judge(f"there is no estimate of its {q} here")
        if moe is None:
            return cannot_judge(f"its {q} carries no margin to judge it with")
        low[q], high[q] = max(estimate - moe, 0.0), estimate + moe
    says = {t["id"]: t["says"] for t in tiers}
    reachable = tiers_within(low, high, tiers)
    if len(reachable) == 1:
        (only,) = reachable
        if only is None:
            return Verdict("does_not_cross", f"below every tier at both ends of its margins: "
                                             f"{below_every_tier}")
        return Verdict("crosses", f"crosses at both ends of its margins: {says[only]}",
                       tier=only)
    order = [t["id"] for t in tiers] + [None]
    possible = [t for t in order if t in reachable]
    named = [says[t] if t else below_every_tier for t in possible]
    return Verdict("within_margin", "the margins cannot say which applies: "
                                    + ", or ".join(named),
                   tiers_possible=tuple(t or "below_every_tier" for t in possible))


def as_published(covered: list[str], determined: int, *, publisher: str) -> Verdict:
    """D-273: a published determination, reported as its publisher made it:
    the groups it determined covered, of how many it determined."""
    if not determined:
        return cannot_judge(f"{publisher} publishes no determination for this place")
    if covered:
        return Verdict("as_published", f"{publisher} determined these groups covered: "
                                       + "; ".join(covered))
    return Verdict("as_published", f"{publisher} determined no group covered here")


def borrowed_shares(parts) -> list[dict]:
    """D-276: the coarser places a value comes from, each with its share of
    this place's residents. `parts` is (key, residents_here) pairs, a key
    seen more than once summed. a place with no residents has no shares."""
    totals: dict = {}
    for key, residents in parts:
        residents = number(residents)
        if residents is None or residents < 0:
            raise ValueError(f"residents for {key} must be a count, got {residents!r}")
        totals[key] = totals.get(key, 0.0) + residents
    whole = sum(totals.values())
    return [{"key": key, "residents_here": n, "share": (n / whole if whole else None)}
            for key, n in sorted(totals.items(), key=lambda kv: (-kv[1], str(kv[0])))]


def comparable(unit_a: str, unit_b: str) -> bool:
    """two values of one measure can be subtracted when their units match,
    or both are percents of it (the measure fixes what they are percents
    of). anything else is shown side by side with no difference."""
    if unit_a == unit_b:
        return True
    return unit_a.split("_")[0] == "percent" and unit_b.split("_")[0] == "percent"
