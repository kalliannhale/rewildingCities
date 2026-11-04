"""
tests/test_publish_latch.py

EXP-1: a map reaches ArcGIS Online only when someone asks for it (publish=True,
`rewilding map --publish`), and a publish that was asked for and cannot happen
says why instead of falling back in silence.

nothing here can publish. the network is refused for every test, ArcGIS is a
fake that only records what it was asked to do, and credentials are a test
value set per test.
"""

import argparse
import json
import socket
import sys
import types
from types import SimpleNamespace

import pytest

from canopy import introspect
from canopy import visuals
from canopy.cli import map as m
from canopy.visuals import PublishError, render


FAKE_URL = "https://example.invalid/home/item.html?id=fake-item-1"


class FakeItem:
    def __init__(self, fail_publish):
        self.id = "fake-item-1"
        self.fail_publish = fail_publish
        self.publish_calls = 0

    def publish(self):
        self.publish_calls += 1
        if self.fail_publish:
            raise RuntimeError("service unavailable")
        return SimpleNamespace(homepage=FAKE_URL)


class FakeArcGIS:
    """stands in for the arcgis package; records sign-ins and uploads. ~"""

    def __init__(self):
        self.fail_add = False
        self.fail_publish = False
        self.signins = []
        self.uploads = []
        self.items = []

    def GIS(self, *args, **kwargs):
        self.signins.append(args)
        return SimpleNamespace(content=SimpleNamespace(add=self._add))

    def _add(self, props, data=None):
        if self.fail_add:
            raise RuntimeError("upload rejected")
        self.uploads.append((props, data))
        item = FakeItem(self.fail_publish)
        self.items.append(item)
        return item


@pytest.fixture(autouse=True)
def network_off_and_no_credentials(monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("the network is off in these tests")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.delenv("ARCGIS_API_KEY", raising=False)
    monkeypatch.delenv("ARCGIS_USERNAME", raising=False)


@pytest.fixture
def arcgis(monkeypatch):
    fake = FakeArcGIS()
    gis_module = types.ModuleType("arcgis.gis")
    gis_module.GIS = fake.GIS
    package = types.ModuleType("arcgis")
    package.gis = gis_module
    monkeypatch.setitem(sys.modules, "arcgis", package)
    monkeypatch.setitem(sys.modules, "arcgis.gis", gis_module)
    return fake


def online(monkeypatch, is_online):
    monkeypatch.setattr(introspect, "is_online", lambda timeout=1.5: is_online)


def credentials(monkeypatch):
    monkeypatch.setenv("ARCGIS_API_KEY", "test-key-not-real")


def vector_result(tmp_path):
    return {"metadata": {"semantic_type": "park_boundaries", "data_category": "vector"},
            "data": {"path": str(tmp_path / "not-there.geojson"), "format": "geojson"}}


# ── render(): off unless asked ────────────────────────────────────────────
def test_without_publish_nothing_leaves_even_online_and_credentialed(tmp_path, monkeypatch, arcgis):
    online(monkeypatch, True)
    credentials(monkeypatch)
    view = render(vector_result(tmp_path), tmp_path / "out")
    assert view.mode == "geojson" and view.arcgis_url is None
    assert arcgis.signins == [] and arcgis.uploads == []
    assert (tmp_path / "out" / "map.geojson").exists()


def test_without_publish_reachability_is_not_even_checked(tmp_path, monkeypatch, arcgis):
    monkeypatch.setattr(visuals, "_arcgis_unreachable",
                        lambda: pytest.fail("checked reachability without publish=True"))
    render(vector_result(tmp_path), tmp_path / "out", publish=False)
    assert arcgis.uploads == []


def test_publish_online_with_credentials_uploads_once(tmp_path, monkeypatch, arcgis):
    online(monkeypatch, True)
    credentials(monkeypatch)
    view = render(vector_result(tmp_path), tmp_path / "out", publish=True)
    assert view.mode == "arcgis+geojson" and view.arcgis_url == FAKE_URL
    assert arcgis.signins == [("home",)]
    assert len(arcgis.uploads) == 1 and arcgis.items[0].publish_calls == 1
    assert arcgis.uploads[0][1] == str(tmp_path / "out" / "map.geojson")


# ── render(): asked for, cannot happen, says why ──────────────────────────
def test_publish_without_credentials_is_refused_out_loud(tmp_path, monkeypatch, arcgis):
    online(monkeypatch, True)
    with pytest.raises(PublishError, match="credentials") as e:
        render(vector_result(tmp_path), tmp_path / "out", publish=True)
    assert arcgis.signins == [] and arcgis.uploads == []
    assert e.value.geojson_path == str(tmp_path / "out" / "map.geojson")
    assert (tmp_path / "out" / "map.geojson").exists()


def test_publish_offline_is_refused_out_loud(tmp_path, monkeypatch, arcgis):
    online(monkeypatch, False)
    credentials(monkeypatch)
    with pytest.raises(PublishError, match="offline"):
        render(vector_result(tmp_path), tmp_path / "out", publish=True)
    assert arcgis.signins == [] and arcgis.uploads == []


def test_a_failed_upload_is_raised_not_swallowed(tmp_path, monkeypatch, arcgis):
    online(monkeypatch, True)
    credentials(monkeypatch)
    arcgis.fail_add = True
    with pytest.raises(PublishError, match="could not upload") as e:
        render(vector_result(tmp_path), tmp_path / "out", publish=True)
    assert e.value.geojson_path == str(tmp_path / "out" / "map.geojson")


def test_a_failed_publish_names_the_item_left_on_arcgis(tmp_path, monkeypatch, arcgis):
    online(monkeypatch, True)
    credentials(monkeypatch)
    arcgis.fail_publish = True
    with pytest.raises(PublishError, match="fake-item-1"):
        render(vector_result(tmp_path), tmp_path / "out", publish=True)
    assert len(arcgis.uploads) == 1


def test_a_missing_arcgis_package_is_raised_not_swallowed(tmp_path, monkeypatch):
    online(monkeypatch, True)
    credentials(monkeypatch)
    monkeypatch.setitem(sys.modules, "arcgis", None)
    with pytest.raises(PublishError, match="arcgis package"):
        render(vector_result(tmp_path), tmp_path / "out", publish=True)


# ── rewilding map: the --publish flag ─────────────────────────────────────
def parse(argv):
    parser = argparse.ArgumentParser()
    m.register(parser.add_subparsers())
    return parser.parse_args(argv)


def test_map_publish_is_off_by_default():
    assert parse(["map", "demo", "park_boundaries"]).publish is False
    assert parse(["map", "demo", "park_boundaries", "--publish"]).publish is True


def plot_with_one_result(tmp_path, monkeypatch):
    envelopes = tmp_path / "plots" / "demo" / ".envelopes"
    envelopes.mkdir(parents=True)
    (envelopes / "parks.envelope.json").write_text(json.dumps(vector_result(tmp_path)))
    monkeypatch.setattr(m, "find_root", lambda: tmp_path)
    return tmp_path / "plots" / "demo" / "harvest" / "map.geojson"


def test_rewilding_map_without_publish_writes_locally_only(tmp_path, monkeypatch, arcgis):
    online(monkeypatch, True)
    credentials(monkeypatch)
    local_map = plot_with_one_result(tmp_path, monkeypatch)
    assert m.run(parse(["map", "demo", "park_boundaries"])) == 0
    assert arcgis.uploads == []
    assert local_map.exists()


def test_rewilding_map_publish_without_credentials_exits_1_and_says_why(
        tmp_path, monkeypatch, capsys, arcgis):
    online(monkeypatch, True)
    local_map = plot_with_one_result(tmp_path, monkeypatch)
    assert m.run(parse(["map", "demo", "park_boundaries", "--publish"])) == 1
    err = capsys.readouterr().err
    assert "not published" in err and "credentials" in err
    assert str(local_map) in err
    assert arcgis.uploads == []
    assert local_map.exists()
