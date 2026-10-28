"""
soil/validate/window_comments.py
Kalli A. Hale | October 2026 | rewildingCities

Assign each comment a timeline window within its case.

WHY THIS IS ITS OWN STEP. Comment volume is spiked: a case's corpus is mostly
the few days around an event. A draw taken from the corpus as a whole is
therefore a draw from the peak, and quiet-period discourse ~ which is where
the low end of the scale lives ~ never enters the sample. Windowing first
makes the quiet periods addressable, so the draw can reach them.

Windows are EQUAL IN TIME, not equal in volume. Equal-volume windows would
re-introduce the spike by making a busy day into many windows and a quiet
month into one.

Contract: canopy/pr_io.py (three args, stdout metadata).
  inputs : {"corpus": <comment_corpus .csv>}
  output : comment_corpus windowed (.csv) ~ adds window_index, window_start
  params : {"n_windows": 10,
            "start": null (else min observed timestamp),
            "end": null (else max observed timestamp),
            "drop_undated": true}
"""
import csv
from datetime import datetime, timezone

try:
    from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                              WarningsCollector, primitive_success,
                              primitive_failure, primitive_error_handling)
except ImportError:
    from pr_io import (parse_primitive_args, get_input, get_param,
                       WarningsCollector, primitive_success,
                       primitive_failure, primitive_error_handling)

PRIMITIVE = "window_comments"


def _ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        args = parse_primitive_args()
        path = get_input(args["inputs"], "corpus")
        p = args["params"]

        n_windows = int(get_param(p, "n_windows", 10))
        if n_windows < 1:
            primitive_failure("Bad parameter", "n_windows must be >= 1")
        drop_undated = get_param(p, "drop_undated", True)

        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            primitive_failure("Empty corpus", f"{path} has no rows")

        cases = {r.get("case_id") for r in rows}
        if len(cases) > 1:
            primitive_failure(
                "Mixed cases",
                f"corpus carries {len(cases)} case_ids; windows are defined "
                f"within a case, so split before windowing")

        for r in rows:
            r["_t"] = _ts(r.get("published_at"))

        dated = [r for r in rows if r["_t"] is not None]
        undated = [r for r in rows if r["_t"] is None]
        if not dated:
            primitive_failure("No timestamps",
                              "no comment carries a parseable timestamp")

        start = _ts(get_param(p, "start")) or min(r["_t"] for r in dated)
        end = _ts(get_param(p, "end")) or max(r["_t"] for r in dated)
        span = (end - start).total_seconds()
        if span <= 0:
            w.warn(
                  "every comment shares one timestamp; all rows land in window 0")
            span = 1.0

        out_rows = []
        for r in dated:
            frac = (r["_t"] - start).total_seconds() / span
            idx = min(int(frac * n_windows), n_windows - 1)
            if idx < 0:
                w.warn(
                      f"comment {r['comment_id']} predates the declared start; "
                      f"clamped to window 0")
                idx = 0
            r["window_index"] = idx
            r["window_start"] = (
                start.timestamp() + (span / n_windows) * idx)
            r.pop("_t")
            out_rows.append(r)

        if undated:
            msg = (f"{len(undated)} undated comment(s) "
                   + ("dropped" if drop_undated else "kept with window_index -1"))
            w.warn(msg)
            if not drop_undated:
                for r in undated:
                    r["window_index"] = -1
                    r["window_start"] = None
                    r.pop("_t")
                    out_rows.append(r)

        counts = {}
        for r in out_rows:
            counts[r["window_index"]] = counts.get(r["window_index"], 0) + 1

        # An empty window is not a defect to be smoothed away; it is the
        # quiet period being honest. It must still be visible, because a
        # later draw asked to sample it will refuse rather than silently
        # take its quota from elsewhere.
        empty = [i for i in range(n_windows) if counts.get(i, 0) == 0]
        if empty:
            w.info(
                  f"{len(empty)} of {n_windows} windows are empty: "
                  f"{empty}; a stratified draw cannot fill them")

        fields = [c for c in out_rows[0] if c != "_t"]
        with open(args["output"], "w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=fields)
            wr.writeheader()
            wr.writerows(out_rows)

        primitive_success({
            "output_path": args["output"],
            "semantic_type": "comment_corpus",
            "data_category": "tabular",
            "case_id": next(iter(cases)),
            "n_comments": len(out_rows),
            "n_windows": n_windows,
            "window_start_iso": start.isoformat(),
            "window_end_iso": end.isoformat(),
            "span_days": round(span / 86400, 2),
            "counts_by_window": {str(k): counts.get(k, 0)
                                 for k in range(n_windows)},
            "n_empty_windows": len(empty),
            "n_undated": len(undated),
        }, warnings=w)


if __name__ == "__main__":
    main()
