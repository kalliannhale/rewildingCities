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
    """
    Parse a plot's manifest. Loads ALL datasets, including incomplete ones.

    The single reader for both halves of the system. It does NOT invent
    values a manifest never declared: the old defaults turned a dataset with
    no `format` into a geojson and a dataset with no `cache.path` into
    `.data/<name>.geojson`, so a raster that forgot to say so was silently
    looked for under the wrong name. A missing declaration is recorded in
    `underspecified` instead, which keeps the dataset visible to a reader
    that wants to report the gap while making it unusable to one that would
    act on it.

    Plot identity stays lenient, because it can be: a manifest may name
    itself under `city`, or `plot`, or simply by living in a directory. That
    is a real convenience rather than a guess about data. P-01.
    """
    path = Path(path)
    with open(path, 'r') as f:
        data = yaml.safe_load(f) or {}

    datasets = {}
    for name, ds_data in (data.get("datasets") or {}).items():
        ds_data = ds_data or {}
        cache_config = ds_data.get("cache") or {}
        cache_path = cache_config.get("path")
        semantic_type = ds_data.get("semantic_type")
        fmt = ds_data.get("format")

        missing = []
        if not semantic_type:
            missing.append("semantic_type ~ a holding must name what it is")
        if not fmt:
            missing.append("format ~ never assumed; a raster is not a geojson")
        if not cache_path:
            missing.append("cache.path ~ where the data rests once acquired")

        datasets[name] = ManifestDataset(
            name=name, path=cache_path,
            semantic_type=semantic_type,
            format=fmt,
            available=ds_data.get("available", False),
            source=ds_data.get("source"),
            cache=cache_config or None,
            description=ds_data.get("description", ""),
            temporal=ds_data.get("temporal"),
            quality=ds_data.get("quality"),
            provenance=ds_data.get("provenance"),
            classification=ds_data.get("classification"),
            underspecified=missing,
        )

    # a manifest may name itself three ways; the directory is a fair last word
    city = data.get("city") or {}
    plot_id = city.get("id") or data.get("plot") or path.parent.name
    plot_name = city.get("name") or plot_id

    crs_data = data.get("crs") or {}
    gee_data = data.get("gee") or {}
    return Manifest(
        city_name=plot_name, city_id=plot_id,
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
