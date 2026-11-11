"""
soil/transform/build_seats.py  |  rewildingCities

The seats table (Contract 3, section 6): one row per seat per Legislature,
keyed (legislature, chamber, seat_kind, seat_ref).

  district seats  one per House (sldl) and Senate (sldu) place, generated from
                  the places table, so every seat exists whether or not anyone
                  holds it; seat_ref is the district code
  tribal seats    House seats only, one per nation in the declared list, keyed
                  by the nation's name as 3 MRSA §601(1)(A) defines the
                  Wabanaki Nations (D-136); no district, no place link
  holders         from the Legislature's rosters (D-134); a seat the roster
                  names no one for is vacant, which is what vacant means here:
                  the record names no holder

LegiScan's columns are carried and left empty until LegiScan is acquired; it
never fills a field the record leaves empty.

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:
  places   the places table (build_places)
  house    the House roster (maine_legislature provider)
  senate   the Senate roster (maine_legislature provider)
Params:
  legislature   required, e.g. "133"; the rosters do not say
  sworn_in      required, the date the Legislature was sworn in (YYYY-MM-DD);
                a roster fetched before it is refused (D-135)
  tribal_seats  required list of {name, statute_wording (optional)}
  state_fips    two digits, required
Output: the seats table, parquet or csv by the output's extension.
Refuses: an empty roster; a roster fetched before the swearing-in; a holder
with no district (TRIBE-4), or whose district has no place; two holders for
one seat; a district place under the wrong authority; a tribal name declared
twice; a seat key used twice; holders and vacancies that do not add up.
"""

from __future__ import annotations

try:
    from canopy.pr_io import (parse_primitive_args, get_input, require_param,
                              WarningsCollector, primitive_success, primitive_failure,
                              primitive_error_handling)
except ImportError:
    from pr_io import (parse_primitive_args, get_input, require_param,
                       WarningsCollector, primitive_success, primitive_failure,
                       primitive_error_handling)

COLUMNS = ["legislature", "chamber", "seat_kind", "seat_ref", "district_authority",
           "district_code", "statute_wording", "seat_number", "vacant", "holder_name",
           "holder_party", "position", "email", "profile_url", "legiscan_people_id",
           "legiscan_district", "legiscan_agreement", "source", "as_of"]
KEY = ["legislature", "chamber", "seat_kind", "seat_ref"]
# what one row IS: an office for one Legislature, never a place (D-136);
# declared in the receipt with KEY, so loam joins on it (KEYS-1)
SPATIAL_UNIT = "seat"

# which places are seats, in which chamber, under which authority (GRAPH-1)
CHAMBER_OF = {"sldl": ("house", "us_census_sldl"), "sldu": ("senate", "us_census_sldu")}


def read_table(path):
    import pandas as pd
    if str(path).endswith(".parquet"):
        frame = pd.read_parquet(path)
    else:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        frame = frame.replace({"": None})
    return frame.astype(object).where(frame.notna(), None)


def write_table(frame, path):
    if str(path).endswith(".parquet"):
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)


def empty_seat(legislature, chamber, kind, ref, roster_source, roster_as_of):
    row = dict.fromkeys(COLUMNS)
    row.update({"legislature": legislature, "chamber": chamber, "seat_kind": kind,
                "seat_ref": ref, "vacant": True, "source": roster_source,
                "as_of": roster_as_of})
    return row


def roster_stamp(roster, chamber, sworn_in):
    """the record's source and fetch time, the same on every row of a roster."""
    if roster is None or len(roster) == 0:
        primitive_failure("Empty roster", f"the {chamber} roster names no one; a seat "
                          f"cannot be called vacant without the record")
    early = [a for a in roster["as_of"] if str(a)[:10] < sworn_in]
    if early:
        primitive_failure("Roster before the swearing-in",
                          f"the {chamber} roster was fetched {early[0]}, before {sworn_in}; "
                          f"it lists the previous Legislature (D-135)")
    return roster["source"].iloc[0], roster["as_of"].iloc[0]


def build(places, house, senate, legislature, sworn_in, tribal_seats, state_fips, w):
    import pandas as pd

    legislature = str(legislature).strip()
    if not legislature:
        primitive_failure("Missing legislature", "params.legislature is required")
    stamps = {"house": roster_stamp(house, "house", sworn_in),
              "senate": roster_stamp(senate, "senate", sworn_in)}

    # every district place is a seat, held or not
    seats = {}
    for p in places[places["level"].isin(list(CHAMBER_OF))].itertuples(index=False):
        chamber, authority = CHAMBER_OF[p.level]
        if p.authority != authority:
            primitive_failure("District under the wrong authority",
                              f"{p.level} place {p.code} is under {p.authority}, expected {authority}")
        number = str(p.code)[len(state_fips):]
        if not str(p.code).startswith(state_fips) or not number.isdigit():
            primitive_failure("District code not understood",
                              f"{authority} {p.code}: expected {state_fips} and a district number")
        row = empty_seat(legislature, chamber, "district", str(p.code), *stamps[chamber])
        row.update({"district_authority": authority, "district_code": str(p.code)})
        seats[(chamber, int(number))] = row
    for chamber in ("house", "senate"):
        if not any(c == chamber for c, _ in seats):
            primitive_failure("No districts", f"the places table holds no {chamber} districts")

    # holders, from the record
    held = {"house": 0, "senate": 0}
    for roster in (house, senate):
        for r in roster.itertuples(index=False):
            if r.district is None or not str(r.district).strip():
                primitive_failure("Holder with no district",
                                  f"{r.chamber} roster names {r.name} with no district; a tribal "
                                  f"representative cannot be matched to a nation from the record "
                                  f"(TRIBE-4)")
            if not str(r.district).strip().isdigit():
                primitive_failure("District not understood",
                                  f"{r.chamber} roster names {r.name} in district {r.district!r}")
            key = (r.chamber, int(str(r.district).strip()))
            if key not in seats:
                primitive_failure("Holder's district has no place",
                                  f"{r.chamber} roster names {r.name} in district {key[1]}, "
                                  f"which is not in the places table")
            seat = seats[key]
            if not seat["vacant"]:
                primitive_failure("Two holders for one seat",
                                  f"{r.chamber} district {key[1]}: {seat['holder_name']} and {r.name}")
            seat.update({"vacant": False, "holder_name": r.name, "holder_party": r.party,
                         "position": r.position, "seat_number": r.seat_number,
                         "email": r.email, "profile_url": r.profile_url})
            held[r.chamber] += 1

    # tribal seats, declared per Legislature (D-136, TRIBE-3)
    names = [str((t or {}).get("name") or "").strip() for t in tribal_seats]
    if not names or not all(names):
        primitive_failure("Tribal seats not declared",
                          "params.tribal_seats must list each nation by name")
    if len(set(names)) != len(names):
        primitive_failure("Tribal seat declared twice", f"names: {names}")
    rows = list(seats.values())
    for t, name in zip(tribal_seats, names):
        row = empty_seat(legislature, "house", "tribal", name, *stamps["house"])
        row["statute_wording"] = t.get("statute_wording")
        rows.append(row)

    frame = pd.DataFrame(rows, columns=COLUMNS)
    twice = frame[frame.duplicated(KEY, keep=False)]
    if len(twice):
        primitive_failure("Seat key used twice", f"e.g. {twice.iloc[0][KEY].tolist()}")
    for chamber in ("house", "senate"):
        mine = frame[(frame["chamber"] == chamber) & (frame["seat_kind"] == "district")]
        if (~mine["vacant"].astype(bool)).sum() != held[chamber]:
            primitive_failure("Holders and vacancies do not add up", f"{chamber}")
        w.info(f"{chamber}: {len(mine)} district seat(s), {held[chamber]} held, "
               f"{len(mine) - held[chamber]} vacant")
    w.info(f"tribal seats: {len(names)}, none matched to a holder from the record (TRIBE-4)")
    return frame


def output_metadata(frame):
    """what the receipt says of the seats table, its key included (KEYS-1)."""
    return {"data_category": "tabular", "crs": None, "row_count": len(frame),
            "variables": COLUMNS, "id_fields": KEY, "spatial_unit": SPATIAL_UNIT}


def main():
    args = parse_primitive_args()
    w = WarningsCollector("build_seats")
    with primitive_error_handling(w):
        p = args["params"]
        frame = build(read_table(get_input(args["inputs"], "places")),
                      read_table(get_input(args["inputs"], "house")),
                      read_table(get_input(args["inputs"], "senate")),
                      require_param(p, "legislature"), str(require_param(p, "sworn_in")),
                      require_param(p, "tribal_seats"),
                      str(require_param(p, "state_fips")).zfill(2), w)
        write_table(frame, args["output"])
        primitive_success(output_metadata(frame), w)


if __name__ == "__main__":
    main()
