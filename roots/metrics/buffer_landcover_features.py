"""
roots/metrics/buffer_landcover_features.py
Kalli A. Hale | August 2026 | rewildingCities

The buffer-principle feature builder for predicting temperature from land cover.
Draws random sample points across the scene and, for each, computes the
land-cover composition within a buffer around it (what SURROUNDS the point,
following Xiao's buffer analysis) as predictors, paired with the point's LST as
the target. The output feature table feeds split_dataset -> train_regressor ->
score_regression.

Land cover is collapsed to blue-green-grey so the predictors are few and
interpretable (green = vegetation, grey = built/bare, blue = water), the same
trichotomy the platform uses elsewhere. These three fractions sum to ~1, i.e.
they are compositional, so read their effect via random-forest importances or a
reference-dropped linear model, train_regressor warns about this.

Rasters are reconciled the same way as cooling_differential: land cover is
majority-resampled onto the LST grid, never the reverse.

Contract: canopy/pr_io.py (three args, stdout metadata).
  inputs : {"lst": <LST GeoTIFF>, "land_cover": <categorical GeoTIFF>}
  output : feature table (.csv/.parquet): id, x, y, green, grey, blue, lst
  params : {"n_samples": 1500, "buffer_radius_m": 100, "seed": 0,
            "bgg_mapping": {"green":[10,20,30,40,90,95,100],"grey":[50,60],
                            "blue":[80]},
            "lst_nodata": null, "lc_nodata": 0, "min_buffer_valid": 10}
"""
import numpy as np

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "buffer_landcover_features"
DEFAULT_BGG = {"green": [10, 20, 30, 40, 90, 95, 100], "grey": [50, 60], "blue": [80]}


def sample_buffer_fractions(lst, lc, valid, rows, cols, rpix, bgg_map,
                            min_buffer_valid):
    """Pure over arrays (numpy only): for each sample pixel, the fraction of each
    BGG group among valid land-cover pixels in its buffer, plus the point LST.
    Unit-testable without rasterio."""
    H, W = lst.shape
    recs = []
    for k, (r, c) in enumerate(zip(rows, cols)):
        r0, r1 = max(0, r - rpix), min(H, r + rpix + 1)
        c0, c1 = max(0, c - rpix), min(W, c + rpix + 1)
        wv = valid[r0:r1, c0:c1]
        n = int(wv.sum())
        if n < min_buffer_valid:
            continue
        wlc = lc[r0:r1, c0:c1]
        rec = {"id": k, "row": int(r), "col": int(c), "lst": float(lst[r, c])}
        for name, classes in bgg_map.items():
            rec[name] = round(float(np.isin(wlc, classes)[wv].sum()) / n, 5)
        recs.append(rec)
    return recs


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        import os
        import rasterio
        from rasterio.warp import reproject, Resampling
        import pandas as pd

        args = parse_primitive_args()
        lst_path = get_input(args["inputs"], "lst")
        lc_path = get_input(args["inputs"], "land_cover")
        p = args["params"]
        n_samples = int(get_param(p, "n_samples", 1500))
        buffer_radius_m = float(get_param(p, "buffer_radius_m", 100))
        seed = int(get_param(p, "seed", 0))
        bgg_map = get_param(p, "bgg_mapping", DEFAULT_BGG)
        lst_nodata_param = get_param(p, "lst_nodata", None)
        lc_nodata = get_param(p, "lc_nodata", 0)
        min_buffer_valid = int(get_param(p, "min_buffer_valid", 10))

        with rasterio.open(lst_path) as lst_ds:
            lst = lst_ds.read(1).astype(np.float32)
            lst_nodata = lst_nodata_param if lst_nodata_param is not None else lst_ds.nodata
            tr, crs, shape = lst_ds.transform, lst_ds.crs, lst.shape
            pixel_m = abs(tr.a)

        lc = np.zeros(shape, dtype=np.int32)
        with rasterio.open(lc_path) as lc_ds:
            reproject(source=rasterio.band(lc_ds, 1), destination=lc,
                      src_transform=lc_ds.transform, src_crs=lc_ds.crs,
                      dst_transform=tr, dst_crs=crs, resampling=Resampling.mode)

        valid = np.isfinite(lst)
        if lst_nodata is not None:
            valid &= (lst != lst_nodata)
        valid &= (lc != lc_nodata)

        rpix = max(1, int(round(buffer_radius_m / pixel_m)))
        w.info(f"pixel size {pixel_m:.1f} m; buffer radius {buffer_radius_m} m "
               f"= {rpix} px; {int(valid.sum())} valid pixels.")

        vr, vc = np.where(valid)
        if len(vr) == 0:
            primitive_failure("No valid pixels", "check nodata/overlap", w)
        rng = np.random.default_rng(seed)
        take = min(n_samples, len(vr))
        pick = rng.choice(len(vr), size=take, replace=False)
        rows, cols = vr[pick], vc[pick]

        recs = sample_buffer_fractions(lst, lc, valid, rows, cols, rpix, bgg_map,
                                       min_buffer_valid)
        if len(recs) < 10:
            primitive_failure("Too few samples",
                              f"only {len(recs)} points had enough valid buffer", w)
        df = pd.DataFrame(recs)
        # pixel (row,col) -> map x,y so split_dataset can block spatially in meters
        xs, ys = rasterio.transform.xy(tr, df["row"].to_numpy(), df["col"].to_numpy())
        df["x"], df["y"] = np.asarray(xs), np.asarray(ys)
        df = df[["id", "x", "y"] + list(bgg_map.keys()) + ["lst"]]

        out = args["output"]
        d = os.path.dirname(os.path.abspath(out))
        if d:
            os.makedirs(d, exist_ok=True)
        df.to_csv(out, index=False) if out.endswith(".csv") else df.to_parquet(out, index=False)

        primitive_success({
            "primitive": PRIMITIVE, "output": out, "n_samples": int(len(df)),
            "buffer_radius_m": buffer_radius_m, "buffer_px": rpix,
            "features": list(bgg_map.keys()),
            "lst_mean": round(float(df["lst"].mean()), 3),
            "green_mean_fraction": round(float(df["green"].mean()), 3),
        }, w)


if __name__ == "__main__":
    main()
