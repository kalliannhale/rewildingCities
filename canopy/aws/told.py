"""
canopy/aws/told.py ~ the told copy and the refusal record (Sprint 09, zip 9b1)

two things the explorer reads, written once, outside ArcGIS, the way every
canonical object is (Contract 2):

  the refusal record   what the plot holds that the gate keeps in, and why: one
                       entry per withheld receipt, its kind of data and the
                       gate's refusal records, never a value or a member of it
                       (Contract 1, rules 7 and 8; D-363). it is the gate's own
                       words, so nothing judges it; it is versioned by its
                       content, which holds no time, so the same judgment is the
                       same version.

      harvests/<plot>/_refusals/versions/<sha256>/data.json
      harvests/<plot>/_refusals/current

                       `_refusals` is a name no receipt can take: an artifact
                       name never starts with `_` (s3.validate_artifact).

  the told copy        every place the explorer shows, in plain sentences
                       (canopy/wonder/telling.py), drawn from the profile's
                       current version and the current refusal record. it is a
                       display copy that is a document (D-370), under the
                       profile's version:

      versions/<profile sha256>/display/told_<sha12>.json
      versions/<profile sha256>/display/told_<sha12>.envelope.json

                       named by the hash of everything that can change its
                       bytes (TOLD_INPUTS, and the refusal record's version,
                       D-378, D-381), so a changed seed or a new judgment is a
                       new name and never new bytes under one (D-322). its
                       envelope keeps the profile's lineage, notes and chain,
                       and adds a `told` record (rule 11). the refusal record
                       is named in the entry's params, never as an input, since
                       it is no semantic type and an input's type binds rule 2.

both are dry runs unless written, and both write only with If-None-Match, the
pointer with If-Match, as the bucket's policy requires (D-309). nothing here
removes anything. ~
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from canopy.aws import s3

REFUSALS = "_refusals"
PROFILE = "place_profile_profiles"
PRIMITIVE = "tell_places"
VERSION = "1.0.0"
# every file whose bytes can change the told copy's (D-370 as revised, D-381):
# the telling and the helpers it imports, this module, the notes it carries and
# the register it is held to. the standard reaches the telling only through the
# profile, whose version is already the copy's own.
TOLD_INPUTS = ("canopy/aws/told.py", "canopy/wonder/telling.py", "canopy/wonder/place.py",
               "seeds/notes/notes.yml", "seeds/language/plain_language.yml")
_RECORD_FIELDS = ("rule", "semantic_type", "tier", "ancestor", "reason", "would_admit")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def document_bytes(doc: dict) -> bytes:
    """one form for every document this module writes: keys sorted, no spaces,
    so the same content is always the same bytes and the same version."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


# ── the refusal record ───────────────────────────────────────────────────
def _refused_before_the_gate(root: Path, plot: str, artifact: str) -> bool:
    """True when the canonical write refuses this receipt's data file before
    the gate is asked: a fetched source passed through (D-297, D-337), or a
    file outside the plot's .data. that is the write's refusal, never the
    gate's, so it is not in the record (D-363), whatever the gate would say."""
    path = Path(root) / "plots" / plot / ".envelopes" / f"{artifact}.envelope.json"
    if not path.is_file():
        return False
    try:
        s3.source_file(Path(root), plot, json.loads(path.read_text()))
    except s3.CanonicalRefusal:
        return True
    return False


def refusal_record(plot: str, *, root: Path, judged: dict | None = None,
                   before_gate=None) -> dict:
    """the gate's refusals for every receipt in the plot, at the canonical
    write's own question (target canonical, sharing public). a receipt the
    write refuses before it asks the gate (a fetched source, D-337) is named
    apart and not told; one it refuses after, for its format, the gate
    allowed. so the record holds the gate's refusals only (D-363)."""
    if judged is None:
        from canopy.expose.check import judge_receipts
        judged = judge_receipts(plot, root=root, sharing_level=s3.SHARING_LEVEL,
                                target=s3.TARGET)
    before_gate = before_gate or (lambda a: _refused_before_the_gate(root, plot, a))
    from canopy.expose.gate import GATE_VERSION
    withheld, by_the_write = [], []
    for artifact, j in sorted(judged.items()):
        res = j.get("result") or {}
        if res.get("decision") == "allow":
            continue
        if before_gate(artifact):
            by_the_write.append(artifact)
            continue
        withheld.append({
            "receipt": artifact, "semantic_type": j.get("semantic_type"),
            "refusals": [{k: r.get(k) for k in _RECORD_FIELDS}
                         for r in res.get("refusals") or []]})
    return {"plot": plot, "target": s3.TARGET, "sharing_level": s3.SHARING_LEVEL,
            "gate_version": GATE_VERSION, "receipts_judged": len(judged),
            "refused_before_the_gate": by_the_write, "withheld": withheld}


def refusals_keys(plot: str, sha256: str) -> dict:
    prefix = s3.version_prefix(plot, REFUSALS, sha256)
    return {"data": f"{prefix}/data.json", "current": s3.pointer_key(plot, REFUSALS)}


def read_refusals(client, bucket: str, plot: str) -> tuple[str, dict] | None:
    """the current refusal record as the bucket holds it, its bytes checked
    against their name; None when none has been written."""
    pointer, _ = s3.read_pointer(client, bucket, s3.pointer_key(plot, REFUSALS))
    if pointer is None:
        return None
    sha = pointer["sha256"]
    data = s3._get_bytes(client, bucket, refusals_keys(plot, sha)["data"])
    if data is None or _sha(data) != sha:
        raise s3.CanonicalRefusal(f"the refusal record {sha[:12]} is missing or does not "
                                  f"hash to its name", "read the bucket before anything else")
    return sha, json.loads(data)


def write_refusals(record: dict, *, client, bucket: str, by: str, reason: str,
                   now: datetime | None = None) -> dict:
    """write the record if it is new, then move `current` to it if it is not
    already there. returns what happened."""
    if not (by or "").strip() or not (reason or "").strip():
        raise s3.CanonicalRefusal("a write names who moved the pointer and why",
                                  "give --by and --reason")
    body = document_bytes(record)
    sha = _sha(body)
    keys = refusals_keys(record["plot"], sha)
    written = [keys["data"]] if s3._put_once(client, bucket, keys["data"], body,
                                             s3.JSON_TYPE) else []
    pointer, etag = s3.read_pointer(client, bucket, keys["current"])
    previous = (pointer or {}).get("sha256")
    said = {"sha256": sha, "previous": previous, "written": written, "keys": keys}
    if previous == sha:
        return dict(said, pointer="unchanged")
    moved = {"sha256": sha, "allow": None, "previous": previous, "previous_allow": None,
             "data": "data.json", "moved_at": _now(now), "moved_by": by.strip(),
             "reason": reason.strip()}
    condition = {"IfMatch": etag} if pointer is not None else {"IfNoneMatch": "*"}
    try:
        client.put_object(Bucket=bucket, Key=keys["current"],
                          Body=(json.dumps(moved, indent=2) + "\n").encode(),
                          ContentType=s3.JSON_TYPE, CacheControl=s3.POINTER_CACHE, **condition)
    except Exception as e:
        if s3._precondition(e):
            raise s3.CanonicalRefusal(
                "the pointer moved while this write ran, so it was left as the other "
                "writer set it; the record is written",
                "read current, then write again if this record should be current") from None
        raise
    written.append(keys["current"])
    return dict(said, written=written, pointer="created" if pointer is None else "moved")


# ── the told copy ────────────────────────────────────────────────────────
def told_inputs(root: Path) -> dict:
    """{path: sha256} for every file in TOLD_INPUTS, read from the garden."""
    out = {}
    for rel in TOLD_INPUTS:
        path = Path(root) / rel
        if not path.is_file():
            raise s3.CanonicalRefusal(f"{rel} is missing, so the told copy cannot be named",
                                      "run this from the rewildingCities repo root")
        out[rel] = _sha(path.read_bytes())
    return out


def told_name(inputs: dict, refusals_sha256: str) -> str:
    """told_<sha12>: the hash of every input's hash and the refusal record's
    version, so any change to either is another copy (D-322, D-378)."""
    key = document_bytes({"inputs": inputs, "refusals": refusals_sha256})
    return f"told_{_sha(key)[:12]}"


def told_keys(plot: str, profile_sha256: str, name: str, harvest: str = PROFILE) -> dict:
    prefix = f"{s3.version_prefix(plot, harvest, profile_sha256)}/display/{name}"
    return {"json": f"{prefix}.json", "envelope": f"{prefix}.envelope.json"}


@dataclass
class PreparedTold:
    plot: str
    harvest: str
    sha256: str
    allow_sha256: str
    refusals_sha256: str
    name: str
    body: bytes
    envelope: dict
    rows: int
    skipped: dict
    keys: dict = field(default_factory=dict)
    local: bool = False
    copy_sha256: str = ""


def _profile_version(plot, harvest, *, local, client, bucket, root, judge) -> dict:
    if local:
        p = s3.prepare(plot, harvest, root=root, judge=judge)
        if p.data_name != "data.json":
            raise s3.CanonicalRefusal(f"'{harvest}' is not a document", "tell a place profile")
        return {"sha256": p.sha256, "allow": p.allow_sha256, "data": p.data_bytes,
                "receipt": json.loads(p.receipt_bytes),
                "prefix": s3.version_prefix(plot, harvest, p.sha256)}
    pointer, _ = s3.read_pointer(client, bucket, s3.pointer_key(plot, harvest))
    if pointer is None:
        raise s3.CanonicalRefusal(f"'{harvest}' has no canonical version yet",
                                  f"write it first: canonical {plot} {harvest} --write")
    if pointer.get("data") != "data.json":
        raise s3.CanonicalRefusal(f"'{harvest}' is a {pointer.get('data')} harvest; the "
                                  f"told copy tells a place profile, a document",
                                  f"canonical {plot} {PROFILE} --told")
    sha, prefix = pointer["sha256"], s3.version_prefix(plot, harvest, pointer["sha256"])
    data = s3._get_bytes(client, bucket, f"{prefix}/data.json")
    receipt = s3._get_bytes(client, bucket, f"{prefix}/envelope.json")
    if data is None or receipt is None:
        raise s3.CanonicalRefusal(f"version {sha[:12]} is not whole in the bucket",
                                  "write it again; a write cut off partway finishes")
    if _sha(data) != sha:
        raise s3.CanonicalRefusal(f"the bytes at version {sha[:12]} do not hash to its name",
                                  "stop and read the bucket's history before anything else")
    return {"sha256": sha, "allow": pointer.get("allow"), "data": data,
            "receipt": json.loads(receipt), "prefix": prefix}


def told_envelope(receipt: dict, *, key: str, data_url: str, sha256: str, allow_sha256: str,
                  harvest: str, name: str, rows: list, body: bytes, params: dict,
                  duration_seconds: float, now: datetime | None = None) -> dict:
    """the copy's own envelope: the profile's metadata, lineage, notes and chain
    (inherited under the branch `version`), its rows described as told rows,
    and this telling's entry with its `told` record."""
    at = _now(now)
    meta = dict(receipt.get("metadata") or {})
    variables: list = []
    for r in rows:
        for k in r:
            if k not in variables:
                variables.append(k)
    meta.update({"row_count": len(rows), "column_count": len(variables), "variables": variables,
                 "id_field": "key", "derived_from": sha256, "allow": allow_sha256,
                 "display_of": harvest, "display_name": name, "display_kind": "told",
                 "size_bytes": len(body)})
    inherited = []
    for entry in receipt.get("provenance") or []:
        e = dict(entry)
        if e.get("lineage_branch") is None:
            e["lineage_branch"] = "version"
        inherited.append(e)
    own = {
        "primitive": PRIMITIVE, "version": VERSION, "timestamp": at, "params": params,
        "inputs": [{"name": "version", "semantic_type": meta.get("semantic_type"),
                    "path": data_url,
                    "hash": {"value": sha256, "method": "full_file", "algorithm": "sha256"}}],
        "duration_seconds": round(float(duration_seconds), 3), "lineage_branch": None,
        "publication": [{"step": "told", "count": len(rows), "by": PRIMITIVE, "at": at,
                         "detail": (
            f"{len(rows)} places told in plain sentences by canopy/wonder/telling.py, every "
            f"field built from the profile's structured parts, working ids taken out; the "
            f"state's row also tells the refusal record {params['refusals']['version'][:12]}; "
            f"places outside the explorer's levels left out and counted "
            f"({', '.join(f'{k} {v}' for k, v in sorted(params['skipped'].items())) or 'none'})")}],
    }
    return {"data": {"path": key, "format": "json", "secondary": {}}, "metadata": meta,
            "provenance": inherited + [own], "warnings": list(receipt.get("warnings") or [])}


def prepare_told(plot: str, *, client, bucket: str, domain: str, root: Path,
                 harvest: str = PROFILE, judge=s3.default_judge, validate=None,
                 now: datetime | None = None, local: bool = False,
                 refusals: tuple[str, dict] | None = None) -> PreparedTold:
    """read the profile's current version (or, local, make it from the plot's
    files) and the current refusal record (or, local, judge it now), tell
    every place, build the envelope and ask the gate. sends nothing."""
    import time
    from canopy.wonder.telling import tell_all
    s3.validate_plot(plot)
    s3.validate_artifact(harvest)
    root = Path(root)
    started = time.monotonic()
    v = _profile_version(plot, harvest, local=local, client=client, bucket=bucket, root=root,
                         judge=judge)
    if refusals is None:
        if local:
            record = refusal_record(plot, root=root)
            refusals = (_sha(document_bytes(record)), record)
        else:
            refusals = read_refusals(client, bucket, plot)
    if refusals is None:
        raise s3.CanonicalRefusal("no refusal record is written, so the state's row cannot "
                                  "say what the tool keeps in",
                                  f"write it first: canonical {plot} --refusals --write")
    rsha, record = refusals
    try:
        rows, ctx = tell_all(json.loads(v["data"]), root, refusals=record)
    except Exception as e:                # a telling's error is a refusal, never a crash
        said = (str(e).splitlines() or [""])[0][:300]
        raise s3.CanonicalRefusal(f"telling the profile failed: {type(e).__name__}: {said}",
                                  "read the error; tests/test_telling.py holds the telling")
    if not any(r.get("withheld") for r in rows):
        raise s3.CanonicalRefusal("no row of the profile is the state's, so the refusal "
                                  "record has no home in the told copy (D-376)",
                                  "rebuild the profile, which profiles the state")
    inputs = told_inputs(root)
    name = told_name(inputs, rsha)
    body = document_bytes({"profile_version": v["sha256"], "refusals_version": rsha,
                           "told_inputs": inputs, "skipped": dict(ctx.skipped), "rows": rows})
    keys = told_keys(plot, v["sha256"], name, harvest)
    base = f"https://{domain}" if domain else "local:"
    params = {"name": name, "inputs": inputs, "skipped": dict(ctx.skipped),
              "refusals": {"version": rsha,
                           "url": f"{base}/{refusals_keys(plot, rsha)['data']}"}}
    env = told_envelope(v["receipt"], key=keys["json"], data_url=f"{base}/{v['prefix']}/data.json",
                        sha256=v["sha256"], allow_sha256=v["allow"], harvest=harvest, name=name,
                        rows=rows, body=body, params=params,
                        duration_seconds=time.monotonic() - started, now=now)
    errors = s3._validator(validate, root)(env)
    if errors:
        raise s3.CanonicalRefusal("the told copy's envelope does not match the envelope schema: "
                                  + "; ".join(str(x) for x in errors[:3]),
                                  "fix the envelope's shape in canopy/aws/told.py")
    s3._judge(judge, env, plot, root / "plots" / plot)
    return PreparedTold(plot=plot, harvest=harvest, sha256=v["sha256"], allow_sha256=v["allow"],
                        refusals_sha256=rsha, name=name, body=body, envelope=env,
                        rows=len(rows), skipped=dict(ctx.skipped), keys=keys, local=local,
                        copy_sha256=_sha(body))


def write_told(prepared: PreparedTold, *, client, bucket: str) -> dict:
    """the envelope, then the copy last, each with If-None-Match. a copy there
    with these bytes writes nothing; one there with other bytes is refused."""
    from canopy.aws.display import envelope_bytes
    if prepared.local:
        raise s3.CanonicalRefusal("a local told copy is a dry run only; the copy that is "
                                  "written is told from the bucket",
                                  "write the profile and the refusal record, then tell it "
                                  "without --local")
    keys = prepared.keys
    there = s3._get_bytes(client, bucket, keys["json"])
    if there is not None:
        if _sha(there) == prepared.copy_sha256:
            return {"copy": "exists", "written": [], "keys": keys}
        raise s3.CanonicalRefusal(
            f"a told copy named '{prepared.name}' already stands under version "
            f"{prepared.sha256[:12]} with other bytes, and a version's files never change",
            "find what changed: every input that can change the copy is in its name")
    written = []
    for key, body in ((keys["envelope"], envelope_bytes(prepared.envelope)),
                      (keys["json"], prepared.body)):
        if s3._put_once(client, bucket, key, body, s3.JSON_TYPE):
            written.append(key)
    return {"copy": "new", "written": written, "keys": keys}
