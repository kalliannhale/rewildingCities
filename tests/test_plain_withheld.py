"""
tests/test_plain_withheld.py ~ the withheld field in plain words (PLAINWORDS-1, zip 9b2)

the state's withheld field names each kind of data the map holds back. its
words come from seeds/language/plain_language.yml's `kinds`, held to the same
register as every told sentence: no working id, no claim word, under the
grade ceiling. a kind the register does not name falls back to its type with
the underscores taken out, so a dry run's sentence shows which still needs
words. the labels are short, since the places map has little headroom (LIMIT-1). ~
"""

from __future__ import annotations

import re
from pathlib import Path

from canopy.wonder.telling import Language, TellingContext, reading_grade, tell_withheld

REPO = Path(__file__).resolve().parents[1]


def _ctx():
    return TellingContext(names={}, county_of={}, notes={}, language=Language.load(REPO))


def test_every_label_keeps_the_register():
    lang = Language.load(REPO)
    assert lang.kinds, "plain_language.yml names no kinds"
    for st, words in lang.kinds.items():
        assert not lang.working_ids.search(words), (st, words)
        assert not set(re.findall(r"[a-z']+", words.lower())) & set(lang.claim_words), st
        assert "_" not in words and reading_grade(words + ".") <= lang.ceiling + 3, st


def test_the_labels_stay_short():
    lang = Language.load(REPO)
    assert all(len(w) <= 90 for w in lang.kinds.values())
    assert sum(len(w) for w in lang.kinds.values()) < 400


def test_a_named_kind_is_told_in_its_words_and_another_by_its_type():
    record = {"withheld": [
        {"semantic_type": "news_outlet", "refusals": [{"rule": 5}]},
        {"semantic_type": "something_new", "refusals": [{"rule": 9}]}]}
    said = tell_withheld(record, _ctx())
    assert "News outlets, by name and place:" in said
    assert "Something new:" in said and "news_outlet" not in said
    assert said.startswith("This tool holds 2 kinds of data")
