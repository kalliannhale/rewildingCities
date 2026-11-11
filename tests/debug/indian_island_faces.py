"""tests/debug/indian_island_faces.py ~ read-only probe, not a test.

why does county subdivision 57936 (Penobscot Indian Island Reservation) have
only water faces at level cousub? counts the 2024 faces by county, LWFLAG and
tribal area, so the answer comes from the data, not from a guess.

  python tests/debug/indian_island_faces.py [cousub_code]
"""

import io
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import pyogrio

FACES = Path("plots/maine/.data/maine_faces_2024.zip")
COUSUB = sys.argv[1] if len(sys.argv) > 1 else "57936"
FIELDS = {"county": ("COUNTYFP", "COUNTYFP20"), "cousub": ("COUSUBFP", "COUSUBFP20"),
          "lwflag": ("LWFLAG",), "aiannh": ("AIANNHCE", "AIANNHCE20")}


def dbf_frames(zf, tmp, prefix=""):
    for name in zf.namelist():
        if name.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(zf.read(name))) as inner:
                yield from dbf_frames(inner, tmp, prefix + Path(name).stem + "_")
        elif name.lower().endswith(".dbf"):
            out = Path(tmp) / (prefix + Path(name).name)
            out.write_bytes(zf.read(name))
            yield pyogrio.read_dataframe(out, read_geometry=False)


def tidy(df):
    keep = {}
    for short, names in FIELDS.items():
        hit = next((n for n in names if n in df.columns), None)
        if hit:
            keep[hit] = short
    return df[list(keep)].rename(columns=keep).astype(str)


with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(FACES) as zf:
    faces = pd.concat([tidy(df) for df in dbf_frames(zf, tmp)], ignore_index=True)

print("fields found:", [c for c in FIELDS if c in faces.columns])
print("LWFLAG statewide:", faces["lwflag"].value_counts().to_dict())
mine = faces[faces["cousub"] == COUSUB]
print(f"cousub {COUSUB} by (county, lwflag):", mine.groupby(["county", "lwflag"]).size().to_dict())
if "aiannh" in faces.columns:
    codes = sorted(set(mine["aiannh"]) - {"", "None", "nan"})
    print(f"aiannh codes on cousub {COUSUB} faces:", codes)
    tribe = faces[faces["aiannh"].isin(codes)]
    print("those tribal areas by (county, cousub, lwflag):",
          tribe.groupby(["county", "cousub", "lwflag"]).size().to_dict())
