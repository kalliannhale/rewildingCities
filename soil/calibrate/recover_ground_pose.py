"""
soil/calibrate/recover_ground_pose.py
Kalli A. Hale | August 2026 | rewildingCities

Recover the pose of the ground plane from a flat board in a scene photo.
Detects the board, runs solvePnP against the known intrinsics, and writes the
rvec/tvec that rectify_to_ground consumes. This is what turns a scene frame
into a rectifiable one: the board defines the ground plane.

Python primitive on the standard contract; the EnvelopeBuilder wraps it.

The reprojection error is surfaced as a typed warning (the confidence-to-warning
bridge): a low error means the pose is trustworthy, a high one means any
rectification built on it will be wrong. If the board is not detected at all,
the primitive fails loudly rather than writing a garbage pose, because a frame
with no visible board cannot anchor the ground plane.

Flip note: a symmetric board (equal internal corners per side, e.g. 7x7) has a
180-degree orientation ambiguity, so solvePnP may return a pose flipped from how
the board was actually laid. The primitive flags this so the rectified image can
be sanity-checked. An asymmetric board removes the ambiguity entirely.

contract:
  inputs : {"image": <scene PNG with board flat>, "intrinsics": <profile YAML>}
  output : pose YAML {rvec: [..], tvec: [..], ...}
  params : {
    "board_cols": 7, "board_rows": 7,      # REQUIRED: internal corners
    "square_size": 1.0,
    "detect_downscale_width": 1000,
    "subpix_window": 11, "subpix_max_iter": 30, "subpix_eps": 0.001,
    "reproj_warn": 1.0, "reproj_critical": 2.0
  }
"""

import numpy as np
import cv2

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          require_param, WarningsCollector,
                          primitive_success, primitive_failure,
                          primitive_error_handling)

PRIMITIVE = "recover_ground_pose"


def build_object_points(cols, rows, square_size):
    """Board points (j, -i, 0) * square_size, row-outer/col-inner to match
    OpenCV corner order. Same layout as solve_intrinsics and Project 4."""
    pts = np.zeros((rows * cols, 3), np.float32)
    k = 0
    for i in range(rows):
        for j in range(cols):
            pts[k] = (j * square_size, -i * square_size, 0.0)
            k += 1
    return pts


def find_board(gray_full, board, detect_width, subpix):
    # 1) Robust detector first: findChessboardCornersSB (OpenCV 4.x), full res.
    #    Handles small, dim, tilted, cluttered boards the classic one misses,
    #    and returns sub-pixel corners directly.
    if hasattr(cv2, "findChessboardCornersSB"):
        try:
            flags_sb = cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY
            found, corners = cv2.findChessboardCornersSB(gray_full, board, flags=flags_sb)
            if found:
                return corners.astype(np.float32)
        except cv2.error:
            pass
    # 2) Fallback: classic detector, FULL res first, then downscaled.
    win, it, eps = subpix
    crit = (cv2.TermCriteria_EPS + cv2.TermCriteria_MAX_ITER, it, eps)
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
    for s in (1.0, detect_width / gray_full.shape[1]):
        img = gray_full if s >= 1.0 else cv2.resize(
            gray_full, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        found, corners = cv2.findChessboardCorners(img, board, flags)
        if found:
            corners = (corners / s).astype(np.float32)
            return cv2.cornerSubPix(gray_full, corners, (win, win), (-1, -1), crit)
    return None


def load_intrinsics(path):
    import yaml
    with open(path) as f:
        prof = yaml.safe_load(f)
    K = np.array(prof["camera_matrix"], float)
    dist = np.array(prof.get("distortion_coefficients", []), float)
    return K, (dist if dist.size else np.zeros(5))


def write_pose(path, pose):
    import os
    import yaml
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(pose, f, sort_keys=False)


def main():
    args = parse_primitive_args()
    w = WarningsCollector(PRIMITIVE)

    with primitive_error_handling(warnings=w):
        image_path = get_input(args["inputs"], "image")
        intr_path = get_input(args["inputs"], "intrinsics")
        out_path = args["output"]
        p = args["params"]

        cols = int(require_param(p, "board_cols"))
        rows = int(require_param(p, "board_rows"))
        board = (cols, rows)
        square_size = float(get_param(p, "square_size", 1.0))
        detect_width = int(get_param(p, "detect_downscale_width", 1000))
        subpix = (int(get_param(p, "subpix_window", 11)),
                  int(get_param(p, "subpix_max_iter", 30)),
                  float(get_param(p, "subpix_eps", 0.001)))
        reproj_warn = float(get_param(p, "reproj_warn", 1.0))
        reproj_critical = float(get_param(p, "reproj_critical", 2.0))

        K, dist = load_intrinsics(intr_path)

        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            primitive_failure("Unreadable image", f"cv2 could not read {image_path}")

        corners = find_board(gray, board, detect_width, subpix)
        if corners is None:
            primitive_failure(
                "Board not detected",
                f"No {board} board found in {image_path}; cannot anchor the "
                f"ground plane. Check board dimensions and that it is fully "
                f"visible and flat in the frame.",
                warnings=w)

        obj = build_object_points(cols, rows, square_size)

        # Planar target: IPPE_SQUARE is the right solver for a flat board and
        # resolves the near/far pose better than the default (see Project 4).
        ok, rvec, tvec = cv2.solvePnP(obj, corners, K, dist,
                                      flags=cv2.SOLVEPNP_IPPE)
        if not ok:
            primitive_failure("solvePnP failed",
                              "Pose could not be recovered from the detected board",
                              warnings=w)

        # reprojection error: reproject the board corners and compare to detected
        proj, _ = cv2.projectPoints(obj, rvec, tvec, K, dist)
        proj = proj.reshape(-1, 2)
        reproj_err = float(np.sqrt(np.mean(np.sum(
            (proj - corners.reshape(-1, 2)) ** 2, axis=1))))

        # confidence-to-warning bridge
        if reproj_err > reproj_critical:
            w.critical(f"Reprojection error {reproj_err:.3f} px exceeds "
                       f"{reproj_critical}; pose unreliable, rectification will be wrong")
        elif reproj_err > reproj_warn:
            w.warn(f"Reprojection error {reproj_err:.3f} px above {reproj_warn}; "
                   f"pose borderline")
        else:
            w.info(f"Reprojection error {reproj_err:.3f} px; pose is trustworthy")

        # flip-ambiguity flag for symmetric boards
        if cols == rows:
            w.warn(f"Board is symmetric ({cols}x{rows}); solvePnP pose may be "
                   f"rotated 180 degrees from how the board was laid. Sanity-check "
                   f"the rectified orientation, or use an asymmetric board.")

        pose = {
            "rvec": [float(v) for v in rvec.ravel()],
            "tvec": [float(v) for v in tvec.ravel()],
            "reproj_err_px": round(reproj_err, 4),
            "board_internal_corners": [cols, rows],
            "square_size": square_size,
            "source_image": image_path,
            "intrinsics": intr_path,
        }
        write_pose(out_path, pose)

        primitive_success(
            metadata={
                "reproj_err_px": round(reproj_err, 4),
                "board_internal_corners": [cols, rows],
                "n_corners": int(corners.shape[0]),
                "rvec": pose["rvec"],
                "tvec": pose["tvec"],
            },
            warnings=w)


if __name__ == "__main__":
    main()