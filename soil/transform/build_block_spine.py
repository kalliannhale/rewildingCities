"""
soil/transform/build_block_spine.py  |  rewildingCities

The block spine (Sprint 04, Contract 3): one row per 2020 Census tabulation
block in a state, with its counts and every unit it belongs to. Every overlaps
edge in the geography graph is a sum over this table, so it is built once,
checked once, and read by everything after it.

Each column comes from the Census file that is authoritative for it:
  persons, housing_units, households   2020 redistricting data (P1_001N,
                                       H1_001N, H1_002N: occupied units)
  cousub, cousub_split                 2024 TIGER/Line topological faces, when
                                       given (D-126): ACS 2024 is tabulated on
                                       2024 towns, so the spine's towns are
                                       2024 too. a 2020 block that a later
                                       boundary split goes whole to the town
                                       holding most of its land, and is flagged
  cousub_2020                          the 2020 block assignment file, MCD,
                                       kept beside the 2024 town as the check
  aiannh, aiannh_comptyp               the 2020 block assignment file, AIANNH
  sldl, sldu                           the 2024 block equivalency files
The 2020 assignment file's own SLDL and SLDU are never read: they predate the
2021 redistricting, and joined to ACS 2024 values they would draw the right
number of districts with the wrong lines.

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:
  counts      blocks with GEOID, P1_001N, H1_001N, H1_002N (parquet or csv)
  baf         the state's 2020 block assignment zip
  bef_sldl    the 2024 lower-chamber block equivalency zip (national)
  bef_sldu    the 2024 upper-chamber block equivalency zip (national)
  faces       optional: 2024 TIGER/Line faces, one county's zip or a zip of
              county zips (tl_2024_<county>_faces.zip). without it, towns are
              the 2020 file's, and the spine says so
Params:
  state_fips  two digits, required (e.g. "23")
Output: the spine, parquet or csv by the output's extension.
Refuses: a counts block missing from any assignment; a block assigned twice;
no member of an equivalency zip holding the state, or two that disagree;
households above housing units; a counted block with no 2024 face.
"""

from __future__ import annotations

import io
import struct
import zipfile

try:
    from canopy.pr_io import (parse_primitive_args, get_input, require_param,
                              WarningsCollector, primitive_success, primitive_failure,
                              primitive_error_handling)
except ImportError:
    from pr_io import (parse_primitive_args, get_input, require_param,
                       WarningsCollector, primitive_success, primitive_failure,
                       primitive_error_handling)


def read_table(path):
    import pandas as pd
    if str(path).endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype=str)


def write_table(frame, path):
    if str(path).endswith(".parquet"):
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)


def _member(z: zipfile.ZipFile, suffix: str) -> str:
    names = [n for n in z.namelist() if n.upper().endswith(suffix.upper())]
    if len(names) != 1:
        primitive_failure("Block assignment file not found",
                          f"expected exactly one member ending {suffix}; found {names}")
    return names[0]


def read_baf(path, suffix, columns):
    """one member of a 2020 block assignment zip, pipe-delimited, as text."""
    import pandas as pd
    with zipfile.ZipFile(path) as z:
        raw = z.read(_member(z, suffix)).decode("utf-8-sig")
    frame = pd.read_csv(io.StringIO(raw), sep="|", dtype=str, keep_default_na=False)
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        primitive_failure("Unexpected block assignment layout",
                          f"{suffix} lacks {missing}; it has {list(frame.columns)}")
    return frame


def read_bef_state(path, state_fips, w, label):
    """the one member of a national block equivalency zip that holds this
    state's blocks. the zip lists changed states first and the national file
    among them, so its name is not assumed: whichever member has the state's
    rows is read, and two that disagree are refused."""
    import pandas as pd
    found = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            raw = z.read(name).decode("utf-8-sig")
            lines = raw.splitlines()
            if not lines:
                continue
            rows = [l for l in lines[1:] if l[:2] == state_fips]
            if rows:
                found[name] = pd.read_csv(io.StringIO("\n".join([lines[0]] + rows)), dtype=str)
    if not found:
        primitive_failure("State not in equivalency file",
                          f"no member of {label} holds blocks of state {state_fips}")
    frames = list(found.values())
    first = frames[0].sort_values(frames[0].columns[0]).reset_index(drop=True)
    for other in frames[1:]:
        if not first.equals(other.sort_values(other.columns[0]).reset_index(drop=True)):
            primitive_failure("Equivalency files disagree",
                              f"{label}: members {list(found)} assign this state's blocks differently")
    w.info(f"{label}: read {len(first)} block(s) of state {state_fips} from {sorted(found)}")
    return first


FACE_FIELDS = ["STATEFP20", "COUNTYFP20", "TRACTCE20", "BLOCKCE20",
               "STATEFP", "COUNTYFP", "COUSUBFP", "SLDLST", "SLDUST", "LWFLAG", "ATOTAL"]


def read_dbf(raw, fields, label):
    """the named fields of a dBase table, as text, for every live record.
    a faces shapefile's attributes are its .dbf, so geometry is never read."""
    import pandas as pd
    count = struct.unpack("<I", raw[4:8])[0]
    header_len, record_len = struct.unpack("<HH", raw[8:12])
    specs, pos, offset = {}, 32, 1
    while raw[pos] != 0x0D:
        name = raw[pos:pos + 11].split(b"\0")[0].decode("ascii")
        specs[name] = (offset, raw[pos + 16])
        offset += raw[pos + 16]
        pos += 32
    missing = [f for f in fields if f not in specs]
    if missing:
        primitive_failure("Unexpected faces layout",
                          f"{label} lacks {missing}; it has {sorted(specs)}")
    cuts = [specs[f] for f in fields]
    rows = []
    for i in range(count):
        rec = raw[header_len + i * record_len: header_len + (i + 1) * record_len]
        if rec[:1] == b"*":
            continue
        rows.append([rec[o:o + n].decode("utf-8", "replace").strip() for o, n in cuts])
    return pd.DataFrame(rows, columns=fields)


def read_faces(path, w):
    """every faces table in a county zip, or in a zip of county zips."""
    import pandas as pd
    tables = []
    with zipfile.ZipFile(path) as outer:
        for name in sorted(outer.namelist()):
            if name.lower().endswith("_faces.dbf"):
                tables.append(read_dbf(outer.read(name), FACE_FIELDS, name))
            elif name.lower().endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(outer.read(name))) as inner:
                    dbf = [n for n in inner.namelist() if n.lower().endswith("_faces.dbf")]
                    if len(dbf) != 1:
                        primitive_failure("Faces table not found",
                                          f"{name}: expected one _faces.dbf; found {dbf}")
                    tables.append(read_dbf(inner.read(dbf[0]), FACE_FIELDS, name))
    if not tables:
        primitive_failure("Faces table not found", f"no _faces.dbf in {path}")
    w.info(f"faces: read {sum(len(t) for t in tables)} face(s) from {len(tables)} table(s)")
    return pd.concat(tables, ignore_index=True)


def faces_by_block(faces, state_fips, w):
    """each 2020 block's 2024 town, House and Senate district, from the faces
    that make it up. a block whose faces lie in two towns goes whole to the
    town holding most of its land (then most of its area, then the lower
    code), because a block's counts cannot be divided, and is flagged."""
    import pandas as pd
    f = faces[faces["STATEFP20"] == state_fips].copy()
    f["GEOID"] = f["STATEFP20"] + f["COUNTYFP20"] + f["TRACTCE20"] + f["BLOCKCE20"]
    f["town"] = f["STATEFP"] + f["COUNTYFP"] + f["COUSUBFP"]
    f["area"] = pd.to_numeric(f["ATOTAL"], errors="coerce").fillna(0.0)
    f["land"] = f["area"].where(f["LWFLAG"] == "L", 0.0)
    pieces = f.groupby(["GEOID", "town"], as_index=False)[["land", "area"]].sum()
    pieces = pieces.sort_values(["GEOID", "land", "area", "town"],
                                ascending=[True, False, False, True])
    towns = pieces.groupby("GEOID")["town"].agg(["first", "size"])
    by_block = pd.DataFrame({"GEOID": towns.index, "cousub_2024": towns["first"].values,
                             "cousub_split": (towns["size"] > 1).values})

    def majority(col):
        p = f.groupby(["GEOID", col], as_index=False)["land"].sum()
        p = p.sort_values(["GEOID", "land", col], ascending=[True, False, True])
        return p.groupby("GEOID")[col].first()
    by_block = by_block.join(majority("SLDLST").rename("faces_sldl"), on="GEOID")
    by_block = by_block.join(majority("SLDUST").rename("faces_sldu"), on="GEOID")
    undefined = by_block["cousub_2024"].str.endswith("00000")
    if undefined.any():
        w.warn(f"{int(undefined.sum())} block(s) lie mostly in a county subdivision not "
               f"defined (code 00000)")
    return by_block


def build(counts, baf, bef_sldl, bef_sldu, state_fips, w, faces=None):
    import pandas as pd
    c = counts.copy()
    c["GEOID"] = c["GEOID"].astype(str)
    c = c[c["GEOID"].str[:2] == state_fips]
    for v in ("P1_001N", "H1_001N", "H1_002N"):
        c[v] = pd.to_numeric(c[v]).astype("int64")

    mcd = read_baf(baf, "_MCD.txt", ["BLOCKID", "COUNTYFP", "COUSUBFP"])
    ai = read_baf(baf, "_AIANNH.txt", ["BLOCKID", "AIANNHCE", "COMPTYP"])
    lower = read_bef_state(bef_sldl, state_fips, w, "2024 lower-chamber equivalency")
    upper = read_bef_state(bef_sldu, state_fips, w, "2024 upper-chamber equivalency")

    mcd = mcd.assign(cousub=state_fips + mcd["COUNTYFP"] + mcd["COUSUBFP"])[["BLOCKID", "cousub"]]
    ai = ai.assign(aiannh=ai["AIANNHCE"].where(ai["AIANNHCE"] != "", None),
                   aiannh_comptyp=ai["COMPTYP"].where(ai["COMPTYP"] != "", None))
    ai = ai[["BLOCKID", "aiannh", "aiannh_comptyp"]]
    lower = lower.rename(columns={lower.columns[0]: "BLOCKID", lower.columns[1]: "district"})
    upper = upper.rename(columns={upper.columns[0]: "BLOCKID", upper.columns[1]: "district"})
    lower = lower.assign(sldl=state_fips + lower["district"].str.zfill(3))[["BLOCKID", "sldl"]]
    upper = upper.assign(sldu=state_fips + upper["district"].str.zfill(3))[["BLOCKID", "sldu"]]

    for label, frame in (("MCD", mcd), ("AIANNH", ai), ("SLDL", lower), ("SLDU", upper)):
        dup = frame["BLOCKID"].duplicated()
        if dup.any():
            primitive_failure("Block assigned twice",
                              f"{label}: {int(dup.sum())} block(s) appear more than once, "
                              f"e.g. {frame.loc[dup, 'BLOCKID'].iloc[0]}")
        absent = set(c["GEOID"]) - set(frame["BLOCKID"])
        if absent:
            primitive_failure("Block without an assignment",
                              f"{len(absent)} counted block(s) have no {label} assignment, "
                              f"e.g. {sorted(absent)[0]}")
        extra = set(frame["BLOCKID"]) - set(c["GEOID"])
        if extra:
            w.warn(f"{label} assigns {len(extra)} block(s) that the counts do not hold; "
                   f"they are not in the spine")

    spine = (c.rename(columns={"P1_001N": "persons", "H1_001N": "housing_units",
                               "H1_002N": "households"})
              .merge(mcd, left_on="GEOID", right_on="BLOCKID").drop(columns="BLOCKID")
              .merge(ai, left_on="GEOID", right_on="BLOCKID").drop(columns="BLOCKID")
              .merge(lower, left_on="GEOID", right_on="BLOCKID").drop(columns="BLOCKID")
              .merge(upper, left_on="GEOID", right_on="BLOCKID").drop(columns="BLOCKID"))
    spine = spine.assign(county=spine["GEOID"].str[:5], cousub_2020=spine["cousub"])

    if faces is None:
        spine = spine.assign(cousub_split=False)
        w.warn("no 2024 faces given: towns are the 2020 block assignment file's, and "
               "will not match ACS 2024 wherever a town changed since 2020 (TOWN-1)")
    else:
        current = faces_by_block(faces, state_fips, w)
        absent = set(spine["GEOID"]) - set(current["GEOID"])
        if absent:
            primitive_failure("Block without a 2024 face",
                              f"{len(absent)} counted block(s) have no face in the 2024 "
                              f"faces, e.g. {sorted(absent)[0]}")
        spine = spine.merge(current, on="GEOID", how="left")
        spine["cousub"] = spine["cousub_2024"]
        moved = spine[spine["cousub"] != spine["cousub_2020"]]
        if len(moved):
            pairs = (moved.groupby(["cousub_2020", "cousub"])
                          .agg(blocks=("GEOID", "size"), persons=("persons", "sum"))
                          .reset_index())
            w.info(f"{len(moved)} block(s), {int(moved['persons'].sum())} persons, are in a "
                   f"different town in 2024 than in 2020, as {len(pairs)} change(s)")
            for r in pairs.head(25).itertuples():
                w.info(f"  {r.cousub_2020} -> {r.cousub}: {r.blocks} block(s), "
                       f"{r.persons} persons")
        split = spine[spine["cousub_split"]]
        if len(split):
            w.info(f"{len(split)} block(s), {int(split['persons'].sum())} persons, are split "
                   f"between 2024 towns; each went whole to its larger land piece")
        for chamber in ("sldl", "sldu"):
            check = spine[f"faces_{chamber}"].notna()
            off = check & (state_fips + spine[f"faces_{chamber}"].str.zfill(3) != spine[chamber])
            w.info(f"{chamber}: the 2024 faces and the 2024 equivalency file disagree on "
                   f"{int(off.sum())} of {int(check.sum())} block(s)")

    spine = spine[["GEOID", "county", "cousub", "cousub_2020", "cousub_split", "sldl", "sldu",
                   "aiannh", "aiannh_comptyp", "persons", "housing_units", "households"]]

    over = spine["households"] > spine["housing_units"]
    if over.any():
        primitive_failure("Households exceed housing units",
                          f"{int(over.sum())} block(s), e.g. {spine.loc[over, 'GEOID'].iloc[0]}")
    bad_county = spine["cousub"].str[:5] != spine["county"]
    if bad_county.any():
        primitive_failure("Town outside its county",
                          f"{int(bad_county.sum())} block(s) whose town code names another county")
    w.info(f"spine: {len(spine)} block(s), {spine['persons'].sum()} persons, "
           f"{spine['households'].sum()} households, {spine['cousub'].nunique()} town(s), "
           f"{spine['sldl'].nunique()} House and {spine['sldu'].nunique()} Senate district(s), "
           f"{spine['aiannh'].nunique()} tribal area code(s)")
    return spine


def main():
    args = parse_primitive_args()
    w = WarningsCollector("build_block_spine")
    with primitive_error_handling(w):
        state = str(require_param(args["params"], "state_fips")).zfill(2)
        faces_path = get_input(args["inputs"], "faces", required=False)
        spine = build(read_table(get_input(args["inputs"], "counts")),
                      get_input(args["inputs"], "baf"),
                      get_input(args["inputs"], "bef_sldl"),
                      get_input(args["inputs"], "bef_sldu"), state, w,
                      faces=read_faces(faces_path, w) if faces_path else None)
        write_table(spine, args["output"])
        primitive_success({"data_category": "tabular", "crs": None,
                           "row_count": len(spine), "id_field": "GEOID",
                           "variables": list(spine.columns)}, w)


if __name__ == "__main__":
    main()