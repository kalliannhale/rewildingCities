"""
soil/register/acquire_gee.py

Acquire raster datasets from Google Earth Engine for any city.

Currently supports:
  - VIIRS Nighttime Lights (annual composite)
  - WorldPop Population Density

Requires: earthengine-api, authenticated via `earthengine authenticate`

Usage:
    python -m soil.register.acquire_gee plots/nyc/manifest.yml -v
    python -m soil.register.acquire_gee plots/nyc/manifest.yml --datasets ntl population -v

Dependencies: earthengine-api, requests, rasterio, numpy
"""

import argparse
import json
import logging
import time
import yaml
import numpy as np
from pathlib import Path

logger = logging.getLogger("acquire_gee")


def get_bbox_from_data(data_dir):
    """Extract bounding box from available vector data."""
    for filename in ["parks.geojson", "city_boundary.geojson"]:
        path = data_dir / filename
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            coords = []
            for feat in data.get("features", []):
                geom = feat.get("geometry")
                if geom and geom.get("coordinates"):
                    def flatten(c):
                        if isinstance(c[0], (int, float)):
                            coords.append(c)
                        else:
                            for sub in c:
                                flatten(sub)
                    flatten(geom["coordinates"])
            if coords:
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                return [min(lons), min(lats), max(lons), max(lats)]
    return None


def download_ee_image(image, bbox, output_path, scale, description="export"):
    """
    Download an Earth Engine image to a local GeoTIFF.

    Uses getDownloadURL for direct download — no Drive export needed.
    """
    import ee
    import requests

    region = ee.Geometry.Rectangle(bbox)

    logger.info(f"  Requesting download URL for {description}...")

    try:
        url = image.getDownloadURL({
            "region": region,
            "scale": scale,
            "format": "GEO_TIFF",
            "crs": "EPSG:4326"
        })
    except Exception as e:
        # getDownloadURL has size limits — fall back to getThumbURL
        # or use a tiled approach
        logger.warning(f"  Direct download failed: {e}")
        logger.info("  Trying tiled download...")
        return download_ee_image_tiled(image, bbox, output_path, scale, description)

    logger.info(f"  Downloading {description}...")
    resp = requests.get(url, timeout=300, stream=True)
    resp.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(65536):
            f.write(chunk)
            total += len(chunk)
            if total % (5 * 1024 * 1024) < 65536:
                logger.info(f"    {total / (1024*1024):.1f} MB...")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"  Saved: {output_path.name} ({size_mb:.1f} MB)")
    return True


def download_ee_image_tiled(image, bbox, output_path, scale, description):
    """
    Download a large EE image by splitting into tiles and merging.
    Fallback when getDownloadURL exceeds size limits.
    """
    import ee
    import requests
    import rasterio
    from rasterio.merge import merge

    west, south, east, north = bbox
    # Split into 4 quadrants
    mid_lon = (west + east) / 2
    mid_lat = (south + north) / 2

    quadrants = [
        [west, south, mid_lon, mid_lat],
        [mid_lon, south, east, mid_lat],
        [west, mid_lat, mid_lon, north],
        [mid_lon, mid_lat, east, north]
    ]

    temp_dir = output_path.parent / ".gee_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    tile_paths = []

    for i, quad in enumerate(quadrants):
        tile_path = temp_dir / f"{description}_tile_{i}.tif"
        region = ee.Geometry.Rectangle(quad)

        try:
            url = image.getDownloadURL({
                "region": region,
                "scale": scale,
                "format": "GEO_TIFF",
                "crs": "EPSG:4326"
            })

            resp = requests.get(url, timeout=300, stream=True)
            resp.raise_for_status()

            with open(tile_path, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)

            tile_paths.append(tile_path)
            logger.info(f"    Tile {i+1}/4 downloaded")

        except Exception as e:
            logger.warning(f"    Tile {i+1}/4 failed: {e}")

    if not tile_paths:
        logger.error("  All tiles failed")
        return False

    # Merge tiles
    if len(tile_paths) == 1:
        import shutil
        shutil.move(tile_paths[0], output_path)
    else:
        datasets = [rasterio.open(p) for p in tile_paths]
        merged, transform = merge(datasets)
        profile = datasets[0].profile.copy()
        profile.update(
            width=merged.shape[2],
            height=merged.shape[1],
            transform=transform
        )
        for ds in datasets:
            ds.close()

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(merged)

    # Clean up tiles
    for p in tile_paths:
        p.unlink(missing_ok=True)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"  Merged and saved: {output_path.name} ({size_mb:.1f} MB)")
    return True


def acquire_ntl(ee, bbox, output_path, year=2023):
    """
    Acquire VIIRS Nighttime Lights annual composite.

    Uses NOAA/VIIRS/DNB/ANNUAL_V22 (or V21 for pre-2022).
    """
    logger.info(f"  Acquiring nighttime lights for {year}...")

    region = ee.Geometry.Rectangle(bbox)

    if year >= 2022:
        collection_id = "NOAA/VIIRS/DNB/ANNUAL_V22"
    else:
        collection_id = "NOAA/VIIRS/DNB/ANNUAL_V21"

    collection = (ee.ImageCollection(collection_id)
        .filterDate(f"{year}-01-01", f"{year+1}-01-01")
        .filterBounds(region))

    count = collection.size().getInfo()
    logger.info(f"  Found {count} images in {collection_id}")

    if count == 0:
        # Fall back to monthly composites
        logger.info("  Falling back to monthly composites...")
        collection = (ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
            .filterDate(f"{year}-01-01", f"{year+1}-01-01")
            .filterBounds(region)
            .select("avg_rad"))
        count = collection.size().getInfo()
        logger.info(f"  Found {count} monthly images")

        if count == 0:
            logger.error("  No NTL data found")
            return False

        image = collection.median().clip(region)
    else:
        image = collection.first().select("average_masked").clip(region)

    return download_ee_image(
        image, bbox, output_path,
        scale=500,  # VIIRS native resolution ~500m
        description="ntl"
    )


def acquire_population(ee, bbox, output_path, year=2020):
    """
    Acquire WorldPop population density.

    Uses WorldPop/GP/100m/pop dataset — 100m resolution,
    global coverage, UN-adjusted.
    """
    logger.info(f"  Acquiring population density for {year}...")

    region = ee.Geometry.Rectangle(bbox)

    collection = (ee.ImageCollection("WorldPop/GP/100m/pop")
        .filterDate(f"{year}-01-01", f"{year+1}-01-01")
        .filterBounds(region))

    count = collection.size().getInfo()
    logger.info(f"  Found {count} images in WorldPop")

    if count == 0:
        logger.error("  No population data found")
        return False

    image = collection.mosaic().clip(region)

    return download_ee_image(
        image, bbox, output_path,
        scale=100,  # WorldPop native resolution
        description="population"
    )


# Registry of available GEE datasets
GEE_DATASETS = {
    "ntl": {
        "function": acquire_ntl,
        "output_filename": "ntl.tif",
        "description": "VIIRS Nighttime Lights annual composite",
        "semantic_type": "nighttime_lights",
        "manifest_key": "nighttime_lights"
    },
    "population": {
        "function": acquire_population,
        "output_filename": "population.tif",
        "description": "WorldPop population density (persons/100m pixel)",
        "semantic_type": "population_density",
        "manifest_key": "population_density"
    }
}


def acquire_for_city(manifest_path, datasets=None, project=None):
    """
    Acquire GEE datasets for a city.

    Args:
        manifest_path: path to city manifest
        datasets: list of dataset keys to acquire (default: all)
        project: GEE project ID (reads from manifest if not provided)
    """
    import ee

    manifest_path = Path(manifest_path)
    plot_dir = manifest_path.parent
    data_dir = plot_dir / ".data"

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    # Determine GEE project
    if project is None:
        project = manifest.get("gee", {}).get("project", "rewildingcities")

    # Initialize EE
    logger.info(f"  Initializing Earth Engine (project: {project})...")
    try:
        ee.Initialize(project=project)
    except Exception as e:
        logger.error(f"  Earth Engine initialization failed: {e}")
        logger.error("  Run: earthengine authenticate")
        return {}

    # Get bounding box
    bbox = get_bbox_from_data(data_dir)
    if bbox is None:
        logger.error("  Cannot determine bounding box. Fetch vector data first.")
        return {}

    logger.info(f"  BBox: {[round(x, 3) for x in bbox]}")

    # Determine which datasets to acquire
    if datasets is None:
        datasets = list(GEE_DATASETS.keys())

    results = {}
    for key in datasets:
        if key not in GEE_DATASETS:
            logger.warning(f"  Unknown dataset: {key}")
            continue

        config = GEE_DATASETS[key]
        output_path = data_dir / config["output_filename"]

        if output_path.exists():
            logger.info(f"  {key}: already exists ({output_path.name})")
            results[key] = True
            continue

        logger.info(f"\n  Acquiring {config['description']}...")
        try:
            success = config["function"](ee, bbox, output_path)
            results[key] = success
            if success:
                logger.info(f"  {key}: acquired successfully")
        except Exception as e:
            logger.error(f"  {key}: failed — {e}")
            results[key] = False

    # Update 'available' flags in manifest
    try:
        from soil.register.manifest_utils import set_multiple_available
        updates = {}
        for key, success in results.items():
            manifest_key = GEE_DATASETS[key].get("manifest_key", key)
            updates[manifest_key] = success
        set_multiple_available(manifest_path, updates)
    except ImportError:
        pass

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Acquire datasets from Google Earth Engine.")
    parser.add_argument("manifest", help="Path to city manifest YAML")
    parser.add_argument("--datasets", nargs="*", default=None,
        choices=list(GEE_DATASETS.keys()),
        help="Specific datasets to acquire (default: all)")
    parser.add_argument("--project", default=None,
        help="GEE project ID (default: from manifest or 'rewildingcities')")
    parser.add_argument("--force", action="store_true",
        help="Re-acquire even if files exist")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s")

    if args.force:
        data_dir = Path(args.manifest).parent / ".data"
        for key in (args.datasets or GEE_DATASETS.keys()):
            config = GEE_DATASETS.get(key, {})
            path = data_dir / config.get("output_filename", "")
            path.unlink(missing_ok=True)

    logger.info("Acquiring data from Google Earth Engine...")
    results = acquire_for_city(args.manifest, args.datasets, args.project)

    logger.info("\n--- GEE Acquisition Summary ---")
    for key, success in results.items():
        status = "OK" if success else "FAILED"
        logger.info(f"  [{status}] {key}")


if __name__ == "__main__":
    main()