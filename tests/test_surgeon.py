"""
tests/test_surgeon.py

durable invariants for surgical manifest edits: every edit lands inside the
dataset it names, and an edit that cannot be verified is refused.
"""

import yaml
import pytest

from canopy.manifest.surgeon import ManifestSurgeon

MANIFEST = """\
city_id: test
datasets:
  first:
    available: false
    description: >
      Prose that mentions fetched_at: and available: in passing.
    semantic_type: indicator_source
    source:
      type: local
      path: elsewhere/source.csv
    cache:
      path: .data/first.parquet
      refresh_policy: manual

  second:
    available: false
    semantic_type: indicator_source
    cache:
      path: .data/second.parquet
      fetched_at: '2026-01-01T00:00:00+00:00'

notes:
  fetched_at: not a dataset field
"""


@pytest.fixture
def surgeon(tmp_path):
    p = tmp_path / "manifest.yml"
    p.write_text(MANIFEST)
    return ManifestSurgeon(p)


def _ds(text, name):
    return yaml.safe_load(text)["datasets"][name]


def test_missing_field_is_inserted_in_its_own_block_not_the_next(surgeon):
    text, ok = surgeon.set_field(MANIFEST, "first", "fetched_at", "'2026-10-06T00:00:00+00:00'")
    assert ok
    assert _ds(text, "first")["cache"]["fetched_at"] == "2026-10-06T00:00:00+00:00"
    assert _ds(text, "second")["cache"]["fetched_at"] == "2026-01-01T00:00:00+00:00"


def test_existing_field_is_replaced_in_place(surgeon):
    text, ok = surgeon.set_field(MANIFEST, "second", "available", "true")
    assert ok
    assert _ds(text, "second")["available"] is True
    assert _ds(text, "first")["available"] is False


def test_prose_mentioning_a_field_is_never_edited(surgeon):
    text, ok = surgeon.set_field(MANIFEST, "first", "available", "true")
    assert ok
    assert "mentions fetched_at: and available: in passing" in text
    assert _ds(text, "first")["available"] is True


def test_cache_path_is_not_confused_with_source_path(surgeon):
    text, ok = surgeon.set_field(MANIFEST, "first", "path", ".data/moved.parquet")
    assert ok
    assert _ds(text, "first")["cache"]["path"] == ".data/moved.parquet"
    assert _ds(text, "first")["source"]["path"] == "elsewhere/source.csv"


def test_block_scalar_is_refused(surgeon):
    text, ok = surgeon.set_field(MANIFEST, "first", "description", "short")
    assert not ok
    assert text == MANIFEST


def test_last_dataset_block_stops_at_a_new_top_level_section(surgeon):
    text, ok = surgeon.set_field(MANIFEST, "second", "available", "true")
    assert ok
    assert yaml.safe_load(text)["notes"]["fetched_at"] == "not a dataset field"


def test_unknown_dataset_is_refused(surgeon):
    text, ok = surgeon.set_field(MANIFEST, "nope", "available", "true")
    assert not ok
    assert text == MANIFEST


def test_backslashes_in_a_value_are_written_literally(surgeon):
    text, ok = surgeon.set_field(MANIFEST, "first", "path", r"'C:\data\first.parquet'")
    assert ok
    assert _ds(text, "first")["cache"]["path"] == r"C:\data\first.parquet"
