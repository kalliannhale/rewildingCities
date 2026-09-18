"""
canopy/api/app.py

the API seam ~ the engine, offered over HTTP

two faces, held apart on purpose.

the READ face is cheap, side-effect-free, and every endpoint is a projection
of one PlotReading. that is the whole reason the read-model exists: the CLI
and this speak about the same measurement, so they cannot tell different
stories about the same ground.

the ACT face can change things ~ found a plot, acquire data, compose an
experiment, run one. these delegate to capabilities that already exist
(ResolutionEngine.acquire_types, wondering.compose, Orchestrator.run) rather
than reimplementing them here.

A NOTE ON EXPOSURE, while it is still true: running an experiment executes
primitives on this machine. that is fine on a laptop and is a real
consideration the moment this is reachable from anywhere else. bind to
localhost, and treat authentication and the exposure gate as prerequisites
for deployment, not as polish. the sovereignty wall belongs before the door
opens, not after. ~
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query

from ..paths import project_root
from ..wonder.reading import read_plot
from ..wonder.session import PlotNotFound, open_plot, plot_display_name, plot_names

app = FastAPI(
    title="rewildingCities",
    version="0.1.0",
    description=(
        "A pedagogical geospatial analysis platform. Read what a plot can ask, "
        "see what it would take to ask more, compose an experiment, run it."
    ),
)

# run records live in memory for now, which is honest about what this is:
# a single-process local server. a real deployment needs them durable, and
# the run log on disk (compost/logs) is already the durable half.
_RUNS: dict[str, dict[str, Any]] = {}


def _reading(plot: str):
    try:
        _vocab, loam, report = open_plot(plot)
    except PlotNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return read_plot(loam, plot, plot_name=plot_display_name(plot)), loam, report


# ─────────────────────────────────────────────────────────────────────────────
# READ ~ projections of PlotReading. nothing here changes anything.
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["read"])
def health() -> dict:
    """is the garden reachable, and where is it?"""
    return {"ok": True, "root": str(project_root()), "plots": plot_names()}


@app.get("/plots", tags=["read"])
def list_plots() -> dict:
    """
    every plot this garden holds.

    a scan of plots/, not a catalog ~ honest about being a scan until the
    grove exists to federate them properly.
    """
    return {"plots": [{"plot": p, "name": plot_display_name(p)}
                      for p in plot_names()]}


@app.get("/plots/{plot}/reading", tags=["read"])
def plot_reading(plot: str) -> dict:
    """
    the whole account: what this ground holds, and every question it could
    ask of that. the single measurement the CLI also renders.
    """
    reading, _loam, report = _reading(plot)
    return {"reading": reading.to_dict(), "opened": report}


@app.get("/plots/{plot}/holdings", tags=["read"])
def plot_holdings(plot: str) -> dict:
    """what this ground holds, by canonical type, with coverage ranges."""
    reading, _loam, _report = _reading(plot)
    d = reading.to_dict()
    return {"plot": plot, "tiers": d["tiers"], "holdings": d["holdings"],
            "declared_unconformed": d["declared_unconformed"]}


@app.get("/plots/{plot}/curiosities", tags=["read"])
def plot_curiosities(plot: str,
                     verdict: str | None = Query(
                         None, description="runnable | runnable_with_uncertainty | blocked")
                     ) -> dict:
    """what this plot could ask, readiest first."""
    reading, _loam, _report = _reading(plot)
    curiosities = reading.to_dict()["curiosities"]
    if verdict:
        curiosities = [c for c in curiosities if c["best_verdict"] == verdict]
    return {"plot": plot, "answerable_now": reading.answerable_now,
            "curiosities": curiosities}


@app.get("/curiosities", tags=["read"])
def curiosities() -> dict:
    """the curiosity space itself, independent of any plot."""
    from ..wonder.possibility import _load_dir
    base = project_root() / "garden" / "curiosity-space"
    docs = _load_dir(base)
    return {"curiosities": [
        {"id": cid, "question": d.get("question"), "domain": d.get("domain"),
         "significance": d.get("significance", ""),
         "tags": d.get("tags") or []}
        for cid, d in sorted(docs.items()) if d.get("question")]}


@app.get("/methods", tags=["read"])
def methods() -> dict:
    """every way of answering, and what each one needs."""
    from ..wonder.possibility import _load_dir
    base = project_root() / "garden" / "methods"
    docs = _load_dir(base)
    out = []
    for mid, d in sorted(docs.items()):
        if not d.get("requires_data") and not d.get("choices"):
            continue
        out.append({
            "id": mid, "name": d.get("name", mid), "domain": d.get("domain"),
            "requires_data": [
                {"name": r.get("name"),
                 "accepts": r.get("semantic_types") or ([r["type"]] if r.get("type") else []),
                 "critical": bool(r.get("critical", True)),
                 "role": (r.get("role") or "").strip(),
                 "uncertainty_without": (r.get("uncertainty_without") or "").strip()}
                for r in (d.get("requires_data") or [])],
            "choices": list((d.get("choices") or {}).keys()),
        })
    return {"methods": out}


@app.get("/plots/{plot}/acquire", tags=["read"])
def sense_acquisition(plot: str,
                      method: str = Query(..., description="path to a method .yml"),
                      enriching: bool = False) -> dict:
    """
    what it would take to answer this here ~ senses only, fetches nothing.

    the ring, read forward: readiness names what is missing, the resolution
    engine says what it would take to get each one on this machine.
    """
    reading, loam, _report = _reading(plot)
    from ..loam.readiness import acquisition_gap
    from ..orchestrator.parsing import parse_manifest
    from ..orchestrator.resolution import ResolutionEngine
    from ..providers import create_default_registry

    method_path = project_root() / method
    if not method_path.is_file():
        raise HTTPException(status_code=404, detail=f"no method at {method}")

    gap = acquisition_gap(loam, plot, str(method_path), include_enriching=enriching)
    if not gap:
        return {"plot": plot, "method": method, "gap": [],
                "message": "nothing missing ~ this ground can answer as it stands."}

    manifest = parse_manifest(project_root() / "plots" / plot / "manifest.yml")
    engine = ResolutionEngine(manifest=manifest,
                              provider_registry=create_default_registry())
    return {"plot": plot, "method": method, "gap": gap,
            "report": engine.acquire_types(gap, dry=True, loam=loam, plot=plot)}


# ─────────────────────────────────────────────────────────────────────────────
# ACT ~ these change things. each delegates to an existing capability.
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/plots/{plot}/experiments", tags=["act"], status_code=201)
def compose_experiment(plot: str, curiosity: str, method: str,
                       sub_question: str | None = None) -> dict:
    """
    bind a question to a way of answering it ~ writes a runnable experiment.

    the door does not lock: this composes whatever was chosen and lets
    provenance teach through honest limitation.
    """
    _reading_obj, loam, _report = _reading(plot)
    from ..wonder.wondering import compose

    try:
        composed = compose(loam, plot, curiosity, method,
                           sub_question=sub_question, write=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"plot": plot, "curiosity": curiosity, "method": method,
            "path": str(composed.path) if composed.path else None,
            "verdict": composed.guidance.verdict,
            "guidance": {
                "question": composed.guidance.question,
                "what_youll_learn": composed.guidance.what_youll_learn,
                "cannot_yet": composed.guidance.cannot_yet,
                "whats_uncertain": composed.guidance.whats_uncertain,
                "the_wide_door": composed.guidance.the_wide_door,
            }}


def _execute_run(run_id: str, experiment: str, profile: str) -> None:
    from ..orchestrator.orchestrator import Orchestrator

    record = _RUNS[run_id]
    record["status"] = "running"
    try:
        orch = Orchestrator(experiment_path=str(project_root() / experiment),
                            profile=profile)
        result = orch.run()
        record.update(
            status="complete" if result.success else "failed",
            success=result.success,
            completed_steps=list(result.completed_steps),
            failed_step=result.failed_step,
            error=result.error,
            message=result.message,
            warnings=list(result.warnings or []),
            finished=datetime.now(timezone.utc).isoformat())
    except Exception as e:
        record.update(status="failed", success=False,
                      error=type(e).__name__, message=str(e),
                      finished=datetime.now(timezone.utc).isoformat())


@app.post("/plots/{plot}/runs", tags=["act"], status_code=202)
def start_run(plot: str, experiment: str, background: BackgroundTasks,
              profile: str = "dev") -> dict:
    """
    run an experiment ~ a background job, since a full pass is minutes.

    returns a run id to poll. the durable record is the run log the
    orchestrator already writes to compost/logs.
    """
    path = project_root() / experiment
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"no experiment at {experiment}")

    run_id = uuid.uuid4().hex[:12]
    _RUNS[run_id] = {"run_id": run_id, "plot": plot, "experiment": experiment,
                     "profile": profile, "status": "queued",
                     "started": datetime.now(timezone.utc).isoformat()}
    background.add_task(_execute_run, run_id, experiment, profile)
    return _RUNS[run_id]


@app.get("/plots/{plot}/runs/{run_id}", tags=["read"])
def run_status(plot: str, run_id: str) -> dict:
    record = _RUNS.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no run {run_id}")
    return record
