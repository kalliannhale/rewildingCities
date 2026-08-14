"""
soil/validate/calibrate_from_stills.py
Kalli A. Hale | August 2026 | rewildingCities Sprint 9

Camera calibration from a FOLDER OF STILLS, ported from Project 4's calibrate.cpp.
Project 4 was a live-video loop (bank good frames with 's', solve with 'c').
Here the frames already exist on disk, so the interaction goes away: detect on
every image, keep the ones that find the board, solve on the whole pile.

Two deliberate changes from the C++:
  1. board is (7,7) internal corners (the 8x8 chess board actually shot),
     NOT Project 4's (9,6). Detection at (9,6) was 0/20; at (7,7) it was 16/20.
  2. aspect ratio is left FREE (no CALIB_FIX_ASPECT_RATIO). Phone sensors are
     not guaranteed square-pixel, so forcing fx == fy can hide real error.

Note: today's frames are indoor, so this K is PROVISIONAL. The real intrinsics
are the ones solved at the site Monday, from the phone in the same focus-locked
state as the site photos. Today's job is to prove the path runs and the numbers
are sane, not to produce the final intrinsics.

usage:
    python3 calibrate_from_stills.py [IMAGE_DIR] [OUTPUT_YAML]
    defaults: IMAGE_DIR=./frames  OUTPUT_YAML=./intrinsics_indoor.yml
"""

import sys
import glob
import os
import numpy as np
import cv2

# ---- configuration -------------------------------------------------------

# (columns, rows) of INTERNAL corners. Size is (cols, rows), same convention
# as OpenCV; swapping these is the classic checkerboard bug, so we set it once.
BOARD = (7, 7)

# one square = SQUARE_SIZE world units. 1.0 keeps everything in board-square
# units, which is fine for intrinsics (K is scale-agnostic) and for IPM area
# FRACTIONS. Only absolute ground areas would need the real edge length (metric).
SQUARE_SIZE = 1.0

# detect on a downscaled copy for speed (findChessboardCorners is slow at full
# res, especially when it fails), then refine at full res so accuracy holds.
# this mirrors findBoardFast() from Project 4's ar.cpp.
DETECT_WIDTH = 1000

# sub-pixel refine settings, identical to Project 4
SUBPIX_WIN = (11, 11)
SUBPIX_CRIT = (cv2.TermCriteria_EPS + cv2.TermCriteria_MAX_ITER, 30, 0.001)

DETECT_FLAGS = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE


# ---- object-point template ----------------------------------------------

def build_object_points(board, square_size):
    """
    The 3D world points, glued to the target, identical for every frame.
    Order matches how OpenCV hands back detected corners: row outer, column
    inner, so the two lists stay lined up. (j, -i, 0), one square = square_size.
    This is Project 4's buildPointSet(), in numpy.
    """
    cols, rows = board
    pts = np.zeros((rows * cols, 3), np.float32)
    k = 0
    for i in range(rows):
        for j in range(cols):
            pts[k] = (j * square_size, -i * square_size, 0.0)
            k += 1
    return pts


# ---- detection -----------------------------------------------------------

def find_board(gray_full):
    """
    Detect on a downscaled copy, scale the corners back up, refine at full res.
    Returns refined full-res corners, or None if the board was not found.
    """
    h, w = gray_full.shape
    s = DETECT_WIDTH / float(w)
    small = cv2.resize(gray_full, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)

    found, corners = cv2.findChessboardCorners(small, BOARD, DETECT_FLAGS)
    if not found:
        return None

    corners = corners / s  # scale pixel coords back to full res
    corners = cv2.cornerSubPix(gray_full, corners.astype(np.float32),
                               SUBPIX_WIN, (-1, -1), SUBPIX_CRIT)
    return corners


# ---- main ----------------------------------------------------------------

def main():
    image_dir = sys.argv[1] if len(sys.argv) > 1 else "./frames"
    out_yaml = sys.argv[2] if len(sys.argv) > 2 else "./intrinsics_indoor.yml"

    paths = []
    for ext in ("png", "jpg", "jpeg", "PNG", "JPG", "JPEG"):
        paths += glob.glob(os.path.join(image_dir, f"*.{ext}"))
    paths = sorted(set(paths))
    if not paths:
        print(f"no images found in {image_dir}")
        sys.exit(1)

    obj_template = build_object_points(BOARD, SQUARE_SIZE)

    objpoints = []      # 3D world points, one entry per detected frame
    imgpoints = []      # 2D image corners, matching order
    used, missed = [], []
    image_size = None   # (width, height); must be the size we detect at

    print(f"scanning {len(paths)} images for a {BOARD} board...\n")
    for p in paths:
        img = cv2.imread(p)
        if img is None:
            missed.append((os.path.basename(p), "unreadable"))
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if image_size is None:
            image_size = (gray.shape[1], gray.shape[0])  # (w, h)

        corners = find_board(gray)
        if corners is None:
            missed.append((os.path.basename(p), "no board"))
            print(f"  .   {os.path.basename(p)}")
            continue

        objpoints.append(obj_template.copy())
        imgpoints.append(corners)
        used.append(os.path.basename(p))
        print(f"  YES {os.path.basename(p)}")

    print(f"\ndetected {len(used)}/{len(paths)} frames")
    if missed:
        print("missed:", ", ".join(f"{n} ({why})" for n, why in missed))
    if len(used) < 5:
        print("\nneed >= 5 detected frames to solve. stopping.")
        sys.exit(1)

    # the solve. aspect ratio FREE (no flags), so fx and fy float independently.
    print("\nsolving...")
    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, image_size, None, None)

    # the adjudication numbers, straight from Project 4's checklist:
    #   RMS under ~1 px  -> sub-pixel reprojection, set is trustworthy
    #   (u0, v0) near image center
    #   fx, fy sane and roughly comparable
    fx, fy = K[0, 0], K[1, 1]
    u0, v0 = K[0, 2], K[1, 2]
    cx, cy = image_size[0] / 2.0, image_size[1] / 2.0

    print("\n=== results ===")
    print(f"reprojection error (RMS, px): {rms:.4f}")
    print(f"image size (w x h):           {image_size[0]} x {image_size[1]}")
    print("camera matrix K:")
    print(K)
    print(f"fx, fy:                       {fx:.2f}, {fy:.2f}   "
          f"(ratio {fx/fy:.4f})")
    print(f"principal point (u0, v0):     ({u0:.1f}, {v0:.1f})")
    print(f"image center   (cx, cy):      ({cx:.1f}, {cy:.1f})")
    print(f"principal-point offset:       "
          f"({u0-cx:+.1f}, {v0-cy:+.1f}) px from center")
    print(f"distortion [k1 k2 p1 p2 k3]:  {dist.ravel()}")

    # honest read on the numbers
    print("\n=== read ===")
    print("RMS   :", "good (< 1 px)" if rms < 1.0
          else "high, diagnose before trusting" if rms > 1.5
          else "borderline, watch it")
    print("aspect:", "fx/fy within 2%" if abs(fx/fy - 1) < 0.02
          else "fx/fy differ > 2%, sensor may be non-square or set is thin")
    off = max(abs(u0 - cx), abs(v0 - cy)) / max(cx, cy)
    print("center:", "principal point near center" if off < 0.10
          else "principal point far from center, check edge coverage")

    # write-out: provenance-tracked, reusable. same role as Project 4's
    # data/intrinsics.yml. for the real project this lands in seeds/profiles/.
    fs = cv2.FileStorage(out_yaml, cv2.FILE_STORAGE_WRITE)
    fs.write("camera_matrix", K)
    fs.write("distortion_coefficients", dist)
    fs.write("image_width", image_size[0])
    fs.write("image_height", image_size[1])
    fs.write("rms_reproj_px", rms)
    fs.write("board_internal_corners", np.array(BOARD))
    fs.write("square_size_units", SQUARE_SIZE)
    fs.write("n_frames_used", len(used))
    fs.write("provisional_indoor", 1)  # today's set is indoor, reshoot at site
    fs.release()
    print(f"\nwrote {out_yaml}")
    print("NOTE: provisional (indoor). Reshoot a calibration set at the site,")
    print("      same focus-locked state as the site photos, for the real K.")


if __name__ == "__main__":
    main()