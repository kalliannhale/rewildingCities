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
owes, the same way `current` knows what is current (O-4, D-327, D-328). ~
"""

from __future__ import annotations

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
            "refused", "failed")


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
            "after zip 8b: draw a choropleth copy, canonical <plot> <table> --display "
            "--join <outline>, then publish that")
    kinds = meta.get("geometry_type")
    kinds = set(kinds if isinstance(kinds, list) else [kinds])
    if kinds <= {"Point", "MultiPoint"}:
        return display.display_name("points", display.DEFAULT_TOLERANCE_M)
    return display.display_name("polygons", display.DEFAULT_TOLERANCE_M)


def read_copy(plot: str, artifact: str, *, domain: str, fetch=default_fetch,
              display: str | None = None) -> dict:
    """everything the door shows, read from the bucket through CloudFront and
    checked against itself: the pointer, the allow record it names, the
    version's receipt, the display copy and its envelope."""
    from canopy.aws import s3
    s3.validate_plot(plot)
    s3.validate_artifact(artifact)
    base = f"https://{domain}"
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
        raise PublishRefusal(f"version {sha[:12]} is not whole behind CloudFront",
                             "read the bucket before anything else")
    name = display or _display_name(receipt)
    keys = s3.display_keys(plot, artifact, sha, name)
    display_env = _json(fetch, f"{base}/{keys['envelope']}")
    if display_env is None:
        raise PublishRefusal(f"version {sha[:12]} has no display copy '{name}'",
                             f"draw it: canonical {plot} {artifact} --display --write")
    if (display_env.get("metadata") or {}).get("derived_from") != sha:
        raise PublishRefusal(f"the display copy '{name}' names another version",
                             "read the bucket before anything else")
    raw = fetch(f"{base}/{keys['geojson']}")
    if raw is None:
        raise PublishRefusal(f"the display copy '{name}' has an envelope but no GeoJSON",
                             f"draw it again: canonical {plot} {artifact} --display --write")
    return {"plot": plot, "artifact": artifact, "sha256": sha, "allow": allow,
            "current": current, "allow_doc": allow_doc, "receipt": receipt,
            "display": name, "display_env": display_env, "geojson": json.loads(raw),
            "url": f"{base}/{keys['geojson']}", "version_url": f"{base}/{prefix}",
            "harvest_url": f"{base}/harvests/{plot}/{artifact}/versions/",
            "title": f"{artifact} ({plot})"}


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
    held = (copy["allow_doc"].get("gate") or {}).get("context_text") or {}
    for note, text in (record.get("context_text") or {}).items():
        if held.get(note) != text:
            raise PublishRefusal(
                f"note '{note}' reads differently in seeds/notes than in the canonical "
                f"allow record, so the map would say what the bucket does not",
                f"write the canonical version again, which moves its allow record "
                f"(D-320), then publish")
    return record


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
    if entry.get("sha256") != copy["sha256"]:
        return "move"
    if (entry.get("allow") != copy["allow"]
            or entry.get("description_sha256") != sha256_text(built.description)):
        return "describe"
    if entry.get("sharing") != target.sharing or list(entry.get("groups") or []) != list(target.groups):
        return "share"
    return "unchanged"


_SAY = {"create": "would create a web map in folder '{folder}'",
        "adopt": "would adopt item {adopt} and move its layer to this version",
        "move": "would move the layer from version {old} to {new}, and the description",
        "describe": "would rewrite the description alone (a new allow record or new words)",
        "share": "would share it at {sharing}",
        "unchanged": "nothing owed"}


def _check_live(kind, session, target, entry: dict, replace: bool) -> str | None:
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
    if sha256_text(state["description"]) != entry["description_sha256"]:
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
        "previous": ({"sha256": prior.get("sha256"), "allow": prior.get("allow")}
                     if prior else None),
    }


def publish(plot: str, artifact: str, target_ids: list[str], *, root: Path,
            write: bool = False, by: str | None = None, reason: str | None = None,
            adopt: str | None = None, replace: bool = False, display: str | None = None,
            domain: str | None = None, fetch=default_fetch, judge=default_judge,
            kinds: dict | None = None, ask=None, now: str | None = None) -> list[Outcome]:
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
    domain = domain or os.environ.get(DOMAIN_ENV)
    if not domain:
        raise PublishRefusal(f"{DOMAIN_ENV} is not set, so the door cannot read the bucket",
                             "set it as the canonical command needs it")
    copy = read_copy(plot, artifact, domain=domain, fetch=fetch, display=display)
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
            entry = (record["targets"].get(tid) or {}).get(artifact)
            if entry and (entry.get("portal") != target.portal or entry.get("owner") != target.owner):
                raise PublishRefusal(f"the record's item lives at {entry.get('portal')} as "
                                     f"{entry.get('owner')}, not as this target declares",
                                     "ownership moves in ArcGIS, by a person; then the record")
            built = kind.build(target, copy)
            due = owed(entry, copy, built, target, adopt)
            o.lines.append(_SAY[due].format(folder=target.folder, adopt=adopt,
                                            old=(entry or {}).get("sha256", "")[:12],
                                            new=copy["sha256"][:12], sharing=target.sharing))
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

            key = (target.portal, target.owner)
            if key not in sessions:
                password = (ask or _ask)(f"password for {target.owner} at {target.portal} "
                                         f"(typed, never stored): ")
                session = kind.sign_in(target, password)
                who = kind.whoami(session)
                if who != target.owner:
                    raise PublishRefusal(f"the portal says this sign-in is {who}, not "
                                         f"{target.owner}", "sign in as the target's owner (F4)")
                sessions[key] = session
            session = sessions[key]

            layer_id = built.layer_id
            if entry is not None:
                if _check_live(kind, session, target, entry, replace) == "create":
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
                record["targets"].setdefault(tid, {})[artifact] = provisional
                write_record(plot_dir, record)
                kind.share(session, target, item_id)
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
                o.outcome = "published"
            else:
                item_id = entry["item_id"]
                if due == "move":
                    state = kind.read(session, item_id)
                    kind.update(session, target, item_id, built,
                                data=kind.moved(state["data"], layer_id, built))
                elif due == "describe":
                    kind.update(session, target, item_id, built, data=None)
                kind.share(session, target, item_id)
                o.outcome = "updated"

            rest = kind.rest_version(session) if hasattr(kind, "rest_version") else None
            record["targets"].setdefault(tid, {})[artifact] = _entry(
                copy, target, built, item_id, layer_id, gate_record, by, reason,
                entry_prior, rest, when)
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


def _ask(prompt: str) -> str:
    import getpass
    return getpass.getpass(prompt)
