"""
garden/experiments/predict_temperature_from_landcover.py
Kalli A. Hale | August 2026 | rewildingCities

Predict surface temperature from surrounding land cover, the buffer analysis
turned PREDICTIVE. Xiao regress cooling on land-cover fractions across parks and
read the coefficients; the upgrade here is a SPATIAL train/test split, so the
reported R2 is out-of-sample skill, not in-sample fit. An experiment driver: the
primitives it calls stay general.

Pipeline:
  buffer_landcover_features  (sample points -> green/grey/blue fractions + LST)
  split_dataset --spatial    (block by coordinate; nearby points can't leak)
  train_regressor            (fit on train; report importances = dominant factors)
  apply_regressor            (predict held-out)
  score_regression           (held-out R2 / RMSE / MAE = the predictive answer)

Usage:
  python garden/experiments/predict_temperature_from_landcover.py \
    --lst  plots/michigan/delton/.data/lst_summer.tif \
    --land-cover plots/michigan/delton/.data/land_cover.tif \
    --out  plots/michigan/delton/.data/eval_thermal \
    --n-samples 1500 --buffer-m 100 --block-size 300 --estimator random_forest
"""
import argparse
import json
import os
import subprocess
import sys

import pandas as pd

PY = sys.executable


def run_primitive(path, inputs, output, params):
    cmd = [PY, path, json.dumps(inputs), output, json.dumps(params)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{path} failed:\n{r.stdout}\n{r.stderr}")
    return json.loads(r.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lst", required=True)
    ap.add_argument("--land-cover", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-samples", type=int, default=1500)
    ap.add_argument("--buffer-m", type=float, default=100)
    ap.add_argument("--block-size", type=float, default=300)
    ap.add_argument("--test-frac", type=float, default=0.3)
    ap.add_argument("--estimator", default="random_forest")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    # 1) sample buffer features
    feats = os.path.join(a.out, "features.csv")
    fmeta = run_primitive("roots/metrics/buffer_landcover_features.py",
                          {"lst": a.lst, "land_cover": a.land_cover}, feats,
                          {"n_samples": a.n_samples, "buffer_radius_m": a.buffer_m,
                           "seed": a.seed})
    print(f"[features] {fmeta['n_samples']} points, buffer {fmeta['buffer_px']} px, "
          f"features {fmeta['features']}")

    # 2) spatial split (block by coordinate so nearby points don't leak)
    part = os.path.join(a.out, "partition.csv")
    run_primitive("soil/scope/split_dataset.py", {"samples": feats}, part,
                  {"strategy": "spatial", "x_col": "x", "y_col": "y",
                   "block_size": a.block_size, "test_frac": a.test_frac,
                   "seed": a.seed})
    df = pd.read_csv(part)
    train = df[df["partition"] == "train"]
    test = df[df["partition"] == "test"]
    train_csv = os.path.join(a.out, "train.csv"); train.to_csv(train_csv, index=False)
    test_csv = os.path.join(a.out, "test.csv"); test.to_csv(test_csv, index=False)
    print(f"[split] spatial blocks of {a.block_size} m: "
          f"train {len(train)}, test {len(test)}")

    # 3) train (report dominant factors)
    model = os.path.join(a.out, "regressor.joblib")
    tr = run_primitive("roots/statistics/train_regressor.py", {"table": train_csv},
                       model, {"estimator": a.estimator, "target_col": "lst"})
    factors = tr.get("feature_importances") or tr.get("coefficients")
    print(f"[train] in-sample R2 {tr['in_sample_r2']}  dominant factors: {factors}")

    # 4) predict held-out + 5) score
    preds = os.path.join(a.out, "preds.csv")
    run_primitive("roots/statistics/apply_regressor.py",
                  {"model": model, "table": test_csv}, preds, {})
    skill = run_primitive("roots/metrics/score_regression.py",
                          {"pred": preds, "truth": test_csv}, 
                          os.path.join(a.out, "skill.json"), {"truth_col": "lst"})
    print(f"\n=== held-out predictive skill (n={skill['n']}) ===")
    print(f"  R2   = {skill['r2']}   (out-of-sample: can land cover predict "
          f"unseen temperature?)")
    print(f"  RMSE = {skill['rmse']} C")
    print(f"  MAE  = {skill['mae']} C")

    summary = {"n_samples": fmeta["n_samples"], "buffer_m": a.buffer_m,
               "block_size_m": a.block_size, "estimator": a.estimator,
               "dominant_factors": factors, "in_sample_r2": tr["in_sample_r2"],
               "held_out": skill}
    with open(os.path.join(a.out, "thermal_prediction.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nwrote {os.path.join(a.out, 'thermal_prediction.json')}")


if __name__ == "__main__":
    main()
