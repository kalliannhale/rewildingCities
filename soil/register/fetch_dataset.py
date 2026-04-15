"""
soil/register/fetch_dataset.py

Fetch and cache datasets declared in a city manifest.

This is the only Python primitive — it talks to the internet,
which R doesn't do gracefully. It reads the manifest, checks
which datasets need fetching, downloads them to .data/, and
updates cache metadata.

Unlike R primitives, this doesn't go through the PrimitiveRunner
subprocess contract. It's invoked directly by the orchestrator
(or by a CLI command) because it needs to run *before* any
experiment can start — it populates the data that experiments
reference.

Usage:
    python -m soil.register.fetch_dataset plots/nyc/manifest.yml
    python -m soil.register.fetch_dataset plots/nyc/manifest.yml --datasets parks lst_median
    python -m soil.register.fetch_dataset plots/nyc/manifest.yml --force
"""

import sys
import yaml
import json
import hashlib
import shutil
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("fetch_dataset")


# === Fetcher Registry ===

class FetchResult:
    """Result of a single dataset fetch."""
    def __init__(self, dataset_name: str, success: bool, path: str | None = None,
                 message: str = "", warnings: list[dict] | None = None):
        self.dataset_name = dataset_name
        self.success = success
        self.path = path
        self.message = message
        self.warnings = warnings or []


def fetch_local(source: dict, cache_path: Path, dataset_name: str) -> FetchResult:
    """Handle 'local' source type — data already on disk."""
    source_path = Path(source.get("path", ""))

    if not source_path.exists():
        return FetchResult(dataset_name, False,
            message=f"Local source not found: {source_path}")

    if source_path.resolve() != cache_path.resolve():
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, cache_path)

    return FetchResult(dataset_name, True, path=str(cache_path),
        message=f"Copied from {source_path}")


def fetch_url(source: dict, cache_path: Path, dataset_name: str) -> FetchResult:
    """Handle 'url' source type — direct download."""
    import requests

    url = source.get("url", "")
    if not url:
        return FetchResult(dataset_name, False,
            message="URL source has no 'url' field.")

    try:
        logger.info(f"  Downloading {dataset_name} from {url}")
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = cache_path.stat().st_size / (1024 * 1024)
        return FetchResult(dataset_name, True, path=str(cache_path),
            message=f"Downloaded {size_mb:.1f} MB from {url}")

    except Exception as e:
        return FetchResult(dataset_name, False,
            message=f"Download failed: {e}")


def fetch_socrata(source: dict, cache_path: Path, dataset_name: str) -> FetchResult:
    """Handle Socrata API (NYC Open Data, etc.) with pagination."""
    import requests

    endpoint = source.get("endpoint", "")
    if not endpoint:
        return FetchResult(dataset_name, False,
            message="Socrata source has no 'endpoint' field.")

    query_params = source.get("query_params", {})
    params = dict(query_params)

    # Add app token if available
    auth = source.get("auth", {})
    if auth.get("type") == "api_key":
        import os
        key_var = auth.get("key_env_var", "SOCRATA_APP_TOKEN")
        token = os.environ.get(key_var)
        if token:
            params["$app_token"] = token
        else:
            logger.warning(f"  Auth token env var '{key_var}' not set. "
                           "Proceeding without — may be rate limited.")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    ext = cache_path.suffix.lower()
    is_geojson = ext in (".geojson", ".json") or endpoint.endswith(".geojson")

    try:
        if is_geojson:
            # GeoJSON: paginate and merge features
            all_features = []
            page_size = int(params.pop("$limit", 2000))
            offset = 0

            logger.info(f"  Fetching {dataset_name} from Socrata (paginated, {page_size}/page): {endpoint}")

            while True:
                page_params = dict(params)
                page_params["$limit"] = page_size
                page_params["$offset"] = offset

                resp = requests.get(endpoint, params=page_params, timeout=120)
                resp.raise_for_status()
                page_data = resp.json()

                # GeoJSON response has "features" array
                if isinstance(page_data, dict) and "features" in page_data:
                    features = page_data["features"]
                    if not features:
                        break
                    all_features.extend(features)
                    logger.info(f"    Page {offset // page_size + 1}: {len(features)} features (total: {len(all_features)})")
                    if len(features) < page_size:
                        break
                    offset += page_size
                # Plain JSON array response (non-geo Socrata)
                elif isinstance(page_data, list):
                    if not page_data:
                        break
                    all_features.extend(page_data)
                    logger.info(f"    Page {offset // page_size + 1}: {len(page_data)} records (total: {len(all_features)})")
                    if len(page_data) < page_size:
                        break
                    offset += page_size
                else:
                    # Single-page response, no pagination needed
                    all_features = page_data
                    break

            # Write merged GeoJSON
            if isinstance(all_features, list) and len(all_features) > 0:
                if isinstance(all_features[0], dict) and "geometry" in all_features[0]:
                    # It's GeoJSON features — wrap in FeatureCollection
                    merged = {
                        "type": "FeatureCollection",
                        "features": all_features
                    }
                else:
                    # Plain JSON records
                    merged = all_features
            else:
                merged = all_features

            with open(cache_path, "w") as f:
                json.dump(merged, f)

        else:
            # Non-GeoJSON (raster, CSV, etc): single request with high limit
            params.setdefault("$limit", 50000)
            logger.info(f"  Fetching {dataset_name} from Socrata: {endpoint}")
            resp = requests.get(endpoint, params=params, timeout=120)
            resp.raise_for_status()
            with open(cache_path, "wb") as f:
                f.write(resp.content)

        size_mb = cache_path.stat().st_size / (1024 * 1024)
        n_features = len(all_features) if is_geojson and isinstance(all_features, list) else "unknown"
        return FetchResult(dataset_name, True, path=str(cache_path),
            message=f"Fetched {size_mb:.1f} MB from Socrata ({n_features} features)")

    except Exception as e:
        return FetchResult(dataset_name, False,
            message=f"Socrata fetch failed: {e}")


def fetch_arcgis_rest(source: dict, cache_path: Path, dataset_name: str) -> FetchResult:
    """Handle ArcGIS REST API."""
    import requests

    endpoint = source.get("endpoint", "")
    if not endpoint:
        return FetchResult(dataset_name, False,
            message="ArcGIS source has no 'endpoint' field.")

    # ArcGIS REST query endpoint
    query_url = f"{endpoint.rstrip('/')}/query"
    params = {
        "where": source.get("query_params", {}).get("where", "1=1"),
        "outFields": source.get("query_params", {}).get("outFields", "*"),
        "f": "geojson",
        "resultRecordCount": source.get("query_params", {}).get("limit", 10000),
    }

    try:
        logger.info(f"  Fetching {dataset_name} from ArcGIS REST: {query_url}")
        resp = requests.get(query_url, params=params, timeout=120)
        resp.raise_for_status()

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(resp.json(), f)

        size_mb = cache_path.stat().st_size / (1024 * 1024)
        return FetchResult(dataset_name, True, path=str(cache_path),
            message=f"Fetched {size_mb:.1f} MB from ArcGIS REST")

    except Exception as e:
        return FetchResult(dataset_name, False,
            message=f"ArcGIS fetch failed: {e}")


# Fetcher dispatch
FETCHERS = {
    "local": fetch_local,
    "url": fetch_url,
    "api": lambda s, c, d: (
        fetch_socrata(s, c, d) if s.get("provider") == "socrata"
        else fetch_arcgis_rest(s, c, d) if s.get("provider") == "arcgis_rest"
        else FetchResult(d, False, message=f"Unknown API provider: {s.get('provider')}")
    ),
    "manual": lambda s, c, d: FetchResult(d, False,
        message="Manual acquisition required. See source.notes in manifest.",
        warnings=[{"level": "info", "primitive": "fetch_dataset",
                   "message": f"Dataset '{d}' requires manual acquisition: {s.get('notes', '')}"}]),
    "earthengine": lambda s, c, d: FetchResult(d, False,
        message="Earth Engine export not yet implemented. Export manually and set source.type to 'local'.",
        warnings=[{"level": "warning", "primitive": "fetch_dataset",
                   "message": f"Dataset '{d}' requires Earth Engine. Export and place at cache path."}]),
}


# === Main Logic ===

def should_fetch(dataset: dict, cache_path: Path, force: bool = False) -> tuple[bool, str]:
    """Determine whether a dataset needs fetching."""
    if force:
        return True, "forced refresh"

    if not cache_path.exists():
        return True, "not cached"

    # Check refresh policy
    cache_config = dataset.get("cache", {})
    policy = cache_config.get("refresh_policy", "manual")

    if policy == "always":
        return True, "refresh_policy: always"

    if policy in ("daily", "weekly"):
        max_age = cache_config.get("max_age_days",
                                   1 if policy == "daily" else 7)
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime, tz=timezone.utc)
        age_days = (datetime.now(timezone.utc) - mtime).days
        if age_days >= max_age:
            return True, f"cache is {age_days} days old (max: {max_age})"

    return False, "cached and fresh"


def fetch_all(
    manifest_path: str | Path,
    dataset_names: list[str] | None = None,
    force: bool = False
) -> dict[str, FetchResult]:
    """
    Fetch all (or specified) datasets from a manifest.

    Args:
        manifest_path: Path to manifest YAML
        dataset_names: Specific datasets to fetch (None = all available)
        force: Re-fetch even if cached

    Returns:
        Dict of dataset_name -> FetchResult
    """
    manifest_path = Path(manifest_path)
    plot_dir = manifest_path.parent

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    datasets = manifest.get("datasets", {})
    results = {}

    for name, config in datasets.items():
        # Skip if not in requested list
        if dataset_names and name not in dataset_names:
            continue

        # Skip unavailable datasets
        if not config.get("available", False):
            results[name] = FetchResult(name, False,
                message="Marked as unavailable in manifest.")
            continue

        # Resolve source and cache
        source = config.get("source", {})
        source_type = source.get("type", "local")

        cache_config = config.get("cache", {})
        cache_rel = cache_config.get("path", f".data/{name}")
        cache_path = plot_dir / cache_rel

        # Check if fetch needed
        needed, reason = should_fetch(config, cache_path, force)
        if not needed:
            results[name] = FetchResult(name, True, path=str(cache_path),
                message=f"Using cached data ({reason}).")
            logger.info(f"  {name}: cached ({reason})")
            continue

        # Dispatch to fetcher
        fetcher = FETCHERS.get(source_type)
        if fetcher is None:
            results[name] = FetchResult(name, False,
                message=f"Unknown source type: {source_type}")
            continue

        logger.info(f"  {name}: fetching ({reason})")
        result = fetcher(source, cache_path, name)
        results[name] = result

        # Update cache timestamp in manifest if successful
        if result.success:
            if "cache" not in config:
                config["cache"] = {}
            config["cache"]["fetched_at"] = datetime.now(timezone.utc).isoformat()
            config["cache"]["path"] = cache_rel

    # Write updated manifest (with fetched_at timestamps)
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    return results


# === CLI ===

def main():
    parser = argparse.ArgumentParser(
        description="Fetch datasets declared in a city manifest.")
    parser.add_argument("manifest", help="Path to manifest YAML")
    parser.add_argument("--datasets", nargs="*",
        help="Specific datasets to fetch (default: all)")
    parser.add_argument("--force", action="store_true",
        help="Re-fetch even if cached")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s")

    logger.info(f"Fetching datasets from {args.manifest}")

    results = fetch_all(args.manifest, args.datasets, args.force)

    # Summary
    logger.info("\n--- Fetch Summary ---")
    success = sum(1 for r in results.values() if r.success)
    failed = sum(1 for r in results.values() if not r.success)

    for name, result in results.items():
        status = "OK" if result.success else "FAILED"
        logger.info(f"  [{status}] {name}: {result.message}")

    logger.info(f"\n{success} succeeded, {failed} failed, "
                f"{len(results)} total.")

    # Print warnings as JSON for integration with envelope system
    all_warnings = []
    for result in results.values():
        all_warnings.extend(result.warnings)

    if all_warnings:
        print(json.dumps({"warnings": all_warnings}))

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()