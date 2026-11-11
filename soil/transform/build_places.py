"""
soil/transform/build_places.py  |  rewildingCities

The places table (Sprint 04, Contract 3): one row per place at every level,
keyed by (authority, code), with what the place is, the Census's own status
for it, its flags and the context note that must travel with it.

A place's `kind` says what it is in words a reader can use: town, plantation,
city, unorganized territory, reservation subdivision, gore, and so on. The
Census's functional status is kept verbatim in `census_funcstat`, never shown
as a bare word: in Maine all 23 cities are F, as are the four reservation
subdivisions, and "fictitious" beside Portland would be false (D-128, FUNC-2).

  state, county       the ACS 2024 county table's names; counties 2024 (D-127)
  cousub (towns)      2024 TIGER/Line county subdivisions: kind from LSAD,
                      census_funcstat from FUNCSTAT; towns 2024 (D-126)
  sldl, sldu          the ACS 2024 district tables' names
  aiannh              the Census's 2020 legal areas, keyed by GEOID (D-125),
                      each with the census_tribal_area context note (D-123)
  megis_division      Maine's 923 civil divisions (MEGIS-2), with LURC

A reservation subdivision is found by geometry, never by name: a town whose
every 2020 block lies in a Census reservation (R). It carries the context
note, and `part_of` names the tribal area it belongs to, so Penobscot Indian
Island's two Census subdivisions in two counties read as one place, the
Penobscot Reservation, without inventing a code (PEN-1, D-129).

A place that is not itself a tribal boundary but holds any 2020 block of a
Census tribal area, reservation (R) or trust land (T), carries the tribal
note's merged form, contains_census_tribal_area, at every level: the state, a
county, a town partly in a reservation or holding trust land, a district, a
civil division (D-158). Houlton, Littleton and Old Town are such towns. No
share threshold: "all or part" is true of a sliver too, and a sliver that is
only boundary noise is a finding about the edges, not a judgment to bury here.

The table's own metadata lists its notes for the gate (Contract 1, rule 9,
D-156): context_notes, every note it carries, its own type's note
census_tribal_places included; row_context_notes, the notes its rows carry.
Before step 6 it listed none, and the gate refused it (NOTE-1).

LURC (D-130): a civil division is under LURC if any of its polygons says so;
one whose polygons disagree is also flagged lurc_mixed. A town is flagged lurc
if any of its blocks lies in a LURC division, and lurc_share_population says
how many of its people do.

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:
  spine             the block spine (build_block_spine)
  edges             the graph's edges (build_place_edges)
  subdivisions      tl_2024_<state>_cousub.zip (its .dbf is read)
  counties          ACS county table with GEOID, NAME
  house, senate     ACS lower and upper district tables with GEOID, NAME
  reservations      Census 2020 reservations (geojson, properties read)
  trust_lands       Census 2020 off-reservation trust lands (as above)
  divisions         MEGIS divisions, dissolved (geojson, GEOCODE and TOWN)
  division_polygons MEGIS divisions, undissolved (geojson, GEOCODE and LURC)
  division_blocks   blocks assigned to divisions (GEOID, division)
Params:
  state_fips  two digits, required
  state_name  the state's name, required
  vintages    required mapping: state, county, town, sldl, sldu, aiannh, division
Output: the places table, parquet or csv by the output's extension.
Refuses: towns in the spine and the 2024 layer that differ; an LSAD with no
kind; a reservation subdivision by LSAD that geometry does not confirm, or the
reverse; a key used twice; an edge end with no place; an edge family whose
vintage differs from the vintage these params declare for it (D-162); a
tribal place without its note; the tribal note on a place that is not a
tribal boundary.
"""

from __future__ import annotations

import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from canopy.pr_io import (parse_primitive_args, get_input, require_param,
                              WarningsCollector, primitive_success, primitive_failure,
                              primitive_error_handling)
except ImportError:
    from pr_io import (parse_primitive_args, get_input, require_param,
                       WarningsCollector, primitive_success, primitive_failure,
                       primitive_error_handling)

from build_block_spine import read_dbf  # noqa: E402  (the reader the spine's tests cover)

GEOID, SLDL, SLDU, AIANNH, MEGIS = ("us_census_geoid", "us_census_sldl", "us_census_sldu",
                                    "us_census_aiannh", "megis")
# note texts live in seeds/notes/notes.yml (D-157). CONTAINS_NOTE is
# TRIBAL_NOTE's when_merged there; tests/test_places.py holds the two equal
TRIBAL_NOTE = "census_tribal_area"
CONTAINS_NOTE = "contains_census_tribal_area"
TABLE_NOTE = "census_tribal_places"
COLUMNS = ["authority", "code", "level", "kind", "vintage", "name", "census_funcstat",
           "flags", "context_note", "part_of_authority", "part_of_code",
           "lurc_share_population"]

# Maine's legal/statistical area descriptions, as the 2024 layer carries them
# (places probe, 2026-11-10): one kind per code. a code not here is refused
LSAD_KIND = {"43": "town", "39": "plantation", "25": "city", "46": "unorganized_territory",
             "86": "reservation_subdivision", "31": "gore"}
FUNCSTAT_KNOWN = set("ASFNE")
COUSUB_FIELDS = ["GEOID", "NAMELSAD", "LSAD", "FUNCSTAT"]


def read_table(path):
    import pandas as pd
    if str(path).endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype=str)


def write_table(frame, path):
    if str(path).endswith(".parquet"):
        frame.to_parquet(path, index=False)
    else:
        frame.assign(flags=frame["flags"].map(";".join)).to_csv(path, index=False)


def properties(path):
    import pandas as pd
    with open(path) as f:
        return pd.DataFrame([feat["properties"] for feat in json.load(f)["features"]])


def read_subdivisions(path):
    with zipfile.ZipFile(path) as z:
        dbf = [n for n in z.namelist() if n.lower().endswith("_cousub.dbf")]
        if len(dbf) != 1:
            primitive_failure("Subdivision table not found",
                              f"expected one _cousub.dbf in {path}; found {dbf}")
        return read_dbf(z.read(dbf[0]), COUSUB_FIELDS, dbf[0])


def row(authority, code, level, kind, vintage, name, funcstat=None, flags=(),
        note=None, part_of=(None, None), lurc_share=None):
    return {"authority": authority, "code": str(code), "level": level, "kind": kind,
            "vintage": vintage, "name": name, "census_funcstat": funcstat,
            "flags": list(flags), "context_note": note,
            "part_of_authority": part_of[0], "part_of_code": part_of[1],
            "lurc_share_population": lurc_share}


def context_metadata(places):
    """what the gate reads instead of the rows (D-156): the notes the rows
    carry, and every note the table carries, its own type's included."""
    rows = sorted({n for n in places["context_note"] if isinstance(n, str) and n})
    return {"context_notes": sorted(set(rows) | {TABLE_NOTE}), "row_context_notes": rows}


def zero_flags(persons, households):
    out = []
    if persons == 0:
        out.append("zero_population")
    if households == 0:
        out.append("zero_households")
    return out


def build(spine, edges, subdivisions, counties, house, senate, reservations, trust_lands,
          divisions, division_polygons, division_blocks, state_fips, state_name, vintages, w):
    import pandas as pd
    for need in ("state", "county", "town", "sldl", "sldu", "aiannh", "division"):
        if not vintages.get(need):
            primitive_failure("Missing vintage", f"vintages.{need} is required")

    spine = spine.copy()
    has_ai = spine["aiannh"].notna()
    spine["aiannh_geoid"] = (spine["aiannh"].astype(str)
                             + spine["aiannh_comptyp"].astype(str)).where(has_ai)
    rows = []

    # which places hold any tribal block, R or T, at each level (D-158)
    tribal_blocks = spine[has_ai]

    def holding(col):
        return set(tribal_blocks[col].dropna().astype(str))

    def contains_note(code, held):
        return CONTAINS_NOTE if str(code) in held else None

    # the state and its counties
    st = spine[["persons", "households"]].sum()
    rows.append(row(GEOID, state_fips, "state", "state", vintages["state"], state_name,
                    flags=zero_flags(st["persons"], st["households"]),
                    note=CONTAINS_NOTE if has_ai.any() else None))
    county_held = holding("county")
    names = counties.assign(GEOID=counties["GEOID"].astype(str)).set_index("GEOID")["NAME"]
    by_county = spine.groupby("county")[["persons", "households"]].sum()
    for code, n in by_county.iterrows():
        if code not in names.index:
            primitive_failure("County without a name",
                              f"{code} is in the spine but not in the ACS county table")
        rows.append(row(GEOID, code, "county", "county", vintages["county"], names[code],
                        flags=zero_flags(n["persons"], n["households"]),
                        note=contains_note(code, county_held)))

    # towns, from the 2024 layer (D-126, D-128)
    sub = subdivisions.assign(GEOID=subdivisions["GEOID"].astype(str))
    spine_towns, layer_towns = set(spine["cousub"]), set(sub["GEOID"])
    if spine_towns != layer_towns:
        primitive_failure("Towns differ from the 2024 layer",
                          f"in the spine only: {sorted(spine_towns - layer_towns)[:5]}; "
                          f"in the layer only: {sorted(layer_towns - spine_towns)[:5]}")
    unknown_lsad = sorted(set(sub["LSAD"]) - set(LSAD_KIND))
    if unknown_lsad:
        primitive_failure("Unknown kind of town",
                          f"LSAD {unknown_lsad} has no kind; a reader would not know what "
                          f"the place is. Add it to LSAD_KIND with its meaning")

    blocks = spine.groupby("cousub").agg(
        blocks=("GEOID", "size"), persons=("persons", "sum"),
        households=("households", "sum"),
        in_r=("aiannh_comptyp", lambda c: int((c == "R").sum())))
    r_area = (spine[spine["aiannh_comptyp"] == "R"].groupby("cousub")["aiannh_geoid"]
              .agg(lambda g: sorted(set(g))))

    lurc_poly = division_polygons.assign(
        GEOCODE=division_polygons["GEOCODE"].astype(str),
        LURC=division_polygons["LURC"].astype(str).str.lower())
    lurc_values = lurc_poly.groupby("GEOCODE")["LURC"].agg(lambda v: set(v))
    lurc_division = {code for code, v in lurc_values.items() if "y" in v}
    lurc_mixed = {code for code, v in lurc_values.items() if len(v) > 1}
    placed = division_blocks.dropna(subset=["division"]).assign(
        division=lambda d: d["division"].astype(str))
    in_lurc = spine.merge(placed[["GEOID", "division"]], on="GEOID", how="left")
    in_lurc["lurc"] = in_lurc["division"].isin(lurc_division)
    in_lurc["lurc_persons"] = in_lurc["persons"].where(in_lurc["lurc"], 0)
    lurc_town = in_lurc.groupby("cousub").agg(any_block=("lurc", "any"),
                                              persons=("lurc_persons", "sum"))
    town_held = holding("cousub")

    for t in sub.sort_values("GEOID").itertuples(index=False):
        b = blocks.loc[t.GEOID]
        kind = LSAD_KIND[t.LSAD]
        by_geometry = b["blocks"] == b["in_r"]
        if (kind == "reservation_subdivision") != bool(by_geometry):
            primitive_failure("Reservation subdivision not confirmed",
                              f"{t.GEOID} {t.NAMELSAD}: LSAD says {kind}, but "
                              f"{b['in_r']} of its {b['blocks']} block(s) lie in a reservation")
        flags = zero_flags(b["persons"], b["households"])
        if t.FUNCSTAT not in FUNCSTAT_KNOWN:
            flags.append("funcstat_unknown")
        share = None
        if lurc_town.loc[t.GEOID, "any_block"]:
            flags.append("lurc")
            if b["persons"] > 0:
                share = lurc_town.loc[t.GEOID, "persons"] / b["persons"]
        note, part = contains_note(t.GEOID, town_held), (None, None)
        if kind == "reservation_subdivision":
            areas = r_area.get(t.GEOID, [])
            if len(areas) != 1:
                primitive_failure("Reservation subdivision in two reservations",
                                  f"{t.GEOID}: its blocks lie in {areas}")
            note, part = TRIBAL_NOTE, (AIANNH, areas[0])
        rows.append(row(GEOID, t.GEOID, "cousub", kind, vintages["town"], t.NAMELSAD,
                        funcstat=t.FUNCSTAT, flags=flags, note=note, part_of=part,
                        lurc_share=share))

    # districts, named as the ACS publishes them
    for level, auth, table, col in (("sldl", SLDL, house, "sldl"), ("sldu", SLDU, senate, "sldu")):
        dnames = table.assign(GEOID=table["GEOID"].astype(str)).set_index("GEOID")["NAME"]
        by = spine.groupby(col)[["persons", "households"]].sum()
        held = holding(col)
        for code, n in by.iterrows():
            if code not in dnames.index:
                primitive_failure("District without a name",
                                  f"{auth} {code} is in the spine but not in its ACS table")
            kind = "house_district" if level == "sldl" else "senate_district"
            rows.append(row(auth, code, level, kind, vintages[level], dnames[code],
                            flags=zero_flags(n["persons"], n["households"]),
                            note=contains_note(code, held)))

    # Census tribal areas, the legal areas only (D-123, D-125)
    by_area = spine.dropna(subset=["aiannh_geoid"]).groupby("aiannh_geoid")[
        ["persons", "households"]].sum()
    for layer, kind in ((reservations, "tribal_reservation"), (trust_lands, "tribal_trust_land")):
        for a in layer.itertuples(index=False):
            code = str(a.GEOID)
            n = by_area.loc[code] if code in by_area.index else pd.Series(
                {"persons": 0, "households": 0})
            rows.append(row(AIANNH, code, "aiannh", kind, vintages["aiannh"], a.NAME,
                            flags=zero_flags(n["persons"], n["households"]), note=TRIBAL_NOTE))

    # Maine's own civil divisions (MEGIS-2, D-130)
    edged = set(edges.loc[edges["from_authority"] == MEGIS, "from_code"].astype(str))
    division_held = set(placed.merge(tribal_blocks[["GEOID"]], on="GEOID")["division"])
    for d in divisions.assign(GEOCODE=divisions["GEOCODE"].astype(str)).itertuples(index=False):
        flags = []
        if d.GEOCODE in lurc_division:
            flags.append("lurc")
        if d.GEOCODE in lurc_mixed:
            flags.append("lurc_mixed")
        if d.GEOCODE not in edged:
            flags.append("no_block_points")
        rows.append(row(MEGIS, d.GEOCODE, "megis_division", "civil_division",
                        vintages["division"], d.TOWN, flags=flags,
                        note=contains_note(d.GEOCODE, division_held)))

    places = pd.DataFrame(rows)[COLUMNS]

    # checks, each a Contract 3 invariant
    dup = places.duplicated(["authority", "code"])
    if dup.any():
        first = places[dup].iloc[0]
        primitive_failure("Place key used twice",
                          f"{int(dup.sum())} key(s), e.g. ({first['authority']}, {first['code']})")
    keys = set(zip(places["authority"], places["code"].astype(str)))
    ends = edges[edges["kind"].isin(["contains", "overlaps"])]
    missing = set()
    for a, c in (("from_authority", "from_code"), ("to_authority", "to_code")):
        missing |= set(zip(ends[a], ends[c].astype(str))) - keys
    if missing:
        primitive_failure("Edge end without a place",
                          f"{len(missing)} edge end(s) name no place, e.g. {sorted(missing)[0]}")
    # an edge's vintage is its places' (D-162). the edges step and this step
    # declare their vintages apart, so a change to one that misses the other
    # is refused here. a family with no edges is skipped; located_in is not
    # checked, since no step writes it yet (Sprint 06)
    is_overlap = edges["kind"] == "overlaps"
    families = (
        ("contains", edges["kind"] == "contains", "town"),
        ("overlaps to House districts", is_overlap & (edges["to_authority"] == SLDL), "sldl"),
        ("overlaps to Senate districts", is_overlap & (edges["to_authority"] == SLDU), "sldu"),
        ("overlaps to Census tribal areas", is_overlap & (edges["to_authority"] == AIANNH),
         "aiannh"),
        ("overlaps from civil divisions", is_overlap & (edges["from_authority"] == MEGIS),
         "division"),
    )
    for label, mask, key in families:
        found = sorted(set(edges.loc[mask, "vintage"].astype(str)))
        if found and found != [str(vintages[key])]:
            primitive_failure("Edge vintage differs from its places'",
                              f"{label}: the edges carry {found}, the places declare "
                              f"vintages.{key} {str(vintages[key])!r} (D-162)")
    tribal = places[(places["level"] == "aiannh")
                    | (places["kind"] == "reservation_subdivision")]
    unnoted = tribal[tribal["context_note"] != TRIBAL_NOTE]
    if len(unnoted):
        primitive_failure("Tribal place without its note",
                          f"{len(unnoted)} place(s), e.g. {unnoted.iloc[0]['code']}")
    misnoted = places[(places["context_note"] == TRIBAL_NOTE) & ~places.index.isin(tribal.index)]
    if len(misnoted):
        primitive_failure("Tribal note on a place that is not a tribal boundary",
                          f"{len(misnoted)} place(s), e.g. {misnoted.iloc[0]['code']}; such a "
                          f"place carries {CONTAINS_NOTE} (D-158)")

    w.info("places: " + ", ".join(f"{k} {v}" for k, v in
                                  places["level"].value_counts().sort_index().items()))
    w.info("town kinds: " + ", ".join(f"{k} {v}" for k, v in
                                      places.loc[places["level"] == "cousub", "kind"]
                                      .value_counts().items()))
    held = places[places["context_note"] == CONTAINS_NOTE]
    w.info(f"{len(held)} place(s) hold a Census tribal area in whole or part and carry "
           f"{CONTAINS_NOTE}: " + ", ".join(f"{k} {v}" for k, v in
                                            held["level"].value_counts().sort_index().items()))
    w.info(f"{int(places['flags'].map(lambda f: 'lurc' in f).sum())} place(s) flagged lurc; "
           f"{len(lurc_mixed)} division(s) lurc_mixed")
    return places


def main():
    args = parse_primitive_args()
    w = WarningsCollector("build_places")
    with primitive_error_handling(w):
        p, i = args["params"], args["inputs"]
        places = build(
            read_table(get_input(i, "spine")), read_table(get_input(i, "edges")),
            read_subdivisions(get_input(i, "subdivisions")),
            read_table(get_input(i, "counties")), read_table(get_input(i, "house")),
            read_table(get_input(i, "senate")),
            properties(get_input(i, "reservations")), properties(get_input(i, "trust_lands")),
            properties(get_input(i, "divisions")), properties(get_input(i, "division_polygons")),
            read_table(get_input(i, "division_blocks")),
            str(require_param(p, "state_fips")).zfill(2), require_param(p, "state_name"),
            require_param(p, "vintages"), w)
        write_table(places, args["output"])
        primitive_success({"data_category": "tabular", "crs": None, "row_count": len(places),
                           "variables": COLUMNS, **context_metadata(places)}, w)


if __name__ == "__main__":
    main()
