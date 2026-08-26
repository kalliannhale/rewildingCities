"""
soil/validate/resolve_ownership.py  |  rewildingCities
Resolve raw owner strings to canonical entities via an auditable crosswalk.
Mechanical normalization (case/whitespace) is automatic; every real merge is a
crosswalk row with a confidence flag; uncertain inferences stay flagged; near
-duplicates that are NOT in the crosswalk are SUGGESTED, never silently merged.

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:
  outlets:   table with a raw owner field
  crosswalk: raw,owner_entity,confidence,note
Params:
  owner_field      (default "Ownership")
  output_field     (default "owner_entity")
  confidence_field (default "owner_confidence")
  unrecorded_label (default "Not recorded")
  suggest_fuzzy    (default True)
  fuzzy_cutoff     (default 0.88)
Output: the outlet rows plus owner_entity and owner_confidence; raw preserved.
"""
import csv, difflib, re
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

def _normkey(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower()).strip(" .,;")

def main():
    args = parse_primitive_args()
    w = WarningsCollector("resolve_owner_entity")
    with primitive_error_handling(w):
        outlets = _read(get_input(args["inputs"], "outlets"))
        xw_rows = _read(get_input(args["inputs"], "crosswalk"))
        owner_field = get_param(args["params"], "owner_field", "Ownership")
        out_field = get_param(args["params"], "output_field", "owner_entity")
        conf_field = get_param(args["params"], "confidence_field", "owner_confidence")
        unrecorded = get_param(args["params"], "unrecorded_label", "Not recorded")
        suggest = bool(get_param(args["params"], "suggest_fuzzy", True))
        cutoff = float(get_param(args["params"], "fuzzy_cutoff", 0.88))

        xw = {_normkey(r["raw"]): (r["owner_entity"].strip(),
                                   (r.get("confidence") or "high").strip())
              for r in xw_rows}

        results, conf_counts, as_recorded = [], Counter(), set()
        for r in outlets:
            raw = (r.get(owner_field) or "").strip()
            if not raw:
                ent, conf = unrecorded, "none"
            else:
                k = _normkey(raw)
                if k in xw:
                    ent, conf = xw[k]
                else:
                    ent, conf = raw, "as_recorded"
                    as_recorded.add(ent)
            conf_counts[conf] += 1
            row = dict(r); row[out_field] = ent; row[conf_field] = conf
            results.append(row)

        # SUGGEST near-duplicates among the as-recorded entities; do not merge
        suggestions = []
        if suggest:
            names = sorted(as_recorded)
            seen = set()
            for n in names:
                for m in difflib.get_close_matches(n, names, n=3, cutoff=cutoff):
                    if m != n and (m, n) not in seen:
                        seen.add((n, m)); suggestions.append(f"{n!r} ~ {m!r}")

        cols = list(outlets[0].keys()) + [out_field, conf_field] if outlets else []
        with open(args["output"], "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=cols); wr.writeheader()
            for row in results: wr.writerow(row)

        if conf_counts.get("provisional"):
            w.warn(f"{conf_counts['provisional']} rows resolved by a PROVISIONAL "
                   f"crosswalk entry (inference, not confirmed); keep flagged.")
        w.info(f"resolved: " + ", ".join(f"{k}={v}" for k, v in conf_counts.items()))
        if suggestions:
            w.info("possible merges to add to the crosswalk (not applied): "
                   + "; ".join(suggestions))

        primitive_success({"data_category": "vector", "n_total": len(results),
                           "by_confidence": dict(conf_counts),
                           "n_suggestions": len(suggestions)}, w)

if __name__ == "__main__":
    main()
