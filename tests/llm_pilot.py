"""
tests/llm_pilot.py

PILOT LLM annotation for megan_2022. Three subcommands:

  prepare   corpus.csv -> masked, shuffled coding sheet + keymap + blank human sheet
  annotate  coding sheet -> LLM labels (stage 1 for every row, stage 2 for routed rows)
  compare   human sheet vs LLM labels -> per-column agreement table

Run from the repo root. Needs:  pip install requests pyyaml
OpenRouter key:                 export OPENROUTER_API_KEY="..."

FREE-TIER LIMITS (OpenRouter docs, Oct 2026): 20 requests/minute; 50 :free
requests/day on accounts that have bought under $10 of credits, 1000/day after.
So this script BATCHES comments (default 10 per request). Batching is a known
confound (comments can influence each other); batch id and position are
recorded on every label so the effect can be tested later.
"""

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

API_URL = "https://openrouter.ai/api/v1/chat/completions"

STAGE1 = ["not_discourse", "not_codeable", "case_reference", "counter_speech",
          "empathy_accused", "empathy_victim",
          "advocate", "attack", "deny", "stereotype", "uncertain"]
FACETS = ["advocate", "attack", "deny", "stereotype"]

# ── masking ────────────────────────────────────────────────────────────────
# Longest aliases first so "Tory Lanez" is replaced before "Tory".
# "Megan's Law" is the statute, not the person: protected before masking.
VICTIM_ALIASES = ["Megan Thee Stallion", "Megan The Stallion", "Megan Pete",
                  "Thee Stallion", "Hot Girl Meg", "Tina Snow", "Megan", "Meg"]
ACCUSED_ALIASES = ["Tory Lanez", "Torey Lanez", "Daystar Peterson", "Daystar",
                   "Lanez", "Tory", "Torey"]


def mask(text: str) -> str:
    t = text or ""
    t = re.sub(r"megan'?s law", "<<STATUTE>>", t, flags=re.I)
    t = re.sub(r"@[\w.\-]+", "[USER]", t)
    for alias in sorted(ACCUSED_ALIASES, key=len, reverse=True):
        t = re.sub(rf"\b{re.escape(alias)}\b", "[ACCUSED]", t, flags=re.I)
    for alias in sorted(VICTIM_ALIASES, key=len, reverse=True):
        t = re.sub(rf"\b{re.escape(alias)}\b", "[VICTIM]", t, flags=re.I)
    return t.replace("<<STATUTE>>", "Megan's Law")


# ── prepare ────────────────────────────────────────────────────────────────
def cmd_prepare(a):
    with open(a.corpus, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("text") or "").strip()]
    rng = random.Random(a.seed)
    rng.shuffle(rows)                          # shuffled, so a subset is not "the newest"
    if a.n:
        rows = rows[: a.n]

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    codebook = yaml.safe_load(open(a.codebook))
    s2_items = [i["id"] for f in codebook["stage2"].values() for i in f]

    sheet, keymap, human = [], [], []
    for n, r in enumerate(rows, 1):
        row = f"r{n:04d}"
        text = mask(r["text"])
        sheet.append({"comment_row": row, "text": text})
        keymap.append({"comment_row": row, "comment_id": r["comment_id"]})
        human.append({"comment_row": row, "text": text,
                      **{c: "" for c in STAGE1 + s2_items}})

    def write(name, recs):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(recs[0].keys()))
            w.writeheader()
            w.writerows(recs)

    write("coding_sheet_masked.csv", sheet)
    write("keymap.csv", keymap)                # hold aside; never open while coding
    write("human_labels.csv", human)           # fill in: 1 where yes, leave blank for 0
    print(f"prepared {len(sheet)} rows -> {out}/")
    print("  coding_sheet_masked.csv  (what the LLM sees)")
    print("  human_labels.csv         (what YOU fill in: 1 = yes, blank = no)")
    print("  keymap.csv               (hold aside)")


# ── annotate ───────────────────────────────────────────────────────────────
INSTRUCTIONS = """You are an annotator applying the codebook below to YouTube comments.
Read the primer, the case record card, the power map, the global rules and the
controlling_images section before coding. Apply them exactly.

You will receive a JSON array of comments, each with "comment_row" and "text".
Return ONLY a JSON array, with one object per comment, in the same order, with
exactly the fields listed under output_schema.{stage}. Every flag is 0 or 1.
No prose, no markdown fences, nothing before or after the array.

CODEBOOK:
"""


def call_model(model, system, user, key, retries=3):
    import requests
    for attempt in range(retries + 1):
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"model": model, "temperature": 0,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user}]},
            timeout=180,
        )
        if resp.status_code == 429:
            body = resp.text.lower()
            if "per day" in body or "daily" in body or "free-models-per-day" in body:
                return None, "daily_limit"
            wait = 65
            print(f"    429 rate limited; waiting {wait}s (attempt {attempt + 1})")
            time.sleep(wait)
            continue
        if resp.status_code >= 400:
            return None, f"http_{resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"], None
        except (KeyError, IndexError, TypeError):
            return None, f"bad_response: {str(data)[:200]}"
    return None, "rate_limited_out"


def parse_array(text):
    if not text:
        return None
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = t.find("["), t.rfind("]")
    if start == -1 or end == -1:
        return None
    try:
        out = json.loads(t[start:end + 1])
        return out if isinstance(out, list) else None
    except json.JSONDecodeError:
        return None


def validate(obj, fields):
    rec = {}
    for f in fields:
        v = obj.get(f)
        if v in (0, 1, "0", "1"):
            rec[f] = int(v)
        else:
            return None                         # any missing or non-binary flag fails the row
    return rec


def run_stage(stage, rows, fields, model, system, key, batch_size, raw_f, state):
    labels = {}
    for b in range(0, len(rows), batch_size):
        if state["requests"] >= state["max_requests"]:
            print("  request budget reached; stopping (progress saved)")
            state["stopped"] = "budget"
            break
        batch = rows[b:b + batch_size]
        batch_id = f"{stage}-{b // batch_size:04d}"
        user = json.dumps([{"comment_row": r["comment_row"], "text": r["text"]} for r in batch],
                          ensure_ascii=False)
        for attempt in (1, 2):                  # one retry on a parse failure
            content, err = call_model(model, system, user, key)
            state["requests"] += 1
            raw_f.write(json.dumps({"stage": stage, "batch_id": batch_id, "attempt": attempt,
                                    "rows": [r["comment_row"] for r in batch],
                                    "error": err, "content": content}) + "\n")
            raw_f.flush()
            if err == "daily_limit":
                print("  DAILY free-model limit reached; stopping (progress saved)")
                state["stopped"] = "daily_limit"
                return labels
            if err:
                print(f"    {batch_id} attempt {attempt}: {err[:300]}")
            parsed = parse_array(content) if not err else None
            if parsed is not None:
                break
            if err and err.startswith(("http_4", "bad_response")):
                break                           # a retry cannot fix a bad model id or key
            if not err:
                print(f"    {batch_id} attempt {attempt}: reply was not a JSON array: "
                      f"{(content or '')[:200]!r}")
            time.sleep(state["pause"])
        by_row = {str(o.get("comment_row")): o for o in (parsed or []) if isinstance(o, dict)}
        for pos, r in enumerate(batch):
            rec = validate(by_row.get(r["comment_row"], {}), fields)
            status = "ok" if rec else ("refused_or_error" if err else "parse_failure")
            labels[r["comment_row"]] = {**(rec or {}), "status": status,
                                        "batch_id": batch_id, "batch_pos": pos}
        print(f"  {batch_id}: {sum(1 for r in batch if labels[r['comment_row']]['status'] == 'ok')}"
              f"/{len(batch)} ok   (requests used: {state['requests']})")
        time.sleep(state["pause"])
    return labels


def cmd_annotate(a):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set in this shell.")
    with open(a.sheet, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if a.limit:
        rows = rows[: a.limit]
    cb_text = open(a.codebook, encoding="utf-8").read()
    codebook = yaml.safe_load(cb_text)
    s2_fields = [k for k in codebook["output_schema"]["stage2"]["fields"]
                 if k not in ("comment_row", "rationale")]
    s1_fields = [k for k in codebook["output_schema"]["stage1"]["fields"]
                 if k not in ("comment_row", "language")]

    sys1 = INSTRUCTIONS.format(stage="stage1") + cb_text
    sys2 = INSTRUCTIONS.format(stage="stage2") + cb_text
    prompt_hash = hashlib.sha256((sys1 + sys2).encode()).hexdigest()[:12]

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tag = a.tag or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    state = {"requests": 0, "max_requests": a.max_requests, "pause": 3.2, "stopped": None}

    with open(out / f"raw_{tag}.jsonl", "w", encoding="utf-8") as raw_f:
        print(f"stage 1: {len(rows)} comments, batches of {a.batch_size}")
        s1 = run_stage("s1", rows, s1_fields, a.model, sys1, key, a.batch_size, raw_f, state)

        rng = random.Random(a.seed)
        routed = []
        for r in rows:
            lab = s1.get(r["comment_row"], {})
            if lab.get("status") != "ok":
                continue
            if any(lab.get(f) == 1 for f in FACETS):
                routed.append((r, "facet_yes"))
            elif lab.get("case_reference") == 1 and rng.random() < a.s2_slice:
                routed.append((r, "miss_check"))  # measures what the filter misses
        s2 = {}
        if routed and not state["stopped"]:
            print(f"stage 2: {len(routed)} routed comments")
            s2 = run_stage("s2", [r for r, _ in routed], s2_fields, a.model, sys2, key,
                           a.batch_size, raw_f, state)
        route_reason = {r["comment_row"]: why for r, why in routed}

    cols = (["comment_row", "s1_status"] + s1_fields +
            ["s2_route", "s2_status"] + s2_fields + ["s1_batch", "s1_pos", "s2_batch", "s2_pos"])
    with open(out / f"llm_labels_{tag}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            k = r["comment_row"]
            l1, l2 = s1.get(k, {"status": "not_run"}), s2.get(k, {})
            rec = {"comment_row": k, "s1_status": l1["status"],
                   "s2_route": route_reason.get(k, ""),
                   "s2_status": l2.get("status", "not_routed" if k not in route_reason else "not_run"),
                   "s1_batch": l1.get("batch_id", ""), "s1_pos": l1.get("batch_pos", ""),
                   "s2_batch": l2.get("batch_id", ""), "s2_pos": l2.get("batch_pos", "")}
            rec.update({c: l1.get(c, "") for c in s1_fields})
            # unrouted rows with a clean stage 1 are 0 on every item, by design
            unrouted_zero = l1["status"] == "ok" and k not in route_reason
            rec.update({c: (l2.get(c, "") if not unrouted_zero else 0) for c in s2_fields})
            w.writerow(rec)

    meta = {"tag": tag, "model": a.model, "prompt_hash": prompt_hash,
            "codebook": a.codebook, "batch_size": a.batch_size, "temperature": 0,
            "rows": len(rows), "routed": len(routed), "requests_used": state["requests"],
            "stopped": state["stopped"], "run_at": datetime.now(timezone.utc).isoformat()}
    json.dump(meta, open(out / f"run_{tag}.json", "w"), indent=2)
    print(f"\nlabels:  {out}/llm_labels_{tag}.csv")
    print(f"raw:     {out}/raw_{tag}.jsonl")
    print(f"run:     {json.dumps(meta)}")


# ── compare ────────────────────────────────────────────────────────────────
def kappas(h, m):
    n = len(h)
    if n == 0:
        return None
    po = sum(1 for x, y in zip(h, m) if x == y) / n
    ph, pm = sum(h) / n, sum(m) / n
    pe = ph * pm + (1 - ph) * (1 - pm)
    cohen = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    return po, 2 * po - 1, cohen                # Brennan-Prediger for binary = 2*Po - 1


def cmd_compare(a):
    def load(p):
        with open(p, newline="", encoding="utf-8") as f:
            return {r["comment_row"]: r for r in csv.DictReader(f)}
    human, llm = load(a.human), load(a.llm)
    to01 = lambda v: 1 if str(v).strip() in ("1", "1.0") else 0
    s2_cols = [c for c in next(iter(llm.values())).keys()
               if c not in ("comment_row", "s1_status", "s2_route", "s2_status",
                            "s1_batch", "s1_pos", "s2_batch", "s2_pos") and c not in STAGE1]

    usable = [k for k in human if k in llm and llm[k]["s1_status"] == "ok"]
    # rows you skipped entirely (every cell blank) are treated as not coded
    coded = [k for k in usable
             if any(str(human[k].get(c, "")).strip() for c in STAGE1 + s2_cols)
             or a.blank_is_zero]
    print(f"rows compared: {len(coded)} (human rows: {len(human)}; LLM ok: "
          f"{sum(1 for r in llm.values() if r['s1_status'] == 'ok')})\n")

    out_rows = []
    print(f"{'column':<26}{'human+':>7}{'llm+':>6}{'agree':>8}{'BP-k':>7}{'Cohen':>7}")
    for c in [x for x in STAGE1 if x != "not_codeable"] + s2_cols:
        h = [to01(human[k].get(c, "")) for k in coded]
        m = [to01(llm[k].get(c, "")) for k in coded]
        res = kappas(h, m)
        if not res:
            continue
        po, bp, ck = res
        out_rows.append({"column": c, "human_pos": sum(h), "llm_pos": sum(m), "n": len(h),
                         "agreement": round(po, 3), "bp_kappa": round(bp, 3),
                         "cohen_kappa": round(ck, 3) if ck == ck else ""})
        print(f"{c:<26}{sum(h):>7}{sum(m):>6}{po:>8.2f}{bp:>7.2f}"
              f"{(f'{ck:.2f}' if ck == ck else '  n/a'):>7}")
    path = Path(a.llm).with_name("comparison.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nwritten: {path}")
    print("Read BP-k with the positives counts: with few positives, agreement is "
          "dominated by shared zeros and the interval is very wide.")


# ── cli ────────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("prepare")
    pp.add_argument("--corpus", required=True)
    pp.add_argument("--codebook", default="r_rev_codebook_v1.yml")
    pp.add_argument("--out-dir", required=True)
    pp.add_argument("--n", type=int, default=None, help="keep only n shuffled rows")
    pp.add_argument("--seed", type=int, default=7)

    pa = sub.add_parser("annotate")
    pa.add_argument("--sheet", required=True)
    pa.add_argument("--codebook", default="r_rev_codebook_v1.yml")
    pa.add_argument("--model", required=True, help="OpenRouter model id, e.g. something:free")
    pa.add_argument("--out-dir", required=True)
    pa.add_argument("--batch-size", type=int, default=10)
    pa.add_argument("--max-requests", type=int, default=45,
                    help="stop before this many requests (free daily cap is 50)")
    pa.add_argument("--s2-slice", type=float, default=0.10)
    pa.add_argument("--limit", type=int, default=None)
    pa.add_argument("--seed", type=int, default=7)
    pa.add_argument("--tag", default=None)

    pc = sub.add_parser("compare")
    pc.add_argument("--human", required=True)
    pc.add_argument("--llm", required=True)
    pc.add_argument("--blank-is-zero", action="store_true",
                    help="count fully blank human rows as all-0 instead of uncoded")

    a = p.parse_args()
    {"prepare": cmd_prepare, "annotate": cmd_annotate, "compare": cmd_compare}[a.cmd](a)


if __name__ == "__main__":
    main()