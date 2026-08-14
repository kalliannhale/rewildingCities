"""
roots/statistics/apply_classifier.py
Kalli A. Hale | August 2026 | rewildingCities

Apply a saved classifier bundle to a feature table. GENERAL partner to
train_classifier: no image or domain assumptions, just the same feature columns
the model was trained on. It binds features BY NAME (from the bundle), so a
table with columns in a different order, or with extra meta columns, still
scores correctly. Fails loudly if a required feature column is missing, because
predicting on the wrong columns is a silent way to get confident nonsense.

Contract: canopy/pr_io.py (three args, stdout metadata). EnvelopeBuilder wraps.
  inputs : {"model": <.joblib bundle>, "table": <feature table, .parquet/.csv>}
  output : predictions table (.parquet/.csv): id (if present) + pred + confidence
  params : {"id_col": "id", "proba": true}
"""
import os

import numpy as np
import pandas as pd

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "apply_classifier"


def _read(path):
    return pd.read_csv(path) if path.endswith(".csv") else pd.read_parquet(path)


def _write(df, path):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    df.to_csv(path, index=False) if path.endswith(".csv") else df.to_parquet(path, index=False)


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        import joblib
        args = parse_primitive_args()
        bundle = joblib.load(get_input(args["inputs"], "model"))
        df = _read(get_input(args["inputs"], "table"))
        p = args["params"]
        id_col = get_param(p, "id_col", "id")
        want_proba = bool(get_param(p, "proba", True))

        feature_cols = bundle["feature_cols"]
        clf = bundle["sklearn_model"]

        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            primitive_failure("Missing feature columns",
                              f"model needs {missing}; table has "
                              f"{list(df.columns)}", w)

        X = df[feature_cols].to_numpy()
        pred = clf.predict(X)

        out = pd.DataFrame()
        if id_col in df.columns:
            out[id_col] = df[id_col].to_numpy()
        out["pred"] = pred.astype(int)

        if want_proba and hasattr(clf, "predict_proba"):
            proba = clf.predict_proba(X)
            out["confidence"] = np.round(proba.max(axis=1), 4)

        _write(out, args["output"])

        vals, counts = np.unique(pred, return_counts=True)
        primitive_success({
            "primitive": PRIMITIVE,
            "output": args["output"],
            "estimator": bundle.get("estimator"),
            "n_samples": int(len(df)),
            "feature_cols": feature_cols,
            "pred_distribution": {int(v): int(c) for v, c in zip(vals, counts)},
        }, w)


if __name__ == "__main__":
    main()
