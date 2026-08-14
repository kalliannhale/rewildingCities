"""
soil/scope/split_dataset.py
Kalli A. Hale | August 2026 | rewildingCities

Split an abstract sample-index into train / test / val partitions. Deliberately
domain-agnostic: it operates on a table of SAMPLE RECORDS (an id, and optionally
a label to stratify on, a group to keep intact, coordinates for spatial blocks,
a time column for temporal order), never on rasters or geometries directly. Each
domain produces that little table its own way and consumes the partition its own
way, so this one primitive serves classification, regression, spatial CV, etc.

The `strategy` is an epistemological choice, not a knob:
  random     - shuffle and cut. Fine for independent rows; leaky for pixels.
  stratified - preserve label proportions across partitions.
  grouped    - keep each group wholly in one partition (identity leakage guard;
               e.g. group_by=frame so no frame straddles train and test).
  spatial    - split by coordinate blocks (geospatial CV; places, not rows).
  temporal   - sort by time and cut so test is strictly later than train
               (lookahead leakage guard).

Grouped and temporal answer DIFFERENT leakage questions (identity vs lookahead);
composing both at once is a future need this version does not handle. Temporal
and stratified pull against each other, so a temporal cut can leave a class out
of a partition; the primitive WARNS rather than proceeding silently.

Contract: canopy/pr_io.py (three args, stdout metadata). EnvelopeBuilder wraps.
  inputs : {"samples": <sample_index table, .parquet or .csv, with an id column>}
  output : dataset_partition table (input rows + a `partition` column)
  params : {strategy, test_frac=0.2, val_frac=0.0, seed=42, id_col="id",
            stratify_by, group_by, block_size, x_col="x", y_col="y", time_col}
"""
import os

import numpy as np
import pandas as pd

from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                          require_param, WarningsCollector, primitive_success,
                          primitive_failure, primitive_error_handling)

PRIMITIVE = "split_dataset"


def _read(path):
    if path.endswith(".csv"):
        return pd.read_csv(path)
    if path.endswith((".parquet", ".pq")):
        return pd.read_parquet(path)
    try:
        return pd.read_parquet(path)
    except Exception:
        return pd.read_csv(path)


def _write(df, path):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    if path.endswith(".csv"):
        df.to_csv(path, index=False)
    else:
        df.to_parquet(path, index=False)


def _cut(n, test_frac, val_frac):
    """Sizes for (train, val, test) given n and the two fractions."""
    n_test = int(round(test_frac * n))
    n_val = int(round(val_frac * n))
    n_train = n - n_test - n_val
    return n_train, n_val, n_test


def _labels_for_order(order, n_train, n_val, n_test):
    """Assign partition labels to items in a given order (train first)."""
    lab = np.array(["train"] * n_train + ["val"] * n_val + ["test"] * n_test)
    out = np.empty(len(order), dtype=object)
    out[order] = lab
    return out


def _assign_units(unit_ids, test_frac, val_frac, rng):
    """Group/spatial: assign whole UNITS (groups or blocks) to partitions."""
    units = np.array(sorted(pd.unique(unit_ids), key=str))
    perm = rng.permutation(len(units))
    n_train, n_val, n_test = _cut(len(units), test_frac, val_frac)
    unit_part = {}
    labels = ["train"] * n_train + ["val"] * n_val + ["test"] * n_test
    for u_idx, part in zip(perm, labels):
        unit_part[units[u_idx]] = part
    return np.array([unit_part[u] for u in unit_ids], dtype=object)


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        args = parse_primitive_args()
        df = _read(get_input(args["inputs"], "samples")).reset_index(drop=True)
        p = args["params"]

        strategy = get_param(p, "strategy", "grouped")
        test_frac = float(get_param(p, "test_frac", 0.2))
        val_frac = float(get_param(p, "val_frac", 0.0))
        seed = int(get_param(p, "seed", 42))
        id_col = get_param(p, "id_col", "id")
        stratify_by = get_param(p, "stratify_by", None)
        group_by = get_param(p, "group_by", None)
        block_size = get_param(p, "block_size", None)
        x_col = get_param(p, "x_col", "x")
        y_col = get_param(p, "y_col", "y")
        time_col = get_param(p, "time_col", None)

        if id_col not in df.columns:
            primitive_failure("Missing id column",
                              f"'{id_col}' not in samples: {list(df.columns)}", w)
        if test_frac < 0 or val_frac < 0 or (test_frac + val_frac) >= 1:
            primitive_failure("Bad fractions",
                              f"test_frac+val_frac must be in [0,1): "
                              f"{test_frac}+{val_frac}", w)

        n = len(df)
        rng = np.random.default_rng(seed)

        if strategy == "random":
            order = rng.permutation(n)
            nt, nv, nte = _cut(n, test_frac, val_frac)
            part = _labels_for_order(order, nt, nv, nte)

        elif strategy == "stratified":
            if not stratify_by or stratify_by not in df.columns:
                primitive_failure("Missing stratify_by",
                                  f"strategy=stratified needs a valid stratify_by "
                                  f"column; got '{stratify_by}'", w)
            part = np.empty(n, dtype=object)
            for _, idx in df.groupby(stratify_by).groups.items():
                idx = np.array(list(idx))
                order = rng.permutation(len(idx))
                nt, nv, nte = _cut(len(idx), test_frac, val_frac)
                part[idx] = _labels_for_order(order, nt, nv, nte)

        elif strategy == "grouped":
            if not group_by or group_by not in df.columns:
                primitive_failure("Missing group_by",
                                  f"strategy=grouped needs a valid group_by "
                                  f"column; got '{group_by}'", w)
            part = _assign_units(df[group_by].to_numpy(), test_frac, val_frac, rng)

        elif strategy == "spatial":
            if block_size is None or x_col not in df.columns or y_col not in df.columns:
                primitive_failure("Missing spatial inputs",
                                  f"strategy=spatial needs block_size and "
                                  f"'{x_col}'/'{y_col}' columns", w)
            bx = np.floor(df[x_col].to_numpy() / float(block_size)).astype(int)
            by = np.floor(df[y_col].to_numpy() / float(block_size)).astype(int)
            blocks = np.array([f"{a}_{b}" for a, b in zip(bx, by)])
            part = _assign_units(blocks, test_frac, val_frac, rng)

        elif strategy == "temporal":
            if not time_col or time_col not in df.columns:
                primitive_failure("Missing time_col",
                                  f"strategy=temporal needs a valid time_col; "
                                  f"got '{time_col}'", w)
            order_by_time = np.argsort(df[time_col].to_numpy(), kind="stable")
            nt, nv, nte = _cut(n, test_frac, val_frac)
            part = np.empty(n, dtype=object)
            part[order_by_time[:nt]] = "train"
            part[order_by_time[nt:nt + nv]] = "val"
            part[order_by_time[nt + nv:]] = "test"
        else:
            primitive_failure("Unknown strategy",
                              f"'{strategy}' not in random/stratified/grouped/"
                              f"spatial/temporal", w)

        df = df.copy()
        df["partition"] = part

        # ---- honesty checks -------------------------------------------------
        counts = {k: int(v) for k, v in pd.Series(part).value_counts().items()}
        for need in (["train", "test"] + (["val"] if val_frac > 0 else [])):
            if counts.get(need, 0) == 0:
                lvl = "critical" if need == "test" else "warning"
                w.add(lvl, PRIMITIVE, f"partition '{need}' is empty; check "
                      f"fractions vs the number of units.")

        # temporal can leave a class out of a partition (tension w/ stratified)
        class_col = stratify_by if (stratify_by in df.columns) else None
        if strategy == "temporal" and class_col:
            all_classes = set(df[class_col].unique())
            for pk in df["partition"].unique():
                missing = all_classes - set(df.loc[df["partition"] == pk, class_col].unique())
                if missing:
                    w.warn(f"temporal split leaves partition '{pk}' missing "
                           f"class(es) {sorted(map(str, missing))}; temporal and "
                           f"stratified cannot both be satisfied by one flat cut.")

        _write(df, args["output"])

        actual_frac = {k: round(v / n, 4) for k, v in counts.items()}
        metadata = {
            "primitive": PRIMITIVE,
            "output": args["output"],
            "strategy": strategy,
            "n_samples": n,
            "id_col": id_col,
            "seed": seed,
            "requested": {"test_frac": test_frac, "val_frac": val_frac},
            "counts": counts,
            "actual_fraction": actual_frac,
        }
        if strategy in ("grouped", "spatial"):
            unit_col = group_by if strategy == "grouped" else f"{x_col}/{y_col} blocks"
            metadata["n_units"] = int(pd.unique(
                df[group_by]).size if strategy == "grouped" else len(set(
                    f"{a}_{b}" for a, b in zip(
                        np.floor(df[x_col] / float(block_size)).astype(int),
                        np.floor(df[y_col] / float(block_size)).astype(int)))))
            metadata["unit"] = unit_col
        primitive_success(metadata, w)


if __name__ == "__main__":
    main()
