"""
roots/metrics/counterfactual_cooling.py
Kalli A. Hale | August 2026 | rewildingCities

The what-if. Given a space's cooling estimate, apply a hypothetical land-cover
conversion (convert some impervious to canopy, say) and re-score it, so a
community can see the cooling a change would buy before anyone breaks ground.
This is the imagination step: measurement turned into a shared picture of a
cooler version of your own block. (emergent strategy; Butler.)

It is a PROJECTION, doubly so: the base estimate is already an estimate (image
composition x an external relationship, no measured temperature), and the
counterfactual assumes a composition change with everything else held equal.
The delta is a relative direction and rough magnitude, not a promised degree
drop. The output says so.

A transform moves a portion of one class's fraction into another:
  {"from": "impervious", "to": "canopy", "fraction": 1.0}   # convert all of it
  {"from": "grass", "to": "canopy", "fraction": 0.5}        # convert half

Contract: canopy/pr_io.py (three args, stdout metadata).
  inputs : {"estimate": <space_cooling_estimate JSON from space_cooling_potential>}
  output : counterfactual_cooling JSON
  params : {"transforms": [ {from, to, fraction} ... ], "space_id": <str>}
"""
import os
import json

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "counterfactual_cooling"


def index_of(fractions, weights):
    return round(sum(weights.get(k, 0.0) * v for k, v in fractions.items()), 5)


def apply_transforms(fractions, weights, transforms, warns):
    after = dict(fractions)
    applied = []
    for t in transforms:
        src, dst = t.get("from"), t.get("to")
        frac = float(t.get("fraction", 1.0))
        if src not in after:
            warns.warn(f"transform source '{src}' absent in this space; skipped.")
            continue
        if dst not in weights:
            warns.warn(f"transform target '{dst}' has no weight; skipped.")
            continue
        moved = round(after[src] * max(0.0, min(1.0, frac)), 5)
        after[src] = round(after[src] - moved, 5)
        after[dst] = round(after.get(dst, 0.0) + moved, 5)
        applied.append({"from": src, "to": dst, "fraction": frac, "moved": moved})
    return after, applied


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        args = parse_primitive_args()
        est = json.load(open(get_input(args["inputs"], "estimate")))
        p = args["params"]
        transforms = get_param(p, "transforms",
                               [{"from": "impervious", "to": "canopy", "fraction": 1.0}])
        space_id = get_param(p, "space_id", est.get("space_id", "space"))

        fractions = est.get("fractions_by_class")
        weights = est.get("weights")
        if not fractions or not weights:
            primitive_failure("Malformed estimate",
                              "input must be a space_cooling_potential output with "
                              "fractions_by_class and weights", w)

        before_index = index_of(fractions, weights)
        after_fractions, applied = apply_transforms(fractions, weights, transforms, w)
        after_index = index_of(after_fractions, weights)
        delta = round(after_index - before_index, 5)

        result = {
            "space_id": space_id,
            "projection_not_promise": True,
            "basis": "hypothetical composition change, all else held equal, on top "
                     "of an already-estimated cooling index; relative direction "
                     "and rough magnitude, not a measured degree drop",
            "before_index": before_index,
            "after_index": after_index,
            "delta": delta,
            "cooler": delta < 0,
            "transforms_applied": applied,
            "before_composition": fractions,
            "after_composition": after_fractions,
        }
        out = args["output"]
        d = os.path.dirname(os.path.abspath(out))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(out, "w") as f:
            json.dump(result, f, indent=2)

        direction = "cooler" if delta < 0 else "warmer" if delta > 0 else "no change"
        moves = ", ".join(f"{a['moved']} {a['from']}->{a['to']}" for a in applied)
        w.info(f"{space_id}: {before_index} -> {after_index} "
               f"(delta {delta:+}, {direction}) under "
               f"{moves or 'no applicable transforms'}.")
        primitive_success({"primitive": PRIMITIVE, "output": out, **result}, w)


if __name__ == "__main__":
    main()
