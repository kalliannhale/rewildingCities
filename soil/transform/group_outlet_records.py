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
  ~ name   lowercased, & read as and, a trailing parenthetical and a leading
           "the" dropped, punctuation removed, spaces collapsed

a missed match costs a duplicate someone can see; a wrong match attributes
one outlet's owner to another. so a key never joins two records from the
same source: one source listing two outlets under one key is two outlets.
and a key value one source uses twice joins nothing at all, for anyone:
which of its two records another source's record belongs with would
otherwise be decided by row order, a silent choice. such a value is named
in match_note on every record that holds it. a join refused because two
keys together would put one source in a group twice is noted the same way
(D-202). ~

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  stack   the stack from stack_outlet_sources
Params:  none
Output:  the stack with url_key, name_key, group_id, match_basis and
         match_note, csv, keyed by (source, source_line)

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
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
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
    text = re.sub(r"^the\s+", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


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


def group_records(stack: pd.DataFrame) -> pd.DataFrame:
    """the stack with url_key, name_key, group_id, match_basis and match_note."""
    out = stack.copy().reset_index(drop=True)
    out["url_key"] = out["url"].map(url_key)
    out["name_key"] = out["name"].map(name_key)
    groups = _Groups(list(out["source"]))
    basis = {i: set() for i in range(len(out))}
    notes = {i: [] for i in range(len(out))}

    for key in ("url_key", "name_key"):
        for value, rows in out.groupby(key, sort=True).groups.items():
            rows = sorted(rows)
            sources = out.loc[rows, "source"]
            twice = sorted(sources[sources.duplicated(keep=False)].unique())
            if twice:
                msg = (f"{key} {value!r} is held by more than one record of "
                       f"{', '.join(twice)}; not used to join")
                for r in rows:
                    notes[r].append(msg)
                continue
            for other in rows[1:]:
                joined = groups.join(rows[0], other)
                if joined:
                    basis[rows[0]].add(key)
                    basis[other].add(key)
                elif joined is False:
                    msg = (f"{key} {value!r} also names {out.loc[rows[0], 'source']} "
                           f"line {out.loc[rows[0], 'source_line']}; not joined, "
                           f"since with the other key the group would hold one "
                           f"source twice")
                    notes[other].append(msg)

    roots = [groups.find(i) for i in range(len(out))]
    first = {}
    for i, r in enumerate(roots):
        first.setdefault(r, len(first) + 1)
    out["group_id"] = [f"g{first[r]:04d}" for r in roots]
    out["match_basis"] = [",".join(sorted(basis[i])) or None for i in range(len(out))]
    out["match_note"] = ["; ".join(notes[i]) or None for i in range(len(out))]
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
    return [f"{len(grouped)} records in {len(sizes)} groups",
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
