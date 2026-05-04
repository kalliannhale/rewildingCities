"""
canopy/providers/__init__.py

Data acquisition providers. Each knows one protocol.
The registry dispatches to the right provider based on source config.
"""

from .base import (
    Provider,
    ProviderRegistry,
    AcquisitionResult,
    DiscoveryResult,
    LocalProvider,
    URLProvider,
    ManualProvider,
)
from .socrata import SocrataProvider
from .arcgis import ArcGISProvider
from .stac import STACProvider
from .s3 import S3Provider
from .earthengine import EarthEngineProvider


def create_default_registry() -> ProviderRegistry:
    """Create a registry with all built-in providers."""
    registry = ProviderRegistry()
    registry.register(LocalProvider())
    registry.register(URLProvider())
    registry.register(ManualProvider())
    registry.register(SocrataProvider())
    registry.register(ArcGISProvider())
    registry.register(STACProvider())
    registry.register(S3Provider())
    registry.register(EarthEngineProvider())
    return registry


__all__ = [
    "Provider",
    "ProviderRegistry",
    "AcquisitionResult",
    "DiscoveryResult",
    "LocalProvider",
    "URLProvider",
    "ManualProvider",
    "SocrataProvider",
    "ArcGISProvider",
    "STACProvider",
    "S3Provider",
    "EarthEngineProvider",
    "create_default_registry",
]
