"""
soil/validate/normalize_yt_comments.py
Kalli A. Hale | October 2026 | rewildingCities

Raw YouTube provider JSON -> one typed comment_corpus table.

TAXONOMY NOTE. By the standing ruling, a lossless container swap is an
acquisition UTILITY and earns no Envelope. This step is close to that line
but lands on the other side of it: it DROPS fields (display name, avatar),
COERCES types, and MINTS a stable row key. Dropping identity fields is an
interpretive act with consequences downstream, so it is recorded rather
than done invisibly. If you rule otherwise, demote it to a plain function
in soil/acquire and nothing else in the chain changes.

Contract: canopy/pr_io.py (three args, stdout metadata).
  inputs : {"raw": <provider JSON written by YouTubeCommentsProvider>}
  output : comment_corpus (.csv)
  params : {"case_id": null (else taken from the payload),
            "drop_empty_text": true,
            "min_chars": 1}
"""
import csv
import json

try:
    from canopy.pr_io import (parse_primitive_args, get_input, get_param,
                              WarningsCollector, primitive_success,
                              primitive_failure, primitive_error_handling)
except ImportError:
    from pr_io import (parse_primitive_args, get_input, get_param,
                       WarningsCollector, primitive_success,
                       primitive_failure, primitive_error_handling)

PRIMITIVE = "normalize_yt_comments"

COLUMNS = ["comment_id", "case_id", "video_id", "parent_id", "is_reply",
           "text", "n_chars", "published_at", "like_count", "author_channel_id"]


def _canonical(text):
    """Collapse line endings to \n before anything measures or stores the text.

    Left alone, a CRLF survives into the file and is read back as LF by the
    csv module, so a length recorded at write time quietly disagrees with the
    text read at the other end. Normalising HERE makes that a deliberate,
    counted act rather than an invisible one ~ the stored text is the text
    every later step sees. ~
    """
    if "\r" not in text:
        return text, False
    return text.replace("\r\n", "\n").replace("\r", "\n"), True


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def main():
    w = WarningsCollector(PRIMITIVE)
    with primitive_error_handling(warnings=w):
        args = parse_primitive_args()
        raw_path = get_input(args["inputs"], "raw")
        p = args["params"]

        with open(raw_path, encoding="utf-8") as fh:
            payload = json.load(fh)

        case_id = get_param(p, "case_id") or payload.get("case_id")
        if not case_id:
            primitive_failure(
                "Missing case_id",
                "neither the payload nor params names a case; a corpus with no "
                "case cannot join to the registry")

        drop_empty = get_param(p, "drop_empty_text", True)
        min_chars = _int(get_param(p, "min_chars", 1)) or 1

        records = payload.get("comments") or []
        if not records:
            primitive_failure("Empty corpus",
                              f"{raw_path} carries no comments")

        rows, seen = [], set()
        dropped_empty = dropped_dupe = n_crlf = 0

        for r in records:
            cid = r.get("comment_id")
            if cid is None:
                dropped_empty += 1
                continue
            if cid in seen:
                dropped_dupe += 1
                continue
            seen.add(cid)

            text, normalized = _canonical((r.get("text") or "").strip())
            if normalized:
                n_crlf += 1
            if drop_empty and len(text) < min_chars:
                dropped_empty += 1
                continue

            parent = r.get("parent_id")
            rows.append({
                "comment_id": cid,
                "case_id": case_id,
                "video_id": r.get("video_id"),
                "parent_id": parent,
                "is_reply": 1 if parent else 0,
                "text": text,
                "n_chars": len(text),
                "published_at": r.get("published_at"),
                "like_count": _int(r.get("like_count")),
                "author_channel_id": r.get("author_channel_id"),
            })

        if not rows:
            primitive_failure("Empty after normalization",
                              "every record was dropped; nothing to type")

        # an id that repeats is a fact about the pull, not a tidy-up to hide
        if dropped_dupe:
            w.warn(f"{dropped_dupe} duplicate comment_id(s) dropped")
        if dropped_empty:
            w.info(f"{dropped_empty} record(s) dropped as empty or unidentified")

        if n_crlf:
            w.info(f"{n_crlf} comment(s) had line endings normalised to LF")

        undated = sum(1 for r in rows if not r["published_at"])
        if undated:
            w.warn(
                  f"{undated} comment(s) carry no timestamp; they cannot be "
                  f"windowed and will not enter a stratified draw")

        out = args["output"]
        with open(out, "w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=COLUMNS)
            wr.writeheader()
            wr.writerows(rows)

        primitive_success({
            "output_path": out,
            "semantic_type": "comment_corpus",
            "data_category": "tabular",
            "case_id": case_id,
            "n_comments": len(rows),
            "n_top_level": sum(1 for r in rows if not r["is_reply"]),
            "n_replies": sum(1 for r in rows if r["is_reply"]),
            "n_videos": len({r["video_id"] for r in rows}),
            "n_authors": len({r["author_channel_id"] for r in rows
                              if r["author_channel_id"]}),
            "n_undated": undated,
            "dropped_duplicate": dropped_dupe,
            "dropped_empty": dropped_empty,
            "n_newline_normalized": n_crlf,
            "source_fetched_at": payload.get("fetched_at"),
        }, warnings=w)


if __name__ == "__main__":
    main()