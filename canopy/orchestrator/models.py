"""Data structures for the orchestrator: manifests, experiments, methods,
step definitions, primitives, and results.

Split from orchestrator.py during Sprint 6 refactor. Pure data, no logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..envelope import Envelope


@dataclass
class ManifestDataset:
    """
    A dataset declared in a manifest.

    One model, read by both halves of the system. The orchestrator needs its
    richness (source, availability, provenance); loam needs its strictness
    (a holding that does not declare what it is cannot be planted). Two
    separate readers used to supply one each: parse_manifest invented
    defaults a dataset never declared, and plant_manifest refused the same
    dataset outright. The same file yielded two different pictures of
    itself. P-01.

    `underspecified` carries the reasons a declaration is unusable, so a
    dataset stays visible to the reader that wants to REPORT the gap while
    remaining unusable to the one that would act on it. Declared-and-
    incomplete is a real state and deserves a name, rather than being
    papered over with a default or dropped on the floor.
    """
    name: str
    path: str | None
    semantic_type: str | None
    format: str | None
    available: bool = False
    source: dict | None = None
    cache: dict | None = None
    description: str = ""
    temporal: dict | None = None
    quality: dict | None = None
    provenance: dict | None = None
    # the declared classification scheme, which parse_manifest used to drop
    # entirely while plant_manifest read it as conformed_by. the orchestrator
    # cannot crosswalk a scheme it cannot see.
    classification: dict | None = None
    # why this declaration cannot be used, if it cannot. empty means usable.
    underspecified: list[str] = field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        """A complete declaration ~ nothing was guessed on its behalf."""
        return not self.underspecified

    @property
    def classification_scheme(self) -> str | None:
        if not self.classification:
            return None
        return self.classification.get("scheme")

    @property
    def source_type(self) -> str | None:
        if self.source is None:
            return None
        return self.source.get("type")

    @property
    def provider_name(self) -> str | None:
        if self.source is None:
            return None
        return self.source.get("provider")

    @property
    def is_auto_acquirable(self) -> bool:
        if self.source is None:
            return False
        return self.source_type in ("api", "url", "local", "stac", "s3")

    @property
    def requires_auth(self) -> bool:
        if self.source is None:
            return False
        auth = self.source.get("auth", {})
        return auth.get("type", "none") != "none" or self.source_type == "earthengine"

    @property
    def requires_manual_action(self) -> bool:
        return self.source_type in ("manual",)


@dataclass
class ManifestInconsistency:
    """A detected inconsistency in the manifest's state."""
    dataset_name: str
    issue: str
    path: str
    suggestion: str


@dataclass
class Manifest:
    """A parsed city manifest."""
    city_name: str
    city_id: str
    datasets: dict[str, ManifestDataset]
    data_dir: Path
    manifest_path: Path | None = None
    crs_working: str = ""
    gee_project: str | None = None
    raw: dict = field(default_factory=dict)

    def available_datasets(self) -> dict[str, ManifestDataset]:
        return {k: v for k, v in self.datasets.items() if v.available}

    def unavailable_datasets(self) -> dict[str, ManifestDataset]:
        return {k: v for k, v in self.datasets.items() if not v.available}

    def acquirable_datasets(self) -> dict[str, ManifestDataset]:
        return {k: v for k, v in self.datasets.items()
                if not v.available and v.is_auto_acquirable}

    def datasets_by_semantic_type(self, semantic_type: str) -> list[ManifestDataset]:
        return [ds for ds in self.datasets.values()
                if ds.semantic_type == semantic_type]

    def check_consistency(self) -> list[ManifestInconsistency]:
        issues = []
        for name, ds in self.datasets.items():
            full_path = self.data_dir / ds.path
            if ds.available and not full_path.exists():
                issues.append(ManifestInconsistency(
                    dataset_name=name, issue="available_but_missing",
                    path=str(full_path),
                    suggestion=f"File not found at {ds.path}. Either acquire the data or set available: false."
                ))
            if not ds.available and full_path.exists():
                issues.append(ManifestInconsistency(
                    dataset_name=name, issue="file_exists_but_unavailable",
                    path=str(full_path),
                    suggestion=f"File exists at {ds.path} but manifest says unavailable. Set available: true if ready."
                ))
        return issues


@dataclass
class StepDefinition:
    """A step in an experiment."""
    id: str
    primitive: str
    version: str
    description: str
    inputs: dict[str, str]
    outputs: dict[str, str]
    params: dict[str, Any]


RUN_KINDS = ("experiment", "preparation")


@dataclass
class Lineage:
    """Scientific lineage — where this run comes from.

    kind is "experiment" (answers a curiosity) or "preparation" (readies data
    and answers none, D-98). A preparation has no curiosity at all, so
    curiosity_ref is None for it, never "": an empty string would still read
    as "a question, unknown"."""
    curiosity_ref: str | None
    sub_question: str | None
    method_ref: str
    choices: dict[str, Any]
    kind: str = "experiment"


@dataclass
class Experiment:
    """A parsed experiment."""
    id: str
    name: str
    description: str
    lineage: Lineage
    city: str
    manifest_path: str
    choices: dict[str, Any]
    parameters: dict[str, Any]
    steps: list[StepDefinition]


@dataclass
class PrimitiveSpec:
    """A primitive's specification from a registry."""
    name: str
    path: str
    version: str
    inputs: list[dict]
    outputs: dict
    params: dict
    passthrough: bool = False


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_id: str
    success: bool
    envelope: Envelope | None
    output_paths: dict[str, str]
    error: str | None = None
    message: str | None = None


@dataclass
class OrchestrationResult:
    """Result of executing a full experiment."""
    success: bool
    completed_steps: list[str]
    failed_step: str | None
    step_results: dict[str, StepResult]
    final_envelopes: dict[str, Envelope]
    lineage: Lineage | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    # the failing step's detailed diagnosis, carried up so the CLI and the
    # run log can say WHAT failed and not merely THAT it failed.
    message: str | None = None


@dataclass
class MethodChoice:
    """A choice declared in a method file."""
    name: str
    options: list[Any]
    description: str = ""


@dataclass
class Method:
    """A parsed method file. kind says which kind of run may use it (D-98)."""
    id: str
    name: str
    choices: dict[str, MethodChoice]
    kind: str = "experiment"


@dataclass
class MethodIndexEntry:
    """A method's entry in garden/methods/index.yml.

    The index is the authoritative router from method id to file path.
    Read at experiment-time by Orchestrator._resolve_method_path and at
    catalog-time by the future discover/methods endpoint.
    """
    id: str
    domain: str
    path: str
    name: str
    answers: list[str]
    raw: dict
