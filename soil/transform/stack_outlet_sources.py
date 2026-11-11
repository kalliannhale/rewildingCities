"""
soil/transform/stack_outlet_sources.py

stack_outlet_sources ~ every outlet source's records, side by side

the first step of reconciling Maine's outlets (Sprint 06, step 8). it reads
each source the way seeds/crosswalks/outlets/outlet_sources.yml declares,
and stacks their records into one table, one row per source record. it
matches nothing and merges nothing: which records are the same outlet is a
later choice, and a stack that kept both is what lets that choice be seen.

  ~ a header row is found by its declared column names, never by position
  ~ a column the seed does not name is never read; a never_read column
    cannot be declared at all
  ~ a declared column missing from its file refuses the source by name
  ~ frequency maps to a cycle only by exact match; anything else stays
    unmapped, and frequency_note says why
  ~ a frequency_when gate reads frequency only for the media it names, and
    says what it left unread
  ~ nothing is defaulted: a source that declares no language has none
  ~ place fields keep their meaning: office_* is a postal address, named_*
    a town a source names, served_raw the coverage it describes. a county
    outside the seed's `counties` is flagged in location_note, never fixed

it reads only and writes only where it is told. ~
"""

from __future__ import annotations

import argparse
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


class SourceRefused(ValueError):
    """a source, or the seed, that cannot be read as declared, with why."""


def _cell(x) -> str | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    text = str(x).strip()
    return text or None


def load_seed(path: str | Path) -> dict:
    """the declared sources and the frequency vocabulary, checked."""
    doc = yaml.safe_load(Path(path).read_text()) or {}
    vocabulary = {}
    for cycle, raws in (doc.get("frequency_vocabulary") or {}).items():
        for raw in raws or []:
            if raw in vocabulary:
                raise SourceRefused(
                    f"{path}: frequency {raw!r} is listed under both "
                    f"{vocabulary[raw]} and {cycle}; a value maps to one cycle")
            vocabulary[raw] = cycle
    sources = doc.get("sources") or {}
    if not sources:
        raise SourceRefused(f"{path}: declares no sources")
    for key, spec in sources.items():
        spec = spec or {}
        columns = spec.get("columns") or {}
        if not spec.get("file"):
            raise SourceRefused(f"{path}: source {key} names no file")
        if "name" not in columns:
            raise SourceRefused(f"{path}: source {key} declares no name column")
        unknown = sorted(set(columns) - set(FIELDS))
        if unknown:
            raise SourceRefused(f"{path}: source {key} declares fields this stack "
                                f"does not carry: {', '.join(unknown)}")
        for field, column in columns.items():
            for prefix in spec.get("never_read") or []:
                if str(column).startswith(prefix):
                    raise SourceRefused(
                        f"{path}: source {key} declares {field} from {column!r}, "
                        f"which its never_read list refuses ({prefix!r})")
    counties = {str(c).strip().lower() for c in doc.get("counties") or []}
    return {"vocabulary": vocabulary, "sources": sources, "counties": counties}


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
        missing = sorted(wanted - seen)
        raise SourceRefused(f"source {key}: no row holds every declared column; "
                            f"missing: {', '.join(missing)}")
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
        bare = v.lower().removesuffix(" county").strip()
        if bare not in counties:
            notes.append(f"{field} {v!r} is not a county in the seed's list")
    return "; ".join(notes) or None


def read_source(key: str, spec: dict, root: str | Path,
                vocabulary: dict[str, str],
                counties: set[str] | None = None) -> pd.DataFrame:
    """one source's records, as declared, in the stack's columns."""
    path = Path(root) / spec["file"]
    if not path.is_file():
        raise SourceRefused(f"source {key}: {spec['file']} is not on disk")
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


def _frequency(rec: dict, spec: dict, vocabulary: dict[str, str]):
    raw = rec.get("frequency_raw")
    if raw is None:
        return None, None
    gate = spec.get("frequency_when") or {}
    for field, allowed in gate.items():
        if rec.get(field) not in allowed:
            rec["frequency_raw"] = None
            return None, (f"{raw!r} not read as a frequency: its {field} is "
                          f"{rec.get(field)!r}, and frequency is read only for "
                          f"{', '.join(allowed)}")
    cycle = vocabulary.get(raw)
    if cycle is None:
        return None, f"{raw!r} is in no cycle of the frequency vocabulary"
    return cycle, None


def stack_sources(seed: str | Path = SEED, root: str | Path = ".") -> pd.DataFrame:
    """every declared source's records, stacked in declaration order."""
    declared = load_seed(Path(root) / seed if not Path(seed).is_absolute() else seed)
    frames = [read_source(k, s, root, declared["vocabulary"], declared["counties"])
              for k, s in declared["sources"].items()]
    return pd.concat(frames, ignore_index=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="stack the declared outlet sources")
    ap.add_argument("--root", default=".")
    ap.add_argument("--seed", default=str(SEED))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    stack = stack_sources(args.seed, args.root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stack.to_csv(out, index=False)
    for key, g in stack.groupby("source", sort=False):
        mapped = g["frequency"].notna().sum()
        noted = g["frequency_note"].notna().sum()
        flagged = g["location_note"].notna().sum()
        print(f"{key}: {len(g)} rows, frequency mapped {mapped}, unmapped {noted}, "
              f"county flagged {flagged}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
