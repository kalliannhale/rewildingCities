"""
canopy/indicators/registry.py

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
# located_count (D-209): a count of located_in edges per place, over the
# place's own persons. it reads no published table, so it adds nothing to an
# acquisition and never reaches derive_indicator.R. it names the type of the
# points it counts (D-224): whose points, and which release, are the run's to
# say, in the label its edges carry, and so the receipt's, never a seed's
DERIVATION_KINDS = ("ratio", "passthrough", "located_count")
LOCATED_DENOMINATORS = ("persons", "households")
# what a value is for, read by the place profile to put it in its part
# (Contract 4). one role per indicator (D-107).
ROLES = ("need", "barrier", "carrier", "outcome", "context")

REQUIRED = ("name", "defined_by", "measures", "unit", "derivation",
            "direction", "aggregation", "uncertainty", "source",
            "role", "rests_on")
OPTIONAL = ("weight_by", "replicates", "rationale")
KNOWN = REQUIRED + OPTIONAL

REPLICATES_REQUIRED = ("publisher", "edition", "column")


@dataclass(frozen=True)
class Derivation:
    kind: str                                   # ratio | passthrough | located_count
    numerator: tuple[str, ...] = ()
    denominator: str | None = None
    scale: float = 1.0
    column: str | None = None                   # passthrough only
    # passthrough only: (lower, upper), the edges of a published distribution's
    # two end categories. a median the Census marks open-ended (-333333333 on
    # its margin) is reported as a bound past one of them, never as a number.
    open_ended: tuple[float, float] | None = None
    counts: str | None = None                   # located_count only: the points' type

    def as_dict(self) -> dict:
        """the derivation as plain JSON, the one shape every reader shows
        (the registry's declaration and preview's describe alike)."""
        out: dict = {"kind": self.kind}
        if self.kind == "ratio":
            out.update(numerator=list(self.numerator), denominator=self.denominator,
                       scale=self.scale)
        elif self.kind == "located_count":
            out.update(counts=self.counts, denominator=self.denominator, scale=self.scale)
        else:
            out.update(column=self.column)
            if self.open_ended is not None:
                out["open_ended"] = {"lower": self.open_ended[0],
                                     "upper": self.open_ended[1]}
        return out


@dataclass(frozen=True)
class RestsOn:
    """what a value rests on: the count of households (or persons) behind it,
    from the same release (Sprint 02, item 2).

    either a count built from source variables, `add` minus `subtract`, with
    `counts` naming what is counted ("households"), or `not_published` with
    the reason the count cannot be known. a value never rests on nothing in
    silence."""
    add: tuple[str, ...] = ()
    subtract: tuple[str, ...] = ()
    counts: str | None = None
    not_published: str | None = None

    def variables(self) -> list[str]:
        return list(self.add) + list(self.subtract)

    def as_dict(self) -> dict:
        if self.not_published is not None:
            return {"not_published": self.not_published}
        return {"add": list(self.add), "subtract": list(self.subtract),
                "counts": self.counts}


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
    role: str = ""
    rests_on: RestsOn = RestsOn(not_published="undeclared")
    weight_by: str | None = None
    replicates: dict | None = None
    rationale: str = ""
    declared_in: str = ""

    def estimate_variables(self) -> list[str]:
        """every source column this indicator reads, in a stable order. a
        located_count reads no source table, so it has none (D-209)."""
        d = self.derivation
        if d.kind == "located_count":
            return []
        cols = list(d.numerator)
        if d.denominator:
            cols.append(d.denominator)
        if d.column:
            cols.append(d.column)
        if self.weight_by:
            cols.append(self.weight_by)
        # the count a value rests on is fetched with it, so an acquisition
        # that lacks it reads as stale (ACQ-4) rather than silently countless.
        cols.extend(self.rests_on.variables())
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

    def as_declaration(self, declaration_sha256: str | None = None) -> dict:
        """this indicator as a primitive receives it: plain JSON, nothing parsed later.

        the orchestrator hands this to a primitive through `$indicators.<id>`,
        so R never reads YAML and the registry stays the one place a variable
        code is written. it is recorded in the step's provenance params, so an
        envelope says exactly which definition produced its numbers, and the
        hash says which version of the file that definition came from.
        """
        derivation = self.derivation.as_dict()
        return {
            "id": self.id,
            "name": self.name,
            "defined_by": self.defined_by,
            "measures": self.measures,
            "unit": self.unit,
            "derivation": derivation,
            "direction": self.direction,
            "aggregation": self.aggregation,
            "uncertainty": self.uncertainty,
            "role": self.role,
            "rests_on": self.rests_on.as_dict(),
            "moe_variables": self.moe_variables(),
            "declared_in": self.declared_in,
            "declaration_sha256": declaration_sha256,
        }


class IndicatorRegistry:
    """every declared indicator, across seeds/indicators/*.yml."""

    def __init__(self, indicators: dict[str, Indicator], root: Path | None = None):
        self._indicators = indicators
        self._root = root

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
        return cls(indicators, root)

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
        role = enum("role", ROLES)
        aggregation = enum("aggregation", AGGREGATIONS)
        uncertainty = enum("uncertainty", UNCERTAINTIES)

        weight_by = spec.get("weight_by")
        if aggregation == "population_weighted_mean" and not weight_by:
            raise ValueError(
                f"{where}: aggregation is population_weighted_mean but no weight_by "
                f"is declared. a weighted mean without a weight is a mean of means.")

        derivation = IndicatorRegistry._parse_derivation(where, spec["derivation"])
        rests_on = IndicatorRegistry._parse_rests_on(where, spec["rests_on"])

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
            role=role,
            rests_on=rests_on,
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
    def _parse_rests_on(where: str, r) -> RestsOn:
        """`rests_on` is required on every indicator and has two shapes:
        {add: [...], subtract: [...], counts: households} or
        {not_published: <reason>}. nothing else, and never empty."""
        if not isinstance(r, dict):
            raise ValueError(f"{where}: rests_on must be a mapping")
        if "not_published" in r:
            if set(r) != {"not_published"} or not str(r["not_published"]).strip():
                raise ValueError(
                    f"{where}: rests_on with not_published takes only that field, "
                    f"with the reason the count cannot be known")
            return RestsOn(not_published=str(r["not_published"]).strip())
        extra = [k for k in r if k not in ("add", "subtract", "counts")]
        if extra:
            raise ValueError(f"{where}: unknown rests_on field(s): {', '.join(extra)}")
        add, subtract = r.get("add"), r.get("subtract", [])
        if not isinstance(add, list) or not add:
            raise ValueError(
                f"{where}: rests_on needs add as a non-empty list of source "
                f"variables, or not_published with a reason")
        if not isinstance(subtract, list):
            raise ValueError(f"{where}: rests_on subtract must be a list")
        counts = r.get("counts")
        if not counts or not isinstance(counts, str):
            raise ValueError(
                f"{where}: rests_on needs counts, naming what is counted "
                f"(households, persons), so a count is never read as the wrong unit")
        return RestsOn(add=tuple(add), subtract=tuple(subtract), counts=counts)

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

        if kind == "located_count":
            if "layer" in d:
                raise ValueError(
                    f"{where}: a located_count names the type of the points it "
                    f"counts, counts: <type>, never a layer label (D-224). whose "
                    f"points and which release are the preparation's to say, in "
                    f"the layer its located_in edges carry")
            counts, denominator = d.get("counts"), d.get("denominator")
            if not counts or not isinstance(counts, str):
                raise ValueError(f"{where}: a located_count needs counts, the semantic "
                                 f"type of the points whose located_in edges it counts")
            if denominator not in LOCATED_DENOMINATORS:
                raise ValueError(f"{where}: a located_count's denominator must be one of "
                                 f"{', '.join(LOCATED_DENOMINATORS)}, a count the spine holds")
            scale = d.get("scale", None)
            if not isinstance(scale, (int, float)) or isinstance(scale, bool) or scale <= 0:
                raise ValueError(f"{where}: a located_count needs a positive numeric scale "
                                 f"(1000 for per 1,000). no default")
            extra = [k for k in d if k not in ("kind", "counts", "denominator", "scale")]
            if extra:
                raise ValueError(f"{where}: unknown derivation field(s): {', '.join(extra)}")
            return Derivation(kind="located_count", counts=counts, denominator=denominator,
                              scale=float(scale))

        column = d.get("column")
        if not column or not isinstance(column, str):
            raise ValueError(f"{where}: a passthrough needs a single column")
        extra = [k for k in d if k not in ("kind", "column", "open_ended")]
        if extra:
            raise ValueError(f"{where}: unknown derivation field(s): {', '.join(extra)}")

        open_ended = None
        if "open_ended" in d:
            oe = d["open_ended"]
            if not isinstance(oe, dict) or set(oe) != {"lower", "upper"}:
                raise ValueError(
                    f"{where}: open_ended must be a mapping of exactly lower and "
                    f"upper, the edges of the published distribution's two end "
                    f"categories (e.g. 10 and 50 for B25071)")
            lo, hi = oe["lower"], oe["upper"]
            numeric = all(isinstance(x, (int, float)) and not isinstance(x, bool)
                          for x in (lo, hi))
            if not numeric or lo >= hi:
                raise ValueError(
                    f"{where}: open_ended lower and upper must be numbers with "
                    f"lower below upper; got {lo!r} and {hi!r}")
            open_ended = (float(lo), float(hi))
        return Derivation(kind="passthrough", column=column, open_ended=open_ended)

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

    def with_role(self, role: str) -> list[str]:
        """every indicator in this role, whoever defined it. carrier-hood
        lives here, as each indicator's role (D-223), never on a type: a
        thing is a carrier for one claim and something else for another."""
        if role not in ROLES:
            raise ValueError(f"role '{role}' is not one of: {', '.join(ROLES)}")
        return sorted(i for i, ind in self._indicators.items() if ind.role == role)

    def measuring(self, measures: str) -> list[str]:
        """every indicator that measures this thing, whoever defined it."""
        return sorted(i for i, ind in self._indicators.items() if ind.measures == measures)

    def declaration(self, ind_id: str) -> dict:
        """`as_declaration`, with the sha256 of the file the indicator lives in."""
        import hashlib
        ind = self.get(ind_id)
        digest = None
        if self._root is not None:
            f = self._root / ind.declared_in.split("/", 1)[-1]
            if f.is_file():
                digest = hashlib.sha256(f.read_bytes()).hexdigest()
        return ind.as_declaration(digest)
