"""
garden/experiments/falsification_test.py
Kalli A. Hale | August 2026 | rewildingCities

The kill switch. Tests the claim: image-plane surface composition is a biased
estimator of ground-plane composition; the bias is predictable from camera
geometry; and IPM corrects it.

This is an EXPERIMENT, not a primitive: it composes the geometry primitives
(recover_ground_pose -> rectify_to_ground) and scores the result. It does not
emit an Envelope of its own; it reads primitive outputs and renders a verdict.

Everything is counted in ONE currency: label masks. Raw, rectified, and ground
truth are all class rasters, counted by the same function over the same valid
region, so the comparison is apples-to-apples-to-apples and a class clipped at
the frustum edge cannot masquerade as an error.

Verdict logic: rectified composition should be closer to ground truth than raw
image-plane composition. If it is not, the correction is not doing the work
claimed of it, and the test reports that honestly. A falsification test that can
only pass is not a falsification test.

Inputs (production):
  scene_image : photo with the board flat on the ground
  intrinsics  : solved camera profile (K, distortion)
  scene_mask  : hand-annotated label mask of scene_image (image-plane)
  truth_mask  : ground-truth label mask in BIRD'S-EYE ground-plane space,
                over the same ground extent used for rectification
Params:
  board dims, square_size, output_scale, ground_extent, class names, nodata
"""

import numpy as np
import cv2

# geometry primitives (import their core functions, not the CLI wrappers)
from soil.calibrate.recover_ground_pose import find_board, build_object_points
from soil.transform.rectify_to_ground import build_ground_homography, rectify


# ---- the single counting function, used for all three masks ----

def class_fractions(mask, class_ids, nodata):
    """Fraction of each class over the VALID (non-nodata) pixels of a mask.
    One function for raw, rectified, and truth, so all three are counted
    identically."""
    valid = mask != nodata
    total = int(np.count_nonzero(valid))
    if total == 0:
        return {c: 0.0 for c in class_ids}, 0
    return ({c: np.count_nonzero((mask == c) & valid) / total for c in class_ids},
            total)


def total_abs_error(frac_a, frac_b, class_ids):
    """Sum of per-class absolute differences (L1). Zero means identical."""
    return sum(abs(frac_a[c] - frac_b[c]) for c in class_ids)


def run_falsification(scene_mask, truth_mask, K, dist, rvec, tvec,
                      ground_extent, output_scale, class_ids, nodata,
                      min_coverage=0.5):
    """Score the claim. Returns raw/rectified/truth fractions, their errors,
    and the verdict. Pure over arrays, so the synthetic test drives it directly.

    A coverage guard makes the verdict honest: if the rectified output covers
    too little of the ground extent, its fractions are counted over an
    unrepresentative sliver and cannot be trusted, so the verdict is
    'inconclusive' rather than a spurious pass. This closes the hole where a
    broken pose warps everything out of frame and the leftover fragment happens
    to look correct."""

    # 1. RAW: image-plane composition, counted straight from the scene mask
    raw_frac, raw_n = class_fractions(scene_mask, class_ids, nodata)

    # 2. RECTIFIED: warp the SAME label mask to bird's-eye, nearest-neighbor
    H = build_ground_homography(K, rvec, tvec)
    rect_mask, meta = rectify(scene_mask, H, ground_extent, output_scale,
                              is_mask=True, nodata=nodata)
    rect_frac, rect_n = class_fractions(rect_mask, class_ids, nodata)

    # 3. TRUTH: ground-plane composition, counted the same way
    truth_frac, truth_n = class_fractions(truth_mask, class_ids, nodata)

    # 4. SCORE against truth, with the coverage guard
    raw_err = total_abs_error(raw_frac, truth_frac, class_ids)
    rect_err = total_abs_error(rect_frac, truth_frac, class_ids)
    coverage = meta["valid_fraction"]
    improved = rect_err < raw_err

    if coverage < min_coverage:
        verdict = "inconclusive"          # rectified fractions untrustworthy
    elif improved:
        verdict = "supported"
    else:
        verdict = "kill_switch"           # rectification did not beat raw

    return {
        "raw_fractions": raw_frac,
        "rectified_fractions": rect_frac,
        "truth_fractions": truth_frac,
        "raw_error_L1": raw_err,
        "rectified_error_L1": rect_err,
        "rectification_improved": bool(improved),
        "verdict": verdict,
        "min_coverage": min_coverage,
        "error_reduction": raw_err - rect_err,
        "valid_pixels": {"raw": raw_n, "rectified": rect_n, "truth": truth_n},
        "rectified_coverage": coverage,
        "rectified_mask": rect_mask,
    }


def report(result, class_names, verbose=True):
    """Human-readable verdict."""
    if verbose:
        ids = list(class_names.keys())
        header = f"{'':12}" + "".join(f"{class_names[c]:>14}" for c in ids)
        print(header)
        for label, key in [("TRUE", "truth_fractions"),
                           ("RAW image", "raw_fractions"),
                           ("RECTIFIED", "rectified_fractions")]:
            row = f"{label:12}" + "".join(f"{result[key][c]:>14.3f}" for c in ids)
            print(row)
        print(f"\nraw error (L1)       : {result['raw_error_L1']:.4f}")
        print(f"rectified error (L1) : {result['rectified_error_L1']:.4f}")
        print(f"error reduction      : {result['error_reduction']:+.4f}")
        print(f"rectified coverage   : {result['rectified_coverage']}")
    messages = {
        "inconclusive": (
            f"INCONCLUSIVE: rectified coverage {result['rectified_coverage']:.2f} "
            f"below {result['min_coverage']}; fractions counted over too small a "
            f"region to trust. Pose or extent is likely wrong."),
        "kill_switch": (
            "KILL SWITCH: rectification did NOT beat raw; the correction is not "
            "doing the claimed work."),
        "supported": (
            "rectification reduced the error toward ground truth "
            "(claim supported on this case)."),
    }
    print(f"\nVERDICT: {messages[result['verdict']]}")
    return result["verdict"]
