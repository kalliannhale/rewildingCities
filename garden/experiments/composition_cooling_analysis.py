"""
garden/experiments/composition_cooling_analysis.py
Kalli A. Hale | rewildingCities

Unblocks the numbers. Consolidates the per-frame class compositions the survey
already wrote (fractions_by_class inside each cool/*.json) into one tidy table,
then, using the LOCALLY-MEASURED per-class LST from cooling_differential.json as
weights, computes:

  (1) predicted_LST per space and per scene under the new estimator
        predicted_LST = sum_k  fraction_k * median_LST_k
  (2) soil sensitivity, three ways (soil is n=1 in the differential):
        soil_measured  : bare LST 36.29
        soil_excluded  : drop soil, renormalize remaining fractions
        soil_organic   : treat soil as vegetation-adjacent (grass LST 30.13)
  (3) the canopy gap re-expressed in composition units: image green fraction
        (canopy+shrub+grass) by scene and model, vs the satellite green fraction.

Reads only files already on disk. Writes three CSVs to <out>.

Usage:
  python garden/experiments/composition_cooling_analysis.py \
    --eval-dir plots/michigan/delton/.data/eval_landscape \
    --differential plots/michigan/delton/.data/.../cooling_differential.json \
    --out plots/michigan/delton/.data/eval_landscape/composition_analysis
"""
import argparse, glob, json, os
import pandas as pd

VEG = ["canopy", "shrub", "grass"]          # image green
GREY = ["impervious", "building"]

# 7-class name -> ESA WorldCover code whose measured LST is its weight
NAME2ESA = {"canopy":"10","shrub":"10","grass":"30","soil":"60",
            "impervious":"50","water":"80","building":"50"}
SAT_GREEN_ESA = {"10","30","40","90"}       # tree, grass, crop, wetland


def scene_of(fid):
    parts = fid.split("_")
    return parts[1] if len(parts) > 1 else "unknown"


def weighted_lst(fracs, lst, soil_mode):
    f = dict(fracs)
    if soil_mode == "excluded":
        f.pop("soil", None)
    tot = sum(f.values())
    if tot <= 0:
        return None
    out = 0.0
    for k, v in f.items():
        if k == "soil":
            w = {"measured": lst["soil"], "organic": lst["grass"]}[soil_mode]
        else:
            w = lst.get(k)
        if w is None:
            return None
        out += (v / tot) * w
    return round(out, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", required=True)
    ap.add_argument("--differential", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    # --- measured per-class LST weights from the local differential ---
    pc = json.load(open(a.differential))["per_class"]
    lst = {name: pc[esa]["median"] for name, esa in NAME2ESA.items() if esa in pc}
    missing = [n for n in NAME2ESA if n not in lst]
    if missing:
        print(f"[warn] no local LST for {missing}; those rows will be skipped")
    print("per-class LST weights (C):", {k: round(v,2) for k,v in lst.items()})

    # satellite green fraction (reference), by pixel counts
    tot_px = sum(pc[c]["n"] for c in pc)
    sat_green = round(sum(pc[c]["n"] for c in pc if c in SAT_GREEN_ESA) / tot_px, 3)

    # --- consolidate per-frame compositions from cool/*.json ---
    rows = []
    for jf in sorted(glob.glob(os.path.join(a.eval_dir, "cool", "*.json"))):
        base = os.path.basename(jf)[:-5]            # <fid>_<model>_<reading>
        try:
            d = json.load(open(jf))
        except Exception:
            continue
        fr = d.get("fractions_by_class")
        if not fr:
            continue
        # parse trailing _<model>_<reading>
        for model in ("rf", "deep"):
            for reading in ("whole", "ground"):
                suf = f"_{model}_{reading}"
                if base.endswith(suf):
                    fid = base[: -len(suf)]
                    rec = {"id": fid, "scene": scene_of(fid),
                           "model": model, "reading": reading}
                    for c in NAME2ESA:
                        rec[f"f_{c}"] = round(float(fr.get(c, 0.0)), 4)
                    rec["green"] = round(sum(fr.get(c,0.0) for c in VEG), 4)
                    rec["grey"] = round(sum(fr.get(c,0.0) for c in GREY), 4)
                    rec["water"] = round(float(fr.get("water",0.0)), 4)
                    for mode in ("measured", "excluded", "organic"):
                        rec[f"predLST_{mode}"] = weighted_lst(fr, lst, mode)
                    rows.append(rec)
    comp = pd.DataFrame(rows)
    if comp.empty:
        print("no compositions found under", os.path.join(a.eval_dir, "cool"))
        return
    comp.to_csv(os.path.join(a.out, "compositions.csv"), index=False)
    print(f"[wrote] compositions.csv  ({len(comp)} frame-readings)")

    # --- (1)+(2) predicted_LST per scene, per model/reading, 3 soil modes ---
    agg = (comp.groupby(["scene","model","reading"])
              [["predLST_measured","predLST_excluded","predLST_organic","green","grey","water"]]
              .agg(["mean","count"]).round(3))
    agg.to_csv(os.path.join(a.out, "predicted_lst_by_scene.csv"))
    print("[wrote] predicted_lst_by_scene.csv")
    print("\n== predicted_LST (C) by scene, rf/whole, 3 soil treatments ==")
    sub = comp[(comp.model=="rf") & (comp.reading=="whole")]
    print(sub.groupby("scene")[["predLST_measured","predLST_excluded","predLST_organic"]]
             .mean().round(2).to_string())

    # --- (3) canopy gap as green fraction: image (rf/deep) vs satellite ---
    green = (comp.groupby(["scene","model","reading"])["green"].mean().round(3)
                 .reset_index().pivot_table(index="scene", columns=["model","reading"], values="green"))
    green.to_csv(os.path.join(a.out, "green_fraction_comparison.csv"))
    print(f"\n== image green fraction by scene (satellite green fraction = {sat_green}) ==")
    print(green.round(3).to_string())
    print("\nThe canopy gap: compare rf vs deep green fraction on forest — if rf<<deep,")
    print("the classical model is under-detecting canopy in composition units (not proxy units).")

    with open(os.path.join(a.out, "_notes.txt"), "w") as f:
        f.write(f"satellite_green_fraction={sat_green}\n")
        f.write(f"per_class_LST={json.dumps(lst)}\n")
        f.write("soil modes: measured=bare 36.29 (n=1); excluded=renormalized; organic=grass LST 30.13\n")
        f.write("shrub assigned canopy/tree LST (no local shrub class in differential)\n")
    print("\n[wrote] _notes.txt  (weights, satellite green, soil-mode definitions)")


if __name__ == "__main__":
    main()
