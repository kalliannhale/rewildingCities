"""Parsers for manifest, experiment, and method YAML files.

Split from orchestrator.py during Sprint 6 refactor. Pure functions —
read a path, return a dataclass.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from .models import (
    RUN_KINDS,
    Lineage,
    Manifest,
    ManifestDataset,
    Method,
    MethodChoice,
    Experiment,
    StepDefinition,
)


# words a dataset's declaration may no longer use, each with the word that
# replaced it and why. a retired word makes only that dataset unusable, never
# the whole plot, so a community plot written against older docs still opens
# and says what to change (NAME-4).
RETIRED_DECLARATIONS = {
    ("provenance", "authority"): (
        "provenance.published_by",
        "a source's publisher is provenance.published_by; `authority` means "
        "only who assigns a place's code (D-186, D-187, NAME-4)"),
}


def declaration_problems(spec: dict | None) -> list[str]:
    """what a dataset's declaration says in words this system has retired.

    one rule for every reader of a manifest: parse_manifest records these as
    underspecified, and compose refuses a source that has them, so no reader
    reads a retired word as if it still meant something. ~"""
    problems = []
    for (block, word), (now, why) in RETIRED_DECLARATIONS.items():
        held = (spec or {}).get(block)
        if isinstance(held, dict) and word in held:
            problems.append(f"{block}.{word} ~ write {now}: {why}")
    return problems


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
        missing.extend(declaration_problems(ds_data))

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
        places=data.get("places"),
    )


def _run_kind(value, path) -> str:
    """the declared kind of a run or method, refusing anything but the two
    known kinds. omitted means experiment, the only kind that existed before
    D-98, so every older file reads as it always did."""
    if value is None:
        return "experiment"
    if value not in RUN_KINDS:
        raise ValueError(
            f"{path}: kind must be one of {', '.join(RUN_KINDS)}; got {value!r}")
    return value


def parse_experiment(path: str | Path) -> Experiment:
    """Parse an experiment YAML file."""
    path = Path(path)
    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    kind = _run_kind(data.get("kind"), path)
    method_data = data.get("method", {})
    curiosity_data = data.get("curiosity")
    if kind == "preparation" and curiosity_data is None:
        # a preparation names no question, so it has no curiosity at all.
        curiosity_ref, sub_question = None, None
    else:
        # an experiment, or a preparation that names a curiosity anyway. the
        # latter is kept as written so validate() refuses it by name rather
        # than it vanishing here.
        curiosity_data = curiosity_data or {}
        curiosity_ref = curiosity_data.get("ref", "")
        sub_question = curiosity_data.get("sub_question")
    lineage = Lineage(
        curiosity_ref=curiosity_ref,
        sub_question=sub_question,
        method_ref=method_data.get("ref", ""),
        choices=data.get("choices", {}),
        kind=kind,
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


# ── methods ──────────────────────────────────────────────────────────────────
# seeds/schemas/method.schema.yml is the one home of a method's shape (D-213).
# every reader of a method file comes through load_method_data, so no reader
# reads a shape the schema does not describe, and none reads a typo as absent.

METHOD_SCHEMA = Path("seeds") / "schemas" / "method.schema.yml"


class MethodShapeError(ValueError):
    """a method file the method schema does not describe. ~"""


@lru_cache(maxsize=None)
def _method_validator(project_root: str):
    import jsonschema
    with open(Path(project_root) / METHOD_SCHEMA, "r") as f:
        schema = yaml.safe_load(f)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def method_shape_problems(data, project_root: str | Path | None = None) -> list[str]:
    """every way a method's data departs from the method schema, one line
    each, ordered by where in the file it is. empty means the shape holds.

    the schema says what may be written; it cannot say that a default is one
    of its own options, so that rule is checked here too. ~"""
    if project_root is None:
        from canopy.paths import project_root as _resolve_root
        project_root = _resolve_root()
    if not isinstance(data, dict):
        return [f"a method is a mapping; this file holds {type(data).__name__}"]
    validator = _method_validator(str(project_root))
    problems = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path))):
        where = ".".join(str(p) for p in err.absolute_path) or "(top level)"
        problems.append(f"{where}: {err.message}")
    for name, choice in (data.get("choices") or {}).items():
        if not isinstance(choice, dict):
            continue
        options = choice.get("options")
        if isinstance(options, dict) and "default" in choice and choice["default"] not in options:
            problems.append(
                f"choices.{name}.default: {choice['default']!r} is not one of its "
                f"options ({', '.join(map(str, options))})")
    return problems


def load_method_data(path: str | Path, project_root: str | Path | None = None) -> dict:
    """read a method file and return it as written, or refuse it.

    a key written twice is refused (REG-5), and so is any shape the method
    schema does not describe, with every problem named at once. ~"""
    from .registry import UniqueKeyLoader
    path = Path(path)
    with open(path, "r") as f:
        data = yaml.load(f, Loader=UniqueKeyLoader)
    problems = method_shape_problems(data, project_root)
    if problems:
        raise MethodShapeError(
            f"{path} does not match {METHOD_SCHEMA} (D-213):\n  - "
            + "\n  - ".join(problems))
    return data


def parse_method(path: str | Path, project_root: str | Path | None = None) -> Method:
    """parse a method file into what a run is checked against.

    a choice's options are the keys of its options mapping, in order; a
    parametric choice has none. ~"""
    path = Path(path)
    data = load_method_data(path, project_root)

    choices = {}
    for name, choice_data in (data.get("choices") or {}).items():
        choices[name] = MethodChoice(
            name=name,
            options=list(choice_data.get("options") or {}),
            description=choice_data.get("description", ""),
        )

    return Method(
        id=data["id"],
        name=data["name"],
        choices=choices,
        kind=_run_kind(data.get("kind"), path),
    )
