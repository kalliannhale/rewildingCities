"""
roots/metrics/score_regression.py
Kalli A. Hale | August 2026 | rewildingCities

Held-out regression skill: R2, RMSE, MAE between predicted and true values.
This is the number that makes the analysis PREDICTIVE rather than merely
descriptive: computed on samples the model never trained on (a spatial split,
so nearby pixels don't leak), it says whether land cover actually predicts
temperature out of sample, not just correlates with it in sample.

Contract: canopy/pr_io.py (three args, stdout metadata).
  inputs : {"pred": <predictions table with a pred column + id>,
            "truth": <table with the true target + id>}
  output : regression_skill JSON
  params : {"id_col": "id", "pred_col": "pred", "truth_col": "lst"}
"""
import os
import json

import numpy as np
import pandas as pd

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "score_regression"


def _read(path):
    return pd.read_csv(path) if path.endswith(".csv") else pd.read_parquet(path)


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        args = parse_primitive_args()
        pred_df = _read(get_input(args["inputs"], "pred"))
        truth_df = _read(get_input(args["inputs"], "truth"))
        p = args["params"]
        id_col = get_param(p, "id_col", "id")
        pred_col = get_param(p, "pred_col", "pred")
        truth_col = get_param(p, "truth_col", "lst")

        if id_col in pred_df.columns and id_col in truth_df.columns:
            m = pred_df[[id_col, pred_col]].merge(
                truth_df[[id_col, truth_col]], on=id_col)
            yp = m[pred_col].to_numpy(float)
            yt = m[truth_col].to_numpy(float)
        else:
            if len(pred_df) != len(truth_df):
                primitive_failure("No id to join on and lengths differ",
                                  "provide an id column in both tables", w)
            yp = pred_df[pred_col].to_numpy(float)
            yt = truth_df[truth_col].to_numpy(float)

        n = len(yt)
        if n < 2:
            primitive_failure("Too few paired points", f"n={n}", w)

        resid = yp - yt
        ss_res = float(np.sum(resid ** 2))
        ss_tot = float(np.sum((yt - yt.mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else None
        rmse = float(np.sqrt(np.mean(resid ** 2)))
        mae = float(np.mean(np.abs(resid)))

        result = {"n": n,
                  "r2": round(r2, 4) if r2 is not None else None,
                  "rmse": round(rmse, 4), "mae": round(mae, 4),
                  "target": truth_col}
        out = args["output"]
        d = os.path.dirname(os.path.abspath(out))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(out, "w") as f:
            json.dump(result, f, indent=2)

        if r2 is not None and r2 < 0:
            w.warn(f"held-out R2 is negative ({r2:.3f}): the model predicts worse "
                   f"than the mean. Land cover may not predict temperature out of "
                   f"sample here, an honest finding, not a bug.")
        primitive_success({"primitive": PRIMITIVE, "output": out, **result}, w)


if __name__ == "__main__":
    main()
