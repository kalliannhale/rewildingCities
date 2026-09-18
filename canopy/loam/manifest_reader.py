"""
canopy/loam/manifest_reader.py

manifest_reader ~ how rewilding plants what has arrived

a plot's manifest is its bronze registry: a receipt of the sources it
declares, not of conformed artifacts. so a planted holding carries a true
name, a source path, its declared classification scheme, and whether it is
available yet ~ but not a crs, which only arrives when the data is tilled.
this reads the receipt and never writes back, never invents a field. ~

it no longer parses that receipt itself. it used to, and the two readers
drifted: the orchestrator's parser invented a format and a cache path a
dataset never declared, while this one refused the same dataset outright,
and it read `classification.scheme` which the other dropped entirely. one
file, two pictures of itself. now there is one parser (canopy.orchestrator
.parsing.parse_manifest) and one model (ManifestDataset), and this plants
from that model. the strictness that lived here moved INTO the model, where
both halves inherit it. P-01. ~

"""

from __future__ import annotations

from pathlib import Path


def read_manifest(manifest_path: str) -> tuple[str, dict]:
    """

    open a plot's manifest receipt ~ returns (plot_id, datasets), where each
    dataset is a ManifestDataset. kept for callers that want the pair; the
    parsing itself belongs to parse_manifest. ~

    """
    from ..orchestrator.parsing import parse_manifest
    manifest = parse_manifest(manifest_path)
    return manifest.city_id, manifest.datasets


def plant_manifest(loam, manifest_path: str, *, sweep: bool = True,
                   manifest=None) -> dict:
    """

    rewilding plants ~ settle every holding the manifest declares into the
    loam at the arrived tier. available-but-unconformed holdings arrive
    without a frame, honestly; the gap between what is declared and what is
    acquired is what rewilding wonders reads backward as the seed still
    missing. when sweep is true, holdings the manifest no longer names are
    let go. ~

    an already-parsed Manifest may be passed in, so a caller that has one
    (the orchestrator does) need not read the file twice. ~

    """
    if manifest is None:
        from ..orchestrator.parsing import parse_manifest
        manifest = parse_manifest(manifest_path)

    plot = manifest.city_id
    planted, refused, living = [], [], []

    for key, dataset in manifest.datasets.items():
        # an incomplete declaration is REFUSED, not defaulted. the model
        # already named every reason, so this reports rather than re-judges.
        if not dataset.is_usable:
            refused.append((key, "manifest missing " + "; ".join(dataset.underspecified)))
            continue

        try:
            row, notes = loam.plant(
                plot=plot,
                semantic_type=dataset.semantic_type,
                data_path=dataset.path,
                fmt=dataset.format,
                crs=None,                        # a source has no frame yet; honest
                spatial_ref=plot,
                conformed_by=dataset.classification_scheme,
                coverage=None,
                content_hash=None,               # the source url could seed this later
                receipt_path=str(manifest.manifest_path or manifest_path))
            living.append(row.name)
            planted.append((key, dataset.semantic_type, dataset.available,
                            [n.message for n in notes]))
        except Exception as e:
            refused.append((key, str(e)))

    swept = loam.reconcile(plot, "arrived", living) if sweep else 0
    return {"plot": plot, "planted": planted, "refused": refused, "swept": swept}
