"""Parsers for manifest, experiment, and method YAML files.

Split from orchestrator.py during Sprint 6 refactor. Pure functions —
read a path, return a dataclass.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import (
    Lineage,
    Manifest,
    ManifestDataset,
    Method,
    MethodChoice,
    Experiment,
    StepDefinition,
)


def parse_manifest(path: str | Path) -> Manifest:
    """Parse a city manifest YAML file. Loads ALL datasets."""
    path = Path(path)
    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    datasets = {}
    for name, ds_data in data.get("datasets", {}).items():
        cache_config = ds_data.get("cache", {})
        cache_path = cache_config.get("path", f".data/{name}.geojson")
        datasets[name] = ManifestDataset(
            name=name, path=cache_path,
            semantic_type=ds_data.get("semantic_type", name),
            format=ds_data.get("format", "geojson"),
            available=ds_data.get("available", False),
            source=ds_data.get("source"),
            cache=cache_config if cache_config else None,
            description=ds_data.get("description", ""),
            temporal=ds_data.get("temporal"),
            quality=ds_data.get("quality"),
            provenance=ds_data.get("provenance"),
        )

    crs_data = data.get("crs", {})
    gee_data = data.get("gee", {})
    return Manifest(
        city_name=data["city"]["name"], city_id=data["city"]["id"],
        datasets=datasets, data_dir=path.parent, manifest_path=path,
        crs_working=crs_data.get("working", ""),
        gee_project=gee_data.get("project"), raw=data,
    )


def parse_experiment(path: str | Path) -> Experiment:
    """Parse an experiment YAML file."""
    path = Path(path)
    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    curiosity_data = data.get("curiosity", {})
    method_data = data.get("method", {})
    lineage = Lineage(
        curiosity_ref=curiosity_data.get("ref", ""),
        sub_question=curiosity_data.get("sub_question"),
        method_ref=method_data.get("ref", ""),
        choices=data.get("choices", {})
    )

    steps = []
    for step_data in data.get("steps", []):
        steps.append(StepDefinition(
            id=step_data["id"], primitive=step_data["primitive"],
            version=step_data.get("version", "1.0.0"),
            description=step_data.get("description", ""),
            inputs=step_data.get("inputs", {}),
            outputs=step_data.get("outputs", {}),
            params=step_data.get("params", {})
        ))

    return Experiment(
        id=data["id"], name=data["name"],
        description=data.get("description", ""),
        lineage=lineage, city=data["city"],
        manifest_path=data["manifest"],
        choices=data.get("choices", {}),
        parameters=data.get("parameters", {}),
        steps=steps
    )


def parse_method(path: str | Path) -> Method:
    """Parse a method YAML file."""
    path = Path(path)
    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    choices = {}
    for name, choice_data in data.get("choices", {}).items():
        choices[name] = MethodChoice(
            name=name,
            options=choice_data.get("options", []),
            description=choice_data.get("description", "")
        )

    return Method(
        id=data.get("id", path.stem),
        name=data.get("name", path.stem),
        choices=choices
    )
