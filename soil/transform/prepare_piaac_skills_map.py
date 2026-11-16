"""
soil/transform/prepare_piaac_skills_map.py
adult literacy at or below PIAAC Level 1, for one state and its counties,
from the U.S. PIAAC Skills Map workbook (D-265).

reads only the columns the crosswalk piaac_skills_map declares, sheet by
sheet, for the declared group (all: adults 16 to 74), and writes one row per
place: the share, its 95 percent credible bounds, its CV, the workbook's own
quality flags decoded in its words, the population the share applies to, and
left_out, that population times the share and times each bound, as NCES's
user guide computes a total.

rules (D-212):
  ~ a column the crosswalk names and the sheet lacks refuses the run, named
  ~ a flag code the workbook's Variable List does not define refuses the run
  ~ a share is never written without its bounds: a row missing either
    refuses the run (NCES asks that every report carry the interval)
  ~ the estimate is model-based, partly predicted from the share of Black and
    Hispanic residents, poverty, education, insurance and service work: the
    rows say so, and no index may combine them with those predictors
    (tests/test_piaac_skills_map.py holds the roots registry and the weights
    to it)
inputs:
  workbook: the Skills Map's downloadable workbook (piaac_skills_map_workbook)
params:
  state_fips: two digits
  reading: the crosswalk, whole
output:  literacy_estimates, one row per place
"""
from __future__ import annotations

import math

import pandas as pd

NOTES = [
    "Model-based small area estimates (hierarchical Bayes), not a test of the people living here: NCES predicted each county's share from ACS 2013-2017 covariates, the shares of adults with less than and more than high school, in poverty, without health insurance, in service occupations, and the shares of Black and of Hispanic residents.",
    "Every share carries its 95 percent credible interval; a share is never reported without it (NCES SAE user guide).",
    "left_out multiplies the 16 to 74 population, from ACS 2013-2017, by the share and its bounds, as the user guide does; the true interval is wider, because the population's own sampling error is not counted.",
    "Never combine these estimates with their own predictors in an index or regression: NCES warns this confounds the result.",
]


class SkillsMapRefused(ValueError):
    """a workbook, or a declaration, that cannot be read as declared."""


def _num(x):
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def _decode(x, table: dict, column: str):
    v = _num(x)
    if v is None:
        return None
    if not v.is_integer() or int(v) not in table:
        raise SkillsMapRefused(f"{column} holds {x!r}, a code the Variable List does not define")
    return table[int(v)]


def rows_from(sheets: dict[str, pd.DataFrame], state_fips: str, reading: dict) -> list[dict]:
    out = []
    oob, cvc = reading["flag_codes"]["out_of_bound"], reading["flag_codes"]["cv"]
    for level, spec in reading["sheets"].items():
        frame = sheets.get(spec["sheet"])
        if frame is None:
            raise SkillsMapRefused(f"the workbook has no sheet {spec['sheet']!r}")
        cols = spec["columns"]
        needed = [spec["key"], spec["name"], reading["group_column"], *cols.values()]
        absent = [c for c in needed if c not in frame.columns]
        if absent:
            raise SkillsMapRefused(f"sheet {spec['sheet']} lacks {', '.join(absent)}")
        keys = frame[spec["key"]].map(lambda k: str(int(float(k))).zfill(spec["key_width"]))
        pick = frame[keys.str.startswith(state_fips) & (frame[reading["group_column"]] == reading["group"])]
        for i, r in pick.iterrows():
            share, lo, hi = (_num(r[cols["share"]]), _num(r[cols["lower"]]), _num(r[cols["upper"]]))
            code = keys[i]
            if None in (share, lo, hi):
                raise SkillsMapRefused(f"{code} has a share without both bounds")
            pop = _num(r[cols["population"]])
            row = {
                "record_id": f"{level}:{code}", "level": level,
                "unit_authority": "us_census_geoid", "unit_code": code,
                "name": str(r[spec["name"]]), "group": reading["group"],
                "measure": reading["measure"], "share": share,
                "lower": lo, "upper": hi, "confidence": reading["confidence"],
                "cv": _num(r[cols["cv"]]),
                "share_flag": _decode(r[cols["share_flag"]], oob, cols["share_flag"]) if "share_flag" in cols else None,
                "lower_flag": _decode(r[cols["lower_flag"]], oob, cols["lower_flag"]) if "lower_flag" in cols else None,
                "upper_flag": _decode(r[cols["upper_flag"]], oob, cols["upper_flag"]) if "upper_flag" in cols else None,
                "cv_flag": _decode(r[cols["cv_flag"]], cvc, cols["cv_flag"]) if "cv_flag" in cols else None,
                "population_16_74": pop,
                "left_out": pop * share if pop is not None else None,
                "left_out_lower": pop * lo if pop is not None else None,
                "left_out_upper": pop * hi if pop is not None else None,
                "estimate_kind": "model_based", "period": reading["period"],
            }
            out.append(row)
    return out


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
    w = WarningsCollector("prepare_piaac_skills_map")
    with primitive_error_handling(w):
        p = args["params"]
        try:
            reading = require_param(p, "reading")
            state_fips = str(require_param(p, "state_fips"))
            wanted = [s["sheet"] for s in reading["sheets"].values()]
            sheets = pd.read_excel(get_input(args["inputs"], "workbook"), sheet_name=wanted,
                                   engine="openpyxl")
            rows = rows_from(sheets, state_fips, reading)
        except SkillsMapRefused as e:
            primitive_failure("Skills Map estimates refused", str(e))
        frame = pd.DataFrame(rows)
        out = str(args["output"])
        frame.to_parquet(out, index=False) if out.endswith(".parquet") else frame.to_csv(out, index=False)
        flagged = [r["record_id"] for r in rows
                   if any(r[k] for k in ("share_flag", "lower_flag", "upper_flag", "cv_flag"))]
        if flagged:
            w.warn(f"{len(flagged)} estimate(s) carry a quality flag: {', '.join(flagged)}")
        w.info(f"{len(rows)} place(s) read for group {reading['group']}")
        primitive_success({
            "crs": None, "row_count": len(frame), "column_count": len(frame.columns),
            "variables": list(frame.columns), "id_field": "record_id",
            "spatial_unit": "state and county", "flagged": flagged,
            "interpretation_notes": NOTES,
        }, w)


if __name__ == "__main__":
    main()
