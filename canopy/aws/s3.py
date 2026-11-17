"""
canopy/aws/s3.py ~ the canonical write (Contract 2)

the truth that leaves is written here, once. a receipt from a plot's
.envelopes is asked the gate's question at the target `canonical`, at
`public`, because CloudFront makes everything under harvests/ readable by
anyone (D-302). only an allowed receipt is written, and only in this shape:

  harvests/<plot>/<harvest>/versions/<sha256>/envelope.json   the receipt, byte for byte
  harvests/<plot>/<harvest>/versions/<sha256>/data.parquet    (or data.json, a document)
  harvests/<plot>/<harvest>/versions/<sha256>/allow/<allow-sha256>.json
                                                              one per distinct allow record
  harvests/<plot>/<harvest>/current                           the one thing that moves

the sha256 is of the data file's own bytes, so two writes of the same bytes
are one version. the data file is put last: a version is whole when its data
file exists, and a write cut off partway finishes on the next try.

an allow record can change while the data does not: a note's text settled
with the nations, a license term read again (D-320). so allow records are
versioned inside their version, each named by the sha256 of its own content
less its timestamps. the same data and the same allow record write nothing;
the same data and a changed allow record write the allow record alone, and
`current` moves to it, naming both.

formats (D-314):
  parquet  written as it is
  json     written as it is: a document, like the place profile
  geojson  converted to GeoParquet, twice, and refused if the two disagree;
           the change is a format_changed record in the allow record (rule 11)
  anything else is refused by name; nothing is converted quietly

the bucket's own policy refuses a version put without If-None-Match and a
pointer put without If-None-Match or If-Match (D-309), and the writer role
may never remove anything (D-308). this module asks for no removal of any
kind, and a test reads its source to hold it to that.

a lineage that holds a `custom` tier is refused here even when the gate
allows it: a version stays readable forever, so a consent withdrawn later
could not be honoured until Contract 2 says how a version is withdrawn (O-6).

the client is passed in (D-305): boto3's in a real write, a fake in tests. ~
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

TARGET = "canonical"
SHARING_LEVEL = "public"
WRITTEN_BY = "the canonical write (canopy/aws/s3.py)"

BUCKET_ENV = "REWILDING_CANONICAL_BUCKET"
DOMAIN_ENV = "REWILDING_CANONICAL_DOMAIN"
PROFILE_ENV = "REWILDING_CANONICAL_PROFILE"
DEFAULT_PROFILE = "rewilding-writer"

PARQUET_TYPE = "application/vnd.apache.parquet"
JSON_TYPE = "application/json"
VERSION_CACHE = "public, max-age=31536000, immutable"
POINTER_CACHE = "no-cache"

# a receipt's format: (canonical format, data file name, content type, how)
_FORMATS = {
    "parquet": ("parquet", "data.parquet", PARQUET_TYPE, "as_is"),
    "json": ("json", "data.json", JSON_TYPE, "as_is"),
    "geojson": ("geoparquet", "data.parquet", PARQUET_TYPE, "convert"),
}
_REFUSED_FORMATS = {
    "csv": "a CSV here is a listing or a record table; Contract 2 writes "
           "Parquet tables, GeoParquet features and JSON documents",
    "gpkg": "GeoPackage is made only on request, as a display copy (D-303)",
    "tiff": "rasters have no canonical form yet",
    "arrow": "Arrow files have no canonical form yet",
}

_SEGMENT = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_ARTIFACT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class CanonicalRefusal(Exception):
    """the write declines, saying why and what would admit it. `refusals`
    carries the gate's own refusal records when the gate is what refused."""

    def __init__(self, reason: str, would_admit: str, refusals: list[dict] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.would_admit = would_admit
        self.refusals = refusals or []


@dataclass
class Prepared:
    """everything one write needs, made before any client is touched."""
    plot: str
    harvest: str
    sha256: str
    canonical_format: str
    data_name: str
    content_type: str
    data_bytes: bytes
    receipt_bytes: bytes
    allow_doc: dict
    allow_sha256: str = ""
    features: int | None = None
    keys: dict = field(default_factory=dict)


# ── names ────────────────────────────────────────────────────────────────
def validate_plot(plot: str) -> str:
    """a plot name is one or more lower-case segments joined by `/`, as in
    maine or michigan/delton; anything else, `..` included, is refused."""
    parts = (plot or "").split("/")
    if not plot or not all(_SEGMENT.match(p) for p in parts):
        raise CanonicalRefusal(
            f"'{plot}' is not a plot name: lower-case letters, digits, _ and -, "
            f"in segments joined by /",
            "name the plot as its folder under plots/ is named")
    return plot


def validate_artifact(artifact: str) -> str:
    if not artifact or not _ARTIFACT.match(artifact) or ".." in artifact:
        raise CanonicalRefusal(
            f"'{artifact}' is not an artifact name: a receipt's name, less "
            f".envelope.json, with no path in it",
            "name a receipt in the plot's .envelopes folder")
    return artifact


def version_prefix(plot: str, harvest: str, sha256: str) -> str:
    return f"harvests/{plot}/{harvest}/versions/{sha256}"


def pointer_key(plot: str, harvest: str) -> str:
    return f"harvests/{plot}/{harvest}/current"


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def allow_identity(doc: dict) -> str:
    """the sha256 an allow record is named by: its content less every time
    it was made at (the gate's checked_at, this write's own steps' at, when
    it was prepared) and less which receipt was read, so a rerun that judges
    the same data the same way names the same record. anything else that
    changes, a note's text, a license, a library's version in a conversion's
    detail, makes a new record, loudly."""
    gate = {k: v for k, v in (doc.get("gate") or {}).items() if k != "checked_at"}
    gate["publication_steps"] = [
        {k: v for k, v in step.items() if not (k == "at" and step.get("by") == WRITTEN_BY)}
        for step in gate.get("publication_steps") or []]
    core = {"sha256": doc.get("sha256"), "format": doc.get("format"),
            "data": doc.get("data"), "gate": gate}
    return sha256_of(json.dumps(core, sort_keys=True, separators=(",", ":"),
                                allow_nan=False).encode())


# ── reading the receipt ──────────────────────────────────────────────────
def list_receipts(root: Path, plot: str) -> list[str]:
    folder = Path(root) / "plots" / plot / ".envelopes"
    return sorted(p.name[:-len(".envelope.json")] for p in folder.glob("*.envelope.json")) \
        if folder.is_dir() else []


def read_receipt(root: Path, plot: str, artifact: str) -> tuple[bytes, dict]:
    """the receipt's bytes and its parsed form. only a receipt in the plot's
    .envelopes is ever a write's input, never a manifest dataset."""
    path = Path(root) / "plots" / plot / ".envelopes" / f"{artifact}.envelope.json"
    if not path.is_file():
        raise CanonicalRefusal(
            f"plots/{plot}/.envelopes holds no receipt named '{artifact}'",
            f"run `python -m canopy.cli canonical {plot} --all` to list the receipts")
    raw = path.read_bytes()
    try:
        return raw, json.loads(raw)
    except ValueError:
        raise CanonicalRefusal(f"the receipt '{artifact}' could not be read as JSON",
                               "re-run the step that wrote it") from None


def source_file(root: Path, plot: str, envelope: dict) -> Path:
    """the receipt's data file, resolved against the garden's root (receipts
    write paths like plots/maine/preparations/../.data/x.geojson). it must
    sit inside the plot's own .data, and travel alone."""
    data = envelope.get("data") or {}
    if data.get("secondary"):
        raise CanonicalRefusal(
            f"the receipt names secondary files ({', '.join(sorted(data['secondary']))}), "
            f"which this write would leave behind",
            "write each as its own receipt, or decide in Contract 2 how secondaries travel")
    given = data.get("path")
    if not given:
        raise CanonicalRefusal("the receipt names no data file", "re-run the step that wrote it")
    path = Path(given)
    path = (path if path.is_absolute() else Path(root) / path).resolve()
    home = (Path(root) / "plots" / plot / ".data").resolve()
    if home not in path.parents:
        raise CanonicalRefusal(
            f"the receipt's data file is not in plots/{plot}/.data: {given}",
            "only a plot's own results leave through this write")
    if not path.is_file():
        raise CanonicalRefusal(f"the receipt's data file is missing: {given}",
                               "re-run the step that wrote it")
    return path


# ── the gate ─────────────────────────────────────────────────────────────
def default_judge(envelope: dict, *, plot: str, plot_dir: Path) -> dict:
    from canopy.expose.check import check_envelope
    return check_envelope(envelope, plot=plot, target=TARGET,
                          sharing_level=SHARING_LEVEL, plot_dir=plot_dir)


def _judge(judge, envelope: dict, plot: str, plot_dir: Path) -> dict:
    try:
        decision = judge(envelope, plot=plot, plot_dir=plot_dir)
    except ValueError as e:              # rule 1: a declaration error, said plainly
        raise CanonicalRefusal(f"the gate could not judge it: {e}",
                               "correct the declaration") from None
    if decision.get("decision") != "allow":
        refusals = decision.get("refusals") or []
        raise CanonicalRefusal(
            f"the exposure gate withheld it ({len(refusals)} refusal(s))",
            "what each refusal names", refusals=refusals)
    record = decision.get("record") or {}
    custom = [t for t in record.get("tiers") or [] if t.get("tier") == "custom"]
    if custom:
        raise CanonicalRefusal(
            f"its lineage holds a custom tier ({', '.join(t['semantic_type'] for t in custom)}); "
            f"a version stays readable forever, so a consent withdrawn later could "
            f"not be honoured",
            "Contract 2's O-6: how a version is withdrawn, decided on the terms "
            "of the people the data describes")
    return record


# ── conversion ───────────────────────────────────────────────────────────
def geojson_to_geoparquet(src: Path, dst: Path) -> dict:
    """the one conversion: GeoJSON read by geopandas, written as GeoParquet
    with no index column. returns what the format_changed record says.

    GDAL refuses one GeoJSON object past a size limit, and Maine's whole
    outline (one feature, every island) is past it, so the limit is lifted
    for this process: OGR_GEOJSON_MAX_OBJ_SIZE 0. it bounds the reader's
    memory, never what the file holds, so the bytes written do not depend
    on it."""
    import geopandas
    import pyarrow
    import pyogrio
    pyogrio.set_gdal_config_options({"OGR_GEOJSON_MAX_OBJ_SIZE": "0"})
    frame = geopandas.read_file(src, engine="pyogrio")
    frame.to_parquet(dst, index=False)
    return {"features": int(len(frame)),
            "crs": frame.crs.to_string() if frame.crs is not None else None,
            "libraries": {"geopandas": geopandas.__version__, "pyarrow": pyarrow.__version__}}


def convert_stably(src: Path, converter=geojson_to_geoparquet) -> tuple[bytes, dict]:
    """convert twice and keep the bytes only if both runs made the same ones,
    so a version's sha256 names the content, not the moment it was made."""
    with tempfile.TemporaryDirectory(prefix="canonical-") as tmp:
        first, second = Path(tmp) / "first.parquet", Path(tmp) / "second.parquet"
        try:
            info = converter(src, first)
            converter(src, second)
        except CanonicalRefusal:
            raise
        except Exception as e:           # a reader's error is a refusal, never a crash
            said = (str(e).splitlines() or [""])[0][:300]
            raise CanonicalRefusal(
                f"the conversion failed: {type(e).__name__}: {said}",
                "read the error: the file may need a reader option or a repair step") from None
        a, b = first.read_bytes(), second.read_bytes()
    if sha256_of(a) != sha256_of(b):
        raise CanonicalRefusal(
            "converting this GeoJSON twice made two different files, so its "
            "sha256 would not name its content",
            "find what varies between runs (a timestamp in the file's metadata, "
            "row order) and pin it")
    return a, info


# ── preparing a write ────────────────────────────────────────────────────
def prepare(plot: str, artifact: str, *, root: Path, judge=default_judge,
            converter=geojson_to_geoparquet, now: datetime | None = None) -> Prepared:
    """everything up to the first byte sent: names, receipt, gate, format,
    conversion, hash. touches no client, so a dry run is this alone."""
    validate_plot(plot)
    validate_artifact(artifact)
    root = Path(root)
    receipt_bytes, envelope = read_receipt(root, plot, artifact)
    src = source_file(root, plot, envelope)
    record = _judge(judge, envelope, plot, root / "plots" / plot)

    fmt = (envelope.get("data") or {}).get("format")
    if fmt in _REFUSED_FORMATS:
        raise CanonicalRefusal(f"its data is {fmt}: {_REFUSED_FORMATS[fmt]}",
                               "a step that writes it as Parquet, GeoParquet or JSON")
    if fmt not in _FORMATS:
        raise CanonicalRefusal(f"its data format '{fmt}' is not one this write knows",
                               "declare the format in Contract 2 first")
    canonical_format, data_name, content_type, how = _FORMATS[fmt]

    source_bytes = src.read_bytes()
    source_sha = sha256_of(source_bytes)
    steps = [dict(s) for s in record.get("publication_steps") or []]
    features = None
    if how == "convert":
        data_bytes, info = convert_stably(src, converter)
        features = info.get("features")
        libs = ", ".join(f"{k} {v}" for k, v in sorted((info.get("libraries") or {}).items()))
        steps.append({
            "step": "format_changed",
            "detail": (f"GeoJSON to GeoParquet ({libs}); property types as the reader "
                       f"assigned them; crs {info.get('crs')}; source sha256 {source_sha}"),
            "count": features, "by": WRITTEN_BY, "at": _now(now), "lineage_branch": None})
    else:
        data_bytes = source_bytes
    sha = sha256_of(data_bytes)

    gate = dict(record, publication_steps=steps)
    rel_source = src.relative_to(root.resolve()).as_posix() \
        if root.resolve() in src.parents else str(src)
    allow_doc = {
        "harvest": artifact, "plot": plot, "sha256": sha,
        "format": canonical_format, "data": data_name,
        "receipt": {"artifact": artifact, "sha256": sha256_of(receipt_bytes)},
        "source": {"path": rel_source, "format": fmt, "sha256": source_sha},
        "gate": gate,
        "prepared_at": _now(now),
    }
    allow_sha = allow_identity(allow_doc)
    allow_doc["allow"] = allow_sha
    prefix = version_prefix(plot, artifact, sha)
    keys = {"envelope": f"{prefix}/envelope.json",
            "allow": f"{prefix}/allow/{allow_sha}.json",
            "data": f"{prefix}/{data_name}", "current": pointer_key(plot, artifact)}
    return Prepared(plot=plot, harvest=artifact, sha256=sha,
                    canonical_format=canonical_format, data_name=data_name,
                    content_type=content_type, data_bytes=data_bytes,
                    receipt_bytes=receipt_bytes, allow_doc=allow_doc,
                    allow_sha256=allow_sha, features=features, keys=keys)


# ── writing ──────────────────────────────────────────────────────────────
def _code(exc: Exception) -> str:
    return str(((getattr(exc, "response", None) or {}).get("Error") or {}).get("Code") or "")


def _missing(exc: Exception) -> bool:
    return _code(exc) in ("404", "NoSuchKey", "NotFound")


def _precondition(exc: Exception) -> bool:
    return _code(exc) in ("412", "PreconditionFailed")


def _exists(client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except Exception as e:
        if _missing(e):
            return False
        raise


def _put_once(client, bucket: str, key: str, body: bytes, content_type: str) -> bool:
    """put a version's file with If-None-Match: True when written, False when
    it was already there (a write cut off partway, finishing now)."""
    try:
        client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type,
                          CacheControl=VERSION_CACHE, IfNoneMatch="*")
        return True
    except Exception as e:
        if _precondition(e):
            return False
        raise


def read_pointer(client, bucket: str, key: str) -> tuple[dict | None, str | None]:
    try:
        got = client.get_object(Bucket=bucket, Key=key)
    except Exception as e:
        if _missing(e):
            return None, None
        raise
    return json.loads(got["Body"].read()), got.get("ETag")


def write(prepared: Prepared, *, client, bucket: str, by: str, reason: str,
          now: datetime | None = None) -> dict:
    """write the version if it is new and the allow record if it is new,
    then move `current` to the pair if it is not already there. returns what
    happened, in words and keys."""
    if (prepared.allow_doc.get("gate") or {}).get("decision") != "allow":
        raise CanonicalRefusal("this write carries no allow record",
                               "prepare it through prepare(), which asks the gate")
    if not (by or "").strip() or not (reason or "").strip():
        raise CanonicalRefusal("a write names who moved the pointer and why",
                               "give --by and --reason")
    keys = prepared.keys
    written: list[str] = []
    allow_bytes = (json.dumps(prepared.allow_doc, indent=2, allow_nan=False) + "\n").encode()
    version_new = not _exists(client, bucket, keys["data"])
    if version_new:
        puts = ((keys["envelope"], prepared.receipt_bytes, JSON_TYPE),
                (keys["allow"], allow_bytes, JSON_TYPE),
                (keys["data"], prepared.data_bytes, prepared.content_type))
    elif not _exists(client, bucket, keys["allow"]):
        puts = ((keys["allow"], allow_bytes, JSON_TYPE),)
    else:
        puts = ()                        # the same data, judged the same way: nothing to send
    for key, body, ctype in puts:
        if _put_once(client, bucket, key, body, ctype):
            written.append(key)
    allow_new = keys["allow"] in written

    pointer, etag = read_pointer(client, bucket, keys["current"])
    previous = (pointer or {}).get("sha256")
    previous_allow = (pointer or {}).get("allow")
    said = {"version": "new" if version_new else "exists",
            "allow": "new" if allow_new else "exists",
            "sha256": prepared.sha256, "allow_sha256": prepared.allow_sha256,
            "previous": previous, "previous_allow": previous_allow}
    if previous == prepared.sha256 and previous_allow == prepared.allow_sha256:
        return dict(said, pointer="unchanged", written=written, keys=keys)

    moved = {"sha256": prepared.sha256, "allow": prepared.allow_sha256,
             "previous": previous, "previous_allow": previous_allow,
             "data": prepared.data_name,
             "moved_at": _now(now), "moved_by": by.strip(), "reason": reason.strip()}
    body = (json.dumps(moved, indent=2) + "\n").encode()
    condition = {"IfMatch": etag} if pointer is not None else {"IfNoneMatch": "*"}
    try:
        client.put_object(Bucket=bucket, Key=keys["current"], Body=body,
                          ContentType=JSON_TYPE, CacheControl=POINTER_CACHE, **condition)
    except Exception as e:
        if _precondition(e):
            raise CanonicalRefusal(
                "the pointer moved while this write ran, so it was left as the "
                "other writer set it; the version is written",
                "read current, then write again if this version should be current") from None
        raise
    written.append(keys["current"])
    return dict(said, pointer="created" if pointer is None else "moved",
                written=written, keys=keys)


def make_client(profile: str):
    """boto3's S3 client under the writer's profile (D-308): the role is
    assumed from the person's own login, so no key is ever handled here."""
    import boto3
    return boto3.Session(profile_name=profile).client("s3")


# ── display copies (Contract 2, section 4) ───────────────────────────────
@dataclass
class PreparedDisplay:
    """a display copy drawn from the current version, judged, not yet sent."""
    plot: str
    harvest: str
    sha256: str
    allow_sha256: str
    name: str
    body: bytes
    envelope: dict
    stats: dict
    keys: dict = field(default_factory=dict)


def display_keys(plot: str, harvest: str, sha256: str, name: str) -> dict:
    prefix = f"{version_prefix(plot, harvest, sha256)}/display/{name}"
    return {"geojson": f"{prefix}.geojson", "envelope": f"{prefix}.envelope.json"}


def _get_bytes(client, bucket: str, key: str) -> bytes | None:
    try:
        return client.get_object(Bucket=bucket, Key=key)["Body"].read()
    except Exception as e:
        if _missing(e):
            return None
        raise


def prepare_display(plot: str, artifact: str, *, client, bucket: str, domain: str,
                    root: Path, tolerance_m: int | None = None, judge=default_judge,
                    drawer=None, validate=None, now: datetime | None = None) -> PreparedDisplay:
    """read the current version back from the bucket, check its bytes against
    its name, draw the copy, build its envelope, and ask the gate. sends
    nothing; a dry run is this alone."""
    from canopy.aws import display
    validate_plot(plot)
    validate_artifact(artifact)
    tolerance_m = display.DEFAULT_TOLERANCE_M if tolerance_m is None else tolerance_m
    pointer, _ = read_pointer(client, bucket, pointer_key(plot, artifact))
    if pointer is None:
        raise CanonicalRefusal(f"'{artifact}' has no canonical version yet",
                               "write it first: canonical <plot> <artifact> --write")
    sha, allow_sha = pointer.get("sha256"), pointer.get("allow")
    if pointer.get("data") != "data.parquet":
        raise CanonicalRefusal(f"'{artifact}' is a {pointer.get('data')} document; a display "
                               f"copy is drawn from features", "draw a features version")
    prefix = version_prefix(plot, artifact, sha)
    data = _get_bytes(client, bucket, f"{prefix}/data.parquet")
    receipt_raw = _get_bytes(client, bucket, f"{prefix}/envelope.json")
    if data is None or receipt_raw is None:
        raise CanonicalRefusal(f"version {sha[:12]} is not whole in the bucket",
                               "write it again; a write cut off partway finishes")
    if sha256_of(data) != sha:
        raise CanonicalRefusal(f"the bytes at version {sha[:12]} do not hash to its name",
                               "stop and read the bucket's history before anything else")
    receipt = json.loads(receipt_raw)
    drawer = drawer or display.draw
    id_field = (receipt.get("metadata") or {}).get("id_field")
    try:
        drawn, seconds = display.timed(drawer, data, tolerance_m=tolerance_m, id_field=id_field)
    except CanonicalRefusal:
        raise
    except Exception as e:               # a drawing's error is a refusal, never a crash
        said = (str(e).splitlines() or [""])[0][:300]
        raise CanonicalRefusal(f"drawing the copy failed: {type(e).__name__}: {said}",
                               "read the error; the version may hold a type GeoJSON "
                               "cannot carry") from None
    keys = display_keys(plot, artifact, sha, drawn["name"])
    data_url = f"https://{domain}/{prefix}/data.parquet"
    params = {"tolerance_m": tolerance_m if drawn["kind"] == "polygons" else None,
              "projected": display.PROJECTED, "web": display.WEB,
              "decimals": display.DECIMALS, "name": drawn["name"]}
    env = display.display_envelope(receipt, display_key=keys["geojson"], data_url=data_url,
                                   sha256=sha, allow_sha256=allow_sha, harvest=artifact,
                                   drawn=drawn, params=params, duration_seconds=seconds,
                                   now=now)
    if validate is None:
        from canopy.envelope import validate_envelope
        def validate(e):
            return validate_envelope(e, Path(root))
    errors = validate(env)
    if errors:
        raise CanonicalRefusal("the copy's envelope does not match the envelope schema: "
                               + "; ".join(str(x) for x in errors[:3]),
                               "fix the envelope's shape in canopy/aws/display.py")
    _judge(judge, env, plot, Path(root) / "plots" / plot)
    return PreparedDisplay(plot=plot, harvest=artifact, sha256=sha, allow_sha256=allow_sha,
                           name=drawn["name"], body=drawn["bytes"], envelope=env,
                           stats=drawn["stats"], keys=keys)


def write_display(prepared: PreparedDisplay, *, client, bucket: str) -> dict:
    """send the envelope, then the GeoJSON last, each with If-None-Match. a
    copy already there with these bytes writes nothing; one there with other
    bytes is refused, never replaced."""
    from canopy.aws.display import GEOJSON_TYPE, envelope_bytes
    keys = prepared.keys
    there = _get_bytes(client, bucket, keys["geojson"])
    if there is not None:
        if sha256_of(there) == sha256_of(prepared.body):
            return {"copy": "exists", "written": [], "keys": keys}
        raise CanonicalRefusal(
            f"a display copy named '{prepared.name}' already stands under version "
            f"{prepared.sha256[:12]} with other bytes, and a version's files never change",
            "draw it under another name (another --tolerance), or find what changed")
    written = []
    for key, body, ctype in ((keys["envelope"], envelope_bytes(prepared.envelope), JSON_TYPE),
                             (keys["geojson"], prepared.body, GEOJSON_TYPE)):
        if _put_once(client, bucket, key, body, ctype):
            written.append(key)
    return {"copy": "new", "written": written, "keys": keys}
