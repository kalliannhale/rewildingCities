"""
soil/transform/build_block_spine.py  |  rewildingCities

The block spine (Sprint 04, Contract 3): one row per 2020 Census tabulation
block in a state, with its counts and every unit it belongs to. Every overlaps
edge in the geography graph is a sum over this table, so it is built once,
checked once, and read by everything after it.

Each column comes from the Census file that is authoritative for it:
  persons, housing_units, households   2020 redistricting data (P1_001N,
                                       H1_001N, H1_002N: occupied units)
  cousub                               the 2020 block assignment file, MCD
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
Params:
  state_fips  two digits, required (e.g. "23")
Output: the spine, parquet or csv by the output's extension.
Refuses: a counts block missing from any assignment; a block assigned twice;
no member of an equivalency zip holding the state, or two that disagree;
households above housing units.
"""

from __future__ import annotations

import io
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


def build(counts, baf, bef_sldl, bef_sldu, state_fips, w):
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
    spine = spine.assign(county=spine["GEOID"].str[:5])
    spine = spine[["GEOID", "county", "cousub", "sldl", "sldu", "aiannh", "aiannh_comptyp",
                   "persons", "housing_units", "households"]]

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
        spine = build(read_table(get_input(args["inputs"], "counts")),
                      get_input(args["inputs"], "baf"),
                      get_input(args["inputs"], "bef_sldl"),
                      get_input(args["inputs"], "bef_sldu"), state, w)
        write_table(spine, args["output"])
        primitive_success({"data_category": "tabular", "crs": None,
                           "row_count": len(spine), "id_field": "GEOID",
                           "variables": list(spine.columns)}, w)


if __name__ == "__main__":
    main()
