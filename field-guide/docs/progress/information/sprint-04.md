# Sprint 04 ~ the geography graph: progress report

**Closed:** 2026-11-11, at step 8. **Domain:** information. **Contract:** 3, draft 0.9.
**Tests:** 417 passed. **Decisions:** D-125 to D-162.

## The goal, and the answer

The plan's done-when: "Which towns touch this district, and with what shares?" is a query, for every district in both chambers. It is: the edges table answers it for all 151 House and 35 Senate districts, with population and household shares, and step 1's graph summary confirmed every district is touched by a town. Asked through loam rather than read from the table, it arrives in Sprint 05 (LOAM-1).

## Built, against the plan

| # | Plan item | What exists | Decisions |
| --- | --- | --- | --- |
| 1 | District geographies in the ACS provider | both chambers; their names key the district places | tests/test_district_geographies.py |
| 2 | build_place_edges | contains, and overlaps to districts, tribal areas and from civil divisions, each with both weights | D-121, D-122, D-125, D-126 |
| 3 | flag_places | folded into build_places: kind, Census status, LURC, zero counts, no block points. Baxter State Park open | D-128, D-130, BAXTER-1 |
| 4 | The tribal-area inventory with its note | the 8 Census 2020 legal areas, from the layers, each with census_tribal_area; the contains note on every place holding a tribal block | D-123, D-125, D-156 to D-158 |
| 5 | The places table | 1,663 places at seven levels | D-128, D-129, PLACES-1 |
| 6 | Legislators joined to districts | the Legislature's rosters as provider, build_seats, the seats table in Contract 3 section 6. Built and tested, not run: it runs when loam reads places (LOAM-1). The tribal representation note is not written (NOTE-3) | D-134 to D-141, TIME-2 |
| 7 | Display geometry, recorded as a publication step | outlines from the 2024 land faces at six levels, with clipped and held_out records in provenance | D-143 to D-155 |

## Where the plan changed, and why

- Flags are columns of the places table, not a separate validate step, because what a place is and what a reader must know before a value are written where the place is (D-128, D-130).
- The weight fork was decided as both: population and household shares on every overlaps edge, chosen by the value's `rests_on.counts`. Housing units were refused, since Maine's seasonal homes would weigh summer camps like year-round towns (D-121).
- Civil divisions join towns through 2020 block internal points (D-122).
- Tribal areas are keyed by the Census GEOID with component, so a reservation and its trust land are two places (D-125, TRIBE-1).
- Towns are the 2024 county subdivisions, from the 2024 topological faces, and a block's county follows its town (D-126, D-127). This closed TOWN-1, where 2020 towns met 2024 values.
- The record for seats is the Maine Legislature, with LegiScan as a second authority, because LegiScan lists people who acted, not seats that exist (D-134, LEG-1).
- Seats are their own table, and tribal seats are keyed by the nations' names in 3 MRSA §601 with no place link, so a Census boundary is never read as a nation's constituency (D-136, D-137).
- Step 4's close moved from a date to a dependency (TIME-2).
- Rule 9 learned to bind notes by row (D-156, D-157), so the places table can say which notes its rows carry.

## The numbers

47,138 blocks and 1,362,359 persons (2020). 1,663 places: 1 state, 16 counties, 529 towns, 151 House districts, 35 Senate districts, 8 Census tribal areas, 923 civil divisions. Town kinds: 430 towns, 42 unorganized territories, 29 plantations, 23 cities, 4 reservation subdivisions, 1 gore. At step 1, before towns moved to the 2024 faces, 46 towns touched more than one House district (at most 8) and 5 more than one Senate district; those two counts were not re-run after D-126.

## Every vintage used

| What | Vintage | Declared in |
| --- | --- | --- |
| Blocks and their counts | 2020 Census, P.L. 94-171 (P1, H1) | the spine's inputs |
| Towns | 2024 TIGER/Line topological faces and county subdivisions | maine_geography_graph.yml, both vintages mappings |
| Counties and the state | 2024, following the towns (D-127) | as above |
| House and Senate districts | 2024 block equivalency files, which ACS 2020-2024 is tabulated on | as above |
| Census tribal areas | 2020 legal areas and block assignment (D-123) | as above |
| Civil divisions | MEGIS METWP24P | as above |
| District and county names | ACS 2024 tables | the places step's inputs |
| Legislators | the House export and Senate listing, shapes fetched 2026-11-11, test fixtures only (D-139) | the manifest, available: false |

Edge vintages are held to place vintages by build_places (D-162). Estimate vintages are matched where values join places, not yet built; the aiannh places' 2020 vintage against ACS 2024 is carried to LOAM-1.

## Carried forward

| Waiting on | Items |
| --- | --- |
| Others | the 133rd's rosters after 2026-12-02 (TRIBE-4, SEN-1); Person 3's wording (PENOB-1, the contains note, NOTE-3, D-118, ROLE-1); CII's reply (HIST-1); a source for Baxter State Park (BAXTER-1) |
| Sprint 05 | LOAM-1, with the aiannh vintage question; SRC-1; running build_seats |
| Sprint 06 | located_in edges and their end checks |
| Sprint 08 | rule 10's refusing license (LIC-1?); GJSON-1 |
| Unscheduled | TRIBE-5, ZERO-1, DAS-1, MEGIS-3, XCHK-1, BOUND-1's map check; untested refusals listed in state.md |

## Three lessons worth keeping

- A source's word for a thing is not ours. LegiScan's "people" are people who acted, and a seats table shaped by them would have called every quiet seat vacant (LEG-1).
- The plan is ordered by dependency, never by the calendar (TIME-2).
- A probe that assumes a field exists repeats the bug it was written to find (step 1).
