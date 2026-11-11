# Contract 3 ~ The geography graph

**Status:** draft 0.8, 2026-11-11 (seats, D-134, D-136 to D-138; G-3, D-103; G-1, D-121; G-2, D-122; authorities by level, GRAPH-1; tribal keys, D-125; 923 divisions, MEGIS-2; towns from 2024 faces, D-126; county follows town, D-127, BOUND-1; kind and Census status, D-128, FUNC-2; reservation parts, D-129, PEN-1; LURC, D-130). **Owner:**
Kalli. **Built in:** Sprint 04 (the tables, by preparations), Sprint 05 (loam
learns them). **Read by:** the place profile (Contract 4), the grove's
cross-plot catalog, every district product. **Rests on:** MP-75 (towns get
values, never standings), MP-76 (split towns shown in every district they
touch), MP-72 (Wabanaki places as a qualified Census view), MP-80 (the grove
is a weighted graph), D-19 (rows keyed by authority and code), D-27 (medians
never combine).

Maine's places do not form a tree. A town can sit in two House districts, a
district can cross a county line, and a Census tribal area overlaps towns that
are not inside it. So the geography is stored as a graph: places, and edges
between them. Every plot's loam bed holds its part of the graph; the grove is
the union of every bed.

## 1. Places

One row per place, at every level. The key is `(authority, code)`, as D-19
already keys indicator rows, so a value and its place join by derivation,
never by name.

**A Census GEOID is unique only within its level (GRAPH-1).** `23001` is
Androscoggin County, House District 1 and Senate District 1. So the authority
names the level wherever codes could collide, and `(authority, code)` always
names exactly one place.

| Field | Type | Meaning |
| --- | --- | --- |
| `authority` | text | who assigns the code, and at which level: `us_census_geoid` (state, county, town), `us_census_sldl` (House), `us_census_sldu` (Senate), `us_census_aiannh` (Census tribal area, keyed by the Census GEOID: AIANNH plus component, `2760R` and `2760T` are two places, D-125), `megis` (Maine civil division) |
| `code` | text | the code as that authority writes it, leading zeros kept: `23005`, `2300560825` |
| `level` | text | `state`, `county`, `cousub`, `sldl` (Maine House), `sldu` (Maine Senate), `aiannh` (Census tribal area), `megis_division` |
| `vintage` | text | the boundary year; it must match the ACS vintage it is joined to |
| `kind` | text | what the place is, in words a reader can use (D-128): `state`, `county`, `house_district`, `senate_district`, `tribal_reservation`, `tribal_trust_land`, `civil_division`, and for towns, from the 2024 LSAD: `town` (43), `plantation` (39), `city` (25), `unorganized_territory` (46), `reservation_subdivision` (86), `gore` (31). An LSAD with no kind is refused |
| `name` | text | as the authority publishes it |
| `census_funcstat` | text or null | the Census's functional status for a town, verbatim (A, S, F, N, E). Kept, never shown as a bare word: Maine's 23 cities and its 4 reservation subdivisions are F (FUNC-2) |
| `flags` | list of text | from the list below; empty, never null |
| `context_note` | text or null | the id of the note Contract 1, rule 9, requires (`census_tribal_area`); its text lives with its type in `seeds/schemas` |
| `part_of_authority`, `part_of_code` | text or null | for a reservation subdivision, the Census tribal area it belongs to (D-129). Penobscot Indian Island is two Census subdivisions in two counties, both part of `2760R` |
| `lurc_share_population` | number or null | for a town flagged `lurc`, the share of its people in blocks inside a LURC division; null when it has nobody |

**Flags:** `zero_population`, `zero_households`, `lurc`, `lurc_mixed`,
`no_block_points`, `funcstat_unknown`. A flag says something a reader must
know before reading a value. What a place is lives in `kind`, so a reader never
mistakes a township with no government for a town with no news, nor a city for
a fiction. `lurc` (D-130): a division any of whose polygons MEGIS marks LURC; a
town any of whose blocks lies in one. `lurc_mixed`: a division whose polygons
disagree. `no_block_points`: a division no 2020 block's internal point falls in
(Cove Point Twp, Kineo Twp); it has no edges and is still a place. Baxter State
Park is not a Census subdivision and is in neither file, so it carries no flag
until a source for it is chosen (BAXTER-1).

**Reservation subdivisions are found by geometry, never by name** (D-129): a
town whose every 2020 block lies in a Census reservation. A town coded LSAD 86
that the blocks do not confirm, or the reverse, is refused.

**Counts for Maine** (Sprint 04 builds and tests them): 1 state, 16 counties,
529 county subdivisions, 151 House districts, 35 Senate districts, the Census
tribal areas inventoried from the AIANNH layer (never from a list of names),
and the 923 MEGIS civil divisions (924 polygons, MEGIS-2).

## 2. Edges

One row per relationship. Each end is a place key, so an edge has four key
columns.

| Field | Type | Meaning |
| --- | --- | --- |
| `from_authority`, `from_code` | text | the containing or overlapping place; for `located_in`, the point's layer (its dataset id) and its feature id |
| `to_authority`, `to_code` | text | the other place |
| `kind` | text | `contains`, `overlaps` or `located_in` |
| `weight_population` | number or null | the share of the `from` town's population inside the `to` place; see below |
| `weight_households` | number or null | the share of the `from` town's households (occupied housing units) inside the `to` place |
| `weight_reason` | text or null | why a weight is null, e.g. `zero_households` |
| `source` | text | the file or method the edge came from |
| `vintage` | text | the vintage of that source |

| Kind | Means | Weights |
| --- | --- | --- |
| `contains` | clean nesting: state to county, county to town | 1 and 1 |
| `overlaps` | partial: town to district, town to tribal area | the town's population share and household share inside the other place, summed over 2020 Census blocks (P.L. 94-171: P1 population, H1 occupied housing units). Each block's town is its 2024 town from the TIGER/Line 2024 topological faces (D-126); a block a 2024 boundary split goes whole to the town holding most of its land, and is flagged |
| `located_in` | a point (a library, an outlet) to every area it falls in | 1 and 1 |

**Two weights, chosen by the value (D-121).** Population shares answer
representation ("how much of this town does this district's legislator
represent"); household shares answer values counted in households. A reader
never picks one: a value uses the weight named by its indicator's
`rests_on.counts` (households -> `weight_households`, persons ->
`weight_population`), and representation uses `weight_population`. A town
with no households has a null household share with `weight_reason:
zero_households`, never 0. Housing units are not used: Maine's seasonal homes
are counted as vacant housing and would give summer camps the weight of
year-round towns.

A point inside two districts has a `located_in` edge to each, so it counts in
both (Sprint 06 test).

**Points are not places (D-103).** A library or an outlet is named only inside
its `located_in` edges, by layer and feature id; it never has a row in
`places`. `places` holds the areas a profile can be built for, exactly the
list Contract 4 enumerates. So the ends of every `contains` and `overlaps`
edge are rows in `places`, and the `to` end of every `located_in` edge is
one; the `from` end of a `located_in` edge is a feature in a declared layer.

## 3. Invariants

These are tested where the tables are built (Sprint 04):

- Every town has exactly one `contains` edge from its county.
- A block's county is its 2024 town's county (D-127). A block whose 2020 county differs is listed by the spine, with both counties, so a boundary change shows instead of hiding (BOUND-1).
- A town's `overlaps` weights across one chamber's districts sum to 1, for each
  basis separately; a null household share is excluded from the sum and the
  town carries the `zero_households` flag.
- Every district touches at least one town.
- Both ends of every `contains` and `overlaps` edge, and the `to` end of every
  `located_in` edge, exist in `places`; the `from` end of every `located_in`
  edge exists in its declared layer.
- Boundary and estimate vintages match, place by place.
- Every reservation subdivision and tribal area carries its context note, and every reservation subdivision names its tribal area (D-129).
- The towns in the places table and the 2024 county subdivision layer are the same set (D-126).

## 4. The three rules

1. **Districts come from the ACS directly.** A district's value is the ACS's
   own legislative-district estimate, never a sum or average of its towns.
2. **Medians are never combined** across places (D-27). A median exists only
   where the publisher computed it.
3. **A larger place's value is shown with its towns' range.** A district or
   county value always travels with the minimum and maximum across the towns
   that touch it, and how many towns that is, so one number never hides the
   places inside it.

Split towns appear in every district they touch, with their share (MP-76).
Towns carry values and never standings (MP-75).

## 5. Storage

Until the grove exists, the graph lives as two Parquet tables in each plot,
`places` and `edges`, each written by a preparation from `soil/` primitives
(D-98), with an envelope. A table nobody wrote by a preparation is not part of
the graph. Loam reads them as holdings keyed by place (Sprint 05); the grove's
catalog is their union across plots.

## 6. Seats

A seat is an office in a chamber for one Legislature. It is not a place and
never has a row in `places`: a district seat points at its district place,
and a tribal seat points at none. A tribal representative speaks for a
nation's members wherever they live, so joining a tribal seat to a Census
tribal area would claim the Census's boundary is the nation's constituency,
the claim D-123's note refuses (D-136).

**The record is the Maine Legislature (D-134).** Holders come from the
House's member export and the Senate's district listing. LegiScan is a second
authority, held beside the record: its `people_id` and district are carried
and compared, never used to fill a field. LegiScan lists people with activity
in a session, not seats, so it cannot say a seat is vacant (LEG-1).

**Key:** `(legislature, chamber, seat_kind, seat_ref)`. For a district seat,
`seat_ref` is the district code (`23042`); for a tribal seat, the nation's
name as 3 MRSA §601(1)(A) defines the Wabanaki Nations (D-136). The kind
travels with the ref, so a code and a name are never mistaken for each other.

| Field | Type | Meaning |
| --- | --- | --- |
| `legislature` | text | declared, e.g. `133`; the record does not say |
| `chamber` | text | `house`, `senate` |
| `seat_kind` | text | `district`, `tribal` |
| `seat_ref` | text | the district code, or the nation's §601 name |
| `district_authority`, `district_code` | text or null | the district place (`us_census_sldl`, `23042`); null for a tribal seat |
| `statute_wording` | text or null | for a tribal seat, the nation as 3 MRSA §1 words it, where it differs ("Penobscot Indian Nation", NAME-3) |
| `seat_number` | text or null | the chamber's chair number, verbatim; never a key, it changes each Legislature |
| `vacant` | boolean | the seat exists and the record names no holder |
| `holder_name`, `holder_party`, `position` | text or null | verbatim from the record; null when vacant |
| `email` | text or null | where the record gives one (the House) |
| `profile_url` | text or null | the member's page, where the record links one (the Senate) |
| `legiscan_people_id`, `legiscan_district` | text or null | the second authority, verbatim |
| `legiscan_agreement` | text or null | `agrees`, `differs`, `absent` |
| `source`, `as_of` | text | the record's address and the fetch time |

**No phone numbers (D-138).** Some are members' own cell phones, published by
the Legislature for constituents; a public harvest would republish them in a
new context. A reader reaches a member by email or through the member's own
page.

**Where seats come from.** District seats are generated from `places`, one per
`sldl` and `sldu` place, so all 151 and all 35 exist and a vacancy is a seat
with no holder. Tribal seats come from a list declared per Legislature, citing
3 MRSA §1 and §601; the 133rd has four (TRIBE-3). Seats are built for a
Legislature only after it is sworn in (D-135).

**Invariants**, refused in `build_seats` or tested:

- Every House and Senate district place has exactly one seat per Legislature.
- No seat key appears twice.
- A holder whose district has no place is refused by name.
- Tribal seats are House seats only, carry no district, and match the declared list exactly.
- Holders plus vacancies equal seats, per chamber.
- The districts a Legislature was elected on are the graph's district vintage (tested; not yet verified for the 133rd).

**Storage:** a third Parquet table, `seats`, beside `places` and `edges`,
written by a preparation with an envelope (Section 5).

## Open

| ID | Question | Decided in |
| --- | --- | --- |

## Decided in review

| ID | Decision |
| --- | --- |
| G-3 | Points stay out of `places`; they are named by layer and feature id inside their `located_in` edges (D-103) |
| G-1 | Both population and household weights on every `overlaps` edge; the value's `rests_on.counts` chooses (D-121) |
| G-2 | MEGIS civil divisions join Census towns through blocks: each 2020 block goes to the division containing its internal point (D-122) |
| S-1 | Seats are their own table, keyed by legislature, chamber, kind and ref; the Legislature is the record and LegiScan the second authority; tribal seats keyed by the §601 names with no place link; no phone numbers (D-134, D-136, D-137, D-138) |

## Review

| Reviewer | Date | Result |
| --- | --- | --- |
| Kalli, author, acting as grove teammate | 2026-11-10 | Reviewed; G-3 decided. Reviewed by its author, not by a second person |
