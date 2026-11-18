"""
tests/test_standard_sources.py ~ what the standard says it will read (Sprint 09)

D-294 left Cision out of every count, so no measure may name it as a source
it will read. the Civic Information Index's published values are not in the
Maine plot (no receipt holds them), so they are acquirable, waiting on terms
of use (CII-19), never acquired. ~
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
STANDARD = REPO / "seeds" / "standards" / "information_barriers.yml"


def _measures():
    return yaml.safe_load(STANDARD.read_text())["measures"]


def test_no_measure_names_cision_as_a_source_it_will_read():
    for m_id, m in _measures().items():
        assert "cision" not in str(m.get("source") or "").lower(), m_id


def test_the_cii_published_values_wait_on_their_terms():
    for m_id in ("cii_pub_broadband", "cii_pub_literacy"):
        m = _measures()[m_id]
        assert m["status"] == "acquirable" and "terms of use" in m["needs"]
        assert m["source"]


def test_the_last_post_has_no_listed_source_left():
    assert _measures()["outlet_last_post"]["status"] == "needs_our_model"
