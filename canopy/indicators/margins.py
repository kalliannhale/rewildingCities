"""
canopy/indicators/margins.py
the Census's approximations for the margin of a derived estimate (D-258, D-259).

one home for the arithmetic in Python; derive_indicator.R holds the same
arithmetic in R, in the same order, and tests/test_derive_indicator_oracle.py
holds the two to each other exactly. the formulas are the Census's
"Instructions for Applying Statistical Testing to American Community Survey
Data" (2025 edition), the vintage that goes with ACS 2020-2024:

  ~ a sum or difference: the root of the sum of squared margins
  ~ a proportion (the numerator is part of the denominator): the root of
    MOE(A)^2 - P^2 MOE(B)^2, over B; when the value under the root is
    negative, the ratio formula instead, and the row says so
  ~ a ratio (the numerator is not part of the denominator): the root of
    MOE(A)^2 + P^2 MOE(B)^2, over B
  ~ a margin the Census marks controlled (-555555555, five stars) is 0

every derived margin is an approximation: the instructions say these
formulas leave out the correlation between estimates, so they may over- or
understate it. the 2025 instructions carry no rule for zero estimates in a
sum, so none is applied. the special case of a proportion equal to 1 has its
own formula, which the text read for this build did not show; such a row
says not_derived rather than guess it.
"""
from __future__ import annotations

import math

CONTROLLED = -555555555

PROPORTION, RATIO_FALLBACK, RATIO, SUM = "proportion", "ratio_fallback", "ratio", "sum"


def part_margin(moe: float | None, annotation: int | None) -> float | None:
    """one published estimate's margin: its own number, 0 when the Census
    marks the estimate controlled, otherwise none (never a guess)."""
    if moe is not None:
        return moe
    if annotation == CONTROLLED:
        return 0.0
    return None


def sum_margin(margins: list[float]) -> float:
    """the margin of a sum or difference of estimates. accumulated in order,
    one square at a time, as the R half does, so the two agree exactly."""
    acc = 0.0
    for m in margins:
        acc = acc + m * m
    return math.sqrt(acc)


def quotient_margin(num: float, num_moe: float, den: float, den_moe: float,
                    relation: str) -> tuple[float | None, str | None]:
    """the margin of num / den, unscaled, and the formula used. the
    denominator is never zero here: a zero denominator has no value."""
    p = num / den
    if relation == "proportion":
        if p == 1:
            return None, None
        rad = num_moe * num_moe - p * p * den_moe * den_moe
        formula = PROPORTION
        if rad < 0:
            rad = num_moe * num_moe + p * p * den_moe * den_moe
            formula = RATIO_FALLBACK
    else:
        rad = num_moe * num_moe + p * p * den_moe * den_moe
        formula = RATIO
    return math.sqrt(rad) / den, formula
