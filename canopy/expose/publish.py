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
when nothing is owed (DOORCHECK-1). ~
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
from canopy.expose.targets.arcgis_webmap import sha256_text

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


def _current(fetch, base: str, plot: str, artifact: str) -> dict:
    """a harvest's current version as CloudFront serves it: the pointer, the
    allow record it names and the version's receipt."""
    from canopy.aws import s3
    current = _json(fetch, f"{base}/{s3.pointer_key(plot, artifact)}")
    if current is None:
        raise PublishRefusal(f"'{artifact}' has no canonical version",
                             f"write it first: canonical {plot} {artifact} --write")
    if current.get("data") != "data.parquet":
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
        "kind": target.kind, "portal": target.portal, "owner": target.owner,
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
            session = sessions[account]

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
                if due == "move":
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
          ask=None) -> list[Outcome]:
    """every recorded item of the named targets (every target, when none is
    named) read as it stands and set beside the record. signs in, writes
    nothing, and moves nothing: `unchanged` means the record and the bucket
    agree, and this is how the item itself is seen agreeing (DOORCHECK-1)."""
    plot_dir = Path(root) / "plots" / plot
    kinds = kinds or registered(version=VERSION)
    targets = load_targets(plot_dir, kinds)
    unknown = [t for t in target_ids if t not in targets]
    if unknown:
        raise PublishRefusal(f"no target named {', '.join(unknown)} in this plot",
                             f"one of {', '.join(sorted(targets))}")
    record = read_record(plot_dir)
    sessions: dict = {}
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
                if entry.get("portal") != target.portal or entry.get("owner") != target.owner:
                    o.lines.append(f"the record's item lives at {entry.get('portal')} as "
                                   f"{entry.get('owner')}, not as the target declares")
                    continue
                skey = (target.portal, target.owner)
                if skey not in sessions:
                    password = (ask or _ask)(f"password for {target.owner} at {target.portal} "
                                             f"(typed, never stored): ")
                    session = kind.sign_in(target, password)
                    who = kind.whoami(session)
                    if who != target.owner:
                        raise PublishRefusal(f"the portal says this sign-in is {who}, not "
                                             f"{target.owner}", "sign in as the target's owner (F4)")
                    sessions[skey] = session
                session = sessions[skey]
                state = kind.read(session, entry["item_id"])
                found = []
                if state is None:
                    found.append(f"item {entry['item_id']} is gone; publish with --replace")
                else:
                    if state["owner"] != target.owner:
                        found.append(f"owned by {state['owner']}, not {target.owner}")
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
                    shared = _access_of(entry.get("sharing"))
                    if state.get("access") != shared:
                        found.append(f"it is shared '{state.get('access')}', the record says "
                                     f"{entry.get('sharing')}")
                    if (entry.get("renderer_sha256") and hasattr(kind, "renderer_sha256")
                            and kind.renderer_sha256(state["data"], entry["layer_id"])
                            != entry["renderer_sha256"]):
                        found.append("its renderer was restyled by hand; the next move puts "
                                     "the door's back")
                if found:
                    o.lines.extend(found)
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


def _access_of(sharing: str | None) -> str | None:
    """the portal's word for a sharing level, as an item reports its access."""
    return {"private": "private", "organization": "org", "public": "public"}.get(sharing or "")


def _ask(prompt: str) -> str:
    import getpass
    return getpass.getpass(prompt)
