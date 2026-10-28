"""
canopy/providers/youtube.py

YouTube Data API v3 provider for comment threads.

Acquires the comment discourse attached to a set of videos. One video is a
vantage point, not a dataset; a case is assembled from several, so this
provider takes a LIST of video ids and writes one corpus.

Free, but key-gated and quota-metered.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from .base import Provider, AcquisitionResult, DiscoveryResult

logger = logging.getLogger("providers.youtube")

API_ROOT = "https://www.googleapis.com/youtube/v3"

# commentThreads.list and comments.list each cost 1 quota unit per call,
# regardless of page size. The default daily ceiling is 10,000 units. We
# record the count rather than enforce it: a provider that silently stops
# at a budget would truncate exactly like the ArcGIS bug this file is
# written to avoid.
PAGE_SIZE = 100


class YouTubeCommentsProvider(Provider):
    """Acquires comment threads from the YouTube Data API v3."""

    @property
    def name(self) -> str:
        return "YouTube Data API (comments)"

    def can_handle(self, source_config: dict) -> bool:
        return (
            source_config.get("type") == "api"
            and source_config.get("provider") == "youtube_comments"
        )

    # ──────────────────────────────────────────────────────────────────────
    # fetch
    # ──────────────────────────────────────────────────────────────────────

    def _page(self, requests, path: str, params: dict, timeout: int = 60):
        """One API call. Returns (doc, error_reason). Never raises for an
        API-level refusal: a disabled comment section is a FACT about the
        video, not a failure of acquisition, and it has to reach provenance
        intact rather than as an exception string."""
        resp = requests.get(f"{API_ROOT}/{path}", params=params, timeout=timeout)
        if resp.status_code == 403:
            try:
                reason = resp.json()["error"]["errors"][0].get("reason", "forbidden")
            except Exception:
                reason = "forbidden"
            return None, reason
        if resp.status_code == 404:
            return None, "notFound"
        resp.raise_for_status()
        return resp.json(), None

    def _fetch_replies(self, requests, parent_id: str,
                       key: str) -> tuple[list, int, str | None]:
        """Full reply chain for one top-level comment.

        commentThreads.list returns at most ~5 replies inline no matter what
        is asked of it. Taking those as the whole thread would understate
        reply volume on exactly the threads that drew the most argument ~ the
        same silent truncation as a FeatureServer page read as a full layer.
        So any thread claiming more replies than came inline is re-fetched
        in full through comments.list.

        Returns (replies, calls, reason). reason is None on a clean fetch and
        the API's refusal reason otherwise (e.g. quotaExceeded). A failed
        re-fetch must say so: dropping the reason here is how a thread loses
        its replies without anyone being told.
        """
        out, calls, token, reason = [], 0, None, None
        while True:
            params = {"part": "snippet", "parentId": parent_id,
                      "maxResults": PAGE_SIZE, "key": key, "textFormat": "plainText"}
            if token:
                params["pageToken"] = token
            doc, reason = self._page(requests, "comments", params)
            calls += 1
            if doc is None:
                break
            out.extend(doc.get("items") or [])
            token = doc.get("nextPageToken")
            if not token:
                break
        return out, calls, reason

    def _fetch_video(self, requests, video_id: str, key: str,
                     max_threads: int | None) -> dict:
        """Every comment thread on one video, with its full reply chains."""
        threads: list = []
        token, calls, reason = None, 0, None

        while True:
            params = {"part": "snippet,replies", "videoId": video_id,
                      "maxResults": PAGE_SIZE, "order": "time",
                      "key": key, "textFormat": "plainText"}
            if token:
                params["pageToken"] = token

            doc, reason = self._page(requests, "commentThreads", params)
            calls += 1
            if doc is None:
                break

            page = doc.get("items") or []
            threads.extend(page)
            token = doc.get("nextPageToken")

            # stop on absence of a token, not on a short page: YouTube will
            # return fewer than maxResults and still hand back a token.
            if not token:
                break
            if max_threads is not None and len(threads) >= max_threads:
                reason = "stopped_at_max_threads"
                break

        records: list[dict] = []
        reply_calls = 0
        reply_failures: list[dict] = []
        for t in threads:
            top = t.get("snippet", {}).get("topLevelComment", {})
            tsnip = top.get("snippet", {})
            records.append(self._record(top.get("id"), tsnip, video_id, parent_id=None))

            declared = t.get("snippet", {}).get("totalReplyCount", 0) or 0
            inline = (t.get("replies") or {}).get("comments") or []

            if declared > len(inline):
                full, c, r_reason = self._fetch_replies(requests, top.get("id"), key)
                reply_calls += c
                if r_reason is None:
                    source = full
                else:
                    # The re-fetch failed partway (or at once). Keep whichever
                    # set is larger so a failure never leaves a thread with
                    # FEWER replies than it arrived with, and record it.
                    source = full if len(full) >= len(inline) else inline
                    reply_failures.append({
                        "thread_id": top.get("id"),
                        "reason": r_reason,
                        "declared_replies": declared,
                        "kept_replies": len(source),
                    })
            else:
                source = inline

            for r in source:
                records.append(self._record(r.get("id"), r.get("snippet", {}),
                                            video_id, parent_id=top.get("id")))

        # Three outcomes, never two. "refused" means nothing came back;
        # "partial" means comments came back but the record is incomplete,
        # either because thread paging stopped early or because some reply
        # chains failed. Calling a partial video "refused" hides real data;
        # calling it "ok" hides the gap.
        if not records:
            status = "refused"
        elif reason or reply_failures:
            status = "partial"
        else:
            status = "ok"

        return {
            "video_id": video_id,
            "records": records,
            "thread_count": len(threads),
            "comment_count": len(records),
            "api_calls": calls + reply_calls,
            "status": status,
            "reason": reason,                 # thread-level stop reason, if any
            "reply_failures": reply_failures, # per-thread reply gaps, if any
        }

    @staticmethod
    def _record(cid, snip: dict, video_id: str, parent_id: str | None) -> dict:
        """One comment, flattened to the fields the corpus needs.

        Author CHANNEL ID is kept because it is the only stable handle for
        'same account, two comments' and the sampling design needs that.
        Display name and avatar are dropped: they identify a person and the
        analysis never asks who anyone is.
        """
        return {
            "comment_id": cid,
            "video_id": video_id,
            "parent_id": parent_id,
            "text": snip.get("textOriginal") or snip.get("textDisplay"),
            "published_at": snip.get("publishedAt"),
            "updated_at": snip.get("updatedAt"),
            "like_count": snip.get("likeCount"),
            "author_channel_id": (snip.get("authorChannelId") or {}).get("value"),
        }

    # ──────────────────────────────────────────────────────────────────────
    # acquire
    # ──────────────────────────────────────────────────────────────────────

    def acquire(self, source_config, cache_path, dataset_name, **kwargs):
        import os
        import requests

        key = (kwargs.get("youtube_api_key")
               or source_config.get("api_key_env")
               and os.environ.get(source_config["api_key_env"])
               or os.environ.get("YOUTUBE_API_KEY"))

        if not key:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=f"YouTube API key required for '{dataset_name}'.",
                requires_auth=True,
                auth_instructions=(
                    "To set up the YouTube Data API:\n"
                    "  1. Create a project at https://console.cloud.google.com/\n"
                    "  2. Enable 'YouTube Data API v3'\n"
                    "  3. Create an API key (no OAuth needed for public comments)\n"
                    "  4. export YOUTUBE_API_KEY=...\n"
                    "Default quota is 10,000 units/day; one page of 100 comments "
                    "costs 1 unit."
                ),
                warnings=[{
                    "level": "info",
                    "primitive": "youtube_provider",
                    "message": f"'{dataset_name}' needs a YouTube Data API key.",
                }],
            )

        video_ids = source_config.get("video_ids") or (
            [source_config["video_id"]] if source_config.get("video_id") else [])
        if not video_ids:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message="YouTube source declares neither 'video_ids' nor 'video_id'.",
            )

        max_threads = source_config.get("max_threads_per_video")
        started = time.time()

        videos, records, refused, partial = [], [], [], []
        try:
            for vid in video_ids:
                logger.info(f"  YouTube: commentThreads for {vid}")
                res = self._fetch_video(requests, vid, key, max_threads)
                records.extend(res.pop("records"))
                videos.append(res)
                if res["status"] == "refused":
                    refused.append({"video_id": vid,
                                    "reason": res["reason"] or "empty"})
                elif res["status"] == "partial":
                    partial.append({
                        "video_id": vid,
                        "reason": res["reason"],
                        "reply_failures": len(res["reply_failures"]),
                        "comment_count": res["comment_count"],
                    })
        except Exception as e:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=f"YouTube fetch failed: {e}",
            )

        # Every video refusing is not a thin corpus, it is no corpus. Writing
        # an empty file here would let a case enter the registry looking
        # acquired.
        if not records:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=("no comments returned for any declared video "
                         f"({len(refused)} refused: "
                         f"{', '.join(r['reason'] for r in refused) or 'empty'})"),
                provenance={"videos": videos, "refused": refused},
                warnings=[{
                    "level": "critical",
                    "primitive": "youtube_provider",
                    "message": f"'{dataset_name}' acquired nothing.",
                }],
            )

        payload = {
            "dataset": dataset_name,
            "source": "youtube_data_api_v3",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "case_id": source_config.get("case_id"),
            "videos": [v["video_id"] for v in videos],
            "comments": records,
        }

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(payload, f)
        size = cache_path.stat().st_size

        api_calls = sum(v["api_calls"] for v in videos)
        warnings = []
        if refused:
            warnings.append({
                "level": "warning",
                "primitive": "youtube_provider",
                "message": (f"{len(refused)} of {len(video_ids)} videos returned "
                            f"nothing: " + "; ".join(
                                f"{r['video_id']} ({r['reason']})" for r in refused)),
            })
        if partial:
            warnings.append({
                "level": "warning",
                "primitive": "youtube_provider",
                "message": (f"{len(partial)} of {len(video_ids)} videos are "
                            f"INCOMPLETE: " + "; ".join(
                                f"{p['video_id']} ({p['comment_count']} comments"
                                + (f", stopped: {p['reason']}" if p['reason'] else "")
                                + (f", {p['reply_failures']} reply chain(s) failed"
                                   if p['reply_failures'] else "")
                                + ")" for p in partial)),
            })

        return AcquisitionResult(
            dataset_name=dataset_name,
            success=True,
            path=str(cache_path),
            size_bytes=size,
            message=(f"Fetched {len(records)} comments across "
                     f"{len(videos)} video(s) in {api_calls} API call(s) "
                     f"~ {size / 1024 / 1024:.1f} MB"),
            warnings=warnings,
            # the request, never the credential
            provenance={
                "api": "youtube/v3/commentThreads",
                "fetched_at": payload["fetched_at"],
                "case_id": source_config.get("case_id"),
                "videos": videos,
                "refused": refused,
                "partial": partial,
                "comment_count": len(records),
                "top_level_count": sum(1 for r in records if r["parent_id"] is None),
                "reply_count": sum(1 for r in records if r["parent_id"] is not None),
                "api_calls": api_calls,
                "quota_units_estimate": api_calls,
                "page_size": PAGE_SIZE,
                "max_threads_per_video": max_threads,
                "duration_seconds": round(time.time() - started, 1),
            },
        )

    # ──────────────────────────────────────────────────────────────────────
    # discover
    # ──────────────────────────────────────────────────────────────────────

    def discover(self, bbox, semantic_types=None, **kwargs):
        """Not offered.

        Discovery here answers 'what is available for this bounding box',
        and a comment corpus has no bounding box. Which videos constitute a
        case is a research judgment recorded in the case registry, not
        something a provider should guess from a search ranking.
        """
        return []