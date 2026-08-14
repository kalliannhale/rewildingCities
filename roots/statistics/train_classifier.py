"""
roots/statistics/train_classifier.py
Kalli A. Hale | August 2026 | rewildingCities

Fit a classifier on a tabular feature set and save the model. GENERAL: it knows
nothing about images, pixels, or land cover, only a table of feature columns and
a label column. The segmentation path turns frames into that table upstream
(rgb_landcover_features); a future tabular domain builds it its own way. The
estimator is an explicit, small, named set, not "train anything," so the
primitive stays honest rather than collapsing into a god-model.

Regression is a SIBLING primitive, not a mode here.

Contract: canopy/pr_io.py (three args, stdout metadata). EnvelopeBuilder wraps.
  inputs : {"table": <feature table, .parquet or .csv, incl. a label column>}
  output : model bundle (.joblib) = {estimator, feature_cols, label_col,
                                     classes, sklearn_model, params}
  params : {"estimator": "random_forest"|"gradient_boost"|"logistic",
            "label_col": "label", "feature_cols": [...] | null (auto),
            "exclude_cols": ["id","frame","partition","x","y"],
            "n_estimators": 200, "max_depth": null, "seed": 0,
            "class_weight": null}
"""
import os

import numpy as np
import pandas as pd

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "train_classifier"


def _read(path):
    return pd.read_csv(path) if path.endswith(".csv") else pd.read_parquet(path)


def _make_estimator(name, n_estimators, max_depth, seed, class_weight):
    if name == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(
            n_estimators=n_estimators, max_depth=max_depth, oob_score=True,
            n_jobs=-1, random_state=seed, class_weight=class_weight)
    if name == "gradient_boost":
        from sklearn.ensemble import GradientBoostingClassifier
        return GradientBoostingClassifier(random_state=seed)
    if name == "logistic":
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(max_iter=1000, class_weight=class_weight)
    return None


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        import joblib
        args = parse_primitive_args()
        df = _read(get_input(args["inputs"], "table"))
        p = args["params"]

        estimator = get_param(p, "estimator", "random_forest")
        label_col = get_param(p, "label_col", "label")
        feature_cols = get_param(p, "feature_cols", None)
        exclude = get_param(p, "exclude_cols",
                            ["id", "frame", "partition", "x", "y"])
        n_estimators = int(get_param(p, "n_estimators", 200))
        max_depth = get_param(p, "max_depth", None)
        seed = int(get_param(p, "seed", 0))
        class_weight = get_param(p, "class_weight", None)

        if label_col not in df.columns:
            primitive_failure("Missing label column",
                              f"'{label_col}' not in table: {list(df.columns)}", w)

        if not feature_cols:
            feature_cols = [c for c in df.columns
                            if c != label_col and c not in exclude]
        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            primitive_failure("Missing feature columns", f"{missing}", w)
        if not feature_cols:
            primitive_failure("No feature columns",
                              "nothing left after excluding label/meta columns", w)

        X = df[feature_cols].to_numpy()
        y = df[label_col].to_numpy()
        classes = sorted(int(c) for c in np.unique(y))
        if len(classes) < 2:
            primitive_failure("Single class",
                              f"only class {classes} present; cannot train a "
                              f"classifier", w)

        clf = _make_estimator(estimator, n_estimators, max_depth, seed, class_weight)
        if clf is None:
            primitive_failure("Unknown estimator",
                              f"'{estimator}' not in random_forest/gradient_boost/"
                              f"logistic", w)
        clf.fit(X, y)

        bundle = {
            "estimator": estimator,
            "feature_cols": feature_cols,
            "label_col": label_col,
            "classes": classes,
            "sklearn_model": clf,
            "params": {"n_estimators": n_estimators, "max_depth": max_depth,
                       "seed": seed, "class_weight": class_weight},
        }
        out = args["output"]
        d = os.path.dirname(os.path.abspath(out))
        if d:
            os.makedirs(d, exist_ok=True)
        joblib.dump(bundle, out)

        meta = {
            "primitive": PRIMITIVE,
            "output": out,
            "estimator": estimator,
            "n_samples": int(len(df)),
            "n_features": len(feature_cols),
            "feature_cols": feature_cols,
            "classes": classes,
        }
        if hasattr(clf, "oob_score_"):
            meta["oob_score"] = round(float(clf.oob_score_), 4)
        # honest class-balance note
        counts = {int(c): int(np.count_nonzero(y == c)) for c in classes}
        meta["class_counts"] = counts
        thin = {c: n for c, n in counts.items() if n < 30}
        for c, n in thin.items():
            w.warn(f"class {c} has only {n} training samples; may classify poorly.")

        primitive_success(meta, w)


if __name__ == "__main__":
    main()
