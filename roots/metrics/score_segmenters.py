"""
roots/metrics/score_segmenters.py
Kalli A. Hale | August 2026 | rewildingCities

The comparative evaluation from the proposal, factored out of
garden/experiments/compare_segmenters.py into a registered metric so the
segmenter-comparison experiment can run it as an orchestrated step.

Scores one or two segmenter predictions against a ground-truth class mask over
the VALID region (truth != nodata), on three axes: per-class accuracy, mean
intersection-over-union, and Cohen's Kappa. The deep prediction is OPTIONAL, so
this runs RF-only and honestly reports the deep model as absent until it exists.

Predictions and truth must describe the same frame. If a prediction is a
different size (e.g. segment_rf works downscaled), it is resized to the truth
grid with NEAREST-neighbor (labels are never blended) and a warning is emitted.

Contract: canopy/pr_io.py (three args, stdout metadata). EnvelopeBuilder wraps.
  inputs : {"truth": <class-id PNG>, "pred_rf": <mask PNG>,
            "pred_deep": <mask PNG, optional>}
  output : segmenter_comparison JSON
  params : {"nodata": 0, "class_names": {code: name}}
"""
import os
import json

import numpy as np
from PIL import Image

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "score_segmenters"


def _load_mask(path):
    return np.asarray(Image.open(path).convert("L"))


def _match_grid(pred, truth, w):
    """Resize pred to truth's shape with nearest-neighbor if they differ."""
    if pred.shape == truth.shape:
        return pred
    th, tw = truth.shape
    w.warn(f"prediction {pred.shape} != truth {truth.shape}; "
           f"nearest-resized to truth grid.")
    im = Image.fromarray(pred).resize((tw, th), Image.NEAREST)
    return np.asarray(im)


def _cohen_kappa(pred, truth, classes):
    """Agreement corrected for chance. Matches sklearn.cohen_kappa_score for a
    shared label set, implemented here so the primitive carries no hidden dep."""
    n = len(truth)
    if n == 0:
        return None
    po = float(np.mean(pred == truth))
    pe = 0.0
    for c in classes:
        pe += (np.mean(pred == c)) * (np.mean(truth == c))
    return round((po - pe) / (1 - pe), 4) if (1 - pe) > 1e-12 else None


def _evaluate(pred, truth, nodata):
    valid = truth != nodata
    p, t = pred[valid], truth[valid]
    classes = sorted(int(c) for c in np.unique(t))

    per_acc = {}
    per_iou = {}
    for c in classes:
        m = t == c
        nc = int(np.count_nonzero(m))
        per_acc[c] = round(float(np.count_nonzero(p[m] == c) / nc), 4) if nc else None
        inter = int(np.count_nonzero((p == c) & (t == c)))
        union = int(np.count_nonzero((p == c) | (t == c)))
        per_iou[c] = round(inter / union, 4) if union else None

    ious = [v for v in per_iou.values() if v is not None]
    return {
        "overall_accuracy": round(float(np.mean(p == t)), 4) if len(t) else None,
        "per_class_accuracy": per_acc,
        "mean_iou": round(float(np.mean(ious)), 4) if ious else None,
        "per_class_iou": per_iou,
        "cohen_kappa": _cohen_kappa(p, t, classes),
        "n_valid_px": int(len(t)),
    }


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        args = parse_primitive_args()
        inp = args["inputs"]
        truth = _load_mask(get_input(inp, "truth"))
        pred_rf = _load_mask(get_input(inp, "pred_rf"))
        deep_path = get_input(inp, "pred_deep", required=False, must_exist=False)

        p = args["params"]
        nodata = int(get_param(p, "nodata", 0))
        names = get_param(p, "class_names", {}) or {}
        names = {int(k): v for k, v in names.items()}

        pred_rf = _match_grid(pred_rf, truth, w)
        segmenters = {"rf": _evaluate(pred_rf, truth, nodata)}

        if deep_path:
            pred_deep = _match_grid(_load_mask(deep_path), truth, w)
            segmenters["deep"] = _evaluate(pred_deep, truth, nodata)
        else:
            segmenters["deep"] = None
            w.info("no deep prediction supplied; reporting RF only "
                   "(deep model not yet trained).")

        # winner per dimension (skip absent segmenters)
        winners = {}
        for dim in ("overall_accuracy", "mean_iou", "cohen_kappa"):
            scored = {k: v[dim] for k, v in segmenters.items()
                      if v is not None and v.get(dim) is not None}
            winners[dim] = max(scored, key=scored.get) if scored else None

        valid_classes = sorted(int(c) for c in np.unique(truth[truth != nodata]))
        result = {
            "segmenters": segmenters,
            "winners": winners,
            "classes_scored": valid_classes,
            "class_names": {c: names.get(c, str(c)) for c in valid_classes},
            "nodata": nodata,
        }

        out = args["output"]
        d = os.path.dirname(os.path.abspath(out))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(out, "w") as f:
            json.dump(result, f, indent=2)

        primitive_success({"primitive": PRIMITIVE, "output": out, **result}, w)


if __name__ == "__main__":
    main()
