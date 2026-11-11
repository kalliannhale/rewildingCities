"""
canopy/expose/records.py

what the gate reads besides the artifact: a plot's consent records (one file
each in plots/<plot>/consent/, D-115), the controlled license list
(seeds/licenses/, D-116) and the context notes (seeds/notes/, D-157). all are
loaded loudly: a malformed record is an error, never a record that quietly
admits nothing or everything.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from .gate import SHARING_LEVELS

CONSENT_REQUIRED = ("id", "plot", "target", "sharing_level", "covers",
                    "granted_by", "on_behalf_of", "granted_on", "terms", "status")
STATUSES = ("active", "withdrawn")
NOTE_FIELDS = ("text", "when_merged")


def load_licenses(licenses_dir: str | Path) -> dict[str, dict]:
    path = Path(licenses_dir) / "licenses.yml"
    doc = yaml.safe_load(path.read_text()) or {}
    terms = doc.get("terms") or {}
    for tid, t in terms.items():
        bad = [lv for lv in t.get("permits") or [] if lv not in SHARING_LEVELS]
        if bad or not t.get("permits"):
            raise ValueError(f"license term '{tid}': permits must list sharing levels "
                             f"from {', '.join(SHARING_LEVELS)}; got {t.get('permits')}")
        if not t.get("verified") and set(t["permits"]) - {"private"}:
            raise ValueError(f"license term '{tid}' is unverified, so it may permit "
                             f"private only, never {t['permits']}")
    return terms


def load_consents(plot_dir: str | Path) -> list[dict]:
    folder = Path(plot_dir) / "consent"
    records = []
    for f in sorted(folder.glob("*.yml")) if folder.is_dir() else []:
        r = yaml.safe_load(f.read_text()) or {}
        where = f"{folder.name}/{f.name}"
        missing = [k for k in CONSENT_REQUIRED if r.get(k) in (None, "", [])]
        if missing:
            raise ValueError(f"consent record {where} is missing: {', '.join(missing)}")
        if r["status"] not in STATUSES:
            raise ValueError(f"consent record {where}: status must be active or withdrawn")
        if r["sharing_level"] not in SHARING_LEVELS:
            raise ValueError(f"consent record {where}: unknown sharing level "
                             f"'{r['sharing_level']}'")
        for k in ("granted_on", "expires_on", "withdrawn_on"):
            if isinstance(r.get(k), str):
                r[k] = date.fromisoformat(r[k])
        records.append(dict(r, file=where))
    return records


class _UniqueKeyLoader(yaml.SafeLoader):
    """safe_load keeps the last of two equal keys and says nothing. a note id
    declared twice would then have two texts with no trace, so this refuses."""


def _mapping_without_duplicates(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise ValueError(f"'{key}' is declared twice")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                                 _mapping_without_duplicates)


def load_notes(notes_dir: str | Path) -> dict[str, dict]:
    """every context note: id -> {text, when_merged}. the one home of a note's
    text (D-157). refuses an id declared twice, a note without text, a field
    it does not know, and a when_merged that names no note or itself."""
    path = Path(notes_dir) / "notes.yml"
    try:
        doc = yaml.load(path.read_text(), Loader=_UniqueKeyLoader) or {}
    except ValueError as e:
        raise ValueError(f"{path.name}: {e}") from None
    notes = doc.get("notes") or {}
    if not notes:
        raise ValueError(f"{path.name} declares no notes")
    for nid, spec in notes.items():
        spec = spec or {}
        unknown = sorted(set(spec) - set(NOTE_FIELDS))
        if unknown:
            raise ValueError(f"note '{nid}': unknown field(s) {', '.join(unknown)}; "
                             f"a note has {', '.join(NOTE_FIELDS)}")
        if not isinstance(spec.get("text"), str) or not spec["text"].strip():
            raise ValueError(f"note '{nid}' has no text, so it cannot travel (rule 9)")
        merged = spec.get("when_merged")
        if merged is not None and (merged == nid or merged not in notes):
            raise ValueError(f"note '{nid}': when_merged names '{merged}', which is "
                             f"{'itself' if merged == nid else 'not a note'}")
        notes[nid] = {"text": spec["text"].strip(), "when_merged": merged}
    return notes


def check_required_notes(vocabulary, notes: dict) -> None:
    """every note a type requires has its text in the notes file, and no type
    carries a text of its own: one id, one text, one home (D-149, D-157).
    run when the gate's context is loaded, so a broken declaration stops
    every exit at once, not one artifact at a time."""
    for name in vocabulary.all_types():
        for note in vocabulary.get(name).extra.get("required_context") or []:
            nid = (note or {}).get("id")
            if not nid or nid not in notes:
                raise ValueError(f"semantic type '{name}' requires the note '{nid}', "
                                 f"which is not in seeds/notes/notes.yml")
            if "text" in note:
                raise ValueError(f"semantic type '{name}' carries a text for '{nid}'; "
                                 f"a note's text lives only in seeds/notes/notes.yml")
