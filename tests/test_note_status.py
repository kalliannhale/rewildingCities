"""
tests/test_note_status.py ~ a note says whether its wording is a draft (Sprint 09)

TRIBE-7: the Wabanaki notes show as drafts until they are settled. a draft
was marked only by a comment, which nothing reads, so a note now carries
`status: draft`, and the telling says "Draft wording" before its text. ~
"""

from __future__ import annotations

from pathlib import Path

import pytest

from canopy.expose.records import NOTE_STATUSES, load_notes

REPO = Path(__file__).resolve().parents[1]


def test_every_note_has_a_status_and_the_wabanaki_drafts_say_so():
    notes = load_notes(REPO / "seeds" / "notes")
    assert all(n["status"] in NOTE_STATUSES for n in notes.values())
    for nid in ("contains_census_tribal_area", "penobscot_main_stem_waters",
                "carrier_unseen_on_nations_land", "carrier_seen_on_nations_land",
                "tribal_representation_legislature"):
        assert notes[nid]["status"] == "draft", nid


def test_the_representation_note_names_all_four_nations():
    text = load_notes(REPO / "seeds" / "notes")["tribal_representation_legislature"]["text"]
    for nation in ("Passamaquoddy Tribe", "Houlton Band of Maliseet Indians",
                   "Penobscot Nation", "Mi'kmaq Nation"):
        assert nation in text
    assert "133rd Legislature" in text and "not on the House or Senate floor" in text


def test_a_note_with_no_status_is_reviewed_and_an_unknown_status_is_refused(tmp_path):
    (tmp_path / "notes.yml").write_text("notes:\n  a:\n    text: plain words\n")
    assert load_notes(tmp_path)["a"]["status"] == "reviewed"
    (tmp_path / "notes.yml").write_text("notes:\n  a:\n    text: plain words\n    status: final\n")
    with pytest.raises(ValueError, match="status 'final'"):
        load_notes(tmp_path)
