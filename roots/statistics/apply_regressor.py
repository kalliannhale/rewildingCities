"""
roots/statistics/apply_regressor.py
Kalli A. Hale | August 2026 | rewildingCities

Apply a saved regressor bundle to a feature table. General partner to
train_regressor; binds features by name and fails loudly on a missing column.

Contract: canopy/pr_io.py (three args, stdout metadata).
  inputs : {"model": <.joblib>, "table": <feature table>}
  output : predictions table (id if present + pred)
  params : {"id_col": "id"}
"""
import os

import pandas as pd

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "apply_regressor"


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
        id_col = get_param(args["params"], "id_col", "id")

        feats = bundle["feature_cols"]
        missing = [c for c in feats if c not in df.columns]
        if missing:
            primitive_failure("Missing feature columns",
                              f"model needs {missing}; have {list(df.columns)}", w)

        pred = bundle["sklearn_model"].predict(df[feats].to_numpy(float))
        out = pd.DataFrame()
        if id_col in df.columns:
            out[id_col] = df[id_col].to_numpy()
        out["pred"] = pred

        _write(out, args["output"])
        primitive_success({"primitive": PRIMITIVE, "output": args["output"],
                           "estimator": bundle.get("estimator"),
                           "target_col": bundle.get("target_col"),
                           "n_samples": int(len(df))}, w)


if __name__ == "__main__":
    main()
