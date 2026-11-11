"""
soil/transform/build_located_in.py  |  rewildingCities

located_in edges (Contract 3, section 2): every point of a declared layer to
every area it falls in, weights 1 and 1. a point is never a place (D-103):
it is named only here, by its layer and feature id.

each level comes from what that level is defined on (Sprint 06, step 2):

  ~ state, county, town   the 2024 topological face the point falls in. a
                          face never straddles a boundary, so this is exact,
                          even inside a block a 2024 line split
  ~ sldl, sldu, aiannh    the face's 2020 block, through the spine. districts
                          and tribal areas are defined on whole blocks (the
                          equivalency files, the block assignment file), so
                          the block is exact for them, and a point can never
                          land in a district its block's overlaps edges deny
  ~ megis division        the block's division, as the graph assigns it (D-122)

a point whose face town differs from its block's spine town sits in a split
block (D-126): it is placed by its face and listed as split, so the rare
disagreement shows rather than hides. a point in no face, or in a block the
spine does not hold, is listed as unplaced and gets no edge; it is never
dropped silently and never placed by a guess.

this file holds the logic only, as pure functions over tables. reading the
faces and the spine, and the pr_io main, arrive once their shapes are read.

Refuses: a feature id used twice in one layer; a placed point the spine
gives no House or Senate district; an edge whose `to` place is not in
places; two edges between one point and one place. ~
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

GEOID, SLDL, SLDU, AIANNH, MEGIS = ("us_census_geoid", "us_census_sldl",
                                    "us_census_sldu", "us_census_aiannh", "megis")
COLUMNS = ["from_authority", "from_code", "to_authority", "to_code", "kind",
           "weight_population", "weight_households", "weight_reason", "source", "vintage"]
KEY = ["from_authority", "from_code", "to_authority", "to_code"]
KIND = "located_in"
FACE_LEVELS = ("state", "county", "town")
BLOCK_LEVELS = ("sldl", "sldu", "aiannh", "division")
REQUIRED_VINTAGES = ("state", "county", "town", "sldl", "sldu", "aiannh", "division")


class LocatedInRefused(ValueError):
    """a placement the contract refuses, with why."""


@dataclass
class Placement:
    edges: pd.DataFrame
    unplaced: list[dict] = field(default_factory=list)
    split: list[dict] = field(default_factory=list)


def _text(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    t = str(x).strip()
    return t or None


def locate(points: pd.DataFrame, spine: pd.DataFrame, divisions: pd.DataFrame | None,
           places: pd.DataFrame, vintages: dict, source: str) -> Placement:
    """
    points     layer, feature_id, block, town, county: each point with the face
               it fell in, its face's 2020 block and 2024 town and county
               (block null when the point fell in no face)
    spine      block, town, sldl, sldu, aiannh: one row per 2020 block
    divisions  block, division (optional, D-122)
    places     authority, code: the places table
    vintages   state, county, town, sldl, sldu, aiannh, division
    """
    missing = [k for k in REQUIRED_VINTAGES if k not in (vintages or {})]
    if missing:
        raise LocatedInRefused(f"vintages must declare {', '.join(missing)}")

    dup = points[points.duplicated(["layer", "feature_id"], keep=False)]
    if len(dup):
        ids = sorted({f"{r.layer}:{r.feature_id}" for r in dup.itertuples()})
        raise LocatedInRefused(f"a feature id names one feature in its layer; used "
                               f"twice: {', '.join(ids[:10])}")

    by_block = spine.set_index("block")
    division_of = ({} if divisions is None
                   else dict(zip(divisions["block"].astype(str), divisions["division"].astype(str))))
    known = set(zip(places["authority"].astype(str), places["code"].astype(str)))

    rows, unplaced, split = [], [], []
    for p in points.itertuples(index=False):
        who = {"layer": p.layer, "feature_id": str(p.feature_id)}
        block = _text(p.block)
        if block is None:
            unplaced.append({**who, "why": "the point falls in no 2024 face in this state"})
            continue
        if block not in by_block.index:
            unplaced.append({**who, "why": f"its face's block {block} is not in the spine"})
            continue
        b = by_block.loc[block]
        town, county = _text(p.town), _text(p.county)
        if _text(b["town"]) != town:
            split.append({**who, "block": block, "face_town": town,
                          "block_town": _text(b["town"])})
        sldl, sldu = _text(b["sldl"]), _text(b["sldu"])
        if not (sldl and sldu):
            raise LocatedInRefused(f"{p.layer}:{p.feature_id} lies in block {block}, which "
                                   f"the spine gives no House or Senate district")
        to = [(GEOID, county[:2], "state"), (GEOID, county, "county"), (GEOID, town, "town"),
              (SLDL, sldl, "sldl"), (SLDU, sldu, "sldu")]
        aiannh = _text(b.get("aiannh"))
        if aiannh:
            to.append((AIANNH, aiannh, "aiannh"))
        division = division_of.get(block)
        if division:
            to.append((MEGIS, division, "division"))
        for authority, code, level in to:
            rows.append({"from_authority": p.layer, "from_code": str(p.feature_id),
                         "to_authority": authority, "to_code": code, "kind": KIND,
                         "weight_population": 1.0, "weight_households": 1.0,
                         "weight_reason": None, "source": source,
                         "vintage": str(vintages[level])})

    edges = pd.DataFrame(rows, columns=COLUMNS)
    absent = sorted({f"{r.to_authority}:{r.to_code}" for r in edges.itertuples()
                     if (r.to_authority, r.to_code) not in known})
    if absent:
        raise LocatedInRefused(f"an edge's `to` end must be a place; not in places: "
                               f"{', '.join(absent[:10])}")
    if edges.duplicated(KEY).any():
        raise LocatedInRefused("one point has two edges to one place")
    return Placement(edges=edges, unplaced=unplaced, split=split)


def output_metadata(placement: Placement) -> dict:
    """what the receipt says: its key (KEYS-1), and every point it could not
    place or placed inside a split block, by name."""
    return {"data_category": "tabular", "crs": None, "row_count": len(placement.edges),
            "variables": COLUMNS, "id_fields": KEY, "spatial_unit": "edge",
            "unplaced": placement.unplaced, "split_block_points": placement.split}
