"""
tests/test_door_restyle.py ~ darker means harder, and the door owes a restyle (Sprint 09)

RAMP-1: the door drew a higher standing darker, and the Maine plan says darker
always means harder access. the lowest fifth is now the darkest, a value is
drawn darker in the direction its indicator declares worse, and a copy that
records no direction is refused rather than guessed. a renderer the door now
draws differently is owed to every item that holds the old one, by the move's
own path, which is UPDATE-1's first real update. the description says where
the data is stored, and carries the plot's credit and citation.

the bucket, the portal and the gate are the fakes the choropleth tests keep. ~
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from canopy.expose import publish as door
from canopy.expose.targets import PublishRefusal
from canopy.expose.targets.arcgis_webmap import RAMP, choropleth_of, fields_of

_spec = importlib.util.spec_from_file_location(
    "_choropleth_tests", Path(__file__).with_name("test_door_choropleth.py"))
ch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch)
fakes, KEY, IND = ch.fakes, ch.KEY, ch.IND


def _renderer(portal):
    _, layer = ch.layer_of(portal)
    return layer, layer["layerDefinition"]["drawingInfo"]["renderer"]


def test_the_lowest_fifth_is_the_darkest(tmp_path):
    root, portal = ch.garden(tmp_path), fakes.FakePortal()
    ch.run(root, ch.pages(), portal)
    layer, r = _renderer(portal)
    colours = [i["symbol"]["color"][:3] for i in r["classBreakInfos"]]
    assert colours[0] == RAMP[-1] and colours[-1] == RAMP[0]
    assert "darker is a lower standing" in layer["title"]


def test_a_renderer_the_door_now_draws_differently_is_owed(tmp_path):
    root, portal = ch.garden(tmp_path), fakes.FakePortal()
    ch.run(root, ch.pages(), portal)
    rec = fakes.record(root)
    rec["targets"]["test"][KEY]["renderer_sha256"] = "an older renderer"
    door.write_record(root / "plots" / fakes.PLOT, rec)
    [plan] = ch.run(root, ch.pages(), portal, write=False)
    assert any(line.startswith("owed: the layer's colours") for line in plan.lines)
    [o] = ch.run(root, ch.pages(), portal)
    assert o.outcome == "updated"
    _, r = _renderer(portal)
    assert r["classBreakInfos"][0]["symbol"]["color"][:3] == RAMP[-1]
    assert fakes.record(root)["targets"]["test"][KEY]["renderer_sha256"] != "an older renderer"


def test_an_unchanged_renderer_owes_nothing(tmp_path):
    root, portal = ch.garden(tmp_path), fakes.FakePortal()
    ch.run(root, ch.pages(), portal)
    [o] = ch.run(root, ch.pages(), portal)
    assert o.outcome == "unchanged"


def _value_copy(direction=None):
    copy = {"indicator": IND, "plot": "maine", "markers": False,
            "display_env": {"metadata": {
                "joined_to": {"level": "county"},
                "join": {"columns": {IND: [f"{IND}__value"]},
                         **({"directions": {IND: direction}} if direction else {})}}},
            "geojson": {"type": "FeatureCollection", "features": [
                {"type": "Feature", "properties": {f"{IND}__value": v}} for v in (10.0, 50.0, 90.0)]}}
    return copy, fields_of(copy["geojson"])


def test_a_value_with_no_recorded_direction_is_refused():
    copy, fields = _value_copy()
    with pytest.raises(PublishRefusal, match="easier or harder"):
        choropleth_of(copy, fields)


@pytest.mark.parametrize("direction, darkest_class", [("higher_is_worse", 4),
                                                      ("higher_is_better", 0)])
def test_a_value_is_darker_where_its_indicator_declares_worse(direction, darkest_class):
    copy, fields = _value_copy(direction)
    r, _field, title = choropleth_of(copy, fields)
    colours = [i["symbol"]["color"][:3] for i in r["classBreakInfos"]]
    assert colours[darkest_class] == RAMP[-1]
    assert "harder access and drawn darker" in title


def test_the_description_says_where_the_data_is_stored(tmp_path):
    root, portal = ch.garden(tmp_path), fakes.FakePortal()
    ch.run(root, ch.pages(), portal)
    item, _ = ch.layer_of(portal)
    assert "Where the data is stored" in item["description"]
    assert "truth" not in item["description"].lower()


def _credit(root, **doc):
    path = root / "plots" / fakes.PLOT / "publish" / "credit.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc))


CREDIT = {"credit": "Prepared by Kalli A. Hale.",
          "citation": "Hale, K. A. (2026). {title}. Version {version}. {url}",
          "data_guide": "The data guide comes with the open data hub."}


def test_every_item_carries_the_plots_credit_and_its_own_citation(tmp_path):
    root, portal = ch.garden(tmp_path), fakes.FakePortal()
    _credit(root, **CREDIT)
    ch.run(root, ch.pages(), portal)
    item, layer = ch.layer_of(portal)
    d = item["description"]
    assert "Credit and citation" in d and "Prepared by Kalli A. Hale." in d
    assert f"Version {ch.T1[:12]}." in d and "open data hub" in d


def test_a_credit_file_missing_a_field_or_naming_another_is_refused(tmp_path):
    root, portal = ch.garden(tmp_path), fakes.FakePortal()
    _credit(root, credit="x", citation="y")
    with pytest.raises(PublishRefusal, match="missing data_guide"):
        ch.run(root, ch.pages(), portal)
    _credit(root, **CREDIT, extra="z")
    with pytest.raises(PublishRefusal, match="unknown fields extra"):
        ch.run(root, ch.pages(), portal)
    _credit(root, **dict(CREDIT, citation="{title} {doi}"))
    with pytest.raises(PublishRefusal, match="does not fill"):
        ch.run(root, ch.pages(), portal)
