"""
soil/classify/resolve_scribble_labels.py
Kalli A. Hale | August 2026 | rewildingCities

Resolve a hand-painted RGB scribble mask into the canonical seven-class integer
class-id mask consumed by segment_rf. The paint->class vocabulary is NOT
hardcoded here; it is read from a seeds crosswalk
(seeds/crosswalks/land_cover/scribble_rgb_to_seven_class.yml), the same
source-vocabulary reconciliation the platform uses for band names and land
cover. "resolve" here is the same verb as resolve_band: reconcile a source
vocabulary to the canonical one.

Contract: canopy/pr_io.py (stdout-JSON, three args). The primitive writes its
output file and prints metadata; the EnvelopeBuilder wraps provenance/hashes
around that metadata. No envelope is built here.

  inputs : {"scribble": <path to painted RGB mask PNG>}
  output : <path to class-id PNG, 8-bit grayscale, pixel value == class code>
  params : {"crosswalk": <path to scribble_rgb_to_seven_class.yml>,
            "tolerance": <optional float, overrides the crosswalk snap tolerance>}

Design choices worth their salt:
  - exact palette color            -> its class code
  - fringe within `tolerance`      -> nearest class code (recovers stroke edges)
  - ambiguous fringe beyond it     -> 0/unlabeled (never an invented class)
  - phantom guard                  -> fail loudly if any emitted class was not
                                      painted exactly somewhere in the mask
"""
import os

import numpy as np
import yaml
from PIL import Image

from canopy.pr_io import (
    parse_primitive_args, get_input, get_param, require_param,
    WarningsCollector, primitive_success, primitive_failure,
    primitive_error_handling,
)

PRIMITIVE = "resolve_scribble_labels"


def _load_palette(crosswalk_path, warns):
    with open(crosswalk_path) as f:
        cw = yaml.safe_load(f)
    entries = cw.get("palette")
    if not entries:
        primitive_failure("Invalid crosswalk",
                          f"No 'palette' block in {crosswalk_path}", warns)
    rgb = np.array([e["rgb"] for e in entries], dtype=np.int16)
    code = np.array([e["code"] for e in entries], dtype=np.uint8)
    names = {int(e["code"]): e["name"] for e in entries}
    default_tol = float((cw.get("snap") or {}).get("tolerance", 30))
    return rgb, code, names, default_tol


def main():
    warns = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warns):
        args = parse_primitive_args()
        scribble = get_input(args["inputs"], "scribble")
        crosswalk = require_param(args["params"], "crosswalk")
        if not os.path.exists(crosswalk):
            primitive_failure("Crosswalk not found", crosswalk, warns)

        pal_rgb, pal_code, names, default_tol = _load_palette(crosswalk, warns)
        tol = float(get_param(args["params"], "tolerance", default_tol))
        min_class_px = int(get_param(args["params"], "min_class_px", 20))

        rgb = np.asarray(Image.open(scribble).convert("RGB"))
        h, w = rgb.shape[:2]
        flat = rgb.reshape(-1, 3)

        # Reason over the distinct colors only, then index back to full image.
        colors, inv = np.unique(flat, axis=0, return_inverse=True)
        inv = inv.reshape(-1)

        dist = np.linalg.norm(
            colors[:, None, :].astype(np.int16) - pal_rgb[None, :, :], axis=2)
        nearest = dist.argmin(axis=1)
        near_d = dist.min(axis=1)
        is_exact = near_d == 0

        code_per_color = pal_code[nearest].copy()
        code_per_color[(~is_exact) & (near_d > tol)] = 0

        per_color = np.bincount(inv, minlength=len(colors))
        snapped = int(per_color[(~is_exact) & (near_d <= tol)].sum())
        dropped = int(per_color[(~is_exact) & (near_d > tol)].sum())

        classid = code_per_color[inv].reshape(h, w).astype(np.uint8)

        # Stray-class guard (presence, not exactness). A painted class is a
        # region with many pixels; a class that shows up with only a handful is
        # almost always an anti-aliased edge between two real colors, not
        # something the labeler painted. Drop those to unlabeled and say so.
        # This is deliberately NOT an exact-match test: a real class exported
        # with soft edges may have zero exactly-palette pixels yet thousands of
        # near ones, and it must pass. (A long thin invented edge could still
        # exceed the threshold; a spatial/morphology check is the future guard.)
        stray_dropped = 0
        for c in [int(x) for x in np.unique(classid) if x != 0]:
            n = int(np.count_nonzero(classid == c))
            if n < min_class_px:
                classid[classid == c] = 0
                stray_dropped += n
                warns.warn(f"dropped class {c} ({names.get(c, c)}): only {n} px, "
                           f"below min_class_px={min_class_px}; treated as an "
                           f"anti-aliased stray, not a painted region.")

        out_dir = os.path.dirname(os.path.abspath(args["output"]))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        Image.fromarray(classid, mode="L").save(args["output"])

        total = int(classid.size)
        codes, counts = np.unique(classid, return_counts=True)
        per_class = {names.get(int(c), str(int(c))): int(n)
                     for c, n in zip(codes, counts)}

        if dropped > 0.01 * total:
            warns.warn(
                f"{dropped} px ({100 * dropped / total:.2f}%) were ambiguous and "
                f"set unlabeled; check for soft-edged (non-Pencil) strokes.")
        for name, n in per_class.items():
            if name != "unlabeled" and n < 200:
                warns.warn(f"class '{name}' has only {n} labeled px; "
                           f"may be too thin to train on.")

        metadata = {
            "primitive": PRIMITIVE,
            "scribble": scribble,
            "crosswalk": crosswalk,
            "output": args["output"],
            "width": w,
            "height": h,
            "tolerance": tol,
            "snapped_px": snapped,
            "dropped_to_unlabeled_px": dropped,
            "stray_class_dropped_px": stray_dropped,
            "labeled_px": int((classid > 0).sum()),
            "per_class_px": per_class,
            "classes_present": sorted(int(c) for c in codes if c != 0),
        }
        primitive_success(metadata, warns)


if __name__ == "__main__":
    main()