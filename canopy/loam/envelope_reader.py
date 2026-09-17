"""
canopy/loam/envelope_reader.py

envelope_reader ~ how rewilding tills what it has worked

an envelope is a receipt of what happened to one artifact. this reads that
receipt and settles the artifact into the loam as tended (or gathered),
resolving any retired name forward through the vocabulary so old work stays
answerable. it reads only; it never writes back to the envelope, never
invents a field it cannot find. ♡

it does not decide loam's columns; it PROJECTS them. every column derives from
a named field the envelope metadata contract now enforces (see the spine, III.B):

  ~ semantic_type   <- metadata.semantic_type (kept verbatim)
  ~ canonical       <- resolved through canonical.py (what it means today)
  ~ crs             <- metadata.crs
  ~ bbox            <- metadata.bbox
  ~ id_field        <- metadata.id_field         (a single declared join key)
  ~ id_fields       <- metadata.id_fields        (a composite join key, a list)
  ~ unit_key        <- metadata.spatial_unit     (what each row IS)
  ~ conformed_by    <- metadata.classification_scheme.name
  ~ coverage        <- derived from metadata.nodata_percentage (raster) or
                       metadata.data_quality.complete_cases / row_count (tabular)
  ~ parent_ref      <- the last provenance step's first input, named as its clump
  ~ warnings        <- count, and whether any were critical

a field the metadata does not carry projects as None ~ an honest unknown, loam
faithfully reflecting an under-described artifact rather than papering over it.
(the fix for that is upstream: the primitive emits the field; then this projects
it. enforcement makes the omission visible; projection carries it truthfully.)

a composite key (metadata.id_fields, an array) projects into its own loam column,
so an artifact keyed on more than one field (e.g. [feature_id, distance_m]) stays
joinable on its real key rather than losing it. still None until the schema grows:
an output content-hash (the path anchors the name for now) and crosswalk lineage. ~

"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .loam import clump_name, TENDED, GATHERED, ConformanceError
from ..vocabulary import Vocabulary


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


def _coverage(meta: dict, category: str | None) -> float | None:
    """

    coverage as a fraction (0..1), derived from the metadata the contract
    carries, or None when the metadata does not carry what it would take to
    know. never guessed, never defaulted. ~

    ~ raster:  (100 - nodata_percentage) / 100
    ~ tabular: data_quality.complete_cases / row_count

    """
    if category == "raster":
        nodata = meta.get("nodata_percentage")
        if nodata is not None:
            return max(0.0, (100.0 - float(nodata)) / 100.0)
    elif category == "tabular":
        dq = meta.get("data_quality") or {}
        complete = dq.get("complete_cases")
        rows = meta.get("row_count")
        if complete is not None and rows:
            return float(complete) / float(rows)
    return None


def read_envelope(envelope_path: str, vocab: Vocabulary, plot: str) -> dict:
    """

    read one envelope receipt and PROJECT the fields loam indexes. every column
    derives from a named metadata field; nothing is guessed and nothing is
    invented. a field the metadata does not carry projects as None. ~

    """
    doc = json.loads(Path(envelope_path).read_text())
    data = doc.get("data") or {}
    meta = doc.get("metadata") or {}
    prov = doc.get("provenance") or []
    warns = doc.get("warnings") or []

    declared = meta.get("semantic_type")
    res = vocab.resolve(declared) if declared else None
    canonical = res.canonical if res else None

    category = meta.get("data_category")
    bbox = meta.get("bbox")

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

    # the join grammar, PROJECTED from the metadata contract (III.B):
    #   id_field   <- metadata.id_field      (a single declared key)
    #   id_fields  <- metadata.id_fields     (a composite key, a list of fields)
    #   unit_key   <- metadata.spatial_unit  (what each row IS)
    id_field = meta.get("id_field")
    id_fields = meta.get("id_fields")
    unit_key = meta.get("spatial_unit")
    conformed_by = (meta.get("classification_scheme") or {}).get("name")

    return {
        "plot": plot,
        "semantic_type": declared,
        "canonical": canonical,
        "data_path": _norm(data.get("path")),
        "fmt": data.get("format"),
        "crs": meta.get("crs"),
        "native_crs": (meta.get("transform") or {}).get("source_crs"),
        "bbox": tuple(bbox) if bbox else None,
        "spatial_ref": plot,
        "parent_ref": parent_ref,
        "id_field": id_field,
        "id_fields": id_fields,
        "unit_key": unit_key,
        "conformed_by": conformed_by,
        "coverage": _coverage(meta, category),
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
