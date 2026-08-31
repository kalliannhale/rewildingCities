"""
canopy/loam/envelope_reader.py

envelope_reader ~ how rewilding tills what it has worked

an envelope is a receipt of what happened to one artifact. this reads that
receipt and settles the artifact into the loam as tended (or gathered),
resolving any retired name forward through the vocabulary so old work stays
answerable. it reads only; it never writes back to the envelope, never
invents a field it cannot find. ♡

what it derives, honestly, from your real envelope shape:
  ~ the name it was called (metadata.semantic_type), kept verbatim
  ~ what it means today (resolved through canonical.py)
  ~ its frame (metadata.crs) and where it came from (transform.source_crs)
  ~ its extent (metadata.bbox)
  ~ its lineage (the last provenance step's input, named as its own clump)
  ~ how loud its warnings were (count, and whether any were critical)

what the envelope does not yet carry, left null and honest until the
schema grows: coverage, an output content-hash (the path anchors the name
for now), and crosswalk lineage. ~

"""

from __future__ import annotations

import json
import os
from pathlib import Path

from loam import clump_name, TENDED, GATHERED, ConformanceError
from canonical import Vocabulary


def _norm(path: str | None) -> str | None:
    return os.path.normpath(path) if path else None


def _tier_of(canonical: str | None) -> str:
    """

    silver vs gold should be declared in the vocabulary seed (a `tier:`
    field on result types), never guessed here. until that seed field
    lands, every worked artifact settles as tended; adding `tier: gathered`
    to result types in seeds/schemas is the one honest way to raise gold. ~

    """
    return TENDED


def read_envelope(envelope_path: str, vocab: Vocabulary, plot: str) -> dict:
    """

    read one envelope receipt and derive the fields loam needs. ~

    """
    doc = json.loads(Path(envelope_path).read_text())
    data = doc.get("data") or {}
    meta = doc.get("metadata") or {}
    prov = doc.get("provenance") or []
    warns = doc.get("warnings") or []

    declared = meta.get("semantic_type")
    res = vocab.resolve(declared) if declared else None
    canonical = res.canonical if res else None

    transform = meta.get("transform") or {}
    bbox = meta.get("bbox")
    attrs = meta.get("attribute_fields") or []

    # the immediate parent ~ the last step's first input, named the way it
    # will be named when its own envelope is tilled (declared type + path).
    parent_ref = None
    if prov:
        inputs = (prov[-1] or {}).get("inputs") or []
        if inputs:
            p_declared = inputs[0].get("semantic_type")
            p_path = _norm(inputs[0].get("path"))
            if p_declared and p_path:
                parent_ref = clump_name(plot, p_declared, None, p_path)

    return {
        "plot": plot,
        "semantic_type": declared,
        "canonical": canonical,
        "data_path": _norm(data.get("path")),
        "fmt": data.get("format"),
        "crs": meta.get("crs"),
        "native_crs": transform.get("source_crs"),
        "bbox": tuple(bbox) if bbox else None,
        "spatial_ref": plot,
        "parent_ref": parent_ref,
        "id_field": "feature_id" if "feature_id" in attrs else None,
        "unit_key": None,
        "coverage": None,
        "content_hash": None,
        "receipt_path": _norm(envelope_path),
        "upstream_warnings": len(warns),
        "upstream_has_critical": any((w or {}).get("level") == "critical" for w in warns),
        "tier": _tier_of(canonical),
    }


def till_envelopes(loam, envelopes_dir: str, vocab: Vocabulary, plot: str,
                   sweep: bool = True) -> dict:
    """

    rewilding tills ~ read every envelope receipt in a plot's .envelopes and
    settle each into the loam, resolving retired names forward. when sweep
    is true, tended clumps no longer backed by a receipt are let go, so the
    bed mirrors the receipts. returns a small report. ~

    """
    tilled, refused, living_by_tier = [], [], {}
    for ep in sorted(Path(envelopes_dir).glob("*.envelope.json")):
        try:
            fields = read_envelope(str(ep), vocab, plot)
            tier = fields.pop("tier")
            if not fields.get("semantic_type"):
                refused.append((ep.name, "envelope carries no semantic_type"))
                continue
            row, notes = loam.till(tier=tier, **fields)
            tilled.append((ep.name, row.semantic_type_declared, row.semantic_type, tier))
            living_by_tier.setdefault(tier, []).append(row.name)
        except ConformanceError as e:
            refused.append((ep.name, str(e)))
        except Exception as e:
            refused.append((ep.name, f"{type(e).__name__}: {e}"))

    swept = 0
    if sweep:
        for tier, living in living_by_tier.items():
            swept += loam.reconcile(plot, tier, living)
    return {"plot": plot, "tilled": tilled, "refused": refused, "swept": swept}
