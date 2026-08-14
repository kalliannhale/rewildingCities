"""
soil/classify/featurize_frame.py
Kalli A. Hale | August 2026 | rewildingCities

The bridge from image to table. Turns one frame (+ optional class-id label mask)
into the per-pixel feature table the GENERAL classifier primitives eat, so the
image-specific concerns stay quarantined here and train_classifier / apply_
classifier never learn what a pixel is.

Columns: frame, x, y, then the seven rgb_landcover_features (r,g,b,exg,vari,gli,
texture), then `label` when a mask is supplied. `frame` and x/y are meta the
trainer excludes; they let split_dataset group by frame or block by coordinate,
and let a prediction table be rasterized back later.

Two modes:
  labeled - only pixels with label > 0 (nodata). For building training tables.
  all     - every pixel. For prediction over a whole frame.

Works at the SAME working resolution as segment_rf (long edge -> work_max), so
features line up with how the segmenter sees the frame.

Contract: canopy/pr_io.py (three args, stdout metadata). EnvelopeBuilder wraps.
  inputs : {"image": <RGB PNG>, "labels": <class-id PNG, optional>}
  output : feature table (.parquet/.csv)
  params : {"mode": "labeled"|"all", "texture_window": 7, "work_max": 1024,
            "frame_id": <str>, "nodata": 0}
"""
import os

import numpy as np
import pandas as pd

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)
from soil.classify.rgb_landcover_features import feature_stack, FEATURE_NAMES

PRIMITIVE = "featurize_frame"


def _write(df, path):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    df.to_csv(path, index=False) if path.endswith(".csv") else df.to_parquet(path, index=False)


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        from PIL import Image
        args = parse_primitive_args()
        image_path = get_input(args["inputs"], "image")
        labels_path = get_input(args["inputs"], "labels",
                                required=False, must_exist=False)
        p = args["params"]

        mode = get_param(p, "mode", "labeled")
        tex_win = int(get_param(p, "texture_window", 7))
        work_max = int(get_param(p, "work_max", 1024))
        nodata = int(get_param(p, "nodata", 0))
        frame_id = get_param(p, "frame_id",
                             os.path.splitext(os.path.basename(image_path))[0])

        if mode == "labeled" and not labels_path:
            primitive_failure("Labels required",
                              "mode=labeled needs a labels input", w)

        img = Image.open(image_path).convert("RGB")
        scale = work_max / float(max(img.size))
        if scale < 1:
            img = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)))
        rgb = np.asarray(img)
        H, W = rgb.shape[:2]

        feats = feature_stack(rgb, tex_win)          # (H, W, 7)
        yy, xx = np.mgrid[0:H, 0:W]

        cols = {"frame": frame_id, "x": xx.ravel(), "y": yy.ravel()}
        for i, name in enumerate(FEATURE_NAMES):
            cols[name] = feats[..., i].ravel()

        labels = None
        if labels_path:
            lab = np.asarray(Image.open(labels_path).convert("L"))
            if lab.shape != (H, W):
                lab = np.asarray(Image.fromarray(lab).resize((W, H), Image.NEAREST))
            labels = lab.ravel()
            cols["label"] = labels

        df = pd.DataFrame(cols)

        if mode == "labeled":
            df = df[df["label"] != nodata].reset_index(drop=True)
            if len(df) == 0:
                primitive_failure("No labeled pixels",
                                  f"every pixel is nodata ({nodata})", w)
        elif mode != "all":
            primitive_failure("Unknown mode", f"'{mode}' not in labeled/all", w)

        _write(df, args["output"])

        meta = {
            "primitive": PRIMITIVE,
            "output": args["output"],
            "frame": frame_id,
            "mode": mode,
            "working_size": [W, H],
            "n_rows": int(len(df)),
            "feature_cols": FEATURE_NAMES,
        }
        if labels is not None:
            present = sorted(int(c) for c in np.unique(df["label"]) if c != nodata)
            meta["classes_present"] = present
        primitive_success(meta, w)


if __name__ == "__main__":
    main()
