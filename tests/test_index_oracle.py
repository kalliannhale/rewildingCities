"""
tests/test_index_oracle.py

two-stage nearest-neighbour imputation and weighted indices, in the oracle:
the rules recovered from CII's file (CII-12), on small hand-built cases.
"""

from canopy.indicators import oracle as ox

IDS = ["a", "b", "c"]


def standings(table):
    """{unit: [z_a, z_b, z_c]} -> long rows; None is a missing value."""
    rows = []
    for u, zs in table.items():
        for i, z in zip(IDS, zs):
            rows.append({"unit_code": u, "name": u, "indicator": i, "z": z,
                         "outside_reason": None if z is not None else "no value"})
    return rows


def test_stage_one_shortlists_by_similarity_and_stage_two_picks_by_distance():
    table = {"T": [0.0, 0.0, None],
             "D1": [0.1, 0.1, 5.0], "D2": [0.2, 0.2, 6.0], "D3": [3.0, 3.0, 7.0]}
    locs = {"T": (44.0, -70.0), "D1": (40.0, -100.0), "D2": (44.1, -70.1), "D3": (44.0, -70.0)}
    out, recs = ox.impute(standings(table), IDS, locs, k=2)
    rec = recs[0]
    assert rec["shortlist"] == ["D1", "D2"]          # D3 is closest but not similar
    assert rec["donor"] == "D2"                       # nearer of the two most similar
    z = {(r["unit_code"], r["indicator"]): r for r in out}
    assert z[("T", "c")]["z"] == 6.0 and z[("T", "c")]["imputed_from"] == "D2"


def test_two_or_more_missing_is_never_imputed():
    table = {"T": [0.0, None, None], "D1": [0.1, 0.1, 5.0], "D2": [0.2, 0.2, 6.0]}
    out, recs = ox.impute(standings(table), IDS, {u: (0.0, 0.0) for u in table}, k=2)
    assert recs == []
    assert all(not r["imputed"] for r in out)


def test_a_unit_without_a_location_is_left_missing_with_a_reason():
    table = {"T": [0.0, 0.0, None], "D1": [0.1, 0.1, 5.0], "D2": [0.2, 0.2, 6.0]}
    out, recs = ox.impute(standings(table), IDS, {"D1": (0, 0), "D2": (0, 0)}, k=2)
    assert recs[0]["donor"] is None and "no location" in recs[0]["reason"]


def test_ties_break_on_the_unit_code():
    table = {"T": [0.0, 0.0, None], "DB": [0.1, 0.1, 1.0], "DA": [0.1, 0.1, 2.0]}
    _, recs = ox.impute(standings(table), IDS, {u: (0.0, 0.0) for u in table}, k=2)
    assert recs[0]["shortlist"] == ["DA", "DB"] and recs[0]["donor"] == "DA"


def test_nan_counts_as_missing():
    table = {"T": [0.0, 0.0, float("nan")], "D1": [0.1, 0.1, 5.0]}
    _, recs = ox.impute(standings(table), IDS, {u: (0.0, 0.0) for u in table}, k=1)
    assert recs and recs[0]["donor"] == "D1"


W = {"pillars": {
    "p1": {"name": "P one", "chips": 10, "components": {"a": 10, "b": 30}},
    "p2": {"name": "P two", "chips": 30, "components": {"c": 10}}}}


def test_a_pillar_is_a_weighted_mean_and_a_gap_drops_it():
    rows = standings({"U1": [1.0, 3.0, 0.0], "U2": [0.0, None, 1.0], "U3": [2.0, 2.0, 2.0]})
    p = {(r["unit_code"], r["index"]): r for r in ox.weighted_index(rows, W, "pillars")}
    assert p[("U1", "p1")]["score"] == (10 * 1.0 + 30 * 3.0) / 40
    assert p[("U2", "p1")]["score"] is None and p[("U2", "p1")]["missing_components"] == "b"
    assert p[("U2", "p2")]["score"] == 1.0


def test_the_composite_needs_every_pillar():
    rows = standings({"U1": [1.0, 3.0, 0.0], "U2": [0.0, None, 1.0], "U3": [2.0, 2.0, 2.0]})
    pil = ox.weighted_index(rows, W, "pillars")
    comp = {r["unit_code"]: r for r in ox.weighted_index(pil, W, "composite")}
    assert comp["U2"]["percentile"] is None and comp["U2"]["missing_components"] == "p1"
    assert comp["U1"]["percentile"] is not None and comp["U3"]["percentile"] is not None


def test_imputed_components_are_counted_on_the_index():
    rows = standings({"U1": [1.0, 3.0, 0.0]})
    rows[0]["imputed"] = True
    p = {r["index"]: r for r in ox.weighted_index(rows, W, "pillars")}
    assert p["p1"]["n_imputed_components"] == 1 and p["p2"]["n_imputed_components"] == 0


def test_haversine_is_sane():
    assert abs(ox.haversine_km((0, 0), (0, 1)) - 111.195) < 0.01
