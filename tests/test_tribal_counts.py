"""a Census tribal area is counted only beside its note (D-233): every
count_located step in every plot that counts the tribal level names a
tribal_note, and that note's words live in seeds/notes/notes.yml, marked a
draft until the nations' terms settle them (P-8)."""

from pathlib import Path

import yaml

from canopy.expose.records import load_notes

ROOT = Path(__file__).resolve().parents[1]


def _count_steps():
    for path in sorted((ROOT / "plots").glob("**/*.yml")):
        doc = yaml.safe_load(path.read_text()) or {}
        if not isinstance(doc, dict):
            continue
        for step in doc.get("steps") or []:
            if isinstance(step, dict) and step.get("primitive") == "soil/count_located":
                yield path.relative_to(ROOT), step.get("params") or {}


def test_every_tribal_count_names_a_note_that_exists():
    notes = load_notes(ROOT / "seeds" / "notes")
    tribal = [(p, s) for p, s in _count_steps() if "aiannh" in (s.get("levels") or [])]
    assert tribal, "no plot counts a tribal area"
    for path, params in tribal:
        assert params.get("tribal_note") in notes, (str(path), params.get("tribal_note"))


def test_no_count_names_a_note_without_the_tribal_level():
    for path, params in _count_steps():
        if params.get("tribal_note"):
            assert "aiannh" in (params.get("levels") or []), str(path)


def test_the_three_carriers_each_say_what_their_source_sees():
    prep = ROOT / "plots" / "maine" / "preparations"
    want = {"maine_libraries.yml": "carrier_unseen_on_nations_land",
            "maine_schools.yml": "carrier_seen_on_nations_land",
            "maine_health_centers.yml": "carrier_unseen_on_nations_land"}
    for name, note in want.items():
        steps = yaml.safe_load((prep / name).read_text())["steps"]
        (count,) = [s for s in steps if s["primitive"] == "soil/count_located"]
        assert count["params"]["tribal_note"] == note, name
