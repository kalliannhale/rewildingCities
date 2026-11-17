"""
canopy/wonder/profile.py

profile ~ one place, in six parts, which every product reads (Contract 4)

products cannot disagree about a place, because none of them computes it:
the explorer, the briefs, the outreach planner and the hub all read this.
build_profile composes read_place (D-197) and never grows it (D-184):
read_place measures a place through its edges; this gathers that reading,
the standard's verdicts, the carriers, the disagreements and the gaps into
one document.

  0  header        the place, its flags and note, who built it, and where
                   its gate record will come from (D-274: the door decides
                   that, never the file it judges)
  1  represented   who lives here: population and households with their
                   release, needs never judged, legislators, what it holds
                   and what it overlaps
  2  barriers      the standard's barriers (seeds/standards, D-270), every
                   measure at its grain, judged by the rules in verdicts.py
                   (D-272, D-273); borrowed values named as their places'
                   own (D-276)
  3  carriers      every exact count of carriers here (D-209)
  4  disagreements one measure two publishers publish, both shown (D-282)
  5  cannot answer every gap, every measure not acquired, every
                   cannot_judge with its reason, every withheld receipt
  6  channels      the pairing table's suggestions (P-2), present and empty
                   until it is written (D-285)

the gate is asked first (D-284). every receipt a value would come from is
judged at public before its value enters. a withheld receipt's values never
enter the file; its refusal does, saying the data exists and why it stays
(Contract 1, rules 7 and 8). so a profile can leave by the door, and what
it could not carry is said, never silently missing. the places and edges
receipts are the one exception: every profile's names, contents and shares
come from them, so they are always its inputs, and when the gate withholds
them the command says the whole file cannot leave (D-293).

every level of the graph is profiled: Contract 4's first, then any other
level a plot holds (Maine's MEGIS civil divisions), each saying it is
groundwork rather than one of the contract's levels (D-292).

it reads a bed opened by open_plot and writes nothing; build_profiles and
write_profiles (the profile command, D-274) are the only writers. ~
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .verdicts import (MEETS_UNREACHABLE, Verdict, as_published, borrowed_shares,
                       cannot_judge, comparable, no_threshold, number, trigger_on_group,
                       universal_on_count, universal_on_interval)

PROFILE_VERSION = "0.4.0"
CONTRACT = "Contract 4, draft 0.4"
STANDARD_ID = "information_barriers"
PROFILE_TYPE = "place_profile"
STEP, OUTPUT = "place_profile", "profiles"
TARGET = SHARING_LEVEL = "public"

LEVEL_ORDER = ("state", "county", "cousub", "sldl", "sldu", "aiannh")   # Contract 4's levels
OTHER_LEVEL_WHY = ("a unit of analysis outside Contract 4's levels, profiled as groundwork for "
                   "later analyses (D-292); each part says what can be answered here")
PART_LEVEL = {"state": "county", "cousub": None}     # every other level reads its towns
TOWN_LEVEL = "cousub"
PERSONS = "persons"

CHANNELS_LABEL = "standard outreach practice, not a finding"
CHANNELS_EMPTY = ("the pairing table (P-2) waits on cited research; this part ships "
                  "present and empty until it is written (D-285)")
GATE_WHY = ("the allow record is decided at the publish door and never written inside "
            "the file it judges (D-274)")
LEGISLATORS_WHY = ("the 133rd Legislature's rosters are acquired on or after 2026-12-02 "
                   "(TRIBE-4, SEN-1); until then no seats are held")


# ── small readers ────────────────────────────────────────────────────────────
def _plain(x):
    """a value as JSON can hold it: NaN is None, numpy and duckdb scalars
    and arrays become Python's own."""
    if x is None:
        return None
    if isinstance(x, float):
        return None if math.isnan(x) else x
    if isinstance(x, (str, bool, int)):
        return x
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if hasattr(x, "tolist"):
        return _plain(x.tolist())
    if hasattr(x, "item"):
        return _plain(x.item())
    return str(x)


def _text(x) -> str:
    x = _plain(x)
    return "" if x is None else str(x)


def _rows(con, sql: str, params=()) -> list[dict]:
    cursor = con.execute(sql, list(params))
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _views(con) -> set[str]:
    return {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}


def _stem(receipt: str) -> str:
    """a receipt's artifact name, from its file name or its name alone."""
    name = Path(str(receipt)).name
    return name[:-len(".envelope.json")] if name.endswith(".envelope.json") else name


def _key(authority, code) -> tuple[str, str]:
    return str(authority), str(code)


def _place_key(authority, code, name=None) -> dict:
    out = {"authority": str(authority), "code": str(code)}
    if name:
        out["name"] = name
    return out


# ── the context: everything read once for every place ────────────────────────
@dataclass
class ProfileContext:
    """what every profile in one build shares: the registry, the standard,
    the notes, the gate's answer for every receipt, and the graph's own
    structure. read once; a profile only looks things up in it."""
    root: Path                                # the garden: seeds, registry, notes
    plot: str
    plot_dir: Path                            # the plot's own folder (D-164)
    loam: object
    registry: object
    standard: object
    notes: dict
    judged: dict                              # artifact -> {semantic_type, result}
    envelopes: dict                           # artifact -> receipt dict, for those read
    views: set
    places: dict                              # (authority, code) -> place row
    persons: dict                             # (authority, code) -> (count, artifact)
    county_of: dict                           # town key -> county key
    indicator_receipts: dict                  # indicator -> set of artifacts holding it
    structure: tuple = ()                     # the places and edges receipts, always inputs
    literacy: dict = field(default_factory=dict)      # (authority, code, measure) -> row
    section203: dict = field(default_factory=dict)    # (authority, code) -> rows
    seats_held: bool = False
    read: set = field(default_factory=set)    # artifacts whose values entered a profile
    withheld: set = field(default_factory=set)  # every artifact withheld in this build
    withheld_here: set = field(default_factory=set)  # those withheld for the place being built

    @classmethod
    def open(cls, loam, plot: str, root: str | Path,
             plot_dir: str | Path | None = None) -> "ProfileContext":
        from canopy.expose.check import judge_receipts
        from canopy.expose.records import load_notes
        from canopy.indicators import IndicatorRegistry
        from canopy.standards import load_standard
        root = Path(root)
        plot_dir = Path(plot_dir) if plot_dir else root / "plots" / plot
        registry = IndicatorRegistry.load(root / "seeds" / "indicators")
        standard = load_standard(STANDARD_ID, root=root, registry=registry)
        con = loam.con
        views = _views(con)
        missing = [v for v in ("places", "edges", "place_values") if v not in views]
        if missing:
            raise ProfileUnavailable(f"this bed has no {', '.join(missing)} view, so no place "
                                     f"can be profiled; `wonder {plot}` says why")
        places = {_key(p["authority"], p["code"]): p
                  for p in _rows(con, "SELECT * FROM places")}
        county_of = {}
        for e in _rows(con, "SELECT e.from_authority, e.from_code, e.to_authority, e.to_code "
                            "FROM edges e JOIN places p ON p.authority = e.from_authority AND "
                            "CAST(p.code AS VARCHAR) = CAST(e.from_code AS VARCHAR) "
                            "WHERE e.kind = 'contains' AND p.level = 'county'"):
            county_of[_key(e["to_authority"], e["to_code"])] = _key(e["from_authority"],
                                                                     e["from_code"])
        judged = judge_receipts(plot, root=root, sharing_level=SHARING_LEVEL, target=TARGET)
        holding: dict[str, set] = {}
        for r in _rows(con, "SELECT indicator, recorded_in FROM indicator_values"):
            holding.setdefault(r["indicator"], set()).update(
                _stem(x) for x in _text(r["recorded_in"]).split(", ") if x)
        ctx = cls(root=root, plot=plot, plot_dir=plot_dir, loam=loam, registry=registry, standard=standard,
                  notes=load_notes(root / "seeds" / "notes"), judged=judged, envelopes={},
                  views=views, places=places, persons={}, county_of=county_of,
                  indicator_receipts=holding)
        ctx.persons = ctx._read_persons()
        ctx.structure = ctx._structure_receipts()
        ctx.literacy, ctx.section203 = ctx._read_records()
        ctx.seats_held = any(loam.find(semantic_type="seats", plot=plot, tier=tier)
                             for tier in ("tended", "gathered"))
        return ctx

    def _structure_receipts(self) -> tuple:
        """the one places and one edges receipt every profile's names,
        contents, overlaps and borrowed shares come from (D-163). they are
        inputs of every profile, whatever the gate says of them, so the
        door judges the lineage the file's structure rests on (D-293)."""
        from canopy.loam.graph import CONFORMED_TIERS, GRAPH_VIEWS
        found = []
        for semantic_type in GRAPH_VIEWS.values():
            rows = [r for tier in CONFORMED_TIERS
                    for r in self.loam.find(semantic_type=semantic_type, plot=self.plot,
                                            tier=tier)]
            found += [_stem(r["receipt_path"]) for r in rows if r.get("receipt_path")]
        return tuple(found)

    def structure_withheld(self) -> list[str]:
        return [r for r in self.structure if not self.may_leave(r)]

    def _read_records(self) -> tuple[dict, dict]:
        """the literacy and section 203 views, read once for the build: each
        query of a view over a csv reads the whole file again (D-275 keeps
        the views; this keeps their rows for one build, copying nothing
        into the bed)."""
        literacy, section203 = {}, {}
        if "literacy_estimates" in self.views:
            for r in _rows(self.loam.con, "SELECT * FROM literacy_estimates"):
                literacy.setdefault((_text(r["unit_authority"]), _text(r["unit_code"]),
                                     _text(r["measure"])), r)
        if "section203_records" in self.views:
            for r in _rows(self.loam.con, "SELECT * FROM section203_records "
                                          "WHERE group_class <> 'total'"):
                section203.setdefault((_text(r["unit_authority"]), _text(r["unit_code"])),
                                      []).append(r)
        return literacy, section203

    # the gate, asked once per receipt (D-284)
    def may_leave(self, artifact: str) -> bool:
        j = self.judged.get(_stem(artifact))
        return bool(j) and j["result"]["decision"] == "allow"

    def allowed(self, recorded_in) -> str | None:
        """the first receipt saying a value that may leave, or None."""
        for r in [x for x in _text(recorded_in).split(", ") if x]:
            if self.may_leave(r):
                return _stem(r)
        return None

    def refusal(self, artifact: str) -> dict:
        """presence before contents (rule 8): what is withheld and why,
        never what it holds."""
        artifact = _stem(artifact)
        j = self.judged.get(artifact) or {"semantic_type": None, "result": {"refusals": [
            {"rule": None, "reason": "no receipt of this name was judged",
             "would_admit": "re-run what made it"}]}}
        seen, refusals = set(), []
        for r in j["result"].get("refusals", []):
            key = (r.get("rule"), r.get("semantic_type"), r.get("reason"))
            if key in seen:
                continue
            seen.add(key)
            refusals.append({k: r.get(k) for k in ("rule", "semantic_type", "tier", "ancestor",
                                                   "reason", "would_admit")})
        return {"receipt": artifact, "semantic_type": j["semantic_type"], "refusals": refusals}

    def note(self, note_id) -> dict | None:
        note_id = _text(note_id)
        if not note_id:
            return None
        return {"id": note_id, "text": _text((self.notes.get(note_id) or {}).get("text")).strip()
                or None}

    def envelope(self, artifact: str) -> dict:
        artifact = _stem(artifact)
        if artifact not in self.envelopes:
            path = self.plot_dir / ".envelopes" / f"{artifact}.envelope.json"
            self.envelopes[artifact] = json.loads(path.read_text()) if path.is_file() else {}
        return self.envelopes[artifact]

    def run_of(self, artifact: str) -> str | None:
        lineage = (self.envelope(artifact).get("metadata") or {}).get("lineage") or {}
        return lineage.get("run")

    def take(self, artifact: str) -> None:
        self.read.add(_stem(artifact))

    def withhold(self, artifact: str) -> str:
        """a receipt the gate keeps back, for this build and this place."""
        artifact = _stem(artifact)
        self.withheld.add(artifact)
        self.withheld_here.add(artifact)
        return artifact

    def _read_persons(self) -> dict:
        """D-280: every place's 2020 Census persons, as every per_1000 divides
        by them, from the first carrier count whose receipt may leave."""
        carriers = [i for i in self.registry.with_role("carrier")
                    if self.registry.get(i).derivation.kind == "located_count"]
        out = {}
        if not carriers:
            return out
        marks = ", ".join("?" for _ in carriers)
        for r in _rows(self.loam.con,
                       f"SELECT unit_authority, unit_code, indicator, households, "
                       f"households_counts, recorded_in FROM indicator_values "
                       f"WHERE indicator IN ({marks}) ORDER BY indicator", carriers):
            key = _key(r["unit_authority"], r["unit_code"])
            if key in out or _text(r["households_counts"]) != PERSONS:
                continue
            artifact = self.allowed(r["recorded_in"])
            count = number(r["households"])
            if artifact and count is not None:
                out[key] = (count, artifact, r["indicator"])
        return out


class ProfileUnavailable(RuntimeError):
    """no place in this bed can be profiled, and why. ~"""


# ── one value row, read for a place ──────────────────────────────────────────
@dataclass
class Value:
    """an indicator's row at one place, after the gate: its numbers, or why
    there are none."""
    indicator: str
    row: dict | None
    receipt: str | None
    withheld_from: str | None = None
    why: str = ""

    @property
    def present(self) -> bool:
        return self.row is not None and self.receipt is not None and not self.why

    def get(self, column):
        return _plain((self.row or {}).get(column))


def _values_at(ctx: ProfileContext, authority: str, code: str) -> dict[str, Value]:
    """every indicator's own row here, the attached one first (other
    vintages are someone else's boundaries), through the gate."""
    rows = _rows(ctx.loam.con, "SELECT * FROM place_values WHERE unit_authority = ? AND "
                               "unit_code = ? ORDER BY attached DESC, value_receipt",
                 (authority, code))
    out: dict[str, Value] = {}
    for row in rows:
        indicator = row["indicator"]
        if indicator in out:
            continue
        allowed = ctx.allowed(row.get("recorded_in"))
        if not allowed:
            first = ctx.withhold(_text(row.get("recorded_in")).split(", ")[0])
            out[indicator] = Value(indicator, None, None, withheld_from=first,
                                   why=f"withheld by the gate at {TARGET}: see refusals, "
                                       f"{first} (D-284)")
            continue
        if not row.get("attached"):
            out[indicator] = Value(indicator, row, allowed,
                                   why=_text(row.get("why")) or f"not attached ({row.get('status')})")
            continue
        out[indicator] = Value(indicator, row, allowed)
    return out


def _uncertainty(ctx: ProfileContext, indicator, v: Value) -> dict:
    """the margin and its confidence (D-277), or why there is none."""
    from canopy.indicators.registry import UNCERTAINTY_CONFIDENCE
    status = _text(v.get("moe_status"))
    moe = number(v.get("moe"))
    if status in ("published", "derived") and moe is not None:
        out = {"margin": moe, "confidence": UNCERTAINTY_CONFIDENCE.get(indicator.uncertainty),
               "method": status}
        if _text(v.get("moe_formula")):
            out["formula"] = _text(v.get("moe_formula"))
        if out["confidence"] is None:
            out["why_no_confidence"] = (f"its declared uncertainty '{indicator.uncertainty}' "
                                        f"states no confidence")
        return out
    if status == "open_ended":
        return {"margin": None, "confidence": None, "method": "open_ended",
                "why": "the publisher marks this median open-ended; its bound is in words"}
    if status == "not_applicable":
        return {"margin": None, "confidence": None, "method": "absent",
                "why": "an exact count of points standing here; no sample, so no margin (D-209)"}
    if status == "not_derived":
        return {"margin": None, "confidence": None, "method": "absent",
                "why": "the margin was not derived: "
                       + (_text(v.get("moe_formula")) or "a proportion of exactly 1 (D-269)")}
    return {"margin": None, "confidence": None, "method": "absent",
            "why": "the publisher gives no margin here"}


def _behind(v: Value) -> dict:
    """households_behind: the count in the value's denominator, from the same
    release (Contract 4); a rate over 14 is a different fact from one over
    14,000."""
    count = number(v.get("households"))
    out = {"count": count, "counts": _text(v.get("households_counts")) or None}
    if count is None:
        out["why"] = _text(v.get("households_reason")) or "the publisher gives no count behind it"
    return out


def _value_entry(ctx: ProfileContext, place_level: str, measure, v: Value | None) -> dict:
    """one registered indicator's entry (2b), before any verdict."""
    ind = ctx.registry.get(measure.indicator)
    entry = {"measure": measure.id, "indicator": ind.id, "name": ind.name,
             "measures": ind.measures, "status": measure.status,
             "estimate_kind": measure.estimate_kind, "unit": ind.unit, "value": None,
             "grain": None, "borrowed_from": [], "uncertainty": None, "bound": None,
             "households_behind": {"count": None, "counts": None,
                                   "why": "there is no value here"},
             "published_by": None, "vintage": None, "method": None}
    if measure.method:
        entry["estimate_method"] = measure.method
    if v is None:
        entry["why"] = "this plot holds no value for it here"
        return entry
    if v.withheld_from:
        entry.update(withheld=True, why=v.why)
        return entry
    entry.update(published_by=v.get("published_by"), vintage=v.get("time"),
                 method=ctx.run_of(v.receipt), receipt=v.receipt)
    if v.why:
        entry["why"] = v.why
        return entry
    ctx.take(v.receipt)
    entry.update(value=number(v.get("value")), grain=place_level,
                 uncertainty=_uncertainty(ctx, ind, v), households_behind=_behind(v))
    bound = _text(v.get("bound"))
    if bound:
        entry.update(bound=bound, value_is_measurement=False)
    if entry["value"] is None:
        entry["why"] = _text(v.get("empty_reason")) or "the publisher gives no value here"
    if _text(v.get("reliability_note")):
        entry["reliability_note"] = _text(v.get("reliability_note"))
    if v.get("status") == "unchecked_statistical":
        entry["unchecked"] = _text(v.get("why"))
    return entry


# ── the parts a place is made of, for ranges and for borrowing ───────────────
def _towns_here(ctx: ProfileContext, authority: str, code: str, level: str) -> list[tuple]:
    """(town key, share of the town's residents here) for every town this
    place's edges reach; a town is its own one town."""
    if level == TOWN_LEVEL:
        return [(_key(authority, code), 1.0)]
    out = []
    for e in _rows(ctx.loam.con, "SELECT from_authority, from_code, weight_population FROM "
                                 "edges WHERE kind = 'overlaps' AND to_authority = ? AND "
                                 "CAST(to_code AS VARCHAR) = ?", (authority, code)):
        out.append((_key(e["from_authority"], e["from_code"]), number(e["weight_population"])))
    for e in _rows(ctx.loam.con, "SELECT to_authority, to_code, weight_population FROM edges "
                                 "WHERE kind = 'contains' AND from_authority = ? AND "
                                 "CAST(from_code AS VARCHAR) = ?", (authority, code)):
        out.append((_key(e["to_authority"], e["to_code"]), number(e["weight_population"])))
    return [(k, w) for k, w in out
            if (ctx.places.get(k) or {}).get("level") == TOWN_LEVEL]


def _borrowed_from(ctx: ProfileContext, authority: str, code: str, level: str,
                   has_own) -> tuple[list[dict], str]:
    """D-276: the coarser places (counties) a value is borrowed from, each
    with its share of this place's residents from the graph's edges. returns
    the shares, or none and why."""
    parts = []
    for town, weight in _towns_here(ctx, authority, code, level):
        county = ctx.county_of.get(town)
        persons = (ctx.persons.get(town) or (None,))[0]
        if county is None:
            return [], f"the town {town[1]} is in no county the graph holds"
        if weight is None or persons is None:
            return [], (f"how many of {town[1]}'s residents are here cannot be told, so no "
                        f"share can be given")
        parts.append((county, weight * persons))
    if not parts:
        return [], "no town this place's edges reach lies in a county the graph holds"
    shares = borrowed_shares(parts)
    for s in shares:
        authority_c, code_c = s.pop("key")
        s["place"] = _place_key(authority_c, code_c,
                                _text((ctx.places.get((authority_c, code_c)) or {}).get("name")))
        s["has_value"] = has_own(authority_c, code_c)
    return shares, ""


# ── part 2: barriers ─────────────────────────────────────────────────────────
def _literacy_rows(ctx: ProfileContext, authority: str, code: str, measure: str) -> dict | None:
    return ctx.literacy.get((str(authority), str(code), measure))


def _artifact_entry_literacy(ctx: ProfileContext, place: dict, m) -> dict:
    """a model's share with its credible bounds (D-265): this place's own,
    or its counties', labelled as theirs (D-276)."""
    authority, code, level = place["authority"], place["code"], place["level"]
    entry = {"measure": m.id, "artifact": m.artifact, "name": m.measure, "measures": m.measure,
             "status": m.status, "estimate_kind": m.estimate_kind, "unit": m.unit, "value": None,
             "grain": None, "borrowed_from": [], "uncertainty": None, "bound": None,
             "households_behind": {"count": None, "counts": "adults 16 to 74",
                                   "why": "there is no estimate here"},
             "published_by": "nces", "vintage": None, "method": None}
    if m.note:
        entry["note"] = m.note
    if "literacy_estimates" not in ctx.views:
        entry["why"] = "this plot's bed has no literacy_estimates view"
        return entry
    row = _literacy_rows(ctx, authority, code, m.measure)

    def usable(r):
        return r is not None and ctx.may_leave(r["record_receipt"])

    if row is not None and not usable(row):
        ctx.withhold(row["record_receipt"])
        entry.update(withheld=True, why=f"withheld by the gate at {TARGET}: see refusals, "
                                        f"{_stem(row['record_receipt'])} (D-284)")
        return entry
    if row is not None:
        receipt = _stem(row["record_receipt"])
        ctx.take(receipt)
        entry.update(
            value=number(row["share"]), grain=level, vintage=_text(row["period"]),
            method=ctx.run_of(receipt), receipt=receipt,
            uncertainty={"interval": [number(row["lower"]), number(row["upper"])],
                         "confidence": number(row["confidence"]), "method": "credible_interval"},
            households_behind={"count": number(row["population_16_74"]),
                               "counts": "adults 16 to 74"},
            flags={k: _text(row[k]) for k in ("share_flag", "lower_flag", "upper_flag", "cv_flag")
                   if k in row and _text(row[k])},
            judged_count={"count": number(row["left_out"]), "lower": number(row["left_out_lower"]),
                          "upper": number(row["left_out_upper"]),
                          "confidence": number(row["confidence"])})
        return entry

    def has_own(a, c):
        return usable(_literacy_rows(ctx, a, c, m.measure))

    shares, why = _borrowed_from(ctx, authority, code, level, has_own)
    for s in shares:
        r = _literacy_rows(ctx, s["place"]["authority"], s["place"]["code"], m.measure)
        if usable(r):
            ctx.take(r["record_receipt"])
            s.update(value=number(r["share"]), interval=[number(r["lower"]), number(r["upper"])],
                     confidence=number(r["confidence"]), vintage=_text(r["period"]))
        s.pop("has_value", None)
    entry["borrowed_from"] = shares
    entry["why"] = (f"published only for counties and the state; every value here is the "
                    f"named place's own, never this place's (D-276)" if shares else why)
    return entry


def _section203_entry(ctx: ProfileContext, place: dict, m) -> dict:
    """the Census Bureau's own determinations, reported as published (D-263)."""
    entry = {"measure": m.id, "artifact": m.artifact, "name": "section 203 determinations",
             "measures": "section_203_coverage", "status": m.status,
             "estimate_kind": m.estimate_kind, "unit": None, "value": None, "grain": None,
             "borrowed_from": [], "uncertainty": {"margin": None, "confidence": None,
                                                  "method": "absent",
                                                  "why": "a published determination states no "
                                                         "confidence (D-263)"},
             "bound": None,
             "households_behind": {"count": None, "counts": None,
                                   "why": "a determination is the publisher's, group by group"},
             "published_by": "us_census_bureau", "vintage": None, "method": None}
    if m.note:
        entry["note"] = m.note
    if "section203_records" not in ctx.views:
        entry["why"] = "this plot's bed has no section203_records view"
        return entry
    rows = ctx.section203.get((place["authority"], place["code"]), [])
    if not rows:
        entry["why"] = ("no determination is published under this place's own code; a Census "
                        "town split at a county line, or no longer ours, is held apart (D-267)")
        return entry
    receipt = _stem(rows[0]["record_receipt"])
    if not ctx.may_leave(receipt):
        ctx.withhold(receipt)
        entry.update(withheld=True, why=f"withheld by the gate at {TARGET}: see refusals, "
                                        f"{receipt} (D-284)")
        return entry
    ctx.take(receipt)
    covered = [_text(r["group_as_written"]) for r in rows
               if _text(r["flag_cov"]) in ("1", "1.0")]
    entry.update(grain=place["level"], receipt=receipt, method=ctx.run_of(receipt),
                 vintage=_text((ctx.envelope(receipt).get("metadata") or {})
                               .get("determination_date")) or None,
                 value={"groups_determined": len(rows), "covered": covered,
                        "suppressed_rows": sum(1 for r in rows
                                               if _text(r["suppressed"]).lower() == "true")})
    return entry


def _measure_entry(ctx: ProfileContext, place: dict, m, values: dict) -> dict:
    if m.status != "acquired":
        return {"measure": m.id, "status": m.status, "source": m.source, "needs": m.needs,
                "value": None, "borrowed_from": [], "uncertainty": None,
                "households_behind": {"count": None, "counts": None,
                                      "why": f"not acquired ({m.status})"},
                "why": f"not acquired: {m.needs}"}
    if m.indicator:
        return _value_entry(ctx, place["level"], m, values.get(m.indicator))
    if m.artifact == "literacy_estimates":
        return _artifact_entry_literacy(ctx, place, m)
    if m.artifact == "section203_records":
        return _section203_entry(ctx, place, m)
    return {"measure": m.id, "status": m.status, "value": None, "borrowed_from": [],
            "uncertainty": None, "households_behind": {"count": None, "counts": None,
                                                       "why": "no reader for this artifact"},
            "why": f"no profile reader is built for the artifact '{m.artifact}'"}


def _why_unjudged(entry: dict) -> str:
    if entry.get("borrowed_from"):
        return "a borrowed value is never judged here; it is the named places' own (D-276)"
    return entry.get("why") or "there is no value here"


def _universal(ctx: ProfileContext, side, entry: dict) -> Verdict:
    if entry.get("value") is None and "judged_count" not in entry:
        return cannot_judge(_why_unjudged(entry))
    if entry.get("artifact"):
        jc = entry.get("judged_count") or {}
        return universal_on_interval(jc.get("count"), jc.get("lower"), jc.get("upper"),
                                     counts=entry["households_behind"].get("counts") or "people",
                                     confidence=jc.get("confidence"))
    if entry.get("unchecked"):
        return cannot_judge(f"a statistical area attached unchecked: {entry['unchecked']}")
    unc = entry.get("uncertainty") or {}
    if unc.get("method") not in ("published", "derived"):
        return cannot_judge(unc.get("why") or "the count carries no margin to judge it with")
    return universal_on_count(entry["value"], unc.get("margin"), counts=entry.get("unit") or "people",
                              confidence=unc.get("confidence"))


def _group_quantity(entry: dict, q: str):
    if entry.get("value") is None:
        return None, _why_unjudged(entry)
    unc = entry.get("uncertainty") or {}
    if unc.get("method") not in ("published", "derived"):
        return None, unc.get("why") or "no margin"
    return (entry["value"], unc.get("margin")), ""


def _judge_barrier(ctx: ProfileContext, barrier, entries: dict) -> list[dict]:
    """every side's verdicts, written onto the entries they judge; every
    other entry says which entry carries its barrier's verdict (D-272)."""
    sides, carrier_of_verdict = [], None
    for side in barrier.sides:
        s = side.as_dict()
        if side.kind == "none":
            for e in entries.values():
                shown = e.get("value") is not None
                v = no_threshold(shown, "" if shown else _why_unjudged(e))
                e["verdict"] = dict(v.as_dict(), side=side.id)
        elif side.kind == "universal":
            e = entries[side.judges]
            v = _universal(ctx, side, e)
            e["verdict"] = dict(v.as_dict(), side=side.id)
            e["verdict"].pop("left_out", None)
            e["left_out"] = v.left_out or {"count": None, "why": v.reason}
            s["meets"] = MEETS_UNREACHABLE
            carrier_of_verdict = carrier_of_verdict or side.judges
        elif side.as_published:
            e = entries[side.as_published]
            value = e.get("value") or {}
            v = (as_published(value.get("covered", []), value.get("groups_determined", 0),
                              publisher="the Census Bureau") if value
                 else cannot_judge(_why_unjudged(e)))
            e["verdict"] = dict(v.as_dict(), side=side.id)
            s["crosses"] = [{"group": g, "as_published": True}
                            for g in (e.get("value") or {}).get("covered", [])]
        else:
            results, crosses = [], []
            for g in side.groups:
                measures = list(g["quantities"].items())
                lead = entries[measures[0][1]]
                quantities, why = {}, ""
                for q, m_id in measures:
                    got, why = _group_quantity(entries[m_id], q)
                    if got is None:
                        break
                    quantities[q] = got
                v = (cannot_judge(why) if len(quantities) < len(measures) else
                     trigger_on_group(quantities, side.tiers,
                                      below_every_tier=side.below_every_tier))
                lead["verdict"] = dict(v.as_dict(), side=side.id, group=g["group"])
                for _q, m_id in measures[1:]:
                    entries[m_id]["judged_on"] = measures[0][1]
                behind = {"persons": lead.get("value")}
                results.append({"group": g["group"], "measure": measures[0][1],
                                "verdict": v.verdict, **({"tier": v.tier} if v.tier else {}),
                                **behind})
                if v.verdict == "crosses":
                    crosses.append({"group": g["group"], "tier": v.tier, **behind})
            s["groups"] = results
            s["crosses"] = crosses
        sides.append(s)
    for m_id, e in entries.items():
        if "verdict" not in e and "judged_on" not in e:
            if carrier_of_verdict:
                e["judged_on"] = carrier_of_verdict
            else:
                e["verdict"] = dict(cannot_judge("no side of this barrier judges it").as_dict())
    return sides


def _towns_summary(reading) -> dict:
    """a county's, district's or state's parts for one indicator, from
    read_place (D-183, D-185), with the statement every range carries."""
    from .place import RANGE_STATEMENT

    def town(t):
        return {"name": t.name, "code": t.code, "value": t.value}

    return {
        "statement": RANGE_STATEMENT, "touching": len(reading.towns),
        "in_range": len(reading.in_range),
        "range": {"minimum": reading.minimum, "maximum": reading.maximum,
                  "minimum_towns": reading.minimum_towns, "maximum_towns": reading.maximum_towns},
        "wholly_here": {"count": reading.whole_count, "minimum": reading.whole_minimum,
                        "maximum": reading.whole_maximum,
                        "minimum_towns": reading.whole_minimum_towns,
                        "maximum_towns": reading.whole_maximum_towns},
        "firm": (None if reading.firm_count is None else
                 {"count": reading.firm_count, "minimum": reading.firm_minimum,
                  "maximum": reading.firm_maximum, "minimum_towns": reading.firm_minimum_towns,
                  "maximum_towns": reading.firm_maximum_towns,
                  "means": "towns wholly here, without small samples or unchecked areas"}),
        "split": [dict(town(t), share_here=t.share, of=t.universe_count) for t in reading.split],
        "out_of_range": [dict(town(t), why=t.out_why) for t in reading.out_of_range],
    }


def _part_barriers(ctx: ProfileContext, place: dict, values: dict, reading) -> list[dict]:
    by_indicator = {i.indicator: i for i in (reading.indicators if reading else [])}
    out = []
    for barrier in ctx.standard.barriers:
        entries = {m_id: _measure_entry(ctx, place, ctx.standard.measures[m_id], values)
                   for m_id in barrier.measures}
        sides = _judge_barrier(ctx, barrier, entries)
        for e in entries.values():
            ind = by_indicator.get(e.get("indicator"))
            if ind is not None and not ind.located and e.get("value") is not None and all(
                    ctx.may_leave(r) for r in ctx.indicator_receipts.get(ind.indicator, ())):
                e["towns"] = _towns_summary(ind)
        out.append({"barrier": barrier.id, "words": barrier.words, "sides": sides,
                    "indicators": list(entries.values())})
    return out


# ── part 1: who is represented ───────────────────────────────────────────────
HOUSEHOLDS_FROM = "households_without_broadband"     # D-286: its own denominator


def _part_represented(ctx: ProfileContext, place: dict, values: dict) -> dict:
    from canopy.standards import Measure, _inferred_kind
    key = _key(place["authority"], place["code"])
    persons = ctx.persons.get(key)
    if persons:
        count, receipt, indicator = persons
        ctx.take(receipt)
        population = {"count": count, "counts": PERSONS,
                      "release": "2020 Census redistricting data (P1_001N), summed over this "
                                 "place's blocks by the block spine",
                      "published_by": "rewildingcities", "margin": None,
                      "why_no_margin": "a census count, published without a margin",
                      "receipt": receipt, "read_from": indicator}
    else:
        population = {"count": None, "counts": PERSONS,
                      "why": "no carrier count that may leave holds this place's persons (D-280)"}

    hv = values.get(HOUSEHOLDS_FROM)
    if hv is not None and hv.present and number(hv.get("households")) is not None:
        ctx.take(hv.receipt)
        households = {"count": number(hv.get("households")), "counts": "households",
                      "release": hv.get("time"), "published_by": hv.get("published_by"),
                      "margin": None,
                      "why_no_margin": "the ACS publishes one for this count, but the values "
                                       "file does not carry it (D-286)",
                      "receipt": hv.receipt, "read_from": HOUSEHOLDS_FROM}
    else:
        households = {"count": None, "counts": "households",
                      "why": (hv.why if hv is not None and hv.why else
                              "the ACS gives no household count here (D-286)")}

    needs = []
    for ind_id in ctx.registry.with_role("need"):
        v = values.get(ind_id)
        if v is None:
            continue
        ind = ctx.registry.get(ind_id)
        m = Measure(id=ind_id, status="acquired", indicator=ind_id,
                    estimate_kind=_inferred_kind(ind))
        entry = _value_entry(ctx, place["level"], m, v)
        entry["judged"] = "never: a need is shown, never held against a threshold"
        needs.append(entry)

    legislators = ({"status": "held_not_read", "why": "seats are held, but reading them into "
                                                     "profiles is not built yet"}
                   if ctx.seats_held else
                   {"status": "not_held", "missing_holding": "seats", "why": LEGISLATORS_WHY})

    con = ctx.loam.con
    inside = []
    for e in _rows(con, "SELECT to_authority, to_code FROM edges WHERE kind = 'contains' AND "
                        "from_authority = ? AND CAST(from_code AS VARCHAR) = ? "
                        "ORDER BY to_authority, to_code", key):
        child = _key(e["to_authority"], e["to_code"])
        row = ctx.places.get(child) or {}
        inside.append(_place_key(*child, _text(row.get("name"))) | {"level": _text(row.get("level"))})
    overlapping = []
    for e in _rows(con, "SELECT * FROM edges WHERE kind = 'overlaps' AND ((from_authority = ? "
                        "AND CAST(from_code AS VARCHAR) = ?) OR (to_authority = ? AND "
                        "CAST(to_code AS VARCHAR) = ?))", key + key):
        here_is_from = _key(e["from_authority"], e["from_code"]) == key
        other = (_key(e["to_authority"], e["to_code"]) if here_is_from else
                 _key(e["from_authority"], e["from_code"]))
        o = ctx.places.get(other) or {}
        overlapping.append(_place_key(*other, _text(o.get("name"))) | {
            "level": _text(o.get("level")),
            "edge": {"from": _place_key(e["from_authority"], e["from_code"]),
                     "to": _place_key(e["to_authority"], e["to_code"]),
                     "weight_population": number(e.get("weight_population")),
                     "weight_households": number(e.get("weight_households")),
                     "weight_reason": _text(e.get("weight_reason")) or None,
                     "means": "the share of the from place's residents and households "
                              "that lie in the to place (D-121)"}})
    overlapping.sort(key=lambda o: (o["level"], o["code"]))
    return {"population": population, "households": households, "needs": needs,
            "legislators": legislators, "inside": inside, "overlapping": overlapping}


# ── part 3: carriers ─────────────────────────────────────────────────────────
def _part_carriers(ctx: ProfileContext, place: dict, values: dict) -> list[dict]:
    out = []
    for ind_id in ctx.registry.with_role("carrier"):
        ind = ctx.registry.get(ind_id)
        if ind.derivation.kind != "located_count":
            continue
        v = values.get(ind_id)
        entry = {"indicator": ind_id, "type": ind.derivation.counts, "count": None,
                 "per_1000": None, "population": None, "use": None,
                 "use_why": "no use is recorded by this source", "published_by": None,
                 "vintage": None}
        if v is None:
            entry["why"] = "this plot holds no count of it here"
        elif v.withheld_from:
            entry.update(withheld=True, why=v.why)
        elif v.why:
            entry["why"] = v.why
        else:
            ctx.take(v.receipt)
            count = number(v.get("count"))
            entry.update(
                count=None if count is None else int(count),
                per_1000=number(v.get("value")),
                population={"count": number(v.get("households")),
                            "counts": _text(v.get("households_counts")) or None,
                            "release": "2020 Census (" + ", ".join(ind.rests_on.add) + ")"},
                published_by=v.get("published_by"), vintage=v.get("time"),
                boundary_vintage=v.get("boundary_vintage"), receipt=v.receipt,
                method=ctx.run_of(v.receipt))
            if entry["per_1000"] is None:
                entry["why_no_rate"] = _text(v.get("empty_reason")) or "no rate here"
            note = ctx.note(v.get("context_note"))
            if note:
                entry["context_note"] = note
        out.append(entry)
    return out


# ── part 4: where sources disagree ───────────────────────────────────────────
def _part_disagreements(ctx: ProfileContext, values: dict) -> list[dict]:
    """one measure only (D-282): indicators that measure the same thing,
    with values here from different publishers. both shown, none picked."""
    by_measure: dict[str, list] = {}
    for ind_id, v in values.items():
        if v.present and number(v.get("value")) is not None:
            by_measure.setdefault(ctx.registry.get(ind_id).measures, []).append((ind_id, v))
    out = []
    for measures, found in sorted(by_measure.items()):
        if len({_text(v.get("published_by")) for _, v in found}) < 2:
            continue
        shown = [{"indicator": i, "published_by": v.get("published_by"),
                  "value": number(v.get("value")), "unit": ctx.registry.get(i).unit,
                  "vintage": v.get("time"), "receipt": v.receipt} for i, v in sorted(found)]
        for i, v in found:
            ctx.take(v.receipt)
        entry = {"measures": measures, "values": shown, "difference": None, "reason": "unknown"}
        if len(shown) != 2:
            entry["difference_why"] = "more than two publishers; each value is shown"
        elif not comparable(shown[0]["unit"], shown[1]["unit"]):
            entry["difference_why"] = (f"their units differ ({shown[0]['unit']}, "
                                       f"{shown[1]['unit']}), so no difference is taken")
        else:
            entry["difference"] = shown[0]["value"] - shown[1]["value"]
            entry["difference_is"] = f"{shown[0]['indicator']} less {shown[1]['indicator']}"
        out.append(entry)
    return out


# ── part 5: what cannot be answered ──────────────────────────────────────────
def _part_cannot_answer(ctx: ProfileContext, barriers: list[dict], represented: dict,
                        withheld_here: set) -> dict:
    gaps = []
    if represented["legislators"]["status"] == "not_held":
        gaps.append({"holding": "seats", "why": LEGISLATORS_WHY})
    for m_id, m in ctx.standard.measures.items():
        if m.status == "acquired" and m.indicator and not ctx.indicator_receipts.get(m.indicator):
            gaps.append({"measure": m_id, "why": "declared acquired, but this plot holds no "
                                                 "values for it"})
    not_acquired = [{"measure": m_id, "barrier": ctx.standard.barrier_of(m_id).id,
                     "status": m.status, "source": m.source, "needs": m.needs}
                    for m_id, m in ctx.standard.measures.items() if m.status != "acquired"]
    cannot = [{"barrier": b["barrier"], "measure": e["measure"],
               "reason": e["verdict"].get("reason") or e["verdict"].get("says")}
              for b in barriers for e in b["indicators"]
              if (e.get("verdict") or {}).get("verdict") == "cannot_judge"]
    refusals = [ctx.refusal(r) for r in sorted(withheld_here)]
    part = {"gaps": gaps, "not_acquired": not_acquired, "cannot_judge": cannot,
            "refusals": refusals}
    if not any(part.values()):
        part["nothing_missing"] = "nothing is missing for this place"
    return part


# ── one place ────────────────────────────────────────────────────────────────
def build_profile(loam, authority: str, code: str, *, context: ProfileContext) -> dict:
    """one place's profile, all six parts, every part present (Contract 4).
    `context` is ProfileContext.open(loam, plot, root), read once per build."""
    from .place import read_place
    ctx = context
    key = _key(authority, code)
    place_row = ctx.places.get(key)
    if place_row is None:
        raise KeyError(f"{authority} {code} is not a place in this plot's graph")
    place = {"authority": key[0], "code": key[1], "level": _text(place_row.get("level")),
             "kind": _text(place_row.get("kind")), "name": _text(place_row.get("name")),
             "vintage": _text(place_row.get("vintage"))}
    if place["level"] not in LEVEL_ORDER:
        place["level_note"] = OTHER_LEVEL_WHY

    ctx.withheld_here = set()
    for receipt in ctx.structure:
        ctx.take(receipt)
    values = _values_at(ctx, *key)
    part_level = PART_LEVEL.get(place["level"], TOWN_LEVEL)
    reading = (read_place(loam, *key, root=ctx.root, part_level=part_level)
               if part_level else None)

    represented = _part_represented(ctx, place, values)
    barriers = _part_barriers(ctx, place, values, reading)
    carriers = _part_carriers(ctx, place, values)
    disagreements = _part_disagreements(ctx, values)
    cannot_answer = _part_cannot_answer(ctx, barriers, represented, set(ctx.withheld_here))

    note = ctx.note(place_row.get("context_note"))
    return {
        "place_key": f"{key[0]}:{key[1]}",
        "header": {"place": place, "flags": _plain(place_row.get("flags")),
                   "context_note": note,
                   "built_at": datetime.now(timezone.utc).isoformat(),
                   "built_by": {"profile": PROFILE_VERSION, "contract": CONTRACT,
                                "standard": ctx.standard.header()},
                   "gate": {"record": None, "why": GATE_WHY}},
        "represented": represented,
        "barriers": barriers,
        "carriers": carriers,
        "disagreements": {"entries": disagreements, **({} if disagreements else {
            "empty_because": "no measure here is published by more than one publisher"})},
        "cannot_answer": cannot_answer,
        "channels": {"pairings": [], "label": CHANNELS_LABEL, "source": None,
                     "empty_because": CHANNELS_EMPTY},
    }


def row_notes(profile: dict) -> list[str]:
    """every note a profile's rows carry: the place's own and its counts'."""
    notes = []
    if profile["header"].get("context_note"):
        notes.append(profile["header"]["context_note"]["id"])
    notes += [c["context_note"]["id"] for c in profile["carriers"] if c.get("context_note")]
    return list(dict.fromkeys(notes))


# ── every place, and the one artifact (D-274) ────────────────────────────────
def _enumerated(ctx: ProfileContext) -> list[tuple[str, str]]:
    """every place this plot answers for: plot_places when the manifest
    declares them, else every place. Contract 4's levels first, in its
    order, then every other level by name (D-292), then codes."""
    table = "plot_places" if "plot_places" in ctx.views else "places"
    rows = _rows(ctx.loam.con, f"SELECT authority, CAST(code AS VARCHAR) AS code, level "
                               f"FROM {table}")
    order = {lvl: i for i, lvl in enumerate(LEVEL_ORDER)}
    rows.sort(key=lambda r: (order.get(r["level"], len(order)), r["level"], r["authority"],
                             r["code"]))
    return [(r["authority"], r["code"]) for r in rows]


def build_profiles(loam, plot: str, root: str | Path, plot_dir: str | Path | None = None,
                   progress=None) -> tuple[list[dict], ProfileContext]:
    """every place's profile. `progress(done, total)` is called after each
    place, so a long build is never silent."""
    ctx = ProfileContext.open(loam, plot, root, plot_dir)
    keys = _enumerated(ctx)
    profiles = []
    for done, (a, c) in enumerate(keys, start=1):
        profiles.append(build_profile(loam, a, c, context=ctx))
        if progress is not None:
            progress(done, len(keys))
    return profiles, ctx


def _shown(path: Path, root: Path) -> str:
    """a path as receipts write it: from the garden's root when inside it."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def write_profiles(profiles: list[dict], ctx: ProfileContext, *, started: float) -> dict:
    """the one place_profile artifact and its receipt (D-274). its inputs
    are every receipt whose values entered, so the gate binds exactly what
    the file holds; every receipt withheld is named in its params, never
    an input (D-284)."""
    from canopy.envelope import (Envelope, Hasher, InputRecord, ProvenanceEntry, Warning,
                                 read_envelope, write_envelope)
    root, plot = ctx.root, ctx.plot
    data = ctx.plot_dir / ".data" / f"{STEP}_{OUTPUT}.json"
    receipt = ctx.plot_dir / ".envelopes" / f"{STEP}_{OUTPUT}.envelope.json"
    built_at = datetime.now(timezone.utc).isoformat()
    data.parent.mkdir(parents=True, exist_ok=True)
    data.write_text(json.dumps({"profile_version": PROFILE_VERSION, "contract": CONTRACT,
                                "plot": plot, "built_at": built_at,
                                "standard": ctx.standard.header(), "places": profiles},
                               indent=1, allow_nan=False))

    hasher = Hasher("full")
    read = sorted(ctx.read)
    inputs, inherited, datasets = [], [], []
    for artifact in read:
        path = ctx.plot_dir / ".envelopes" / f"{artifact}.envelope.json"
        env = read_envelope(path, validate=False)
        source = Path(env.data["path"])
        on_disk = source if source.is_absolute() else root / source
        inputs.append(InputRecord(name=artifact, semantic_type=env.metadata["semantic_type"],
                                  path=str(env.data["path"]), hash=hasher.hash_file(on_disk)))
        for entry in env.provenance:
            entry.lineage_branch = entry.lineage_branch or artifact
            inherited.append(entry)
        res = (env.metadata.get("lineage") or {}).get("data_resolution") or {}
        for name in (res.get("datasets_available") or []) + (res.get("datasets_acquired") or []):
            if name not in datasets:
                datasets.append(name)
    if not inputs:
        raise ProfileUnavailable("no receipt this build read may leave, so the profile has "
                                 "no lineage; nothing is written that the door could not judge")

    notes = list(dict.fromkeys(n for p in profiles for n in row_notes(p)))
    own = ProvenanceEntry(
        primitive="build_profile", version=PROFILE_VERSION, timestamp=built_at,
        params={"standard": ctx.standard.header(), "target": TARGET,
                "sharing_level": SHARING_LEVEL, "receipts_read": read,
                "receipts_withheld": sorted(ctx.withheld), "places": len(profiles),
                "structure": list(ctx.structure),
                "structure_withheld": ctx.structure_withheld()},
        inputs=inputs, duration_seconds=round(time.monotonic() - started, 3))
    metadata = {
        "semantic_type": PROFILE_TYPE, "data_category": "tabular", "crs": None,
        "row_count": len(profiles), "column_count": 8,
        "variables": ["place_key", "header", "represented", "barriers", "carriers",
                      "disagreements", "cannot_answer", "channels"],
        "id_field": "place_key", "spatial_unit": "place",
        "row_context_notes": notes, "context_notes": list(dict.fromkeys(
            ["census_tribal_places"] + notes)),
        "lineage": {"kind": "profile", "run": STEP,
                    "method": "canopy/wonder/profile.py (Contract 4, D-274)",
                    "data_resolution": {"datasets_available": datasets}},
        "interpretation_notes": [
            "A profile shows values, never standings (D-104).",
            "A verdict holds a place's own value against a stated, cited line; "
            "within_margin never means the line is met (D-272).",
            "A borrowed value is the named place's own, never this place's (D-276).",
            "Values from receipts the gate withholds at public never enter this file; "
            "each profile's part 5 names them (D-284)."]}
    warnings = [Warning(level="info", primitive="build_profile",
                        message=f"{len(profiles)} place(s) profiled; {len(read)} receipt(s) "
                                f"read, {len(ctx.withheld)} withheld at {TARGET}")]
    envelope = Envelope(data={"path": _shown(data, root), "format": "json"},
                        metadata=metadata, provenance=inherited + [own], warnings=warnings)
    write_envelope(envelope, receipt, validate=True, project_root=root)
    return {"data": _shown(data, root), "receipt": _shown(receipt, root),
            "read": read, "withheld": sorted(ctx.withheld), "places": len(profiles),
            "structure_withheld": ctx.structure_withheld(),
            "seconds": round(time.monotonic() - started, 1)}
