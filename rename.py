#!/usr/bin/env python3
"""
Rename and organize RAW shadow-capture images for CS 5330 submission.

Copies IMG_####.DNG files from ~/Downloads into a clean submission folder,
renamed to the assignment convention: hale_kalli_000.DNG ... in capture order.

Non-destructive: your originals are left untouched. Run the dry run first,
read the old -> new mapping, then flip DRY_RUN to actually write files.
"""

from pathlib import Path
import re
import shutil
import sys

# --- config -------------------------------------------------
SRC     = Path.home() / "Downloads"
DST     = Path.home() / "Downloads" / "hale_kalli_shadows"
LAST    = "hale"
FIRST   = "kalli"
EXT     = ".DNG"
NUM_LO  = 64      # IMG_0064.DNG
NUM_HI  = 240     # IMG_0240.DNG
DRY_RUN = False   # set to False to actually copy the files
# ------------------------------------------------------------

num_re = re.compile(r"IMG_(\d+)\.DNG$", re.IGNORECASE)


def collect(src):
    """Return (original_number, path) for every DNG in range, sorted by number.

    We glob real files rather than counting through the range, because the
    range has gaps (177 possible numbers, ~135 actual photos). Sorting by the
    iPhone's IMG number preserves capture order, and therefore your sequence.
    """
    hits = []
    for p in src.iterdir():
        m = num_re.search(p.name)
        if not m:
            continue
        n = int(m.group(1))
        if NUM_LO <= n <= NUM_HI:
            hits.append((n, p))
    hits.sort(key=lambda t: t[0])
    return hits


def main():
    if not SRC.exists():
        sys.exit(f"Source folder not found: {SRC}")

    files = collect(SRC)
    if not files:
        sys.exit(f"No {EXT} files in IMG_{NUM_LO:04d}-IMG_{NUM_HI:04d} found in {SRC}")

    print(f"Found {len(files)} {EXT} files in range "
          f"IMG_{NUM_LO:04d}-IMG_{NUM_HI:04d}.")
    print(f"Numbering them {LAST}_{FIRST}_000 ... {LAST}_{FIRST}_{len(files) - 1:03d}\n")

    if not DRY_RUN:
        DST.mkdir(parents=True, exist_ok=True)

    for i, (_orig_num, path) in enumerate(files):
        new_name = f"{LAST}_{FIRST}_{i:03d}{EXT}"
        print(f"{path.name:>16}  ->  {new_name}")
        if not DRY_RUN:
            shutil.copy2(path, DST / new_name)  # copy2 keeps EXIF/timestamps

    print()
    if DRY_RUN:
        print("DRY RUN. Nothing was copied. Set DRY_RUN = False to write files.")
    else:
        print(f"Done. {len(files)} files copied to {DST}")


if __name__ == "__main__":
    main()