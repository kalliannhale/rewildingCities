"""
soil/transform/list_outlet_disagreements.py  |  rewildingCities

list_outlet_disagreements ~ where a group's sources say different things

the third step of reconciling Maine's outlets (Sprint 06, step 8). for every
group holding two or more sources, one row per field and source wherever
the group holds two or more different values. an empty value is not a
disagreement, and like is compared only with like: an office address never
with a named town (D-203). nothing is resolved here; a disagreement is
what the profile's "where sources disagree" shows.

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  grouped   the output of group_outlet_records
Params:  fields    optional list; defaults to group_outlet_records.COMPARED
Output:  disagreements, csv, keyed by (group_id, field, source, source_line) ~
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from group_outlet_records import COMPARED, disagreements, _pr_io  # noqa: E402

KEY = ["group_id", "field", "source", "source_line"]
SPATIAL_UNIT = "outlet_disagreement"


def output_metadata(diff: pd.DataFrame) -> dict:
    return {"data_category": "tabular", "crs": None, "row_count": len(diff),
            "variables": list(diff.columns), "id_fields": KEY,
            "spatial_unit": SPATIAL_UNIT}


def main():
    io = _pr_io()
    args = io.parse_primitive_args()
    w = io.WarningsCollector("list_outlet_disagreements")
    with io.primitive_error_handling(w):
        grouped = pd.read_csv(io.get_input(args["inputs"], "grouped"), dtype=str)
        fields = tuple(io.get_param(args["params"], "fields", None) or COMPARED)
        diff = disagreements(grouped, fields)
        by_field = diff.groupby("field")["group_id"].nunique().to_dict() if len(diff) else {}
        w.info(f"disagreeing groups by field: {by_field}")
        diff.to_csv(args["output"], index=False)
        io.primitive_success(output_metadata(diff), w)


if __name__ == "__main__":
    main()
