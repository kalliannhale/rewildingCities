"""
roots/statistics/train_regressor.py
Kalli A. Hale | August 2026 | rewildingCities

The regression sibling of train_classifier: fit a regressor on a tabular feature
set with a CONTINUOUS target and save the model. GENERAL, no domain assumptions.
For the cooling analysis the features are land-cover fractions in a buffer and
the target is LST, but the primitive neither knows nor cares.

Beyond prediction, it reports the fitted COEFFICIENTS (for linear) or feature
IMPORTANCES (for forests), which is the Xiao "dominant influencing factors"
answer: which land covers push temperature up or down. Because land-cover
fractions share a 0..1 scale, linear coefficients are directly comparable.

Contract: canopy/pr_io.py (three args, stdout metadata). EnvelopeBuilder wraps.
  inputs : {"table": <feature table, .parquet/.csv, incl. a target column>}
  output : model bundle (.joblib)
  params : {"estimator": "random_forest"|"linear"|"gradient_boost",
            "target_col": "lst", "feature_cols": [...] | null (auto),
            "exclude_cols": ["id","x","y","partition"], "n_estimators": 300,
            "max_depth": null, "seed": 0}
"""
import os

import numpy as np
import pandas as pd

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "train_regressor"


def _read(path):
    return pd.read_csv(path) if path.endswith(".csv") else pd.read_parquet(path)


def _make(name, n_estimators, max_depth, seed):
    if name == "random_forest":
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth,
                                     n_jobs=-1, random_state=seed, oob_score=True)
    if name == "gradient_boost":
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(random_state=seed)
    if name == "linear":
        from sklearn.linear_model import LinearRegression
        return LinearRegression()
    return None


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        import joblib
        args = parse_primitive_args()
        df = _read(get_input(args["inputs"], "table"))
        p = args["params"]

        estimator = get_param(p, "estimator", "random_forest")
        target_col = get_param(p, "target_col", "lst")
        feature_cols = get_param(p, "feature_cols", None)
        exclude = get_param(p, "exclude_cols", ["id", "x", "y", "partition"])
        n_estimators = int(get_param(p, "n_estimators", 300))
        max_depth = get_param(p, "max_depth", None)
        seed = int(get_param(p, "seed", 0))

        if target_col not in df.columns:
            primitive_failure("Missing target",
                              f"'{target_col}' not in {list(df.columns)}", w)
        if not feature_cols:
            feature_cols = [c for c in df.columns
                            if c != target_col and c not in exclude]
        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            primitive_failure("Missing feature columns", f"{missing}", w)

        X = df[feature_cols].to_numpy(float)
        y = df[target_col].to_numpy(float)
        reg = _make(estimator, n_estimators, max_depth, seed)
        if reg is None:
            primitive_failure("Unknown estimator",
                              f"'{estimator}' not in random_forest/linear/"
                              f"gradient_boost", w)
        reg.fit(X, y)

        bundle = {"estimator": estimator, "feature_cols": feature_cols,
                  "target_col": target_col, "sklearn_model": reg,
                  "params": {"n_estimators": n_estimators, "max_depth": max_depth,
                             "seed": seed}}
        out = args["output"]
        d = os.path.dirname(os.path.abspath(out))
        if d:
            os.makedirs(d, exist_ok=True)
        joblib.dump(bundle, out)

        # in-sample fit + the "dominant factors" readout
        r2_in = round(float(reg.score(X, y)), 4)
        meta = {"primitive": PRIMITIVE, "output": out, "estimator": estimator,
                "n_samples": int(len(df)), "n_features": len(feature_cols),
                "feature_cols": feature_cols, "target_col": target_col,
                "in_sample_r2": r2_in}
        if hasattr(reg, "coef_"):
            meta["coefficients"] = {c: round(float(v), 4)
                                    for c, v in zip(feature_cols, reg.coef_)}
            meta["intercept"] = round(float(reg.intercept_), 4)
            # Compositional features (fractions summing to ~1) make the design
            # near-singular; individual coefficients then blow up into nonsense
            # even while predictions stay fine. Exact rank misses the "~1" case,
            # so use the condition number.
            cond = float(np.linalg.cond(np.c_[X, np.ones(len(X))]))
            meta["design_condition_number"] = round(cond, 1)
            if cond > 1e3:
                w.warn(f"design condition number {cond:.0f} is high (features are "
                       f"near-collinear; land-cover fractions summing to ~1 do "
                       f"this), so these linear coefficients are UNRELIABLE. Drop "
                       f"a reference feature to read them relative to it, or use "
                       f"estimator=random_forest for feature_importances.")
        if hasattr(reg, "feature_importances_"):
            meta["feature_importances"] = {c: round(float(v), 4)
                                           for c, v in zip(feature_cols,
                                                           reg.feature_importances_)}
        if hasattr(reg, "oob_score_"):
            meta["oob_r2"] = round(float(reg.oob_score_), 4)
        w.info(f"in-sample R2 {r2_in}; this is FIT, not predictive skill, "
               f"score on a held-out split for that.")
        primitive_success(meta, w)


if __name__ == "__main__":
    main()
