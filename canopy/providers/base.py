"""
canopy/providers/base.py

Provider base class, registry, result types, and simple providers
(Local, URL, Manual).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import shutil
import logging

logger = logging.getLogger("providers")


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AcquisitionResult:
    """Result of acquiring a single dataset."""
    dataset_name: str
    success: bool
    path: str | None = None
    size_bytes: int | None = None
    message: str = ""
    warnings: list[dict] = field(default_factory=list)
    requires_auth: bool = False
    auth_instructions: str | None = None
    requires_manual: bool = False
    manual_instructions: str | None = None


@dataclass
class DiscoveryResult:
    """Result of discovering an available dataset for a territory."""
    semantic_type: str
    description: str
    source_config: dict
    estimated_size: str | None = None
    requires_auth: bool = False
    quality_notes: str | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER BASE
# ═══════════════════════════════════════════════════════════════════════════════

class Provider(ABC):
    """Base class for data providers.
    
    Each provider knows one protocol and implements:
      - can_handle(): whether it handles a given source config
      - acquire(): download data to a cache path
      - discover(): find available datasets for a bounding box (optional)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def can_handle(self, source_config: dict) -> bool:
        ...

    @abstractmethod
    def acquire(
        self,
        source_config: dict,
        cache_path: Path,
        dataset_name: str,
        **kwargs
    ) -> AcquisitionResult:
        ...

    def discover(
        self,
        bbox: tuple[float, float, float, float],
        semantic_types: list[str] | None = None,
        **kwargs
    ) -> list[DiscoveryResult]:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class ProviderRegistry:
    """Dispatches acquisition to the right provider."""

    def __init__(self):
        self._providers: list[Provider] = []

    def register(self, provider: Provider) -> None:
        self._providers.append(provider)
        logger.debug(f"Registered provider: {provider.name}")

    def find_provider(self, source_config: dict) -> Provider | None:
        for provider in self._providers:
            if provider.can_handle(source_config):
                return provider
        return None

    def acquire(
        self,
        source_config: dict,
        cache_path: Path,
        dataset_name: str,
        **kwargs
    ) -> AcquisitionResult:
        provider = self.find_provider(source_config)

        if provider is None:
            source_type = source_config.get("type", "unknown")
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=(
                    f"No provider registered for source type '{source_type}'. "
                    f"Dataset '{dataset_name}' cannot be auto-acquired."
                ),
            )

        logger.info(f"Acquiring '{dataset_name}' via {provider.name}...")
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = provider.acquire(source_config, cache_path, dataset_name, **kwargs)
        except Exception as e:
            result = AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=f"Provider '{provider.name}' error: {e}",
                warnings=[{
                    "level": "critical",
                    "primitive": "provider_registry",
                    "message": f"Acquisition failed for '{dataset_name}': {e}"
                }],
            )

        if result.success:
            logger.info(f"  ✓ {dataset_name}: {result.message}")
        else:
            logger.warning(f"  ✗ {dataset_name}: {result.message}")

        return result

    def discover_all(
        self,
        bbox: tuple[float, float, float, float],
        semantic_types: list[str] | None = None,
        **kwargs
    ) -> list[DiscoveryResult]:
        results = []
        for provider in self._providers:
            try:
                found = provider.discover(bbox, semantic_types, **kwargs)
                results.extend(found)
            except Exception as e:
                logger.warning(f"Discovery failed for {provider.name}: {e}")
        return results

    @property
    def registered_providers(self) -> list[str]:
        return [p.name for p in self._providers]


# ═══════════════════════════════════════════════════════════════════════════════
# SIMPLE PROVIDERS
# ═══════════════════════════════════════════════════════════════════════════════

class LocalProvider(Provider):
    """Handles datasets already on disk (source.type: local)."""

    @property
    def name(self) -> str:
        return "Local"

    def can_handle(self, source_config: dict) -> bool:
        return source_config.get("type") == "local"

    def acquire(self, source_config, cache_path, dataset_name, **kwargs):
        source_path = Path(source_config.get("path", ""))
        if not source_path.exists():
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=f"Local source not found: {source_path}",
            )
        if source_path.resolve() != cache_path.resolve():
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, cache_path)
        size = cache_path.stat().st_size
        return AcquisitionResult(
            dataset_name=dataset_name,
            success=True,
            path=str(cache_path),
            size_bytes=size,
            message=f"Copied from {source_path} ({size / 1024 / 1024:.1f} MB)",
        )


class URLProvider(Provider):
    """Handles direct URL downloads (source.type: url)."""

    @property
    def name(self) -> str:
        return "URL"

    def can_handle(self, source_config: dict) -> bool:
        return source_config.get("type") == "url"

    def acquire(self, source_config, cache_path, dataset_name, **kwargs):
        import requests

        url = source_config.get("url", "")
        if not url:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message="URL source has no 'url' field.",
            )
        try:
            logger.info(f"  Downloading from {url[:80]}...")
            resp = requests.get(url, stream=True, timeout=300)
            resp.raise_for_status()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            size = cache_path.stat().st_size
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=True,
                path=str(cache_path),
                size_bytes=size,
                message=f"Downloaded {size / 1024 / 1024:.1f} MB",
            )
        except Exception as e:
            return AcquisitionResult(
                dataset_name=dataset_name,
                success=False,
                message=f"URL download failed: {e}",
            )


class ManualProvider(Provider):
    """Advisory-only provider for datasets requiring manual acquisition."""

    @property
    def name(self) -> str:
        return "Manual"

    def can_handle(self, source_config: dict) -> bool:
        return source_config.get("type") == "manual"

    def acquire(self, source_config, cache_path, dataset_name, **kwargs):
        notes = source_config.get("notes", "No instructions provided.")
        return AcquisitionResult(
            dataset_name=dataset_name,
            success=False,
            message=f"Manual acquisition required for '{dataset_name}'.",
            requires_manual=True,
            manual_instructions=notes,
            warnings=[{
                "level": "info",
                "primitive": "manual_provider",
                "message": f"Manual acquisition needed: {notes}"
            }],
        )
