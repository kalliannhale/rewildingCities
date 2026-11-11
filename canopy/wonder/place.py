"""
canopy/wonder/place.py

place ~ one place, read through its edges

read_plot reads a plot by what it holds; this reads one place by what is
true of it. it is the first reader keyed by place rather than by type, and
it is kept small on purpose: a reading through edges, which the place
profile (Contract 4, Sprint 06) can grow from rather than replace (D-184).
one measurement, many renderings (P-03): read_place measures and returns an
object, say_place speaks it, and neither computes what the other does.

for a district or a county it reads, per indicator:

  ~ the place's own value, the publisher's estimate (Contract 3 rule 1),
    never a sum or average of its towns
  ~ every town its edges touch, with both shares (MP-76): overlaps edges
    into the place, or contains edges out of it
  ~ the towns' range: minimum, maximum and how many towns (rule 3)

what enters the range is declared, and everything left out is named:

  ~ a town with none of the value's universe here stays listed and out of
    the range (D-180, ZERO-1), judged by the weight its universe declares
  ~ a value not attached to its place (other boundaries, no declared rule,
    a Census tribal area) or with no value stays out, with why
  ~ a statistical area attached unchecked, and a value resting on a small
    sample, enter the range, and the range's ends say what they rest on.
    when either is among the towns wholly here, a firm range is read too:
    the towns wholly here without them, the core whose values describe
    this place's people on a sound sample, so neither a shaky value nor a
    split town can quietly set an end of it (D-183, D-185)
  ~ a share is shown only where the universe equals its weight; a
    contained universe shows its count and no share (D-182)
  ~ a town wholly inside the place is told apart from a town its line
    splits, by the universe's own weight: exactly all of it here, or not.
    a whole town's value is a statement about this place's people; a split
    town's describes people partly elsewhere, so split towns are named one
    by one with how much of them is here, and never quietly set an end of
    the range of whole towns (D-185). no threshold is chosen: the boundary
    is the data's own
  ~ each indicator's towns are listed most-here first, so the reader sees
    who makes the place up; the top list stays alphabetical, for finding

a town range is one estimate per town, however much of the town lies in
the place: a spread of town estimates, not of the place's people, and wider
than the truth where samples are small. every telling says so.

the parts are towns by default (`cousub`); `part_level` reads any other
level an edge reaches, so the same reader serves tracts or divisions in
another plot (D-184).

it is a READ. it writes nothing, allocates nothing (D-179), and needs a bed
opened by open_plot, whose views it reads. ~
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from ..loam.edge_rules import load_universes, share_of, universe_for, zero_here

TOWN_LEVEL = "cousub"
NEEDED_VIEWS = ("places", "edges", "place_values")

RANGE_STATEMENT = ("each range is one estimate per town, however much of the town lies "
                   "here: a spread of town estimates, not of this place's people, and wider "
                   "than the truth where samples are small")


@dataclass
class TownReading:
    """a town one of the place's edges touches, and how much of it is here."""
    authority: str
    code: str
    name: str
    kind: str
    edge_kind: str
    weight_population: float | None
    weight_households: float | None
    weight_reason: str | None
    residents_here: bool | None       # by the population weight (D-121, D-180)
    note: str = ""


@dataclass
class TownValue:
    """one town's value for one indicator, and whether it enters the range."""
    authority: str
    code: str
    name: str
    value: float | None
    status: str | None
    universe_count: float | None
    share: float | None
    share_why: str
    in_range: bool
    out_why: str = ""
    unchecked: bool = False
    small_sample: str = ""
    zero_unjudged: str = ""
    # the universe's own weight on this town's edge, and whether all of the
    # universe is here by it (D-185); None when the weight is unknown
    weight: float | None = None
    whole: bool | None = None


@dataclass
class IndicatorReading:
    """one indicator at this place: its own value, and its towns' range."""
    indicator: str
    name: str
    own_value: float | None
    own_status: str | None
    own_why: str
    own_moe: float | None
    own_moe_status: str | None
    own_reliability: str
    universe: str | None
    universe_relation: str | None
    universe_note: str
    towns: list[TownValue] = field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    minimum_towns: list[str] = field(default_factory=list)
    maximum_towns: list[str] = field(default_factory=list)
    # the towns wholly here without small samples or unchecked areas (D-183,
    # D-185); None when no town wholly here is shaky, since then the firm
    # range is the range of towns wholly here
    firm_minimum: float | None = None
    firm_maximum: float | None = None
    firm_minimum_towns: list[str] = field(default_factory=list)
    firm_maximum_towns: list[str] = field(default_factory=list)
    firm_count: int | None = None
    # the range of towns wholly inside the place (D-185)
    whole_minimum: float | None = None
    whole_maximum: float | None = None
    whole_minimum_towns: list[str] = field(default_factory=list)
    whole_maximum_towns: list[str] = field(default_factory=list)
    whole_count: int = 0

    @property
    def in_range(self) -> list[TownValue]:
        return [t for t in self.towns if t.in_range]

    @property
    def split(self) -> list[TownValue]:
        """towns in the range that the place's line splits, most-here first."""
        return [t for t in self.towns if t.in_range and not t.whole]

    @property
    def left_out(self) -> list[TownValue]:
        return [t for t in self.towns if not t.in_range]


@dataclass
class PlaceReading:
    """everything this reading knows about one place, at one moment."""
    authority: str
    code: str
    found: bool
    why: str = ""
    level: str = ""
    kind: str = ""
    name: str = ""
    vintage: str = ""
    context_note: str | None = None
    towns: list[TownReading] = field(default_factory=list)
    indicators: list[IndicatorReading] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        for ind, ind_d in zip(self.indicators, d["indicators"]):
            ind_d["in_range_count"] = len(ind.in_range)
            ind_d["touching_count"] = len(ind.towns)
        d["range_statement"] = RANGE_STATEMENT
        return d


def _number(x) -> float | None:
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def _text(x) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return str(x)


def _rows(con, sql: str, params=()) -> list[dict]:
    cursor = con.execute(sql, list(params))
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _views(con) -> set[str]:
    return {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}


def _indicator_names(root: Path) -> dict[str, str]:
    names: dict[str, str] = {}
    for f in sorted((root / "seeds" / "indicators").glob("*.yml")):
        doc = yaml.safe_load(f.read_text()) or {}
        for key, spec in (doc.get("indicators") or {}).items():
            names[key] = (spec or {}).get("name") or key
    return names


# plain words for the reasons a derivation gives when it has no value; the
# code's own words follow in brackets, so nothing is lost in translation
def _plain_empty(reason: str, universe: str | None) -> str:
    if reason == "zero denominator":
        return f"the ACS estimates none of its {universe or 'units'} (zero denominator)"
    if reason.startswith("source value empty"):
        column = reason.partition(":")[2].strip()
        return f"the ACS publishes no value here ({column or 'its source'} is empty)"
    return reason or "none given"


WHOLE = 1 - 1e-9


def _range(values: list) -> tuple[float | None, float | None, list[str], list[str]]:
    low = min((t.value for t in values), default=None)
    high = max((t.value for t in values), default=None)
    return (low, high, [t.name for t in values if t.value == low],
            [t.name for t in values if t.value == high])


def _touching(con, authority: str, code: str, towns: dict) -> list[tuple[dict, dict]]:
    """(edge, town) for every town an edge of this place reaches: overlaps
    edges into it, and contains edges out of it (a county's towns)."""
    found = []
    for edge in _rows(con, "SELECT * FROM edges WHERE kind = 'overlaps' AND "
                           "to_authority = ? AND CAST(to_code AS VARCHAR) = ?", (authority, code)):
        town = towns.get((str(edge["from_authority"]), str(edge["from_code"])))
        if town:
            found.append((edge, town))
    for edge in _rows(con, "SELECT * FROM edges WHERE kind = 'contains' AND "
                           "from_authority = ? AND CAST(from_code AS VARCHAR) = ?", (authority, code)):
        town = towns.get((str(edge["to_authority"]), str(edge["to_code"])))
        if town:
            found.append((edge, town))
    return sorted(found, key=lambda pair: (_text(pair[1].get("name")), str(pair[1]["code"])))


def read_place(loam, authority: str, code: str, *, root: str | Path | None = None,
               part_level: str = TOWN_LEVEL) -> PlaceReading:
    """
    read one place through its edges ~ its own values, every part it
    touches (towns, by default) with both shares, and their range per
    indicator. ~
    """
    from .possibility import _root
    base = Path(root) if root else _root()
    con = loam.con
    authority, code = str(authority), str(code)

    missing = [v for v in NEEDED_VIEWS if v not in _views(con)]
    if missing:
        return PlaceReading(authority, code, found=False,
                            why=f"this bed has no {', '.join(missing)} view; the graph was not "
                                f"made, and wonder says why under its graph line")
    place = _rows(con, "SELECT * FROM places WHERE authority = ? AND CAST(code AS VARCHAR) = ?",
                  (authority, code))
    if not place:
        return PlaceReading(authority, code, found=False,
                            why=f"{authority} {code} is not a place in this plot's graph")
    place = place[0]

    towns_by_key = {(str(t["authority"]), str(t["code"])): t
                    for t in _rows(con, "SELECT * FROM places WHERE level = ?", (part_level,))}
    touching = _touching(con, authority, code, towns_by_key)
    universes = load_universes(base)
    persons = universe_for("persons", universes)

    towns: list[TownReading] = []
    for edge, town in touching:
        here, why = zero_here(edge, persons)
        note = ("its land touches this place; none of its residents live here (D-180)"
                if here is True else (f"whether its residents live here cannot be told: {why}"
                                      if here is None else ""))
        towns.append(TownReading(
            authority=str(town["authority"]), code=str(town["code"]),
            name=_text(town.get("name")), kind=_text(town.get("kind")),
            edge_kind=_text(edge.get("kind")),
            weight_population=_number(edge.get("weight_population")),
            weight_households=_number(edge.get("weight_households")),
            weight_reason=_text(edge.get("weight_reason")) or None,
            residents_here=None if here is None else not here, note=note))

    own_rows = _rows(con, "SELECT * FROM place_values WHERE unit_authority = ? AND unit_code = ?",
                     (authority, code))
    keys = [(t.authority, t.code) for t in towns]
    town_rows: dict[tuple[str, str, str], dict] = {}
    if keys:
        holes = ", ".join("(?, ?)" for _ in keys)
        flat = [x for k in keys for x in k]
        for row in _rows(con, f"SELECT v.* FROM place_values v JOIN (VALUES {holes}) AS k(a, c) "
                              f"ON v.unit_authority = k.a AND v.unit_code = k.c", flat):
            key = (row["unit_authority"], row["unit_code"], row["indicator"])
            # a town with several rows for one indicator (other vintages) keeps
            # the attached one; the rest are someone else's boundaries
            if key not in town_rows or (row.get("attached") and not town_rows[key].get("attached")):
                town_rows[key] = row

    names = _indicator_names(base)
    indicators = sorted({r["indicator"] for r in own_rows} | {k[2] for k in town_rows})
    readings: list[IndicatorReading] = []
    for indicator in indicators:
        own = next((r for r in own_rows if r["indicator"] == indicator and r.get("attached")),
                   next((r for r in own_rows if r["indicator"] == indicator), None))
        counts = _text((own or {}).get("households_counts")) or next(
            (_text(r.get("households_counts")) for k, r in town_rows.items()
             if k[2] == indicator and _text(r.get("households_counts"))), "")
        universe = universe_for(counts, universes)
        universe_note = ("" if universe else
                         (f"'{counts}' is not a declared universe (seeds/universes, D-181), so "
                          f"no share is shown and zero cannot be judged" if counts else
                          "this value names no universe, so no share is shown and zero "
                          "cannot be judged"))
        if universe and universe.relation == "contains":
            universe_note = (f"no share is shown: {universe.weight} only contains "
                             f"{universe.counts} (D-182)")

        values: list[TownValue] = []
        for (edge, town), reading in zip(touching, towns):
            row = town_rows.get((reading.authority, reading.code, indicator))
            value = _number((row or {}).get("value"))
            share, share_why = share_of(edge, universe)
            tv = TownValue(
                authority=reading.authority, code=reading.code, name=reading.name,
                value=value, status=(row or {}).get("status"),
                universe_count=_number((row or {}).get("households")),
                share=share, share_why=share_why, in_range=False,
                unchecked=(row or {}).get("status") == "unchecked_statistical",
                small_sample=_text((row or {}).get("reliability_note")))
            zero, zero_why = zero_here(edge, universe)
            tv.weight = _number(edge.get(universe.weight)) if universe else None
            tv.whole = None if tv.weight is None else tv.weight >= WHOLE
            if row is None:
                tv.out_why = "no value for this town"
            elif not row.get("attached"):
                tv.out_why = _text(row.get("why")) or f"not attached ({row.get('status')})"
            elif value is None:
                tv.out_why = f"no value: {_plain_empty(_text(row.get('empty_reason')), counts)}"
            elif zero is True:
                tv.out_why = f"{zero_why} (D-180)"
            else:
                tv.in_range = True
                tv.zero_unjudged = zero_why if zero is None else ""
            values.append(tv)

        # most-here first, so the reader sees who makes the place up; an
        # unknown weight goes last, and names break ties
        values.sort(key=lambda t: (-(t.weight if t.weight is not None else -1), t.name))
        entered = [t for t in values if t.in_range]
        low, high, low_names, high_names = _range(entered)
        whole = [t for t in entered if t.whole]
        w_low, w_high, w_low_names, w_high_names = _range(whole)
        firm = [t for t in whole if not (t.small_sample or t.unchecked)]
        shaky = len(firm) < len(whole)
        f_low, f_high, f_low_names, f_high_names = _range(firm) if shaky else (None, None, [], [])
        readings.append(IndicatorReading(
            indicator=indicator, name=names.get(indicator, indicator),
            own_value=_number((own or {}).get("value")),
            own_status=(own or {}).get("status"),
            own_why=_text((own or {}).get("why")) if own else "the publisher gives no value here",
            own_moe=_number((own or {}).get("moe")),
            own_moe_status=_text((own or {}).get("moe_status")) or None,
            own_reliability=_text((own or {}).get("reliability_note")),
            universe=counts or None,
            universe_relation=universe.relation if universe else None,
            universe_note=universe_note, towns=values,
            minimum=low, maximum=high, minimum_towns=low_names, maximum_towns=high_names,
            firm_minimum=f_low, firm_maximum=f_high,
            firm_minimum_towns=f_low_names, firm_maximum_towns=f_high_names,
            firm_count=len(firm) if shaky else None,
            whole_minimum=w_low, whole_maximum=w_high,
            whole_minimum_towns=w_low_names, whole_maximum_towns=w_high_names,
            whole_count=len(whole)))

    return PlaceReading(
        authority=authority, code=code, found=True,
        level=_text(place.get("level")), kind=_text(place.get("kind")),
        name=_text(place.get("name")), vintage=_text(place.get("vintage")),
        context_note=_text(place.get("context_note")) or None,
        towns=towns, indicators=readings)


def _pct(w: float | None) -> str:
    if w is None:
        return "unknown"
    if w == 0:
        return "0%"
    if w < 0.001:
        return "under 0.1%"
    if w >= 0.9995:
        return "100%"
    return f"{w * 100:.1f}%"


def _figure(v: float | None) -> str:
    return "no value" if v is None else f"{v:.1f}"


def _count(n: float | None) -> str:
    return "an unknown count of" if n is None else f"{n:,.0f}"


def _rests(t: TownValue, universe: str | None) -> str:
    """what one town's value rests on, said beside it."""
    bits = [f"on {_count(t.universe_count)} {universe or 'units'}"]
    if t.small_sample:
        bits.append("a small sample")
    if t.unchecked:
        bits.append("a statistical area, attached unchecked")
    return ", ".join(bits)


def _how_much_here(t: TownValue, universe: str | None) -> str:
    """for a split town: how much of it is here, with the count it is of, so
    a share is never read without its scale (D-185). a contained universe
    has no share of its own to say (D-182)."""
    if t.whole:
        return ""
    if t.share is not None:
        return f"{_pct(t.share)} of its {_count(t.universe_count)} {universe or 'units'} here"
    return "partly here"


def _about(t: TownValue, universe: str | None) -> str:
    """everything a reader must know beside a town named at a range's end."""
    bits = [b for b in (_how_much_here(t, universe),
                        "a small sample" if t.small_sample else "",
                        "a statistical area, attached unchecked" if t.unchecked else "") if b]
    return f"{t.name}, {', '.join(bits)}" if bits else t.name


def _end(value: float | None, names: list[str], towns: list[TownValue],
         universe: str | None) -> str:
    """one end of a range, saying what it rests on and how much of it is
    here (D-183, D-185)."""
    said = [_about(next(x for x in towns if x.name == name), universe) for name in names]
    return f"{_figure(value)} ({'; '.join(said)})"


def _span(low, high, low_names, high_names, towns, universe, across: str) -> str:
    """a range, said once: `low to high`, or `all X` when its ends are one."""
    if low == high:
        names = sorted(set(low_names) | set(high_names),
                       key=lambda n: next(i for i, t in enumerate(towns) if t.name == n))
        return f"all {_end(low, names, towns, universe)}, {across}"
    return (f"{_end(low, low_names, towns, universe)} to "
            f"{_end(high, high_names, towns, universe)}, {across}")


def say_place(reading: PlaceReading) -> str:
    """speak a place reading, plainly. it computes nothing. ~"""
    if not reading.found:
        return f"📍  {reading.authority} {reading.code}: {reading.why}"

    lines = [f"📍  {reading.name}",
             f"   {reading.authority} {reading.code} ~ {reading.kind}, "
             f"on {reading.vintage} boundaries"]
    if reading.context_note:
        lines.append(f"   carries the note {reading.context_note} (seeds/notes)")

    lines.append(f"\n   towns its edges touch: {len(reading.towns)}")
    for t in reading.towns:
        if t.residents_here is False:
            lines.append(f"     ~ {t.name} ({t.kind}): {t.note}")
            continue
        households = (_pct(t.weight_households) if t.weight_households is not None
                      else f"no household share ({t.weight_reason or 'no reason given'})")
        lines.append(f"     ~ {t.name} ({t.kind}): {_pct(t.weight_population)} of its "
                     f"residents, {households} of its households")
        if t.note:
            lines.append(f"         {t.note}")
    if reading.indicators:
        lines.append(f"\n   {RANGE_STATEMENT}.")

    for ind in reading.indicators:
        lines.append(f"\n   {ind.name} ({ind.indicator})")
        own = f"     this place: {_figure(ind.own_value)}"
        if ind.own_value is None:
            own += f" ({ind.own_why})"
        elif ind.own_moe is not None:
            own += f", margin {ind.own_moe:.1f}"
        elif ind.own_moe_status == "not_derived":
            own += ", margin not derived (D-18)"
        if ind.own_reliability:
            own += f"; {ind.own_reliability}"
        lines.append(own + ", the publisher's own estimate")
        if ind.universe_note:
            lines.append(f"     {ind.universe_note}")

        lines.append("     each town, as the publisher gives it, most of it here first:")
        for t in ind.towns:
            if not t.in_range:
                value = f"{_figure(t.value)}, " if t.value is not None else ""
                lines.append(f"       ~ {t.name}: {value}left out of the range: {t.out_why}")
                continue
            line = f"       ~ {t.name}: {_figure(t.value)}, {_rests(t, ind.universe)}"
            if t.share is not None:
                line += f"; {_pct(t.share)} of its {ind.universe} here"
            if t.zero_unjudged:
                line += f"; whether any are here cannot be told ({t.zero_unjudged})"
            lines.append(line)

        entered = ind.in_range
        if not entered:
            lines.append(f"     range: none; no town of {len(ind.towns)} has a value that enters it")
            continue
        lines.append("     range: " + _span(
            ind.minimum, ind.maximum, ind.minimum_towns, ind.maximum_towns, entered,
            ind.universe, f"across {len(entered)} of {len(ind.towns)} towns"))
        whole = [t for t in entered if t.whole]
        if whole:
            lines.append("     towns wholly here: " + _span(
                ind.whole_minimum, ind.whole_maximum, ind.whole_minimum_towns,
                ind.whole_maximum_towns, whole, ind.universe, f"across {len(whole)}"))
        else:
            lines.append("     towns wholly here: none with a value in the range")
        if ind.split:
            lines.append("     towns split by its line: " + "; ".join(
                f"{_figure(t.value)} ({_about(t, ind.universe)})" for t in ind.split))
        if ind.firm_count is not None:
            label = "     wholly here, without small samples or unchecked areas: "
            if ind.firm_count:
                firm = [t for t in whole if not (t.small_sample or t.unchecked)]
                lines.append(label + _span(
                    ind.firm_minimum, ind.firm_maximum, ind.firm_minimum_towns,
                    ind.firm_maximum_towns, firm, ind.universe, f"across {ind.firm_count}"))
            else:
                lines.append(label + "none; every town wholly here rests on a small "
                                     "sample or is a statistical area attached unchecked")
    return "\n".join(lines)
