"""
roots/metrics/segmenter_disagreement.py
Kalli A. Hale | August 2026 | rewildingCities

Where two ways of seeing disagree is a measurement, not a nuisance. Given two
class masks of the same frame (e.g. the local RF and the ADE20K-trained deep
model), this maps where they agree and where they contest the label, and
tabulates what each calls the contested ground. It lifts "no silent choices"
from one model to the ensemble: instead of asking which model is right, it marks
where the meaning of a surface is unstable, so a human knows where to look and a
community is never handed false confidence about its own ground.

Domain-general: it knows nothing about land cover or heat. Any two categorical
rasters of the same scene work.

Outputs an agreement mask (1 = agree, 0 = disagree, over the valid region) and a
summary: agreement rate, and the top confused class-pairs (A says X, B says Y).

Contract: canopy/pr_io.py (three args, stdout metadata).
  inputs : {"a": <class mask PNG>, "b": <class mask PNG>}
  output : disagreement map PNG (255 agree, 0 disagree, nodata stays nodata)
  params : {"nodata": 0, "class_names": {...}, "summary_path": <optional json>}
"""
import os
import json

import numpy as np
from PIL import Image

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "segmenter_disagreement"


def _load(path):
    return np.asarray(Image.open(path).convert("L"))


def _match(a, b, w):
    if a.shape == b.shape:
        return a, b
    th, tw = a.shape
    w.warn(f"masks differ in size {a.shape} vs {b.shape}; "
           f"nearest-resizing b to a.")
    b2 = np.asarray(Image.fromarray(b).resize((tw, th), Image.NEAREST))
    return a, b2


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        args = parse_primitive_args()
        a = _load(get_input(args["inputs"], "a"))
        b = _load(get_input(args["inputs"], "b"))
        p = args["params"]
        nodata = int(get_param(p, "nodata", 0))
        names = {int(k): v for k, v in (get_param(p, "class_names", {}) or {}).items()}

        a, b = _match(a, b, w)
        # valid where BOTH models labelled something (exclude nodata in either)
        valid = (a != nodata) & (b != nodata)
        n_valid = int(valid.sum())
        if n_valid == 0:
            primitive_failure("No jointly-labelled pixels",
                              "the two masks share no valid region", w)

        agree = (a == b) & valid
        agreement_rate = round(float(agree.sum()) / n_valid, 4)

        # agreement map: 255 agree, 0 disagree, over valid; nodata elsewhere
        out_map = np.zeros(a.shape, np.uint8)
        out_map[agree] = 255
        Image.fromarray(out_map, mode="L").save(args["output"])

        # confusion on the contested pixels: which (a_label, b_label) pairs recur
        contested = valid & (a != b)
        pairs = {}
        av, bv = a[contested], b[contested]
        for ca, cb in zip(av.tolist(), bv.tolist()):
            key = f"{names.get(ca, ca)} vs {names.get(cb, cb)}"
            pairs[key] = pairs.get(key, 0) + 1
        top = dict(sorted(pairs.items(), key=lambda kv: kv[1], reverse=True)[:8])

        result = {
            "n_valid_px": n_valid,
            "agreement_rate": agreement_rate,
            "disagreement_rate": round(1 - agreement_rate, 4),
            "top_contested_pairs": top,
        }
        summary_path = get_param(p, "summary_path", None)
        if summary_path:
            d = os.path.dirname(os.path.abspath(summary_path))
            if d:
                os.makedirs(d, exist_ok=True)
            with open(summary_path, "w") as f:
                json.dump(result, f, indent=2)

        w.info(f"agreement {agreement_rate*100:.1f}% over {n_valid} px; "
               f"most contested: {next(iter(top), 'none')}")
        primitive_success({"primitive": PRIMITIVE, "output": args["output"],
                           "summary_path": summary_path, **result}, w)


if __name__ == "__main__":
    main()
