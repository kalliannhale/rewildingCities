"""
tests/test_adopt_app.py ~ `publish --adopt-app` (zip 9b2, D-366)

the hand-built Experience Builder app is recorded, never built, by the door:
refused when it is a rehearsal the plot lists, not an app, owned by another
account, outside the target's folder, or never published. recorded, it names
the hash of its published config and every item it reads, and warns of any
the door did not make. `--check` reads it again: a config published since,
another folder or another sharing is said. the portal is the door's fake,
taught the few app calls. ~
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

from canopy.cli import publish as cli
from canopy.expose import publish as door
from canopy.expose.targets import registered

_spec = importlib.util.spec_from_file_location(
    "_door_fakes", Path(__file__).with_name("test_publish_door.py"))
fakes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fakes)

PLOT = "demo"
APP, REHEARSAL = "app1", "05b3d08a86174f78a725e77e7d833a1e"
CONFIG = {"dataSources": {"places": {"itemId": "places1"}, "lens": {"itemId": "lens1"}},
          "widgets": {"map": {"useDataSources": [{"dataSourceId": "places"}]}}}


class AppPortal(fakes.FakePortal):
    """the fake portal, with apps: an item's type and folder, the owner's
    folders, and the published config as an item resource."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.folders = [{"id": "f1", "title": "rc explorer"}, {"id": "f2", "title": "elsewhere"}]
        self.apps = {}

    def add_app(self, item_id, *, owner="RDS_NU", folder="f1", config=CONFIG,
                kind="Web Experience", access="public"):
        self.apps[item_id] = {"owner": owner, "ownerFolder": folder, "config": config,
                              "type": kind, "access": access, "title": "Maine explorer"}

    def get(self, url, params=None, headers=None, timeout=None):
        path = self._path(url)
        parts = path.split("/")
        if path.startswith("content/items/") and parts[2] in self.apps:
            self.calls.append(("get", path, dict(params or {})))
            app = self.apps[parts[2]]
            if len(parts) == 3:
                return fakes.Resp({"id": parts[2], "owner": app["owner"], "access": app["access"],
                                   "type": app["type"], "title": app["title"],
                                   "ownerFolder": app["ownerFolder"], "description": ""})
            if parts[3:] == ["resources", "config", "config.json"]:
                if app["config"] is None:
                    return fakes.Resp({"error": {"code": 404, "message": "Resource does not exist"}})
                return fakes.Resp(app["config"])
        return super().get(url, params=params, headers=headers, timeout=timeout)


def garden(tmp_path):
    root = fakes.garden(tmp_path, {"explorer": {
        "kind": "arcgis", "portal": fakes.PORTAL, "owner": "RDS_NU",
        "owner_kind": "institutional", "folder": "rc explorer", "sharing": "public",
        "groups": []}})
    pub = root / "plots" / PLOT / "publish"
    (pub / "rehearsals.yml").write_text(yaml.safe_dump({"never_adopt": {REHEARSAL: "read_9a"}}))
    (pub / "published.yml").write_text(yaml.safe_dump({"targets": {"explorer": {
        "places": {"kind": "arcgis_places_map", "item_id": "places1"}}}}))
    return root


def adopt(root, portal, item=APP, write=True):
    return door.adopt_app(PLOT, item, "explorer", root=root, write=write,
                          by="tester", reason="a test", kinds=registered(http=portal),
                          ask=lambda p: "test-password", now="2026-11-18T00:00:00+00:00")


def entry(root):
    return door.read_record(root / "plots" / PLOT)["targets"]["explorer"].get(door.APP_KEY)


def test_the_app_is_recorded_with_its_config_hash_and_what_it_reads(tmp_path):
    root, portal = garden(tmp_path), AppPortal()
    portal.add_app(APP)
    o = adopt(root, portal)
    assert o.outcome == "published", o.lines
    e = entry(root)
    assert e["kind"] == "arcgis_app" and e["config_sha256"] == door.config_sha256(CONFIG)
    assert e["reads"] == ["places1", "lens1"] and e["foreign"] == ["lens1"]
    assert any("lens1, which the door did not make" in line for line in o.lines)


def test_a_rehearsal_is_refused_before_any_sign_in(tmp_path):
    root, portal = garden(tmp_path), AppPortal()
    portal.add_app(REHEARSAL)
    o = adopt(root, portal, item=REHEARSAL)
    assert o.outcome == "refused" and portal.calls == []
    assert "rehearsal" in "\n".join(o.lines)


def test_each_refusal_of_d366_is_said(tmp_path):
    cases = {"another owner": dict(owner="someone"), "folder": dict(folder="f2"),
             "never been published": dict(config=None), "not an Experience Builder": dict(kind="Web Map")}
    for said, kw in cases.items():
        root, portal = garden(tmp_path / said.replace(" ", "_")), AppPortal()
        portal.add_app(APP, **kw)
        o = adopt(root, portal)
        assert o.outcome == "refused" and entry(root) is None, said
        assert said.split()[-1] in "\n".join(o.lines), (said, o.lines)


def test_reading_without_write_records_nothing(tmp_path):
    root, portal = garden(tmp_path), AppPortal()
    portal.add_app(APP)
    o = adopt(root, portal, write=False)
    assert o.outcome == "would publish" and entry(root) is None


def test_check_reads_the_app_again(tmp_path):
    root, portal = garden(tmp_path), AppPortal()
    portal.add_app(APP)
    adopt(root, portal)
    rec = door.read_record(root / "plots" / PLOT)
    rec["targets"]["explorer"].pop("places")
    door.write_record(root / "plots" / PLOT, rec)
    kinds = registered(http=portal)
    [o] = door.check(PLOT, ["explorer"], root=root, kinds=kinds, ask=lambda p: "test-password")
    assert o.outcome == "as recorded", o.lines
    portal.apps[APP]["config"] = dict(CONFIG, theme="dark")
    portal.apps[APP]["access"] = "private"
    [o] = door.check(PLOT, ["explorer"], root=root, kinds=kinds, ask=lambda p: "test-password")
    said = "\n".join(o.lines)
    assert o.outcome == "differs" and "published again" in said and "private" in said


def _args(argv):
    import argparse
    parser = argparse.ArgumentParser()
    cli.register(parser.add_subparsers())
    return parser.parse_args(["publish", *argv])


def test_the_command_takes_the_app_only_with_write_and_one_target():
    assert cli._asked_wrongly(_args(["maine", "--adopt-app", APP, "--to", "explorer"]))
    assert cli._asked_wrongly(_args(["maine", "--adopt-app", APP, "--to", "explorer", "--to",
                                     "test", "--write", "--by", "k", "--reason", "r"]))
    assert cli._asked_wrongly(_args(["maine", "--adopt-app", APP, "--to", "explorer", "--write",
                                     "--by", "k", "--reason", "r"])) is None
    assert cli._asked_wrongly(_args(["maine", "--lens", "carriers", "--lens", "carriers",
                                     "--to", "test"]))
    assert cli._asked_wrongly(_args(["maine", "--lens", "carriers", "--to", "test"])) is None


def test_restore_goes_only_with_write_and_a_whole_map():
    assert cli._asked_wrongly(_args(["maine", "--lens", "carriers", "--to", "test", "--restore"]))
    assert cli._asked_wrongly(_args(["maine", "clerks", "--to", "test", "--write", "--by", "k",
                                     "--reason", "r", "--restore"]))
    assert cli._asked_wrongly(_args(["maine", "--places", "--to", "test", "--write", "--by", "k",
                                     "--reason", "r", "--restore"])) is None
