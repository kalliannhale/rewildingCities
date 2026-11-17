"""
canopy/expose/targets ~ the kinds of place the publish door can write to

  arcgis_webmap   a web map item in an ArcGIS portal whose layer reads a display
                  copy by URL (D-326)

a kind is a TargetKind (base.py) registered here by name; targets.yml names
the kind each target is. ~
"""

from __future__ import annotations

from .arcgis_webmap import ArcGISWebMap
from .base import Built, PublishRefusal, Target, TargetKind, load_targets, record_path


def registered(http=None, version: str = "1.0.0") -> dict:
    """every kind, by name. http reaches the kinds that speak HTTP, so tests
    hand them a fake."""
    return {ArcGISWebMap.name: ArcGISWebMap(http=http, version=version)}


__all__ = ["ArcGISWebMap", "Built", "PublishRefusal", "Target", "TargetKind",
           "load_targets", "record_path", "registered"]
