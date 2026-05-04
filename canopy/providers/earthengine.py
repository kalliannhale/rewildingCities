"""
canopy/providers/earthengine.py

Google Earth Engine provider.
Wraps the export logic from soil/register/acquire_gee.py.

Requires authentication (free GEE account).
"""

import logging
from pathlib import Path

from .base import Provider, AcquisitionResult, DiscoveryResult

logger = logging.getLogger("providers.earthengine")


class EarthEngineProvider(Provider):
    """Acquires data from Google Earth Engine.
    
    Handles VIIRS nighttime lights, WorldPop population density,
    and any GEE ImageCollection. Requires authenticated GEE account.
    
    If authenticated: runs the export directly.
    If not: returns advisory with setup instructions.
    """

    @property
    def name(self) -> str:
        return "Google Earth Engine"

    def can_handle(self, source_config: dict) -> bool:
        return source_config.get("type") == "earthengine"

    def _check_auth(self) -> bool:
        """Check if Earth Engine is authenticated and initialized."""
        try:
            import ee
            ee.Initialize()
            return True
        except Exception:
            return False

    def acquire(self, source_config, cache_path, dataset_name, **kwargs):
        collection = source_config.get("collection", "unknown")
        gee_project = kwargs.get("gee_project", "rewildingcities")

        # Check authentication
        if not self._check_auth():
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=(
                    f"Earth Engine authentication required for '{dataset_name}' "
                    f"(collection: {collection})."
                ),
                requires_auth=True,
                auth_instructions=(
                    "To set up Google Earth Engine:\n"
                    "  1. Sign up at https://earthengine.google.com/ (free)\n"
                    "  2. Run: earthengine authenticate\n"
                    "  3. Then retry, or run manually:\n"
                    f"     python -m soil.register.acquire_gee "
                    f"plots/{{city}}/manifest.yml --datasets {dataset_name} "
                    f"--project {gee_project}"
                ),
                warnings=[{
                    "level": "info",
                    "primitive": "earthengine_provider",
                    "message": (
                        f"GEE dataset '{dataset_name}' ({collection}) "
                        f"requires authenticated export."
                    )
                }],
            )

        # Authenticated — try to delegate to acquire_gee
        try:
            from soil.register.acquire_gee import acquire_for_city
        except ImportError as e:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=(
                    f"GEE provider requires soil.register.acquire_gee module. "
                    f"Import error: {e}"
                ),
            )

        # The existing acquire_gee works on the whole manifest.
        # For single-dataset acquisition, we call it with a dataset filter.
        plot_dir = kwargs.get("plot_dir") or cache_path.parent.parent
        manifest_path = plot_dir / "manifest.yml"

        if not manifest_path.exists():
            # Try parent directory
            manifest_path = plot_dir.parent / "manifest.yml"

        if not manifest_path.exists():
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=(
                    f"Cannot find manifest.yml for GEE acquisition. "
                    f"Looked in {plot_dir} and {plot_dir.parent}"
                ),
            )

        try:
            results = acquire_for_city(
                str(manifest_path),
                datasets=[dataset_name],
                project=gee_project,
            )

            if results.get(dataset_name):
                size = cache_path.stat().st_size if cache_path.exists() else 0
                return AcquisitionResult(
                    dataset_name=dataset_name,
                    success=True,
                    path=str(cache_path),
                    size_bytes=size,
                    message=f"Acquired from GEE ({collection})",
                )
            else:
                return AcquisitionResult(
                    dataset_name=dataset_name,
                    success=False,
                    message=f"GEE export did not produce {dataset_name}",
                )

        except Exception as e:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=f"GEE acquisition failed: {e}",
            )

    def discover(self, bbox, semantic_types=None, **kwargs):
        """GEE has global coverage for NTL and population."""
        results = []
        
        gee_offerings = {
            "nighttime_lights": {
                "description": (
                    "VIIRS nighttime lights annual composite via GEE. "
                    "Requires free GEE account."
                ),
                "collection": "NOAA/VIIRS/DNB/ANNUAL_V22",
                "band": "average_masked",
                "quality": "500m resolution. Annual composite.",
            },
            "population_density": {
                "description": (
                    "WorldPop population density 100m via GEE. "
                    "Requires free GEE account."
                ),
                "collection": "WorldPop/GP/100m/pop",
                "band": None,
                "quality": "100m resolution. UN-adjusted estimates.",
            },
        }

        for stype, info in gee_offerings.items():
            if semantic_types and stype not in semantic_types:
                continue
            
            source_config = {
                "type": "earthengine",
                "collection": info["collection"],
                "notes": f"Acquired via GEE. {info['description']}",
            }
            if info["band"]:
                source_config["band"] = info["band"]

            results.append(DiscoveryResult(
                semantic_type=stype,
                description=info["description"],
                source_config=source_config,
                requires_auth=True,
                quality_notes=info["quality"],
            ))

        return results
