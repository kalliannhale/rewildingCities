"""
canopy/api/indicators.py

indicators, over the read face of the API

four routes, all read-only. nothing here acquires, derives into the mart,
writes an envelope or publishes, so like the rest of the read face it needs no
exposure gate (P-22 comes before anything that can leave).

  GET /indicators                          the registry, every declared field
  GET /indicators/{indicator_id}           one indicator
  GET /plots/{plot}/indicators             which sources a plot holds, and what
                                           it could hold but does not
  GET /plots/{plot}/indicators/{id}        preview values, long-form, one row
                                           per unit, every row labelled preview.
                                           requires ?unit_authority=, whose codes
                                           name the units (D-133); without it,
                                           422 before anything is read

the router is thin on purpose. every decision lives in
canopy/indicators/preview.py, where it can be tested without a server, and
this file only translates a refusal into an HTTP status, with the reason as
a plain-string detail like every other route on the read face:

  not_found    404   no such plot, indicator, or source listing it
  ambiguous    409   more than one source could answer; name one
  unavailable  409   declared, not acquired
  malformed    422   a plot name that is not a name, a source missing columns
  registry     500   the registry itself did not load

mounted at the end of canopy/api/app.py.

NOT A PROJECTION OF PlotReading, and saying so. the rest of the read face
projects one PlotReading so the CLI and the API cannot tell different stories.
these routes read declarations (the registry, the manifest) and an acquired
file directly, because the preview exists before the pipeline does. the CLI
twin is `python -m canopy.indicators.preview`, so nothing here answers a
question the CLI cannot. once derive_indicator.R writes indicator_values into
loam, the values route becomes a projection like the others (D-29).
♡
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..indicators import preview as ip

router = APIRouter(tags=["read"])

HTTP_STATUS = {
    "not_found": 404,
    "ambiguous": 409,
    "unavailable": 409,
    "malformed": 422,
    "registry": 500,
}


def _refuse(e: ip.PreviewError):
    raise HTTPException(status_code=HTTP_STATUS.get(e.kind, 500), detail=e.message)


@router.get("/indicators")
def list_indicators(defined_by: str | None = Query(None),
                    measures: str | None = Query(None)):
    try:
        reg = ip.load_registry()
    except ip.PreviewError as e:
        _refuse(e)
    ids = reg.all()
    if defined_by is not None:
        ids = [i for i in ids if i in reg.defined_by(defined_by)]
    if measures is not None:
        ids = [i for i in ids if i in reg.measuring(measures)]
    return {"count": len(ids),
            "indicators": [ip.describe(reg.get(i)) for i in ids]}


@router.get("/indicators/{indicator_id}")
def get_indicator(indicator_id: str):
    try:
        reg = ip.load_registry()
        return ip.describe(ip.get_indicator(reg, indicator_id))
    except ip.PreviewError as e:
        _refuse(e)


@router.get("/plots/{plot}/indicators")
def plot_indicators(plot: str):
    try:
        return ip.plot_summary(plot, ip.load_registry())
    except ip.PreviewError as e:
        _refuse(e)


@router.get("/plots/{plot}/indicators/{indicator_id}")
def plot_indicator_values(plot: str, indicator_id: str,
                          unit_authority: str = Query(...),
                          dataset: str | None = Query(None)):
    try:
        return ip.preview(plot, indicator_id, dataset, unit_authority=unit_authority)
    except ip.PreviewError as e:
        _refuse(e)