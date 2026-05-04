"""
canopy/providers/arcgis.py

ArcGIS REST Feature Server provider.
Wraps the fetch logic from soil/register/fetch_dataset.py.
"""

import json
import logging
from pathlib import Path

from .base import Provider, AcquisitionResult

logger = logging.getLogger("providers.arcgis")


class ArcGISProvider(Provider):
    """Acquires data from ArcGIS REST Feature Servers."""

    @property
    def name(self) -> str:
        return "ArcGIS REST"

    def can_handle(self, source_config: dict) -> bool:
        return (
            source_config.get("type") == "api"
            and source_config.get("provider") == "arcgis_rest"
        )

    def acquire(self, source_config, cache_path, dataset_name, **kwargs):
        import requests

        endpoint = source_config.get("endpoint", "")
        if not endpoint:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message="ArcGIS source missing 'endpoint' field.",
            )

        query_url = f"{endpoint.rstrip('/')}/query"
        qp = source_config.get("query_params", {})
        params = {
            "where": qp.get("where", "1=1"),
            "outFields": qp.get("outFields", "*"),
            "f": "geojson",
            "resultRecordCount": qp.get("limit", 10000),
        }

        try:
            logger.info(f"  Fetching from ArcGIS REST: {query_url[:70]}...")
            resp = requests.get(query_url, params=params, timeout=120)
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
                message=f"Fetched {size / 1024 / 1024:.1f} MB from ArcGIS REST",
            )
        except Exception as e:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=f"ArcGIS fetch failed: {e}",
            )
