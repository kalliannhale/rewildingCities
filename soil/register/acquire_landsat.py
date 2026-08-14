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

    # Rank scenes: deprioritize Landsat-7 (its scan-line corrector failed in
    # 2003, so L7 scenes carry striping gaps), then prefer lowest cloud cover.
    # An equally clear L8/L9 scene therefore wins over an L7 one. Ties within a
    # platform tier fall back to cloud cover.
    def sensor_penalty(item):
        platform = str(item["properties"].get("platform", "")).lower()
        return 1 if "landsat-7" in platform or "landsat_7" in platform else 0

    items.sort(key=lambda x: (sensor_penalty(x),
                              x["properties"].get("eo:cloud_cover", 100)))

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


# Band asset names are NOT stable across scenes, collections, or STAC catalogs.
# The same semantic band (e.g. thermal surface temperature) may be exposed as
# "lwir", "lwir11", "ST_B10", etc. Hardcoding one literal works for one city and
# breaks on the next. Instead, list known aliases per semantic band in
# preference order and let the scene's own asset list decide. This is the same
# canonical-vs-source-vocabulary pattern as the land-cover crosswalks; in the
# long run it belongs in the seeds layer, but a preference list is the
# right-sized version for the acquisition primitive.
BAND_ALIASES = {
    "thermal": ["lwir", "lwir11", "ST_B10", "lwir1"],   # surface-temp thermal
    "nir":     ["nir08", "nir", "B5"],
    "red":     ["red", "B4"],
    "qa":      ["qa_pixel", "QA_PIXEL"],                 # per-pixel quality
}


# QA_PIXEL bit flags. This layout is standardized across Landsat 4-9 Collection 2,
# so masking on it is general, not scene-specific: it is the sensor's own record
# of which pixels are unusable, unlike a temperature clamp, which is a guess.
QA_FILL          = 1 << 0
QA_DILATED_CLOUD = 1 << 1
QA_CIRRUS        = 1 << 2   # L8/9 only; bit is 0 on L7, so masking it is harmless
QA_CLOUD         = 1 << 3
QA_CLOUD_SHADOW  = 1 << 4


def qa_bad_mask(qa):
    """Boolean mask of pixels to EXCLUDE, from the QA_PIXEL band: fill, cloud,
    dilated cloud, cirrus, and cloud shadow. Water and snow are left in, they
    are valid surfaces we may want. QA_PIXEL is an integer bitmask (no scale)."""
    import numpy as np
    bad_bits = (QA_FILL | QA_DILATED_CLOUD | QA_CIRRUS | QA_CLOUD | QA_CLOUD_SHADOW)
    return (qa.astype(np.uint32) & bad_bits) > 0


def resolve_band(item, semantic):
    """Return the asset key this scene actually uses for a semantic band,
    trying known aliases in order. Fails loudly with both the tried aliases
    and the scene's real asset list if none match."""
    available = list(item.get("assets", {}).keys())
    for alias in BAND_ALIASES[semantic]:
        if alias in available:
            if alias != BAND_ALIASES[semantic][0]:
                logger.info(f"    {semantic}: using '{alias}' "
                            f"(scene does not expose '{BAND_ALIASES[semantic][0]}')")
            return alias
    raise ValueError(
        f"No {semantic} band found. Tried {BAND_ALIASES[semantic]}; "
        f"scene exposes {available}")


def convert_lst_to_celsius(raw_path, output_path, qa_path=None):
    """
    Convert Landsat Collection 2 Surface Temperature to Celsius.

    Scale: Kelvin = DN * 0.00341802 + 149.0
    Then: Celsius = Kelvin - 273.15

    Bad pixels (fill, cloud, cloud shadow) are removed using the scene's QA_PIXEL
    band when supplied, which is the principled mask: the sensor's own quality
    record, general across all Collection 2 scenes. Without QA, only the raw
    fill value (DN 0) is masked, and edge/fill artifacts may survive.
    """
    import rasterio

    logger.info("  Converting LST to Celsius...")

    with rasterio.open(raw_path) as src:
        data = src.read(1).astype(np.float32)
        profile = src.profile.copy()

    celsius = data * 0.00341802 + 149.0 - 273.15
    celsius[data == 0] = np.nan   # raw fill

    if qa_path is not None:
        with rasterio.open(qa_path) as q:
            bad = qa_bad_mask(q.read(1))
        n_bad = int(np.count_nonzero(bad & ~np.isnan(celsius)))
        celsius[bad] = np.nan
        logger.info(f"  QA masked {n_bad} LST pixels (fill/cloud/shadow)")
    else:
        logger.info("  No QA band supplied; only raw fill masked "
                    "(edge artifacts may survive)")

    profile.update(dtype="float32", nodata=float("nan"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(celsius, 1)

    logger.info(f"  LST range: {np.nanmin(celsius):.1f} to {np.nanmax(celsius):.1f} °C")
    return output_path


def compute_ndvi(nir_path, red_path, output_path, qa_path=None):
    """
    Compute NDVI from NIR (B5) and Red (B4) bands.

    Landsat Collection 2 Surface Reflectance:
        Reflectance = DN * 0.0000275 + (-0.2)

    Bad pixels are removed with the QA_PIXEL band when supplied (same principled
    mask as LST), in addition to per-band fill and the [-1, 1] bound.
    """
    import rasterio

    logger.info("  Computing NDVI...")

    with rasterio.open(nir_path) as nir_src, rasterio.open(red_path) as red_src:
        nir = nir_src.read(1).astype(np.float32) * 0.0000275 + (-0.2)
        red = red_src.read(1).astype(np.float32) * 0.0000275 + (-0.2)
        profile = nir_src.profile.copy()

    denominator = nir + red
    with np.errstate(invalid="ignore", divide="ignore"):
        ndvi = np.where(denominator != 0, (nir - red) / denominator, np.nan)

    # Mask nodata where EITHER band was fill (DN==0). The original masked only
    # NIR; a red-nodata pixel with valid NIR drives the denominator to ~0 and
    # explodes NDVI (the -64..677 range). Both bands must be valid.
    with rasterio.open(nir_path) as src:
        nir_raw = src.read(1)
    with rasterio.open(red_path) as src:
        red_raw = src.read(1)
    ndvi[(nir_raw == 0) | (red_raw == 0)] = np.nan

    # QA_PIXEL mask (cloud/shadow/fill): the sensor's own quality record.
    if qa_path is not None:
        with rasterio.open(qa_path) as q:
            ndvi[qa_bad_mask(q.read(1))] = np.nan

    # NDVI is bounded to [-1, 1] by definition. Anything outside is a near-zero
    # denominator artifact, not signal: mask it rather than clip, since clipping
    # would fake a real extreme.
    ndvi[np.abs(ndvi) > 1] = np.nan

    profile.update(dtype="float32", nodata=float("nan"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(ndvi, 1)

    logger.info(f"  NDVI range: {np.nanmin(ndvi):.2f} to {np.nanmax(ndvi):.2f}")
    return output_path


def clip_to_boundary(raster_path, bbox_wgs84, label="raster"):
    """Clip a raster in place to a WGS84 [west, south, east, north] bbox.

    General across projections: the clip geometry is reprojected from WGS84 into
    the raster's OWN CRS before masking, so this works whether the raster is
    WGS84 (like WorldCover) or UTM (like Landsat Collection 2) or anything else.
    Assuming the bbox and raster share a CRS, as a naive crop would, silently
    clips the wrong region on any projected raster. Nothing here is
    site-specific: the CRS and extent come from the raster and the boundary.
    """
    import rasterio
    from rasterio.mask import mask as rio_mask
    from rasterio.warp import transform_geom
    from shapely.geometry import box, mapping

    geom_wgs84 = mapping(box(*bbox_wgs84))
    with rasterio.open(raster_path) as src:
        geom = transform_geom("EPSG:4326", src.crs, geom_wgs84)
        out_image, out_transform = rio_mask(src, [geom], crop=True)
        profile = src.profile.copy()
        profile.update(height=out_image.shape[1], width=out_image.shape[2],
                       transform=out_transform)
    with rasterio.open(raster_path, "w", **profile) as dst:
        dst.write(out_image)

    arr = out_image[0].astype("float32")
    valid = arr[np.isfinite(arr)]
    if valid.size:
        logger.info(f"  Clipped {label} to boundary: {out_image.shape[2]} x "
                    f"{out_image.shape[1]} px, range {valid.min():.2f} to "
                    f"{valid.max():.2f}")
    else:
        logger.info(f"  Clipped {label} to boundary: {out_image.shape[2]} x "
                    f"{out_image.shape[1]} px (no valid pixels in extent)")
    return out_image.shape[2], out_image.shape[1]


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

    def mark_available():
        try:
            from soil.register.manifest_utils import set_multiple_available
            updates = {}
            if lst_output.exists():
                updates["land_surface_temperature"] = True
            if ndvi_output.exists():
                updates["ndvi"] = True
            if updates:
                set_multiple_available(manifest_path, updates)
        except ImportError:
            pass

    # Cache hit: both files already on disk, flags reflect reality.
    if lst_output.exists() and ndvi_output.exists():
        logger.info("LST and NDVI already exist. Use --force to re-acquire.")
        mark_available()
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
        download_band(best, resolve_band(best, "thermal"), st_path)
    else:
        logger.info("    LST raw already downloaded")

    # QA_PIXEL band, used to mask cloud/shadow/fill in both LST and NDVI.
    qa_path = temp_dir / "qa_pixel.tif"
    if not qa_path.exists():
        try:
            download_band(best, resolve_band(best, "qa"), qa_path)
        except (ValueError, KeyError) as e:
            logger.warning(f"  QA band unavailable ({e}); proceeding without it")
            qa_path = None
    else:
        logger.info("    QA already downloaded")

    # Convert to Celsius
    convert_lst_to_celsius(st_path, lst_output, qa_path=qa_path)
    clip_to_boundary(lst_output, bbox, label="LST (°C)")

    # Download NIR and Red from same scene for NDVI
    nir_path = temp_dir / "nir08.tif"
    red_path = temp_dir / "red.tif"

    if not nir_path.exists():
        download_band(best, resolve_band(best, "nir"), nir_path)
    else:
        logger.info("    NIR already downloaded")

    if not red_path.exists():
        download_band(best, resolve_band(best, "red"), red_path)
    else:
        logger.info("    Red already downloaded")

    compute_ndvi(nir_path, red_path, ndvi_output, qa_path=qa_path)
    clip_to_boundary(ndvi_output, bbox, label="NDVI")

    # Summary
    logger.info("\n  Acquisition complete:")
    for path in [lst_output, ndvi_output]:
        if path.exists():
            logger.info(f"    {path.name}: "
                         f"{path.stat().st_size / (1024*1024):.1f} MB")

    mark_available()   # flags set ONLY after the files exist on disk
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