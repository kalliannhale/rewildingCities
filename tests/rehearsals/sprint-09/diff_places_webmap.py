"""
diff_places_webmap.py ~ what ArcGIS changed in the rehearsal's web map

rebuilds the map from the same canonical versions, checks it is the map that
was sent, reads the stored map back and lists every place the two differ:
grouped by path pattern first, then the first few by exact path. run it from
the rewildingCities repo root; it writes nothing. session 3 found 16
differences, all whole coordinates stored as integers (D-362). ~
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rehearse_places_webmap as r


def walk(a, b, path="$"):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in b:
                yield path + "." + k, a[k], "(missing)"
            elif k not in a:
                yield path + "." + k, "(missing)", b[k]
            else:
                yield from walk(a[k], b[k], path + "." + k)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            yield path, f"list of {len(a)}", f"list of {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            yield from walk(x, y, f"{path}[{i}]")
    elif a != b or type(a) is not type(b):
        yield path, a, b


def short(v):
    text = json.dumps(v) if not isinstance(v, str) else repr(v)
    return text if len(text) <= 80 else text[:77] + "..."


def main():
    sent = json.loads(r.SENT.read_text())
    domain = os.environ.get(r.DOMAIN_ENV)
    if not domain:
        sys.exit(f"STOP: {r.DOMAIN_ENV} is not set; activate the rewilding env")
    webmap, _report = r.build(f"https://{domain}")
    rebuilt = r.sha(r.canonical(webmap))
    if rebuilt != sent["sha256"]:
        sys.exit(f"STOP: the rebuilt map hashes to {rebuilt[:12]}, not the sent "
                 f"{sent['sha256'][:12]}; a version moved, so this is no comparison")
    print(f"rebuilt map is the sent map ({rebuilt[:12]})")
    _target, _kind, session = r.sign_in(r.ROOT / "plots" / r.PLOT)
    stored = session["portal"].get(f"content/items/{sent['item_id']}/data", session["token"])
    diffs = list(walk(webmap, stored))
    print(f"{len(diffs)} differences")
    patterns = {}
    for path, _a, _b in diffs:
        p = re.sub(r"\[\d+\]", "[]", path)
        patterns[p] = patterns.get(p, 0) + 1
    for p, n in sorted(patterns.items(), key=lambda kv: -kv[1]):
        print(f"  {n:6}  {p}")
    print("first 15, sent then stored:")
    for path, a, b in diffs[:15]:
        print(f"  {path}")
        print(f"      sent   {short(a)}")
        print(f"      stored {short(b)}")


if __name__ == "__main__":
    main()
