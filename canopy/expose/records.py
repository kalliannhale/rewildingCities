"""
canopy/expose/records.py

what the gate reads besides the artifact: a plot's consent records (one file
each in plots/<plot>/consent/, D-115) and the controlled license list
(seeds/licenses/, D-116). both are loaded loudly: a malformed record is an
error, never a record that quietly admits nothing or everything.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from .gate import SHARING_LEVELS

CONSENT_REQUIRED = ("id", "plot", "target", "sharing_level", "covers",
                    "granted_by", "on_behalf_of", "granted_on", "terms", "status")
STATUSES = ("active", "withdrawn")


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
