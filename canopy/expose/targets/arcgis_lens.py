"""
canopy/expose/targets/arcgis_lens.py ~ a lens as one ArcGIS web map (zip 9b2, D-385)

a lens draws one lane's measures, one group of layers per level (towns, House
districts, Senate districts, counties), in the plan's order. every layer reads
a joined display copy by URL and is coloured by the door's own renderer
(choropleth_of, RAMP-1), so a lens holds no features: it is a few kilobytes
whatever its copies weigh. the first group is visible, and in each group only
its first measure, so turning a group on shows one map, not a stack.

the door owns the whole lens, as it owns the places map (D-380): the map is
sent in D-362's form, recorded by its hash, and any other change to it reads as
changed by hand. an empty lens holds the orientation copy and says, in its
description and its one layer's title, that nothing is placed there yet. ~
"""

from __future__ import annotations

import html

from .arcgis_places import door_form, map_sha256
from .arcgis_webmap import (BASEMAP, MADE_LENS, SPEC_VERSION, WEB_MERCATOR, _li, extent_of,
                            fields_of, layer_of)
from .base import Built


def _layer_id(lens: dict, level: str, indicator: str) -> str:
    return f"rewilding-lens-{lens['lane']}-{level}-{indicator}"


def lens_webmap(lens: dict, version: str) -> tuple[dict, dict]:
    """(the web map in D-362's form, a report of what each group holds)."""
    import copy as _copy
    groups, report = [], {"levels": {}, "empty": False}
    for i, lv in enumerate(lens["levels"]):
        layers = []
        for j, copy in enumerate(lv["layers"]):
            layer = layer_of(copy, _layer_id(lens, lv["level"], copy["indicator"]),
                             fields_of(copy["geojson"]))
            layer["visibility"] = j == 0
            layers.append(layer)
        groups.append({"id": f"rewilding-lens-{lens['lane']}-{lv['level']}",
                       "title": f"{lv['label']} ({lens['plot']})", "layerType": "GroupLayer",
                       "visibility": i == 0, "layers": layers})
        report["levels"][lv["level"]] = [c["indicator"] for c in lv["layers"]]
    first = lens["levels"][0]["layers"][0] if lens["levels"] else lens.get("orientation")
    if not lens["levels"]:
        o = lens["orientation"]
        layer = layer_of(o, f"rewilding-lens-{lens['lane']}-orientation", fields_of(o["geojson"]))
        layer["title"] = (f"No measure is placed in this lens yet: places shown for "
                          f"orientation only ({lens['plot']})")
        groups.append(layer)
        report["empty"] = True
    webmap = {
        "operationalLayers": groups,
        "baseMap": _copy.deepcopy(BASEMAP),
        "spatialReference": dict(WEB_MERCATOR),
        "authoringApp": "rewildingCities",
        "authoringAppVersion": version,
        "version": SPEC_VERSION,
    }
    extent = extent_of(((first or {}).get("display_env", {}).get("metadata") or {}).get("bbox"))
    if extent:
        webmap["initialState"] = {"viewpoint": {"targetGeometry": extent}}
    return door_form(webmap), report


def description_of(lens: dict, report: dict, sha: str, version: str) -> tuple[str, str, str]:
    """(description, license_info, access_information) from the bucket's records
    alone, with no time in them: the same records always write the same words."""
    e = html.escape
    licenses = lens.get("licenses") or {}
    notes, terms, credits, steps, seen = {}, [], [], [], set()
    for p in lens["parents"]:
        for doc in [p["allow_doc"]]:
            gate = doc.get("gate") or {}
            notes.update(gate.get("context_text") or {})
            for row in gate.get("license") or []:
                if (row.get("dataset"), row.get("term")) in seen:
                    continue
                seen.add((row.get("dataset"), row.get("term")))
                term = licenses.get(row.get("term")) or {}
                label = term.get("name") or row.get("term")
                terms.append(f"{e(str(row.get('dataset')))}: {e(str(label))} "
                             f"({e(str(row.get('term')))})")
                if term.get("attribution") == "required":
                    credits.append(str(label))
        own = (p["env"].get("provenance") or [{}])[-1]
        steps += [f"{e(p['role'])}, {e(str(s.get('step')))}: {e(str(s.get('detail')))}"
                  for s in own.get("publication") or []]
    if lens["kind"] == "pillar":
        kind = (f"One of the Civic Information Index's five pillars. A measure is here only "
                f"when it repeats a measure CII itself places in {e(lens['name'])}.")
    else:
        kind = ("A lane rewildingCities draws beside CII's pillars. Every measure here was "
                "placed by rewildingCities, for the reason given below.")
    members = [f"<b>{e(ind)}</b>: {'placed by CII' if m['placed_by'] == 'replicates' else 'placed by rewildingCities'}. {e(m['reason'])}"
               for ind, m in lens["members"].items()]
    drawn = [f"{e(lv['label'])}: " + ", ".join(e(c["indicator"]) for c in lv["layers"])
             for lv in lens["levels"]]
    parts = [
        f"<p><b>{e(lens['name'])}</b>, a lens on the {e(lens['plot'])} plot. {kind} The "
        f"map's own hash is <code>{sha}</code>.</p>",
        "<p>Every layer reads a copy in the canonical store by its address. Darker always "
        "means harder access; a place with no value is hatched, never drawn as zero. Values "
        "only: no place is ranked here.</p>",
        "<h3>What this lens draws</h3>",
        _li(drawn) if drawn else
        "<p>No measure is placed in this lens yet. The places are shown only so the map "
        "has somewhere to stand.</p>",
        "<h3>Its measures, and why each is here</h3>",
        _li(members) if members else "<p>None yet.</p>",
        "<h3>Context notes</h3>",
        _li([f"<b>{e(k)}</b>: {e(str(v))}" for k, v in sorted(notes.items())]),
        "<h3>Where the data is stored</h3>",
        _li([f"{e(p['role'])}: <code>{e(p['url'])}</code> (version <code>{p['sha256']}</code>, "
             f"allow record <code>{p['allow']}</code>)" for p in lens["parents"]]),
        "<h3>License</h3>", _li(terms),
        "<h3>What changed on the way out</h3>", _li(steps),
        *_credit(lens, sha),
        f"<p>Made by the rewildingCities publish door {e(version)}. The door writes this "
        f"whole map and this description; a change made by hand is undone by the next move.</p>",
    ]
    license_info = "; ".join(sorted({str((licenses.get(r.get("term")) or {}).get("name")
                                          or r.get("term"))
                                     for p in lens["parents"]
                                     for r in (p["allow_doc"].get("gate") or {}).get("license")
                                     or []}))
    access = "; ".join(sorted(set(credits))) + ("; " if credits else "") + \
        "rewildingCities canonical store"
    return "\n".join(parts), license_info, access


def _credit(lens: dict, sha: str) -> list[str]:
    c = lens.get("credit")
    if not c:
        return []
    e = html.escape
    url = f"https://{lens['domain']}/harvests/{lens['plot']}/"
    citation = str(c["citation"]).format(title=lens["title"], version=sha[:12], url=url)
    return ["<h3>Credit and citation</h3>",
            _li([e(str(c["credit"])), f"Suggested citation: {e(citation)}",
                 e(str(c["data_guide"]))])]


def build_lens(lens: dict, version: str) -> Built:
    """the item for the lens the door read: its map, its words, its hash."""
    data, report = lens_webmap(lens, version)
    sha = map_sha256(data)
    description, license_info, access = description_of(lens, report, sha, version)
    snippet = (f"{lens['name']}, a lens on the {lens['plot']} plot: values only, darker is "
               f"harder access, read by URL from the canonical store")[:250]
    return Built(title=lens["title"][:256], snippet=snippet, description=description,
                 tags=["rewildingCities", lens["plot"], "lens", lens["lane"]],
                 license_info=license_info, access_information=access, data=data,
                 layer_id="lens", url="",
                 extra={"made": MADE_LENS, "map_sha256": sha, "report": report})
