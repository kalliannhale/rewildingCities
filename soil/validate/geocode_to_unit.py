"""
soil/validate/geocode_to_unit.py  |  rewildingCities
Assign each node (outlet) to a canonical governance_unit feature_id by matching
its place-name field. No place names are hardcoded here; they arrive in `units`.

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:
  outlets: table to place (e.g. formal_outlet), carrying place-name fields
  units:   governance_unit reference (feature_id, unit_name, unit_level, parent_name)
Params:
  target_level   (default "county"): unit level to assign
  name_field     (default "County"):  outlet column matched at target_level
  fallback_field (default None):      finer column (e.g. Town) used when name_field
                                      is blank/unmatched; its parent at target_level is taken
  fuzzy          (default True):      allow close-match on typos
  fuzzy_cutoff   (default 0.8)
Output: the outlet rows plus feature_id, unit_name, match_source.
"""
import csv, difflib
try:
    from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                              WarningsCollector, primitive_success, primitive_failure,
                              primitive_error_handling)
except ImportError:
    from pr_io import (parse_primitive_args, get_input, get_param,
                       WarningsCollector, primitive_success, primitive_failure,
                       primitive_error_handling)

def _read(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))

def _norm(s):
    if not s: return ""
    s = s.split("/")[0].split(";")[0].strip()   # take primary of a list
    return s.title()

def main():
    args = parse_primitive_args()
    w = WarningsCollector("geocode_to_unit")
    with primitive_error_handling(w):
        outlets = _read(get_input(args["inputs"], "outlets"))
        units = _read(get_input(args["inputs"], "units"))
        target = get_param(args["params"], "target_level", "county")
        name_field = get_param(args["params"], "name_field", "County")
        fallback_field = get_param(args["params"], "fallback_field", None)
        fuzzy = bool(get_param(args["params"], "fuzzy", True))
        cutoff = float(get_param(args["params"], "fuzzy_cutoff", 0.8))

        # index the reference
        target_by_name, parent_names = {}, {}
        finer_parent = {}   # finer unit_name -> parent unit_name
        for u in units:
            lvl = (u.get("unit_level") or "").strip()
            nm = _norm(u.get("unit_name"))
            if lvl == target:
                target_by_name[nm] = {"feature_id": u.get("feature_id"), "unit_name": u.get("unit_name")}
            else:
                finer_parent[nm] = _norm(u.get("parent_name"))
        target_names = list(target_by_name)

        def match_target(raw):
            n = _norm(raw)
            if not n: return None, None
            if n in target_by_name: return n, "name"
            if fuzzy:
                m = difflib.get_close_matches(n, target_names, n=1, cutoff=cutoff)
                if m: return m[0], "name_fuzzy"
            return None, None

        finer_names = list(finer_parent)
        def match_fallback(raw):
            n = _norm(raw)
            if not n: return None, None
            hit = n if n in finer_parent else (difflib.get_close_matches(n, finer_names, n=1, cutoff=cutoff)[0]
                                               if fuzzy and difflib.get_close_matches(n, finer_names, n=1, cutoff=cutoff) else None)
            if hit and finer_parent[hit] in target_by_name:
                return finer_parent[hit], ("fallback_fuzzy" if hit != n else "fallback")
            return None, None

        results, counts = [], {"name":0,"name_fuzzy":0,"fallback":0,"fallback_fuzzy":0,"unmatched":0}
        for r in outlets:
            key, src = match_target(r.get(name_field, ""))
            if key is None and fallback_field:
                key, src = match_fallback(r.get(fallback_field, ""))
            if key is None:
                fid, uname, src = "", "", "unmatched"
            else:
                fid, uname = target_by_name[key]["feature_id"], target_by_name[key]["unit_name"]
            counts[src] += 1
            row = dict(r); row.update(feature_id=fid, unit_name=uname, match_source=src)
            results.append(row)

        cols = list(outlets[0].keys()) + ["feature_id","unit_name","match_source"] if outlets else []
        with open(args["output"], "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=cols); wr.writeheader()
            for row in results: wr.writerow(row)

        if counts["unmatched"]:
            w.warn(f"{counts['unmatched']} rows could not be matched to a {target} "
                   f"(statewide or unresolved); left unplaced.")
        if counts["name_fuzzy"] or counts["fallback_fuzzy"]:
            w.info(f"{counts['name_fuzzy']+counts['fallback_fuzzy']} rows matched by fuzzy "
                   f"(likely typos); review recommended.")
        if counts["fallback"] or counts["fallback_fuzzy"]:
            w.info(f"{counts['fallback']+counts['fallback_fuzzy']} rows recovered via {fallback_field}.")

        primitive_success({"data_category":"vector","n_total":len(results),
                           "n_matched":len(results)-counts["unmatched"],
                           "by_source":counts,"target_level":target}, w)

if __name__ == "__main__":
    main()
