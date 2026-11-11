"""
soil/transform/stack_outlet_sources.py  |  rewildingCities

stack_outlet_sources ~ every outlet source's records, side by side

the first step of reconciling Maine's outlets (Sprint 06, step 8). it reads
each source the way its declaration says (seeds/crosswalks/outlets/
outlet_sources.yml) and stacks their records into one table, one row per
source record. it matches nothing and merges nothing: which records are the
same outlet is a later step, and a stack that kept both lets that be seen.

  ~ a header row is found by its declared column names, never by position
  ~ a column the declaration does not name is never read; a never_read
    column cannot be declared at all (D-201)
  ~ a declared column missing from its file refuses the source by name
  ~ frequency maps to a cycle only by exact match; anything else stays
    unmapped, and frequency_note says why
  ~ a frequency_when gate reads frequency only for the media it names
  ~ nothing is defaulted: a source that declares no language has none
  ~ place fields keep their meaning (D-203): office_* is a postal address,
    named_* a town a source names, served_raw the coverage it describes. a
    county outside the declaration's `counties` is flagged in
    location_note, never fixed

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  one per declared source, named by its key (cision, easton, ...)
Params:  declaration   the outlet_sources declaration, as a mapping
Output:  the stack, csv. one row per source record, keyed by
         (source, source_line)
Refuses: a declared source with no input, or an input no source declares;
         a declaration that maps one raw frequency to two cycles, names a
         field this stack does not carry, or declares a never_read column;
         a source whose header holds a declared column twice, or none.

Run by hand for a look, outside any run, with `--out` (the paths come from
each source's `file:`, read from --root). ~
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import yaml

SEED = Path("seeds") / "crosswalks" / "outlets" / "outlet_sources.yml"
FIELDS = ("name", "url", "office_town", "office_county", "named_town",
          "named_county", "served_raw", "medium_raw", "frequency_raw",
          "ownership_raw", "business_model_raw", "affiliation_raw",
          "operating_raw", "language_raw", "address_raw", "zip_raw")
COLUMNS = ("source", "source_line") + FIELDS + ("frequency", "frequency_note",
                                                 "location_note")
COUNTY_FIELDS = ("office_county", "named_county")
KEY = ["source", "source_line"]
SPATIAL_UNIT = "outlet_record"


class SourceRefused(ValueError):
    """a source, or the declaration, that cannot be read as declared, with why."""


def _cell(x) -> str | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    text = str(x).strip()
    return text or None


def check_declaration(doc: dict, where: str = "the declaration") -> dict:
    """the declared sources, frequency vocabulary and counties, checked."""
    doc = doc or {}
    vocabulary = {}
    for cycle, raws in (doc.get("frequency_vocabulary") or {}).items():
        for raw in raws or []:
            if raw in vocabulary:
                raise SourceRefused(
                    f"{where}: frequency {raw!r} is listed under both "
                    f"{vocabulary[raw]} and {cycle}; a value maps to one cycle")
            vocabulary[raw] = cycle
    sources = doc.get("sources") or {}
    if not sources:
        raise SourceRefused(f"{where}: declares no sources")
    for key, spec in sources.items():
        spec = spec or {}
        columns = spec.get("columns") or {}
        if "name" not in columns:
            raise SourceRefused(f"{where}: source {key} declares no name column")
        unknown = sorted(set(columns) - set(FIELDS))
        if unknown:
            raise SourceRefused(f"{where}: source {key} declares fields this stack "
                                f"does not carry: {', '.join(unknown)}")
        for field, column in columns.items():
            for prefix in spec.get("never_read") or []:
                if str(column).startswith(prefix):
                    raise SourceRefused(
                        f"{where}: source {key} declares {field} from {column!r}, "
                        f"which its never_read list refuses ({prefix!r})")
    counties = {str(c).strip().lower() for c in doc.get("counties") or []}
    return {"vocabulary": vocabulary, "sources": sources, "counties": counties}


def load_seed(path: str | Path) -> dict:
    """read and check a declaration file."""
    return check_declaration(yaml.safe_load(Path(path).read_text()), str(path))


def _read_raw(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, dtype=str, header=None)
    except UnicodeDecodeError:
        return pd.read_csv(path, dtype=str, header=None, encoding="latin-1")


def _header_line(raw: pd.DataFrame, wanted: set[str], key: str) -> int:
    """the one row holding every declared column name, or refused."""
    hits = [i for i in range(len(raw))
            if wanted <= {c for c in (_cell(x) for x in raw.iloc[i]) if c}]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        best = max(range(len(raw)), default=None,
                   key=lambda i: len(wanted & {_cell(x) for x in raw.iloc[i]}))
        seen = set() if best is None else {_cell(x) for x in raw.iloc[best]}
        raise SourceRefused(f"source {key}: no row holds every declared column; "
                            f"missing: {', '.join(sorted(wanted - seen))}")
    raise SourceRefused(f"source {key}: {len(hits)} rows hold the declared columns "
                        f"(lines {', '.join(str(h + 1) for h in hits)}); which is "
                        f"the header is a choice, not a lookup")


def _county_note(rec: dict, counties: set[str]) -> str | None:
    if not counties:
        return None
    notes = []
    for field in COUNTY_FIELDS:
        v = rec.get(field)
        if v is None:
            continue
        if v.lower().removesuffix(" county").strip() not in counties:
            notes.append(f"{field} {v!r} is not a county in the declaration's list")
    return "; ".join(notes) or None


def _frequency(rec: dict, spec: dict, vocabulary: dict[str, str]):
    raw = rec.get("frequency_raw")
    if raw is None:
        return None, None
    for field, allowed in (spec.get("frequency_when") or {}).items():
        if rec.get(field) not in allowed:
            rec["frequency_raw"] = None
            return None, (f"{raw!r} not read as a frequency: its {field} is "
                          f"{rec.get(field)!r}, and frequency is read only for "
                          f"{', '.join(allowed)}")
    cycle = vocabulary.get(raw)
    if cycle is None:
        return None, f"{raw!r} is in no cycle of the frequency vocabulary"
    return cycle, None


def read_source(key: str, spec: dict, path: str | Path,
                vocabulary: dict[str, str],
                counties: set[str] | None = None) -> pd.DataFrame:
    """one source's records, as declared, in the stack's columns."""
    path = Path(path)
    if not path.is_file():
        raise SourceRefused(f"source {key}: {path} is not on disk")
    raw = _read_raw(path)
    columns = spec["columns"]
    head = _header_line(raw, set(columns.values()), key)
    names = [_cell(x) for x in raw.iloc[head]]
    position = {}
    for column in set(columns.values()):
        at = [i for i, n in enumerate(names) if n == column]
        if len(at) > 1:
            raise SourceRefused(f"source {key}: column {column!r} appears {len(at)} "
                                f"times in its header")
        position[column] = at[0]

    rows = []
    for i in range(head + 1, len(raw)):
        line = raw.iloc[i]
        rec = {f: _cell(line.iloc[position[c]]) for f, c in columns.items()}
        if not any(rec.values()):
            continue
        rec = {f: rec.get(f) for f in FIELDS}
        rec["source"], rec["source_line"] = key, i + 1
        rec["frequency"], rec["frequency_note"] = _frequency(rec, spec, vocabulary)
        rec["location_note"] = _county_note(rec, counties or set())
        rows.append(rec)
    return pd.DataFrame(rows, columns=list(COLUMNS))


def stack_from(declared: dict, paths: dict[str, str | Path]) -> pd.DataFrame:
    """every declared source's records, from the paths a run hands in, stacked
    in declaration order. a declared source with no path, or a path no source
    declares, is refused: one silently dropped source is a missing outlet."""
    sources = declared["sources"]
    missing = sorted(set(sources) - set(paths))
    extra = sorted(set(paths) - set(sources))
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"declared with no input: {', '.join(missing)}")
        if extra:
            parts.append(f"input with no declaration: {', '.join(extra)}")
        raise SourceRefused("the run's inputs and the declaration disagree; " + "; ".join(parts))
    frames = [read_source(k, s, paths[k], declared["vocabulary"], declared["counties"])
              for k, s in sources.items()]
    return pd.concat(frames, ignore_index=True)


def stack_sources(seed: str | Path = SEED, root: str | Path = ".") -> pd.DataFrame:
    """the by-hand route: paths from each source's `file:`, read from root."""
    seed = Path(seed) if Path(seed).is_absolute() else Path(root) / seed
    declared = load_seed(seed)
    paths = {}
    for k, s in declared["sources"].items():
        if not s.get("file"):
            raise SourceRefused(f"{seed}: source {k} names no file to read by hand")
        paths[k] = Path(root) / s["file"]
    return stack_from(declared, paths)


def output_metadata(stack: pd.DataFrame) -> dict:
    """what the receipt says of the stack, its key included (KEYS-1)."""
    return {"data_category": "tabular", "crs": None, "row_count": len(stack),
            "variables": list(COLUMNS), "id_fields": KEY, "spatial_unit": SPATIAL_UNIT}


def summary(stack: pd.DataFrame) -> list[str]:
    lines = []
    for key, g in stack.groupby("source", sort=False):
        lines.append(f"{key}: {len(g)} rows, frequency mapped {int(g['frequency'].notna().sum())}, "
                     f"unmapped {int(g['frequency_note'].notna().sum())}, "
                     f"county flagged {int(g['location_note'].notna().sum())}")
    return lines


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from canopy.pr_io import (parse_primitive_args, get_input, require_param,
                                  WarningsCollector, primitive_success,
                                  primitive_error_handling)
    except ImportError:
        from pr_io import (parse_primitive_args, get_input, require_param,
                           WarningsCollector, primitive_success,
                           primitive_error_handling)
    args = parse_primitive_args()
    w = WarningsCollector("stack_outlet_sources")
    with primitive_error_handling(w):
        declared = check_declaration(require_param(args["params"], "declaration"))
        paths = {k: get_input(args["inputs"], k) for k in args["inputs"]}
        stack = stack_from(declared, paths)
        for line in summary(stack):
            w.info(line)
        stack.to_csv(args["output"], index=False)
        primitive_success(output_metadata(stack), w)


def by_hand(argv=None) -> int:
    ap = argparse.ArgumentParser(description="stack the declared outlet sources, by hand")
    ap.add_argument("--root", default=".")
    ap.add_argument("--seed", default=str(SEED))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    stack = stack_sources(args.seed, args.root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stack.to_csv(out, index=False)
    print("\n".join(summary(stack)))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        raise SystemExit(by_hand())
    main()
