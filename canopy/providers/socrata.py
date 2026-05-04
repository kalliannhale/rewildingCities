"""
canopy/providers/socrata.py

Socrata SODA 2.0 API provider.
Wraps the fetch logic from soil/register/fetch_dataset.py.
"""

import json
import logging
from pathlib import Path

from .base import Provider, AcquisitionResult

logger = logging.getLogger("providers.socrata")


class SocrataProvider(Provider):
    """Acquires data from Socrata open data portals (NYC, Chicago, etc.)."""

    @property
    def name(self) -> str:
        return "Socrata"

    def can_handle(self, source_config: dict) -> bool:
        return (
            source_config.get("type") == "api"
            and source_config.get("provider") == "socrata"
        )

    def acquire(self, source_config, cache_path, dataset_name, **kwargs):
        import requests

        endpoint = source_config.get("endpoint", "")
        if not endpoint:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message="Socrata source missing 'endpoint' field.",
            )

        params = dict(source_config.get("query_params", {}))

        try:
            logger.info(f"  Fetching from Socrata: {endpoint[:70]}...")
            resp = requests.get(endpoint, params=params, timeout=120)
            resp.raise_for_status()

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(resp.json(), f)

            size = cache_path.stat().st_size
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=True,
                path=str(cache_path),
                size_bytes=size,
                message=f"Fetched {size / 1024 / 1024:.1f} MB from Socrata",
            )
        except Exception as e:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=f"Socrata fetch failed: {e}",
            )
