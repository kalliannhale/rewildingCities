"""
soil/classify/segment_rf.py
Kalli A. Hale | August 2026 | rewildingCities

Classical land-cover segmenter, the literature baseline after Xiao et al.:
visible-band vegetation indices + texture descriptors + a random forest.

Two ways to run:
  fit-inline (default) - train on this frame's own sparse scribbles and predict
                         it. The interactive single-frame path, unchanged.
  apply-model          - if a `model` input is supplied (a train_classifier
                         bundle), skip fitting and predict with it. This is how
                         a model trained on OTHER frames scores a held-out one.

Features come from soil/classify/rgb_landcover_features (the single source of
truth), so a model trained through featurize_frame + train_classifier sees the
identical feature space here. IMPORTANT: the caller must featurize with the same
work_max and texture_window used at training, or features silently misalign; the
primitive warns to keep that coupling visible.

contract:
  inputs : {"image": <RGB PNG>,
            "labels": <sparse label mask PNG, required only when fitting inline>,
            "model":  <train_classifier bundle .joblib, optional>}
  output : predicted full class mask PNG
  params : {"n_estimators": 200, "max_depth": null, "texture_window": 7,
            "class_names": {...}, "conf_warn": 0.6, "work_max": 1024}
"""
import numpy as np

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)
from soil.classify.rgb_landcover_features import feature_stack, FEATURE_NAMES

PRIMITIVE = "segment_rf"


def main():
    args = parse_primitive_args()
    w = WarningsCollector(PRIMITIVE)

    with primitive_error_handling(warnings=w):
        from PIL import Image

        image_path = get_input(args["inputs"], "image")
        model_path = get_input(args["inputs"], "model",
                               required=False, must_exist=False)
        labels_path = get_input(args["inputs"], "labels",
                                required=(model_path is None),
                                must_exist=(model_path is None))
        out_path = args["output"]
        p = args["params"]

        n_estimators = int(get_param(p, "n_estimators", 200))
        max_depth = get_param(p, "max_depth", None)
        tex_win = int(get_param(p, "texture_window", 7))
        conf_warn = float(get_param(p, "conf_warn", 0.6))
        work_max = int(get_param(p, "work_max", 1024))
        class_names = get_param(p, "class_names", {})

        # image at working resolution; features from the shared recipe
        img = Image.open(image_path).convert("RGB")
        scale = work_max / float(max(img.size))
        if scale < 1:
            img = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)))
        rgb = np.asarray(img)
        feats = feature_stack(rgb, tex_win)
        H, W, F = feats.shape

        meta = {"output_size": [W, H], "n_features": F}

        if model_path:
            # ---- apply a model trained elsewhere (held-out prediction) -------
            import joblib
            w.warn(f"applying a supplied model at work_max={work_max}, "
                   f"texture_window={tex_win}; these MUST match the featurization "
                   f"used to train it, or features silently misalign.")
            bundle = joblib.load(model_path)
            clf = bundle["sklearn_model"]
            cols = bundle["feature_cols"]
            missing = [c for c in cols if c not in FEATURE_NAMES]
            if missing:
                primitive_failure("Feature mismatch",
                                  f"model expects {missing}, not in this frame's "
                                  f"features {FEATURE_NAMES}", w)
            idx = [FEATURE_NAMES.index(c) for c in cols]
            X = feats.reshape(-1, F)[:, idx]
            proba = clf.predict_proba(X)
            classes_ = clf.classes_
            meta["mode"] = "apply"
            meta["model"] = model_path
            meta["classes_trained"] = [int(c) for c in classes_]
        else:
            # ---- fit inline on this frame's own scribbles (unchanged) --------
            from sklearn.ensemble import RandomForestClassifier
            labels = np.asarray(Image.open(labels_path).convert("L"))
            if labels.shape != rgb.shape[:2]:
                labels = np.asarray(Image.fromarray(labels).resize(
                    (rgb.shape[1], rgb.shape[0]), Image.NEAREST))
            labeled = labels > 0
            n_train = int(np.count_nonzero(labeled))
            if n_train < 20:
                primitive_failure("Too few labels",
                                  f"Only {n_train} labeled pixels; scribble more.",
                                  warnings=w)
            classes_present = sorted(int(c) for c in np.unique(labels[labeled]))
            for c in classes_present:
                n = int(np.count_nonzero(labels == c))
                if n < 30:
                    w.warn(f"class {c} ({class_names.get(str(c), c)}) has only {n} "
                           f"labeled pixels; may classify poorly")
            rf = RandomForestClassifier(n_estimators=n_estimators,
                                        max_depth=max_depth, oob_score=True,
                                        n_jobs=-1, random_state=0)
            rf.fit(feats[labeled], labels[labeled])
            proba = rf.predict_proba(feats.reshape(-1, F))
            classes_ = rf.classes_
            meta["mode"] = "fit"
            meta["n_train_pixels"] = n_train
            meta["classes_trained"] = classes_present
            meta["oob_score"] = round(float(rf.oob_score_), 4)

        # shared: assemble prediction + per-pixel confidence
        pred = classes_[np.argmax(proba, axis=1)].reshape(H, W).astype(np.uint8)
        conf = proba.max(axis=1).reshape(H, W)

        per_class_conf = {}
        for c in classes_:
            m = pred == c
            if m.any():
                mc = float(conf[m].mean())
                per_class_conf[int(c)] = round(mc, 3)
                name = class_names.get(str(int(c)), int(c))
                if mc < conf_warn:
                    w.warn(f"class {c} ({name}) mean confidence {mc:.2f} < "
                           f"{conf_warn}; predictions here are weak")
        if 2 in meta["classes_trained"] and 3 in meta["classes_trained"]:
            w.info("shrub/grass boundary present; historically the weakest split")

        Image.fromarray(pred, mode="L").save(out_path)
        meta["per_class_confidence"] = per_class_conf
        primitive_success(meta, warnings=w)


if __name__ == "__main__":
    main()