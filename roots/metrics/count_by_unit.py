"""
roots/metrics/count_by_unit.py  |  rewildingCities
Count placed features per governance unit, emitting a row for EVERY unit in the
reference (zeros included) so absence is visible, not silently dropped. Reusable:
counts any node type per any unit level.

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:
  features: a placed table (output of geocode_to_unit), carrying a unit key
  units:    governance_unit reference (feature_id, unit_name, unit_level, parent_name)
Params:
  unit_field      (default "feature_id"): the unit key on both tables
  unit_name_field (default "unit_name"):  human name to carry through
  target_level    (default "county"):     which unit level to enumerate
Output: one row per unit at target_level: feature_id, unit_name, n_features.
"""
import csv
from collections import Counter
try:
    from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                              WarningsCollector, primitive_success, primitive_failure,
                              primitive_error_handling)
except ImportError:
    from pr_io import (parse_primitive_args, get_input, get_param,
                       WarningsCollector, primitive_success, primitive_failure,
                       primitive_error_handling)

def _read(p):
    with open(p, newline="", encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))

def main():
    args = parse_primitive_args()
    w = WarningsCollector("count_by_unit")
    with primitive_error_handling(w):
        features = _read(get_input(args["inputs"], "features"))
        units = _read(get_input(args["inputs"], "units"))
        unit_field = get_param(args["params"], "unit_field", "feature_id")
        name_field = get_param(args["params"], "unit_name_field", "unit_name")
        target = get_param(args["params"], "target_level", "county")

        # the full universe of units at target_level (this is what makes zeros appear)
        universe = [(u.get("feature_id"), u.get("unit_name"))
                    for u in units if (u.get("unit_level") or "").strip() == target]
        if not universe:
            primitive_failure("No units", f"Reference has no units at level '{target}'", w)

        # count placed features; anything with an empty unit key is unplaced
        placed = Counter()
        n_unplaced = 0
        for r in features:
            key = (r.get(unit_field) or "").strip()
            if key:
                placed[key] += 1
            else:
                n_unplaced += 1

        rows = [{"feature_id": fid, "unit_name": nm, "n_features": placed.get(fid, 0)}
                for fid, nm in universe]
        rows.sort(key=lambda x: (-x["n_features"], x["unit_name"]))

        with open(args["output"], "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=["feature_id", "unit_name", "n_features"])
            wr.writeheader()
            for r in rows:
                wr.writerow(r)

        n_zero = sum(1 for r in rows if r["n_features"] == 0)
        if n_zero:
            w.info(f"{n_zero} of {len(rows)} units have no documented feature "
                   f"(shown as zero, not omitted).")
        if n_unplaced:
            w.warn(f"{n_unplaced} features had no unit key and were not counted "
                   f"(unplaced or statewide).")

        primitive_success({"data_category": "tabular", "n_units": len(rows),
                           "n_units_zero": n_zero, "n_features_placed": sum(placed.values()),
                           "n_features_unplaced": n_unplaced, "target_level": target}, w)

if __name__ == "__main__":
    main()
