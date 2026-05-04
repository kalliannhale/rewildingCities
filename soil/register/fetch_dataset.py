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
        # Use a single large request with streaming to handle big responses.
        # Socrata SODA 2.0 supports $limit up to 50,000 in one request.
        # We stream directly to disk so we don't hold everything in memory.
        # Ensure $limit is set — default to 50000 if not in manifest query_params
        if "$limit" not in params:
            params["$limit"] = 50000
        limit = params["$limit"]

        logger.info(f"  Fetching {dataset_name} from Socrata (limit={limit}): {endpoint}")

        resp = requests.get(endpoint, params=params, timeout=300, stream=True)
        resp.raise_for_status()

        # Stream response to disk
        bytes_written = 0
        with open(cache_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
                bytes_written += len(chunk)
                # Progress indicator every 5MB
                if bytes_written % (5 * 1024 * 1024) < 65536:
                    logger.info(f"    Downloaded {bytes_written / (1024*1024):.1f} MB...")

        size_mb = cache_path.stat().st_size / (1024 * 1024)
        logger.info(f"    Total: {size_mb:.1f} MB")

        # Count features if GeoJSON
        n_features = "unknown"
        if is_geojson and size_mb < 500:
            try:
                with open(cache_path) as f:
                    data = json.load(f)
                if isinstance(data, dict) and "features" in data:
                    n_features = len(data["features"])
                elif isinstance(data, list):
                    n_features = len(data)
            except Exception:
                pass

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

    # Write fetch metadata to a SEPARATE file — never rewrite the manifest.
    # The manifest is a carefully authored document. We don't touch it.
    fetch_log_path = plot_dir / ".data" / "fetch_log.yml"
    fetch_log = {}
    if fetch_log_path.exists():
        with open(fetch_log_path) as f:
            fetch_log = yaml.safe_load(f) or {}

    for name, result in results.items():
        if result.success:
            fetch_log[name] = {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "path": result.path,
                "message": result.message
            }

    fetch_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(fetch_log_path, "w") as f:
        yaml.dump(fetch_log, f, default_flow_style=False, sort_keys=False)

    # Update 'available' flags in manifest for successful downloads
    try:
        from soil.register.manifest_utils import set_multiple_available
        updates = {name: result.success for name, result in results.items()}
        set_multiple_available(manifest_path, updates)
    except ImportError:
        pass  # manifest_utils not yet available — skip silently

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