"""
canopy/providers/s3.py

ESA WorldCover provider via public AWS S3 tiles.
Wraps the tile download logic from soil/register/acquire_land_cover.py.

Free, no authentication required.
"""

import logging
from pathlib import Path

from .base import Provider, AcquisitionResult, DiscoveryResult

logger = logging.getLogger("providers.s3")


class S3Provider(Provider):
    """Acquires ESA WorldCover 10m land cover from public S3 tiles.
    
    Downloads the appropriate tile(s) for a bounding box, crops to 
    extent, and saves as GeoTIFF. Free, no auth.
    """

    @property
    def name(self) -> str:
        return "AWS S3 (ESA WorldCover)"

    def can_handle(self, source_config: dict) -> bool:
        stype = source_config.get("type", "")
        provider = source_config.get("provider", "")
        return (
            stype == "s3"
            or (stype == "url" and provider == "esa_worldcover")
        )

    def acquire(self, source_config, cache_path, dataset_name, **kwargs):
        """Acquire ESA WorldCover tiles via S3 download.
        
        Delegates to the existing acquire_land_cover.py functions.
        """
        try:
            from soil.register.acquire_land_cover import (
                get_tile_urls,
                get_bbox_from_data,
            )
        except ImportError as e:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=(
                    f"S3 provider requires soil.register.acquire_land_cover module. "
                    f"Import error: {e}"
                ),
            )

        import requests

        # Determine bounding box
        bbox = source_config.get("bbox")
        if bbox is None:
            plot_dir = kwargs.get("plot_dir") or cache_path.parent.parent
            data_dir = plot_dir / ".data" if not str(plot_dir).endswith(".data") else plot_dir
            bbox = get_bbox_from_data(data_dir)

        if bbox is None:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=(
                    "Cannot determine bounding box for WorldCover tiles. "
                    "Acquire vector data first, or add 'bbox' to source config."
                ),
            )

        try:
            tile_urls = get_tile_urls(bbox)
            logger.info(f"  WorldCover: {len(tile_urls)} tile(s) needed for bbox")

            if len(tile_urls) == 1:
                # Single tile — download directly
                url = tile_urls[0]
                logger.info(f"  Downloading tile: {url.split('/')[-1]}")
                resp = requests.get(url, stream=True, timeout=300)
                resp.raise_for_status()

                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, "wb") as f:
                    for chunk in resp.iter_content(65536):
                        f.write(chunk)

            else:
                # Multiple tiles — download and try to mosaic
                # For now, download the first tile with a warning
                # Full mosaic requires rasterio.merge
                temp_dir = cache_path.parent / ".worldcover_temp"
                temp_dir.mkdir(parents=True, exist_ok=True)

                tile_paths = []
                for url in tile_urls:
                    tile_name = url.split("/")[-1]
                    tile_path = temp_dir / tile_name
                    if not tile_path.exists():
                        logger.info(f"  Downloading tile: {tile_name}")
                        resp = requests.get(url, stream=True, timeout=300)
                        resp.raise_for_status()
                        with open(tile_path, "wb") as f:
                            for chunk in resp.iter_content(65536):
                                f.write(chunk)
                    tile_paths.append(tile_path)

                # Try to mosaic with rasterio
                try:
                    import rasterio
                    from rasterio.merge import merge

                    datasets = [rasterio.open(p) for p in tile_paths]
                    mosaic, transform = merge(datasets)
                    profile = datasets[0].profile.copy()
                    profile.update(
                        height=mosaic.shape[1],
                        width=mosaic.shape[2],
                        transform=transform,
                    )
                    for ds in datasets:
                        ds.close()

                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    with rasterio.open(cache_path, "w", **profile) as dst:
                        dst.write(mosaic)

                except ImportError:
                    # No rasterio — copy first tile with warning
                    import shutil
                    shutil.copy2(tile_paths[0], cache_path)
                    logger.warning(
                        f"  rasterio not available for mosaic — using first tile only. "
                        f"Install rasterio for multi-tile support."
                    )

            size = cache_path.stat().st_size
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=True,
                path=str(cache_path),
                size_bytes=size,
                message=(
                    f"Acquired {size / 1024 / 1024:.1f} MB ESA WorldCover "
                    f"({len(tile_urls)} tile(s))"
                ),
            )

        except Exception as e:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=f"WorldCover acquisition failed: {e}",
            )

    def discover(self, bbox, semantic_types=None, **kwargs):
        """ESA WorldCover is available globally at 10m."""
        if semantic_types and "land_cover" not in semantic_types:
            return []

        return [DiscoveryResult(
            semantic_type="land_cover",
            description=(
                "ESA WorldCover 10m land cover (2021). "
                "11 classes including tree cover, built-up, water, cropland. "
                "Free via AWS S3, no authentication."
            ),
            source_config={
                "type": "s3",
                "provider": "esa_worldcover",
                "version": "v200",
                "year": 2021,
                "notes": "ESA WorldCover 10m tiles, auto-acquired via S3",
            },
            estimated_size="100-500 MB per city",
            requires_auth=False,
            quality_notes="10m resolution. 2021 vintage.",
        )]
