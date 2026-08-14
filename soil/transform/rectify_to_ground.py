"""
soil/transform/rectify_to_ground.py
Kalli A. Hale | August 2026 | rewildingCities

Inverse-perspective mapping: rectify an oblique image (or its label mask) to a
bird's-eye view in ground-plane coordinates, using known camera intrinsics and
the pose of the ground plane (from a flat board in the scene).

The geometry: a flat ground point is (X, Y, 0). Under a pinhole camera it
projects by  s*[u,v,1]^T = K*[r1 | r2 | t]*[X,Y,1]^T. The 3x3 middle matrix is
the ground->image homography H. Rectification is H^-1, applied to a chosen
FINITE ground rectangle below the horizon (points at/above the horizon recede
to infinity and cannot be rectified; they are rendered nodata).

Python primitive on the standard contract; the EnvelopeBuilder wraps it.

contract:
  inputs : {"image": <PNG>, "intrinsics": <profile YAML>, "pose": <pose YAML>}
  output : rectified raster PNG
  params : {
    "input_kind": "mask" | "rgb",         # mask -> nearest, rgb -> linear
    "output_scale": 50,                    # output pixels per ground unit
    "ground_extent": [x0, x1, y0, y1],     # ground rectangle to render (units)
    "nodata_value": 255,                   # fill for out-of-scene / above horizon
    "undistort": true
  }
"""

import numpy as np
import cv2

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          require_param, WarningsCollector,
                          primitive_success, primitive_error_handling)

PRIMITIVE = "rectify_to_ground"


# ---- core geometry (importable, no I/O, so it is directly testable) ------

def build_ground_homography(K, rvec, tvec):
    """H maps ground (X, Y, 1) -> image (u, v, 1). Drop the third rotation
    column because the ground plane is Z = 0. This is K*[r1 | r2 | t]."""
    R, _ = cv2.Rodrigues(np.asarray(rvec, float).reshape(3, 1))
    t = np.asarray(tvec, float).reshape(3)
    return K @ np.column_stack([R[:, 0], R[:, 1], t])


def _scale_matrix(extent, scale):
    """S maps ground units -> output pixels, with a y-flip so ground +Y (far)
    sits at the top of the raster. Returns (S, width, height)."""
    x0, x1, y0, y1 = extent
    w = int(round((x1 - x0) * scale))
    h = int(round((y1 - y0) * scale))
    S = np.array([[scale, 0.0, -x0 * scale],
                  [0.0, -scale, y1 * scale],
                  [0.0, 0.0, 1.0]])
    return S, w, h


def undistort(img, K, dist, is_mask):
    """Remove lens distortion. Masks use nearest-neighbor so class labels are
    not blended; RGB uses linear. No-op-ish when dist is ~zero."""
    if dist is None or np.allclose(dist, 0):
        return img
    h, w = img.shape[:2]
    mapx, mapy = cv2.initUndistortRectifyMap(K, dist, None, K, (w, h), cv2.CV_32FC1)
    interp = cv2.INTER_NEAREST if is_mask else cv2.INTER_LINEAR
    return cv2.remap(img, mapx, mapy, interp)


def rectify(img, H, extent, scale, is_mask, nodata):
    """Warp an (undistorted) image to bird's-eye over a finite ground extent.
    Returns (rectified, meta)."""
    S, w, h = _scale_matrix(extent, scale)
    if w <= 0 or h <= 0:
        raise ValueError(f"Degenerate output size {w}x{h}; check ground_extent")

    # M maps image -> output(ground) pixels. warpPerspective fills each output
    # pixel by sampling the source, so this yields the bird's-eye view.
    M = S @ np.linalg.inv(H)
    interp = cv2.INTER_NEAREST if is_mask else cv2.INTER_LINEAR

    if is_mask:
        border_val = float(nodata)
    else:
        border_val = (float(nodata),) * (img.shape[2] if img.ndim == 3 else 1)

    rectified = cv2.warpPerspective(
        img, M, (w, h), flags=interp,
        borderMode=cv2.BORDER_CONSTANT, borderValue=border_val)

    # validity: fraction of the ground rectangle that actually came from the image
    if is_mask:
        valid = np.count_nonzero(rectified != nodata)
    else:
        valid = np.count_nonzero(np.any(rectified != nodata, axis=2))
    valid_frac = valid / float(w * h)

    return rectified, {
        "output_width": w, "output_height": h,
        "ground_extent": list(map(float, extent)),
        "output_scale": scale,
        "valid_fraction": round(valid_frac, 4),
    }


# ---- I/O helpers ---------------------------------------------------------

def load_intrinsics(path):
    import yaml
    with open(path) as f:
        prof = yaml.safe_load(f)
    K = np.array(prof["camera_matrix"], float)
    dist = np.array(prof.get("distortion_coefficients", []), float)
    return K, (dist if dist.size else None)


def load_pose(path):
    import yaml
    with open(path) as f:
        pose = yaml.safe_load(f)
    return np.array(pose["rvec"], float), np.array(pose["tvec"], float)


def default_extent(img_shape, H, warnings):
    """Fallback ground extent: project the image's bottom edge and center to
    ground and bound it, clamped so an above-horizon corner cannot blow it up.
    A real run should pass ground_extent explicitly (the measured ROI)."""
    h, w = img_shape[:2]
    Hinv = np.linalg.inv(H)
    # sample the lower half of the frame, which is reliably below the horizon
    pts = np.array([[0, h - 1, 1], [w - 1, h - 1, 1],
                    [0, h * 0.55, 1], [w - 1, h * 0.55, 1],
                    [w * 0.5, h * 0.7, 1]], float).T
    g = Hinv @ pts
    g = g[:2] / g[2]
    x0, x1 = float(g[0].min()), float(g[0].max())
    y0, y1 = float(g[1].min()), float(g[1].max())
    warnings.warn(f"ground_extent auto-derived as [{x0:.2f},{x1:.2f},"
                  f"{y0:.2f},{y1:.2f}]; pass it explicitly for the measured ROI")
    return [x0, x1, y0, y1]


# ---- contract entry point ------------------------------------------------

def main():
    args = parse_primitive_args()
    w = WarningsCollector(PRIMITIVE)

    with primitive_error_handling(warnings=w):
        image_path = get_input(args["inputs"], "image")
        intr_path = get_input(args["inputs"], "intrinsics")
        pose_path = get_input(args["inputs"], "pose")
        out_path = args["output"]
        p = args["params"]

        input_kind = get_param(p, "input_kind", "mask")
        is_mask = (input_kind == "mask")
        scale = float(get_param(p, "output_scale", 50))
        nodata = int(get_param(p, "nodata_value", 255))
        do_undistort = bool(get_param(p, "undistort", True))
        extent = get_param(p, "ground_extent", None)

        K, dist = load_intrinsics(intr_path)
        rvec, tvec = load_pose(pose_path)

        flag = cv2.IMREAD_GRAYSCALE if is_mask else cv2.IMREAD_COLOR
        img = cv2.imread(image_path, flag)
        if img is None:
            from canopy.pr_io import primitive_failure
            primitive_failure("Unreadable image", f"cv2 could not read {image_path}")

        H = build_ground_homography(K, rvec, tvec)

        if do_undistort:
            img = undistort(img, K, dist, is_mask)

        if extent is None:
            extent = default_extent(img.shape, H, w)

        rectified, meta = rectify(img, H, extent, scale, is_mask, nodata)

        if meta["valid_fraction"] < 0.5:
            w.warn(f"Only {meta['valid_fraction']*100:.0f}% of the ground extent "
                   f"came from the image; extent may reach past the horizon")
        else:
            w.info(f"valid ground coverage {meta['valid_fraction']*100:.0f}%")

        cv2.imwrite(out_path, rectified)

        primitive_success(
            metadata={**meta, "input_kind": input_kind, "undistorted": do_undistort},
            warnings=w)


if __name__ == "__main__":
    main()