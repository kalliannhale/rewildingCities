"""
scratch/pilot_pull.py

PILOT acquisition for megan_2022. Not a primitive, not wired to the
orchestrator: a throwaway that calls the YouTube provider directly so real
comments exist before the vocabulary and manifest are written (Route A).

Pilot videos are looked at and pilot-coded; they do NOT enter the final
sample unless the selection protocol would have chosen them anyway.

Usage, from the repo root:
    export YOUTUBE_API_KEY="..."
    python3 tests/pilot_pull.py VIDEO_ID [VIDEO_ID ...]
    python3 tests/pilot_pull.py --max-threads 2000 VIDEO_ID [VIDEO_ID ...]

Writes (uncapped):
    plots/internet/megan_2022/.data/yt_raw.json
    plots/internet/megan_2022/.data/yt_raw_provenance.json
Writes (capped) ~ a different name, so a capped pull can never be mistaken
for a complete one or collide with an uncapped pull running alongside it:
    plots/internet/megan_2022/.data/yt_raw_capped<N>.json
    plots/internet/megan_2022/.data/yt_raw_capped<N>_provenance.json

CAP CAVEAT: the cap counts TOP-LEVEL threads (replies come on top), is checked
per page of 100, and comments arrive newest-first. A capped pull is the most
RECENT slice of a section, not a sample of it. Fine for pilot coding; never
for estimating anything about the section over time.
"""

import json
import logging
import os
import sys
from pathlib import Path

# make `canopy` importable no matter where this file lives in the repo
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from canopy.providers.youtube import YouTubeCommentsProvider  # noqa: E402

CASE_ID = "megan_2022"
DATA_DIR = REPO_ROOT / "plots" / "internet" / CASE_ID / ".data"


def main(argv: list[str]) -> int:
    max_threads = None
    if argv[:1] == ["--max-threads"]:
        if len(argv) < 2 or not argv[1].isdigit():
            print("--max-threads needs a whole number, e.g. --max-threads 2000")
            return 2
        max_threads, argv = int(argv[1]), argv[2:]
    video_ids = argv

    if not video_ids:
        print("give at least one video id: python3 scratch/pilot_pull.py ID [ID ...]")
        return 2
    if not os.environ.get("YOUTUBE_API_KEY"):
        print("YOUTUBE_API_KEY is not set in this shell. export it and rerun.")
        return 2

    stem = "yt_raw" if max_threads is None else f"yt_raw_capped{max_threads}"
    cache_path = DATA_DIR / f"{stem}.json"
    if cache_path.exists():
        print(f"{cache_path} already exists. Move or delete it first; "
              "this script will not overwrite a pull.")
        return 2

    source_config = {
        "type": "api",
        "provider": "youtube_comments",
        "case_id": CASE_ID,
        "video_ids": video_ids,
    }
    if max_threads is not None:
        # newest-first + cap = only the most recent slice. Allowed for the
        # pilot, and the filename says so.
        source_config["max_threads_per_video"] = max_threads
        print(f"CAPPED pull: newest ~{max_threads} threads per video, plus their replies.")

    # show the provider's per-video progress lines so a long pull doesn't
    # look frozen
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        datefmt="%H:%M:%S")

    result = YouTubeCommentsProvider().acquire(source_config, cache_path, stem)

    print(f"\nsuccess: {result.success}")
    print(f"message: {result.message}")
    for w in result.warnings or []:
        print(f"[{w['level']}] {w['message']}")

    prov = result.provenance or {}
    if prov:
        print("\nper video:")
        for v in prov.get("videos", []):
            print(f"  {v['video_id']:<14} {v['status']:<9} "
                  f"{v['comment_count']:>6} comments  {v['api_calls']:>5} calls")
        if "quota_units_estimate" in prov:
            print(f"\nquota used (est.): {prov['quota_units_estimate']} of 10,000/day")
        if "top_level_count" in prov:
            print(f"top-level: {prov['top_level_count']}   replies: {prov['reply_count']}")

        # provenance never carries the key; keep it next to the raw file
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        prov_path = DATA_DIR / f"{stem}_provenance.json"
        with open(prov_path, "w") as f:
            json.dump(prov, f, indent=2)
        print(f"\nprovenance: {prov_path}")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))