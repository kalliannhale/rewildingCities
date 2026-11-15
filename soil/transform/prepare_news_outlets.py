"""
soil/transform/prepare_news_outlets.py  |  rewildingCities

prepare_news_outlets ~ one row per local news outlet, placed in a town by
the town's code, never by a point (Sprint 06, step 3, the fifth carrier)

reads the grouped outlet stack (group_outlet_records) and the places table,
and writes each outlet once, in the town its sources give. what is placed
and why is the outlet_carriers method's (D-212); in short:

  ~ one outlet per group (D-243). its id is made from its members, never
    from row order: outlet:<source>:<name key> of its first member by the
    declaration's source_order, so a fresh copy of one listing renumbers
    nobody else. groups that would share an id each add their first
    member's line, flagged id_by_line
  ~ a town a source names (named_town) places the outlet (D-241). when no
    source names one, the method's choice town_fallback says whether the
    town of the publisher's office may (office_town, D-242): never its
    street address, and never compared with a named town
  ~ towns are matched by name after the declared Census suffixes come off
    (seeds/crosswalks/places/census_name_suffixes.yml): lowercase, periods
    and apostrophes dropped, a hyphen read as a space, spaces collapsed.
    nothing else is forgiven, and no abbreviation is expanded. a named
    county narrows the match when it is one of the state's; an office
    county never does, since Cision's reads Cook (D-204)
  ~ two different towns in one group are towns_disagree; a name matching no
    town is no_town_match; one matching two with no county to choose is
    ambiguous_town; no town at all is no_town_given. each is listed with
    its records, never placed (D-244)
  ~ a source's operating status is read through the declaration's
    operating_vocabulary (D-245): operating, ceased, or last_post (a value
    opening with the declared prefix, kept with its words). a value in no
    list stays counted and says so. what a ceased outlet becomes is the
    method's choice ceased_outlets: listed, or counted and flagged
  ~ a review (seeds/crosswalks/outlets/outlet_reviews.yml) is a person's
    reading: a merge joins the groups of the records it names; a town names
    the code a person read for one record's outlet. a review is keyed by
    the source and the name as written, so it lapses when the words change,
    and it refuses the run when no record gives it or the run no longer
    needs it (D-240's rule)

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  grouped (outlet_groups), places (places)
Params:
  sources         required: the outlet declaration ($crosswalks.outlet_sources)
  names           required: the Census name suffixes ($crosswalks.census_name_suffixes)
  reviews         optional: reviewed records ($crosswalks.outlet_reviews)
  town_fallback   required: none | office_town
  ceased_outlets  required: listed | counted
  state_fips      required: two digits
Output: the outlets, csv, one row per placed outlet, keyed by feature_id;
        every outlet not placed is listed in the receipt with its reason. ~
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

GEOID = "us_census_geoid"
KEY = ["feature_id"]
SPATIAL_UNIT = "news_outlet"
COLUMNS = ["feature_id", "name", "town_code", "town_name", "county_code", "placed_by",
           "town_as_written", "town_from", "operating", "operating_note", "sources",
           "records", "review_evidence", "review_read_on", "review_read_by", "flags"]
TOWN_FALLBACKS = ("none", "office_town")
CEASED_CHOICES = ("listed", "counted")
REVIEWABLE = ("towns_disagree", "no_town_match", "ambiguous_town", "no_town_given")
REVIEW_FIELDS = ("evidence", "read_on", "read_by")


class OutletsRefused(ValueError):
    """an outlet table the declarations refuse, with why."""


def _text(x) -> str | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    t = str(x).strip()
    return t or None


def norm(text: str) -> str:
    """a name as compared: lowercase, periods and apostrophes dropped, a
    hyphen read as a space, spaces collapsed. nothing else."""
    t = str(text).lower()
    t = re.sub(r"[.'\u2019]", "", t)
    t = t.replace("-", " ")
    return re.sub(r"\s+", " ", t).strip()


def strip_suffix(text: str, suffixes) -> str:
    """the name compared, with one declared trailing suffix taken off."""
    t = norm(text)
    for s in sorted((norm(x) for x in suffixes), key=len, reverse=True):
        if s and t.endswith(" " + s):
            return t[: -len(s) - 1].strip()
    return t


# ── the declarations ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class Vocabulary:
    operating: frozenset
    ceased: frozenset
    last_post_prefix: str


def read_vocabulary(sources: dict) -> Vocabulary:
    v = (sources or {}).get("operating_vocabulary")
    if not isinstance(v, dict):
        raise OutletsRefused("the outlet declaration has no operating_vocabulary, so a "
                             "source's operating status cannot be read (D-245)")
    operating = frozenset(norm(x) for x in v.get("operating") or [])
    ceased = frozenset(norm(x) for x in v.get("ceased") or [])
    prefix = _text(v.get("last_post_prefix"))
    if not operating or not ceased or not prefix:
        raise OutletsRefused("operating_vocabulary needs operating, ceased and "
                             "last_post_prefix (D-245)")
    both = sorted(operating & ceased)
    if both:
        raise OutletsRefused(f"operating_vocabulary lists {', '.join(both)} as both "
                             f"operating and ceased; a value means one thing")
    return Vocabulary(operating, ceased, norm(prefix))


def read_source_order(sources: dict, held) -> list[str]:
    order = list((sources or {}).get("source_order") or [])
    declared = set(((sources or {}).get("sources") or {}).keys())
    if not order:
        raise OutletsRefused("the outlet declaration has no source_order, so an outlet's "
                             "id cannot be made from its members (D-243)")
    if len(set(order)) != len(order):
        raise OutletsRefused("source_order names a source twice")
    if set(order) != declared:
        raise OutletsRefused(f"source_order ({', '.join(order)}) and the declared sources "
                             f"({', '.join(sorted(declared))}) must be the same set")
    unknown = sorted(set(held) - set(order))
    if unknown:
        raise OutletsRefused(f"the stack holds sources source_order does not name: "
                             f"{', '.join(unknown)}")
    return order


@dataclass
class Towns:
    by_name: dict = field(default_factory=dict)      # compared name -> [town codes]
    name_of: dict = field(default_factory=dict)      # town code -> the Census name
    county_by_name: dict = field(default_factory=dict)
    cousub_suffixes: tuple = ()
    county_suffixes: tuple = ()


def town_index(places: pd.DataFrame, names: dict, state_fips: str) -> Towns:
    """every town (county subdivision) and county of the state, by the name
    a person writes, read from the places table."""
    sfx = (names or {}).get("suffixes") or {}
    cousub_sfx, county_sfx = tuple(sfx.get("cousub") or ()), tuple(sfx.get("county") or ())
    if not cousub_sfx or not county_sfx:
        raise OutletsRefused("the name declaration gives no suffixes for cousub and county, "
                             "so a Census name cannot be compared with a written one")
    for col in ("authority", "code", "level", "name"):
        if col not in places.columns:
            raise OutletsRefused(f"the places table has no {col!r} column")
    here = places[(places["authority"].astype(str) == GEOID)
                  & places["code"].astype(str).str.startswith(state_fips)]
    towns = here[here["level"].astype(str) == "cousub"]
    counties = here[here["level"].astype(str) == "county"]
    if towns.empty or counties.empty:
        raise OutletsRefused(f"the places table holds no towns or counties for state "
                             f"{state_fips}")
    out = Towns(cousub_suffixes=cousub_sfx, county_suffixes=county_sfx)
    for code, name in zip(towns["code"].astype(str), towns["name"].astype(str)):
        out.by_name.setdefault(strip_suffix(name, cousub_sfx), []).append(code)
        out.name_of[code] = name
    for code, name in zip(counties["code"].astype(str), counties["name"].astype(str)):
        out.county_by_name[strip_suffix(name, county_sfx)] = code
    return out


def resolve(town: str, county: str | None, towns: Towns) -> tuple[str | None, str | None, str]:
    """(code, reason, detail): one town code, or why not."""
    cands = sorted(towns.by_name.get(strip_suffix(town, towns.cousub_suffixes), []))
    detail = town
    if county:
        cc = towns.county_by_name.get(strip_suffix(county, towns.county_suffixes))
        if cc:
            inside = [c for c in cands if c[:5] == cc]
            if cands and not inside:
                return None, "no_town_match", f"{town} (no {town} in {county})"
            cands = inside
            detail = f"{town}, {county}"
    if len(cands) == 1:
        return cands[0], None, detail
    if not cands:
        return None, "no_town_match", detail
    return None, "ambiguous_town", f"{detail} ({len(cands)} towns)"


# ── ids and merges ─────────────────────────────────────────────────────────

def _first_members(grouped: pd.DataFrame, order: list[str]) -> pd.DataFrame:
    rank = {s: i for i, s in enumerate(order)}
    g = grouped.assign(_rank=grouped["source"].map(rank),
                       _line=pd.to_numeric(grouped["source_line"], errors="coerce"),
                       _nk=grouped["name_key"].fillna(""))
    return g.sort_values(["group_id", "_rank", "_nk", "_line"]).groupby("group_id").head(1)


def outlet_ids(grouped: pd.DataFrame, order: list[str]) -> tuple[dict, set]:
    """group_id -> outlet id, and the groups whose id carries a line."""
    first = _first_members(grouped, order)
    base = {r.group_id: f"outlet:{r.source}:{(_text(r.name_key) or 'unnamed').replace(' ', '_')}"
            for r in first.itertuples(index=False)}
    used = Counter(base.values())
    ids, by_line = {}, set()
    for r in first.itertuples(index=False):
        b = base[r.group_id]
        if used[b] > 1:
            ids[r.group_id] = f"{b}:{r.source_line}"
            by_line.add(r.group_id)
        else:
            ids[r.group_id] = b
    if len(set(ids.values())) != len(ids):
        raise OutletsRefused("two outlets share an id even with their lines (D-243)")
    return ids, by_line


def _record(grouped: pd.DataFrame, source: str, name: str, where: str) -> int:
    hits = grouped.index[(grouped["source"].astype(str) == str(source))
                         & (grouped["name"].map(_text) == _text(name))]
    if len(hits) == 0:
        raise OutletsRefused(f"{where}: no {source} record is named {name!r}; a review "
                             f"no record gives refuses the run, since its words have "
                             f"changed (D-240)")
    if len(hits) > 1:
        raise OutletsRefused(f"{where}: {len(hits)} {source} records are named {name!r}; "
                             f"which one is meant is a choice, not a lookup")
    return int(hits[0])


def _review_fields(entry: dict, where: str) -> None:
    missing = [f for f in REVIEW_FIELDS if not _text(entry.get(f))]
    if missing:
        raise OutletsRefused(f"{where}: a review names its {', '.join(missing)}")


def apply_merges(grouped: pd.DataFrame, merges) -> tuple[pd.DataFrame, dict]:
    """the groups with every reviewed merge joined, and each joined group's
    review. a merge naming records already in one group refuses (it is no
    longer needed), and so does one that would put a source in a group twice."""
    out = grouped.copy()
    reviewed = {}
    for n, entry in enumerate(merges or [], start=1):
        where = f"merge {n}"
        _review_fields(entry, where)
        records = entry.get("records") or []
        if len(records) < 2:
            raise OutletsRefused(f"{where}: a merge names two or more records")
        rows = [_record(out, r.get("source"), r.get("name"), where) for r in records]
        gids = sorted(set(out.loc[rows, "group_id"]))
        if len(gids) == 1:
            raise OutletsRefused(f"{where}: its records are already one group; a review "
                                 f"the run no longer needs refuses (D-240)")
        members = out[out["group_id"].isin(gids)]
        if members["source"].duplicated().any():
            twice = sorted(members.loc[members["source"].duplicated(), "source"].unique())
            raise OutletsRefused(f"{where}: joined, the group would hold {', '.join(twice)} "
                                 f"twice; one source listing two records is two outlets (D-202)")
        out.loc[out["group_id"].isin(gids), "group_id"] = gids[0]
        reviewed[gids[0]] = entry
    return out, reviewed


# ── one outlet ─────────────────────────────────────────────────────────────

def operating_of(values, vocab: Vocabulary) -> tuple[str, str | None]:
    """(class, note) from the members' operating values."""
    held = sorted({v for v in (_text(x) for x in values) if v})
    if not held:
        return "not_given", None
    classes = set()
    for v in held:
        n = norm(v)
        if n in vocab.ceased:
            classes.add("ceased")
        elif n in vocab.operating:
            classes.add("operating")
        elif n.startswith(vocab.last_post_prefix):
            classes.add("last_post")
        else:
            classes.add("unmapped")
    if len(classes) > 1:
        return "conflicting", "; ".join(held)
    (cls,) = classes
    return cls, (None if cls == "operating" else "; ".join(held))


def place_one(members: pd.DataFrame, towns: Towns, town_fallback: str) -> dict:
    """where one outlet's sources put it: placed_by and a code, or a reason."""
    named = [(r.named_town, _text(r.named_county), r.source) for r in members.itertuples()
             if _text(r.named_town)]
    if named:
        kind, given = "named_town", named
    elif town_fallback == "office_town":
        kind = "office_town"
        given = [(r.office_town, None, r.source) for r in members.itertuples()
                 if _text(r.office_town)]
    else:
        kind, given = "named_town", []
    if not given:
        return {"reason": "no_town_given", "detail": "no source names a town"
                + ("" if town_fallback == "office_town" else ", and town_fallback is none")}
    found, missed = {}, []
    for town, county, source in given:
        code, reason, detail = resolve(str(town).strip(), county, towns)
        if code:
            found.setdefault(code, []).append((str(town).strip(), source))
        else:
            missed.append((reason, f"{detail} ({source})"))
    if len(found) > 1:
        parts = [f"{towns.name_of[c]} from {', '.join(f'{t} ({s})' for t, s in w)}"
                 for c, w in sorted(found.items())]
        return {"reason": "towns_disagree", "detail": f"{kind}: " + "; ".join(parts)}
    if not found:
        reason = "ambiguous_town" if any(r == "ambiguous_town" for r, _ in missed) else "no_town_match"
        return {"reason": reason, "detail": f"{kind}: " + "; ".join(d for _, d in missed)}
    (code, written), = found.items()
    flags = [f"town_unmatched:{d}" for _, d in missed]
    return {"code": code, "placed_by": kind,
            "town_as_written": "; ".join(sorted({t for t, _ in written})),
            "town_from": "; ".join(sorted({s for _, s in written})), "flags": flags}


def _records_of(members: pd.DataFrame) -> str:
    return "; ".join(f"{r.source}:{r.source_line}" for r in members.itertuples())


@dataclass
class Prepared:
    outlets: pd.DataFrame
    listed: list = field(default_factory=list)


def prepare(grouped: pd.DataFrame, places: pd.DataFrame, sources: dict, names: dict,
            town_fallback: str, ceased_outlets: str, state_fips: str,
            reviews: dict | None = None) -> Prepared:
    if town_fallback not in TOWN_FALLBACKS:
        raise OutletsRefused(f"town_fallback is {town_fallback!r}; it is one of "
                             f"{', '.join(TOWN_FALLBACKS)}")
    if ceased_outlets not in CEASED_CHOICES:
        raise OutletsRefused(f"ceased_outlets is {ceased_outlets!r}; it is one of "
                             f"{', '.join(CEASED_CHOICES)}")
    need = ("source", "source_line", "name", "name_key", "group_id", "named_town",
            "named_county", "office_town", "operating_raw")
    absent = [c for c in need if c not in grouped.columns]
    if absent:
        raise OutletsRefused(f"the grouped stack has no {', '.join(absent)}")
    vocab = read_vocabulary(sources)
    order = read_source_order(sources, grouped["source"].astype(str).unique())
    towns = town_index(places, names, state_fips)
    reviews = reviews or {}
    grouped = grouped.reset_index(drop=True)
    grouped, merged = apply_merges(grouped, reviews.get("merges"))
    ids, by_line = outlet_ids(grouped, order)

    town_reviews = {}
    for n, entry in enumerate(reviews.get("towns") or [], start=1):
        where = f"town review {n}"
        _review_fields(entry, where)
        code = _text(entry.get("town_code"))
        if code not in towns.name_of:
            raise OutletsRefused(f"{where}: {code!r} is not a town of state {state_fips} "
                                 f"in the places table")
        gid = grouped.loc[_record(grouped, entry.get("source"), entry.get("name"), where),
                          "group_id"]
        if gid in town_reviews:
            raise OutletsRefused(f"{where}: its outlet already has a town review")
        town_reviews[gid] = (where, code, entry)

    rows, listed = [], []
    for gid in sorted(ids, key=lambda g: ids[g]):
        members = grouped[grouped["group_id"] == gid]
        first = _first_members(members, order).iloc[0]
        fid, name = ids[gid], _text(first["name"])
        op, op_note = operating_of(members["operating_raw"], vocab)
        records = _records_of(members)
        flags = []
        if gid in by_line:
            flags.append("id_by_line")
        review = merged.get(gid)
        if review is not None:
            flags.append("merged_by_review")
        if op == "ceased" and ceased_outlets == "listed":
            if gid in town_reviews:
                raise OutletsRefused(f"{town_reviews[gid][0]}: its outlet is listed as ceased, "
                                     f"so a town review cannot place it")
            listed.append({"feature_id": fid, "name": name, "reason": "ceased",
                           "detail": op_note, "records": records})
            continue
        placed = place_one(members, towns, town_fallback)
        if gid in town_reviews:
            where, code, entry = town_reviews[gid]
            if "code" in placed:
                raise OutletsRefused(f"{where}: the run places this outlet on its own; a "
                                     f"review the run no longer needs refuses (D-240)")
            placed = {"code": code, "placed_by": "reviewed",
                      "town_as_written": _text(entry.get("name")),
                      "town_from": _text(entry.get("source")),
                      "flags": [f"review_settled:{placed['reason']}"]}
            review = entry
        if "code" not in placed:
            listed.append({"feature_id": fid, "name": name, "reason": placed["reason"],
                           "detail": placed["detail"], "records": records})
            continue
        if op in ("ceased", "last_post", "unmapped", "conflicting"):
            flags.append(f"operating:{op}")
        flags.extend(placed["flags"])
        if placed["placed_by"] == "office_town":
            flags.append("office_town_not_named")
        code = placed["code"]
        rows.append({
            "feature_id": fid, "name": name, "town_code": code,
            "town_name": towns.name_of[code], "county_code": code[:5],
            "placed_by": placed["placed_by"], "town_as_written": placed["town_as_written"],
            "town_from": placed["town_from"], "operating": op, "operating_note": op_note,
            "sources": "; ".join(sorted(set(members["source"].astype(str)))),
            "records": records,
            "review_evidence": _text((review or {}).get("evidence")),
            "review_read_on": _text((review or {}).get("read_on")),
            "review_read_by": _text((review or {}).get("read_by")),
            "flags": ";".join(flags) or None})
    out = pd.DataFrame(rows, columns=COLUMNS)
    if out["feature_id"].duplicated().any():
        raise OutletsRefused("one outlet id twice")
    return Prepared(outlets=out, listed=listed)


def output_metadata(p: Prepared) -> dict:
    """what the receipt says: its key (KEYS-1), how each outlet was placed,
    and every outlet not placed, by name, with its reason."""
    return {"data_category": "tabular", "crs": None, "row_count": len(p.outlets),
            "variables": COLUMNS, "id_fields": KEY, "spatial_unit": SPATIAL_UNIT,
            "placed_by": dict(Counter(p.outlets["placed_by"])),
            "listed_reasons": dict(Counter(r["reason"] for r in p.listed)),
            "listed_outlets": p.listed}


def summary(p: Prepared) -> list[str]:
    return [f"{len(p.outlets)} outlet(s) placed: {dict(Counter(p.outlets['placed_by']))}",
            f"{len(p.listed)} listed: {dict(Counter(r['reason'] for r in p.listed))}",
            f"operating: {dict(Counter(p.outlets['operating']))}"]


def main():
    try:
        from canopy.pr_io import (parse_primitive_args, get_input, get_param, require_param,
                                  WarningsCollector, primitive_success, primitive_failure,
                                  primitive_error_handling)
    except ImportError:
        from pr_io import (parse_primitive_args, get_input, get_param, require_param,
                           WarningsCollector, primitive_success, primitive_failure,
                           primitive_error_handling)

    def read(path):
        return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path, dtype=str)

    args = parse_primitive_args()
    w = WarningsCollector("prepare_news_outlets")
    with primitive_error_handling(w):
        i, p = args["inputs"], args["params"]
        try:
            prepared = prepare(
                pd.read_csv(get_input(i, "grouped"), dtype=str), read(get_input(i, "places")),
                require_param(p, "sources"), require_param(p, "names"),
                str(require_param(p, "town_fallback")), str(require_param(p, "ceased_outlets")),
                str(require_param(p, "state_fips")).zfill(2), get_param(p, "reviews"))
        except OutletsRefused as e:
            primitive_failure("Outlets refused", str(e))
        for line in summary(prepared):
            w.info(line)
        if prepared.listed:
            w.warn(f"{len(prepared.listed)} outlet(s) not placed, each listed in the receipt "
                   f"with its reason")
        prepared.outlets.to_csv(args["output"], index=False)
        primitive_success(output_metadata(prepared), w)


if __name__ == "__main__":
    main()
