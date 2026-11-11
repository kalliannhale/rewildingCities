"""
canopy/expose/check.py

the gate, given a plot. loads what decide() needs from the garden (the
vocabulary, the plot's manifest datasets, its consent records, the license
list, the context notes) so every exit asks the same question the same way:

  check_envelope(envelope, plot=..., target=..., sharing_level=...)
  read_exposure(plot)   every receipt in the plot, judged at `public`

read_exposure is what PlotReading.exposure carries and `wonder` shows: what
this plot holds that may leave, and for what is withheld, why, and what
would admit it (Contract 1, rules 7 and 8). ~
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from .gate import decide
from .records import check_required_notes, load_consents, load_licenses, load_notes


def _root() -> Path:
    from canopy.paths import project_root
    return project_root()


def _context(plot_dir: Path, seeds_root: Path):
    """the vocabulary, license list and notes come from the garden's seeds;
    the datasets and consent records from the plot. a plot without a manifest
    names no datasets, so rule 10 can only pass at private. a type requiring
    a note with no text stops here, before any receipt is judged (D-157)."""
    from canopy.vocabulary import Vocabulary
    vocab = Vocabulary.load(seeds_root / "seeds" / "schemas")
    notes = load_notes(seeds_root / "seeds" / "notes")
    check_required_notes(vocab, notes)
    manifest_path = plot_dir / "manifest.yml"
    manifest = (yaml.safe_load(manifest_path.read_text()) or {}) if manifest_path.is_file() else {}
    return (vocab, manifest.get("datasets") or {}, load_consents(plot_dir),
            load_licenses(seeds_root / "seeds" / "licenses"), notes)


def check_envelope(envelope: dict, *, plot: str, target: str, sharing_level: str,
                   plot_dir: str | Path | None = None) -> dict:
    seeds = _root()
    pdir = Path(plot_dir) if plot_dir else seeds / "plots" / plot
    vocab, datasets, consents, licenses, notes = _context(pdir, seeds)
    return decide(envelope, target=target, sharing_level=sharing_level,
                  vocabulary=vocab, plot=plot, manifest_datasets=datasets,
                  licenses=licenses, notes=notes, consents=consents)


def read_exposure(plot: str, *, root: str | Path | None = None,
                  sharing_level: str = "public", target: str = "public") -> list[dict]:
    """one entry per receipt: may it leave at this level, and if not, why."""
    base = Path(root) if root else _root()
    envelopes = base / "plots" / plot / ".envelopes"
    if not envelopes.is_dir():
        return []
    vocab, datasets, consents, licenses, notes = _context(base / "plots" / plot, base)
    out = []
    for p in sorted(envelopes.glob("*.envelope.json")):
        try:
            env = json.loads(p.read_text())
        except (OSError, ValueError):
            out.append({"artifact": p.name[:-len(".envelope.json")], "semantic_type": None,
                        "may_leave": False, "withheld": [{"rule": None,
                        "reason": "the receipt could not be read", "would_admit": "re-run it"}],
                        "caveats": []})
            continue
        try:
            res = decide(env, target=target, sharing_level=sharing_level, vocabulary=vocab,
                         plot=plot, manifest_datasets=datasets, licenses=licenses,
                         notes=notes, consents=consents)
        except ValueError as e:          # rule 1: a declaration error, said plainly
            res = {"decision": "refuse", "refusals": [
                {"rule": 1, "reason": str(e), "would_admit": "correct the declaration"}]}
        out.append({
            "artifact": p.name[:-len(".envelope.json")],
            "semantic_type": (env.get("metadata") or {}).get("semantic_type"),
            "may_leave": res["decision"] == "allow",
            "withheld": [{"rule": r.get("rule"), "reason": r.get("reason"),
                          "would_admit": r.get("would_admit")}
                         for r in res.get("refusals", [])],
            "caveats": (res.get("record") or {}).get("caveats", []),
        })
    return out
