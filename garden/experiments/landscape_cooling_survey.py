"""
garden/experiments/landscape_cooling_survey.py  (v1.2.0)
Kalli A. Hale | August 2026 | rewildingCities

Run every board frame through the pipeline and rank photographed spaces by
estimated cooling, mapping where the two models contest the ground. Reports TWO
cooling readings per frame, because they answer different questions:

  ground-plane : composition of the RECTIFIED, top-down ground (what is underfoot).
                 Fair across spaces, but structurally cannot see canopy overhead,
                 so it under-ranks forests.
  whole-scene  : composition of the RAW frame (canopy included). Closer to what a
                 body feels standing there, but carries perspective bias.

Per frame: recover_ground_pose -> segment_rf + segment_deep -> (whole-scene
cooling on the raw mask) + (rectify -> ground-plane cooling) -> RF-vs-deep
disagreement on the raw masks. Pose/rectify failures are flagged, not faked.

RUNTIME: segment_deep reloads per frame; use --max-frames to size a run.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

import pandas as pd

PY = sys.executable
BOARD = {"board_cols": 7, "board_rows": 7, "square_size": 1.875}
NODATA_RECT = 255  # rectify fills out-of-frustum with this
NODATA_RAW = 0     # raw predicted masks are dense 1..7; 0 = unlabeled


def run(path, inputs, output, params):
    r = subprocess.run([PY, path, json.dumps(inputs), output, json.dumps(params)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False, (r.stdout or r.stderr)
    return True, json.loads(r.stdout)


def scan(stills):
    rows = []
    for scene_dir in sorted(glob.glob(os.path.join(stills, "landscape-*"))):
        scene = os.path.basename(scene_dir).replace("landscape-", "")
        for img in sorted(glob.glob(os.path.join(scene_dir, "*.png")) +
                          glob.glob(os.path.join(scene_dir, "*.jpg"))):
            if img.endswith(("_labels.png", "_classid.png")):
                continue
            rows.append({"id": os.path.splitext(os.path.basename(img))[0],
                         "scene": scene, "image": img})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", required=True)
    ap.add_argument("--intrinsics", required=True)
    ap.add_argument("--rf-model", required=True)
    ap.add_argument("--deep-weights", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--output-scale", type=float, default=20)
    ap.add_argument("--min-coverage", type=float, default=0.4)
    ap.add_argument("--per-scene", type=int, default=25)
    a = ap.parse_args()
    for sub in ("poses", "masks", "rect", "cool", "dis"):
        os.makedirs(os.path.join(a.out, sub), exist_ok=True)

    frames = scan(a.stills)
    print(f"[scan] {len(frames)} frames available: "
          f"{dict(frames['scene'].value_counts())}; "
          f"target {a.per_scene} successes per scene")

    def cool(mask_path, tag, nodata, fid):
        ok, m = run("roots/metrics/space_cooling_potential.py", {"mask": mask_path},
                    os.path.join(a.out, "cool", f"{fid}_{tag}.json"),
                    {"nodata": nodata, "space_id": fid})
        return m["cooling_index"] if ok else None

    def segment(kind, img, fid):
        mask = os.path.join(a.out, "masks", f"{fid}_{kind}.png")
        if kind == "rf":
            ok, _ = run("soil/classify/segment_rf.py",
                        {"image": img, "model": a.rf_model}, mask, {})
        else:
            ok, _ = run("soil/classify/segment_deep.py",
                        {"image": img}, mask, {"weights": a.deep_weights})
        return mask if ok else None

    def rectify(mask, kind, fid):
        rect = os.path.join(a.out, "rect", f"{fid}_{kind}.png")
        ok, m = run("soil/transform/rectify_to_ground.py",
                    {"image": mask, "intrinsics": a.intrinsics,
                     "pose": os.path.join(a.out, "poses", fid + ".yml")},
                    rect, {"input_kind": "mask", "output_scale": a.output_scale,
                           "nodata_value": NODATA_RECT})
        return (rect, m.get("valid_fraction")) if ok else (None, None)

    def process(fid, scene, img):
        rec = {"id": fid, "scene": scene, "status": "ok",
               "rf_whole": None, "rf_ground": None,
               "deep_whole": None, "deep_ground": None,
               "agreement": None, "coverage": None}
        pose = os.path.join(a.out, "poses", fid + ".yml")
        ok, m = run("soil/calibrate/recover_ground_pose.py",
                    {"image": img, "intrinsics": a.intrinsics}, pose, BOARD)
        if not ok:
            rec["status"] = "pose_failed"; rec["error"] = str(m).strip()[:160]
            print(f"  {fid:26s} POSE FAILED: {rec['error'][:70]}")
            return rec
        rf_raw = segment("rf", img, fid)
        if rf_raw is None:
            rec["status"] = "segment_failed"; return rec
        rec["rf_whole"] = cool(rf_raw, "rf_whole", NODATA_RAW, fid)
        rf_rect, cov = rectify(rf_raw, "rf", fid)
        rec["coverage"] = cov
        if rf_rect is not None:
            rec["rf_ground"] = cool(rf_rect, "rf_ground", NODATA_RECT, fid)
            if cov is not None and cov < a.min_coverage:
                rec["status"] = "low_coverage"
        if a.deep_weights:
            deep_raw = segment("deep", img, fid)
            if deep_raw is not None:
                rec["deep_whole"] = cool(deep_raw, "deep_whole", NODATA_RAW, fid)
                deep_rect, _ = rectify(deep_raw, "deep", fid)
                if deep_rect is not None:
                    rec["deep_ground"] = cool(deep_rect, "deep_ground", NODATA_RECT, fid)
                gok, gm = run("roots/metrics/segmenter_disagreement.py",
                              {"a": rf_raw, "b": deep_raw},
                              os.path.join(a.out, "dis", f"{fid}.png"),
                              {"nodata": NODATA_RAW,
                               "summary_path": os.path.join(a.out, "dis", f"{fid}.json")})
                if gok:
                    rec["agreement"] = gm["agreement_rate"]
        print(f"  {fid:26s} whole rf={rec['rf_whole']} deep={rec['deep_whole']} | "
              f"ground rf={rec['rf_ground']} | agree={rec['agreement']} "
              f"cov={rec['coverage']} [{rec['status']}]")
        return rec

    # A frame counts as a success once it yields a cooling index. Walk each
    # scene in order, keep going past failures, and stop at per_scene successes
    # (or when the folder runs out).
    records = []
    for scene, grp in frames.groupby("scene"):
        got = 0
        attempts = 0
        for _, r in grp.iterrows():
            if got >= a.per_scene:
                break
            attempts += 1
            rec = process(r["id"], scene, r["image"])
            records.append(rec)
            if rec["rf_whole"] is not None:
                got += 1
        print(f"[{scene}] collected {got} successes from {attempts} attempts "
              f"(target {a.per_scene})")

    df = pd.DataFrame(records)
    df.to_csv(os.path.join(a.out, "survey.csv"), index=False)

    def report(col, label):
        ok = df[df[col].notna()].sort_values(col)
        if ok.empty:
            print(f"\n=== {label}: no values ==="); return
        print(f"\n=== spaces ranked by {label} (lower = cooler) ===")
        for _, r in ok.iterrows():
            print(f"  {r['scene']:12s} {r['id']:24s} {r[col]:+.3f}")
        print(f"--- per-scene mean ({label}) ---")
        print(ok.groupby("scene")[col].agg(['mean', 'count']).round(3).to_dict('index'))

    report("rf_whole", "WHOLE-SCENE cooling (canopy included)")
    report("rf_ground", "GROUND-PLANE cooling (underfoot)")

    n_pose = int((df["status"] == "pose_failed").sum())
    n_low = int((df["status"] == "low_coverage").sum())
    print(f"\n[flags] pose failures {n_pose}, low-coverage {n_low}, of {len(df)}")
    if df["agreement"].notna().any():
        print(f"[disagreement] mean RF-vs-deep agreement {df['agreement'].mean():.3f}")
    print(f"\nwrote {os.path.join(a.out, 'survey.csv')}")


if __name__ == "__main__":
    main()