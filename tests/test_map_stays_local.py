"""
tests/test_map_stays_local.py ~ map draws locally; publishing is the door's (D-326)

replaces tests/test_publish_latch.py. the latch it tested uploaded a hosted
feature layer through the arcgis package and is retired (F1, F5). what still
holds is tested here: map writes its geojson every time, offline, and reaches
no network; --publish signposts the door and draws nothing; introspect no
longer claims ArcGIS credentials from variables the login never read (F4).
the gate's own checks moved to tests/test_publish_door.py. ~
"""

from __future__ import annotations

import argparse
import json
import socket

import pytest

from canopy import introspect, visuals
from canopy.cli import map as m


@pytest.fixture(autouse=True)
def network_off(monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("the network is off in these tests")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def vector_result(tmp_path):
    meta = {"semantic_type": "park_boundaries", "data_category": "vector",
            "lineage": {"kind": "experiment", "run": "parks", "method": "$methods/m",
                        "choices": {}, "curiosity": "$curiosity-space/thermal/x"}}
    return {"metadata": meta,
            "data": {"path": str(tmp_path / "not-there.geojson"), "format": "geojson"},
            "provenance": [], "warnings": []}


def parse(argv):
    parser = argparse.ArgumentParser()
    m.register(parser.add_subparsers())
    return parser.parse_args(argv)


def plot_with_one_result(tmp_path, monkeypatch):
    envelopes = tmp_path / "plots" / "demo" / ".envelopes"
    envelopes.mkdir(parents=True)
    (envelopes / "parks.envelope.json").write_text(json.dumps(vector_result(tmp_path)))
    monkeypatch.setattr(m, "find_root", lambda: tmp_path)
    return tmp_path / "plots" / "demo" / "harvest" / "map.geojson"


def test_render_writes_a_local_map_and_takes_no_publish(tmp_path):
    view = visuals.render(vector_result(tmp_path), tmp_path / "out")
    assert (tmp_path / "out" / "map.geojson").exists()
    assert not hasattr(view, "arcgis_url")
    with pytest.raises(TypeError):
        visuals.render(vector_result(tmp_path), tmp_path / "out", publish=True)


def test_visuals_holds_no_upload_path():
    assert not hasattr(visuals, "PublishError")
    assert not hasattr(visuals, "_publish_arcgis")


def test_rewilding_map_writes_locally_and_exits_0(tmp_path, monkeypatch):
    local_map = plot_with_one_result(tmp_path, monkeypatch)
    assert m.run(parse(["map", "demo", "park_boundaries"])) == 0
    assert local_map.exists()


def test_map_publish_signposts_the_door_and_draws_nothing(tmp_path, monkeypatch, capsys):
    local_map = plot_with_one_result(tmp_path, monkeypatch)
    assert m.run(parse(["map", "demo", "park_boundaries", "--publish"])) == 2
    err = capsys.readouterr().err
    assert "canopy.cli publish" in err and "D-326" in err
    assert not local_map.exists()


def test_introspect_claims_no_arcgis_credentials_from_variables(monkeypatch):
    monkeypatch.setenv("ARCGIS_API_KEY", "test-key-not-real")
    monkeypatch.setenv("ARCGIS_USERNAME", "someone")
    assert introspect.has_credentials("arcgis") is False
