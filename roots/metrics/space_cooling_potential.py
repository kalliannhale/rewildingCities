"""
roots/metrics/space_cooling_potential.py  (v1.1.0)
Kalli A. Hale | August 2026 | rewildingCities

Estimate a photographed space's relative cooling potential from the land cover
classified FROM its image (ideally the IPM-rectified ground-plane mask). v1.1.0
weights land cover at the FULL 7-class level, not a blue-green-grey collapse, so
canopy's strong cooling is distinguished from grass's mild cooling instead of
being flattened into one "green" term. That distinction is the whole point: a
forest canopy and a lawn do not cool the same, and standing under a tree proves
it.

IT IS AN ESTIMATE, NOT A MEASUREMENT. The photograph carries no temperature;
this infers a space's cooling character from its composition plus a land-cover/
temperature relationship established from satellite. The output says so.

cooling_index = sum over classes of weight[class] * fraction[class], over the
classified ground (unlabeled excluded; soil is a real class with weight 0). It
is unitless and RELATIVE: only comparisons between spaces mean anything. Lower =
cooler-leaning.

Contract: canopy/pr_io.py (three args, stdout metadata).
  inputs : {"mask": <class-id mask PNG (1..7); use the RECTIFIED mask)>}
  output : space_cooling_estimate JSON
  params : {"cooling_weights": {1:-2,2:-1,3:-0.5,4:0,5:1,6:-1,7:0.5},
            "class_names": {...}, "space_id": <str>, "nodata": 0}
"""
import os
import json

import numpy as np

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "space_cooling_potential"
# Locked weights: canopy strongest cool; soil neutral (forest-floor litter);
# impervious warm; building present but not canceling canopy; water cool.
DEFAULT_WEIGHTS = {1: -2.0, 2: -1.0, 3: -0.5, 4: 0.0, 5: 1.0, 6: -1.0, 7: 0.5}
DEFAULT_NAMES = {1: "canopy", 2: "shrub", 3: "grass", 4: "soil",
                 5: "impervious", 6: "water", 7: "building"}
# readable rollup (context only; the index uses per-class weights)
BGG = {"green": [1, 2, 3], "grey": [5, 7], "blue": [6], "soil": [4]}


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        from PIL import Image
        args = parse_primitive_args()
        mask_path = get_input(args["inputs"], "mask")
        p = args["params"]
        weights = {int(k): float(v) for k, v in
                   (get_param(p, "cooling_weights", DEFAULT_WEIGHTS)).items()}
        names = {int(k): v for k, v in
                 (get_param(p, "class_names", DEFAULT_NAMES)).items()}
        nodata = int(get_param(p, "nodata", 0))
        space_id = get_param(p, "space_id",
                             os.path.splitext(os.path.basename(mask_path))[0])

        mask = np.asarray(Image.open(mask_path).convert("L"))
        classified = mask != nodata
        denom = int(classified.sum())
        if denom == 0:
            primitive_failure("No classified pixels",
                              "mask is entirely nodata", w)

        # per-class fractions over classified ground
        per_class_frac = {}
        for code in sorted(weights):
            per_class_frac[code] = round(float((mask == code).sum()) / denom, 5)

        cooling_index = round(sum(weights[c] * per_class_frac[c]
                                  for c in per_class_frac), 5)

        # readable green/grey/blue/soil rollup (context, not the index basis)
        rollup = {}
        for grp, codes in BGG.items():
            rollup[grp] = round(sum(per_class_frac.get(c, 0.0) for c in codes), 5)

        result = {
            "space_id": space_id,
            "estimate_not_measurement": True,
            "basis": "image-derived composition x satellite land-cover/temperature "
                     "relationship; the photo has no temperature",
            "cooling_index": cooling_index,
            "cooling_index_note": "unitless, relative; lower = cooler-leaning; "
                                  "compare across spaces only",
            "fractions_by_class": {names.get(c, str(c)): per_class_frac[c]
                                   for c in per_class_frac},
            "fractions_rollup": rollup,
            "weights": {names.get(c, str(c)): weights[c] for c in weights},
        }
        out = args["output"]
        d = os.path.dirname(os.path.abspath(out))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(out, "w") as f:
            json.dump(result, f, indent=2)

        dominant = names.get(max(per_class_frac, key=per_class_frac.get), "?")
        w.info(f"{space_id}: dominant {dominant}; green {rollup['green']} "
               f"grey {rollup['grey']} blue {rollup['blue']} soil {rollup['soil']} "
               f"-> cooling index {cooling_index} (relative estimate).")
        primitive_success({"primitive": PRIMITIVE, "output": out, **result}, w)


if __name__ == "__main__":
    main()