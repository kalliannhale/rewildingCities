"""
canopy/indicators/preview.py

indicator values, previewed ~ the registry read over an acquisition, before
any primitive has derived them

why build it anyway
  ~ a derived number shown without saying how it was made is exactly what this
    platform refuses to do, so the demo needs one that says so out loud
  ~ once derive_indicator.R lands, this becomes its test oracle: two
    independent implementations of one declaration that must agree to the last
    decimal. a disagreement is then a finding about one of them.

what it deliberately does not do
  ~ derive a margin of error for a ratio. the registry cannot yet say whether a
    ratio is a proportion (numerator inside the denominator), and the Census
    formulas differ. a margin computed with the wrong one is a plausible wrong
    number, so a ratio row carries its component margins and no derived one. a
    passthrough's margin is the published one, and is served as is.
  ~ round. replication is checked at full precision.
  ~ guess why a value is empty. the provider empties Census annotations; since
    ACS-7 it keeps each code in a <variable>_annotation column, and the one
    read here is -333333333 on a passthrough's margin: a median in an
    open-ended category, reported as a bound rather than a number.
  ~ cache. the registry and manifest are read on every call, so a preview can
    never disagree with the files on disk.

rows are long-form measurements, (unit, indicator, value, published_by, method,
time), with the unit itself an (authority, code) pair, so a second publisher's
claim about the same county can sit beside this one later without a schema
change.

the hand check (`compare`) reads a published file and sets it beside the
preview. it is a check, not a method: it lives here so the comparison uses the
same derivation the API serves, and it says what it is in every result.

run from the repo root:
  python -m canopy.indicators.preview show maine cii_rent_burden
  python -m canopy.indicators.preview compare maine cii_broadband --cii PATH --fips-column COL
♡
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import yaml

from .registry import Indicator, IndicatorRegistry
from canopy.paths import project_root

# one root for the whole garden: the API's read face resolves everything from
# project_root(), so this does too, rather than keeping a second opinion.
REPO = project_root()
INDICATORS_DIR = REPO / "seeds" / "indicators"
PLOTS_DIR = REPO / "plots"

SOURCE_TYPE = "indicator_source"
STATUS = "preview"
# whose codes name a unit, from Contract 3, section 1. a Census GEOID is
# unique only within its level (GRAPH-1), so every caller declares one and
# none is assumed (D-131, D-133). the same five are written in
# derive_indicator.R and build_places.py until one seed holds them (AUTH-1).
KNOWN_UNIT_AUTHORITIES = ("us_census_geoid", "us_census_sldl", "us_census_sldu",
                          "us_census_aiannh", "megis")

# a plot name becomes a path, so it is held to a shape that cannot climb out
# of plots/. refusing '../' here is cheaper than auditing every join later.
PLOT_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

STATUS_NOTE = (
    "computed in Python outside the pipeline from the registry declaration "
    "and the acquired source. no envelope exists for these values; "
    "derive_indicator.R will produce the enveloped ones, and this preview "
    "becomes its test oracle.")

CHECK_NOTE = (
    "hand check, outside the pipeline: a preview derivation set beside a "
    "published file. it is evidence about agreement, not a derived artifact.")


class PreviewError(Exception):
    """a refusal with its reason. `kind` maps to an HTTP status in the API.

    kinds: not_found, ambiguous, unavailable, malformed, registry
    """

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message


# ── registry ──────────────────────────────────────────────────────────────
def load_registry() -> IndicatorRegistry:
    try:
        return IndicatorRegistry.load(INDICATORS_DIR)
    except (FileNotFoundError, ValueError) as e:
        raise PreviewError("registry", f"the indicator registry did not load: {e}")


def get_indicator(registry: IndicatorRegistry, indicator_id: str) -> Indicator:
    try:
        return registry.get(indicator_id)
    except KeyError as e:
        raise PreviewError("not_found", e.args[0] if e.args else str(e))


def describe(ind: Indicator) -> dict:
    """an indicator as the API shows it: every declared field, nothing added."""
    d = ind.derivation
    derivation = {"kind": d.kind}
    if d.kind == "ratio":
        derivation.update(numerator=list(d.numerator), denominator=d.denominator,
                          scale=d.scale)
    else:
        derivation.update(column=d.column)
    return {
        "id": ind.id,
        "name": ind.name,
        "defined_by": ind.defined_by,
        "declared_in": ind.declared_in,
        "measures": ind.measures,
        "unit": ind.unit,
        "derivation": derivation,
        "direction": ind.direction,
        "aggregation": ind.aggregation,
        "weight_by": ind.weight_by,
        "uncertainty": ind.uncertainty,
        "source": dict(ind.source),
        "replicates": dict(ind.replicates) if ind.replicates else None,
        "verified_against_published": ind.replicates is not None,
        "acquisition_variables": ind.acquisition_variables(),
        "rationale": ind.rationale,
    }


# ── plots and their sources ───────────────────────────────────────────────
def load_manifest(plot: str) -> tuple[Path, dict]:
    if not PLOT_NAME.match(plot or ""):
        raise PreviewError(
            "malformed",
            f"'{plot}' is not a plot name. plot names are lowercase letters, "
            f"digits, hyphens and underscores, and never a path.")
    plot_dir = PLOTS_DIR / plot
    manifest = plot_dir / "manifest.yml"
    if not manifest.is_file():
        raise PreviewError("not_found", f"no manifest for plot '{plot}' at {manifest}")
    doc = yaml.safe_load(manifest.read_text()) or {}
    return plot_dir, doc


def _vintage(src: dict) -> str | None:
    if src.get("provider") != "census_acs" or not src.get("year") or not src.get("dataset"):
        return None
    from canopy.providers.census_acs import CensusACSProvider
    return CensusACSProvider.vintage_window(src["dataset"], int(src["year"]))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def indicator_sources(plot: str) -> list[dict]:
    """every indicator_source this plot declares, and whether it is on disk.

    the cache path is resolved against the plot's own directory, the same
    rule for every dataset in the manifest (D-17).
    """
    plot_dir, doc = load_manifest(plot)
    out = []
    for name, spec in (doc.get("datasets") or {}).items():
        spec = spec or {}
        if spec.get("semantic_type") != SOURCE_TYPE:
            continue
        src = spec.get("source") or {}
        cache = spec.get("cache") or {}
        path = (plot_dir / cache["path"]) if cache.get("path") else None
        out.append({
            "dataset": name,
            "declared_available": bool(spec.get("available")),
            "cache_present": bool(path and path.is_file()),
            "cache_path": _display_path(path) if path else None,
            "fetched_at": cache.get("fetched_at"),
            "provider": src.get("provider"),
            "release": src.get("dataset"),
            "year": src.get("year"),
            "vintage_window": _vintage(src),
            "geography": src.get("geography"),
            "within": dict(src.get("within") or {}),
            "indicators": list(src.get("indicators") or []),
            "authority": (spec.get("provenance") or {}).get("authority"),
            "_path": path,
        })
    return out


def public(source: dict) -> dict:
    """a source as it may be shown: the internal Path removed."""
    return {k: v for k, v in source.items() if not k.startswith("_")}


def plot_summary(plot: str, registry: IndicatorRegistry) -> dict:
    """what this plot holds for indicators, and what it could hold but does not."""
    sources = indicator_sources(plot)
    listed = {i for s in sources for i in s["indicators"]}
    unknown = sorted(i for i in listed if i not in registry.all())
    return {
        "plot": plot,
        "sources": [public(s) for s in sources],
        "derivable": sorted(i for s in sources if s["cache_present"]
                            for i in s["indicators"] if i in registry.all()),
        "declared_not_acquired": sorted(i for s in sources if not s["cache_present"]
                                        for i in s["indicators"]),
        "in_registry_not_declared_here": sorted(i for i in registry.all() if i not in listed),
        "listed_but_not_in_registry": unknown,
    }


def choose_source(plot: str, indicator_id: str, dataset: str | None = None) -> dict:
    sources = indicator_sources(plot)
    candidates = [s for s in sources if indicator_id in s["indicators"]]
    if dataset is not None:
        named = [s for s in candidates if s["dataset"] == dataset]
        if not named:
            offered = ", ".join(s["dataset"] for s in candidates) or "none"
            raise PreviewError(
                "not_found",
                f"dataset '{dataset}' in plot '{plot}' does not list '{indicator_id}'. "
                f"sources that do: {offered}")
        candidates = named
    if not candidates:
        raise PreviewError(
            "not_found",
            f"no {SOURCE_TYPE} in plot '{plot}' lists '{indicator_id}'. add it to a "
            f"source's `indicators:` and acquire that source.")
    if len(candidates) > 1:
        raise PreviewError(
            "ambiguous",
            f"{len(candidates)} sources in plot '{plot}' list '{indicator_id}': "
            f"{', '.join(s['dataset'] for s in candidates)}. they may be different "
            f"vintages or geographies, which is a choice and not a lookup. name one "
            f"with dataset=.")
    src = candidates[0]
    if not src["cache_present"]:
        raise PreviewError(
            "unavailable",
            f"'{src['dataset']}' is declared but not on disk at {src['cache_path']}. "
            f"acquire it with: python -m canopy.cli acquire {plot} "
            f"--type {SOURCE_TYPE} --fetch")
    return src


# ── reading ───────────────────────────────────────────────────────────────
def read_table(path: Path):
    """read an acquisition, keeping every identifier a string."""
    import pandas as pd
    ext = path.suffix.lower()
    if ext == ".parquet":
        frame = pd.read_parquet(path)
    elif ext == ".csv":
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    else:
        raise PreviewError("malformed", f"{path.name}: expected .parquet or .csv")
    if "GEOID" not in frame.columns:
        raise PreviewError(
            "malformed",
            f"{path.name} has no GEOID column, so no row can be named as a unit")
    return frame


def _number(x) -> float | None:
    """a value as a float, or None for anything empty. never a guess."""
    if x is None:
        return None
    try:
        import pandas as pd
        if pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(x, str):
        x = x.strip()
        if x == "":
            return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


# ── derivation ────────────────────────────────────────────────────────────
# ACS-7: the Census code on a median's margin meaning "the median falls in the
# lowest or highest category". the estimate beside it (9 or 51 for B25071) is
# an encoding of the category, which sorts correctly but is not a measurement.
OPEN_ENDED = -333333333


def _annotation(x) -> int | None:
    """an annotation cell as its integer code, whatever it was stored as."""
    v = _number(x)
    return int(v) if v is not None and float(v).is_integer() else None


def _bound_label(value: float, edges: tuple[float, float] | None) -> str:
    """what an open-ended median actually claims, in words. derive_indicator.R
    writes the same strings; the oracle test holds them to it."""
    if edges is None:
        return "open-ended interval (edges not declared)"
    lower, upper = edges
    if value >= upper:
        return f"{upper:.1f} or more"
    if value < lower:
        return f"less than {lower:.1f}"
    return "open-ended interval (value inside the declared edges)"


def _rests_on(ind: Indicator, r) -> tuple[float | None, str | None]:
    """the count of households (or persons) this unit's value rests on, from
    the same row of the same release: `add` minus `subtract`. returns the
    count and, when there is none, why. never a silent blank."""
    ro = ind.rests_on
    if ro.not_published is not None:
        return None, ro.not_published
    vals = {v: _number(r[v]) for v in ro.variables()}
    empty = [v for v, x in vals.items() if x is None]
    if empty:
        return None, f"source count empty: {', '.join(empty)}"
    return (sum(vals[v] for v in ro.add) - sum(vals[v] for v in ro.subtract)), None


def _reliability_note(value, households, counts, cv, rule) -> str | None:
    """the declared small-sample rule (D-106), in plain words. two tests, each
    applied where it can be: a household count everywhere a count exists, and
    a coefficient of variation wherever the Census published a margin. the
    note says which test fired. no rule declared, no note."""
    if value is None or not rule:
        return None
    said = []
    floor = rule.get("min_households")
    if floor is not None and households is not None and households < floor:
        # counts as whole numbers and percentages to one decimal, as the R half
        # formats them (sprintf %.0f and %.1f),
        # so the two notes are identical strings (oracle test)
        said.append(f"rests on {households:.0f} {counts or 'households'}, fewer than "
                    f"the {floor:.0f} the small-sample rule asks for")
    ceiling = rule.get("max_cv")
    if ceiling is not None and cv is not None and cv > ceiling:
        said.append(f"its margin of error is wide: a coefficient of variation of "
                    f"{cv * 100:.1f}%, above the {ceiling * 100:.1f}% the small-sample "
                    f"rule allows")
    if not said:
        return None
    return "read with care: " + "; and ".join(said) + "."


def _unit_authority(unit_authority) -> str:
    """the declared authority, or a refusal by name, as derive_indicator.R
    refuses. never a default (D-131). ~"""
    ua = unit_authority.strip() if isinstance(unit_authority, str) else ""
    if not ua:
        raise PreviewError(
            "malformed",
            f"`unit_authority` is required: whose codes name these units, one of "
            f"{', '.join(KNOWN_UNIT_AUTHORITIES)} (Contract 3, section 1). a Census "
            f"GEOID is unique only within its level, so 23001 is a county, a House "
            f"district and a Senate district (GRAPH-1, D-131).")
    if ua not in KNOWN_UNIT_AUTHORITIES:
        raise PreviewError(
            "malformed",
            f"`unit_authority` '{ua}' is not one of "
            f"{', '.join(KNOWN_UNIT_AUTHORITIES)} (Contract 3, section 1; D-131).")
    return ua


def _unit_codes(frame, unit_column: str, unit_pad) -> list[str]:
    """each row's unit code, read as derive_indicator.R reads it: trimmed,
    padded only when asked and only where padding cannot invent a different
    unit, and unique. ~"""
    if unit_column not in frame.columns:
        raise PreviewError(
            "malformed",
            f"the source has no '{unit_column}' column, so no row can be named as a unit.")
    codes = [str(v).strip() for v in frame[unit_column]]
    if unit_pad is not None:
        width = int(unit_pad)
        bad = [c for c in codes if not re.fullmatch(r"[0-9]+", c) or len(c) > width]
        if bad:
            raise PreviewError(
                "malformed",
                f"{len(bad)} code(s) in '{unit_column}' are not digits or are wider "
                f"than {width}, e.g. {bad[0]}. padding would invent a different unit.")
        codes = [c.zfill(width) for c in codes]
    seen, dup = set(), []
    for c in codes:
        if c in seen:
            dup.append(c)
        seen.add(c)
    if dup:
        raise PreviewError(
            "malformed",
            f"{len(dup)} unit code(s) appear more than once, e.g. {dup[0]}.")
    return codes


def derive(frame, ind: Indicator, *, unit_authority: str, published_by: str | None,
           time: str | None, reliability: dict | None = None,
           unit_column: str = "GEOID", unit_pad: int | None = None,
           name_column: str = "NAME") -> tuple[list[dict], list[str]]:
    """long-form preview rows for one indicator over one acquisition. the
    unit column, padding and name column are read as derive_indicator.R
    reads them, so the twins agree by construction, not by every source
    happening to say GEOID (TWIN-2). ~"""
    unit_authority = _unit_authority(unit_authority)
    codes = _unit_codes(frame, unit_column, unit_pad)
    estimates = ind.estimate_variables()
    absent = [v for v in estimates if v not in frame.columns]
    if absent:
        raise PreviewError(
            "malformed",
            f"'{ind.id}' needs {', '.join(absent)}, which the acquisition does not "
            f"hold. it was probably acquired before this indicator was listed; "
            f"re-acquire the source.")

    notes: list[str] = []
    moes = ({v: v[:-1] + "M" for v in estimates}
            if ind.uncertainty == "acs_moe" else {})
    moe_absent = [m for m in moes.values() if m not in frame.columns]
    if ind.uncertainty == "acs_moe" and moe_absent:
        notes.append(f"margins of error absent from the acquisition: {', '.join(moe_absent)}")

    d = ind.derivation
    method = f"{STATUS}:{d.kind}"
    if d.kind == "ratio":
        notes.append(
            "margin of error not derived for ratios: the registry cannot yet say "
            "whether this ratio is a proportion, and the Census formulas differ. "
            "component margins are served instead.")

    # the margin's annotation column, named as derive_indicator.R names it
    ann_col = (re.sub(r"E$", "M", d.column) + "_annotation"
               if d.kind == "passthrough" else None)
    has_ann = ann_col is not None and ann_col in frame.columns
    if d.kind == "passthrough" and d.open_ended is not None and not has_ann:
        notes.append(
            f"{ind.id} declares open-ended edges but the acquisition has no "
            f"{ann_col} column, so no open-ended median can be recognised. it was "
            f"probably acquired before ACS-7; re-acquire the source.")

    rows: list[dict] = []
    for code, (_, r) in zip(codes, frame.iterrows()):
        comp = {}
        for v in estimates:
            m = moes.get(v)
            comp[v] = {"estimate": _number(r[v]),
                       "moe": _number(r[m]) if m and m in frame.columns else None}

        value, moe, moe_status, reason, bound = None, None, None, None, None
        if d.kind == "passthrough":
            value = comp[d.column]["estimate"]
            moe = comp[d.column]["moe"]
            moe_status = "published" if moe is not None else "absent"
            if value is None:
                reason = f"source value empty: {d.column}"
            elif has_ann and _annotation(r[ann_col]) == OPEN_ENDED:
                # D-105: the Census's number for an end category is an
                # encoding, not a measurement. the value rests empty and the
                # bound says, in words, what is known, so nothing downstream
                # can rank or average the encoding by forgetting to check.
                moe_status = "open_ended"
                bound = _bound_label(value, d.open_ended)
                value, moe = None, None
                reason = f"open-ended median: {bound}"
        else:
            moe_status = "not_derived"
            empty = [v for v in (*d.numerator, d.denominator) if comp[v]["estimate"] is None]
            if empty:
                reason = f"source value empty: {', '.join(empty)}"
            else:
                num = sum(comp[v]["estimate"] for v in d.numerator)
                den = comp[d.denominator]["estimate"]
                if den == 0:
                    reason = "zero denominator"
                else:
                    value = (num / den) * d.scale

        households, households_reason = _rests_on(ind, r)
        cv = None
        if value is not None and moe is not None and moe_status == "published" and value != 0:
            cv = (moe / 1.645) / abs(value)
        note = _reliability_note(value, households, ind.rests_on.counts, cv, reliability)

        rows.append({
            "unit": {"authority": unit_authority, "code": code},
            "name": str(r[name_column]) if name_column in frame.columns else "",
            "indicator": ind.id,
            "value": value,
            "moe": moe,
            "moe_status": moe_status,
            "bound": bound,
            "empty_reason": reason,
            "households": households,
            "households_counts": ind.rests_on.counts,
            "households_reason": households_reason,
            "cv": cv,
            "reliability_note": note,
            "published_by": published_by,
            "method": method,
            "time": time,
            "components": comp,
        })

    n_empty = sum(1 for row in rows if row["value"] is None)
    if n_empty:
        notes.append(
            f"{n_empty} unit(s) have no value. where the reason is an empty source "
            f"value, the Census code behind it is in the acquisition's "
            f"<variable>_annotation column when it was acquired after ACS-7.")
    open_rows = [row for row in rows if row["moe_status"] == "open_ended"]
    if open_rows:
        notes.append(
            f"{len(open_rows)} unit(s) have an open-ended median, so their value "
            f"rests empty (D-105): the Census publishes only the end category, and "
            f"`bound` says which, in words. they stand outside any ranking.")
        odd = [row for row in open_rows if row["bound"].startswith("open-ended interval")]
        if odd:
            notes.append(
                f"{len(odd)} open-ended median(s) could not be placed past a declared "
                f"edge ({odd[0]['bound']}). declare or check `open_ended` for {ind.id}.")
    return rows, notes


def preview(plot: str, indicator_id: str, dataset: str | None = None,
            registry: IndicatorRegistry | None = None, *, unit_authority: str) -> dict:
    registry = registry or load_registry()
    ind = get_indicator(registry, indicator_id)
    src = choose_source(plot, indicator_id, dataset)
    frame = read_table(src["_path"])
    rows, notes = derive(frame, ind, unit_authority=unit_authority,
                         published_by=src["authority"], time=src["vintage_window"])
    return {
        "plot": plot,
        "status": STATUS,
        "status_note": STATUS_NOTE,
        "envelope": None,
        "indicator": describe(ind),
        "source": public(src),
        "n_units": len(rows),
        "n_empty": sum(1 for r in rows if r["value"] is None),
        "values": rows,
        "notes": notes,
    }


# ── standings: where a unit stands among others ───────────────────────────
#
# a standing is relative. it says how a unit compares with a reference
# population, never whether its value is sufficient: if every county has poor
# broadband, the top one still stands at 100. the reference population is
# declared, never inferred from whichever rows happen to be present.
#
# the percentile is CII's, recovered from CII's own published file: average
# rank, with higher-is-worse indicators negated, divided by the LARGEST rank,
# times 100. dividing by the largest rank rather than by n only differs when
# the top value is tied, and then it differs a lot: under rank / n, CII's news
# outlet percentiles would be off by 22 points. this reproduces 26 of CII's 27
# per-indicator percentile columns across all 3 144 counties to their
# rounding (CII-8). the z-score cannot be checked against CII, which does not
# publish one, so its SD convention is a required choice.

SD_CONVENTIONS = ("sample", "population")


def _average_ranks(values: list[float]) -> list[float]:
    """1-based ranks, ties sharing their average, exact equality as R's rank()."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + 1 + j + 1) / 2
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


STANDINGS_CARRY = ("empty_reason", "bound", "households", "households_counts",
                   "households_reason", "reliability_note")


def standings(rows: list[dict], ind: Indicator, *, sd: str,
              exclude_state_fips: tuple[str, ...] = (),
              restrict_to: set[str] | None = None) -> tuple[list[dict], dict]:
    """z-score and percentile for each row, against a declared population."""
    if sd not in SD_CONVENTIONS:
        raise PreviewError("malformed", f"sd must be one of {SD_CONVENTIONS}; there is no default")
    sign = 1.0 if ind.direction == "higher_is_better" else -1.0
    excluded = set(exclude_state_fips)

    def why_out(r):
        if r["value"] is None:
            return "no value"
        if r["unit"]["code"][:2] in excluded:
            return f"outside the reference population (state {r['unit']['code'][:2]} excluded)"
        if restrict_to is not None and r["unit"]["code"] not in restrict_to:
            return "outside the reference population (not ranked by the publisher)"
        return None

    ref = [r for r in rows if why_out(r) is None]
    n = len(ref)
    if n < 2:
        raise PreviewError("malformed", f"a reference population of {n} cannot be standardised")
    oriented = [sign * r["value"] for r in ref]
    ranks = _average_ranks(oriented)
    top = max(ranks)
    mean = math.fsum(oriented) / n
    ss = math.fsum((v - mean) ** 2 for v in oriented)
    sdv = math.sqrt(ss / (n - 1 if sd == "sample" else n))
    position = {id(r): k for k, r in enumerate(ref)}

    out = []
    for r in rows:
        k = position.get(id(r))
        row = {"unit": r["unit"], "name": r["name"], "indicator": ind.id,
               "value": r["value"], "direction": ind.direction,
               "z": None, "percentile": None, "outside_reason": why_out(r)}
        # what the value rests on travels with its standing (Sprint 02),
        # exactly as standardize_indicator.R carries it
        for col in STANDINGS_CARRY:
            row[col] = r.get(col)
        if k is not None:
            row["z"] = (oriented[k] - mean) / sdv if sdv > 0 else None
            row["percentile"] = ranks[k] / top * 100
            if sdv == 0:
                row["outside_reason"] = "no variation in the reference population"
        out.append(row)
    rule = "units with a value, outside excluded states"
    if restrict_to is not None:
        rule += ", and ranked by the publisher"
    population = {"n": n, "excluded_state_fips": sorted(excluded), "sd": sd,
                  "mean_oriented": mean, "sd_value": sdv, "rule": rule,
                  "left_out_by_restriction": sorted(
                      r["unit"]["code"] for r in rows
                      if r["value"] is not None and r["unit"]["code"][:2] not in excluded
                      and restrict_to is not None and r["unit"]["code"] not in restrict_to)}
    return out, population


# ── the hand check ────────────────────────────────────────────────────────
def normalise_fips(x) -> str | None:
    """a county FIPS from whatever a published file did to it.

    spreadsheets turn '01001' into 1001 and sometimes 1001.0. a code that does
    not come back to five digits is refused as None rather than padded into a
    different county.
    """
    if x is None:
        return None
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if not s.isdigit() or len(s) > 5:
        return None
    return s.zfill(5)


def read_published(path: Path, fips_column: str, value_column: str):
    import pandas as pd
    if not path.is_file():
        raise PreviewError(
            "not_found",
            f"no published file at {path} (resolved from {Path.cwd()}). "
            f"the hand check reads it from wherever --cii points; the header "
            f"test expects it at garden/reference/cii_2026.csv.")
    ext = path.suffix.lower()
    if ext == ".csv":
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    elif ext in (".xlsx", ".xls"):
        frame = pd.read_excel(path, dtype=str)
    else:
        raise PreviewError("malformed", f"{path.name}: expected .csv or .xlsx")
    missing = [c for c in (fips_column, value_column) if c not in frame.columns]
    if missing:
        raise PreviewError(
            "malformed",
            f"{path.name} has no column(s) {', '.join(repr(c) for c in missing)}. "
            f"its columns: {', '.join(map(repr, frame.columns))}")
    return frame


def compare(plot: str, indicator_id: str, published: str | Path, fips_column: str,
            column: str | None = None, dataset: str | None = None,
            percentile: bool = False, exclude_state_fips: tuple[str, ...] = (),
            match_published_population: bool = False, *, unit_authority: str) -> dict:
    registry = load_registry()
    ind = get_indicator(registry, indicator_id)
    if column is None:
        if not ind.replicates:
            raise PreviewError(
                "malformed",
                f"'{indicator_id}' declares no `replicates`, so there is no published "
                f"column to compare against. name it with --column, copied from the "
                f"file's header.")
        column = ind.replicates["column"]
    if percentile:
        # CII names each percentile column after its raw column.
        column = f"{column} percentile"

    ours = preview(plot, indicator_id, dataset, registry, unit_authority=unit_authority)
    theirs = read_published(Path(published), fips_column, column)
    population = None
    if percentile:
        restrict = None
        if match_published_population:
            # rank against exactly the units the publisher ranked: those with a
            # value in its file. a check of the RULE, so a difference in who was
            # ranked is reported on its own rather than smeared across every row.
            restrict = {normalise_fips(f) for f, v in zip(theirs[fips_column], theirs[column])
                        if str(v).strip() != "" and normalise_fips(f)}
        ranked, population = standings(ours["values"], ind, sd="sample",
                                       exclude_state_fips=exclude_state_fips,
                                       restrict_to=restrict)
        for row, st in zip(ours["values"], ranked):
            row["value"] = st["percentile"]

    state = (ours["source"]["within"] or {}).get("state")
    if state == "*":
        state = None
    published_rows: dict[str, float | None] = {}
    published_decimals: dict[str, int | None] = {}
    published_raws: dict[str, str] = {}
    bad_fips = unparseable = 0
    for _, r in theirs.iterrows():
        code = normalise_fips(r[fips_column])
        if code is None:
            bad_fips += 1
            continue
        if state and not code.startswith(str(state)):
            continue
        raw = str(r[column]).strip()
        v = _number(raw)
        if v is None and raw != "":
            unparseable += 1
        published_rows[code] = v
        published_decimals[code] = _decimals(raw)
        published_raws[code] = raw

    # what precision did the publisher write each value at? two formats seen
    # in CII's one file, and a rule for either breaks the other (PRV-4):
    #   fixed width ~ every value squeezed into the same number of characters,
    #     so a row's precision is the decimals a full-width rendering would
    #     have. "92.3664122" and "5.08905852" are both ten characters, at 7
    #     and 8 decimals. a short row has had trailing zeros dropped: "100" in
    #     a width-ten column is 100.000000, and "30" in a width-four column is
    #     30.0 (PRV-3).
    #   fixed decimals ~ no dominant width: the column's most decimals.
    observed = sorted({d for d in published_decimals.values() if d is not None})
    widths = [len(raw) for raw in published_raws.values() if raw]
    precision_rule, precision, width = "fixed_decimals", (max(observed) if observed else None), None
    if widths:
        mode = max(set(widths), key=widths.count)
        if widths.count(mode) / len(widths) >= 0.75:
            precision_rule, width = "fixed_width", mode

    def row_precision(code):
        raw = published_raws.get(code) or ""
        if precision_rule == "fixed_width" and raw:
            intpart = raw.lstrip("-").split(".")[0]
            implied = width - len(intpart) - 1 - (1 if raw.startswith("-") else 0)
            return max(published_decimals.get(code) or 0, implied, 0)
        return precision

    pairs, table = [], []
    our_codes = set()
    for row in ours["values"]:
        code = row["unit"]["code"]
        our_codes.add(code)
        if code not in published_rows:
            continue
        a, b = row["value"], published_rows[code]
        diff = (a - b) if (a is not None and b is not None) else None
        agrees = _agrees_at(a, b, row_precision(code))
        table.append({"geoid": code, "name": row["name"], "ours": a,
                      "published": b, "difference": diff,
                      "written_decimals": published_decimals.get(code),
                      "agrees_at_published_precision": agrees})
        if diff is not None:
            pairs.append((a, b))

    summary = {
        "n_ours": len(ours["values"]),
        "n_published_in_scope": len(published_rows),
        "n_matched_units": len(table),
        "n_compared": len(pairs),
        "only_ours": sorted(c for c in our_codes - set(published_rows)
                            if c[:2] not in set(exclude_state_fips)),
        "excluded_by_declaration": sorted(c for c in our_codes - set(published_rows)
                                          if c[:2] in set(exclude_state_fips)),
        "only_published": sorted(set(published_rows) - our_codes),
        "published_fips_unreadable": bad_fips,
        "published_values_unparseable": unparseable,
        "max_abs_difference": max((abs(a - b) for a, b in pairs), default=None),
        "agree_at_published_precision": sum(1 for t in table
                                            if t["agrees_at_published_precision"]),
        "precision_rule": precision_rule,
        "column_width": width,
        "column_precision": precision,
        "written_decimals_observed": observed,
        "correlation": _pearson(pairs),
    }
    return {
        "check": CHECK_NOTE,
        "plot": plot,
        "indicator": indicator_id,
        "published_file": str(published),
        "published_column": column,
        "compared": "percentile" if percentile else "value",
        "reference_population": population,
        "vintage_window": ours["source"]["vintage_window"],
        "summary": summary,
        "rows": table,
    }


def _decimals(raw: str) -> int | None:
    """how many decimal places a published value was written with."""
    if raw == "" or _number(raw) is None:
        return None
    if "e" in raw.lower():
        return None
    return len(raw.split(".", 1)[1]) if "." in raw else 0


def _agrees_at(ours: float | None, published: float | None, decimals: int | None) -> bool:
    """would our value, rounded as the publisher rounded, be theirs?

    the test is |ours - published| <= half a unit in the last published place.
    rounding ours and comparing would trip on binary floats; this does not. a
    tiny allowance covers the float error in the subtraction itself.
    """
    if ours is None or published is None or decimals is None:
        return False
    half = 0.5 * 10 ** (-decimals)
    return abs(ours - published) <= half + 1e-12


def _pearson(pairs: list[tuple[float, float]]) -> float | None:
    """None when there are too few pairs or no variance, rather than a NaN."""
    n = len(pairs)
    if n < 3:
        return None
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in pairs)
    return sxy / math.sqrt(sxx * syy)


# ── command line ──────────────────────────────────────────────────────────
def _fmt(v) -> str:
    return "" if v is None else repr(v) if isinstance(v, float) else str(v)


def _print_preview(p: dict) -> None:
    print(f"{p['indicator']['id']} ~ {p['indicator']['name']}")
    print(f"  {p['status']}: {p['status_note']}")
    print(f"  source {p['source']['dataset']}, {p['source']['vintage_window']}")
    for r in p["values"]:
        tail = f"  moe {_fmt(r['moe'])}" if r["moe"] is not None else ""
        why = f"  ({r['empty_reason']})" if r["empty_reason"] else ""
        print(f"  {r['unit']['code']}  {r['name'][:34]:<34}  {_fmt(r['value'])}{tail}{why}")
    for n in p["notes"]:
        print(f"  note: {n}")


def _print_compare(c: dict) -> None:
    s = c["summary"]
    print(f"{c['indicator']} vs '{c['published_column']}'")
    print(f"  {c['check']}")
    print(f"  vintage {c['vintage_window']}")
    pop = c.get("reference_population")
    if pop:
        print(f"  reference population: {pop['n']} units ({pop['rule']}; "
              f"excluded {pop['excluded_state_fips'] or 'none'})")
    rows = c["rows"]
    if len(rows) > 40:
        shown = [r for r in rows if not r["agrees_at_published_precision"]][:20]
        print(f"  {len(rows)} units; showing those that differ ({len(shown)} shown)")
        rows = shown
    for r in rows:
        mark = "agrees" if r["agrees_at_published_precision"] else "DIFFERS"
        print(f"  {r['geoid']}  {r['name'][:34]:<34}  ours {_fmt(r['ours'])}  "
              f"published {_fmt(r['published'])}  diff {_fmt(r['difference'])}  {mark}")
    print(f"  compared {s['n_compared']} of {s['n_ours']} units")
    if s["precision_rule"] == "fixed_width":
        how = (f"each value judged at the digits a {s['column_width']}-character "
               f"rendering holds")
    else:
        how = f"column published to {s['column_precision']} decimal places"
    print(f"  agree at published precision: {s['agree_at_published_precision']} of "
          f"{s['n_compared']} ({how})")
    if pop and pop.get("left_out_by_restriction"):
        print(f"  ranked by us but not by the publisher, left out to compare like with "
              f"like: {', '.join(pop['left_out_by_restriction'])}")
    print(f"  max abs difference {_fmt(s['max_abs_difference'])}")
    print(f"  correlation {_fmt(s['correlation'])}")
    for k in ("only_ours", "only_published"):
        if s[k]:
            print(f"  {k}: {', '.join(s[k])}")
    if s.get("excluded_by_declaration"):
        print(f"  {len(s['excluded_by_declaration'])} unit(s) outside the population by "
              f"declaration, not compared")
    for k in ("published_fips_unreadable", "published_values_unparseable"):
        if s[k]:
            print(f"  {k}: {s[k]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m canopy.indicators.preview")
    sub = ap.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="print a preview derivation")
    show.add_argument("plot")
    show.add_argument("indicator")
    show.add_argument("--dataset")
    show.add_argument("--unit-authority", required=True,
                      choices=KNOWN_UNIT_AUTHORITIES,
                      help="whose codes name the units, e.g. us_census_geoid (D-133)")

    cmp_ = sub.add_parser("compare", help="hand check against a published file")
    cmp_.add_argument("plot")
    cmp_.add_argument("indicator")
    cmp_.add_argument("--cii", required=True, help="path to the published file")
    cmp_.add_argument("--fips-column", required=True)
    cmp_.add_argument("--column", help="published column, if the indicator declares no replicates")
    cmp_.add_argument("--dataset")
    cmp_.add_argument("--unit-authority", required=True,
                      choices=KNOWN_UNIT_AUTHORITIES,
                      help="whose codes name the units, e.g. us_census_geoid (D-133)")
    cmp_.add_argument("--percentile", action="store_true",
                      help="compare CII's percentile column instead of the raw value")
    cmp_.add_argument("--exclude-states", default="",
                      help="state FIPS outside the reference population, comma-separated, e.g. 72")
    cmp_.add_argument("--match-published-population", action="store_true",
                      help="rank only the units the publisher ranked, to test the rule alone")

    a = ap.parse_args(argv)
    try:
        if a.command == "show":
            _print_preview(preview(a.plot, a.indicator, a.dataset,
                                   unit_authority=a.unit_authority))
        else:
            excl = tuple(x.strip() for x in a.exclude_states.split(",") if x.strip())
            _print_compare(compare(a.plot, a.indicator, a.cii, a.fips_column,
                                   a.column, a.dataset, a.percentile, excl,
                                   a.match_published_population,
                                   unit_authority=a.unit_authority))
    except PreviewError as e:
        print(f"refused ({e.kind}): {e.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
