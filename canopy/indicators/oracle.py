"""
canopy/indicators/oracle.py

the later stages of CII's method, in Python, so the R primitives that perform
them can be held to an independent implementation (D-16, D-37):

  impute()          two-stage nearest neighbour, for a unit missing exactly
                    one indicator: the ten most similar complete units by the
                    sum of absolute z differences across the other indicators,
                    then the geographically closest of those ten
  weighted_index()  a weighted mean per pillar, only where every component is
                    present, then CII's percentile; or the same across pillars
                    for the composite

rules recovered from CII's published file (CII-12):
  ~ exactly 461 counties are missing one indicator, and every one has all five
    pillars and an overall index: those are the imputed
  ~ a county missing two or more has no overall index, and keeps only the
    pillars with no gap: a pillar with a missing component is dropped, never
    averaged over what remains

written for exact agreement with R, not for speed:
  ~ sums run sequentially in declared order, never fsum, because R's sum on
    this platform is sequential double arithmetic, and a sum taken in a
    different order can differ in the last bit and flip a tie
  ~ every ranking breaks ties on the unit code, so the choice of donor is
    determined, never an accident of row order
♡
"""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088  # mean radius, IUGG


def _present(v) -> float | None:
    """a value, or None for anything missing: None, NaN, pandas NA. a NaN that
    passes as present poisons every sum it joins (IDX-1). ~"""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    # squared as s * s, not s ** 2, in both languages: R's ^2 and Python's **
    # take different paths, and a donor chosen by distance must not hinge on it
    s1 = math.sin((lat2 - lat1) / 2)
    s2 = math.sin((lon2 - lon1) / 2)
    h = s1 * s1 + math.cos(lat1) * math.cos(lat2) * (s2 * s2)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def _matrix(rows: list[dict], ids: list[str]) -> tuple[dict, dict, set]:
    """unit -> {indicator: z}, unit -> name, and units outside by declaration."""
    z: dict[str, dict[str, float | None]] = {}
    names: dict[str, str] = {}
    declared_out: set[str] = set()
    for r in rows:
        if r["indicator"] not in ids:
            continue
        code = r["unit_code"]
        z.setdefault(code, {i: None for i in ids})[r["indicator"]] = _present(r.get("z"))
        names[code] = r.get("name", "")
        reason = r.get("outside_reason")
        reason = reason if isinstance(reason, str) else ""
        if reason.startswith("outside the reference population (state"):
            declared_out.add(code)
    return z, names, declared_out


def impute(rows: list[dict], ids: list[str], locations: dict[str, tuple[float, float]],
           *, k: int = 10, missing_exactly: int = 1) -> tuple[list[dict], list[dict]]:
    """returns (rows with imputed z filled and flagged, one record per imputation)."""
    z, names, declared_out = _matrix(rows, ids)
    units = sorted(u for u in z if u not in declared_out)
    missing = {u: [i for i in ids if z[u][i] is None] for u in units}
    donors = [u for u in units if not missing[u]]

    records: list[dict] = []
    filled: dict[tuple[str, str], dict] = {}
    for u in units:
        if len(missing[u]) != missing_exactly:
            continue
        target = missing[u][0]
        others = [i for i in ids if i != target]
        scored = []
        for d in donors:
            acc = 0.0
            for i in others:
                acc = acc + abs(z[u][i] - z[d][i])
            scored.append((acc, d))
        scored.sort(key=lambda t: (t[0], t[1]))
        shortlist = scored[:k]
        rec = {"unit_code": u, "name": names.get(u, ""), "indicator": target,
               "shortlist": [d for _, d in shortlist], "donor": None,
               "similarity": None, "distance_km": None, "reason": None}
        if u not in locations:
            rec["reason"] = "no location for this unit, so the geographic stage cannot run"
        else:
            placed = [(haversine_km(locations[u], locations[d]), s, d)
                      for s, d in shortlist if d in locations]
            if not placed:
                rec["reason"] = "none of the ten most similar units has a location"
            else:
                km, s, d = min(placed, key=lambda t: (t[0], t[1], t[2]))
                rec.update(donor=d, similarity=s, distance_km=km)
                filled[(u, target)] = rec
        records.append(rec)

    out = []
    for r in rows:
        row = dict(r)
        row.setdefault("imputed", False)
        row.setdefault("imputed_from", None)
        rec = filled.get((r["unit_code"], r["indicator"]))
        if rec:
            row["z"] = z[rec["donor"]][r["indicator"]]
            row["imputed"] = True
            row["imputed_from"] = rec["donor"]
            row["outside_reason"] = None
        out.append(row)
    return out, records


def _cii_percentile(scores: dict[str, float]) -> dict[str, float]:
    """average rank over the largest rank, times 100 (CII-8). higher is better."""
    order = sorted(scores, key=lambda u: scores[u])
    ranks: dict[str, float] = {}
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg = (i + 1 + j + 1) / 2
        for kk in range(i, j + 1):
            ranks[order[kk]] = avg
        i = j + 1
    top = max(ranks.values()) if ranks else 1.0
    return {u: ranks[u] / top * 100 for u in scores}


def weighted_index(rows: list[dict], weights: dict, level: str) -> list[dict]:
    """pillar indices from standings (level 'pillars'), or the composite from
    pillar indices (level 'composite'). a unit gets an index only when every
    component is present."""
    pillars = weights["pillars"]
    if level == "pillars":
        value_of: dict[str, dict[str, float | None]] = {}
        imputed_of: dict[str, set] = {}
        names: dict[str, str] = {}
        for r in rows:
            value_of.setdefault(r["unit_code"], {})[r["indicator"]] = _present(r.get("z"))
            names[r["unit_code"]] = r.get("name", "")
            if r.get("imputed") is True:
                imputed_of.setdefault(r["unit_code"], set()).add(r["indicator"])
        groups = [(pid, p["name"], p["components"]) for pid, p in pillars.items()]
    elif level == "composite":
        value_of, imputed_of, names = {}, {}, {}
        for r in rows:
            value_of.setdefault(r["unit_code"], {})[r["index"]] = _present(r.get("percentile"))
            names[r["unit_code"]] = r.get("name", "")
        groups = [("overall", "Overall Index", {pid: p["chips"] for pid, p in pillars.items()})]
    else:
        raise ValueError(f"level must be 'pillars' or 'composite', not {level!r}")

    out = []
    for gid, gname, comps in groups:
        scores: dict[str, float] = {}
        missing_of: dict[str, list[str]] = {}
        for u in sorted(value_of):
            vals = value_of[u]
            gap = [c for c in comps if vals.get(c) is None]
            if gap:
                missing_of[u] = gap
                continue
            num = 0.0
            den = 0.0
            for c, chips in comps.items():
                num = num + chips * vals[c]
                den = den + chips
            scores[u] = num / den
        pct = _cii_percentile(scores)
        for u in sorted(value_of):
            gap = missing_of.get(u, [])
            out.append({
                "unit_code": u, "name": names.get(u, ""), "index": gid, "index_name": gname,
                "score": scores.get(u), "percentile": pct.get(u),
                "n_components": len(comps), "missing_components": ", ".join(gap) or None,
                "n_imputed_components": len(imputed_of.get(u, set()) & set(comps)),
            })
    return out
