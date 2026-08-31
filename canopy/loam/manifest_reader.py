"""
canopy/loam/manifest_reader.py

manifest_reader ~ how rewilding plants what has arrived

a plot's manifest is its bronze registry: a receipt of the sources it
declares, not of conformed artifacts. so a planted holding carries a true
name, a source path, its declared classification scheme, and whether it is
available yet ~ but not a crs, which only arrives when the data is tilled.
this reads the receipt and never writes back, never invents a field. ~

"""

from __future__ import annotations

from pathlib import Path

import yaml


def read_manifest(manifest_path: str) -> tuple[str, dict]:
    """

    open a plot's manifest receipt ~ returns (plot_id, datasets). ~

    """
    doc = yaml.safe_load(Path(manifest_path).read_text()) or {}
    city = doc.get("city") or {}
    plot = city.get("id") or doc.get("plot") or Path(manifest_path).parent.name
    return plot, (doc.get("datasets") or {})


def plant_manifest(loam, manifest_path: str, *, sweep: bool = True) -> dict:
    """

    rewilding plants ~ settle every holding the manifest declares into the
    loam at the arrived tier. available-but-unconformed holdings arrive
    without a frame, honestly; the gap between what is declared and what is
    acquired is what rewilding wonders reads backward as the seed still
    missing. when sweep is true, holdings the manifest no longer names are
    let go. ~

    """
    plot, datasets = read_manifest(manifest_path)
    planted, refused, living = [], [], []

    for key, spec in datasets.items():
        spec = spec or {}
        semantic_type = spec.get("semantic_type")
        cache = spec.get("cache") or {}
        path = cache.get("path")
        fmt = spec.get("format")
        classification = spec.get("classification") or {}
        scheme = classification.get("scheme")

        missing = [f for f, v in (("semantic_type", semantic_type),
                                  ("format", fmt), ("cache.path", path)) if v is None]
        if missing:
            refused.append((key, f"manifest missing {', '.join(missing)}"))
            continue

        try:
            row, notes = loam.plant(
                plot=plot, semantic_type=semantic_type, data_path=path, fmt=fmt,
                crs=None,                       # a source has no frame yet; honest
                spatial_ref=plot,
                conformed_by=scheme,            # the classification scheme, straight from the manifest
                coverage=None,
                content_hash=None,              # the source url could seed this later
                receipt_path=manifest_path)
            living.append(row.name)
            planted.append((key, semantic_type, spec.get("available", None),
                            [n.message for n in notes]))
        except Exception as e:
            refused.append((key, str(e)))

    swept = loam.reconcile(plot, "arrived", living) if sweep else 0
    return {"plot": plot, "planted": planted, "refused": refused, "swept": swept}