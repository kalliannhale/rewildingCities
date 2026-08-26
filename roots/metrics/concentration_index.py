"""
roots/metrics/concentration_index.py
rewildingCities | information domain

Ownership concentration per governance unit, as a Herfindahl-Hirschman Index (HHI).

Contract (pr_io, identical to the R side):
  argv: <inputs_json> <output_path> <params_json>

Inputs:
  outlets: a tabular layer, one row per outlet, carrying a unit field and a
           RESOLVED owner field (semantic_type: formal_outlet)
Params:
  unit_field       (default "feature_id"): the governance-unit column to group by
  owner_field      (default "owner_entity"): the resolved owner column
  unrecorded_label (default "Not recorded"): owner value meaning "unknown owner"
  min_outlets      (default 3): below this, a unit is flagged small_n
  min_coverage     (default 0.5): below this attributed share, unit is low_coverage
Output:
  CSV, one row per unit: unit, n_outlets, n_attributed, coverage, n_owners,
  hhi, top_owner, top_owner_share, status

Honesty note: HHI is computed over ATTRIBUTED outlets only. Treating "Not
recorded" as a single owner would invent concentration or diversity, so instead
we report coverage per unit and flag units where the index is under-determined.
The primitive writes its own CSV and prints metadata; the EnvelopeBuilder wraps
provenance around it.
"""
import csv
from collections import Counter, defaultdict

try:
    from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                              WarningsCollector, primitive_success,
                              primitive_failure, primitive_error_handling)
except ImportError:  # standalone / in-repo path differs
    from pr_io import (parse_primitive_args, get_input, get_param,
                       WarningsCollector, primitive_success,
                       primitive_failure, primitive_error_handling)


def _read_rows(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


def _hhi(counts):
    """HHI on a 0-1 scale from per-owner counts. None if nothing attributed."""
    total = sum(counts)
    if total == 0:
        return None
    return round(sum((c / total) ** 2 for c in counts), 4)


def main():
    args = parse_primitive_args()
    w = WarningsCollector("concentration_index")
    with primitive_error_handling(w):
        path = get_input(args["inputs"], "outlets")
        unit_field = get_param(args["params"], "unit_field", "feature_id")
        owner_field = get_param(args["params"], "owner_field", "owner_entity")
        unrecorded = get_param(args["params"], "unrecorded_label", "Not recorded")
        min_outlets = int(get_param(args["params"], "min_outlets", 3))
        min_coverage = float(get_param(args["params"], "min_coverage", 0.5))

        rows = _read_rows(path)
        if not rows:
            primitive_failure("Empty input", "The outlets table has no rows", w)
        for f in (unit_field, owner_field):
            if f not in rows[0].keys():
                primitive_failure("Missing column",
                                  f"Required column '{f}' not in input", w)

        # group by unit, skipping rows with no unit (statewide / unplaced)
        by_unit = defaultdict(list)
        n_skipped = 0
        for r in rows:
            u = (r.get(unit_field) or "").strip()
            if not u:
                n_skipped += 1
                continue
            by_unit[u].append((r.get(owner_field) or "").strip())

        if n_skipped:
            w.info(f"{n_skipped} rows had no {unit_field} and were excluded "
                   f"(statewide or unplaced).")

        results = []
        for unit in sorted(by_unit):
            owners_all = by_unit[unit]
            n_outlets = len(owners_all)
            attributed = [o for o in owners_all if o and o != unrecorded]
            n_attributed = len(attributed)
            coverage = round(n_attributed / n_outlets, 3) if n_outlets else 0.0
            counts = Counter(attributed)
            n_owners = len(counts)
            hhi = _hhi(list(counts.values()))
            if counts:
                top_owner, top_n = counts.most_common(1)[0]
                top_owner_share = round(top_n / n_attributed, 3)
            else:
                top_owner, top_owner_share = None, None

            if n_attributed == 0:
                status = "no_owner_data"
            elif n_outlets < min_outlets:
                status = "small_n"
            elif coverage < min_coverage:
                status = "low_coverage"
            else:
                status = "success"

            results.append({
                "unit": unit, "n_outlets": n_outlets, "n_attributed": n_attributed,
                "coverage": coverage, "n_owners": n_owners, "hhi": hhi,
                "top_owner": top_owner, "top_owner_share": top_owner_share,
                "status": status,
            })

        # write output
        cols = ["unit", "n_outlets", "n_attributed", "coverage", "n_owners",
                "hhi", "top_owner", "top_owner_share", "status"]
        with open(args["output"], "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=cols)
            wr.writeheader()
            for row in results:
                wr.writerow(row)

        # aggregate warnings, honest about under-determined units
        n_low = sum(1 for r in results if r["status"] == "low_coverage")
        n_small = sum(1 for r in results if r["status"] == "small_n")
        n_none = sum(1 for r in results if r["status"] == "no_owner_data")
        if n_low:
            w.warn(f"{n_low} units have owner coverage below {min_coverage}; "
                   f"their HHI is under-determined.")
        if n_small:
            w.warn(f"{n_small} units have fewer than {min_outlets} outlets; "
                   f"concentration is not meaningful there.")
        if n_none:
            w.warn(f"{n_none} units have no recorded owner; HHI is null.")

        metadata = {
            "data_category": "tabular",
            "n_units": len(results),
            "n_success": sum(1 for r in results if r["status"] == "success"),
            "n_low_coverage": n_low,
            "n_small_n": n_small,
            "n_no_owner_data": n_none,
            "n_rows_skipped": n_skipped,
            "unit_field": unit_field,
            "owner_field": owner_field,
        }
        primitive_success(metadata, w)


if __name__ == "__main__":
    main()
