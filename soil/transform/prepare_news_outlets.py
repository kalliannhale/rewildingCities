"""
soil/transform/prepare_news_outlets.py  |  rewildingCities

prepare_news_outlets ~ one row per local news outlet, placed in a town (or,
for an outlet a listing calls statewide, in the state) by the place's code,
never by a point (Sprint 06, step 3, the fifth carrier)

reads the grouped outlet stack (group_outlet_records) and the places table,
and writes each outlet once, where its sources put it. what is placed and
why is the outlet_carriers method's (D-212); in short, in the order the run
asks it of each outlet:

  ~ one outlet per group (D-243). its id is made from its members, never
    from row order: outlet:<source>:<name key> of its first member by the
    declaration's source_order. groups that would share an id each add
    their first member's line, flagged id_by_line
  ~ is it closed? a source's operating status is read through the
    declaration's operating_vocabulary (D-245), and a status a source
    writes in another column through operating_elsewhere (D-251): the
    ecosystem file writes CLOSED in its Medium. what a ceased outlet
    becomes is the method's choice ceased_outlets
  ~ is it local news? each source is declared a local_news_list (a person
    chose every outlet on it as local news) or a media_database (every
    outlet with an address) in source_kinds (D-247). an outlet any list
    holds is local news by that list's say. an outlet only a database
    holds is judged by its database type, read through
    media_database_types: every type declared, an undeclared one refusing
    the run, a placeholder declared unknown. the method's choice
    database_alone says which classes count (D-248). a program never
    counts, under any choice: it airs on a station (a rule). the medium is
    judged before the town, so an outlet listed for its medium never needs
    a town
  ~ where is it? a town a source names places the outlet (D-241); a name
    in statewide_names places it in the state only, unless a town is also
    named, which wins (D-249). when no source names either, the choice
    town_fallback says whether the publisher's office town may (D-242):
    never its street address, and never against a named town. an office
    address that two or more outlets give is a publisher's office: an
    outlet placed there is flagged office_shared, and listed under
    office_town_unshared (D-250). an address is its street as normalized
    and its ZIP as five digits, leading zeros a spreadsheet dropped given
    back
  ~ towns are matched by name after the declared Census suffixes come off,
    lowercase, periods and apostrophes dropped, a hyphen read as a space;
    nothing else forgiven (D-244). two towns, none, two matches or none
    given are listed, never placed
  ~ a review (seeds/crosswalks/outlets/outlet_reviews.yml) is a person's
    reading, keyed by source and name as written: a merge joins groups, a
    town names the code a person read for an outlet the run would list for
    its town. it refuses when no record gives it, when the run no longer
    needs it, and when the outlet is listed as ceased or for its medium
    (D-240's rule). a merge may hold one source twice only when it says,
    in words, what the person read the records as (editions, D-255): the
    grouping never does. an office read is a person's reading of an outlet
    placed by its office town alone: keep it there, move it to the town or
    the state the person read, or list it, with the reason in words
    (D-256). an outlet placed by its office town with no read is flagged
    office_town_unread

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  grouped (outlet_groups), places (places)
Params:
  sources         required: the outlet declaration ($crosswalks.outlet_sources)
  names           required: the Census name suffixes ($crosswalks.census_name_suffixes)
  reviews         optional: reviewed records ($crosswalks.outlet_reviews)
  town_fallback   required: none | office_town | office_town_unshared
  ceased_outlets  required: listed | counted
  database_alone  required: none | newspapers | print_and_web
  state_fips      required: two digits
Output: the outlets, csv, one row per placed outlet, keyed by feature_id;
        every outlet not placed is listed in the receipt with its reason. ~

an office address is compared by group_outlet_records.office_key, its one
home (D-254 reads it there too). ~
"""

from __future__ import annotations

import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from group_outlet_records import office_key, zip5  # noqa: E402  the one home (D-250)

GEOID = "us_census_geoid"
KEY = ["feature_id"]
SPATIAL_UNIT = "news_outlet"
COLUMNS = ["feature_id", "name", "scope", "town_code", "town_name", "county_code",
           "placed_by", "town_as_written", "town_from", "vouched_by", "database_class",
           "medium_as_written", "operating", "operating_note", "sources", "records",
           "review_evidence", "review_read_on", "review_read_by", "flags"]
TOWN_FALLBACKS = ("none", "office_town", "office_town_unshared")
CEASED_CHOICES = ("listed", "counted")
DATABASE_ALONE = ("none", "newspapers", "print_and_web")
KINDS = ("local_news_list", "media_database")
STATUS_CLASSES = ("operating", "ceased")
REVIEWABLE = ("towns_disagree", "no_town_match", "ambiguous_town", "no_town_given",
              "office_shared")
MEDIUM_REASONS = ("medium_not_counted", "medium_conflict", "medium_unknown")
REVIEW_FIELDS = ("evidence", "read_on", "read_by")
OFFICE_VERDICTS = ("keep", "town", "state", "list")


class OutletsRefused(ValueError):
    """an outlet table the declarations refuse, with why."""


def _text(x) -> str | None:
    """a value as text, or None when it is missing in any of pandas' ways
    (None, NaN, NA). judged one value at a time: in pandas 3, Series.map
    over a str column turns a returned None back into NaN, so a missing
    value is never read from a mapped Series by `is None`."""
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
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


def read_kinds(sources: dict, order: list[str]) -> dict:
    """each source's kind: what being on it says about an outlet (D-247)."""
    kinds = (sources or {}).get("source_kinds")
    if not isinstance(kinds, dict):
        raise OutletsRefused("the outlet declaration has no source_kinds, so what being on "
                             "a listing says about an outlet is unknown (D-247)")
    if set(kinds) != set(order):
        raise OutletsRefused(f"source_kinds ({', '.join(sorted(kinds))}) and the declared "
                             f"sources ({', '.join(sorted(order))}) must be the same set")
    bad = sorted(f"{s}: {k}" for s, k in kinds.items() if k not in KINDS)
    if bad:
        raise OutletsRefused(f"a source's kind is one of {', '.join(KINDS)}; read "
                             f"{', '.join(bad)}")
    return dict(kinds)


@dataclass(frozen=True)
class DatabaseTypes:
    read_for: frozenset
    values: dict          # a type as written, trimmed -> class id
    classes: dict         # class id -> its declaration


def read_database_types(sources: dict, kinds: dict) -> DatabaseTypes:
    """the media databases' types, every one declared (D-247, D-248). a class
    counts under the database_alone options it names; a program and an
    unknown class name none, and saying otherwise refuses."""
    databases = {s for s, k in kinds.items() if k == "media_database"}
    d = (sources or {}).get("media_database_types")
    if not databases:
        return DatabaseTypes(frozenset(), {}, {})
    if not isinstance(d, dict):
        raise OutletsRefused("a source is a media_database, so the outlet declaration "
                             "needs media_database_types (D-247)")
    read_for = set(d.get("read_for") or [])
    if read_for != databases:
        raise OutletsRefused(f"media_database_types reads for {', '.join(sorted(read_for))}; "
                             f"the media databases are {', '.join(sorted(databases))}")
    classes = d.get("classes") or {}
    values = {str(k).strip(): str(v) for k, v in (d.get("values") or {}).items()}
    if not classes or not values:
        raise OutletsRefused("media_database_types needs classes and values (D-247)")
    undeclared = sorted({c for c in values.values() if c not in classes})
    if undeclared:
        raise OutletsRefused(f"media_database_types maps a type to an undeclared class: "
                             f"{', '.join(undeclared)}")
    counting = set(DATABASE_ALONE) - {"none"}
    for cid, c in classes.items():
        c = c or {}
        under = list(c.get("counted_under") or [])
        wrong = sorted(set(under) - counting)
        if wrong:
            raise OutletsRefused(f"class {cid} counts under {', '.join(wrong)}; a class counts "
                                 f"under {', '.join(sorted(counting))} or none of them")
        if c.get("program") and under:
            raise OutletsRefused(f"class {cid} is a program and names options it counts "
                                 f"under; a program airs on a station, so counting both "
                                 f"counts one transmitter twice (D-248)")
        if c.get("unknown") and under:
            raise OutletsRefused(f"class {cid} is unknown and names options it counts under; "
                                 f"an unknown type is never evidence of a medium (D-247)")
    return DatabaseTypes(frozenset(read_for), values, dict(classes))


def read_statewide(sources: dict) -> frozenset:
    names = (sources or {}).get("statewide_names")
    if names is None:
        raise OutletsRefused("the outlet declaration has no statewide_names (an empty list "
                             "says none), so a listing's statewide outlet cannot be told "
                             "from a missing town (D-249)")
    return frozenset(norm(x) for x in names)


def read_operating_elsewhere(sources: dict, order: list[str], columns) -> list:
    """(source, column, class, words): statuses a source writes outside its
    operating column (D-251)."""
    d = (sources or {}).get("operating_elsewhere") or {}
    out = []
    for src, cols in d.items():
        if src not in order:
            raise OutletsRefused(f"operating_elsewhere names {src}, which is not a source")
        for col, by_class in (cols or {}).items():
            if col not in columns:
                raise OutletsRefused(f"operating_elsewhere reads {src}'s {col}, which the "
                                     f"grouped stack does not hold")
            for cls, words in (by_class or {}).items():
                if cls not in STATUS_CLASSES:
                    raise OutletsRefused(f"operating_elsewhere: {cls} is not one of "
                                         f"{', '.join(STATUS_CLASSES)}")
                for w in words or []:
                    out.append((src, col, cls, norm(w)))
    return out


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
    first = ([_text(x) is None for x in grouped["same_record_as"]]
             if "same_record_as" in grouped.columns else [True] * len(grouped))
    hits = grouped.index[(grouped["source"].astype(str) == str(source))
                         & (pd.Series([_text(x) for x in grouped["name"]], index=grouped.index)
                            == _text(name))
                         & pd.Series(first, index=grouped.index)]
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


def _held_twice(members: pd.DataFrame) -> list:
    """the sources a group holds as two or more records, a record written
    twice counted once (D-254)."""
    if "same_record_as" in members.columns:
        members = members[[_text(x) is None for x in members["same_record_as"]]]
    s = members["source"].astype(str)
    return sorted(s[s.duplicated()].unique())


def apply_merges(grouped: pd.DataFrame, merges) -> tuple[pd.DataFrame, dict]:
    """the groups with every reviewed merge joined, and each joined group's
    review. a merge naming records already in one group refuses (it is no
    longer needed). one that would put a source in a group twice refuses
    unless it says editions: what the person read the records as (D-255);
    one that says editions where no source is twice refuses too."""
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
        twice = _held_twice(members)
        editions = _text(entry.get("editions"))
        if twice and not editions:
            raise OutletsRefused(f"{where}: joined, the group would hold {', '.join(twice)} "
                                 f"twice; one source listing two records is two outlets "
                                 f"(D-202) unless a person read them as one outlet's "
                                 f"editions and the merge says so in editions (D-255)")
        if editions and not twice:
            raise OutletsRefused(f"{where}: it says editions, but joined, the group holds "
                                 f"no source twice; editions would say what is not there")
        out.loc[out["group_id"].isin(gids), "group_id"] = gids[0]
        reviewed[gids[0]] = entry
    return out, reviewed


# ── one outlet ─────────────────────────────────────────────────────────────

def operating_of(values, vocab: Vocabulary, written=()) -> tuple[str, str | None]:
    """(class, note) from the members' operating values, and from statuses
    written elsewhere, given as (class, words) pairs (D-251)."""
    held = sorted({v for v in (_text(x) for x in values) if v})
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
    words = list(held)
    for cls, w in written:
        classes.add(cls)
        words.append(w)
    if not classes:
        return "not_given", None
    if len(classes) > 1:
        return "conflicting", "; ".join(words)
    (cls,) = classes
    return cls, (None if cls == "operating" else "; ".join(words))


def written_statuses(members: pd.DataFrame, elsewhere: list) -> list:
    """the statuses members write outside their operating column."""
    out = []
    for r in members.to_dict("records"):
        for src, col, cls, word in elsewhere:
            v = _text(r.get(col))
            if r["source"] == src and v and norm(v) == word:
                out.append((cls, f"{v} ({src} {col})"))
    return out


def medium_of(members: pd.DataFrame, kinds: dict, types: DatabaseTypes,
              database_alone: str) -> dict:
    """whether an outlet is local news, and on whose say (D-247, D-248).
    {vouched_by, database_class, medium_as_written} and, when it is not
    counted, a reason and its detail."""
    vouched = sorted({s for s in members["source"].astype(str) if kinds[s] == "local_news_list"})
    found = []                       # (class id, the type as written)
    written = []
    for r in members.to_dict("records"):
        raw = _text(r.get("medium_raw"))
        if raw:
            written.append(f"{r['source']}: {raw}")
        if r["source"] not in types.read_for:
            continue
        cid = types.values.get(raw if raw is not None else "")
        if raw is None:
            cid = None
        elif cid is None:
            raise OutletsRefused(f"{r['source']} line {r['source_line']} gives the type "
                                 f"{raw!r}, which media_database_types does not declare; "
                                 f"every type is declared before it is read (D-247)")
        found.append((cid, raw))
    database_class = "; ".join(sorted({c for c, _ in found if c})) or None
    out = {"vouched_by": "; ".join(vouched) or None, "database_class": database_class,
           "medium_as_written": "; ".join(sorted(set(written))) or None}
    if vouched:
        return out
    known = sorted({c for c, _ in found if c and not (types.classes[c] or {}).get("unknown")})
    if not known:
        as_written = sorted({w for _, w in found if w}) or ["no type"]
        return {**out, "reason": "medium_unknown",
                "detail": f"no list holds it and its database type says nothing: "
                          f"{', '.join(as_written)}"}
    counted = [c for c in known
               if database_alone in ((types.classes[c] or {}).get("counted_under") or [])]
    if len(counted) == len(known):
        return out
    reason = "medium_conflict" if counted else "medium_not_counted"
    return {**out, "reason": reason,
            "detail": f"database_alone is {database_alone}; no list holds it; its database "
                      f"types: {', '.join(known)}"}


def _zip5(z) -> str | None:
    """a ZIP as five digits: group_outlet_records.zip5, its one home (D-250)."""
    return zip5(z)


def office_keys(members: pd.DataFrame) -> set:
    """an outlet's office addresses, compared: street as normalized, ZIP5,
    through group_outlet_records.office_key (D-250)."""
    keys = set()
    for r in members.to_dict("records"):
        k = office_key(r.get("address_raw"), r.get("zip_raw"))
        if k:
            keys.add(k)
    return keys


def place_one(members: pd.DataFrame, towns: Towns, town_fallback: str,
              statewide: frozenset) -> dict:
    """where one outlet's sources put it: a scope, placed_by and a code, or a
    reason."""
    named, state_named = [], []
    for r in members.itertuples():
        t = _text(r.named_town)
        if not t:
            continue
        if norm(t) in statewide:
            state_named.append((t, r.source))
        else:
            named.append((t, _text(r.named_county), r.source))
    if not named and state_named:
        return {"scope": "state", "placed_by": "named_state",
                "town_as_written": "; ".join(sorted({t for t, _ in state_named})),
                "town_from": "; ".join(sorted({s for _, s in state_named})), "flags": []}
    if named:
        kind, given = "named_town", named
    elif town_fallback in ("office_town", "office_town_unshared"):
        kind = "office_town"
        given = [(r.office_town, None, r.source) for r in members.itertuples()
                 if _text(r.office_town)]
    else:
        kind, given = "named_town", []
    if not given:
        return {"reason": "no_town_given", "detail": "no source names a town"
                + ("" if town_fallback != "none" else ", and town_fallback is none")}
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
    flags += [f"statewide_also:{s}" for _, s in state_named]
    return {"scope": "town", "code": code, "placed_by": kind,
            "town_as_written": "; ".join(sorted({t for t, _ in written})),
            "town_from": "; ".join(sorted({s for _, s in written})), "flags": flags}


def _records_of(members: pd.DataFrame) -> str:
    return "; ".join(f"{r.source}:{r.source_line}" for r in members.itertuples())


@dataclass
class Prepared:
    outlets: pd.DataFrame
    listed: list = field(default_factory=list)
    editions: list = field(default_factory=list)
    office_reads: dict = field(default_factory=dict)


def prepare(grouped: pd.DataFrame, places: pd.DataFrame, sources: dict, names: dict,
            town_fallback: str, ceased_outlets: str, database_alone: str, state_fips: str,
            reviews: dict | None = None) -> Prepared:
    if town_fallback not in TOWN_FALLBACKS:
        raise OutletsRefused(f"town_fallback is {town_fallback!r}; it is one of "
                             f"{', '.join(TOWN_FALLBACKS)}")
    if ceased_outlets not in CEASED_CHOICES:
        raise OutletsRefused(f"ceased_outlets is {ceased_outlets!r}; it is one of "
                             f"{', '.join(CEASED_CHOICES)}")
    if database_alone not in DATABASE_ALONE:
        raise OutletsRefused(f"database_alone is {database_alone!r}; it is one of "
                             f"{', '.join(DATABASE_ALONE)}")
    need = ("source", "source_line", "name", "name_key", "group_id", "named_town",
            "named_county", "office_town", "operating_raw", "medium_raw", "address_raw",
            "zip_raw")
    absent = [c for c in need if c not in grouped.columns]
    if absent:
        raise OutletsRefused(f"the grouped stack has no {', '.join(absent)}")
    vocab = read_vocabulary(sources)
    order = read_source_order(sources, grouped["source"].astype(str).unique())
    kinds = read_kinds(sources, order)
    types = read_database_types(sources, kinds)
    statewide = read_statewide(sources)
    elsewhere = read_operating_elsewhere(sources, order, grouped.columns)
    towns = town_index(places, names, state_fips)
    reviews = reviews or {}
    grouped = grouped.reset_index(drop=True)
    grouped, merged = apply_merges(grouped, reviews.get("merges"))
    ids, by_line = outlet_ids(grouped, order)

    # an office address two or more outlets give is a publisher's (D-250),
    # counted over every outlet, whatever becomes of it
    keys_of = {gid: office_keys(grouped[grouped["group_id"] == gid]) for gid in ids}
    holders: dict = {}
    for gid, keys in keys_of.items():
        for k in keys:
            holders.setdefault(k, set()).add(gid)

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

    office_reads = {}
    for n, entry in enumerate(reviews.get("office_reads") or [], start=1):
        where = f"office read {n}"
        _review_fields(entry, where)
        verdict = _text(entry.get("verdict"))
        if verdict not in OFFICE_VERDICTS:
            raise OutletsRefused(f"{where}: verdict is {verdict!r}; it is one of "
                                 f"{', '.join(OFFICE_VERDICTS)} (D-256)")
        code = _text(entry.get("town_code"))
        if verdict == "town" and code not in towns.name_of:
            raise OutletsRefused(f"{where}: {code!r} is not a town of state {state_fips} "
                                 f"in the places table")
        if verdict != "town" and code:
            raise OutletsRefused(f"{where}: only a town verdict names a town_code")
        if verdict == "list" and not _text(entry.get("reason")):
            raise OutletsRefused(f"{where}: a list verdict says its reason in words")
        gid = grouped.loc[_record(grouped, entry.get("source"), entry.get("name"), where),
                          "group_id"]
        if gid in office_reads or gid in town_reviews:
            raise OutletsRefused(f"{where}: its outlet already has a reading of where it is")
        office_reads[gid] = (where, verdict, code, entry)
    reads_used = set()

    rows, listed = [], []
    for gid in sorted(ids, key=lambda g: ids[g]):
        members = grouped[grouped["group_id"] == gid]
        first = _first_members(members, order).iloc[0]
        fid, name = ids[gid], _text(first["name"])
        op, op_note = operating_of(members["operating_raw"], vocab,
                                   written_statuses(members, elsewhere))
        records = _records_of(members)
        flags = []
        if gid in by_line:
            flags.append("id_by_line")
        review = merged.get(gid)
        if review is not None:
            flags.append("merged_by_review")
            if _text(review.get("editions")):
                flags.append("editions_by_review")

        def listing(reason, detail):
            return {"feature_id": fid, "name": name, "reason": reason, "detail": detail,
                    "records": records}

        if op == "ceased" and ceased_outlets == "listed":
            if gid in town_reviews:
                raise OutletsRefused(f"{town_reviews[gid][0]}: its outlet is listed as ceased, "
                                     f"so a town review cannot place it")
            listed.append(listing("ceased", op_note))
            continue
        medium = medium_of(members, kinds, types, database_alone)
        if "reason" in medium:
            if gid in town_reviews:
                raise OutletsRefused(f"{town_reviews[gid][0]}: its outlet is listed for its "
                                     f"medium ({medium['reason']}), so a town review cannot "
                                     f"place it; the medium is judged before the town (D-248)")
            listed.append(listing(medium["reason"], medium["detail"]))
            continue
        placed = place_one(members, towns, town_fallback, statewide)
        if placed.get("placed_by") == "office_town":
            sharers = set().union(*(holders[k] for k in keys_of[gid])) if keys_of[gid] else set()
            if len(sharers) > 1:
                others = sorted(_text(grouped.loc[grouped["group_id"] == g, "name"].iloc[0])
                                or ids[g] for g in sharers - {gid})
                if town_fallback == "office_town_unshared":
                    placed = {"reason": "office_shared",
                              "detail": f"its office address is given by {len(sharers)} "
                                        f"outlets, so it is a publisher's office: with "
                                        f"{', '.join(others[:5])}"
                                        + (f" and {len(others) - 5} more" if len(others) > 5 else "")}
                else:
                    placed["flags"] = placed["flags"] + [f"office_shared:{len(sharers)}"]
        if gid in office_reads:
            where, verdict, code, entry = office_reads[gid]
            if placed.get("placed_by") != "office_town":
                raise OutletsRefused(f"{where}: the run does not place this outlet by its "
                                     f"office town ({placed.get('placed_by') or placed.get('reason')}); "
                                     f"a review the run no longer needs refuses (D-240, D-256)")
            reads_used.add(gid)
            review = entry
            if verdict == "list":
                listed.append(listing("office_read_listed", _text(entry.get("reason"))))
                continue
            if verdict == "town":
                placed = {"scope": "town", "code": code, "placed_by": "reviewed",
                          "town_as_written": placed["town_as_written"],
                          "town_from": placed["town_from"],
                          "flags": ["office_read:town"]}
            elif verdict == "state":
                placed = {"scope": "state", "placed_by": "reviewed",
                          "town_as_written": placed["town_as_written"],
                          "town_from": placed["town_from"],
                          "flags": ["office_read:state", "placed_in_state_only"]}
            else:
                placed["flags"] = placed["flags"] + ["office_read:keep"]
        if gid in town_reviews:
            where, code, entry = town_reviews[gid]
            if "code" in placed or placed.get("scope") == "state":
                raise OutletsRefused(f"{where}: the run places this outlet on its own; a "
                                     f"review the run no longer needs refuses (D-240)")
            placed = {"scope": "town", "code": code, "placed_by": "reviewed",
                      "town_as_written": _text(entry.get("name")),
                      "town_from": _text(entry.get("source")),
                      "flags": [f"review_settled:{placed['reason']}"]}
            review = entry
        if "reason" in placed:
            listed.append(listing(placed["reason"], placed["detail"]))
            continue
        if op in ("ceased", "last_post", "unmapped", "conflicting"):
            flags.append(f"operating:{op}")
        flags.extend(placed["flags"])
        if placed["placed_by"] == "office_town":
            flags.append("office_town_not_named")
            if gid not in reads_used:
                flags.append("office_town_unread")
        if placed["placed_by"] == "named_state":
            flags.append("placed_in_state_only")
        code = placed.get("code")
        rows.append({
            "feature_id": fid, "name": name, "scope": placed["scope"], "town_code": code,
            "town_name": towns.name_of[code] if code else None,
            "county_code": code[:5] if code else None,
            "placed_by": placed["placed_by"], "town_as_written": placed["town_as_written"],
            "town_from": placed["town_from"], "vouched_by": medium["vouched_by"],
            "database_class": medium["database_class"],
            "medium_as_written": medium["medium_as_written"],
            "operating": op, "operating_note": op_note,
            "sources": "; ".join(sorted(set(members["source"].astype(str)))),
            "records": records,
            "review_evidence": _text((review or {}).get("evidence")),
            "review_read_on": _text((review or {}).get("read_on")),
            "review_read_by": _text((review or {}).get("read_by")),
            "flags": ";".join(flags) or None})
    unused = sorted(office_reads[g][0] for g in set(office_reads) - reads_used)
    if unused:
        raise OutletsRefused(f"{', '.join(unused)}: the run lists the outlet before asking "
                             f"where it is (ceased, or for its medium); a review the run "
                             f"no longer needs refuses (D-240, D-256)")
    out = pd.DataFrame(rows, columns=COLUMNS)
    if out["feature_id"].duplicated().any():
        raise OutletsRefused("one outlet id twice")
    editions = [{"feature_id": ids[g], "editions": _text(e.get("editions")),
                 "records": _records_of(grouped[grouped["group_id"] == g])}
                for g, e in sorted(merged.items(), key=lambda kv: ids[kv[0]])
                if _text(e.get("editions"))]
    reads = dict(Counter(office_reads[g][1] for g in reads_used))
    return Prepared(outlets=out, listed=listed, editions=editions, office_reads=reads)


def _tally(series) -> dict:
    return dict(Counter(x for x in series if isinstance(x, str) and x))


def output_metadata(p: Prepared) -> dict:
    """what the receipt says: its key (KEYS-1), how each outlet was placed
    and on whose say it is local news, and every outlet not placed, by name,
    with its reason."""
    o = p.outlets
    alone = o[o["vouched_by"].isna()]
    return {"data_category": "tabular", "crs": None, "row_count": len(o),
            "variables": COLUMNS, "id_fields": KEY, "spatial_unit": SPATIAL_UNIT,
            "placed_by": _tally(o["placed_by"]), "scope": _tally(o["scope"]),
            "vouched_by_a_list": int(o["vouched_by"].notna().sum()),
            "database_alone": int(len(alone)),
            "database_alone_classes": _tally(alone["database_class"]),
            "listed_reasons": dict(Counter(r["reason"] for r in p.listed)),
            "edition_merges": p.editions,
            "office_reads": p.office_reads,
            "office_town_unread": int(o["flags"].fillna("").str.contains("office_town_unread").sum()),
            "listed_outlets": p.listed}


def summary(p: Prepared) -> list[str]:
    o = p.outlets
    return [f"{len(o)} outlet(s) placed: {_tally(o['placed_by'])}",
            f"on a list's say {int(o['vouched_by'].notna().sum())}, "
            f"a database's alone {int(o['vouched_by'].isna().sum())}",
            f"{len(p.listed)} listed: {dict(Counter(r['reason'] for r in p.listed))}",
            f"operating: {_tally(o['operating'])}",
            f"office reads: {p.office_reads}; placed by office town, unread: "
            f"{int(o['flags'].fillna('').str.contains('office_town_unread').sum())}",
            f"edition merges: {len(p.editions)}"]


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
                str(require_param(p, "database_alone")),
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
