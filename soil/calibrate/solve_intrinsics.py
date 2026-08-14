"""
soil/calibrate/solve_intrinsics.py
Kalli A. Hale | August 2026 | rewildingCities

Solve camera intrinsics (K + distortion) from a set of calibration frames.
A Python primitive on the standard contract: reads inputs/output/params,
writes the intrinsics profile, prints metadata + warnings to stdout. The
EnvelopeBuilder wraps this; the primitive does not build its own envelope.

NOTHING capture-specific is hardcoded. Board dimensions, square size, the
detection knobs, and the aspect-ratio flag all arrive as params. A wrong
board size is the classic silent calibration failure, so it is a REQUIRED
param with no default.

The RMS reprojection error, detection count, and principal-point offset are
translated into typed warnings: this is the confidence-to-warning bridge in
miniature, the same pattern the segmentation classifier will use for per-class
confidence.

contract:
  inputs : {"images": "<dir of calibration frames>"}
  output : path to write the intrinsics profile (YAML)
  params : {
    "board_cols": 7, "board_rows": 7,        # REQUIRED: internal corners
    "square_size": 1.0,                        # world units per square
    "square_units": "board_squares",           # "board_squares" or e.g. "mm"
    "detect_downscale_width": 1000,            # speed knob for detection
    "subpix_window": 11,
    "subpix_max_iter": 30, "subpix_eps": 0.001,
    "fix_aspect_ratio": false,                 # phones: leave false
    "min_frames": 5,
    "image_extensions": ["png", "jpg", "jpeg"],
    "rms_warn": 1.0, "rms_critical": 1.5,      # RMS->warning thresholds
    "min_frames_warn": 12,                     # below this, warn (thin set)
    "drop_outlier_mad": 0.0,                    # >0 enables robust outlier drop
    "per_frame_report": true                    # list per-frame error worst-first
  }

Per-frame reprojection error is always computed and reported (worst-first), so a
high whole-set RMS becomes "these specific frames are bad", not a mystery. If
drop_outlier_mad > 0, frames whose per-frame error exceeds
median + drop_outlier_mad * MAD are dropped and the solve is re-run on the
survivors; both the before and after RMS are reported, and every dropped frame
is named in a warning (never a silent choice). The cutoff is median/MAD-based,
not mean/stddev, because the very outliers we are removing would inflate a
mean-based threshold.

standalone (today, to solve site K):
  python soil/calibrate/solve_intrinsics.py \
    '{"images": "plots/michigan/delton/.data/stills/calibration"}' \
    seeds/profiles/delton_iphone14promax_intrinsics.yml \
    '{"board_cols": 7, "board_rows": 7, "square_size": 1.0}'
"""

import os
import glob

import numpy as np
import cv2

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          require_param, WarningsCollector,
                          primitive_success, primitive_error_handling)

PRIMITIVE = "solve_intrinsics"


def build_object_points(cols, rows, square_size):
    """3D board points, row-outer/col-inner to match OpenCV corner order.
    (j, -i, 0) * square_size. Identical layout to Project 4's buildPointSet."""
    pts = np.zeros((rows * cols, 3), np.float32)
    k = 0
    for i in range(rows):
        for j in range(cols):
            pts[k] = (j * square_size, -i * square_size, 0.0)
            k += 1
    return pts


def find_board(gray_full, board, detect_width, subpix):
    """Detect on a downscaled copy for speed, refine at full res for accuracy
    (the findBoardFast trick from Project 4's ar.cpp). Returns corners or None."""
    h, w = gray_full.shape
    s = detect_width / float(w)
    small = cv2.resize(gray_full, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
    found, corners = cv2.findChessboardCorners(small, board, flags)
    if not found:
        return None
    corners = (corners / s).astype(np.float32)
    win, it, eps = subpix
    crit = (cv2.TermCriteria_EPS + cv2.TermCriteria_MAX_ITER, it, eps)
    return cv2.cornerSubPix(gray_full, corners, (win, win), (-1, -1), crit)


def write_profile(path, profile):
    """Write intrinsics as plain YAML (nested lists), NOT cv2.FileStorage.
    Deliberate: Project 4 hit OpenCV 4.13's FileStorage isMap() read bug, so a
    plain, portable YAML anything can read is the safer artifact."""
    import yaml
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(profile, f, sort_keys=False)


def main():
    args = parse_primitive_args()
    w = WarningsCollector(PRIMITIVE)

    with primitive_error_handling(warnings=w):
        images_dir = get_input(args["inputs"], "images")
        out_path = args["output"]
        p = args["params"]

        # --- params: board is REQUIRED (no safe default), rest have defaults
        cols = int(require_param(p, "board_cols"))
        rows = int(require_param(p, "board_rows"))
        board = (cols, rows)
        square_size = float(get_param(p, "square_size", 1.0))
        square_units = get_param(p, "square_units", "board_squares")
        detect_width = int(get_param(p, "detect_downscale_width", 1000))
        subpix = (int(get_param(p, "subpix_window", 11)),
                  int(get_param(p, "subpix_max_iter", 30)),
                  float(get_param(p, "subpix_eps", 0.001)))
        fix_aspect = bool(get_param(p, "fix_aspect_ratio", False))
        min_frames = int(get_param(p, "min_frames", 5))
        exts = get_param(p, "image_extensions", ["png", "jpg", "jpeg"])
        rms_warn = float(get_param(p, "rms_warn", 1.0))
        rms_critical = float(get_param(p, "rms_critical", 1.5))
        min_frames_warn = int(get_param(p, "min_frames_warn", 12))
        drop_outlier_mad = float(get_param(p, "drop_outlier_mad", 0.0))
        per_frame_report = bool(get_param(p, "per_frame_report", True))

        # --- gather frames
        paths = []
        for e in exts:
            paths += glob.glob(os.path.join(images_dir, f"*.{e}"))
            paths += glob.glob(os.path.join(images_dir, f"*.{e.upper()}"))
        paths = sorted(set(paths))
        if not paths:
            from primitive_io import primitive_failure
            primitive_failure("No images", f"No frames in {images_dir}")

        # --- detect
        obj_template = build_object_points(cols, rows, square_size)
        objpoints, imgpoints, used, missed = [], [], [], []
        image_size = None
        for path in paths:
            img = cv2.imread(path)
            if img is None:
                missed.append(os.path.basename(path))
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if image_size is None:
                image_size = (gray.shape[1], gray.shape[0])
            corners = find_board(gray, board, detect_width, subpix)
            if corners is None:
                missed.append(os.path.basename(path))
                continue
            objpoints.append(obj_template.copy())
            imgpoints.append(corners)
            used.append(os.path.basename(path))

        if len(used) < min_frames:
            from primitive_io import primitive_failure
            primitive_failure(
                "Too few detections",
                f"Detected board in {len(used)}/{len(paths)} frames at {board}; "
                f"need >= {min_frames}. Check board dimensions.",
                warnings=w)

        # --- solve (aspect ratio free unless asked)
        flags = cv2.CALIB_FIX_ASPECT_RATIO if fix_aspect else 0
        rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
            objpoints, imgpoints, image_size, None, None, flags=flags)

        # --- per-frame reprojection error: reproject each board with its own
        #     pose and compare to the detected corners. Turns one aggregate RMS
        #     into a diagnosable per-frame list.
        def per_frame_errors(objp, imgp, rv, tv):
            errs = []
            for i in range(len(objp)):
                proj, _ = cv2.projectPoints(objp[i], rv[i], tv[i], K, dist)
                proj = proj.reshape(-1, 2)
                e = float(np.sqrt(np.mean(np.sum(
                    (proj - imgp[i].reshape(-1, 2)) ** 2, axis=1))))
                errs.append(e)
            return errs

        errs = per_frame_errors(objpoints, imgpoints, rvecs, tvecs)
        ranked = sorted(zip(used, errs), key=lambda t: -t[1])
        rms_before_drop = float(rms)
        dropped = []

        if per_frame_report:
            worst = ", ".join(f"{n} {e:.2f}px" for n, e in ranked[:5])
            w.info(f"per-frame RMS (worst first): {worst}")

        # --- optional robust outlier drop, then re-solve on survivors
        if drop_outlier_mad > 0 and len(used) > min_frames:
            arr = np.array(errs)
            med = float(np.median(arr))
            mad = float(np.median(np.abs(arr - med))) or 1e-9
            cutoff = med + drop_outlier_mad * mad
            keep = [i for i, e in enumerate(errs) if e <= cutoff]
            dropped = [used[i] for i in range(len(used)) if i not in keep]

            if dropped and len(keep) >= min_frames:
                objpoints = [objpoints[i] for i in keep]
                imgpoints = [imgpoints[i] for i in keep]
                used = [used[i] for i in keep]
                rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
                    objpoints, imgpoints, image_size, None, None, flags=flags)
                w.warn(f"Dropped {len(dropped)} outlier frame(s) above "
                       f"{cutoff:.2f}px (median {med:.2f} + {drop_outlier_mad}*MAD): "
                       f"{', '.join(dropped)}. RMS {rms_before_drop:.3f} -> {rms:.3f} px")
            elif dropped:
                w.warn(f"Outlier drop would leave < {min_frames} frames; kept all. "
                       f"Worst: {ranked[0][0]} at {ranked[0][1]:.2f}px")

        fx, fy = float(K[0, 0]), float(K[1, 1])
        u0, v0 = float(K[0, 2]), float(K[1, 2])
        cx, cy = image_size[0] / 2.0, image_size[1] / 2.0
        center_off = max(abs(u0 - cx), abs(v0 - cy)) / max(cx, cy)

        # --- confidence-to-warning bridge
        if rms > rms_critical:
            w.critical(f"RMS {rms:.3f} px exceeds {rms_critical}; intrinsics unreliable")
        elif rms > rms_warn:
            w.warn(f"RMS {rms:.3f} px above {rms_warn}; borderline, edge coverage suspect")
        else:
            w.info(f"RMS {rms:.3f} px, sub-pixel; set is trustworthy")

        if len(used) < min_frames_warn:
            w.warn(f"Only {len(used)} frames detected (< {min_frames_warn}); "
                   f"solve may be under-constrained")
        if center_off > 0.10:
            w.warn(f"Principal point {center_off*100:.1f}% off center; "
                   f"check frame-corner coverage")
        if abs(fx / fy - 1) > 0.02:
            w.info(f"fx/fy differ by {abs(fx/fy-1)*100:.1f}%; non-square sensor or thin set")
        if missed:
            w.info(f"{len(missed)} frames did not detect: {', '.join(missed)}")

        # --- write the profile
        profile = {
            "camera_matrix": K.tolist(),
            "distortion_coefficients": dist.ravel().tolist(),
            "image_width": image_size[0],
            "image_height": image_size[1],
            "rms_reproj_px": round(rms, 4),
            "board_internal_corners": [cols, rows],
            "square_size": square_size,
            "square_units": square_units,
            "fix_aspect_ratio": fix_aspect,
            "n_frames_used": len(used),
            "n_frames_total": len(paths),
            "frames_used": used,
            "per_frame_rms_px": {n: round(e, 4) for n, e in ranked},
            "rms_before_drop_px": round(rms_before_drop, 4),
            "frames_dropped": dropped,
            "source_dir": os.path.abspath(images_dir),
        }
        write_profile(out_path, profile)

        # --- metadata to stdout (builder adds semantic_type/provenance)
        primitive_success(
            metadata={
                "n_frames_used": len(used),
                "n_frames_total": len(paths),
                "rms_reproj_px": round(rms, 4),
                "image_width": image_size[0],
                "image_height": image_size[1],
                "fx": round(fx, 3), "fy": round(fy, 3),
                "fx_fy_ratio": round(fx / fy, 5),
                "principal_point": [round(u0, 2), round(v0, 2)],
                "principal_offset_frac": round(center_off, 4),
                "board_internal_corners": [cols, rows],
                "fix_aspect_ratio": fix_aspect,
                "rms_before_drop_px": round(rms_before_drop, 4),
                "n_frames_dropped": len(dropped),
                "worst_frame": {"name": ranked[0][0], "rms_px": round(ranked[0][1], 3)},
            },
            warnings=w)


if __name__ == "__main__":
    main()