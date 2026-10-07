"""
canopy/indicators.py

indicators ~ what a number means, declared once

a semantic type names a kind of artifact. an indicator names a claim: which
numerator over which denominator, in what unit, which direction is better,
how it composes across units, and where its uncertainty comes from. those
facts belong to the indicator, not the type, because one table of
indicator_values holds counts that sum, rates that weight, and ranks that
refuse to combine at all.

every indicator is declared in seeds/indicators/*.yml and read here. names
are flat and global across files, so cii_2026.yml and rewilding.yml can sit
side by side and the difference between CII's framing and ours is a diff
between two files rather than an edit to one.

loud the same way the vocabulary is, because a registry that guesses hands
every derivation a plausible answer to a question nobody asked:

  ~ an indicator id declared twice     -> refuse, naming both files
  ~ a required field missing           -> refuse, naming the field
  ~ an unknown field                   -> refuse, so a typo is not a silent omission
  ~ a value outside its enum           -> refuse, listing what is allowed
  ~ a weighted mean with no weight     -> refuse
  ~ acs_moe over a non-estimate code   -> refuse, since no _M sibling exists
  ~ the indicators directory empty     -> refuse

vintage is deliberately absent. one definition spans many releases; the
year belongs to the manifest's acquisition. ♡
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DIRECTIONS = ("higher_is_better", "higher_is_worse")
AGGREGATIONS = ("sum", "population_weighted_mean", "none", "profile", "recompute")
UNCERTAINTIES = ("acs_moe", "published_interval", "none")
DERIVATION_KINDS = ("ratio", "passthrough")

REQUIRED = ("name", "defined_by", "measures", "unit", "derivation",
            "direction", "aggregation", "uncertainty", "source")
OPTIONAL = ("weight_by", "replicates", "rationale")
KNOWN = REQUIRED + OPTIONAL

REPLICATES_REQUIRED = ("publisher", "edition", "column")


@dataclass(frozen=True)
class Derivation:
    kind: str                                   # ratio | passthrough
    numerator: tuple[str, ...] = ()
    denominator: str | None = None
    scale: float = 1.0
    column: str | None = None                   # passthrough only


@dataclass(frozen=True)
class Indicator:
    id: str
    name: str
    defined_by: str
    measures: str
    unit: str
    derivation: Derivation
    direction: str
    aggregation: str
    uncertainty: str
    source: dict
    weight_by: str | None = None
    replicates: dict | None = None
    rationale: str = ""
    declared_in: str = ""

    def estimate_variables(self) -> list[str]:
        """every source column this indicator reads, in a stable order."""
        d = self.derivation
        cols = list(d.numerator)
        if d.denominator:
            cols.append(d.denominator)
        if d.column:
            cols.append(d.column)
        if self.weight_by:
            cols.append(self.weight_by)
        seen: list[str] = []
        for c in cols:
            if c not in seen:
                seen.append(c)
        return seen

    def moe_variables(self) -> list[str]:
        """the ACS margin-of-error sibling of each estimate, if acs_moe."""
        if self.uncertainty != "acs_moe":
            return []
        return [v[:-1] + "M" for v in self.estimate_variables()]

    def acquisition_variables(self) -> list[str]:
        """what an acquisition must fetch for this indicator to be derived."""
        return self.estimate_variables() + self.moe_variables()


class IndicatorRegistry:
    """every declared indicator, across seeds/indicators/*.yml."""

    def __init__(self, indicators: dict[str, Indicator]):
        self._indicators = indicators

    @classmethod
    def load(cls, indicators_dir: str | Path) -> "IndicatorRegistry":
        root = Path(indicators_dir)
        files = sorted(root.glob("*.yml")) if root.is_dir() else []
        if not files:
            raise FileNotFoundError(
                f"no indicator declarations found at {root}\n"
                f"  a missing directory and an empty one look identical from here,\n"
                f"  and a registry with nothing in it would let every derivation\n"
                f"  fail later and further from the cause. expected *.yml files.")

        indicators: dict[str, Indicator] = {}
        for f in files:
            doc = yaml.safe_load(f.read_text()) or {}
            for ind_id, spec in (doc.get("indicators") or {}).items():
                label = f"{root.name}/{f.name}"
                if ind_id in indicators:
                    raise ValueError(
                        f"indicator id collision: '{ind_id}' is declared in both "
                        f"'{indicators[ind_id].declared_in}' and '{label}'. ids are "
                        f"flat and global across files; rename one of them.")
                indicators[ind_id] = cls._parse(ind_id, spec or {}, label)
        return cls(indicators)

    @staticmethod
    def _parse(ind_id: str, spec: dict, label: str) -> Indicator:
        where = f"indicator '{ind_id}' ({label})"

        unknown = [k for k in spec if k not in KNOWN]
        if unknown:
            raise ValueError(
                f"{where} has unknown field(s): {', '.join(unknown)}. "
                f"known fields: {', '.join(KNOWN)}. an unknown field is refused "
                f"rather than ignored, because a misspelled optional field would "
                f"otherwise vanish without a trace.")

        missing = [k for k in REQUIRED if k not in spec or spec[k] in (None, "")]
        if missing:
            raise ValueError(f"{where} is missing required field(s): {', '.join(missing)}")

        def enum(fieldname: str, allowed: tuple[str, ...]) -> str:
            v = spec[fieldname]
            if v not in allowed:
                raise ValueError(
                    f"{where}: {fieldname} '{v}' is not one of: {', '.join(allowed)}")
            return v

        direction = enum("direction", DIRECTIONS)
        aggregation = enum("aggregation", AGGREGATIONS)
        uncertainty = enum("uncertainty", UNCERTAINTIES)

        weight_by = spec.get("weight_by")
        if aggregation == "population_weighted_mean" and not weight_by:
            raise ValueError(
                f"{where}: aggregation is population_weighted_mean but no weight_by "
                f"is declared. a weighted mean without a weight is a mean of means.")

        derivation = IndicatorRegistry._parse_derivation(where, spec["derivation"])

        source = spec["source"]
        if not isinstance(source, dict) or not source.get("provider"):
            raise ValueError(f"{where}: source must be a mapping with a provider")

        replicates = spec.get("replicates")
        if replicates is not None:
            if not isinstance(replicates, dict):
                raise ValueError(f"{where}: replicates must be a mapping")
            r_missing = [k for k in REPLICATES_REQUIRED if not replicates.get(k)]
            if r_missing:
                raise ValueError(
                    f"{where}: replicates is missing {', '.join(r_missing)}. a claim "
                    f"to reproduce a published value must say exactly which one.")

        ind = Indicator(
            id=ind_id,
            name=spec["name"],
            defined_by=spec["defined_by"],
            measures=spec["measures"],
            unit=spec["unit"],
            derivation=derivation,
            direction=direction,
            aggregation=aggregation,
            uncertainty=uncertainty,
            source=dict(source),
            weight_by=weight_by,
            replicates=dict(replicates) if replicates else None,
            rationale=(spec.get("rationale") or "").strip(),
            declared_in=label,
        )

        if uncertainty == "acs_moe":
            if source.get("provider") != "census_acs":
                raise ValueError(
                    f"{where}: uncertainty acs_moe is declared but the provider is "
                    f"'{source.get('provider')}'. only the ACS publishes _M siblings.")
            not_estimates = [v for v in ind.estimate_variables()
                             if not (isinstance(v, str) and "_" in v and v.endswith("E"))]
            if not_estimates:
                raise ValueError(
                    f"{where}: uncertainty acs_moe needs every variable to be an ACS "
                    f"estimate code ending in E, so its margin-of-error sibling can be "
                    f"fetched. not estimates: {', '.join(map(str, not_estimates))}")

        return ind

    @staticmethod
    def _parse_derivation(where: str, d: dict) -> Derivation:
        if not isinstance(d, dict):
            raise ValueError(f"{where}: derivation must be a mapping")

        kind = d.get("kind")
        if kind not in DERIVATION_KINDS:
            raise ValueError(
                f"{where}: derivation kind '{kind}' is not one of: "
                f"{', '.join(DERIVATION_KINDS)}")

        if kind == "ratio":
            numerator = d.get("numerator")
            if not isinstance(numerator, list) or not numerator:
                raise ValueError(
                    f"{where}: a ratio needs numerator as a non-empty list, even for "
                    f"one variable, so a sum of several is never mistaken for one")
            denominator = d.get("denominator")
            if not denominator or not isinstance(denominator, str):
                raise ValueError(f"{where}: a ratio needs a single denominator")
            scale = d.get("scale", None)
            if not isinstance(scale, (int, float)) or isinstance(scale, bool) or scale <= 0:
                raise ValueError(
                    f"{where}: a ratio needs a positive numeric scale (100 for a "
                    f"percent, 1 for a proportion). no default: a rate off by a "
                    f"factor of 100 still looks like a rate.")
            extra = [k for k in d if k not in ("kind", "numerator", "denominator", "scale")]
            if extra:
                raise ValueError(f"{where}: unknown derivation field(s): {', '.join(extra)}")
            return Derivation(kind="ratio", numerator=tuple(numerator),
                              denominator=denominator, scale=float(scale))

        column = d.get("column")
        if not column or not isinstance(column, str):
            raise ValueError(f"{where}: a passthrough needs a single column")
        extra = [k for k in d if k not in ("kind", "column")]
        if extra:
            raise ValueError(f"{where}: unknown derivation field(s): {', '.join(extra)}")
        return Derivation(kind="passthrough", column=column)

    # ── read surface ───────────────────────────────────────────────────────
    def get(self, ind_id: str) -> Indicator:
        if ind_id not in self._indicators:
            raise KeyError(
                f"unknown indicator: '{ind_id}'\n"
                f"  {len(self._indicators)} declared: {', '.join(sorted(self._indicators))}")
        return self._indicators[ind_id]

    def all(self) -> list[str]:
        return sorted(self._indicators)

    def defined_by(self, who: str) -> list[str]:
        return sorted(i for i, ind in self._indicators.items() if ind.defined_by == who)

    def measuring(self, measures: str) -> list[str]:
        """every indicator that measures this thing, whoever defined it."""
        return sorted(i for i, ind in self._indicators.items() if ind.measures == measures)
