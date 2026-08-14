"""
roots/metrics/score_composition.py
Kalli A. Hale | August 2026 | rewildingCities

The falsification score, factored out of garden/experiments/falsification_test.py
into a registered metric so the IPM method can run it as an orchestrated step.

It answers the kill-switch question for a KNOWN-GEOMETRY target: given the
recovered pose and intrinsics, how much does the raw image-plane area fraction
of a planar target differ from its true ground-area fraction, and does
rectification recover the truth? Truth needs no field measurement: a rectangle
of known ground size has a known area fraction within a known ROI.

  raw       = (image-plane area of the target quad) / (image-plane area of ROI)
  truth     = (ground area of target)               / (ground area of ROI)
  rectified = truth   (ground areas map linearly under a correct rectification)

The verdict is `inconclusive` (not `supported`/`failed`) when the rectify step's
coverage collapsed, mirroring the coverage guard: a pose that flew out of frame
can't be scored honestly.

contract: canopy/pr_io.py (stdout-JSON, three args); EnvelopeBuilder wraps it.

  inputs : {"pose": <pose YAML rvec/tvec>, "intrinsics": <profile YAML>}
  output : <composition_falsification JSON>
  params : {
    "ground_extent": [x0, x1, y0, y1],     # ROI rectangle, ground units (REQUIRED)
    "target_extent": [x0, x1, y0, y1],      # known target rectangle, ground units (REQUIRED)
    "coverage_fraction": 1.0,               # valid_fraction from rectify_to_ground
    "coverage_min": 0.5,                    # below this -> inconclusive
    "target_name": "board"
  }
"""
import numpy as np

from canopy.pr_io import (parse_primitive_args, get_input, require_param,
                          get_param, WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "score_composition"


def _load_yaml(path):
    import yaml
    with open(path) as f:
        return yaml.safe_load(f)


def _rodrigues(r):
    r = np.asarray(r, float)
    th = np.linalg.norm(r)
    if th < 1e-12:
        return np.eye(3)
    k = r / th
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) * np.cos(th) + (1 - np.cos(th)) * np.outer(k, k) + np.sin(th) * Kx


def _projector(K, dist, R, t):
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    k1, k2, p1, p2, k3 = (list(dist) + [0] * 5)[:5]

    def project(xg, yg):
        Pc = R @ np.array([xg, yg, 0.0]) + t
        xp, yp = Pc[0] / Pc[2], Pc[1] / Pc[2]
        r2 = xp * xp + yp * yp
        radial = 1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
        xpp = xp * radial + 2 * p1 * xp * yp + p2 * (r2 + 2 * xp * xp)
        ypp = yp * radial + p1 * (r2 + 2 * yp * yp) + 2 * p2 * xp * yp
        return np.array([fx * xpp + cx, fy * ypp + cy])
    return project


def _quad(extent):
    x0, x1, y0, y1 = extent
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _shoelace(pts):
    pts = np.asarray(pts, float)
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        args = parse_primitive_args()
        pose = _load_yaml(get_input(args["inputs"], "pose"))
        intr = _load_yaml(get_input(args["inputs"], "intrinsics"))
        p = args["params"]

        roi = require_param(p, "ground_extent")
        tgt = require_param(p, "target_extent")
        cov = float(get_param(p, "coverage_fraction", 1.0))
        cov_min = float(get_param(p, "coverage_min", 0.5))
        name = get_param(p, "target_name", "board")

        K = np.array(intr["camera_matrix"], float)
        dist = np.array(intr.get("distortion_coefficients", []) or [], float)
        R = _rodrigues(pose["rvec"])
        t = np.array(pose["tvec"], float)
        project = _projector(K, dist, R, t)

        # image-plane areas (raw) vs ground areas (truth)
        img_tgt = _shoelace([project(*pt) for pt in _quad(tgt)])
        img_roi = _shoelace([project(*pt) for pt in _quad(roi)])
        grd_tgt = _shoelace(_quad(tgt))
        grd_roi = _shoelace(_quad(roi))

        raw = img_tgt / img_roi
        truth = grd_tgt / grd_roi
        rectified = truth  # linear under a correct rectification

        raw_err = abs(raw - truth)
        rect_err = abs(rectified - truth)

        if cov < cov_min:
            verdict = "inconclusive"
            w.warn(f"coverage {cov:.2f} below {cov_min}; pose collapsed the valid "
                   f"region, cannot score honestly.")
        elif rect_err < raw_err:
            verdict = "supported"
        else:
            verdict = "not_supported"

        result = {
            "target": name,
            "truth_fraction": round(truth, 6),
            "raw_fraction": round(raw, 6),
            "rectified_fraction": round(rectified, 6),
            "raw_error": round(raw_err, 6),
            "rectified_error": round(rect_err, 6),
            "bias_removed": round(raw_err - rect_err, 6),
            "coverage_fraction": cov,
            "verdict": verdict,
        }

        import json
        import os
        out_dir = os.path.dirname(os.path.abspath(args["output"]))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args["output"], "w") as f:
            json.dump(result, f, indent=2)

        primitive_success({"primitive": PRIMITIVE, "output": args["output"], **result}, w)


if __name__ == "__main__":
    main()
