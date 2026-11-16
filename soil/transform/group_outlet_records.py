"""
soil/transform/group_outlet_records.py  |  rewildingCities

group_outlet_records ~ which stacked records may be the same outlet, and
where their sources disagree

the second step of reconciling Maine's outlets (Sprint 06, step 8). it reads
the stack from stack_outlet_sources and groups records that share an exact
key, then lists every field on which a group's sources disagree. it merges
nothing: each record keeps its own row, now carrying a group.

two keys, both exact after normalizing, never fuzzy:

  ~ url    scheme, www. and a trailing slash dropped, lowercased. the path is
           kept, because one domain can host several outlets
           (sunjournal.com/weeklies/advertiser-democrat is not sunjournal.com)
  ~ name   lowercased, & read as and, a trailing parenthetical dropped, a
           "the" dropped from the front or, written inverted, from the end
           (Cision's "Star-Herald, The" is the Star-Herald, D-253),
           punctuation removed, spaces collapsed

a missed match costs a duplicate someone can see; a wrong match attributes
one outlet's owner to another. so a key never joins two records from the
same source: one source listing two outlets under one key is two outlets.
and a key value one source uses twice joins nothing at all, for anyone:
which of its two records another source's record belongs with would
otherwise be decided by row order, a silent choice. such a value is named
in match_note on every record that holds it. a join refused because two
keys together would put one source in a group twice is noted the same way
(D-202).

one record written twice is not two outlets (D-254, a rule). records of one
source alike in name key, url key and office address (street normalized,
ZIP as five digits, office_key) are one record: they join each other first,
their key held once, and every row but the first by line says
same_record_as. a source's same name with another url or address stays two
outlets. which identical row is named first decides nothing, since they are
alike in everything grouping reads. ~

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  stack   the stack from stack_outlet_sources
Params:  none
Output:  the stack with url_key, name_key, group_id, match_basis,
         match_note and same_record_as, csv, keyed by (source, source_line)

disagreements() is its own primitive, list_outlet_disagreements, since a
step writes one output. run by hand for a look with --stack, --out and
--disagreements. ~
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd

# like is compared only with like: an office address never with a named town
KEY = ["source", "source_line"]
SPATIAL_UNIT = "outlet_record"

COMPARED = ("frequency", "office_town", "office_county", "named_town", "named_county")


def _text(x) -> str | None:
    """a value as text, or None when it is missing in any of pandas' ways,
    judged one value at a time (pandas 3 reads a missing str as NaN)."""
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
    text = str(x).strip()
    return text or None


def url_key(url) -> str | None:
    text = _text(url)
    if not text:
        return None
    text = text.lower()
    text = re.sub(r"^[a-z]+://", "", text)
    text = re.sub(r"^www\.", "", text)
    text = text.split("#")[0].rstrip("/")
    return text or None


def name_key(name) -> str | None:
    text = _text(name)
    if not text:
        return None
    text = text.lower().replace("&", " and ")
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text)
    text = re.sub(r"\s*,\s*the\s*$", "", text)
    text = re.sub(r"^the\s+", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def address_norm(text) -> str | None:
    """a street as compared: lowercase, periods and apostrophes dropped, a
    hyphen read as a space, spaces collapsed. nothing else (D-250)."""
    t = _text(text)
    if not t:
        return None
    t = re.sub(r"[.'\u2019]", "", t.lower()).replace("-", " ")
    return re.sub(r"\s+", " ", t).strip() or None


def zip5(z) -> str | None:
    """a ZIP as five digits, from its part before any hyphen. three or four
    digits are a ZIP a spreadsheet read as a number, its leading zeros
    dropped (Maine's 04282 written 4282), and get them back, since no US
    ZIP is shorter (a rule, D-250). nine digits are ZIP+4 written whole.
    anything else gives no key."""
    t = _text(z)
    if not t:
        return None
    head = t.split("-")[0].strip()
    if not head.isdigit():
        return None
    if len(head) == 9:
        return head[:5]
    if 3 <= len(head) <= 5:
        return head.zfill(5)
    return None


def office_key(address, zip_code) -> tuple | None:
    """an office address as compared, street and ZIP5, or None. the one home
    of the comparison: prepare_news_outlets reads it from here (D-250)."""
    a, z = address_norm(address), zip5(zip_code)
    return (a, z) if a and z else None


def _identity(row) -> tuple | None:
    """what makes two of one source's rows one record: name key, url key and
    office address, all given (D-254)."""
    parts = (_text(row.get("name_key")), _text(row.get("url_key")),
             office_key(row.get("address_raw"), row.get("zip_raw")))
    return parts if all(parts) else None


def _line_order(line):
    try:
        return (0, int(str(line)))
    except ValueError:
        return (1, str(line))


class _Groups:
    """union-find over record indices that keeps each group's sources, so a
    join that would put one source in a group twice can be refused."""

    def __init__(self, sources):
        self.parent = list(range(len(sources)))
        self.sources = [{s} for s in sources]

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def join(self, a, b) -> bool | None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return None
        if self.sources[ra] & self.sources[rb]:
            return False
        self.parent[rb] = ra
        self.sources[ra] |= self.sources[rb]
        return True

    def same(self, a, b) -> None:
        """join one source's record written twice: no source check, since
        the two rows are one record (D-254)."""
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def group_records(stack: pd.DataFrame) -> pd.DataFrame:
    """the stack with url_key, name_key, group_id, match_basis, match_note
    and same_record_as."""
    out = stack.copy().reset_index(drop=True)
    out["url_key"] = [url_key(x) for x in out["url"]]
    out["name_key"] = [name_key(x) for x in out["name"]]
    groups = _Groups(list(out["source"]))
    basis = {i: set() for i in range(len(out))}
    notes = {i: [] for i in range(len(out))}

    # one record written twice joins itself first (D-254)
    rep = list(range(len(out)))
    same_as = [None] * len(out)
    alike: dict = {}
    for i, row in enumerate(out.to_dict("records")):
        ident = _identity(row)
        if ident:
            alike.setdefault((str(row["source"]),) + ident, []).append(i)
    for rows in alike.values():
        if len(rows) < 2:
            continue
        rows = sorted(rows, key=lambda i: _line_order(out.loc[i, "source_line"]))
        first = rows[0]
        for other in rows[1:]:
            groups.same(first, other)
            rep[other] = first
            same_as[other] = str(out.loc[first, "source_line"])
            notes[other].append(f"same record as {out.loc[first, 'source']} line "
                                f"{out.loc[first, 'source_line']}: name, url and office "
                                f"address alike")
        for r in rows:
            basis[r].add("same_record")

    for key in ("url_key", "name_key"):
        for value, rows in out.groupby(key, sort=True).groups.items():
            rows = sorted(rows)
            reps = sorted({rep[r] for r in rows})
            sources = out.loc[reps, "source"]
            twice = sorted(sources[sources.duplicated(keep=False)].unique())
            if twice:
                msg = (f"{key} {value!r} is held by more than one record of "
                       f"{', '.join(twice)}; not used to join")
                for r in rows:
                    notes[r].append(msg)
                continue
            for other in reps[1:]:
                joined = groups.join(reps[0], other)
                if joined:
                    for r in rows:
                        basis[r].add(key)
                elif joined is False:
                    msg = (f"{key} {value!r} also names {out.loc[reps[0], 'source']} "
                           f"line {out.loc[reps[0], 'source_line']}; not joined, "
                           f"since with the other key the group would hold one "
                           f"source twice")
                    for r in rows:
                        if rep[r] == other:
                            notes[r].append(msg)

    roots = [groups.find(i) for i in range(len(out))]
    first = {}
    for i, r in enumerate(roots):
        first.setdefault(r, len(first) + 1)
    out["group_id"] = [f"g{first[r]:04d}" for r in roots]
    out["match_basis"] = [",".join(sorted(basis[i])) or None for i in range(len(out))]
    out["match_note"] = ["; ".join(notes[i]) or None for i in range(len(out))]
    out["same_record_as"] = same_as
    return out


def disagreements(grouped: pd.DataFrame, fields=COMPARED) -> pd.DataFrame:
    """one row per group, field and source where a group holds two or more
    different values for that field. an empty value is not a disagreement;
    values are compared without regard to case or spacing."""
    rows = []
    for gid, g in grouped.groupby("group_id", sort=True):
        if g["source"].nunique() < 2:
            continue
        for field in fields:
            held = {}
            for _, r in g.iterrows():
                v = _text(r.get(field))
                if v is not None:
                    held.setdefault(" ".join(v.lower().split()), []).append(r)
            if len(held) < 2:
                continue
            for _, rs in held.items():
                for r in rs:
                    rows.append({"group_id": gid, "field": field, "source": r["source"],
                                 "source_line": r["source_line"], "name": r["name"],
                                 "value": _text(r.get(field))})
    return pd.DataFrame(rows, columns=["group_id", "field", "source", "source_line",
                                       "name", "value"])


def output_metadata(grouped: pd.DataFrame) -> dict:
    """what the receipt says of the grouped stack, its key included (KEYS-1)."""
    return {"data_category": "tabular", "crs": None, "row_count": len(grouped),
            "variables": list(grouped.columns), "id_fields": KEY,
            "spatial_unit": SPATIAL_UNIT}


def summary(grouped: pd.DataFrame) -> list[str]:
    sizes = grouped.groupby("group_id")["source"].nunique()
    notes = grouped["match_note"].fillna("")
    same = int(grouped["same_record_as"].notna().sum()) if "same_record_as" in grouped else 0
    return [f"{len(grouped)} records in {len(sizes)} groups",
            f"records read as another of their source's written twice (D-254): {same}",
            f"groups by number of sources: {sizes.value_counts().sort_index().to_dict()}",
            "records holding a key not used (one source holds it twice): "
            f"{int(notes.str.contains('not used to join').sum())}",
            f"joins refused across keys: {int(notes.str.contains('not joined').sum())}"]


def _pr_io():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from canopy import pr_io
    except ImportError:
        import pr_io
    return pr_io


def main():
    io = _pr_io()
    args = io.parse_primitive_args()
    w = io.WarningsCollector("group_outlet_records")
    with io.primitive_error_handling(w):
        stack = pd.read_csv(io.get_input(args["inputs"], "stack"), dtype=str)
        grouped = group_records(stack)
        for line in summary(grouped):
            w.info(line)
        grouped.to_csv(args["output"], index=False)
        io.primitive_success(output_metadata(grouped), w)


def by_hand(argv=None) -> int:
    ap = argparse.ArgumentParser(description="group stacked outlet records, by hand")
    ap.add_argument("--stack", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--disagreements", required=True)
    args = ap.parse_args(argv)
    grouped = group_records(pd.read_csv(args.stack, dtype=str))
    diff = disagreements(grouped)
    for p in (args.out, args.disagreements):
        Path(p).parent.mkdir(parents=True, exist_ok=True)
    grouped.to_csv(args.out, index=False)
    diff.to_csv(args.disagreements, index=False)
    print("\n".join(summary(grouped)))
    fields = diff.groupby("field")["group_id"].nunique().to_dict() if len(diff) else {}
    print(f"disagreeing groups by field: {fields}")
    print(f"wrote {args.out} and {args.disagreements}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        raise SystemExit(by_hand())
    main()
