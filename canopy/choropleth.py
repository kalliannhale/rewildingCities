"""
canopy/choropleth.py ~ a table's values joined onto a plot's places (D-331)

the one home of the join that draws a long-form table on an outline. map.py
imports it to draw locally; the canonical command's --display --join imports it
to draw the joined display copy the door publishes. it knows nothing of files,
buckets or ArcGIS: a frame and a list of features in, features and counts out.

  keyed      a row joins a place on (unit_authority, unit_code) to the place's
             (authority, code), never on a name and never on a code alone: a
             county and a House district can both be 23001 (LAYER-1)
  wide       one feature per place, and every indicator's columns beside it,
             named <indicator>__<column>, so a place's own properties (its
             authority, code, name and notes) are never overwritten
  kept       a place with no row stays, its columns empty and joined false: a
             gap is not a zero, and a town the source never measured never
             vanishes from the map (MAP-2)
  counted    every row is accounted for: in the outline, at the outline's
             level but outside it (the rest of a national reference
             population), at another level of the same authority, or under
             another authority. the widths come from seeds/authorities, so no
             authority's codes are special here
  refused    a table that is not long-form, a row written twice, a place
             without its authority and code, an outline under two
             authorities, a column name that would overwrite a place's own

a joined row's notes are the notes its drawn features carry, read from their
note columns, so a national table's other places bind nothing (D-156). ~
"""

from __future__ import annotations

import math
from pathlib import Path

import yaml

LONG_FORM = ("unit_authority", "unit_code", "indicator")
NOTE_COLUMNS = ("context_note", "display_note")
SEP = "__"
JOINED = "joined"


class ChoroplethRefusal(Exception):
    """the join declines, saying why and what would let it through."""

    def __init__(self, reason: str, would_admit: str):
        super().__init__(reason)
        self.reason = reason
        self.would_admit = would_admit


def load_widths(root: str | Path) -> dict[str, dict[str, int]]:
    """{authority: {level: width}} from seeds/authorities/authorities.yml."""
    path = Path(root) / "seeds" / "authorities" / "authorities.yml"
    doc = yaml.safe_load(path.read_text()) or {}
    out: dict[str, dict[str, int]] = {}
    for authority, spec in (doc.get("authorities") or {}).items():
        levels = (spec or {}).get("levels") or {}
        out[authority] = {lvl: int((d or {}).get("width")) for lvl, d in levels.items()
                          if (d or {}).get("width") is not None}
    return out


def plain(v):
    """a cell as JSON holds it: numpy scalars unwrapped, NaN and NaT as None."""
    if v is None:
        return None
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        try:
            v = v.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(v, float) and math.isnan(v):
        return None
    if type(v).__name__ in ("NaTType", "NAType"):
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def column_name(indicator: str, column: str) -> str:
    return f"{indicator}{SEP}{column}"


def is_long_form(df) -> bool:
    return set(LONG_FORM).issubset(set(df.columns))


def wide(df) -> tuple[dict, list[str], dict[str, list[str]]]:
    """the long table as one record per unit: {(authority, code): {column: value}},
    the indicators in table order, and each indicator's column names."""
    if not is_long_form(df):
        raise ChoroplethRefusal(
            f"the table is not long-form: it lacks {', '.join(c for c in LONG_FORM if c not in df.columns)}",
            "join a table of indicator values or standings, one row per unit and indicator")
    keys = df[list(LONG_FORM)].astype(str)
    twice = keys.duplicated(keep=False)
    if bool(twice.any()):
        ex = keys[twice].iloc[0]
        raise ChoroplethRefusal(
            f"{int(twice.sum())} rows share a unit and indicator, e.g. {ex['unit_authority']} "
            f"{ex['unit_code']} {ex['indicator']}, so which one a map shows would be a choice",
            "one row per unit and indicator, upstream")
    carried = [c for c in df.columns if c not in ("unit_authority", "unit_code", "indicator")]
    indicators: list[str] = []
    for ind in df["indicator"].astype(str):
        if ind not in indicators:
            indicators.append(ind)
    columns = {ind: [column_name(ind, c) for c in carried] for ind in indicators}
    records: dict[tuple, dict] = {}
    for row in df.to_dict(orient="records"):
        key = (str(row["unit_authority"]), str(row["unit_code"]))
        rec = records.setdefault(key, {})
        ind = str(row["indicator"])
        for c in carried:
            rec[column_name(ind, c)] = plain(row[c])
    return records, indicators, columns


def _feature_key(props: dict) -> tuple[str, str] | None:
    a, c = props.get("authority"), props.get("code")
    if a is None or c is None or str(a).strip() == "" or str(c).strip() == "":
        return None
    return str(a), str(c)


def join(df, places: list[dict], *, level: str, widths: dict[str, dict[str, int]]) -> dict:
    """join a long-form table onto places (each a dict of a feature's properties,
    in feature order). returns {"properties": [...], "counts": {...},
    "indicators": [...], "columns": {...}}; properties[i] belongs to places[i]."""
    records, indicators, columns = wide(df)
    keys = []
    for i, props in enumerate(places):
        k = _feature_key(props)
        if k is None:
            raise ChoroplethRefusal(
                f"place {i} carries no authority and code, so nothing can be joined to it "
                f"by key; its properties: {', '.join(sorted(props)) or '(none)'}",
                "draw on a place outline, whose places carry authority and code (LAYER-1)")
        keys.append(k)
    authorities = sorted({a for a, _ in keys})
    if len(authorities) != 1:
        raise ChoroplethRefusal(f"the outline's places are under {len(authorities)} authorities "
                                f"({', '.join(authorities)})", "one authority per outline")
    authority = authorities[0]
    width = (widths.get(authority) or {}).get(level)
    if width is None:
        raise ChoroplethRefusal(
            f"seeds/authorities declares no width for level '{level}' of {authority}, so rows "
            f"outside this outline cannot be told from rows at another level",
            f"declare {authority}'s {level} width in seeds/authorities/authorities.yml")
    if len(set(keys)) != len(keys):
        raise ChoroplethRefusal("two of the outline's places share an authority and code",
                                "repair the outline upstream")
    taken = {name for props in places for name in props}
    every = [c for ind in indicators for c in columns[ind]]
    clash = sorted(taken.intersection(every + [JOINED]))
    if clash:
        raise ChoroplethRefusal(f"the table's columns would overwrite the places' own: "
                                f"{', '.join(clash)}", "rename the column upstream")

    out, without = [], 0
    for props, k in zip(places, keys):
        rec = records.get(k)
        new = dict(props)
        if rec is None:
            without += 1
            for c in every:
                new[c] = None
            new[JOINED] = False
        else:
            for c in every:
                new[c] = rec.get(c)
            new[JOINED] = True
        out.append(new)

    in_outline = set(keys)
    counts = {"rows_in_outline": 0, "rows_outside_outline": 0, "rows_other_level": 0,
              "rows_other_authority": 0, "places": len(places),
              "places_without_row": without}
    for (a, c) in records:
        if (a, c) in in_outline:
            counts["rows_in_outline"] += 1
        elif a != authority:
            counts["rows_other_authority"] += 1
        elif len(c) == width:
            counts["rows_outside_outline"] += 1
        else:
            counts["rows_other_level"] += 1
    if counts["rows_in_outline"] == 0:
        raise ChoroplethRefusal(
            f"no row of the table names a place of this outline ({authority}, level {level}); "
            f"an all-empty map would read as a finding",
            "join the table to the outline its units are drawn on")
    return {"properties": out, "counts": counts, "indicators": indicators,
            "columns": columns, "authority": authority, "level": level}


def row_notes(properties: list[dict]) -> list[str]:
    """every note id the drawn features carry, once each: the places' own
    note columns and each indicator's <indicator>__context_note."""
    found: set[str] = set()
    for props in properties:
        for name, value in props.items():
            if name in NOTE_COLUMNS or name.endswith(SEP + "context_note"):
                if isinstance(value, str) and value.strip():
                    found.add(value.strip())
    return sorted(found)


def colour_field(indicator: str, columns: dict[str, list[str]], *, markers: bool = False) -> str:
    """the column a map of this indicator colours or sizes by: a standing's
    percentile, a marker's count, otherwise the value."""
    names = columns.get(indicator)
    if names is None:
        raise ChoroplethRefusal(f"no indicator '{indicator}' in this copy",
                                f"one of {', '.join(columns) or '(none)'}")
    order = ("count", "value") if markers else ("percentile", "value")
    for c in order:
        if column_name(indicator, c) in names:
            return column_name(indicator, c)
    raise ChoroplethRefusal(f"'{indicator}' has no {' or '.join(order)} column to draw by",
                            "a table of values or standings")
