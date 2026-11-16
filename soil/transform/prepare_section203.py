"""
soil/transform/prepare_section203.py
the Census's Section 203 determinations for one state, read as published
(D-263, D-264).

reads the complete public use file (every jurisdiction by language minority
group, covered or not) from the release zip, by the columns, codes and
summary levels the crosswalk section203_puf_2021 declares, and writes one row
per place and group for the state, its towns (minor civil divisions) and the
American Indian areas that overlap its towns.

rules, each because the other way is simply wrong (D-212):
  ~ the bytes are read in the release's declared encoding, strictly: a byte
    that encoding cannot read refuses the run, never a silent replacement
  ~ a row is keyed by LANCOUNT; its LANGUAGE text is kept as written, beside
    the documented label, and an undeclared code refuses the run
  ~ the flags are copied as Census set them, on unrounded data: coverage is
    never recomputed from the rounded public values
  ~ a town is named by our own town code: the file writes county 000 on
    every town row, so its five-digit MCD is matched to the last five digits
    of a town GEOID. when those five digits name more than one of our town
    pieces (a town Census splits at a county line, as Penobscot Indian
    Island Reservation, 57936), the Census row is the whole town's: it is
    held under census_s203_mcd at state plus MCD, attached to no piece, and
    the pieces are listed (D-267). a Census town matching none of ours (the
    file's towns are of its own, older vintage, so a town since deorganized
    stands in it) is held the same way under census_s203_mcd and listed by
    name; our towns with no record are listed by name
  ~ an AIAN/MCD row is never a town's value: Census gives there the whole
    American Indian area's estimates, not the part inside the town. only the
    overlap itself is kept, in the metadata
  ~ an American Indian area row keeps Census's four-digit area code under its
    own authority, census_s203_aian_area: an area spans reservation and trust
    land together and is none of our places on its own (D-264). whether and
    how it is shown is the nations' to say (P-8)
inputs:
  puf:    the release zip (section203_public_use_file)
  towns:  an acquisition naming the state's towns by GEOID and NAME
params:
  encoding, member, determination_date, acs_basis: the release's facts,
          held to its manifest entry (D-192)
  state_fips: two digits
  reading: the crosswalk, whole
output:  section203_records, one row per place and group
"""
from __future__ import annotations

import csv
import io
import zipfile

import pandas as pd

AIAN_AUTHORITY = "census_s203_aian_area"
MCD_AUTHORITY = "census_s203_mcd"


class Section203Refused(ValueError):
    """a release, or a declaration, that cannot be read as declared."""


def read_member(zip_path: str, member: str, encoding: str) -> list[dict]:
    with zipfile.ZipFile(zip_path) as z:
        if member not in z.namelist():
            raise Section203Refused(
                f"the release holds no {member}; it holds {', '.join(sorted(z.namelist()))}")
        raw = z.read(member)
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError as e:
        raise Section203Refused(
            f"{member} is not {encoding} at byte {e.start}: the release's declared "
            f"encoding is wrong, and no byte is replaced to make it read") from e
    return list(csv.DictReader(io.StringIO(text)))


def check_header(rows: list[dict], reading: dict) -> None:
    if not rows:
        raise Section203Refused("the file holds no rows")
    found, declared = list(rows[0].keys()), list(reading["columns"])
    if found != declared:
        raise Section203Refused(
            f"the header is not the declared one: found {found}, declared {declared}")


def _number(x: str):
    x = (x or "").strip()
    return None if x == "" else float(x)


def _flag(x: str):
    x = (x or "").strip()
    return None if x == "" else x


def town_codes(towns: pd.DataFrame, state_fips: str) -> dict[str, list[tuple[str, str]]]:
    """five-digit MCD code to every (town GEOID, name) of ours ending in it:
    one for a whole town, more for a town Census splits at a county line."""
    out: dict[str, list[tuple[str, str]]] = {}
    for _, t in towns.iterrows():
        geoid = str(t["GEOID"]).strip()
        if len(geoid) != 10 or not geoid.startswith(state_fips):
            raise Section203Refused(f"town code {geoid!r} is not a ten-digit town GEOID in {state_fips}")
        out.setdefault(geoid[-5:], []).append((geoid, str(t.get("NAME", ""))))
    return out


def records_from(rows: list[dict], towns: dict, state_fips: str, reading: dict) -> tuple[list[dict], dict]:
    levels, lan = reading["summary_levels"], reading["lancount"]
    numeric, flags = reading["numeric"], reading["flags"]
    out: list[dict] = []
    overlaps: dict[tuple[str, str], str] = {}
    matched: set[str] = set()
    nation_illrat = None
    not_ours: dict[str, str] = {}
    by_level: dict[str, int] = {}

    def record(r, level, authority, code):
        c = r["LANCOUNT"].strip()
        row = {"record_id": f"{level}:{code}:{c}", "level": level,
               "unit_authority": authority, "unit_code": code, "name": r["NAMELSAD"],
               "lancount": c, "group_class": lan[c]["class"],
               "group_documented": lan[c]["label"], "group_as_written": r["LANGUAGE"]}
        for k in numeric:
            row[k.lower()] = _number(r[k])
        for k in flags:
            row[k.lower()] = _flag(r[k])
        row["suppressed"] = row["vaclep"] is None and lan[c]["class"] != "total"
        return row

    aian_codes: set[str] = set()
    for r in rows:
        s, c = r["SUMLVL"].strip(), r["LANCOUNT"].strip()
        if s not in levels:
            raise Section203Refused(f"summary level {s!r} is not declared")
        if c not in lan:
            raise Section203Refused(f"LANCOUNT {c!r} ({r['LANGUAGE']}) is not declared")
        level = levels[s]
        if level == "nation":
            nation_illrat = _number(r["ILLRAT"])
            continue
        if r["ST"].strip() != state_fips:
            continue
        by_level[level] = by_level.get(level, 0) + 1
        if level == "state":
            out.append(record(r, "state", "us_census_geoid", state_fips))
        elif level == "mcd":
            mcd = r["MCD"].strip()
            if mcd not in towns:
                not_ours[state_fips + mcd] = r["NAMELSAD"]
                out.append(record(r, "census_town_not_ours", MCD_AUTHORITY, state_fips + mcd))
                continue
            matched.add(mcd)
            if len(towns[mcd]) == 1:
                out.append(record(r, "town", "us_census_geoid", towns[mcd][0][0]))
            else:
                out.append(record(r, "split_town", MCD_AUTHORITY, state_fips + mcd))
        elif level == "aian_mcd":
            mcd = r["MCD"].strip()
            aian_codes.add(r["AIAN"].strip())
            for geoid, _ in towns.get(mcd, [(mcd, "")]):
                overlaps[(r["AIAN"].strip(), geoid)] = r["NAMELSAD"]
        elif level == "county":
            out.append(record(r, "county", "us_census_geoid", state_fips + r["CNTY"].strip()))

    area_names: dict[str, str] = {}
    for r in rows:
        if levels[r["SUMLVL"].strip()] == "aian" and r["AIAN"].strip() in aian_codes:
            area_names[r["AIAN"].strip()] = r["NAMELSAD"]
            out.append(record(r, "tribal_area", AIAN_AUTHORITY, r["AIAN"].strip()))

    missing = sorted(set(towns) - matched)
    meta = {
        "rows_by_level": by_level,
        "towns_matched": len(matched),
        "towns_without_record": [{"geoid": g, "name": n} for m in missing for g, n in towns[m]],
        "split_towns_held_whole": [{"census_code": state_fips + m, "pieces": [g for g, _ in towns[m]]}
                                   for m in sorted(matched) if len(towns[m]) > 1],
        "census_towns_not_ours": [{"census_code": k, "name": v} for k, v in sorted(not_ours.items())],
        "tribal_areas": [{"code": k, "name": v} for k, v in sorted(area_names.items())],
        "tribal_areas_without_area_row": sorted(aian_codes - set(area_names)),
        "tribal_area_town_overlaps": [{"aian": a, "town": t} for a, t in sorted(overlaps)],
        "covered_rows": sum(1 for o in out if o["flag_cov"] == "1"),
        "national_illiteracy_rate_in_file": nation_illrat,
        "national_illiteracy_rate_documented": reading.get("documented_national_illiteracy_rate"),
    }
    return out, meta


def main():
    try:
        from canopy.pr_io import (parse_primitive_args, get_input, require_param,
                                  WarningsCollector, primitive_success, primitive_failure,
                                  primitive_error_handling)
    except ImportError:
        from pr_io import (parse_primitive_args, get_input, require_param,
                           WarningsCollector, primitive_success, primitive_failure,
                           primitive_error_handling)
    args = parse_primitive_args()
    w = WarningsCollector("prepare_section203")
    with primitive_error_handling(w):
        p = args["params"]
        try:
            reading = require_param(p, "reading")
            state_fips = str(require_param(p, "state_fips"))
            rows = read_member(get_input(args["inputs"], "puf"), require_param(p, "member"),
                               require_param(p, "encoding"))
            check_header(rows, reading)
            tpath = get_input(args["inputs"], "towns")
            towns = (pd.read_parquet(tpath) if str(tpath).endswith(".parquet")
                     else pd.read_csv(tpath, dtype=str))
            records, meta = records_from(rows, town_codes(towns, state_fips), state_fips, reading)
        except Section203Refused as e:
            primitive_failure("Section 203 records refused", str(e))
        frame = pd.DataFrame(records)
        out = str(args["output"])
        frame.to_parquet(out, index=False) if out.endswith(".parquet") else frame.to_csv(out, index=False)
        meta.update({
            "crs": None, "row_count": len(frame), "column_count": len(frame.columns),
            "variables": list(frame.columns), "id_field": "record_id",
            "spatial_unit": "state, town, split town and American Indian area",
            "determination_date": str(require_param(p, "determination_date")),
            "acs_basis": str(require_param(p, "acs_basis")),
            "interpretation_notes": [
                "Published determinations, modelled by Census from ACS 2015-2019, rounded and partly suppressed; the flags were set on unrounded data and are the evidence of coverage.",
                "Section 203 covers four groups only: American Indian, Alaska Native, Asian American and Spanish heritage. A place with no coverage may still have large limited-English communities in other languages.",
                "The documentation states no confidence level for its margins, so no verdict rests on them (D-263).",
                "An American Indian area's rows are the whole area's, over its American Indian alone or in combination voting-age citizens; they are no town's value and none of our places on their own (D-264).",
            ],
        })
        if meta["national_illiteracy_rate_in_file"] != meta["national_illiteracy_rate_documented"]:
            w.info(f"the nation's illiteracy rate reads {meta['national_illiteracy_rate_in_file']} "
                   f"in the file and {meta['national_illiteracy_rate_documented']} in the "
                   f"documentation's flag rule; the flags are copied as published")
        if meta["census_towns_not_ours"]:
            w.warn(f"{len(meta['census_towns_not_ours'])} Census town(s) match none of ours and are "
                   f"held whole: {', '.join(t['name'] for t in meta['census_towns_not_ours'])}")
        if meta["towns_without_record"]:
            w.warn(f"{len(meta['towns_without_record'])} of the state's towns have no Section 203 "
                   f"record: {', '.join(t['geoid'] for t in meta['towns_without_record'])}")
        w.info(f"{len(frame)} record(s): {meta['rows_by_level']}; {meta['covered_rows']} covered")
        primitive_success(meta, w)


if __name__ == "__main__":
    main()
