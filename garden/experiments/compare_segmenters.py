"""
garden/experiments/compare_segmenters.py
Kalli A. Hale | August 2026 | rewildingCities

The comparative evaluation the proposal requires (deliverable, section 8):
score two segmenters (classical RF and the deep model) against a ground-truth
mask across three dimensions, per-class accuracy, mean intersection-over-union,
and Cohen's Kappa. An EXPERIMENT, not a primitive: it reads segmenter outputs
and renders the comparison.

All three masks are counted over the same VALID region (truth != nodata), so a
class missing from the ground truth cannot distort the scores.
"""
import numpy as np


def per_class_accuracy(pred, truth, classes):
    """Fraction of each ground-truth class's pixels predicted correctly."""
    out = {}
    for c in classes:
        m = truth == c
        n = int(np.count_nonzero(m))
        out[c] = round(float(np.count_nonzero(pred[m] == c) / n), 4) if n else None
    return out


def mean_iou(pred, truth, classes):
    """Mean intersection-over-union across classes present in the truth."""
    ious = {}
    for c in classes:
        inter = int(np.count_nonzero((pred == c) & (truth == c)))
        union = int(np.count_nonzero((pred == c) | (truth == c)))
        ious[c] = round(inter / union, 4) if union else None
    present = [v for v in ious.values() if v is not None]
    return (round(float(np.mean(present)), 4) if present else None), ious


def cohen_kappa(pred, truth):
    """Cohen's Kappa: agreement corrected for chance."""
    from sklearn.metrics import cohen_kappa_score
    return round(float(cohen_kappa_score(truth, pred)), 4)


def evaluate(pred, truth, nodata=0):
    """Score one prediction against truth over the valid region."""
    valid = truth != nodata
    p, t = pred[valid], truth[valid]
    classes = sorted(int(c) for c in np.unique(t))
    miou, per_iou = mean_iou(p, t, classes)
    return {
        "overall_accuracy": round(float(np.mean(p == t)), 4),
        "per_class_accuracy": per_class_accuracy(p, t, classes),
        "mean_iou": miou,
        "per_class_iou": per_iou,
        "cohen_kappa": cohen_kappa(p, t),
        "n_valid": int(np.count_nonzero(valid)),
    }


def compare(pred_rf, pred_deep, truth, nodata=0, names=None):
    """Compare both segmenters against truth. Returns a scored dict per model
    plus the winner on each dimension. pred_deep may be None (not yet trained)."""
    names = names or {}
    result = {"random_forest": evaluate(pred_rf, truth, nodata)}
    if pred_deep is not None:
        result["deep_model"] = evaluate(pred_deep, truth, nodata)
        result["winner"] = {
            dim: ("deep_model"
                  if (result["deep_model"][dim] or 0) > (result["random_forest"][dim] or 0)
                  else "random_forest")
            for dim in ("overall_accuracy", "mean_iou", "cohen_kappa")}
    return result


def report(result):
    dims = ("overall_accuracy", "mean_iou", "cohen_kappa")
    print(f"{'metric':20}{'random_forest':>16}", end="")
    if "deep_model" in result:
        print(f"{'deep_model':>16}", end="")
    print()
    for d in dims:
        print(f"{d:20}{result['random_forest'][d]:>16}", end="")
        if "deep_model" in result:
            print(f"{result['deep_model'][d]:>16}", end="")
        print()
    if "winner" in result:
        print("\nwinner per dimension:", result["winner"])