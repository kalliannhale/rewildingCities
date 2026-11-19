"""
tests/test_publish_door.py ~ the publish door (Sprint 08, D-326 to D-332)

nothing here reaches a network. the bucket is a dict of URLs, the portal is a
fake that keeps items in memory and records every call, the gate is a stub,
and the password is a test value handed to the door. ~
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from canopy.expose import publish as door
from canopy.expose.targets import PublishRefusal, load_targets, registered

DOMAIN = "cdn.example.invalid"
PLOT, ART = "demo", "clerks_points"
SHA1, SHA2 = "a" * 64, "b" * 64
ALLOW1, ALLOW2 = "1" * 64, "2" * 64
PORTAL = "https://portal.example.invalid"


# ── the bucket, by URL ───────────────────────────────────────────────────
def _geojson(n=2):
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-70 - i, 44 + i]},
         "properties": {"name": f"office {i}", "rows_served": i + 1,
                        "review_read_on": "2026-11-01"}} for i in range(n)]}


def bucket(sha=SHA1, allow=ALLOW1, notes=None, table=False):
    notes = {"census_note": "the boundary is the Census Bureau's"} if notes is None else notes
    base = f"https://{DOMAIN}/harvests/{PLOT}/{ART}"
    v = f"{base}/versions/{sha}"
    meta = {"semantic_type": "clerk_office_points", "data_category": "tabular" if table else "vector",
            "geometry_type": None if table else "Point"}
    disp = {"metadata": {"semantic_type": "clerk_office_points", "derived_from": sha,
                         "feature_count": 2, "bbox": [-71.0, 44.0, -70.0, 45.0],
                         "lineage": {"kind": "preparation", "run": "clerks", "method": "$m"}},
            "provenance": [{"primitive": "make_display_copy",
                            "publication": [{"step": "rounded", "detail": "6 places"}]}],
            "warnings": []}
    allow_doc = {"gate": {"context_text": notes, "caveats": [],
                          "license": [{"dataset": "clerks", "term": "geo"}],
                          "publication_steps": [{"step": "format_changed", "detail": "to parquet"}]}}
    return {
        f"{base}/current": json.dumps({"sha256": sha, "allow": allow, "data": "data.parquet"}),
        f"{v}/allow/{allow}.json": json.dumps(allow_doc),
        f"{v}/envelope.json": json.dumps({"metadata": meta}),
        f"{v}/display/web.envelope.json": json.dumps(disp),
        f"{v}/display/web.geojson": json.dumps(_geojson()),
    }


def fetcher(pages):
    def fetch(url):
        body = pages.get(url)
        return None if body is None else body.encode()
    return fetch


def allow_judge(notes=None, refuse_at=None):
    notes = {"census_note": "the boundary is the Census Bureau's"} if notes is None else notes
    def judge(envelope, *, plot, target, sharing_level, plot_dir):
        if refuse_at and target in refuse_at:
            return {"decision": "refuse", "refusals": [
                {"rule": 10, "reason": "the license does not permit it",
                 "would_admit": "a license that permits it"}]}
        return {"decision": "allow", "record": {"sharing_level": sharing_level,
                                                "gate_version": "test", "context_text": notes}}
    return judge


# ── the portal ───────────────────────────────────────────────────────────
class Resp:
    def __init__(self, doc):
        self.doc = doc

    def json(self):
        return self.doc


class FakePortal:
    """an ArcGIS portal in memory: items, folders, and every call it was asked."""

    def __init__(self, username="RDS_NU", fail=False):
        self.username = username
        self.fail = fail
        self.items: dict[str, dict] = {}
        self.folders = []
        self.calls = []
        self.n = 0

    def _path(self, url):
        return url.split("/sharing/rest/", 1)[1]

    def get(self, url, params=None, headers=None, timeout=None):
        path = self._path(url)
        self.calls.append(("get", path, dict(params or {})))
        if self.fail:
            return Resp({"error": {"code": 500, "message": "the portal is down"}})
        if path == "community/self":
            return Resp({"username": self.username})
        if path == "":
            return Resp({"currentVersion": "2026.3"})
        if path.startswith("content/users/") and path.count("/") == 2:
            return Resp({"folders": list(self.folders)})
        if path.startswith("content/items/"):
            parts = path.split("/")
            item = self.items.get(parts[2])
            if item is None:
                return Resp({"error": {"code": 400, "message": "Item does not exist or is inaccessible."}})
            if len(parts) == 4 and parts[3] == "data":
                return Resp(json.loads(item["text"]))
            return Resp({"id": parts[2], "owner": item["owner"], "access": item["access"],
                         "description": item["description"], "title": item.get("title")})
        raise AssertionError(f"unexpected GET {path}")

    def post(self, url, data=None, headers=None, timeout=None):
        path = self._path(url)
        data = dict(data or {})
        self.calls.append(("post", path, data))
        if self.fail:
            return Resp({"error": {"code": 500, "message": "the portal is down"}})
        if path == "generateToken":
            if data.get("password") != "test-password":
                return Resp({"error": {"code": 400, "message": "Invalid username or password."}})
            return Resp({"token": "t0ken"})
        if path.endswith("/createFolder"):
            f = {"id": f"folder{len(self.folders)}", "title": data["title"]}
            self.folders.append(f)
            return Resp({"success": True, "folder": f})
        if path.endswith("/addItem"):
            self.n += 1
            item_id = f"item{self.n}"
            self.items[item_id] = {"owner": path.split("/")[2], "access": "private",
                                   "description": data["description"], "text": data["text"],
                                   "title": data["title"]}
            return Resp({"success": True, "id": item_id})
        if path.endswith("/update"):
            item = self.items[path.split("/")[4]]
            item["description"] = data["description"]
            if "text" in data:
                item["text"] = data["text"]
            if "title" in data:
                item["title"] = data["title"]
            return Resp({"success": True})
        if path.endswith("/share"):
            item = self.items[path.split("/")[4]]
            item["access"] = ("public" if data["everyone"] == "true" else
                              "org" if data["org"] == "true" else "private")
            return Resp({"notSharedWith": []})
        raise AssertionError(f"unexpected POST {path}")

    def posts(self, ending):
        return [c for c in self.calls if c[0] == "post" and c[1].endswith(ending)]


# ── the plot ─────────────────────────────────────────────────────────────
def garden(tmp_path, targets=None):
    lic = tmp_path / "seeds" / "licenses"
    lic.mkdir(parents=True)
    (lic / "licenses.yml").write_text(yaml.safe_dump({"terms": {"geo": {
        "name": "Maine GeoLibrary data", "permits": ["private", "organization", "public"],
        "attribution": "required", "verified": True, "basis": "test"}}}))
    pub = tmp_path / "plots" / PLOT / "publish"
    pub.mkdir(parents=True)
    targets = targets or {"test": {"kind": "arcgis", "portal": PORTAL, "owner": "RDS_NU",
                                   "owner_kind": "institutional", "folder": "rc test",
                                   "sharing": "private", "groups": []}}
    (pub / "targets.yml").write_text(yaml.safe_dump({"targets": targets}))
    return tmp_path


def run(root, pages, portal, *, targets=("test",), write=True, judge=None, asked=None, **kw):
    asked = asked if asked is not None else []
    def ask(prompt):
        asked.append(prompt)
        return "test-password"
    kinds = kw.pop("kinds", None) or registered(http=portal)
    return door.publish(PLOT, ART, list(targets), root=root, write=write,
                        by="tester" if write else None, reason="a test" if write else None,
                        domain=DOMAIN, fetch=fetcher(pages), judge=judge or allow_judge(),
                        kinds=kinds, ask=ask, now="2026-11-17T00:00:00+00:00", **kw)


def record(root):
    return yaml.safe_load((root / "plots" / PLOT / "publish" / "published.yml").read_text())


# ── a dry run ────────────────────────────────────────────────────────────
def test_a_dry_run_signs_in_nowhere_and_writes_nothing(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    [o] = run(root, bucket(), portal, write=False)
    assert o.outcome == "would publish"
    assert portal.calls == []
    assert not (root / "plots" / PLOT / "publish" / "published.yml").exists()
    assert any("signed in nowhere" in line for line in o.lines)


# ── create, then the same truth again ────────────────────────────────────
def test_the_first_push_creates_and_records_the_version_it_shows(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    [o] = run(root, bucket(), portal)
    assert o.outcome == "published"
    [(item_id, item)] = portal.items.items()
    assert item["owner"] == "RDS_NU" and item["access"] == "private"
    layer = json.loads(item["text"])["operationalLayers"][0]
    assert layer["url"].endswith(f"/versions/{SHA1}/display/web.geojson")
    entry = record(root)["targets"]["test"][ART]
    assert entry["item_id"] == item_id and entry["sha256"] == SHA1 and entry["allow"] == ALLOW1
    assert entry["moved_by"] == "tester" and entry["previous"] is None
    assert portal.folders == [{"id": "folder0", "title": "rc test"}]


def test_a_second_push_of_the_same_truth_changes_nothing(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    run(root, bucket(), portal)
    before = len(portal.calls)
    [o] = run(root, bucket(), portal)
    assert o.outcome == "unchanged"
    assert len(portal.calls) == before and len(portal.items) == 1


# ── moves ────────────────────────────────────────────────────────────────
def test_a_new_version_moves_the_url_and_keeps_a_persons_style(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    run(root, bucket(), portal)
    [item] = portal.items.values()
    data = json.loads(item["text"])
    data["operationalLayers"][0]["layerDefinition"]["drawingInfo"] = {"renderer": {"type": "simple"}}
    data["operationalLayers"][0]["popupInfo"]["title"] = "a person chose this"
    item["text"] = json.dumps(data)
    [o] = run(root, bucket(sha=SHA2, allow=ALLOW2), portal)
    assert o.outcome == "updated" and len(portal.items) == 1
    layer = json.loads(item["text"])["operationalLayers"][0]
    assert f"/versions/{SHA2}/" in layer["url"]
    assert layer["layerDefinition"]["drawingInfo"] == {"renderer": {"type": "simple"}}
    assert layer["popupInfo"]["title"] == "a person chose this"
    entry = record(root)["targets"]["test"][ART]
    assert entry["sha256"] == SHA2 and entry["previous"] == {"sha256": SHA1, "allow": ALLOW1}


def test_a_new_allow_record_moves_the_description_alone(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    run(root, bucket(), portal)
    settled = {"census_note": "settled on the nation's terms"}
    [o] = run(root, bucket(allow=ALLOW2, notes=settled), portal, judge=allow_judge(settled))
    assert o.outcome == "updated"
    [update] = portal.posts("/update")
    assert "text" not in update[2]
    assert "settled on the nation" in next(iter(portal.items.values()))["description"]


# ── the item as it stands ────────────────────────────────────────────────
def test_a_deleted_item_waits_for_replace(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    run(root, bucket(), portal)
    portal.items.clear()
    [o] = run(root, bucket(sha=SHA2), portal)
    assert o.outcome == "refused" and any("--replace" in line for line in o.lines)
    assert record(root)["targets"]["test"][ART]["sha256"] == SHA1
    [o] = run(root, bucket(sha=SHA2), portal, replace=True)
    assert o.outcome == "published" and len(portal.items) == 1
    assert record(root)["targets"]["test"][ART]["sha256"] == SHA2


def test_a_layer_url_changed_by_hand_is_refused(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    run(root, bucket(), portal)
    [item] = portal.items.values()
    data = json.loads(item["text"])
    data["operationalLayers"][0]["url"] = "https://elsewhere.invalid/x.geojson"
    item["text"] = json.dumps(data)
    [o] = run(root, bucket(sha=SHA2), portal)
    assert o.outcome == "refused" and any("changed by hand" in line for line in o.lines)
    assert portal.posts("/update") == []


def test_a_description_changed_by_hand_is_refused(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    run(root, bucket(), portal)
    next(iter(portal.items.values()))["description"] = "someone's own words"
    [o] = run(root, bucket(sha=SHA2), portal)
    assert o.outcome == "refused" and any("description" in line for line in o.lines)


# ── who signs in ─────────────────────────────────────────────────────────
def test_a_sign_in_that_is_not_the_owner_writes_nothing(tmp_path):
    root, portal = garden(tmp_path), FakePortal(username="someone_else")
    [o] = run(root, bucket(), portal)
    assert o.outcome == "refused" and any("not RDS_NU" in line for line in o.lines)
    assert portal.items == {} and portal.posts("/addItem") == []


def test_one_password_serves_every_target_of_one_account(tmp_path):
    t = {"kind": "arcgis", "portal": PORTAL, "owner": "RDS_NU",
         "owner_kind": "institutional", "folder": "f", "sharing": "private", "groups": []}
    root, portal, asked = garden(tmp_path, {"test": t, "library": dict(t, sharing="organization")}), FakePortal(), []
    outs = run(root, bucket(), portal, targets=("test", "library"), asked=asked)
    assert [o.outcome for o in outs] == ["published", "published"]
    assert len(asked) == 1 and len(portal.items) == 2
    assert sorted(i["access"] for i in portal.items.values()) == ["org", "private"]


def test_a_personal_owner_is_warned_about(tmp_path):
    t = {"kind": "arcgis", "portal": PORTAL, "owner": "RDS_NU",
         "owner_kind": "personal", "folder": "f", "sharing": "private", "groups": []}
    root, portal = garden(tmp_path, {"test": t}), FakePortal()
    [o] = run(root, bucket(), portal, write=False)
    assert any("R7" in line for line in o.lines)


# ── one target's trouble is its own ──────────────────────────────────────
def test_one_failing_target_never_stops_the_others(tmp_path):
    t = {"kind": "arcgis", "owner": "RDS_NU", "owner_kind": "institutional",
         "folder": "f", "sharing": "private", "groups": []}
    root = garden(tmp_path, {"down": dict(t, portal="https://down.invalid"),
                             "test": dict(t, portal=PORTAL)})
    up, down = FakePortal(), FakePortal(fail=True)

    class Both:
        def get(self, url, **kw):
            return (down if url.startswith("https://down.invalid") else up).get(url, **kw)

        def post(self, url, **kw):
            return (down if url.startswith("https://down.invalid") else up).post(url, **kw)

    outs = run(root, bucket(), None, targets=("down", "test"), kinds=registered(http=Both()))
    assert [o.outcome for o in outs] == ["refused", "published"]
    assert list(record(root)["targets"]) == ["test"]


def test_a_gate_refusal_stops_that_target_only(tmp_path):
    t = {"kind": "arcgis", "portal": PORTAL, "owner": "RDS_NU",
         "owner_kind": "institutional", "folder": "f", "sharing": "private", "groups": []}
    root, portal = garden(tmp_path, {"test": t, "partner": dict(t, sharing="public")}), FakePortal()
    outs = run(root, bucket(), portal, targets=("partner", "test"),
               judge=allow_judge(refuse_at={"partner"}))
    assert [o.outcome for o in outs] == ["refused", "published"]
    assert any("rule 10" in line for line in outs[0].lines)


def test_a_note_that_reads_otherwise_than_the_bucket_is_refused(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    [o] = run(root, bucket(), portal, judge=allow_judge({"census_note": "new words, unwritten"}))
    assert o.outcome == "refused" and any("D-320" in line for line in o.lines)
    assert portal.calls == []


# ── adopting a hand-made map ─────────────────────────────────────────────
def test_a_hand_made_map_is_adopted_and_keeps_its_style(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    old_url = f"https://{DOMAIN}/harvests/{PLOT}/{ART}/versions/{'c' * 64}/display/web.geojson"
    portal.items["5fcd"] = {"owner": "RDS_NU", "access": "private", "description": "by hand",
                            "text": json.dumps({"operationalLayers": [
                                {"id": "1a1e-layer-2", "url": old_url, "layerType": "GeoJSON",
                                 "popupInfo": {"title": "GeoJSON: {name}"},
                                 "layerDefinition": {"fields": [{"name": "review_read_on",
                                                                 "type": "esriFieldTypeDate"}]}}]})}
    [o] = run(root, bucket(), portal, adopt="5fcd")
    assert o.outcome == "published" and list(portal.items) == ["5fcd"]
    layer = json.loads(portal.items["5fcd"]["text"])["operationalLayers"][0]
    assert f"/versions/{SHA1}/" in layer["url"]
    assert layer["popupInfo"]["title"] == "GeoJSON: {name}"
    types = {f["name"]: f["type"] for f in layer["layerDefinition"]["fields"]}
    assert types["review_read_on"] == "esriFieldTypeString"
    entry = record(root)["targets"]["test"][ART]
    assert entry["item_id"] == "5fcd" and entry["layer_id"] == "1a1e-layer-2"


def test_adopting_a_map_that_reads_another_harvest_is_refused(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    portal.items["x"] = {"owner": "RDS_NU", "access": "private", "description": "",
                         "text": json.dumps({"operationalLayers": [
                             {"id": "l", "url": "https://elsewhere.invalid/a.geojson"}]})}
    [o] = run(root, bucket(), portal, adopt="x")
    assert o.outcome == "refused" and portal.posts("/update") == []


# ── what reaches the door ────────────────────────────────────────────────
def test_a_table_reaches_the_door_and_is_told_what_would_draw_it(tmp_path):
    root = garden(tmp_path)
    with pytest.raises(PublishRefusal) as e:
        run(root, bucket(table=True), FakePortal(), write=False)
    assert "--join" in e.value.would_admit


def test_a_harvest_never_written_says_so(tmp_path):
    root = garden(tmp_path)
    with pytest.raises(PublishRefusal) as e:
        run(root, {}, FakePortal(), write=False)
    assert "--write" in e.value.would_admit


def test_targets_are_read_loudly(tmp_path):
    root = garden(tmp_path, {"test": {"kind": "arcgis", "portal": PORTAL,
                                      "owner": "RDS_NU", "owner_kind": "institutional",
                                      "folder": "f", "sharing": "private",
                                      "password": "never here"}})
    with pytest.raises(PublishRefusal) as e:
        load_targets(root / "plots" / PLOT, registered())
    assert "password" in e.value.reason


# ── the command ──────────────────────────────────────────────────────────
def _args(argv):
    import argparse
    from canopy.cli import publish as cli
    parser = argparse.ArgumentParser()
    cli.register(parser.add_subparsers())
    return cli, parser.parse_args(argv)


def test_the_command_asks_for_who_and_why_before_it_writes(capsys):
    cli, args = _args(["publish", PLOT, ART, "--to", "test", "--write"])
    assert cli.run(args) == 2
    assert "--by and --reason" in capsys.readouterr().err


def test_the_command_needs_a_target_and_adopts_into_one(capsys):
    cli, args = _args(["publish", PLOT, ART])
    assert cli.run(args) == 2
    cli, args = _args(["publish", PLOT, ART, "--to", "a", "--to", "b", "--write",
                       "--by", "k", "--reason", "r", "--adopt", "x"])
    assert cli.run(args) == 2
    assert "one item, in one target" in capsys.readouterr().err


def test_a_share_that_fails_after_create_leaves_a_record_that_owes_it(tmp_path):
    root, portal = garden(tmp_path), FakePortal()
    real = portal.post

    def post(url, data=None, **kw):
        if url.endswith("/share"):
            raise ConnectionError("the network dropped")
        return real(url, data=data, **kw)
    portal.post = post
    [o] = run(root, bucket(), portal)
    assert o.outcome == "failed" and len(portal.items) == 1
    assert record(root)["targets"]["test"][ART]["sharing"] is None
    portal.post = real
    [o] = run(root, bucket(), portal)
    assert o.outcome == "updated" and len(portal.items) == 1
    assert record(root)["targets"]["test"][ART]["sharing"] == "private"
