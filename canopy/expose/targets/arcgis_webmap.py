"""
canopy/expose/targets/arcgis_webmap.py ~ a web map in an ArcGIS portal, by REST

the door's first target kind (D-326). it owns web map items, and each layer in
one reads a display copy from CloudFront by URL, so ArcGIS stores the map and
none of the features (D-325, MP-71). it speaks ArcGIS's REST API through
requests, with no Esri package (D-329), so it works the same against ArcGIS
Online and any ArcGIS Enterprise portal, and tests replace the HTTP with a fake.

what the door owns in an item, and nothing else (D-328): the layer's URL and
fields, the description (which carries the notes, Contract 2 section 4), and
the credits. a person may restyle the map in Map Viewer (renderer, popup,
basemap, title) and the door keeps every bit of it when the truth moves.

the web map's JSON follows Esri's web map specification, version 2.38: a
GeoJSON layer references a public file and keeps a reference, never a copy.
field types come from the display copy's own values, never guessed: Map
Viewer typed review_read_on as a date and every number as a double, and the
data holds neither (D-333). __OBJECTID is the field Map Viewer adds for a
GeoJSON layer; the door declares it the same way.

a choropleth (D-331) is a table drawn on an outline, and its renderer is the
door's, since its legend is a claim: a standing is coloured in fixed fifths of
its reference population, higher always the better standing, named in the
layer's title; a count is drawn as markers sized in equal steps, zero its own
class; any other value in equal steps, said so. a place with no value is
hatched (esriSFSBackwardDiagonal) or crossed, and labelled. its popup shows
the place and the one indicator mapped; the other indicators' fields stay in
the layer, hidden.

REST calls, as Esri documents them (cited in the ledger, Sprint 08 session 1):
generateToken for a token from a username and password, over HTTPS only;
addItem with the item's JSON as text, which makes the folder's owner the
item's owner and leaves it private until Share Item; Update and Share at the
user item resource. community/self, a user's folders and createFolder are
used as the portal answers them, and the first write against a real portal
is their check. ~
"""

from __future__ import annotations

import copy as _copy
import hashlib
import html
import json
import math

from .base import Built, PublishRefusal, Target, TargetKind

KIND = "arcgis_webmap"
SPEC_VERSION = "2.38"
OBJECTID = "__OBJECTID"
TOKEN_MINUTES = 60
_R = 6378137.0

# Map Viewer's Topographic basemap, as the first hand-made map holds it
# (D-325's web map, read 2026-11-16). a person may change it; the door keeps theirs.
BASEMAP = {
    "baseMapLayers": [
        {"id": "World_Hillshade_3805", "opacity": 1, "title": "World Hillshade",
         "url": "https://services.arcgisonline.com/arcgis/rest/services/Elevation/"
                "World_Hillshade/MapServer",
         "visibility": True, "layerType": "ArcGISTiledMapServiceLayer"},
        {"id": "rewilding-topographic", "opacity": 1, "title": "World Topographic Map",
         "visibility": True, "layerType": "VectorTileLayer",
         "styleUrl": "https://cdn.arcgis.com/sharing/rest/content/items/"
                     "27e89eb03c1e4341a1d75e597f0291e6/resources/styles/root.json"},
    ],
    "title": "Topographic",
}
WEB_MERCATOR = {"wkid": 102100, "latestWkid": 3857}


class PortalError(Exception):
    def __init__(self, code, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- the REST client ---------------------------------------------------------

class Portal:
    """the few REST calls the door makes. http is anything with get(url,
    params=..., headers=..., timeout=...) and post(url, data=..., headers=...,
    timeout=...) returning an object with .json(); requests.Session by default."""

    def __init__(self, base: str, http=None):
        self.base = base.rstrip("/")
        if http is None:
            import requests
            http = requests.Session()
        self.http = http
        self.headers = {"Referer": self.base}

    def _url(self, path: str) -> str:
        return f"{self.base}/sharing/rest/{path}"

    @staticmethod
    def _read(resp) -> dict:
        doc = resp.json()
        if isinstance(doc, dict) and "error" in doc:
            err = doc["error"] or {}
            raise PortalError(err.get("code"), err.get("message") or "the portal refused")
        return doc

    def get(self, path: str, token: str | None = None, **params) -> dict:
        params = dict(params, f="json")
        if token:
            params["token"] = token
        return self._read(self.http.get(self._url(path), params=params,
                                        headers=self.headers, timeout=60))

    def post(self, path: str, token: str | None = None, **data) -> dict:
        data = dict(data, f="json")
        if token:
            data["token"] = token
        return self._read(self.http.post(self._url(path), data=data,
                                         headers=self.headers, timeout=60))

    def token(self, username: str, password: str) -> str:
        doc = self.post("generateToken", username=username, password=password,
                        client="referer", referer=self.base, expiration=TOKEN_MINUTES)
        return doc["token"]

    def rest_version(self) -> str | None:
        try:
            return str(self.get("").get("currentVersion"))
        except Exception:
            return None

    def item(self, item_id: str, token: str) -> dict | None:
        try:
            return self.get(f"content/items/{item_id}", token)
        except PortalError as e:
            said = (e.message or "").lower()
            if e.code in (400, 404) or "not exist" in said or "inaccessible" in said:
                return None
            raise

    def folder_id(self, owner: str, title: str, token: str) -> str:
        doc = self.get(f"content/users/{owner}", token)
        for f in doc.get("folders") or []:
            if f.get("title") == title:
                return f["id"]
        made = self.post(f"content/users/{owner}/createFolder", token, title=title)
        return (made.get("folder") or {})["id"]


# --- what the door writes ----------------------------------------------------

def _esri_type(values: list) -> tuple[str, int | None]:
    """a field's type from the values the layer will read. a JSON number that
    is always whole is an integer; any other number a double; everything else,
    a date written as text included, is text (D-324 writes dates as ISO text)."""
    seen = [v for v in values if v is not None]
    if seen and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in seen):
        whole = all(float(v).is_integer() for v in seen)
        if whole and all(-2**31 <= v < 2**31 for v in seen):
            return "esriFieldTypeInteger", None
        return "esriFieldTypeDouble", None
    longest = max((len(v if isinstance(v, str) else json.dumps(v)) for v in seen), default=0)
    return "esriFieldTypeString", max(256, longest)


def fields_of(geojson: dict) -> list[dict]:
    features = geojson.get("features") or []
    names: list[str] = []
    for f in features:
        for k in (f.get("properties") or {}):
            if k not in names:
                names.append(k)
    out = [{"name": OBJECTID, "alias": OBJECTID, "type": "esriFieldTypeOID",
            "editable": False, "nullable": False}]
    for n in names:
        kind, length = _esri_type([(f.get("properties") or {}).get(n) for f in features])
        field = {"name": n, "alias": n, "type": kind, "editable": False, "nullable": True}
        if length:
            field["length"] = length
        out.append(field)
    return out


def _mercator(lon: float, lat: float) -> tuple[float, float]:
    lat = max(min(lat, 85.0511), -85.0511)
    return (_R * math.radians(lon),
            _R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def extent_of(bbox) -> dict | None:
    """the copy's own bbox (EPSG:4326), in Web Mercator with a little margin."""
    if not bbox or len(bbox) != 4:
        return None
    x0, y0 = _mercator(bbox[0], bbox[1])
    x1, y1 = _mercator(bbox[2], bbox[3])
    pad_x = max((x1 - x0) * 0.05, 500.0)
    pad_y = max((y1 - y0) * 0.05, 500.0)
    return {"spatialReference": dict(WEB_MERCATOR), "xmin": x0 - pad_x, "ymin": y0 - pad_y,
            "xmax": x1 + pad_x, "ymax": y1 + pad_y}


# a sequential ramp, light to dark, each step distinct to colour-blind
# readers (ColorBrewer YlGnBu, five classes): darker is a better standing
RAMP = ([255, 255, 204], [161, 218, 180], [65, 182, 196], [44, 127, 184], [37, 52, 148])
NO_VALUE_FILL = {"type": "esriSFS", "style": "esriSFSBackwardDiagonal",
                 "color": [110, 110, 110, 255],
                 "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                             "color": [110, 110, 110, 255], "width": 0.75}}
NO_VALUE_MARK = {"type": "esriSMS", "style": "esriSMSX", "color": [110, 110, 110, 255],
                 "size": 7, "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                                        "color": [110, 110, 110, 255], "width": 1}}
_NUMERIC = ("esriFieldTypeInteger", "esriFieldTypeDouble")


def _fill(rgb) -> dict:
    return {"type": "esriSFS", "style": "esriSFSSolid", "color": list(rgb) + [217],
            "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                        "color": [255, 255, 255, 255], "width": 0.75}}


def _mark(size: float, hollow: bool = False) -> dict:
    return {"type": "esriSMS", "style": "esriSMSCircle",
            "color": [0, 0, 0, 0] if hollow else [37, 52, 148, 200], "size": size,
            "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                        "color": [80, 80, 80, 255] if hollow else [255, 255, 255, 255],
                        "width": 1}}


def _number(x: float) -> str:
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.2f}"


def choropleth_of(copy: dict, fields: list[dict]) -> tuple[dict, str, str]:
    """(renderer, colour field, legend title) for a joined copy's indicator.
    refuses a field that holds no number, since a renderer on it draws nothing."""
    from canopy.choropleth import ChoroplethRefusal, colour_field, column_name
    meta = copy["display_env"].get("metadata") or {}
    join = meta.get("join") or {}
    ind, markers = copy["indicator"], bool(copy.get("markers"))
    try:
        field = colour_field(ind, join.get("columns") or {}, markers=markers)
    except ChoroplethRefusal as e:
        raise PublishRefusal(e.reason, e.would_admit) from None
    kind = {f["name"]: f["type"] for f in fields}.get(field)
    if kind not in _NUMERIC:
        raise PublishRefusal(f"'{field}' holds no number in this copy, so a renderer on it "
                             f"would draw nothing", "map an indicator with values here")
    values = [v for v in ((f.get("properties") or {}).get(field)
                          for f in copy["geojson"].get("features") or [])
              if isinstance(v, (int, float)) and not isinstance(v, bool)]
    level = (meta.get("joined_to") or {}).get("level") or "place"
    empty = f"no value here; its {column_name(ind, 'empty_reason')} says why, where it is given"

    if field == column_name(ind, "percentile"):
        ref = (((meta.get("reference_population") or {}).get("per_indicator") or {})
               .get(ind) or {}).get("n")
        if not ref:
            raise PublishRefusal(f"the standing of {ind} names no reference population, so its "
                                 f"fifths cannot be said", "a standings table names it")
        names = ("lowest", "second", "middle", "fourth", "highest")
        infos = [{"classMaxValue": 20 * (i + 1), "symbol": _fill(RAMP[i]),
                  "label": f"{names[i]} fifth ({'0' if i == 0 else f'above {20 * i}'} "
                           f"to {20 * (i + 1)})"} for i in range(5)]
        renderer = {"type": "classBreaks", "field": field, "minValue": 0,
                    "classBreakInfos": infos, "defaultSymbol": NO_VALUE_FILL,
                    "defaultLabel": empty}
        title = (f"{ind} by {level}: standing in fifths of the {int(ref):,} places with a "
                 f"value, higher is better ({copy['plot']})")
        return renderer, field, title

    if not values:
        raise PublishRefusal(f"'{field}' holds no value in any place of this copy",
                             "map an indicator with values here")
    if markers:
        top = max(values)
        infos = []
        if min(values) <= 0:
            infos.append({"classMaxValue": 0, "symbol": _mark(5, hollow=True),
                          "label": "none listed"})
        if top > 0:
            k = int(min(4, top)) if float(top).is_integer() else 4
            step = top / k
            lo = 0.0
            for i in range(k):
                hi = top if i == k - 1 else (round(step * (i + 1)) if float(top).is_integer()
                                             else step * (i + 1))
                first = (int(lo) + 1) if float(top).is_integer() else lo
                label = (_number(hi) if first == hi else f"{_number(first)} to {_number(hi)}")
                infos.append({"classMaxValue": hi, "symbol": _mark(8 + 4 * i), "label": label})
                lo = hi
        renderer = {"type": "classBreaks", "field": field, "minValue": 0,
                    "classBreakInfos": infos, "defaultSymbol": NO_VALUE_MARK,
                    "defaultLabel": empty}
        title = (f"{ind} by {level}, one marker per place, sized in equal steps from 1 to "
                 f"{_number(top)}; none listed is its own class ({copy['plot']})")
        return renderer, field, title

    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    infos = [{"classMaxValue": hi if i == 4 else lo + span * (i + 1) / 5,
              "symbol": _fill(RAMP[i]),
              "label": f"{_number(lo + span * i / 5)} to {_number(hi if i == 4 else lo + span * (i + 1) / 5)}"}
             for i in range(5)]
    renderer = {"type": "classBreaks", "field": field, "minValue": lo,
                "classBreakInfos": infos, "defaultSymbol": NO_VALUE_FILL, "defaultLabel": empty}
    title = (f"{ind} by {level}, in five equal steps from {_number(lo)} to {_number(hi)}, "
             f"not a standard ({copy['plot']})")
    return renderer, field, title


def _visible(copy: dict, name: str) -> bool:
    """in a choropleth's popup: the place's own fields and the one indicator mapped."""
    if name in (OBJECTID, "joined"):
        return False
    if not copy.get("outline"):
        return True
    if "__" not in name:
        return True
    return name.startswith(copy["indicator"] + "__")


def layer_of(copy: dict, layer_id: str, fields: list[dict]) -> dict:
    names = [f["name"] for f in fields]
    title_field = "name" if "name" in names else None
    if copy.get("outline"):
        return _choropleth_layer(copy, layer_id, fields, names, title_field)
    return {
        "id": layer_id,
        "title": copy["title"],
        "url": copy["url"],
        "layerType": "GeoJSON",
        "visibility": True,
        "opacity": 1,
        "layerDefinition": {"fields": fields, "objectIdField": OBJECTID},
        "popupInfo": {
            "title": "{" + title_field + "}" if title_field else copy["title"],
            "popupElements": [{"type": "fields"}],
            "showAttachments": False,
            "fieldInfos": [{"fieldName": n, "label": n, "isEditable": False,
                            "visible": n != OBJECTID} for n in names],
        },
    }


def _choropleth_layer(copy, layer_id, fields, names, title_field) -> dict:
    renderer, field, title = choropleth_of(copy, fields)
    return {
        "id": layer_id,
        "title": title[:256],
        "url": copy["url"],
        "layerType": "GeoJSON",
        "visibility": True,
        "opacity": 1,
        "layerDefinition": {"fields": fields, "objectIdField": OBJECTID,
                            "drawingInfo": {"renderer": renderer}},
        "popupInfo": {
            "title": "{" + title_field + "}" if title_field else title[:256],
            "popupElements": [{"type": "fields"}],
            "showAttachments": False,
            "fieldInfos": [{"fieldName": n, "label": n, "isEditable": False,
                            "visible": _visible(copy, n)} for n in names],
        },
    }


def renderer_sha256_of(renderer: dict | None) -> str | None:
    return None if renderer is None else sha256_text(json.dumps(renderer, sort_keys=True))


def webmap_of(copy: dict, layer_id: str, version: str) -> dict:
    fields = fields_of(copy["geojson"])
    doc = {
        "operationalLayers": [layer_of(copy, layer_id, fields)],
        "baseMap": _copy.deepcopy(BASEMAP),
        "spatialReference": dict(WEB_MERCATOR),
        "authoringApp": "rewildingCities",
        "authoringAppVersion": version,
        "version": SPEC_VERSION,
    }
    extent = extent_of((copy["display_env"].get("metadata") or {}).get("bbox"))
    if extent:
        doc["initialState"] = {"viewpoint": {"targetGeometry": extent}}
    return doc


def _li(items) -> str:
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>" if items else "<p>none</p>"


def description_of(copy: dict, version: str) -> tuple[str, str, str]:
    """(description, license_info, access_information), from the bucket's
    records alone, with no time in them: the same records always write the
    same words, so a description that differs from the record was edited."""
    e = html.escape
    meta = copy["display_env"].get("metadata") or {}
    gate = copy["allow_doc"].get("gate") or {}
    lineage = meta.get("lineage") or {}
    licenses = copy.get("licenses") or {}
    base = copy["version_url"]

    outline = copy.get("outline")
    gates = [gate] + ([outline["allow_doc"].get("gate") or {}] if outline else [])
    notes: dict = {}
    for g in gates:
        notes.update(g.get("context_text") or {})
    terms, credits, seen = [], [], set()
    for row in [r for g in gates for r in g.get("license") or []]:
        if (row.get("dataset"), row.get("term")) in seen:
            continue
        seen.add((row.get("dataset"), row.get("term")))
        term = licenses.get(row.get("term")) or {}
        label = term.get("name") or row.get("term")
        terms.append(f"{e(str(row.get('dataset')))}: {e(str(label))} ({e(str(row.get('term')))})")
        if term.get("attribution") == "required":
            credits.append(str(label))
    steps = [f"{e(str(s.get('step')))}: {e(str(s.get('detail')))}"
             for g in gates for s in (g.get("publication_steps") or [])]
    own = (copy["display_env"].get("provenance") or [{}])[-1]
    steps += [f"{e(str(s.get('step')))}: {e(str(s.get('detail')))}"
              for s in (own.get("publication") or [])]
    warnings = [e(str(w.get("message") or w)) for w in copy["display_env"].get("warnings") or []]
    caveats = [e(str(c)) for g in gates for c in g.get("caveats") or []]

    parts = [
        f"<p><b>{e(str(meta.get('semantic_type') or copy['artifact']))}</b> for the "
        f"{e(copy['plot'])} plot: {e(str(meta.get('feature_count', '')))} features, "
        f"drawn from canonical version <code>{copy['sha256']}</code>.</p>",
        "<p><b>This layer reads a public URL.</b> This item's sharing decides who finds "
        "the map, not who can read the data.</p>",
        *(_drawn_on(copy, meta) if outline else []),
        "<h3>Context notes</h3>",
        _li([f"<b>{e(k)}</b>: {e(str(v))}" for k, v in sorted(notes.items())]),
        "<h3>Where its truth lives</h3>",
        _li([f"version: <code>{e(base)}/</code>",
             f"receipt: <code>{e(base)}/envelope.json</code>",
             f"allow record: <code>{e(base)}/allow/{copy['allow']}.json</code>",
             f"display copy: <code>{e(copy['url'])}</code>"]),
        "<h3>Method</h3>",
        _li([f"{e(k)}: {e(str(lineage.get(k)))}" for k in ("kind", "method", "run", "curiosity")
             if lineage.get(k)]),
        "<h3>License</h3>", _li(terms),
        "<h3>Caveats and warnings</h3>", _li(caveats + warnings),
        "<h3>What changed on the way out</h3>", _li(steps),
        f"<p>Made by the rewildingCities publish door {e(version)}. Edit the map's "
        f"style freely; the door rewrites this description, which carries the notes.</p>",
    ]
    description = "\n".join(parts)
    license_info = "; ".join(sorted({str((licenses.get(r.get("term")) or {}).get("name")
                                          or r.get("term"))
                                     for g in gates for r in g.get("license") or []}))
    access = "; ".join(sorted(set(credits))) + ("; " if credits else "") + \
        "rewildingCities canonical store"
    return description, license_info, access


def _drawn_on(copy: dict, meta: dict) -> list[str]:
    """what a choropleth's description adds: the outline it is drawn on, the
    join's counts, and what its colours mean."""
    e = html.escape
    o, join = copy["outline"], meta.get("join") or {}
    c = join.get("counts") or {}
    ref = meta.get("reference_population") or {}
    lines = [
        f"<p><b>{e(copy['indicator'])}</b>, one indicator of this copy, drawn on "
        f"<b>{e(o['harvest'])}</b> version <code>{o['sha256']}</code>, allow record "
        f"<code>{o['allow']}</code>, joined on its authority and code.</p>",
        _li([f"{c.get('places', 0) - c.get('places_without_row', 0)} of {c.get('places', 0)} "
             f"places with a row; {c.get('places_without_row', 0)} drawn with no value",
             f"{c.get('rows_outside_outline', 0)} of the table's rows belong to places outside "
             f"this map, {c.get('rows_other_level', 0)} to another level, "
             f"{c.get('rows_other_authority', 0)} to another authority",
             f"the outline's version: <code>{e(o['version_url'])}/</code>"]),
    ]
    if ref.get("rule"):
        lines.append(f"<p>A standing compares each place with its reference population "
                     f"({e(str(ref.get('rule')))}); it says how a place compares, never "
                     f"whether its value is enough.</p>")
    return lines


# --- the kind ----------------------------------------------------------------

class ArcGISWebMap(TargetKind):
    name = KIND

    def __init__(self, http=None, version: str = "1.0.0"):
        self.http = http
        self.version = version

    def build(self, target: Target, copy: dict) -> Built:
        layer_id = "rewilding-" + str(copy.get("key") or copy["artifact"]).replace("/", "-")
        description, license_info, access = description_of(copy, self.version)
        meta = copy["display_env"].get("metadata") or {}
        snippet = (f"{meta.get('semantic_type') or copy['artifact']} from rewildingCities, "
                   f"version {copy['sha256'][:12]}, read by URL from the canonical store")[:250]
        data = webmap_of(copy, layer_id, self.version)
        tags = ["rewildingCities", copy["plot"], copy["artifact"]]
        extra = {}
        if copy.get("outline"):
            tags += [copy["outline"]["harvest"], copy["indicator"]]
            layer = data["operationalLayers"][0]
            extra["renderer_sha256"] = renderer_sha256_of(
                layer["layerDefinition"]["drawingInfo"]["renderer"])
        return Built(title=copy["title"][:256], snippet=snippet, description=description,
                     tags=tags, license_info=license_info, access_information=access,
                     data=data, layer_id=layer_id, url=copy["url"], extra=extra)

    def sign_in(self, target: Target, password: str):
        portal = Portal(target.portal, self.http)
        try:
            token = portal.token(target.owner, password)
        except PortalError as e:
            raise PublishRefusal(f"{target.portal} refused the sign-in as {target.owner}: "
                                 f"{e.message}", "check the username and password") from None
        return {"portal": portal, "token": token}

    def whoami(self, session) -> str:
        return session["portal"].get("community/self", session["token"]).get("username")

    def rest_version(self, session) -> str | None:
        return session["portal"].rest_version()

    def read(self, session, item_id: str) -> dict | None:
        portal, token = session["portal"], session["token"]
        item = portal.item(item_id, token)
        if item is None:
            return None
        data = portal.get(f"content/items/{item_id}/data", token)
        return {"owner": item.get("owner"), "access": item.get("access"),
                "description": item.get("description") or "", "data": data}

    def _fields(self, built: Built, data: dict | None) -> dict:
        out = {"description": built.description, "licenseInfo": built.license_info,
               "accessInformation": built.access_information}
        if data is not None:
            out["text"] = json.dumps(data)
        return out

    def create(self, session, target: Target, built: Built) -> str:
        portal, token = session["portal"], session["token"]
        folder = portal.folder_id(target.owner, target.folder, token)
        doc = portal.post(f"content/users/{target.owner}/{folder}/addItem", token,
                          type="Web Map", title=built.title, snippet=built.snippet,
                          tags=",".join(built.tags), **self._fields(built, built.data))
        return doc["id"]

    def update(self, session, target: Target, item_id: str, built: Built, *,
               data: dict | None) -> None:
        session["portal"].post(f"content/users/{target.owner}/items/{item_id}/update",
                               session["token"], **self._fields(built, data))

    def share(self, session, target: Target, item_id: str) -> None:
        session["portal"].post(f"content/users/{target.owner}/items/{item_id}/share",
                               session["token"],
                               everyone=str(target.sharing == "public").lower(),
                               org=str(target.sharing in ("organization", "public")).lower(),
                               groups=",".join(target.groups))

    @staticmethod
    def _layers(data: dict) -> list:
        return (data or {}).get("operationalLayers") or []

    def layer_url(self, data: dict, layer_id: str) -> str | None:
        for layer in self._layers(data):
            if layer.get("id") == layer_id:
                return layer.get("url")
        return None

    def moved(self, data: dict, layer_id: str, built: Built) -> dict:
        new = _copy.deepcopy(data)
        ours = built.data["operationalLayers"][0]
        for layer in self._layers(new):
            if layer.get("id") == layer_id:
                layer["url"] = built.url
                ld = layer.setdefault("layerDefinition", {})
                ld["fields"] = ours["layerDefinition"]["fields"]
                ld["objectIdField"] = OBJECTID
                if built.extra.get("renderer_sha256"):
                    ld["drawingInfo"] = _copy.deepcopy(ours["layerDefinition"]["drawingInfo"])
                    layer["title"] = ours["title"]
                return new
        raise PublishRefusal(f"the item holds no layer '{layer_id}'",
                             "the record and the item disagree; read both before going on")

    def renderer_sha256(self, data: dict, layer_id: str) -> str | None:
        """the hash of the renderer a layer draws with, as it stands."""
        for layer in self._layers(data):
            if layer.get("id") == layer_id:
                return renderer_sha256_of(((layer.get("layerDefinition") or {})
                                           .get("drawingInfo") or {}).get("renderer"))
        return None

    def adoptable_layer(self, data: dict, url_prefix: str) -> tuple[str, str] | None:
        hits = [(l.get("id"), l.get("url")) for l in self._layers(data)
                if str(l.get("url") or "").startswith(url_prefix)]
        if len(hits) > 1:
            raise PublishRefusal(f"{len(hits)} layers in the item read this harvest",
                                 "adopt a map with one layer per harvest")
        return hits[0] if hits else None
