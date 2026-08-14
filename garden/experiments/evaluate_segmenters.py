"""
garden/experiments/evaluate_segmenters.py
Kalli A. Hale | August 2026 | rewildingCities

The real, leakage-safe classical evaluation (step 3). An EXPERIMENT DRIVER, so
it is allowed to be specific to this comparison; every PRIMITIVE it invokes
stays general and is called through its real stdout-JSON contract, exactly as
the orchestrator would. Nothing here reimplements a primitive.

Pipeline:
  scan a labeled folder
  -> resolve each painted scribble to a class-id mask   (resolve_scribble_labels)
  -> build a frame sample index, split by whole frame   (split_dataset)
  -> featurize each TRAIN frame's labeled pixels, pool  (featurize_frame)
  -> fit one classifier on the pool                     (train_classifier)
  -> for each TEST frame: predict a full mask,          (segment_rf, apply mode)
     score it against that frame's class-id truth       (score_segmenters)
  -> report per-frame metrics and a macro-average

Deep is left absent (score_segmenters reports RF-only); it slots in once trained.

Usage:
  python garden/experiments/evaluate_segmenters.py \
      --labeled plots/michigan/delton/.data/stills/labeled \
      --crosswalk seeds/crosswalks/land_cover/scribble_rgb_to_seven_class.yml \
      --out plots/michigan/delton/.data/eval \
      --test-frac 0.3 --strategy stratified --stratify-by scene
"""
import argparse
import glob
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

PY = sys.executable
FEATURES = ["r", "g", "b", "exg", "vari", "gli", "texture"]


def run_primitive(path, inputs, output, params):
    """Invoke a primitive through its contract; return parsed stdout metadata."""
    cmd = [PY, path, json.dumps(inputs), output, json.dumps(params)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{path} failed:\n{r.stdout}\n{r.stderr}")
    return json.loads(r.stdout)


def scan(labeled_dir):
    """Pair each scene frame with its painted label; infer scene from the name."""
    rows = []
    for lab in sorted(glob.glob(os.path.join(labeled_dir, "*_labels.png"))):
        stem = os.path.basename(lab)[: -len("_labels.png")]
        image = os.path.join(labeled_dir, stem + ".png")
        if not os.path.exists(image):
            continue
        parts = stem.split("_")
        scene = parts[1] if len(parts) > 1 else "unknown"
        rows.append({"id": stem, "scene": scene, "image": image,
                     "labels_painted": lab})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labeled", required=True)
    ap.add_argument("--crosswalk", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--test-frac", type=float, default=0.3)
    ap.add_argument("--strategy", default="stratified")
    ap.add_argument("--stratify-by", default="scene")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--work-max", type=int, default=1024)
    ap.add_argument("--texture-window", type=int, default=7)
    ap.add_argument("--deep-weights", default=None,
                    help="path to a train_segmenter_head weights bundle; if "
                         "given, segment_deep runs and is compared against RF")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    idx = scan(a.labeled)
    if len(idx) < 3:
        raise SystemExit(f"Only {len(idx)} labeled frames found; need at least 3 "
                         f"for a meaningful split.")
    print(f"[scan] {len(idx)} labeled frames: "
          f"{dict(idx['scene'].value_counts())}")

    # 1) resolve each painted scribble -> class-id mask
    classids = []
    for _, r in idx.iterrows():
        cid = os.path.join(a.labeled, r["id"] + "_classid.png")
        if not os.path.exists(cid):
            run_primitive("soil/classify/resolve_scribble_labels.py",
                          {"scribble": r["labels_painted"]}, cid,
                          {"crosswalk": a.crosswalk})
        classids.append(cid)
    idx["classid"] = classids

    # 2) split by whole frame
    samples_csv = os.path.join(a.out, "frames_index.csv")
    idx[["id", "scene"]].to_csv(samples_csv, index=False)
    part_csv = os.path.join(a.out, "frames_partition.csv")
    run_primitive("soil/scope/split_dataset.py", {"samples": samples_csv},
                  part_csv, {"strategy": a.strategy, "stratify_by": a.stratify_by,
                             "test_frac": a.test_frac, "seed": a.seed})
    part = pd.read_csv(part_csv).merge(idx, on=["id", "scene"])
    train = part[part["partition"] == "train"]
    test = part[part["partition"] == "test"]
    print(f"[split] train={list(train['id'])}\n        test ={list(test['id'])}")

    # 3) featurize each TRAIN frame's labeled pixels, pool into one table
    tables = []
    for _, r in train.iterrows():
        t = os.path.join(a.out, r["id"] + "_feats.csv")
        run_primitive("soil/classify/featurize_frame.py",
                      {"image": r["image"], "labels": r["classid"]}, t,
                      {"mode": "labeled", "work_max": a.work_max,
                       "texture_window": a.texture_window, "frame_id": r["id"]})
        tables.append(pd.read_csv(t))
    pool = pd.concat(tables, ignore_index=True)
    pool_csv = os.path.join(a.out, "train_table.csv")
    pool.to_csv(pool_csv, index=False)
    print(f"[featurize] pooled train pixels: {len(pool)} "
          f"across {len(train)} frames")

    # 4) fit one classifier on the pool
    model = os.path.join(a.out, "rf_model.joblib")
    tr = run_primitive("roots/statistics/train_classifier.py", {"table": pool_csv},
                       model, {"estimator": "random_forest", "label_col": "label"})
    print(f"[train] classes={tr['classes']} oob={tr.get('oob_score')}")

    # 5) predict + score each TEST frame (RF, and deep if weights supplied)
    dims = ["overall_accuracy", "mean_iou", "cohen_kappa"]
    per_frame = {}
    for _, r in test.iterrows():
        pred_rf = os.path.join(a.out, r["id"] + "_pred_rf.png")
        run_primitive("soil/classify/segment_rf.py",
                      {"image": r["image"], "model": model}, pred_rf,
                      {"work_max": a.work_max, "texture_window": a.texture_window})
        score_inputs = {"truth": r["classid"], "pred_rf": pred_rf}
        if a.deep_weights:
            pred_deep = os.path.join(a.out, r["id"] + "_pred_deep.png")
            run_primitive("soil/classify/segment_deep.py",
                          {"image": r["image"]}, pred_deep,
                          {"weights": a.deep_weights, "work_max": a.work_max})
            score_inputs["pred_deep"] = pred_deep
        cmp_json = os.path.join(a.out, r["id"] + "_score.json")
        s = run_primitive("roots/metrics/score_segmenters.py",
                          score_inputs, cmp_json, {"nodata": 0})
        per_frame[r["id"]] = {"rf": s["segmenters"]["rf"],
                              "deep": s["segmenters"]["deep"],
                              "winners": s["winners"]}

    # 6) report: per-frame, macro-average per model, macro winner
    def macro(model_key):
        vals = [pf[model_key] for pf in per_frame.values() if pf[model_key]]
        if not vals:
            return None
        return {d: round(float(np.mean([v[d] for v in vals if v[d] is not None])), 4)
                for d in dims}

    print("\n=== per test frame ===")
    for fid, pf in per_frame.items():
        rf = pf["rf"]
        print(f"  {fid:26s} RF   acc={rf['overall_accuracy']} "
              f"mIoU={rf['mean_iou']} kappa={rf['cohen_kappa']} (n={rf['n_valid_px']})")
        if pf["deep"]:
            dp = pf["deep"]
            print(f"  {'':26s} DEEP acc={dp['overall_accuracy']} "
                  f"mIoU={dp['mean_iou']} kappa={dp['cohen_kappa']}")

    macro_rf, macro_deep = macro("rf"), macro("deep")
    print(f"\n=== macro-average over {len(per_frame)} test frames ===")
    print(f"  RF  : {macro_rf}")
    if macro_deep:
        print(f"  DEEP: {macro_deep}")
        macro_winner = {d: ("rf" if macro_rf[d] >= macro_deep[d] else "deep")
                        for d in dims}
        print(f"  winner (macro): {macro_winner}")
    else:
        macro_winner = None
        print("  DEEP: not run (pass --deep-weights to compare); RF-only.")

    summary = {"n_frames": len(idx), "train": list(train["id"]),
               "test": list(test["id"]), "per_frame": per_frame,
               "macro_average": {"rf": macro_rf, "deep": macro_deep},
               "macro_winner": macro_winner, "deep_weights": a.deep_weights}
    out_json = os.path.join(a.out, "segmenter_evaluation.json")
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nwrote {out_json}")


if __name__ == "__main__":
    main()