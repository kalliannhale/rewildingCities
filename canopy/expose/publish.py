"""
canopy/expose/publish.py ~ the publish door (Sprint 08; Contract 1's exit to ArcGIS)

one door publishes every result (F1). it reads what the canonical command has
already written and the gate has already judged, and makes or moves an item in
each target the plot declares, so the item points at a display copy by URL and
carries that version's provenance. it never uploads features: ArcGIS stores the
map, CloudFront serves the data (D-325, MP-71).

  read     the plot's targets and its record of what it published, then the
           harvest's `current` pointer, its allow record, its receipt and its
           display copy, all by public URL. the door needs no AWS credentials.
  judge    the display copy's envelope, by the one gate, at each target's
           sharing level: the license there (rule 10) and the notes that must
           travel (rule 9). a note whose text differs from the canonical allow
           record's is refused, so the map never says what the bucket does not.
  compare  the record against `current`, which says what is owed:
             no record                 create (or adopt a hand-made map)
             a new version             the layer's URL and the description
             a new allow record        the description alone (a settled note)
             new sharing               the sharing
             nothing new               unchanged
  write    only with --write: sign in once per portal and account, check who
           the portal says that is (F4), read the item as it stands, refuse a
           missing item until --replace (F2) and an item changed by hand, then
           write, then the record. one target's failure never stops another (R8).

the record, plots/<plot>/publish/published.yml, mirrors the bucket's pointer:
each item names the sha256 and allow record it shows, so the door knows what it
owes, the same way `current` knows what is current (O-4, D-327, D-328).

a choropleth (zip 8b, D-331) is a table drawn on an outline, so it has two
parents, and the door holds both: --join names the outline and --indicator the
one indicator a map colours. the copy it reads is the one drawn on the
outline's current version; a new version or allow record of either parent is
owed; the notes are checked against both allow records, the credits come from
both, and the gate at the target may name no dataset neither record holds. its
record key is <table>/<outline>/<indicator>, so one table on two outlines, or
two indicators of one copy, are two maps. the renderer of a choropleth is the
door's: the legend is a claim, so a move puts it back and says so.

`publish <plot> --check` signs in and reads every recorded item against the
record, writing nothing: the one way a deleted or hand-edited item is seen
when nothing is owed (DOORCHECK-1). it compares every item's sharing with its
target's as well as its record's (D-372).

the places map (zip 9b1, D-371) is the door's other kind of item, and the one
where it stores features: `publish <plot> --places` reads the told copy, the
refusal record and each level's display copy by URL, and copies every place
into one web map's own JSON (file storage, never a hosted feature layer,
arcgis_places.py). its record key is `places` and its kind
arcgis_places_map; it is owed a move when any of its parents moves or the map
the door would build differs, and it is checked by the hash of its stored
JSON (D-362, D-372). every entry names its kind, and an entry with none is
refused (D-371).

a lens (zip 9b2, D-385) is the door's third kind: `publish <plot> --lens <lane>`
reads every joined copy a lane draws (canopy/expose/lenses.py) and writes one
web map whose layers read them by URL, grouped by level. its record key is
`lens/<lane>` and its kind arcgis_lens_map; like the places map, the door owns
it whole and checks it by the hash of its stored JSON (D-380). a lens with any
copy still to draw is never written (LENS-1).

`publish <plot> --adopt-app <item> --to <target> --write` records an
Experience Builder app built by hand (D-366): refused unless the target's
owner owns it, it sits in the target's folder, it is published, and the plot
does not list it as a rehearsal. `--check` reads its published config again,
by hash, and its sharing. ~
"""

from __future__ import annotations

import html
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from canopy.expose.targets import PublishRefusal, load_targets, record_path, registered
from canopy.expose.targets.arcgis_webmap import (MADE_APP, MADE_LENS, MADE_PLACES, MADE_WEBMAP,
                                                 sha256_text)

VERSION = "1.0.0"
DOMAIN_ENV = "REWILDING_CANONICAL_DOMAIN"
OUTCOMES = ("would publish", "would update", "unchanged", "published", "updated",
            "refused", "failed", "as recorded", "differs")


# --- reading the bucket, by URL ---------------------------------------------

def default_fetch(url: str) -> bytes | None:
    """the bytes at a public URL, None when there is nothing there."""
    import requests
    resp = requests.get(url, timeout=60)
    if resp.status_code in (403, 404):
        return None
    resp.raise_for_status()
    return resp.content


def _json(fetch, url: str) -> dict | None:
    raw = fetch(url)
    return None if raw is None else json.loads(raw)


def _display_name(receipt: dict) -> str:
    from canopy.aws import display
    meta = receipt.get("metadata") or {}
    if meta.get("data_category") == "tabular":
        raise PublishRefusal(
            "a table has no geometry, so it has no display copy of its own",
            "draw it on an outline: canonical <plot> <table> --display --join <outline> "
            "--write, then publish it with --join <outline> --indicator <id>")
    kinds = meta.get("geometry_type")
    kinds = set(kinds if isinstance(kinds, list) else [kinds])
    if kinds <= {"Point", "MultiPoint"}:
        return display.display_name("points", display.DEFAULT_TOLERANCE_M)
    return display.display_name("polygons", display.DEFAULT_TOLERANCE_M)


def _current(fetch, base: str, plot: str, artifact: str, document: bool = False) -> dict:
    """a harvest's current version as CloudFront serves it: the pointer, the
    allow record it names and the version's receipt. a document (the place
    profile) is read only when asked for, by the places map."""
    from canopy.aws import s3
    current = _json(fetch, f"{base}/{s3.pointer_key(plot, artifact)}")
    if current is None:
        raise PublishRefusal(f"'{artifact}' has no canonical version",
                             f"write it first: canonical {plot} {artifact} --write")
    if document and current.get("data") != "data.json":
        raise PublishRefusal(f"'{artifact}' is not a document", "read the place profile")
    if not document and current.get("data") != "data.parquet":
        raise PublishRefusal(f"'{artifact}' is a {current.get('data')} document, which no "
                             f"map draws", "the explorer reads documents by URL")
    sha, allow = current["sha256"], current["allow"]
    prefix = s3.version_prefix(plot, artifact, sha)
    allow_doc = _json(fetch, f"{base}/{prefix}/allow/{allow}.json")
    receipt = _json(fetch, f"{base}/{prefix}/envelope.json")
    if allow_doc is None or receipt is None:
        raise PublishRefusal(f"version {sha[:12]} of '{artifact}' is not whole behind CloudFront",
                             "read the bucket before anything else")
    return {"current": current, "sha256": sha, "allow": allow, "allow_doc": allow_doc,
            "receipt": receipt, "prefix": prefix, "version_url": f"{base}/{prefix}"}


def record_key(artifact: str, join: str | None = None, indicator: str | None = None) -> str:
    """the record's key for one map: the harvest alone for a layer that draws
    itself; <table>/<outline>/<indicator> for a choropleth, since one table on
    two outlines, or two indicators of one copy, are two maps (MAP-4)."""
    return artifact if not join else f"{artifact}/{join}/{indicator}"


def read_copy(plot: str, artifact: str, *, domain: str, fetch=default_fetch,
              display: str | None = None, join: str | None = None,
              indicator: str | None = None, markers: bool = False) -> dict:
    """everything the door shows, read from the bucket through CloudFront and
    checked against itself: the pointer, the allow record it names, the
    version's receipt, the display copy and its envelope; with join, the
    outline's current version too, and the copy drawn on it."""
    from canopy.aws import s3
    s3.validate_plot(plot)
    s3.validate_artifact(artifact)
    base = f"https://{domain}"
    if join:
        s3.validate_artifact(join)
        if not indicator:
            raise PublishRefusal("a choropleth colours one indicator, and none was named",
                                 "give --indicator <id>")
    elif indicator or markers:
        raise PublishRefusal("--indicator and --markers draw a table on an outline",
                             "give --join <outline> too")
    t = _current(fetch, base, plot, artifact)
    sha, allow, allow_doc, receipt, prefix = (t["sha256"], t["allow"], t["allow_doc"],
                                              t["receipt"], t["prefix"])
    outline = None
    if join:
        from canopy.aws import display as _display
        if (receipt.get("metadata") or {}).get("data_category") != "tabular":
            raise PublishRefusal(f"--join draws a table on an outline; '{artifact}' is not a table",
                                 f"publish {plot} {artifact} without --join")
        o = _current(fetch, base, plot, join)
        outline = {"harvest": join, "sha256": o["sha256"], "allow": o["allow"],
                   "allow_doc": o["allow_doc"], "version_url": o["version_url"]}
        name = display or _display.joined_name(join, o["sha256"], markers=markers)
    else:
        name = display or _display_name(receipt)
    draw = (f"canonical {plot} {artifact} --display --join {join}"
            + (" --markers" if markers else "") + " --write") if join else \
        f"canonical {plot} {artifact} --display --write"
    keys = s3.display_keys(plot, artifact, sha, name)
    display_env = _json(fetch, f"{base}/{keys['envelope']}")
    if display_env is None:
        raise PublishRefusal(f"version {sha[:12]} has no display copy '{name}'",
                             f"draw it: {draw}")
    dmeta = display_env.get("metadata") or {}
    if dmeta.get("derived_from") != sha:
        raise PublishRefusal(f"the display copy '{name}' names another version",
                             "read the bucket before anything else")
    if join:
        drawn_on = dmeta.get("joined_to") or {}
        if drawn_on.get("harvest") != join or drawn_on.get("sha256") != outline["sha256"]:
            raise PublishRefusal(
                f"the copy '{name}' is drawn on {drawn_on.get('harvest')} version "
                f"{str(drawn_on.get('sha256'))[:12]}, not {join}'s current version "
                f"{outline['sha256'][:12]}", f"draw it on the current outline: {draw}")
        if (dmeta.get("display_kind") == "markers") != bool(markers):
            raise PublishRefusal(f"the copy '{name}' is not drawn as "
                                 f"{'markers' if markers else 'outlines'}",
                                 "name the copy that matches, or drop --display")
        if indicator not in ((dmeta.get("join") or {}).get("indicators") or []):
            raise PublishRefusal(
                f"no indicator '{indicator}' in this copy",
                f"one of {', '.join((dmeta.get('join') or {}).get('indicators') or []) or '(none)'}")
    raw = fetch(f"{base}/{keys['geojson']}")
    if raw is None:
        raise PublishRefusal(f"the display copy '{name}' has an envelope but no GeoJSON",
                             f"draw it again: {draw}")
    level = (dmeta.get("joined_to") or {}).get("level")
    title = (f"{indicator} by {level} ({plot})" if join else f"{artifact} ({plot})")
    return {"plot": plot, "artifact": artifact, "sha256": sha, "allow": allow,
            "current": t["current"], "allow_doc": allow_doc, "receipt": receipt,
            "display": name, "display_env": display_env, "geojson": json.loads(raw),
            "url": f"{base}/{keys['geojson']}", "version_url": t["version_url"],
            "harvest_url": f"{base}/harvests/{plot}/{artifact}/versions/",
            "title": title, "outline": outline, "indicator": indicator,
            "markers": bool(markers), "key": record_key(artifact, join, indicator)}


# --- the gate, at the door ---------------------------------------------------

def default_judge(envelope: dict, *, plot: str, target: str, sharing_level: str,
                  plot_dir: Path) -> dict:
    from canopy.expose.check import check_envelope
    return check_envelope(envelope, plot=plot, target=target,
                          sharing_level=sharing_level, plot_dir=plot_dir)


def judge_at(judge, copy: dict, target, plot_dir: Path) -> dict:
    """the gate's allow record at this target, or a refusal. every note the
    gate binds here must leave with the text the canonical allow record holds."""
    try:
        res = judge(copy["display_env"], plot=copy["plot"], target=target.id,
                    sharing_level=target.sharing, plot_dir=plot_dir)
    except ValueError as e:                          # rule 1, said plainly
        raise PublishRefusal(str(e), "correct the declaration") from None
    if res.get("decision") != "allow":
        said = "; ".join(f"rule {r.get('rule')}: {r.get('reason')}"
                         for r in res.get("refusals") or [])
        admit = "; ".join(str(r.get("would_admit")) for r in res.get("refusals") or [])
        raise PublishRefusal(f"the gate refused it at {target.sharing}: {said}",
                             admit or "read the refusal")
    record = res["record"]
    docs = allow_docs(copy)
    held: dict = {}
    for doc in docs:
        for note, text in ((doc.get("gate") or {}).get("context_text") or {}).items():
            if note in held and held[note] != text:
                raise PublishRefusal(
                    f"note '{note}' reads one way in the table's allow record and another in "
                    f"the outline's, so the map cannot say both",
                    "write the older parent's version again, which moves its allow record "
                    "(D-320), then publish")
            held[note] = text
    for note, text in (record.get("context_text") or {}).items():
        if held.get(note) != text:
            raise PublishRefusal(
                f"note '{note}' reads differently in seeds/notes than in the canonical "
                f"allow record, so the map would say what the bucket does not",
                f"write the canonical version again, which moves its allow record "
                f"(D-320), then publish")
    credited = {r.get("dataset") for doc in docs
                for r in ((doc.get("gate") or {}).get("license") or [])}
    unheld = sorted({r.get("dataset") for r in record.get("license") or []} - credited)
    if unheld:
        raise PublishRefusal(
            f"the gate at {target.sharing} names dataset(s) {', '.join(unheld)}, which no "
            f"canonical allow record holds, so the item's credits would leave one out",
            "write the parent whose lineage holds it again, then publish")
    return record


def allow_docs(copy: dict) -> list[dict]:
    """the canonical allow records a map shows: the table's, then the outline's."""
    docs = [copy["allow_doc"]]
    if copy.get("outline"):
        docs.append(copy["outline"]["allow_doc"])
    return docs


# --- the record --------------------------------------------------------------

def read_record(plot_dir: Path) -> dict:
    path = record_path(plot_dir)
    if not path.is_file():
        return {"targets": {}}
    doc = yaml.safe_load(path.read_text()) or {}
    doc.setdefault("targets", {})
    return doc


def write_record(plot_dir: Path, doc: dict) -> None:
    """written whole, through a temporary file in the same folder, so a crash
    never leaves half a record."""
    path = record_path(plot_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    head = ("# written by the publish door (canopy/expose/publish.py); edited by\n"
            "# nothing else. each entry mirrors the bucket's `current` pointer (D-327).\n")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".published.", suffix=".yml")
    with os.fdopen(fd, "w") as f:
        f.write(head + yaml.safe_dump(doc, sort_keys=True, allow_unicode=True))
    os.replace(tmp, path)


# --- the plot's credit line --------------------------------------------------

CREDIT_FIELDS = ("credit", "citation", "data_guide")


def load_credit(plot_dir: Path) -> dict | None:
    """plots/<plot>/publish/credit.yml: the credit line, the suggested citation
    (with {title}, {version} and {url} filled per item) and the data guide line,
    one home for words every item carries. a plot without the file carries
    none; a file missing a field, or with a field the door does not know, is
    refused, never guessed."""
    path = Path(plot_dir) / "publish" / "credit.yml"
    if not path.is_file():
        return None
    doc = yaml.safe_load(path.read_text()) or {}
    unknown = sorted(set(doc) - set(CREDIT_FIELDS))
    missing = [k for k in CREDIT_FIELDS if not str(doc.get(k) or "").strip()]
    if unknown or missing:
        raise PublishRefusal(
            f"{path.name}: " + "; ".join(([f"unknown fields {', '.join(unknown)}"] if unknown else [])
                                         + ([f"missing {', '.join(missing)}"] if missing else [])),
            f"give exactly {', '.join(CREDIT_FIELDS)}")
    try:
        str(doc["citation"]).format(title="t", version="v", url="u")
    except (KeyError, IndexError, ValueError) as e:
        raise PublishRefusal(f"{path.name}: the citation names a field the door does not fill "
                             f"({e})", "use only {title}, {version} and {url}") from None
    return {k: str(doc[k]).strip() for k in CREDIT_FIELDS}


# --- planning and writing ----------------------------------------------------

@dataclass
class Outcome:
    target: str
    outcome: str
    lines: list = field(default_factory=list)


def owed(entry: dict | None, copy: dict, built, target, adopt: str | None) -> str:
    if entry is None:
        return "adopt" if adopt else "create"
    outline, was = copy.get("outline") or {}, entry.get("outline") or {}
    if entry.get("sha256") != copy["sha256"] or was.get("sha256") != outline.get("sha256"):
        return "move"
    if built.extra.get("renderer_sha256") and entry.get("renderer_sha256") != \
            built.extra["renderer_sha256"]:
        return "restyle"
    if (entry.get("allow") != copy["allow"] or was.get("allow") != outline.get("allow")
            or entry.get("description_sha256") != sha256_text(built.description)):
        return "describe"
    if entry.get("sharing") != target.sharing or list(entry.get("groups") or []) != list(target.groups):
        return "share"
    if not entry.get("description_seen_sha256"):
        return "reseen"
    return "unchanged"


# what the target is owed, said so it reads true before a write and after it;
# the outcome line says what was done (DOORSAY-1)
_SAY = {"create": "owed: a new web map in folder '{folder}'",
        "adopt": "owed: adopting item {adopt}, its layer moved to this version",
        "move": "owed: the layer moved from {old} to {new}, and the description",
        "restyle": "owed: the layer's colours, which the door now draws differently (RAMP-1), "
                   "and the description",
        "describe": "owed: the description alone (a new allow record or new words)",
        "share": "owed: sharing at {sharing}",
        "reseen": "owed: recording the description as ArcGIS stores it, which it rewrites (D-349)",
        "unchanged": "nothing owed"}


def _versions(entry: dict | None, copy: dict) -> tuple[str, str]:
    """the versions a move goes from and to, both parents named for a choropleth."""
    def say(sha, outline):
        s = str(sha or "")[:12]
        return f"{s} on {str((outline or {}).get('sha256') or '')[:12]}" if copy.get("outline") else s
    entry = entry or {}
    return (say(entry.get("sha256"), entry.get("outline")),
            say(copy["sha256"], copy.get("outline")))


def described_as_recorded(stored: str, entry: dict, built=None) -> bool:
    """whether an item's description is the one the door wrote (D-349).
    ArcGIS Online rewrites a description as it saves it: every &#x27; that
    html.escape wrote came back as ' (read 2026-11-17), so the text it stores is
    not the bytes the door sent. so the door reads each description back after
    it writes and records that hash, description_seen_sha256, and compares to
    it. an item written before the read-back has only the sent hash: it is as
    recorded when its stored text is the sent text, or when `built` (the door's
    description rebuilt from the same records) hashes to what was sent and
    differs from the stored text only in how characters are written."""
    seen = entry.get("description_seen_sha256")
    if seen:
        return sha256_text(stored) == seen
    if sha256_text(stored) == entry.get("description_sha256"):
        return True
    return (built is not None and sha256_text(built.description) == entry.get("description_sha256")
            and html.unescape(stored) == html.unescape(built.description))


def _seen(kind, session, item_id: str) -> str | None:
    """the hash of the description as the portal stores it, read back."""
    state = kind.read(session, item_id)
    return sha256_text(state["description"]) if state else None


def _check_live(kind, session, target, entry: dict, replace: bool, built=None) -> str | None:
    """the item as it stands, against the record. returns 'create' when a missing
    item is to be replaced, None when the item is as the door left it."""
    state = kind.read(session, entry["item_id"])
    if state is None:
        if replace:
            return "create"
        raise PublishRefusal(f"item {entry['item_id']} is gone from {target.portal}",
                             "publish with --replace to make a new one (F2)")
    if state["owner"] != target.owner:
        raise PublishRefusal(f"item {entry['item_id']} is owned by {state['owner']}, "
                             f"not {target.owner}", "ownership moves in ArcGIS, by a person")
    live = kind.layer_url(state["data"], entry["layer_id"])
    if live != entry["url"]:
        raise PublishRefusal(f"the item's layer was changed by hand: it reads {live}",
                             "set it back, or adopt the item again")
    if not described_as_recorded(state["description"], entry, built):
        if not entry.get("description_seen_sha256") and built is None:
            raise PublishRefusal(
                "the item was written before the door read descriptions back, and its "
                "stored description cannot be told from the sent one now that the records "
                "have moved", "publish it with --write once at the version it shows, which "
                "records how ArcGIS stores it (D-349); or undo any edit, then publish")
        raise PublishRefusal("the item's description was changed by hand; it is the "
                             "door's, because it carries the notes (D-328)",
                             "undo the edit in ArcGIS, then publish again")
    return None


def _entry(copy, target, built, item_id, layer_id, gate_record, by, reason, prior,
           rest_version, now) -> dict:
    return {
        "kind": built.extra.get("made") or MADE_WEBMAP, "portal": target.portal,
        "owner": target.owner,
        "folder": target.folder, "item_id": item_id, "layer_id": layer_id,
        "display": copy["display"], "url": copy["url"],
        "sha256": copy["sha256"], "allow": copy["allow"],
        "description_sha256": sha256_text(built.description),
        "sharing": target.sharing, "groups": list(target.groups),
        "gate": {"decision": "allow", "target": target.id,
                 "sharing_level": gate_record.get("sharing_level"),
                 "gate_version": gate_record.get("gate_version"),
                 "context_notes": sorted((gate_record.get("context_text") or {}))},
        "door_version": VERSION, "rest_version": rest_version,
        "moved_at": now, "moved_by": by, "reason": reason,
        "previous": ({"sha256": prior.get("sha256"), "allow": prior.get("allow"),
                      **({"outline": prior.get("outline")} if prior.get("outline") else {})}
                     if prior else None),
        **({"outline": {"harvest": copy["outline"]["harvest"],
                        "sha256": copy["outline"]["sha256"],
                        "allow": copy["outline"]["allow"]},
            "indicator": copy["indicator"], "markers": copy["markers"],
            "renderer_sha256": built.extra.get("renderer_sha256")}
           if copy.get("outline") else {}),
    }


def publish(plot: str, artifact: str, target_ids: list[str], *, root: Path,
            write: bool = False, by: str | None = None, reason: str | None = None,
            adopt: str | None = None, replace: bool = False, display: str | None = None,
            domain: str | None = None, fetch=default_fetch, judge=default_judge,
            kinds: dict | None = None, ask=None, now: str | None = None,
            join: str | None = None, indicator: str | None = None,
            markers: bool = False) -> list[Outcome]:
    """the door, for one artifact and the named targets. a dry run unless write."""
    plot_dir = Path(root) / "plots" / plot
    kinds = kinds or registered(version=VERSION)
    targets = load_targets(plot_dir, kinds)
    unknown = [t for t in target_ids if t not in targets]
    if unknown:
        raise PublishRefusal(f"no target named {', '.join(unknown)} in this plot",
                             f"one of {', '.join(sorted(targets))}")
    if adopt and len(target_ids) != 1:
        raise PublishRefusal("--adopt names one item, in one target", "give one --to")
    if adopt and join:
        raise PublishRefusal("a hand-made map is adopted for a layer that draws itself; a "
                             "choropleth's renderer is the door's", "publish it without --adopt")
    domain = domain or os.environ.get(DOMAIN_ENV)
    if not domain:
        raise PublishRefusal(f"{DOMAIN_ENV} is not set, so the door cannot read the bucket",
                             "set it as the canonical command needs it")
    copy = read_copy(plot, artifact, domain=domain, fetch=fetch, display=display,
                     join=join, indicator=indicator, markers=markers)
    key = copy["key"]
    from canopy.expose.records import load_licenses
    copy["licenses"] = load_licenses(Path(root) / "seeds" / "licenses")
    copy["credit"] = load_credit(plot_dir)
    when = now or datetime.now(timezone.utc).isoformat()
    record = read_record(plot_dir)
    sessions: dict = {}
    out: list[Outcome] = []

    for tid in target_ids:
        target = targets[tid]
        kind = kinds[target.kind]
        o = Outcome(tid, "refused")
        out.append(o)
        o.lines.append(f"{target.kind}, owned by {target.owner} at {target.portal}, "
                       f"{target.sharing}")
        if target.owner_kind == "personal":
            o.lines.append("warning: a person's account owns this target's items; "
                           "when they leave, the items leave with them (R7)")
        try:
            gate_record = judge_at(judge, copy, target, plot_dir)
            notes = sorted(gate_record.get("context_text") or {})
            o.lines.append(f"gate: may leave at {target.sharing}"
                           + (f"; carries {', '.join(notes)}" if notes else "; no notes bind it"))
            entry = (record["targets"].get(tid) or {}).get(key)
            _kind_of(entry, MADE_WEBMAP)
            if entry and (entry.get("portal") != target.portal or entry.get("owner") != target.owner):
                raise PublishRefusal(f"the record's item lives at {entry.get('portal')} as "
                                     f"{entry.get('owner')}, not as this target declares",
                                     "ownership moves in ArcGIS, by a person; then the record")
            built = kind.build(target, copy)
            due = owed(entry, copy, built, target, adopt)
            old, new = _versions(entry, copy)
            o.lines.append(_SAY[due].format(folder=target.folder, adopt=adopt, old=old, new=new,
                                            sharing=target.sharing))
            o.lines.append(f"reads {copy['url']}")
            if not write:
                o.outcome = "unchanged" if due == "unchanged" else (
                    "would publish" if due in ("create", "adopt") else "would update")
                o.lines.append("a dry run: signed in nowhere, wrote nothing; the item "
                               "itself is checked when the door writes")
                continue
            if due == "unchanged":
                o.outcome = "unchanged"
                continue

            session = _session(sessions, kind, target, ask)

            layer_id = built.layer_id
            if entry is not None:
                if _check_live(kind, session, target, entry, replace,
                               built if due in ("reseen", "share") else None) == "create":
                    due, entry_prior = "create", entry
                    o.lines.append(f"item {entry['item_id']} is gone; making a new one (--replace)")
                else:
                    entry_prior, layer_id = entry, entry["layer_id"]
            else:
                entry_prior = None

            if due == "create":
                item_id = kind.create(session, target, built)
                # recorded before it is shared, unshared, so a share that fails
                # leaves a record that owes the share, never a second item
                provisional = _entry(copy, target, built, item_id, layer_id, gate_record,
                                     by, reason, entry_prior, None, when)
                provisional["sharing"] = None
                record["targets"].setdefault(tid, {})[key] = provisional
                write_record(plot_dir, record)
                kind.share(session, target, item_id)
                seen = _seen(kind, session, item_id)
                o.outcome = "published"
            elif due == "adopt":
                state = kind.read(session, adopt)
                if state is None:
                    raise PublishRefusal(f"item {adopt} is not in {target.portal}",
                                         "check the id in the item page's address")
                if state["owner"] != target.owner:
                    raise PublishRefusal(f"item {adopt} is owned by {state['owner']}, not "
                                         f"{target.owner}", "ownership moves in ArcGIS, by a person")
                hit = kind.adoptable_layer(state["data"], copy["harvest_url"])
                if hit is None:
                    raise PublishRefusal(f"no layer in item {adopt} reads {artifact}",
                                         "adopt a map whose layer reads this harvest")
                layer_id = hit[0]
                kind.update(session, target, adopt, built,
                            data=kind.moved(state["data"], layer_id, built))
                kind.share(session, target, adopt)
                item_id = adopt
                seen = _seen(kind, session, item_id)
                o.outcome = "published"
            else:
                item_id = entry["item_id"]
                if due in ("move", "restyle"):
                    state = kind.read(session, item_id)
                    if (built.extra.get("renderer_sha256") and hasattr(kind, "renderer_sha256")
                            and kind.renderer_sha256(state["data"], layer_id)
                            != entry.get("renderer_sha256")):
                        o.lines.append("the renderer had been restyled by hand; the door's is "
                                       "put back, since a choropleth's legend is a claim")
                    kind.update(session, target, item_id, built,
                                data=kind.moved(state["data"], layer_id, built))
                elif due == "describe":
                    kind.update(session, target, item_id, built, data=None)
                if due != "reseen":
                    kind.share(session, target, item_id)
                seen = _seen(kind, session, item_id)
                o.outcome = "updated"

            rest = kind.rest_version(session) if hasattr(kind, "rest_version") else None
            final = _entry(copy, target, built, item_id, layer_id, gate_record, by, reason,
                           entry_prior, rest, when)
            final["description_seen_sha256"] = seen
            record["targets"].setdefault(tid, {})[key] = final
            write_record(plot_dir, record)
            o.lines.append(f"item {item_id}: {target.portal}/home/item.html?id={item_id}")
        except PublishRefusal as e:
            o.outcome = "refused"
            o.lines.append(f"refused: {e.reason}")
            o.lines.append(f"  would admit it: {e.would_admit}")
        except Exception as e:                       # one target's failure never stops another
            o.outcome = "failed"
            said = (str(e).splitlines() or [""])[0][:300]
            o.lines.append(f"failed: {type(e).__name__}: {said}")
    return out


def check(plot: str, target_ids: list[str], *, root: Path, kinds: dict | None = None,
          ask=None, fresh_refusals=None) -> list[Outcome]:
    """every recorded item of the named targets (every target, when none is
    named) read as it stands and set beside the record. signs in, writes
    nothing, and moves nothing: `as recorded` means the record, the item and
    the target agree (DOORCHECK-1). each item's sharing is compared with its
    target's as well as its record's (D-372); a places map is compared by the
    hash of its stored JSON, and the refusal record it tells is judged again,
    so a stale one is said (D-363)."""
    plot_dir = Path(root) / "plots" / plot
    kinds = kinds or registered(version=VERSION)
    targets = load_targets(plot_dir, kinds)
    unknown = [t for t in target_ids if t not in targets]
    if unknown:
        raise PublishRefusal(f"no target named {', '.join(unknown)} in this plot",
                             f"one of {', '.join(sorted(targets))}")
    record = read_record(plot_dir)
    sessions: dict = {}
    fresh = {}
    out: list[Outcome] = []
    for tid in (target_ids or sorted(record["targets"])):
        if tid not in targets:
            out.append(Outcome(tid, "differs", [f"the record names a target '{tid}' this "
                                                f"plot no longer declares"]))
            continue
        target, kind = targets[tid], kinds[targets[tid].kind]
        for key, entry in sorted((record["targets"].get(tid) or {}).items()):
            o = Outcome(f"{tid} {key}", "differs")
            out.append(o)
            try:
                made = entry.get("kind")
                if made not in (MADE_WEBMAP, MADE_PLACES, MADE_LENS, MADE_APP):
                    o.lines.append(f"the record's entry names no kind the door makes "
                                   f"({made!r}), so it cannot be read (D-371)")
                    continue
                if entry.get("portal") != target.portal or entry.get("owner") != target.owner:
                    o.lines.append(f"the record's item lives at {entry.get('portal')} as "
                                   f"{entry.get('owner')}, not as the target declares")
                    continue
                session = _session(sessions, kind, target, ask)
                if made == MADE_APP:
                    _check_app(kind, session, target, entry, o)
                    continue
                state = kind.read(session, entry["item_id"])
                found = []
                if entry.get("sharing") != target.sharing:
                    found.append(f"the record says {entry.get('sharing')}, the target "
                                 f"{target.sharing}: publish again to share it as declared")
                if state is None:
                    found.append(f"item {entry['item_id']} is gone; publish with --replace")
                else:
                    if state["owner"] != target.owner:
                        found.append(f"owned by {state['owner']}, not {target.owner}")
                    if made in (MADE_PLACES, MADE_LENS):
                        from canopy.expose.targets.arcgis_places import map_sha256
                        stored = map_sha256(state["data"])
                        if stored != entry.get("map_sha256"):
                            found.append(f"its stored map hashes to {stored[:12]}, not the "
                                         f"recorded {str(entry.get('map_sha256'))[:12]}: "
                                         f"changed by hand; publish it again with --write "
                                         f"--restore to write the door's map back (D-395)")
                        if entry.get("title") and state.get("title") != entry["title"]:
                            found.append(f"its title was changed by hand to "
                                         f"{state.get('title')!r}; --restore puts it back (D-398)")
                    if made == MADE_PLACES:
                        if "now" not in fresh:
                            fresh["now"] = (fresh_refusals or _fresh_refusals)(plot, Path(root))
                        if fresh["now"] != entry.get("refusals_sha256"):
                            found.append(f"the refusal record it tells "
                                         f"({str(entry.get('refusals_sha256'))[:12]}) is stale: "
                                         f"the gate judges {fresh['now'][:12]} now; write it "
                                         f"with canonical {plot} --refusals --write, tell the "
                                         f"profile again, then publish")
                    elif made == MADE_WEBMAP:
                        live = kind.layer_url(state["data"], entry["layer_id"])
                        if live != entry["url"]:
                            found.append(f"its layer reads {live}, not the recorded {entry['url']}")
                    if not described_as_recorded(state["description"], entry):
                        found.append(
                            "its description was changed by hand" if entry.get("description_seen_sha256")
                            else "its description as ArcGIS stores it is not yet recorded (it was "
                                 "written before the door read descriptions back): publish it with "
                                 "--write once, which checks it against the door's own text and "
                                 "records it (D-349)")
                    for said, level in (("record", entry.get("sharing")),
                                        ("target", target.sharing)):
                        if state.get("access") != _access_of(level):
                            found.append(f"it is shared '{state.get('access')}', the {said} "
                                         f"says {level}")
                    if (entry.get("renderer_sha256") and hasattr(kind, "renderer_sha256")
                            and kind.renderer_sha256(state["data"], entry["layer_id"])
                            != entry["renderer_sha256"]):
                        found.append("its renderer was restyled by hand; the next move puts "
                                     "the door's back")
                if found:
                    o.lines.extend(dict.fromkeys(found))
                else:
                    o.outcome = "as recorded"
                    o.lines.append(f"item {entry['item_id']} is as the door left it")
            except PublishRefusal as e:
                o.outcome = "refused"
                o.lines.append(f"refused: {e.reason}")
            except Exception as e:
                o.outcome = "failed"
                o.lines.append(f"failed: {type(e).__name__}: {(str(e).splitlines() or [''])[0][:300]}")
    return out


def _fresh_refusals(plot: str, root: Path) -> str:
    """the sha256 the refusal record would have if it were judged now."""
    from canopy.aws import told
    return told._sha(told.document_bytes(told.refusal_record(plot, root=root)))


def _kind_of(entry: dict | None, wanted: str) -> None:
    """an entry names what the door made (D-371): one with no kind, or another
    kind than this path makes, is refused, never guessed."""
    if entry is None:
        return
    made = entry.get("kind")
    if made != wanted:
        raise PublishRefusal(
            f"the record's entry is {'of no kind' if not made else f'a {made}'}, and this "
            f"path makes a {wanted} (D-371)",
            "publish it by its own path; an entry with no kind is set right in the record "
            "by a person, from the item it names")


def _session(sessions: dict, kind, target, ask):
    """one sign-in per portal and account, checked against who the portal says
    it is (F4)."""
    account = (target.portal, target.owner)
    if account not in sessions:
        password = (ask or _ask)(f"password for {target.owner} at {target.portal} "
                                 f"(typed, never stored): ")
        session = kind.sign_in(target, password)
        who = kind.whoami(session)
        if who != target.owner:
            raise PublishRefusal(f"the portal says this sign-in is {who}, not "
                                 f"{target.owner}", "sign in as the target's owner (F4)")
        sessions[account] = session
    return sessions[account]


def _access_of(sharing: str | None) -> str | None:
    """the portal's word for a sharing level, as an item reports its access."""
    return {"private": "private", "organization": "org", "public": "public"}.get(sharing or "")


def _ask(prompt: str) -> str:
    import getpass
    return getpass.getpass(prompt)


# --- the places map (zip 9b1, D-371) ------------------------------------------

PLACES_KEY = "places"


def read_places(plot: str, *, domain: str, root: Path, fetch=default_fetch) -> dict:
    """every parent of the places map, read through CloudFront and checked
    against itself: the profile's current version and the refusal record it is
    told with, the told copy those name, and each level's display copy on its
    outline's current version. the told copy's name is made from the garden's
    own files, so a seed changed and not yet told is refused here, loudly."""
    from canopy.aws import s3, told
    from canopy.expose.targets import arcgis_places as ap
    s3.validate_plot(plot)
    base = f"https://{domain}"
    prof = _current(fetch, base, plot, told.PROFILE, document=True)
    pointer = _json(fetch, f"{base}/{s3.pointer_key(plot, told.REFUSALS)}")
    if pointer is None:
        raise PublishRefusal("no refusal record is written",
                             f"write it: canonical {plot} --refusals --write")
    rsha = pointer["sha256"]
    rurl = f"{base}/{told.refusals_keys(plot, rsha)['data']}"
    raw = fetch(rurl)
    if raw is None or told._sha(raw) != rsha:
        raise PublishRefusal(f"the refusal record {rsha[:12]} is missing or does not hash to "
                             f"its name", "read the bucket before anything else")
    try:
        name = told.told_name(told.told_inputs(root), rsha)
    except s3.CanonicalRefusal as e:
        raise PublishRefusal(e.reason, e.would_admit) from None
    keys = told.told_keys(plot, prof["sha256"], name)
    tell = f"canonical {plot} {told.PROFILE} --told --write"
    env = _json(fetch, f"{base}/{keys['envelope']}")
    body = fetch(f"{base}/{keys['json']}")
    if env is None or body is None:
        raise PublishRefusal(f"profile version {prof['sha256'][:12]} has no told copy "
                             f"'{name}' for these seeds and refusal record {rsha[:12]}",
                             f"tell it: {tell}")
    doc = json.loads(body)
    if ((env.get("metadata") or {}).get("derived_from") != prof["sha256"]
            or doc.get("profile_version") != prof["sha256"]
            or doc.get("refusals_version") != rsha):
        raise PublishRefusal(f"the told copy '{name}' names another version",
                             "read the bucket before anything else")
    parents = [{"role": "told places", "harvest": told.PROFILE, "sha256": prof["sha256"],
                "allow": prof["allow"], "copy": name, "url": f"{base}/{keys['json']}",
                "allow_doc": prof["allow_doc"], "env": env}]
    levels = {}
    for lv in ap.ORDER:
        harvest = ap.OUTLINES[lv]
        o = _current(fetch, base, plot, harvest)
        shaped = lv in ap.SHAPED
        copy_name = ap.TOWNS_COPY if shaped else ap.POINTS_COPY
        draw = (f"canonical {plot} {harvest} --display "
                + ("--tolerance 250" if shaped else "--markers") + " --write")
        dkeys = s3.display_keys(plot, harvest, o["sha256"], copy_name)
        denv = _json(fetch, f"{base}/{dkeys['envelope']}")
        graw = fetch(f"{base}/{dkeys['geojson']}")
        if denv is None or graw is None:
            raise PublishRefusal(f"version {o['sha256'][:12]} of {harvest} has no display copy "
                                 f"'{copy_name}'", f"draw it: {draw}")
        if (denv.get("metadata") or {}).get("derived_from") != o["sha256"]:
            raise PublishRefusal(f"the copy '{copy_name}' of {harvest} names another version",
                                 "read the bucket before anything else")
        url = f"{base}/{dkeys['geojson']}"
        levels[lv] = {"harvest": harvest, "sha256": o["sha256"], "allow": o["allow"],
                      "copy": copy_name, "url": url, "geojson": json.loads(graw)}
        parents.append({"role": f"{ap.LEVEL_LABELS[lv]} {'shapes' if shaped else 'points'}",
                        "harvest": harvest, "sha256": o["sha256"], "allow": o["allow"],
                        "copy": copy_name, "url": url, "allow_doc": o["allow_doc"],
                        "env": denv})
    return {"plot": plot, "title": f"Places in {plot}: the explorer's map ({plot})",
            "told": {"rows": doc.get("rows") or [], "profile_sha256": prof["sha256"],
                     "refusals_sha256": rsha, "refusals_url": rurl, "name": name,
                     "version_url": prof["version_url"]},
            "levels": levels, "parents": parents}


def _parents(places: dict) -> dict:
    return {p["role"]: {"harvest": p["harvest"], "sha256": p["sha256"], "allow": p["allow"],
                        "copy": p["copy"]} for p in places["parents"]}


def owed_places(entry: dict | None, places: dict, built, target) -> str:
    """what a places map is owed: a move when a parent's version or copy moved,
    or the door would build another map; the description alone when only an
    allow record or the words moved."""
    if entry is None:
        return "create"
    was, now = entry.get("parents") or {}, _parents(places)
    moved = set(was) != set(now) or any(
        (was[r].get("sha256"), was[r].get("copy")) != (now[r]["sha256"], now[r]["copy"])
        for r in now if r in was)
    if moved or entry.get("map_sha256") != built.extra["map_sha256"]:
        return "move"
    if (any(was[r].get("allow") != now[r]["allow"] for r in now)
            or entry.get("description_sha256") != sha256_text(built.description)):
        return "describe"
    if entry.get("sharing") != target.sharing or list(entry.get("groups") or []) != list(target.groups):
        return "share"
    if not entry.get("description_seen_sha256"):
        return "reseen"
    return "unchanged"


_SAY_PLACES = {"create": "owed: a new places map in folder '{folder}'",
               "move": "owed: the whole map, rewritten from its parents (D-380), and the description",
               "describe": "owed: the description alone (a new allow record or new words)",
               "share": "owed: sharing at {sharing}",
               "reseen": "owed: recording the description as ArcGIS stores it (D-349)",
               "unchanged": "nothing owed"}


def _check_places_live(kind, session, target, entry: dict, replace: bool, built=None,
                       what: str = "places map", restore: bool = False) -> str | None:
    """a map the door owns whole (the places map, a lens) as it stands, against
    the record (D-372, D-380). None when it stands as recorded; "create" when it
    is gone and replace was asked; "restore" when it was changed by hand and
    restore was asked, so the door writes its whole map back into the same item,
    keeping the id an app holds (D-395)."""
    from canopy.expose.targets.arcgis_places import map_sha256
    state = kind.read(session, entry["item_id"])
    if state is None:
        if replace:
            return "create"
        raise PublishRefusal(f"item {entry['item_id']} is gone from {target.portal}",
                             "publish with --replace to make a new one (F2)")
    if state["owner"] != target.owner:
        raise PublishRefusal(f"item {entry['item_id']} is owned by {state['owner']}, "
                             f"not {target.owner}", "ownership moves in ArcGIS, by a person")
    stored = map_sha256(state["data"])
    if stored != entry.get("map_sha256"):
        if restore:
            return "restore"
        raise PublishRefusal(f"the {what} was changed by hand: it hashes to {stored[:12]}, "
                             f"not the recorded {str(entry.get('map_sha256'))[:12]}",
                             "the door owns the whole map (D-380): publish again with "
                             "--write --restore, which writes it back into the same item (D-395)")
    if entry.get("title") and state.get("title") != entry["title"]:
        if restore:
            return "restore"
        raise PublishRefusal(f"the {what}'s title was changed by hand to {state.get('title')!r}; "
                             f"the door owns the whole item (D-398)",
                             "publish again with --write --restore, which puts the title back")
    if not described_as_recorded(state["description"], entry, built):
        if restore:
            return "restore"
        raise PublishRefusal("the item's description was changed by hand; it is the "
                             "door's, because it carries the notes (D-328)",
                             "publish again with --write --restore, or undo the edit in ArcGIS")
    return None


def publish_places(plot: str, target_ids: list[str], *, root: Path, write: bool = False,
                   by: str | None = None, reason: str | None = None, replace: bool = False,
                   domain: str | None = None, fetch=default_fetch, judge=default_judge,
                   kinds: dict | None = None, ask=None, now: str | None = None,
                   restore: bool = False) -> list[Outcome]:
    """the places map, for the named targets. a dry run unless write. with
    replace or restore, the item itself is read even when nothing is owed."""
    plot_dir = Path(root) / "plots" / plot
    kinds = kinds or registered(version=VERSION)
    targets = load_targets(plot_dir, kinds)
    unknown = [t for t in target_ids if t not in targets]
    if unknown:
        raise PublishRefusal(f"no target named {', '.join(unknown)} in this plot",
                             f"one of {', '.join(sorted(targets))}")
    domain = domain or os.environ.get(DOMAIN_ENV)
    if not domain:
        raise PublishRefusal(f"{DOMAIN_ENV} is not set, so the door cannot read the bucket",
                             "set it as the canonical command needs it")
    places = read_places(plot, domain=domain, root=Path(root), fetch=fetch)
    from canopy.expose.records import load_licenses
    places["licenses"] = load_licenses(Path(root) / "seeds" / "licenses")
    places["credit"] = load_credit(plot_dir)
    when = now or datetime.now(timezone.utc).isoformat()
    record = read_record(plot_dir)
    sessions: dict = {}
    out: list[Outcome] = []
    for tid in target_ids:
        target = targets[tid]
        kind = kinds[target.kind]
        o = Outcome(tid, "refused")
        out.append(o)
        o.lines.append(f"{target.kind}, owned by {target.owner} at {target.portal}, "
                       f"{target.sharing}")
        if target.owner_kind == "personal":
            o.lines.append("warning: a person's account owns this target's items; "
                           "when they leave, the items leave with them (R7)")
        try:
            records = [judge_at(judge, {"display_env": p["env"], "plot": plot,
                                        "allow_doc": p["allow_doc"]}, target, plot_dir)
                       for p in places["parents"]]
            notes = sorted({n for r in records for n in (r.get("context_text") or {})})
            o.lines.append(f"gate: every parent may leave at {target.sharing}"
                           + (f"; carries {', '.join(notes)}" if notes else "; no notes bind it"))
            entry = (record["targets"].get(tid) or {}).get(PLACES_KEY)
            _kind_of(entry, MADE_PLACES)
            if entry and (entry.get("portal") != target.portal or entry.get("owner") != target.owner):
                raise PublishRefusal(f"the record's item lives at {entry.get('portal')} as "
                                     f"{entry.get('owner')}, not as this target declares",
                                     "ownership moves in ArcGIS, by a person; then the record")
            built = kind.build_places(target, places)
            report = built.extra["report"]
            for lv, line in report["levels"].items():
                o.lines.append(f"{lv}: {line['placed']} of {line['told']} told, as "
                               + (f"shapes rounded to {'1 m' if line['decimals'] == 0 else '0.1 m'}"
                                  if line["shaped"] else "points"))
            for x in report["left_out"]:
                o.lines.append(f"left out: {x}, no place in its level's copy")
            size = len(json.dumps(built.data).encode("utf-8"))
            o.lines.append(f"the map: {size:,} bytes, sha256 {built.extra['map_sha256'][:12]} "
                           f"(LIMIT-1 has no line yet, so none is applied)")
            due = owed_places(entry, places, built, target)
            o.lines.append(_SAY_PLACES[due].format(folder=target.folder, sharing=target.sharing)
                           .replace("nothing owed", "nothing owed by the record"
                                    + ("; the item itself is read next" if write and (replace or restore)
                                       else "")))
            if not write:
                o.outcome = "unchanged" if due == "unchanged" else (
                    "would publish" if due == "create" else "would update")
                o.lines.append("a dry run: signed in nowhere, wrote nothing; the item "
                               "itself is checked when the door writes")
                continue
            if due == "unchanged" and not (replace or restore):
                o.outcome = "unchanged"
                continue
            session = _session(sessions, kind, target, ask)
            prior = entry
            live = None if entry is None else _check_places_live(
                kind, session, target, entry, replace,
                built if due in ("reseen", "share") else None, restore=restore)
            if live == "create":
                due = "create"
                o.lines.append(f"item {entry['item_id']} is gone; making a new one (--replace)")
            elif live == "restore":
                due = "move"
                o.lines.append(f"item {entry['item_id']} was changed by hand; the door's whole map "
                               f"is written back into the same item (--restore, D-395)")
            elif due == "unchanged":
                o.outcome = "unchanged"
                o.lines.append(f"item {entry['item_id']} stands as recorded; nothing written")
                continue
            if due == "create":
                item_id = kind.create(session, target, built)
                provisional = _places_entry(places, target, built, item_id, records, by,
                                            reason, prior, None, when)
                provisional["sharing"] = None
                record["targets"].setdefault(tid, {})[PLACES_KEY] = provisional
                write_record(plot_dir, record)
                kind.share(session, target, item_id)
                o.outcome = "published"
            else:
                item_id = entry["item_id"]
                if due == "move":
                    kind.update(session, target, item_id, built, data=built.data)
                elif due == "describe":
                    kind.update(session, target, item_id, built, data=None)
                if due != "reseen":
                    kind.share(session, target, item_id)
                o.outcome = "updated"
            seen = _seen(kind, session, item_id)
            stored = kind.read(session, item_id)
            from canopy.expose.targets.arcgis_places import map_sha256
            same = stored is not None and map_sha256(stored["data"]) == built.extra["map_sha256"]
            o.lines.append("the stored map hashes SAME as sent" if same else
                           "the stored map DIFFERS from what was sent: the record keeps what "
                           "was sent, and --check will say so until it is read")
            rest = kind.rest_version(session) if hasattr(kind, "rest_version") else None
            final = _places_entry(places, target, built, item_id, records, by, reason, prior,
                                  rest, when)
            final["description_seen_sha256"] = seen
            record["targets"].setdefault(tid, {})[PLACES_KEY] = final
            write_record(plot_dir, record)
            o.lines.append(f"item {item_id}: {target.portal}/home/item.html?id={item_id}")
        except PublishRefusal as e:
            o.outcome = "refused"
            o.lines.append(f"refused: {e.reason}")
            o.lines.append(f"  would admit it: {e.would_admit}")
        except Exception as e:                       # one target's failure never stops another
            o.outcome = "failed"
            said = (str(e).splitlines() or [""])[0][:300]
            o.lines.append(f"failed: {type(e).__name__}: {said}")
    return out


def _places_entry(places, target, built, item_id, records, by, reason, prior, rest_version,
                  now) -> dict:
    first = records[0] if records else {}
    return {
        "kind": MADE_PLACES, "portal": target.portal, "owner": target.owner,
        "folder": target.folder, "item_id": item_id, "title": built.title,
        "map_sha256": built.extra["map_sha256"],
        "parents": _parents(places),
        "refusals_sha256": places["told"]["refusals_sha256"],
        "counts": {lv: line["placed"] for lv, line in built.extra["report"]["levels"].items()},
        "description_sha256": sha256_text(built.description),
        "sharing": target.sharing, "groups": list(target.groups),
        "gate": {"decision": "allow", "target": target.id,
                 "sharing_level": first.get("sharing_level"),
                 "gate_version": first.get("gate_version"),
                 "context_notes": sorted({n for r in records
                                          for n in (r.get("context_text") or {})})},
        "door_version": VERSION, "rest_version": rest_version,
        "moved_at": now, "moved_by": by, "reason": reason,
        "previous": ({"map_sha256": prior.get("map_sha256"), "parents": prior.get("parents")}
                     if prior else None),
    }


# --- the lenses (zip 9b2, D-385) ----------------------------------------------

def publish_lens(plot: str, lane: str, target_ids: list[str], *, root: Path, write: bool = False,
                 by: str | None = None, reason: str | None = None, replace: bool = False,
                 domain: str | None = None, fetch=default_fetch, judge=default_judge,
                 kinds: dict | None = None, ask=None, now: str | None = None,
                 restore: bool = False) -> list[Outcome]:
    """one lane's lens, for the named targets. a dry run unless write. a lens
    with any copy still to draw is named, and never written (LENS-1). with
    replace or restore, the item itself is read even when nothing is owed."""
    from canopy.expose.lenses import describe_members, lens_key, read_lens
    plot_dir = Path(root) / "plots" / plot
    kinds = kinds or registered(version=VERSION)
    targets = load_targets(plot_dir, kinds)
    unknown = [t for t in target_ids if t not in targets]
    if unknown:
        raise PublishRefusal(f"no target named {', '.join(unknown)} in this plot",
                             f"one of {', '.join(sorted(targets))}")
    domain = domain or os.environ.get(DOMAIN_ENV)
    if not domain:
        raise PublishRefusal(f"{DOMAIN_ENV} is not set, so the door cannot read the bucket",
                             "set it as the canonical command needs it")
    lens = read_lens(plot, lane, domain=domain, root=Path(root), fetch=fetch)
    from canopy.expose.records import load_licenses
    lens["licenses"] = load_licenses(Path(root) / "seeds" / "licenses")
    lens["credit"] = load_credit(plot_dir)
    key = lens_key(lane)
    when = now or datetime.now(timezone.utc).isoformat()
    record = read_record(plot_dir)
    sessions: dict = {}
    out: list[Outcome] = []
    for tid in target_ids:
        target = targets[tid]
        kind = kinds[target.kind]
        o = Outcome(tid, "refused")
        out.append(o)
        o.lines.append(f"{lens['name']} ({lens['kind']}), to {target.kind}, owned by "
                       f"{target.owner} at {target.portal}, {target.sharing}")
        try:
            for line in describe_members(lens):
                o.lines.append(f"member: {line}")
            for lv in lens["levels"]:
                o.lines.append(f"{lv['label']}: " + ", ".join(c["indicator"] for c in lv["layers"]))
            for ind in lens["counts"]:
                o.lines.append(f"not drawn: {ind} is a count, kept in the profile (D-385)")
            if lens["orientation"] is not None:
                o.lines.append("no measure of this lane is drawn at any level: the lens holds "
                               "the orientation copy and says so")
            for m in lens["missing"]:
                o.lines.append(f"still to draw: {m}")
            if lens["missing"]:
                raise PublishRefusal(
                    f"{len(lens['missing'])} of the plan's copies are not drawn yet, and a lens "
                    f"is written only when every table is drawn (LENS-1)",
                    "run each command named above, then publish the lens")
            records = [judge_at(judge, c, target, plot_dir) for c in lens["judged"]]
            notes = sorted({n for r in records for n in (r.get("context_text") or {})})
            o.lines.append(f"gate: every layer may leave at {target.sharing}"
                           + (f"; carries {', '.join(notes)}" if notes else "; no notes bind it"))
            entry = (record["targets"].get(tid) or {}).get(key)
            _kind_of(entry, MADE_LENS)
            if entry and (entry.get("portal") != target.portal or entry.get("owner") != target.owner):
                raise PublishRefusal(f"the record's item lives at {entry.get('portal')} as "
                                     f"{entry.get('owner')}, not as this target declares",
                                     "ownership moves in ArcGIS, by a person; then the record")
            built = kind.build_lens(target, lens)
            size = len(json.dumps(built.data).encode("utf-8"))
            o.lines.append(f"the map: {size:,} bytes, sha256 {built.extra['map_sha256'][:12]}; "
                           f"its layers read their copies by URL")
            due = owed_places(entry, lens, built, target)
            o.lines.append(_SAY_PLACES[due].format(folder=target.folder, sharing=target.sharing)
                           .replace("places map", "lens")
                           .replace("nothing owed", "nothing owed by the record"
                                    + ("; the item itself is read next" if write and (replace or restore)
                                       else "")))
            if not write:
                o.outcome = "unchanged" if due == "unchanged" else (
                    "would publish" if due == "create" else "would update")
                o.lines.append("a dry run: signed in nowhere, wrote nothing; the item "
                               "itself is checked when the door writes")
                continue
            if due == "unchanged" and not (replace or restore):
                o.outcome = "unchanged"
                continue
            session = _session(sessions, kind, target, ask)
            prior = entry
            live = None if entry is None else _check_places_live(
                kind, session, target, entry, replace,
                built if due in ("reseen", "share") else None, what="lens", restore=restore)
            if live == "create":
                due = "create"
                o.lines.append(f"item {entry['item_id']} is gone; making a new one (--replace)")
            elif live == "restore":
                due = "move"
                o.lines.append(f"item {entry['item_id']} was changed by hand; the door's whole lens "
                               f"is written back into the same item (--restore, D-395)")
            elif due == "unchanged":
                o.outcome = "unchanged"
                o.lines.append(f"item {entry['item_id']} stands as recorded; nothing written")
                continue
            if due == "create":
                item_id = kind.create(session, target, built)
                provisional = _lens_entry(lens, target, built, item_id, records, by, reason,
                                          prior, None, when)
                provisional["sharing"] = None
                record["targets"].setdefault(tid, {})[key] = provisional
                write_record(plot_dir, record)
                kind.share(session, target, item_id)
                o.outcome = "published"
            else:
                item_id = entry["item_id"]
                if due == "move":
                    kind.update(session, target, item_id, built, data=built.data)
                elif due == "describe":
                    kind.update(session, target, item_id, built, data=None)
                if due != "reseen":
                    kind.share(session, target, item_id)
                o.outcome = "updated"
            seen = _seen(kind, session, item_id)
            stored = kind.read(session, item_id)
            from canopy.expose.targets.arcgis_places import map_sha256
            same = stored is not None and map_sha256(stored["data"]) == built.extra["map_sha256"]
            o.lines.append("the stored map hashes SAME as sent" if same else
                           "the stored map DIFFERS from what was sent: the record keeps what "
                           "was sent, and --check will say so until it is read")
            rest = kind.rest_version(session) if hasattr(kind, "rest_version") else None
            final = _lens_entry(lens, target, built, item_id, records, by, reason, prior,
                                rest, when)
            final["description_seen_sha256"] = seen
            record["targets"].setdefault(tid, {})[key] = final
            write_record(plot_dir, record)
            o.lines.append(f"item {item_id}: {target.portal}/home/item.html?id={item_id}")
        except PublishRefusal as e:
            o.outcome = "refused"
            o.lines.append(f"refused: {e.reason}")
            o.lines.append(f"  would admit it: {e.would_admit}")
        except Exception as e:                       # one target's failure never stops another
            o.outcome = "failed"
            said = (str(e).splitlines() or [""])[0][:300]
            o.lines.append(f"failed: {type(e).__name__}: {said}")
    return out


def _lens_entry(lens, target, built, item_id, records, by, reason, prior, rest_version,
                now) -> dict:
    first = records[0] if records else {}
    return {
        "kind": MADE_LENS, "portal": target.portal, "owner": target.owner,
        "folder": target.folder, "item_id": item_id, "title": built.title, "lane": lens["lane"],
        "map_sha256": built.extra["map_sha256"],
        "parents": _parents(lens),
        "layers": built.extra["report"]["levels"], "empty": built.extra["report"]["empty"],
        "description_sha256": sha256_text(built.description),
        "sharing": target.sharing, "groups": list(target.groups),
        "gate": {"decision": "allow", "target": target.id,
                 "sharing_level": first.get("sharing_level"),
                 "gate_version": first.get("gate_version"),
                 "context_notes": sorted({n for r in records
                                          for n in (r.get("context_text") or {})})},
        "door_version": VERSION, "rest_version": rest_version,
        "moved_at": now, "moved_by": by, "reason": reason,
        "previous": ({"map_sha256": prior.get("map_sha256"), "parents": prior.get("parents")}
                     if prior else None),
    }


# --- adopting the app (zip 9b2, D-366) ----------------------------------------

APP_KEY = "app"
APP_TYPE = "Web Experience"
REHEARSALS_FILE = "rehearsals.yml"


def config_sha256(config: dict) -> str:
    """the one hash of an app's published config: keys sorted, no spaces."""
    return sha256_text(json.dumps(config, sort_keys=True, separators=(",", ":")))


def item_ids_in(doc) -> list[str]:
    """every item id an app's config names (its data sources, its maps), in order."""
    found: list[str] = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "itemId" and isinstance(v, str) and v not in found:
                    found.append(v)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(doc)
    return found


def _rehearsals(plot_dir: Path) -> dict:
    path = Path(plot_dir) / "publish" / REHEARSALS_FILE
    if not path.is_file():
        return {}
    return (yaml.safe_load(path.read_text()) or {}).get("never_adopt") or {}


def _judge_app(app: dict | None, item_id: str, target, plot_dir: Path, record: dict) -> list[str]:
    """the refusals D-366 names, then what the app reads that the door did not make."""
    if item_id in _rehearsals(plot_dir):
        raise PublishRefusal(f"item {item_id} is a rehearsal ({_rehearsals(plot_dir)[item_id]}), "
                             f"never the explorer", "adopt the app built for the explorer")
    if app is None:
        raise PublishRefusal(f"item {item_id} is not in {target.portal}, or this account "
                             f"cannot read it", "check the id in the app's address")
    if app.get("type") != APP_TYPE:
        raise PublishRefusal(f"item {item_id} is a {app.get('type')}, not an Experience "
                             f"Builder app", "adopt the app, not one of its maps")
    if app.get("owner") != target.owner:
        raise PublishRefusal(f"the app is owned by {app.get('owner')}, not {target.owner}",
                             "ownership moves in ArcGIS, by a person (R7)")
    if app.get("folder") != target.folder:
        raise PublishRefusal(f"the app sits in folder {app.get('folder')!r}, not the target's "
                             f"{target.folder!r}", "move it into the target's folder in ArcGIS")
    if app.get("config") is None:
        raise PublishRefusal("the app has never been published, so it has no config to record",
                             "publish it in Experience Builder, then adopt it")
    ours = {e.get("item_id") for entries in (record.get("targets") or {}).values()
            for e in (entries or {}).values()}
    return [i for i in item_ids_in(app["config"]) if i not in ours]


def adopt_app(plot: str, item_id: str, target_id: str, *, root: Path, write: bool = False,
              by: str | None = None, reason: str | None = None, kinds: dict | None = None,
              ask=None, now: str | None = None) -> Outcome:
    """record the hand-built Experience Builder app under the target's key `app`.
    it reads the app, so it signs in; it records only with write."""
    plot_dir = Path(root) / "plots" / plot
    kinds = kinds or registered(version=VERSION)
    targets = load_targets(plot_dir, kinds)
    if target_id not in targets:
        raise PublishRefusal(f"no target named {target_id} in this plot",
                             f"one of {', '.join(sorted(targets))}")
    target = targets[target_id]
    kind = kinds[target.kind]
    o = Outcome(target_id, "refused")
    record = read_record(plot_dir)
    try:
        if item_id in _rehearsals(plot_dir):
            _judge_app(None, item_id, target, plot_dir, record)
        session = _session({}, kind, target, ask)
        app = kind.read_app(session, item_id)
        foreign = _judge_app(app, item_id, target, plot_dir, record)
        sha = config_sha256(app["config"])
        reads = item_ids_in(app["config"])
        o.lines.append(f"app {item_id} ({app.get('title')}), owned by {app['owner']} in "
                       f"{app['folder']}, shared '{app.get('access')}'")
        o.lines.append(f"its published config hashes to {sha[:12]}; it reads {len(reads)} "
                       f"item(s)")
        for i in foreign:
            o.lines.append(f"warning: it reads item {i}, which the door did not make: a "
                           f"layer there is not checked by the gate at this door")
        if app.get("access") != _access_of(target.sharing):
            o.lines.append(f"warning: it is shared '{app.get('access')}', the target says "
                           f"{target.sharing}; share it in ArcGIS, then --check")
        entry = (record["targets"].get(target_id) or {}).get(APP_KEY)
        _kind_of(entry, MADE_APP)
        if not write:
            o.outcome = "would publish" if entry is None else "would update"
            o.lines.append("read only: the record is written with --write")
            return o
        record["targets"].setdefault(target_id, {})[APP_KEY] = {
            "kind": MADE_APP, "portal": target.portal, "owner": target.owner,
            "folder": target.folder, "item_id": item_id, "title": app.get("title"),
            "config_sha256": sha, "reads": reads, "foreign": foreign,
            "sharing": target.sharing, "groups": list(target.groups),
            "door_version": VERSION, "moved_at": now or datetime.now(timezone.utc).isoformat(),
            "moved_by": by, "reason": reason,
            "previous": ({"item_id": entry.get("item_id"), "config_sha256": entry.get("config_sha256")}
                         if entry else None)}
        write_record(plot_dir, record)
        o.outcome = "published" if entry is None else "updated"
        o.lines.append(f"recorded as {target_id} {APP_KEY}")
    except PublishRefusal as e:
        o.outcome = "refused"
        o.lines.append(f"refused: {e.reason}")
        o.lines.append(f"  would admit it: {e.would_admit}")
    return o


def _check_app(kind, session, target, entry: dict, o) -> None:
    """an adopted app, read again: its published config by hash, its owner, its
    folder and its sharing against the target's (D-366)."""
    app = kind.read_app(session, entry["item_id"])
    found = []
    if app is None:
        found.append(f"app {entry['item_id']} is gone, or this account cannot read it")
    else:
        if app.get("owner") != target.owner:
            found.append(f"owned by {app.get('owner')}, not {target.owner}")
        if app.get("folder") != target.folder:
            found.append(f"in folder {app.get('folder')!r}, not {target.folder!r}")
        if app.get("config") is None:
            found.append("it has no published config")
        elif config_sha256(app["config"]) != entry.get("config_sha256"):
            found.append(f"its published config hashes to {config_sha256(app['config'])[:12]}, "
                         f"not the recorded {str(entry.get('config_sha256'))[:12]}: it was "
                         f"published again since it was adopted; read it, then adopt it again")
        if app.get("access") != _access_of(target.sharing):
            found.append(f"it is shared '{app.get('access')}', the target says {target.sharing}")
    if found:
        o.lines.extend(found)
    else:
        o.outcome = "as recorded"
        o.lines.append(f"app {entry['item_id']} is as adopted")
