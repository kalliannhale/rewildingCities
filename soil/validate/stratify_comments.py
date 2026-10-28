"""
soil/validate/stratify_comments.py
Kalli A. Hale | October 2026 | rewildingCities

Draw a stratified sample across timeline windows, recording the inclusion
probability of every drawn row.

THE INCLUSION PROBABILITY IS THE POINT. A stratified draw over-represents
quiet windows on purpose; every prevalence estimate computed downstream is
therefore wrong unless it is weighted back. The weight is not a convenience
here, it is the thing that keeps the sample honest, and it has to be carried
on the row rather than reconstructed later from memory of how the draw was
parameterised. This is the class of bug that runs fine and is wrong.

A window that cannot fill its quota does NOT have its shortfall redistributed
to busier windows. Silently topping up from the peak is exactly the bias the
stratification exists to prevent; the shortfall is reported instead.

Contract: canopy/pr_io.py (three args, stdout metadata).
  inputs : {"corpus": <windowed comment_corpus .csv>}
  output : comment_sample (.csv) ~ adds stratum, inclusion_probability, weight
  params : {"n_target": 1500,
            "stratum_field": "window_index",
            "allocation": "equal" | "proportional",
            "stratum_label": "random",
            "seed": 0,
            "min_chars": 0}
"""
import csv
import random

try:
    from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                              WarningsCollector, primitive_success,
                              primitive_failure, primitive_error_handling)
except ImportError:
    from pr_io import (parse_primitive_args, get_input, get_param,
                       WarningsCollector, primitive_success,
                       primitive_failure, primitive_error_handling)

PRIMITIVE = "stratify_comments"


def _allocate(strata, n_target, mode):
    """How many rows to ask of each stratum."""
    keys = sorted(strata, key=lambda k: (len(str(k)), str(k)))
    total = sum(len(strata[k]) for k in keys)
    if mode == "proportional":
        return {k: round(n_target * len(strata[k]) / total) for k in keys}
    base, extra = divmod(n_target, len(keys))
    return {k: base + (1 if i < extra else 0) for i, k in enumerate(keys)}


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        args = parse_primitive_args()
        path = get_input(args["inputs"], "corpus")
        p = args["params"]

        n_target = int(get_param(p, "n_target", 1500))
        field = get_param(p, "stratum_field", "window_index")
        mode = get_param(p, "allocation", "equal")
        label = get_param(p, "stratum_label", "random")
        seed = int(get_param(p, "seed", 0))
        min_chars = int(get_param(p, "min_chars", 0))

        if mode not in ("equal", "proportional"):
            primitive_failure("Bad parameter",
                              f"allocation must be 'equal' or 'proportional', got '{mode}'")

        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            primitive_failure("Empty corpus", f"{path} has no rows")
        if field not in rows[0]:
            primitive_failure("Missing stratum field",
                              f"'{field}' is not a column; window the corpus first")

        eligible = [r for r in rows
                    if int(r.get("n_chars") or 0) >= min_chars]
        if min_chars and len(eligible) < len(rows):
            w.info(
                  f"{len(rows) - len(eligible)} row(s) below min_chars={min_chars} "
                  f"excluded from the frame")
        if not eligible:
            primitive_failure("Empty frame", "no row met the eligibility filter")

        strata = {}
        for r in eligible:
            strata.setdefault(r[field], []).append(r)

        quota = _allocate(strata, n_target, mode)
        rng = random.Random(seed)

        drawn, shortfalls = [], []
        for k in sorted(strata, key=lambda x: (len(str(x)), str(x))):
            pool = strata[k]
            want = quota[k]
            take = min(want, len(pool))
            if take < want:
                shortfalls.append({"stratum": k, "wanted": want,
                                   "available": len(pool)})
            # p = take / N_stratum. A row taken from a thin window carries a
            # LARGER probability and therefore a SMALLER weight: it stands
            # for fewer unseen rows than one taken from a busy window.
            pi = take / len(pool) if pool else 0.0
            for r in rng.sample(pool, take):
                r = dict(r)
                r["stratum"] = f"{label}:{k}"
                r["inclusion_probability"] = round(pi, 8)
                r["weight"] = round(1.0 / pi, 6) if pi else None
                drawn.append(r)

        if not drawn:
            primitive_failure("Empty draw", "no row was drawn")

        if shortfalls:
            # named, not absorbed
            detail = "; ".join(f"{s['stratum']}: wanted {s['wanted']}, "
                               f"had {s['available']}" for s in shortfalls)
            w.warn(
                  f"{len(shortfalls)} stratum/strata could not fill quota "
                  f"({detail}). The shortfall is NOT redistributed; the draw "
                  f"is {len(drawn)} rather than {n_target}.")

        # A sanity check on the weights themselves: the Horvitz-Thompson
        # estimate of the frame size should land near the real frame size.
        # If it does not, the weighting is wrong and everything downstream
        # inherits it.
        ht_total = sum(r["weight"] for r in drawn if r["weight"])
        drift = abs(ht_total - len(eligible)) / len(eligible)
        if drift > 0.01:
            w.critical(
                  f"weight check failed: weights sum to {ht_total:.0f} but the "
                  f"frame holds {len(eligible)} ({drift:.1%} off)")
        else:
            w.info(
                  f"weight check passed: weights sum to {ht_total:.0f} "
                  f"against a frame of {len(eligible)}")

        fields = list(drawn[0].keys())
        with open(args["output"], "w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=fields)
            wr.writeheader()
            wr.writerows(drawn)

        primitive_success({
            "output_path": args["output"],
            "semantic_type": "comment_sample",
            "data_category": "tabular",
            "case_id": drawn[0].get("case_id"),
            "n_drawn": len(drawn),
            "n_target": n_target,
            "n_frame": len(eligible),
            "n_strata": len(strata),
            "allocation": mode,
            "stratum_label": label,
            "seed": seed,
            "shortfalls": shortfalls,
            "ht_frame_estimate": round(ht_total, 1),
            "weight_drift": round(drift, 5),
            "drawn_by_stratum": {str(k): sum(1 for r in drawn
                                             if r["stratum"] == f"{label}:{k}")
                                 for k in sorted(strata,
                                                 key=lambda x: (len(str(x)), str(x)))},
        }, warnings=w)


if __name__ == "__main__":
    main()
