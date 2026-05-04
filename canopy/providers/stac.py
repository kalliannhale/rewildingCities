"""
canopy/providers/stac.py

Planetary Computer STAC provider for Landsat data.
Wraps the search/download logic from soil/register/acquire_landsat.py.

Free, no authentication required.
"""

import json
import logging
from pathlib import Path

from .base import Provider, AcquisitionResult, DiscoveryResult

logger = logging.getLogger("providers.stac")

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
SIGN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"


class STACProvider(Provider):
    """Acquires satellite imagery from Microsoft Planetary Computer via STAC.
    
    Handles Landsat Collection 2 Level-2 (LST, NDVI, individual bands).
    Free access, no authentication required — uses signed URLs.
    """

    @property
    def name(self) -> str:
        return "Planetary Computer (STAC)"

    def can_handle(self, source_config: dict) -> bool:
        stype = source_config.get("type", "")
        provider = source_config.get("provider", "")
        return (
            stype == "stac"
            or (stype == "api" and provider == "planetary_computer")
        )

    def acquire(self, source_config, cache_path, dataset_name, **kwargs):
        """Acquire Landsat data via STAC search + signed URL download.
        
        Delegates to the existing acquire_landsat.py functions.
        Expects source_config to have collection, band, and optionally
        bbox and temporal parameters.
        """
        # Try importing the existing acquisition module
        try:
            from soil.register.acquire_landsat import (
                search_scenes,
                download_band,
                convert_lst_to_celsius,
                compute_ndvi,
                get_bbox_from_data,
                sign_href,
            )
        except ImportError as e:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=(
                    f"STAC provider requires soil.register.acquire_landsat module. "
                    f"Import error: {e}"
                ),
            )

        # Determine bounding box
        bbox = source_config.get("bbox")
        if bbox is None:
            # Try to derive from existing vector data
            plot_dir = kwargs.get("plot_dir") or cache_path.parent.parent
            data_dir = plot_dir / ".data" if not str(plot_dir).endswith(".data") else plot_dir
            bbox = get_bbox_from_data(data_dir)

        if bbox is None:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=(
                    "Cannot determine bounding box for STAC search. "
                    "Acquire vector data (parks, boundary) first, or "
                    "add 'bbox' to the source config."
                ),
            )

        # Temporal parameters
        year_start = source_config.get("year_start", 2021)
        year_end = source_config.get("year_end", 2024)
        months = source_config.get("months", [6, 7, 8, 9])
        max_cloud = source_config.get("max_cloud", 15)
        semantic_type = source_config.get("semantic_type", dataset_name)

        try:
            # Search for scenes
            items = search_scenes(
                bbox=bbox,
                start_date=f"{year_start}-01-01",
                end_date=f"{year_end}-12-31",
                max_cloud=max_cloud,
                months=months,
            )

            if not items:
                return AcquisitionResult(
                    dataset_name=dataset_name,
                    success=False,
                    message=(
                        f"No Landsat scenes found for bbox={bbox}, "
                        f"years {year_start}-{year_end}, months {months}, "
                        f"cloud <{max_cloud}%. Try relaxing search parameters."
                    ),
                )

            best = items[0]
            props = best["properties"]
            scene_date = props.get("datetime", "?")[:10]
            cloud = props.get("eo:cloud_cover", "?")
            logger.info(
                f"  Best scene: {scene_date}, cloud={cloud}%, "
                f"{props.get('platform', '?')}"
            )

            # Determine what to download based on semantic type
            temp_dir = cache_path.parent / ".landsat_temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            if semantic_type in ("land_surface_temperature", "lst"):
                # Download thermal band and convert to Celsius
                raw_path = temp_dir / f"{dataset_name}_raw.tif"
                download_band(best, "lwir11", raw_path)
                convert_lst_to_celsius(raw_path, cache_path)

            elif semantic_type == "ndvi":
                # Download NIR + Red, compute NDVI
                nir_path = temp_dir / "nir08.tif"
                red_path = temp_dir / "red.tif"
                download_band(best, "nir08", nir_path)
                download_band(best, "red", red_path)
                compute_ndvi(nir_path, red_path, cache_path)

            else:
                # Generic band download
                band = source_config.get("band", "lwir11")
                download_band(best, band, cache_path)

            size = cache_path.stat().st_size
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=True,
                path=str(cache_path),
                size_bytes=size,
                message=(
                    f"Acquired {size / 1024 / 1024:.1f} MB from Planetary Computer "
                    f"(scene: {scene_date}, cloud: {cloud}%)"
                ),
            )

        except Exception as e:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=f"STAC acquisition failed: {e}",
            )

    def discover(self, bbox, semantic_types=None, **kwargs):
        """Check what Landsat data is available for a bounding box."""
        results = []

        # Landsat is available globally — we can always offer LST and NDVI
        landsat_types = {"land_surface_temperature", "ndvi"}
        relevant = landsat_types
        if semantic_types:
            relevant = landsat_types & set(semantic_types)

        for stype in relevant:
            results.append(DiscoveryResult(
                semantic_type=stype,
                description=(
                    "Landsat 8/9 Collection 2 Level-2 via Planetary Computer. "
                    "Free, no authentication required."
                ),
                source_config={
                    "type": "stac",
                    "provider": "planetary_computer",
                    "collection": "landsat-c2-l2",
                    "semantic_type": stype,
                    "months": [6, 7, 8, 9],
                    "max_cloud": 15,
                    "notes": "Summer daytime Landsat, auto-acquired via STAC",
                },
                estimated_size="50-200 MB per scene",
                requires_auth=False,
                quality_notes="30m resolution. Single-scene subject to cloud contamination.",
            ))

        return results
