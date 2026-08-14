"""
roots/metrics/cooling_differential.py
Kalli A. Hale | August 2026 | rewildingCities

The thermal anchor: how much cooler is forest land cover than open land cover,
measured from satellite surface temperature. This is the climate half of the
project, and it connects to the perception half: it asks whether the land-cover
distinctions we can (or cannot) read from a photo actually correspond to a
temperature difference on the ground.

Two rasters, different grids: Landsat LST (~30 m) and ESA WorldCover (10 m).
They are reconciled by resampling LAND COVER onto the LST grid by MAJORITY vote,
so each temperature pixel is counted once with its dominant class. Land cover is
NOT interpolated to a finer grid, and LST is NOT upsampled: inventing thermal
resolution the sensor never had would be a silent lie about precision.

The differential is a RELATIVE measure (open minus forest), so it is robust to
absolute LST calibration. At ~30 m over a 2.6 sq mi CDP this is an anchor:
direction and approximate magnitude, not fine spatial detail. The manifest says
as much; the primitive reports pixel counts so the reader can judge.

Contract: canopy/pr_io.py (three args, stdout metadata). EnvelopeBuilder wraps.
  inputs : {"lst": <LST GeoTIFF, Celsius>, "land_cover": <categorical GeoTIFF>}
  output : cooling_differential JSON
  params : {"forest_classes": [10], "open_classes": [30, 40],
            "central_tendency": "median", "lst_nodata": null, "lc_nodata": 0,
            "min_pixels": 20}
  ESA WorldCover codes: 10 tree, 20 shrub, 30 grassland, 40 cropland,
  50 built-up, 60 bare, 80 water, 90 wetland.
"""
import numpy as np

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "cooling_differential"


def _summ(lst_values):
    return {"n": int(lst_values.size),
            "mean": round(float(lst_values.mean()), 3),
            "median": round(float(np.median(lst_values)), 3),
            "std": round(float(lst_values.std()), 3)}


def cooling_differential_stats(lst, lc, valid, forest_classes, open_classes,
                               central_tendency):
    """Pure over arrays (numpy only), so it is unit-testable without rasterio.
    Returns per-class LST summaries, the forest and open group summaries, and
    the open-minus-forest differential (positive => forest is cooler)."""
    per_class = {}
    for c in sorted(int(x) for x in np.unique(lc[valid])):
        m = valid & (lc == c)
        if m.any():
            per_class[c] = _summ(lst[m])

    def group(classes):
        m = valid & np.isin(lc, list(classes))
        return (_summ(lst[m]) if m.any() else None)

    forest = group(forest_classes)
    openg = group(open_classes)

    differential = None
    if forest and openg:
        k = central_tendency
        differential = {
            "central_tendency": k,
            "forest_lst": forest[k],
            "open_lst": openg[k],
            "open_minus_forest": round(openg[k] - forest[k], 3),
            "mean_differential": round(openg["mean"] - forest["mean"], 3),
            "median_differential": round(openg["median"] - forest["median"], 3),
        }
    return {"per_class": per_class, "forest": forest, "open": openg,
            "differential": differential}


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        import json
        import os
        import rasterio
        from rasterio.warp import reproject, Resampling

        args = parse_primitive_args()
        lst_path = get_input(args["inputs"], "lst")
        lc_path = get_input(args["inputs"], "land_cover")
        p = args["params"]
        forest_classes = get_param(p, "forest_classes", [10])
        open_classes = get_param(p, "open_classes", [30, 40])
        central = get_param(p, "central_tendency", "median")
        lst_nodata_param = get_param(p, "lst_nodata", None)
        lc_nodata = get_param(p, "lc_nodata", 0)
        min_pixels = int(get_param(p, "min_pixels", 20))

        with rasterio.open(lst_path) as lst_ds:
            lst = lst_ds.read(1).astype(np.float32)
            lst_nodata = lst_nodata_param if lst_nodata_param is not None \
                else lst_ds.nodata
            lst_crs, lst_tr, lst_shape = lst_ds.crs, lst_ds.transform, lst.shape

        # Resample land cover onto the LST grid by MAJORITY (categorical-safe).
        lc = np.zeros(lst_shape, dtype=np.int32)
        with rasterio.open(lc_path) as lc_ds:
            reproject(source=rasterio.band(lc_ds, 1), destination=lc,
                      src_transform=lc_ds.transform, src_crs=lc_ds.crs,
                      dst_transform=lst_tr, dst_crs=lst_crs,
                      resampling=Resampling.mode)

        valid = np.isfinite(lst)
        if lst_nodata is not None:
            valid &= (lst != lst_nodata)
        valid &= (lc != lc_nodata)

        n_valid = int(valid.sum())
        if n_valid == 0:
            primitive_failure("No valid pixels",
                              "LST and land cover do not overlap on valid data "
                              "after nodata masking; check CRS/extent.", w)
        frac_valid = n_valid / float(lst.size)
        if frac_valid < 0.5:
            w.warn(f"only {frac_valid*100:.0f}% of pixels are valid after nodata "
                   f"masking; LST nodata coverage may bias the result.")

        result = cooling_differential_stats(lst, lc, valid, forest_classes,
                                            open_classes, central)

        # honesty guards on the two groups that carry the headline
        for label, grp, classes in (("forest", result["forest"], forest_classes),
                                     ("open", result["open"], open_classes)):
            if grp is None:
                w.warn(f"no {label} pixels (classes {classes}) present; "
                       f"differential cannot be computed.")
            elif grp["n"] < min_pixels:
                w.warn(f"{label} has only {grp['n']} LST pixels "
                       f"(classes {classes}); differential is unreliable at this "
                       f"resolution.")

        d = result["differential"]
        if d:
            direction = ("forest cooler" if d["open_minus_forest"] > 0
                         else "forest warmer" if d["open_minus_forest"] < 0
                         else "no difference")
            w.info(f"forest {d['forest_lst']} C vs open {d['open_lst']} C "
                   f"({central}); differential {d['open_minus_forest']:+} C "
                   f"({direction}).")

        out = args["output"]
        od = os.path.dirname(os.path.abspath(out))
        if od:
            os.makedirs(od, exist_ok=True)
        with open(out, "w") as f:
            json.dump(result, f, indent=2)

        meta = {"primitive": PRIMITIVE, "output": out,
                "forest_classes": forest_classes, "open_classes": open_classes,
                "central_tendency": central, "n_valid_px": n_valid,
                "valid_fraction": round(frac_valid, 4),
                "differential": result["differential"]}
        primitive_success(meta, w)


if __name__ == "__main__":
    main()
