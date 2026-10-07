"""
canopy/wonder/recipe.py

recipes ~ a method's own steps, filled at compose time from the question

a method that declares a `recipe:` says exactly how it is run. the curiosity
says what is being asked. compose brings the two together and writes the
result into the experiment as plain values, so a composed experiment is a
complete account of itself: read the file and you know what will run.

compose-time references, resolved here and never seen by the orchestrator:

  $requires.<name>           the manifest dataset bound to that requirement,
                             written as $manifest.<dataset>. one candidate
                             binds; several is a choice, refused with their
                             names unless the person chose; none leaves the
                             requirement visibly missing (the wide door)
  $curiosity.indicated_by    the chosen sub-question's indicators (or every
                             sub-question's, in order, if none was chosen),
                             written as [$indicators.<id>, ...], keeping only
                             those the bound indicator source can serve
  $weighting.<id>.components every indicator a weighting names, in declared
                             order, written as [$indicators.<id>, ...]
  $source.<fact>             a fact about the bound indicator source, read
                             from the manifest: authority, vintage,
                             unit_column, unit_pad, name_column

everything else, $choices, $parameters, $steps, $weights, $indicators and
literals, passes through untouched for the orchestrator to resolve at run
time. a parameter whose compose-time value is nothing is left out, so a
primitive's own default applies and the file does not claim a null.

an indicator the curiosity names but the source cannot serve is not dropped
in silence: it is returned as a note, with the dataset that could serve it,
so a second authority is one more compose away and never averaged in. ♡
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

SOURCE_TYPE = "indicator_source"
SOURCE_FACTS = ("authority", "vintage", "unit_column", "unit_pad", "name_column")

_REQUIRES = re.compile(r"^\$requires\.([a-zA-Z_][a-zA-Z0-9_]*)$")
_CURIOSITY = re.compile(r"^\$curiosity\.indicated_by$")
_WEIGHTING = re.compile(r"^\$weighting\.([a-zA-Z_][a-zA-Z0-9_]*)\.components$")
_SOURCE = re.compile(r"^\$source\.([a-zA-Z_][a-zA-Z0-9_]*)$")
_COMPOSE_PREFIXES = ("$requires.", "$curiosity.", "$weighting.", "$source.")


class ComposeRefusal(ValueError):
    """compose declines, naming the reason and what would let it proceed."""


@dataclass
class RecipeResult:
    steps: list[dict]
    binding: dict[str, str | None]
    source_dataset: str | None
    indicators: list[str]
    notes: list[str] = field(default_factory=list)


# ── binding requirements to datasets ──────────────────────────────────────
def _types_of(req: dict) -> list[str]:
    return req.get("semantic_types") or ([req["type"]] if req.get("type") else [])


def bind_requirements(method: dict, datasets: dict[str, dict],
                      chosen: dict[str, str] | None = None) -> dict[str, str | None]:
    """each requirement's dataset: chosen, or the only candidate, or none."""
    chosen = chosen or {}
    out: dict[str, str | None] = {}
    for req in method.get("requires_data") or []:
        name = req.get("name", "input")
        types = _types_of(req)
        candidates = sorted(n for n, s in datasets.items()
                            if (s or {}).get("semantic_type") in types)
        if name in chosen:
            if chosen[name] not in candidates:
                raise ComposeRefusal(
                    f"'{chosen[name]}' cannot serve requirement '{name}' "
                    f"({' or '.join(types)}). candidates here: "
                    f"{', '.join(candidates) or 'none'}")
            out[name] = chosen[name]
        elif len(candidates) == 1:
            out[name] = candidates[0]
        elif not candidates:
            out[name] = None
        else:
            raise ComposeRefusal(
                f"{len(candidates)} datasets could serve '{name}' "
                f"({' or '.join(types)}): {', '.join(candidates)}. which one is "
                f"a choice, not a lookup. name it, e.g. datasets="
                f"{{'{name}': '{candidates[0]}'}}")
    return out


# ── the indicator source ──────────────────────────────────────────────────
def serves(indicator, dataset_name: str, spec: dict) -> bool:
    """can this dataset supply this indicator? listed by the acquisition, or
    declared by the indicator as coming from this dataset."""
    listed = ((spec or {}).get("source") or {}).get("indicators") or []
    return indicator.id in listed or (indicator.source or {}).get("dataset") == dataset_name


def source_facts(dataset_name: str, spec: dict) -> dict:
    """what the bound source says about itself, for $source.<fact>."""
    src = (spec or {}).get("source") or {}
    prov = (spec or {}).get("provenance") or {}
    vintage = None
    if src.get("provider") == "census_acs" and src.get("year") and src.get("dataset"):
        from canopy.providers.census_acs import CensusACSProvider
        vintage = CensusACSProvider.vintage_window(src["dataset"], int(src["year"]))
    else:
        vintage = ((spec or {}).get("temporal") or {}).get("label") or src.get("edition")
    return {
        "authority": prov.get("authority"),
        "vintage": vintage,
        "unit_column": src.get("unit_column", "GEOID"),
        "unit_pad": src.get("unit_pad"),
        "name_column": src.get("name_column", "NAME"),
    }


def indicated(curiosity: dict, sub_question: str | None) -> list[str]:
    subs = curiosity.get("sub_questions") or {}
    if sub_question is not None:
        if sub_question not in subs:
            raise ComposeRefusal(
                f"no sub-question '{sub_question}' in '{curiosity.get('id')}'. "
                f"its sub-questions: {', '.join(subs)}")
        return list((subs[sub_question] or {}).get("indicated_by") or [])
    out: list[str] = []
    for s in subs.values():
        for i in (s or {}).get("indicated_by") or []:
            if i not in out:
                out.append(i)
    return out


# ── resolving one value ───────────────────────────────────────────────────
def _resolve(value, ctx: dict):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            r = _resolve(v, ctx)
            if r is not None:
                out[k] = r
        return out
    if isinstance(value, list):
        out = []
        for v in value:
            r = _resolve(v, ctx)
            if isinstance(v, str) and isinstance(r, list) and v.startswith(_COMPOSE_PREFIXES):
                out.extend(r)
            elif r is not None:
                out.append(r)
        return out
    if not isinstance(value, str) or not value.startswith(_COMPOSE_PREFIXES):
        return value

    if m := _REQUIRES.match(value):
        name = m.group(1)
        if name not in ctx["binding"]:
            raise ComposeRefusal(f"{value}: the method declares no requirement '{name}'")
        ds = ctx["binding"][name]
        return f"$manifest.{ds}" if ds else f"$manifest.{ctx['missing_label'][name]}"
    if _CURIOSITY.match(value):
        ctx["uses_curiosity"] = True
        return [f"$indicators.{i}" for i in ctx["indicators"]]
    if m := _WEIGHTING.match(value):
        return [f"$indicators.{i}" for i in ctx["weighting_components"](m.group(1))]
    if m := _SOURCE.match(value):
        fact = m.group(1)
        if fact not in SOURCE_FACTS:
            raise ComposeRefusal(f"{value}: known source facts are {', '.join(SOURCE_FACTS)}")
        if ctx["source"] is None:
            raise ComposeRefusal(f"{value}: the method requires no {SOURCE_TYPE}, so there is no source")
        return ctx["source"][fact]
    raise ComposeRefusal(f"{value}: not a compose-time reference this recipe language knows")


# ── composing a recipe ────────────────────────────────────────────────────
def compose_recipe(method: dict, curiosity: dict, sub_question: str | None,
                   datasets: dict[str, dict], indicator_registry,
                   weights_loader=None, chosen_datasets: dict | None = None) -> RecipeResult:
    recipe = method.get("recipe")
    if not isinstance(recipe, list) or not recipe:
        raise ComposeRefusal(f"method '{method.get('id')}' declares no recipe")

    binding = bind_requirements(method, datasets, chosen_datasets)
    missing_label = {req.get("name", "input"): (_types_of(req) or [req.get("name", "input")])[0]
                     for req in method.get("requires_data") or []}

    source_req = next((req.get("name", "input") for req in method.get("requires_data") or []
                       if SOURCE_TYPE in _types_of(req)), None)
    source_ds = binding.get(source_req) if source_req else None
    source = source_facts(source_ds, datasets[source_ds]) if source_ds else None

    notes: list[str] = []
    wanted = indicated(curiosity, sub_question)
    served: list[str] = []
    for iid in wanted:
        try:
            ind = indicator_registry.get(iid)
        except KeyError:
            raise ComposeRefusal(f"the curiosity names '{iid}', which the indicator registry does not declare")
        if source_ds and serves(ind, source_ds, datasets[source_ds]):
            served.append(iid)
        else:
            others = sorted(n for n, s in datasets.items()
                            if (s or {}).get("semantic_type") == SOURCE_TYPE and serves(ind, n, s))
            where = (f"served by {', '.join(others)}; compose again with "
                     f"datasets={{'{source_req}': '{others[0]}'}} to set it beside this one"
                     if others else "no dataset here serves it yet")
            notes.append(f"also answered by {iid} ({ind.defined_by}): {where}")

    def components(wid: str) -> list[str]:
        if weights_loader is None:
            raise ComposeRefusal(f"$weighting.{wid}.components: no weights registry available")
        w = weights_loader(wid)
        out: list[str] = []
        for p in w["pillars"].values():
            for c in p["components"]:
                if c not in out:
                    out.append(c)
        return out

    ctx = {"binding": binding, "missing_label": missing_label, "indicators": served,
           "source": source, "weighting_components": components, "uses_curiosity": False}
    steps = [_resolve(copy.deepcopy(step), ctx) for step in recipe]

    if ctx["uses_curiosity"] and not served:
        raise ComposeRefusal(
            f"none of the indicators this question names can be served by "
            f"{source_ds or 'any bound source'}. " + " ".join(notes))
    return RecipeResult(steps=steps, binding=binding, source_dataset=source_ds,
                        indicators=served, notes=notes)
