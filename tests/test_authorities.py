"""
tests/test_authorities.py  |  rewildingCities, Sprint 05 change 14 (build 6, AUTH-1)

seeds/authorities/authorities.yml declares who may assign a place's code,
and at which levels (D-188). The code still carries copies of that list, and
each is held to the seed here, so adding or changing an authority without
changing every copy fails by name instead of letting the system disagree with
itself about which places exist. Python copies are imported; R copies are read
as text, since a test cannot import R.
"""

import importlib.util
import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "seeds" / "authorities" / "authorities.yml"


def seed():
    return (yaml.safe_load(SEED.read_text()) or {})["authorities"]


def names():
    return set(seed())


def authority_of_level():
    return {level: authority for authority, spec in seed().items()
            for level in (spec.get("levels") or {})}


def module(relative):
    path = REPO / relative
    spec = importlib.util.spec_from_file_location(path.stem, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def r_vector(relative, name):
    """the strings of an R `name <- c(...)`, as written; named entries keep
    their names, so a level map reads as {level: authority}."""
    text = (REPO / relative).read_text()
    match = re.search(rf"^{name}\s*<-\s*c\((.*?)\)", text, re.M | re.S)
    assert match, f"{relative} has no {name} <- c(...)"
    body = match.group(1)
    named = dict(re.findall(r'(\w+)\s*=\s*"([^"]+)"', body))
    return named or re.findall(r'"([^"]+)"', body)


# ── the seed ──────────────────────────────────────────────────────────────
def test_each_level_belongs_to_exactly_one_authority():
    seen = {}
    for authority, spec in seed().items():
        for level in spec.get("levels") or {}:
            assert level not in seen, f"{level} is under {seen.get(level)} and {authority}"
            seen[level] = authority


def test_every_example_has_its_levels_width():
    for authority, spec in seed().items():
        for level, shape in (spec.get("levels") or {}).items():
            example = shape.get("example")
            if example is not None:
                assert len(str(example)) == shape["width"], f"{authority} {level}: {example}"


# ── every copy, held to the seed ──────────────────────────────────────────
def test_preview_knows_exactly_the_seeds_authorities():
    from canopy.indicators import preview
    assert set(preview.KNOWN_UNIT_AUTHORITIES) == names()


def test_derive_indicator_knows_exactly_the_seeds_authorities():
    assert set(r_vector("soil/transform/derive_indicator.R", "KNOWN_UNIT_AUTHORITIES")) == names()


def test_build_places_names_exactly_the_seeds_authorities():
    places = module("soil/transform/build_places.py")
    assert {places.GEOID, places.SLDL, places.SLDU, places.AIANNH, places.MEGIS} == names()


def test_build_place_edges_names_each_level_by_its_authority():
    edges = module("soil/transform/build_place_edges.py")
    levels = authority_of_level()
    assert (edges.GEOID, edges.SLDL, edges.SLDU, edges.AIANNH) == (
        levels["cousub"], levels["sldl"], levels["sldu"], levels["aiannh"])


def test_build_place_outlines_maps_each_level_to_its_authority():
    outlines = r_vector("soil/transform/build_place_outlines.R", "LEVEL_AUTHORITY")
    levels = authority_of_level()
    assert outlines and all(levels.get(level) == authority
                            for level, authority in outlines.items()), outlines


def test_build_seats_keys_each_chamber_by_its_authority():
    seats = module("soil/transform/build_seats.py")
    levels = authority_of_level()
    assert {level: authority for level, (_chamber, authority) in seats.CHAMBER_OF.items()} == {
        "sldl": levels["sldl"], "sldu": levels["sldu"]}
