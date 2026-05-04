"""
soil/register/acquire_land_cover.py

Programmatic acquisition of ESA WorldCover 10m land cover for any city.

Downloads the appropriate tile(s) from AWS S3 (free, no auth),
crops to the city's bounding box, and saves as a GeoTIFF.

Usage:
    python -m soil.register.acquire_land_cover plots/nyc/manifest.yml

Dependencies: requests, rasterio, numpy, shapely
"""

import argparse
import json
import logging
import math
import numpy as np
import yaml
from pathlib import Path

logger = logging.getLogger("acquire_land_cover")

# ESA WorldCover tiles on AWS — truly public, no authentication
TILE_URL_TEMPLATE = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/"
    "v200/2021/map/ESA_WorldCover_10m_2021_v200_{ns}{lat:02d}{ew}{lon:03d}_Map.tif"
)

# ESA WorldCover class definitions
CLASSES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}


def get_tile_urls(bbox):
    """
    Determine which ESA WorldCover tiles cover a bounding box.

    Tiles are 3x3 degrees, named by southwest corner.
    e.g., N39W075 covers 39-42°N, 75-72°W
    """
    west, south, east, north = bbox

    # Floor to nearest 3-degree grid
    lat_start = int(math.floor(south / 3) * 3)
    lat_end = int(math.floor(north / 3) * 3)
    lon_start = int(math.floor(west / 3) * 3)
    lon_end = int(math.floor(east / 3) * 3)

    urls = []
    for lat in range(lat_start, lat_end + 1, 3):
        for lon in range(lon_start, lon_end + 1, 3):
            ns = "N" if lat >= 0 else "S"
            ew = "E" if lon >= 0 else "W"
            url = TILE_URL_TEMPLATE.format(
                ns=ns, lat=abs(lat), ew=ew, lon=abs(lon)
            )
            urls.append(url)

    return urls


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


def acquire_for_city(manifest_path):
    """Download and crop ESA WorldCover land cover for a city."""
    import requests
    import rasterio
    from rasterio.merge import merge
    from rasterio.mask import mask as rio_mask
    from shapely.geometry import box

    manifest_path = Path(manifest_path)
    plot_dir = manifest_path.parent
    data_dir = plot_dir / ".data"
    temp_dir = data_dir / ".landsat_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    output_path = data_dir / "land_cover.tif"

    if output_path.exists():
        logger.info("Land cover already exists. Use --force to re-acquire.")
        # Update 'available' flag in manifest
    try:
        from soil.register.manifest_utils import set_available
        set_available(manifest_path, "land_cover", True)
    except ImportError:
        pass

    return True

    # Get bounding box
    bbox = get_bbox_from_data(data_dir)
    if bbox is None:
        logger.error("Cannot determine bounding box. "
                     "Fetch parks or boundary data first.")
        return False

    logger.info(f"  BBox: {[round(x, 3) for x in bbox]}")

    # Determine tiles needed
    tile_urls = get_tile_urls(bbox)
    logger.info(f"  Need {len(tile_urls)} tile(s)")

    # Download tiles
    tile_paths = []
    for url in tile_urls:
        tile_name = url.split("/")[-1]
        tile_path = temp_dir / tile_name

        if tile_path.exists():
            logger.info(f"    {tile_name}: already downloaded")
            tile_paths.append(tile_path)
            continue

        logger.info(f"    Downloading {tile_name}...")
        try:
            resp = requests.get(url, timeout=300, stream=True)
            resp.raise_for_status()

            total = 0
            with open(tile_path, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
                    total += len(chunk)
                    if total % (10 * 1024 * 1024) < 65536:
                        logger.info(f"      {total / (1024*1024):.0f} MB...")

            logger.info(f"    Done: {total / (1024*1024):.1f} MB")
            tile_paths.append(tile_path)

        except Exception as e:
            logger.warning(f"    Failed: {e}")

    if not tile_paths:
        logger.error("No tiles downloaded.")
        return False

    # Merge tiles if multiple
    if len(tile_paths) > 1:
        logger.info("  Merging tiles...")
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

        merged_path = temp_dir / "merged_worldcover.tif"
        with rasterio.open(merged_path, "w", **profile) as dst:
            dst.write(merged)
        src_path = merged_path
    else:
        src_path = tile_paths[0]

    # Crop to city bbox
    logger.info("  Cropping to city extent...")
    city_bbox = box(*bbox)

    with rasterio.open(src_path) as src:
        out_image, out_transform = rio_mask(
            src, [city_bbox.__geo_interface__], crop=True
        )
        profile = src.profile.copy()
        profile.update(
            height=out_image.shape[1],
            width=out_image.shape[2],
            transform=out_transform
        )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(out_image)

    # Report class distribution
    data = out_image[0]
    unique, counts = np.unique(data[data > 0], return_counts=True)
    total_pixels = counts.sum()

    logger.info(f"\n  Land cover saved: {output_path}")
    logger.info(f"  Size: {output_path.stat().st_size / (1024*1024):.1f} MB")
    logger.info("  Class distribution:")
    for val, count in zip(unique, counts):
        name = CLASSES.get(val, f"Unknown ({val})")
        pct = count / total_pixels * 100
        logger.info(f"    {val:>3} {name:<30} {pct:>5.1f}%")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Acquire ESA WorldCover 10m land cover for a city.")
    parser.add_argument("manifest", help="Path to city manifest YAML")
    parser.add_argument("--force", action="store_true",
                        help="Re-acquire even if file exists")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s")

    if args.force:
        output = Path(args.manifest).parent / ".data" / "land_cover.tif"
        output.unlink(missing_ok=True)

    success = acquire_for_city(args.manifest)
    if not success:
        exit(1)


if __name__ == "__main__":
    main()