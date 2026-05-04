"""
soil/register/acquire_landsat.py

Programmatic acquisition of Landsat 8/9 LST and NDVI for any city.

Uses Microsoft Planetary Computer STAC API to search for scenes,
then downloads Cloud Optimized GeoTIFFs via signed URLs (free, no auth).

Anyone who clones the repo can run:
    python -m soil.register.acquire_landsat plots/nyc/manifest.yml

And get LST + NDVI rasters without touching a browser.

Dependencies: requests, rasterio, numpy
"""

import argparse
import json
import logging
import yaml
import numpy as np
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("acquire_landsat")

# Microsoft Planetary Computer STAC — free, no account needed
STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
SIGN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"


def sign_href(href):
    """Sign a Planetary Computer asset URL for download."""
    import requests
    resp = requests.get(SIGN_URL, params={"href": href}, timeout=15)
    resp.raise_for_status()
    return resp.json()["href"]


def search_scenes(bbox, start_date, end_date, max_cloud=20, months=None):
    """
    Search Planetary Computer STAC for Landsat 8/9 scenes.

    Args:
        bbox: [west, south, east, north] in WGS84
        start_date: "YYYY-MM-DD"
        end_date: "YYYY-MM-DD"
        max_cloud: maximum cloud cover percentage
        months: list of months to include (e.g., [6,7,8,9] for summer)

    Returns:
        List of STAC items with asset URLs
    """
    import requests

    search_body = {
        "collections": ["landsat-c2-l2"],
        "bbox": bbox,
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "limit": 200
    }

    logger.info(f"  Searching Planetary Computer for Landsat scenes...")
    logger.info(f"  Date range: {start_date} to {end_date}, cloud < {max_cloud}%")

    resp = requests.post(f"{STAC_URL}/search", json=search_body, timeout=30)
    resp.raise_for_status()
    results = resp.json()

    items = results.get("features", [])
    logger.info(f"  Found {len(items)} total scenes")

    # Filter by cloud cover
    items = [i for i in items
             if i["properties"].get("eo:cloud_cover", 100) < max_cloud]
    logger.info(f"  {len(items)} scenes with <{max_cloud}% cloud")

    # Filter by month if specified
    if months:
        items = [
            item for item in items
            if datetime.fromisoformat(
                item["properties"]["datetime"].replace("Z", "+00:00")
            ).month in months
        ]
        logger.info(f"  {len(items)} scenes in months {months}")

    # Sort by cloud cover (best first)
    items.sort(key=lambda x: x["properties"].get("eo:cloud_cover", 100))

    return items


def download_band(item, band_name, output_path):
    """Download a single band from a STAC item via signed URL."""
    import requests

    assets = item.get("assets", {})
    if band_name not in assets:
        available = list(assets.keys())
        raise ValueError(
            f"Band '{band_name}' not found. Available: {available}")

    href = assets[band_name]["href"]
    signed = sign_href(href)

    logger.info(f"    Downloading {band_name}...")

    resp = requests.get(signed, timeout=300, stream=True)
    resp.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(65536):
            f.write(chunk)
            total += len(chunk)
            if total % (10 * 1024 * 1024) < 65536:
                logger.info(f"      {total / (1024*1024):.0f} MB...")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"    Saved: {output_path.name} ({size_mb:.1f} MB)")
    return output_path


def convert_lst_to_celsius(raw_path, output_path):
    """
    Convert Landsat Collection 2 Surface Temperature to Celsius.

    Scale: Kelvin = DN * 0.00341802 + 149.0
    Then: Celsius = Kelvin - 273.15
    """
    import rasterio

    logger.info("  Converting LST to Celsius...")

    with rasterio.open(raw_path) as src:
        data = src.read(1).astype(np.float32)
        profile = src.profile.copy()

    nodata_mask = (data == 0)
    celsius = data * 0.00341802 + 149.0 - 273.15
    celsius[nodata_mask] = np.nan

    profile.update(dtype="float32", nodata=float("nan"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(celsius, 1)

    logger.info(f"  LST range: {np.nanmin(celsius):.1f} to {np.nanmax(celsius):.1f} °C")
    return output_path


def compute_ndvi(nir_path, red_path, output_path):
    """
    Compute NDVI from NIR (B5) and Red (B4) bands.

    Landsat Collection 2 Surface Reflectance:
        Reflectance = DN * 0.0000275 + (-0.2)
    """
    import rasterio

    logger.info("  Computing NDVI...")

    with rasterio.open(nir_path) as nir_src, rasterio.open(red_path) as red_src:
        nir = nir_src.read(1).astype(np.float32) * 0.0000275 + (-0.2)
        red = red_src.read(1).astype(np.float32) * 0.0000275 + (-0.2)
        profile = nir_src.profile.copy()

    denominator = nir + red
    ndvi = np.where(denominator != 0, (nir - red) / denominator, np.nan)

    # Mask nodata (where original DN was 0)
    with rasterio.open(nir_path) as src:
        nir_raw = src.read(1)
    ndvi[nir_raw == 0] = np.nan

    profile.update(dtype="float32", nodata=float("nan"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(ndvi, 1)

    logger.info(f"  NDVI range: {np.nanmin(ndvi):.2f} to {np.nanmax(ndvi):.2f}")
    return output_path


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
                bbox = [min(lons), min(lats), max(lons), max(lats)]
                logger.info(f"  BBox from {filename}: {[round(x, 3) for x in bbox]}")
                return bbox

    return None


def acquire_for_city(manifest_path, max_scenes=3, year_start=2021,
                     year_end=2024, summer_months=None):
    """
    Acquire LST and NDVI for a city based on its manifest.

    Reads the bounding box from available vector data, searches
    Planetary Computer for summer Landsat scenes, downloads the
    best ones, and computes LST (Celsius) and NDVI.
    """
    manifest_path = Path(manifest_path)
    plot_dir = manifest_path.parent
    data_dir = plot_dir / ".data"
    temp_dir = data_dir / ".landsat_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    lst_output = data_dir / "lst_summer.tif"
    ndvi_output = data_dir / "ndvi.tif"

    if summer_months is None:
        summer_months = [6, 7, 8, 9]

    # Check if already acquired
    if lst_output.exists() and ndvi_output.exists():
        logger.info("LST and NDVI already exist. Use --force to re-acquire.")
        # Update 'available' flags in manifest
    try:
        from soil.register.manifest_utils import set_multiple_available
        updates = {}
        if lst_output.exists():
            updates["land_surface_temperature"] = True
        if ndvi_output.exists():
            updates["ndvi"] = True
        set_multiple_available(manifest_path, updates)
    except ImportError:
        pass

    return True

    # Get bounding box
    bbox = get_bbox_from_data(data_dir)
    if bbox is None:
        logger.error("Cannot determine bounding box. "
                     "Fetch parks or boundary data first:")
        logger.error("  python -m soil.register.fetch_dataset "
                     f"{manifest_path} -v")
        return False

    # Search for scenes
    items = search_scenes(
        bbox=bbox,
        start_date=f"{year_start}-01-01",
        end_date=f"{year_end}-12-31",
        max_cloud=15,
        months=summer_months
    )

    if not items:
        logger.error("No suitable scenes found. "
                     "Try --max-cloud 30 or expanding --year-start/--year-end.")
        return False

    # Select best scenes
    selected = items[:max_scenes]
    logger.info(f"\n  Selected {len(selected)} scenes:")
    for item in selected:
        props = item["properties"]
        logger.info(f"    {props.get('datetime', '?')[:10]} — "
                     f"cloud: {props.get('eo:cloud_cover', '?'):.1f}% — "
                     f"{props.get('platform', '?')}")

    # Download Surface Temperature band from best scene
    best = selected[0]
    st_path = temp_dir / "lst_raw.tif"
    if not st_path.exists():
        download_band(best, "lwir11", st_path)
    else:
        logger.info("    LST raw already downloaded")

    # Convert to Celsius
    convert_lst_to_celsius(st_path, lst_output)

    # Download NIR and Red from same scene for NDVI
    nir_path = temp_dir / "nir08.tif"
    red_path = temp_dir / "red.tif"

    if not nir_path.exists():
        download_band(best, "nir08", nir_path)
    else:
        logger.info("    NIR already downloaded")

    if not red_path.exists():
        download_band(best, "red", red_path)
    else:
        logger.info("    Red already downloaded")

    compute_ndvi(nir_path, red_path, ndvi_output)

    # Summary
    logger.info("\n  Acquisition complete:")
    for path in [lst_output, ndvi_output]:
        if path.exists():
            logger.info(f"    {path.name}: "
                         f"{path.stat().st_size / (1024*1024):.1f} MB")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Acquire Landsat LST and NDVI for a city.")
    parser.add_argument("manifest", help="Path to city manifest YAML")
    parser.add_argument("--max-scenes", type=int, default=3,
                        help="Number of scenes to consider (default: 3)")
    parser.add_argument("--max-cloud", type=int, default=15,
                        help="Max cloud cover percent (default: 15)")
    parser.add_argument("--year-start", type=int, default=2021)
    parser.add_argument("--year-end", type=int, default=2024)
    parser.add_argument("--summer-months", type=int, nargs="+",
                        default=[6, 7, 8, 9],
                        help="Months to include (default: 6 7 8 9)")
    parser.add_argument("--force", action="store_true",
                        help="Re-acquire even if files exist")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s")

    if args.force:
        data_dir = Path(args.manifest).parent / ".data"
        (data_dir / "lst_summer.tif").unlink(missing_ok=True)
        (data_dir / "ndvi.tif").unlink(missing_ok=True)
        # Also clear temp files so bands re-download
        temp_dir = data_dir / ".landsat_temp"
        if temp_dir.exists():
            for f in temp_dir.iterdir():
                f.unlink()

    logger.info("Acquiring Landsat data...")
    success = acquire_for_city(
        args.manifest,
        max_scenes=args.max_scenes,
        year_start=args.year_start,
        year_end=args.year_end,
        summer_months=args.summer_months
    )

    if not success:
        exit(1)


if __name__ == "__main__":
    main()