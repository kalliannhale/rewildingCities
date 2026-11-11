"""

canopy/wonder/wondering.py

wondering ~ binding a person's question into a real experiment they can run

this is the third layer of the garden (curiosity -> method -> experiment),
reached on a person's request. possibility showed what this ground could
ask; wondering *composes* a chosen question into an experiment recipe and
hands it to the orchestrator you already built. ♡

the keystone, made into structure ~ THE DOOR DOES NOT LOCK. a person may
compose and run an experiment even when something critical is missing, so
they can discover, through honest provenance, why it is wrong. perfectionist
gatekeeping teaches nothing; a documented wrong answer teaches the real
shape of inquiry. so compose() never refuses on readiness ~ readiness only
changes the guidance and the warnings, never whether you may enter.

what it composes, faithfully:
  ~ the binding: curiosity and method, by reference, resolved at runtime
  ~ the choices: each a decision the person made, or a default named in the open
  ~ the parameters: the landscape settings for this plot
  ~ a step skeleton: a best-effort conform-then-analyze draft the orchestrator
    validates ~ composed openly, never claimed as perfect

what it carries alongside, honestly (your "honest, contextualized analysis"
mandate):
  ~ what you will learn (the curiosity's sub-questions)
  ~ where it is uncertain and why (the method's uncertainty_without)
  ~ what it cannot tell you yet, and what running it anyway will reveal
  ~ how to fill a gap (loop to `rewilding acquires`)

it references seeds and the loam only; the orchestrator does the running. ~

"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _root(root=None) -> Path:
    """
    the garden's root ~ an explicit root wins; otherwise canopy.paths, which
    raises rather than falling back to the cwd. C-04. ~
    """
    if root:
        return Path(root)
    from canopy.paths import project_root
    return project_root()


def _load_by_id(folder: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not folder.is_dir():
        return out
    for f in sorted(folder.rglob("*.yml")):
        # an index lists documents; it is not one (WON-5)
        if f.name == "index.yml":
            continue
        try:
            doc = yaml.safe_load(f.read_text()) or {}
        except Exception:
            continue
        out[doc.get("id") or f.stem] = doc
    return out


def _manifest_types(root: Path, plot: str) -> dict[str, str]:
    """map a semantic_type to the manifest dataset that declares it, so steps
    can reference $manifest.<dataset>. a type the manifest doesn't declare is
    left out ~ the orchestrator will then honestly report it missing, which is
    the wide door working. ~"""
    mpath = root / "plots" / plot / "manifest.yml"
    if not mpath.exists():
        return {}
    doc = yaml.safe_load(mpath.read_text()) or {}
    out = {}
    for name, spec in (doc.get("datasets") or {}).items():
        st = (spec or {}).get("semantic_type")
        if st and st not in out:
            out[st] = name
    return out


def _manifest_datasets(root: Path, plot: str) -> dict[str, dict]:
    """every dataset the plot's manifest declares, by name, in full. the
    recipe path binds from this rather than _manifest_types, which keeps the
    first dataset of each type and would choose between two in silence. ~"""
    mpath = root / "plots" / plot / "manifest.yml"
    if not mpath.exists():
        return {}
    doc = yaml.safe_load(mpath.read_text()) or {}
    return {n: (s or {}) for n, s in (doc.get("datasets") or {}).items()}


@dataclass
class Guidance:
    """the honest word that travels with a composed experiment ~ what it will
    teach, where it is unsure, what it cannot yet say, and how to go further.
    the words are the seed authors' own. ~"""
    question: str
    verdict: str
    what_youll_learn: list[str] = field(default_factory=list)
    whats_uncertain: list[str] = field(default_factory=list)
    cannot_yet: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    the_wide_door: str = ""

    def say(self) -> str:
        lines = [f'a wondering, composed ~ "{self.question}"']
        if self.what_youll_learn:
            lines.append("  what you will learn:")
            for q in self.what_youll_learn[:5]:
                lines.append(f"    ~ {q}")
        if self.whats_uncertain:
            lines.append("  where it stays uncertain (and that is honest):")
            for u in self.whats_uncertain:
                lines.append(f"    ~ {u}")
        if self.cannot_yet:
            lines.append("  what it cannot tell you yet:")
            for c in self.cannot_yet:
                lines.append(f"    ~ {c}")
        if self.decisions:
            lines.append("  the choices, named in the open:")
            for d in self.decisions:
                lines.append(f"    ~ {d}")
        if self.the_wide_door:
            lines.append(f"  the open door: {self.the_wide_door}")
        return "\n".join(lines)


@dataclass
class Composed:
    """a bound, runnable experiment plus its honest guidance. ~"""
    experiment_id: str
    experiment: dict
    guidance: Guidance
    path: str | None = None


def _default_choice(spec: dict) -> tuple[str, bool]:
    """the person's pick if given, else the first option, named as a default. ~"""
    options = spec.get("options") or {}
    if isinstance(options, dict) and options:
        return next(iter(options)), True
    if isinstance(options, list) and options:
        first = options[0]
        return (first.get("id", first.get("name")) if isinstance(first, dict) else first), True
    return "default", True


def _compose_steps(method: dict, manifest_types: dict[str, str],
                   target_crs: str) -> list[dict]:
    """a best-effort conform-then-analyze draft. for each required datum, a
    small soil chain (validate -> repair/reproject) that references the
    manifest; then the method's analysis primitive over those conformed
    inputs. composed openly ~ the orchestrator validates it, and a missing
    dataset surfaces there, honestly, not here. ~"""
    steps: list[dict] = []
    analysis_inputs: dict[str, str] = {}

    for req in method.get("requires_data", []) or []:
        name = req.get("name", "input")
        types = req.get("semantic_types") or ([req["type"]] if req.get("type") else [])
        st = types[0] if types else name
        # reference the manifest dataset if declared; else name the expected
        # type, so the orchestrator reports it missing (the wide door).
        dataset = manifest_types.get(st, st)
        category = req.get("type", "vector")

        # a table is frameless by nature and relates through its join keys
        # (the frame law), so it enters the analysis as declared, with no
        # vector validation and no reprojection. composing both onto a
        # parquet table drafted a chain that could only fail (WON-6).
        if category == "tabular":
            analysis_inputs[name] = f"$manifest.{dataset}"
            continue

        validate = f"soil/validate_{'raster' if category == 'raster' else 'vector'}"
        last = f"conform_{name}"
        steps.append({
            "id": last,
            "primitive": validate,
            "inputs": {"features": f"$manifest.{dataset}"},
            "outputs": {"validated": f"{name}_validated"},
            "params": {},
        })
        if category != "raster":
            steps.append({
                "id": f"{last}_frame",
                "primitive": "soil/reproject_vector",
                "inputs": {"features": f"$steps.{last}.validated"},
                "outputs": {"reprojected": f"{name}_reprojected"},
                "params": {"target_crs": target_crs},
            })
            last = f"{last}_frame"
        analysis_inputs[name] = f"$steps.{last}." + list(steps[-1]["outputs"])[0]

    # the analysis step, from the method's declared primitive and outputs
    prims = method.get("requires_primitives") or []
    prim_ref, purpose = "roots/analysis", ""
    if prims:
        first = prims[0]
        if isinstance(first, dict):
            (pname, pspec), = first.items()
            prim_ref = f"{(pspec or {}).get('from', 'roots')}/{pname}"
            purpose = (pspec or {}).get("purpose", "")
        elif isinstance(first, str) and "/" in first:
            # the string form, `soil/derive_indicator`, is already a full
            # reference. it used to fall through to the placeholder
            # roots/analysis, which names no primitive (WON-6).
            prim_ref = first.strip()
    # `produces` is declared two ways across the garden, and both are
    # legitimate. Four methods write a LIST of dicts, each naming an output;
    # one writes a bare MAPPING describing a single product. Iterating a
    # mapping yields its string KEYS, so prod.get() blew up on the newer
    # shape ~ and because nothing had ever run a composed experiment, nobody
    # noticed. Read both rather than legislate one. C-62.
    outputs = {}
    produces = method.get("produces")
    if isinstance(produces, dict):
        # a single product: prefer its own name, else its semantic type
        name = produces.get("name") or produces.get("semantic_type") or "result"
        outputs[name] = name
    else:
        for prod in produces or []:
            if isinstance(prod, dict):
                name = prod.get("name") or prod.get("semantic_type") or "result"
            else:
                name = str(prod)
            outputs[name] = name
    steps.append({
        "id": "analyze",
        "primitive": prim_ref,
        "description": purpose,
        "inputs": analysis_inputs,
        "outputs": outputs or {"result": "result"},
        "params": {},
    })
    return steps


def _guidance(curiosity: dict, method: dict, present: list[str],
              verdict: str, chosen: dict) -> Guidance:
    """build the honest word from what the seed authors already wrote. ~"""
    learn = [(s or {}).get("question", n)
             for n, s in (curiosity.get("sub_questions") or {}).items()]

    uncertain, cannot = [], []
    for req in method.get("requires_data", []) or []:
        types = req.get("semantic_types") or ([req["type"]] if req.get("type") else [])
        if any(t in present for t in types):
            continue
        u = (req.get("uncertainty_without") or "").strip().splitlines()
        line = f"{(types[0] if types else req.get('name'))}: {u[0] if u else 'affects the result'}"
        (cannot if req.get("critical", True) else uncertain).append(line)

    decisions = []
    for name, spec in (method.get("choices") or {}).items():
        picked = chosen.get(name)
        if picked:
            decisions.append(f"{name}: you chose '{picked}'")
        else:
            default, _ = _default_choice(spec or {})
            decisions.append(f"{name}: defaulted to '{default}' (yours to change)")

    door = ""
    if verdict == "not_yet":
        missing = ", ".join(c.split(":")[0] for c in cannot) or "some data"
        door = (f"your community's data does not yet include {missing}. you can still "
                f"run this ~ the system will show you exactly where it cannot proceed "
                f"and why, which is how the shape of this science is learned. to fill "
                f"the gap, `rewilding acquires` can try to gather it.")
    elif verdict == "partial":
        door = ("you can run this today; one input is missing but not essential, so the "
                "result is real, with the honest caveat noted above.")
    else:
        door = "every input is present ~ this is ready to run as composed."

    return Guidance(
        question=curiosity.get("question", curiosity.get("id", "?")),
        verdict=verdict, what_youll_learn=learn,
        whats_uncertain=uncertain, cannot_yet=cannot,
        decisions=decisions, the_wide_door=door)


def compose(loam, plot: str, curiosity_id: str, method_id: str,
            sub_question: str | None = None, chosen: dict | None = None,
            root=None, write: bool = True) -> Composed:
    """bind a chosen question into a runnable experiment ~ the door does not
    lock, so this composes whatever the person chose, and lets provenance
    teach through honest limitation. ~"""
    base = _root(root)
    chosen = chosen or {}
    curiosities = _load_by_id(base / "garden" / "curiosity-space")
    methods = _load_by_id(base / "garden" / "methods")

    curiosity = curiosities.get(curiosity_id)
    method = methods.get(method_id)
    if curiosity is None or method is None:
        raise ValueError(f"could not find curiosity '{curiosity_id}' or method '{method_id}'")

    domain = curiosity.get("domain") or method.get("domain") or "thermal"
    manifest_types = _manifest_types(base, plot)

    # what is present, from the loam ~ so guidance and verdict are honest
    present = sorted({r["semantic_type"] for r in loam.find(plot=plot)
                      if r.get("semantic_type")} & set(
                      t for req in (method.get("requires_data") or [])
                      for t in (req.get("semantic_types")
                                or ([req["type"]] if req.get("type") else []))))
    # verdict, purely to shape guidance (never to gate)
    missing_critical = any(
        req.get("critical", True) and not any(
            t in present for t in (req.get("semantic_types")
                                   or ([req["type"]] if req.get("type") else [])))
        for req in (method.get("requires_data") or []))
    any_missing = any(
        not any(t in present for t in (req.get("semantic_types")
                                       or ([req["type"]] if req.get("type") else [])))
        for req in (method.get("requires_data") or []))
    verdict = "not_yet" if missing_critical else ("partial" if any_missing else "ready")

    # resolve choices ~ person's picks, or defaults named in the open
    resolved_choices = {}
    for name, spec in (method.get("choices") or {}).items():
        resolved_choices[name] = chosen.get(name) or _default_choice(spec or {})[0]

    target_crs = (curiosity.get("parameters", {}) or {}).get("target_crs", "EPSG:4326")

    stem = f"{plot}_{curiosity_id}"
    if sub_question:
        stem += f"_{sub_question}"
    salt = hashlib.md5(f"{stem}:{method_id}".encode()).hexdigest()[:6]
    exp_id = f"{stem}__{method_id}_{salt}"

    experiment = {
        "id": exp_id,
        "name": f"{curiosity.get('question', curiosity_id)}",
        "description": (f"Composed by wonder from curiosity '{curiosity_id}' and method "
                        f"'{method_id}' for plot '{plot}'. The door does not lock: this "
                        f"runs as composed so its limits can be discovered honestly."),
        "curiosity": {"ref": f"$curiosity-space/{domain}/{curiosity_id}",
                      **({"sub_question": sub_question} if sub_question else {})},
        "method": {"ref": f"$methods/{domain}/{method_id}"},
        "city": plot,
        # RELATIVE TO THIS FILE, because the orchestrator resolves the
        # manifest as experiment_path.parent / manifest_path. The
        # project-root form written here before produced
        # plots/<plot>/experiments/plots/<plot>/manifest.yml, which meant
        # every experiment compose had ever written was unrunnable ~ and
        # neither composed file had ever been run, so it went unseen. C-61.
        "manifest": "../manifest.yml",
        "choices": resolved_choices,
        "parameters": {"target_crs": target_crs},
        "steps": None,
    }

    # a method with a recipe says exactly how it runs; compose fills its
    # compose-time references from this question and this ground (D-67).
    # without one, the best-effort conform-then-analyze draft, as before.
    recipe_notes: list[str] = []
    if method.get("recipe"):
        from .recipe import compose_recipe
        from canopy.indicators import IndicatorRegistry
        registry = IndicatorRegistry.load(base / "seeds" / "indicators")

        def weights_loader(wid: str) -> dict:
            from canopy.indicators.weights import WeightsRegistry
            return WeightsRegistry.load(base / "seeds" / "weights", registry.all()).declaration(wid)

        result = compose_recipe(method, curiosity, sub_question,
                                _manifest_datasets(base, plot), registry,
                                weights_loader, chosen.get("datasets"))
        experiment["steps"] = result.steps
        for req_name, ds in result.binding.items():
            recipe_notes.append(f"{req_name}: bound to {ds}" if ds
                                else f"{req_name}: nothing here declares it yet")
        recipe_notes.extend(result.notes)
    else:
        experiment["steps"] = _compose_steps(method, manifest_types, target_crs)

    guidance = _guidance(curiosity, method, present, verdict, chosen)
    guidance.decisions.extend(recipe_notes)

    path = None
    if write:
        out_dir = base / "plots" / plot / "experiments"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = str(out_dir / f"{exp_id}.yml")
        header = (
            "# ════════════════════════════════════════════════════════════\n"
            f"# Composed by wonder ~ {exp_id}\n"
            "# The door does not lock: this experiment runs as composed so its\n"
            "# limits can be discovered through honest provenance, not refused.\n"
            "# Steps are a composed draft; the orchestrator validates them.\n"
            f"# Readiness: {verdict}\n"
            "# ════════════════════════════════════════════════════════════\n\n")
        Path(path).write_text(header + yaml.dump(experiment, sort_keys=False, default_flow_style=False))

    return Composed(experiment_id=exp_id, experiment=experiment, guidance=guidance, path=path)