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

    ITEM_API = "https://www.arcgis.com/sharing/rest/content/items"

    def resolve_item(self, item_id: str, timeout: int = 30) -> tuple[str | None, str]:
        """
        An ArcGIS ITEM ID is the durable identifier; a FeatureServer URL is a
        derived, re-mintable address. A service republished under a new name
        keeps its item id and loses its url, so a manifest that declares the
        url records a transient state rather than an identity ~ the same
        mistake as declaring 'lst_checked' instead of the canonical type.

        So: declare the item, resolve the url at acquisition, and report which
        url it resolved to, so provenance records the address actually used. ~
        """
        import requests

        url = f"{self.ITEM_API}/{item_id}"
        resp = requests.get(url, params={"f": "json"}, timeout=timeout)
        resp.raise_for_status()
        doc = resp.json()
        if doc.get("error"):
            return None, f"item {item_id}: {doc['error'].get('message', 'unknown error')}"
        service_url = doc.get("url")
        if not service_url:
            return None, (f"item {item_id} ('{doc.get('title')}') is a "
                          f"{doc.get('type')} and carries no service url")
        return service_url, f"resolved item {item_id} -> {service_url}"

    def resolve_layer(self, service_url: str, declared_layer, timeout: int = 30):
        """
        Which layer of the service. A declared index wins. Otherwise: exactly
        one layer means there is nothing to choose, and more than one is a
        CHOICE, so it is named and refused rather than guessed ~ picking the
        first would silently decide which boundaries an analysis uses. ~
        """
        import requests

        if declared_layer is not None:
            return int(declared_layer), None, []

        resp = requests.get(f"{service_url.rstrip('/')}", params={"f": "json"},
                            timeout=timeout)
        resp.raise_for_status()
        doc = resp.json()
        layers = doc.get("layers") or []
        max_records = doc.get("maxRecordCount")

        if len(layers) == 1:
            return int(layers[0]["id"]), max_records, []
        if not layers:
            return None, max_records, ["service exposes no layers"]
        listed = ", ".join(f"{l['id']}={l.get('name')}" for l in layers)
        return None, max_records, [
            f"service exposes {len(layers)} layers and none was declared; "
            f"add `layer:` to the source. available: {listed}"]

    def acquire(self, source_config, cache_path, dataset_name, **kwargs):
        import requests

        notes: list[str] = []
        endpoint = source_config.get("endpoint", "")
        item_id = source_config.get("item_id")

        if not endpoint and item_id:
            try:
                endpoint, note = self.resolve_item(item_id)
            except Exception as e:
                return AcquisitionResult(
                    dataset_name=dataset_name, success=False,
                    message=f"could not resolve ArcGIS item {item_id}: {e}")
            if endpoint is None:
                return AcquisitionResult(dataset_name=dataset_name,
                                         success=False, message=note)
            notes.append(note)

        if not endpoint:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message="ArcGIS source declares neither 'endpoint' nor 'item_id'.",
            )

        qp = source_config.get("query_params", {})

        # a layer index may already be on the endpoint (.../FeatureServer/1)
        tail = endpoint.rstrip("/").rsplit("/", 1)[-1]
        if not tail.isdigit():
            try:
                layer, max_records, problems = self.resolve_layer(
                    endpoint, source_config.get("layer"))
            except Exception as e:
                return AcquisitionResult(
                    dataset_name=dataset_name, success=False,
                    message=f"could not read ArcGIS service {endpoint}: {e}")
            if problems:
                return AcquisitionResult(dataset_name=dataset_name, success=False,
                                         message="; ".join(problems))
            endpoint = f"{endpoint.rstrip('/')}/{layer}"
            notes.append(f"using layer {layer}"
                         + (f" (service maxRecordCount {max_records})"
                            if max_records else ""))

        query_url = f"{endpoint.rstrip('/')}/query"

        # A FeatureServer enforces its OWN maxRecordCount whatever we ask for,
        # and flags a truncated response with exceededTransferLimit. The old
        # request asked for 10000, ignored that flag, and wrote a partial
        # feature set to disk as though it were the whole layer ~ a silent
        # truncation that every downstream count would inherit. So: page, and
        # refuse to write a file we know is incomplete.
        page_size = int(qp.get("limit", 2000))
        features: list = []
        payload: dict | None = None
        offset = 0

        try:
            while True:
                params = {
                    "where": qp.get("where", "1=1"),
                    "outFields": qp.get("outFields", "*"),
                    "outSR": qp.get("outSR", 4326),
                    "f": "geojson",
                    "resultRecordCount": page_size,
                    "resultOffset": offset,
                }
                # Sprint 04: any other declared query parameter passes through
                # unchanged, so a source can ask for attributes without
                # geometry (returnGeometry: false) or select by a bounding box
                # (geometry, geometryType, inSR, spatialRel) rather than by name.
                params.update({k: v for k, v in qp.items()
                               if k not in ("where", "outFields", "outSR", "limit")})
                logger.info(f"  ArcGIS REST: {query_url[:70]}... offset={offset}")
                resp = requests.get(query_url, params=params, timeout=180)
                resp.raise_for_status()
                doc = resp.json()

                if doc.get("error"):
                    return AcquisitionResult(
                        dataset_name=dataset_name, success=False,
                        message=f"ArcGIS returned an error: "
                                f"{doc['error'].get('message', doc['error'])}")

                page = doc.get("features") or []
                if payload is None:
                    payload = {k: v for k, v in doc.items()
                               if k not in ("features", "exceededTransferLimit")}
                features.extend(page)

                # exceededTransferLimit is an Esri-JSON field and the GeoJSON
                # serialization DROPS it, so a flag-based guard never fires for
                # the format we request ~ which is how a 2000-feature page got
                # written as a complete 16-county layer. the honest test needs
                # no flag: a page that comes back exactly page_size long may
                # have more behind it. stop only when a page is SHORT.
                if not page or len(page) < page_size:
                    break
                offset += len(page)
                if offset > 500_000:
                    return AcquisitionResult(
                        dataset_name=dataset_name, success=False,
                        message=(f"stopped after {offset} features; a layer this "
                                 f"large wants a bbox or a where clause, not a "
                                 f"full fetch"))

            payload = payload or {"type": "FeatureCollection"}
            payload["features"] = features

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(payload, f)

            size = cache_path.stat().st_size
            pages = offset // page_size + 1 if offset else 1
            notes.append(f"{len(features)} features in {pages} page(s)")
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=True,
                path=str(cache_path),
                size_bytes=size,
                message=f"Fetched {size / 1024 / 1024:.1f} MB from ArcGIS REST "
                        f"~ " + "; ".join(notes),
            )
        except Exception as e:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=f"ArcGIS fetch failed: {e}",
            )
