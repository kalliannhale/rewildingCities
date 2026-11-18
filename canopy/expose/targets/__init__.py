"""
canopy/expose/targets ~ the kinds of place the publish door can write to

  arcgis          an ArcGIS portal, by REST (D-326, D-371). it makes web maps
                  whose layer reads a display copy by URL (arcgis_webmap), and
                  the places map, which holds the explorer's places inside it
                  (arcgis_places_map, arcgis_places.py)

a kind is a TargetKind (base.py) registered here by name; targets.yml names
the kind each target is, and each recorded entry names what was made. ~
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
