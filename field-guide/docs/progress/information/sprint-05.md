# Sprint 05 ~ loam learns the graph: progress report

**Closed:** 2026-11-11, after change 15 and build 6. **Domain:** information. **Contract:** 3, 1.0.
**Tests:** 531 passed. **Decisions:** D-163 to D-191.

## The goal, and the answer

The plan's done-when: "`wonder` reads any Maine district through its edges." It does. `python -m canopy.cli wonder maine --place us_census_sldl:23042` reads House District 42: its own ACS value for four indicators, its 7 towns with both shares, every town's value most-here first with what it rests on, the range, the towns wholly inside apart from the towns its line splits, and a firm range of the towns wholly here on a sound sample. Islesboro, with 0.7% of its 330 households in the district, is named among the split towns and sets no end of any range but the full one, where its share and count are said. Every Maine district, House or Senate, reads the same way.

## Built, against the plan

| # | Plan item | What exists | Decisions |
| --- | --- | --- | --- |
| 1 | Places and edges in loam | DuckDB views over the receipts' files, made by open_plot; a plot with no graph says so (changes 6, 11) | D-168, D-178 |
| 2 | Holdings keyed by place | indicator_values and place_values; vintages by a cited seed; agreeing tables collapse, disagreeing ones make no view (changes 7, 8) | D-169 to D-173 |
| 3 | A plot is a set of places | the manifest's optional `places:`, by key or with contained or touching, in plot_places (change 9) | D-174, D-175 |
| 4 | Edge rules by kind of measure | canopy/loam/edge_rules.py: declared universes, the zero test, and allocation of declared counts only, warned and never stored (change 12) | D-179 to D-182 |
| 5 | Reading through edges | district values from the ACS keyed by chamber (change 10); canopy/wonder/place.py and `wonder --place` (changes 11, 12) | D-176, D-177, D-183 to D-185 |
| 6 | The grove handoff | every key decided: authority's one meaning and the publisher's own word (change 13), one declared home for the authorities (change 14), an index that carries its authority (change 15), sources and layers that declare their own keys (decided, built in NAME-4's sweep) | D-186 to D-191 |

Before the builds: LOAM-1, a run reading another's output as `$loam.<type>`, judged fresh, stale or cannot tell before any step (changes 1 to 4, D-163 to D-167), and KEYS-1, every graph receipt declaring the key that names its rows (change 5).

## Where the plan changed, and why

- `readiness` was left a reader of types against methods; a place is not a type, so the district reading lives in canopy/wonder/place.py and the plan's "readiness and wonder can read a district" is met by wonder alone (D-184).
- No district value existed, so district values came first, from the ACS's own estimates, in their own preparation keyed by each chamber's authority. Keyed as us_census_geoid, House District 5's value would have attached to Cumberland County and passed its vintage rule (D-176, GRAPH-1).
- The allocation fork was decided as a rule built and tested, used by no reading yet. None of the four indicators is a count; the planner is the use that will decide how to say a mixed-vintage estimate (D-179, COUNT-1).
- Which weight counts what a value rests on became a declared seed, keyed by universe, because rent burden counts renter households, which no edge weight counts. A field inside the indicators would have made every value receipt stale, since `$indicators` resolves to the whole declaration (D-181, D-182).
- The range was rebuilt twice against real data. The first reading of House 42 showed Islesboro topping the firm broadband range. Towns wholly inside are now ranged apart from towns a line splits, and the firm range is the towns wholly here (D-183, D-185).
- The publisher of a value was renamed `published_by`, and `authority` now means only who assigns a place's code. The rename stops at manifests, which NAME-4 sweeps (D-186, D-187).
- Three grove keys were decided now and are built later, with one sweep over every manifest: SRC-2, LAYER-1 and NAME-4.

## The numbers

1,663 places, 2,693 edges. 12,526 value rows, 3,222 of them agreeing duplicates collapsed. 744 district values attached: 151 House and 35 Senate districts, four indicators each, every one attached, none collapsed. No value carries an `authority` column; none lacks a publisher; no ACS value at a ruled level lands as no_rule. House District 42: 7 towns, 5 wholly inside, Owls Head 80.1% of its 669 households and Islesboro 0.7% of its 330, broadband 88.7 with a firm town range of 87.2 (Rockland) to 93.7 (North Haven).

## Every vintage used

| What | Vintage | Declared in |
| --- | --- | --- |
| District values | ACS 2020-2024, on 2024 legislative boundaries (the legislative class) | seeds/vintages/boundaries.yml |
| Town, county and state values | ACS 2020-2024, on boundaries in effect January 1, 2024 (the legal class) | as above |
| Unorganized territories | ACS 2020-2024, on 2020 boundaries (the statistical class), attached unchecked | as above |
| Edge weights | 2020 Census blocks, P.L. 94-171 (P1, H1) | Contract 3, section 2 |
| Census tribal areas | 2020 legal areas; their 2024 ACS values are not shown (D-171, TRIBE-6) | seeds/vintages/boundaries.yml |

An allocated count would multiply a 2020 weight by a 2024 count. D-179's warning says so, and no reading yet shows one.

## Carried forward

| Waiting on | Items |
| --- | --- |
| Others | the 133rd's rosters after 2026-12-02 (TRIBE-4, SEN-1, maine_seats); Person 3's wording and review (NOTE-3, D-173, D-118, ROLE-1, PENOB-1); CII's reply (HIST-1); the grove teammate's own review of Contract 3 |
| Sprint 06 | profile.py, grown from canopy/wonder/place.py (D-184); located_in edges |
| Sprint 08 | map.py's join by declared authority (LAYER-1); GJSON-1; rule 10's license (LIC-1?) |
| Sprint 10 | KIT-1: freshness does not judge primitive code. Its first real instance was change 13, where every value receipt read fresh after derive_indicator.R changed and was rerun by hand. Also VER-1, DEPS-1, and the authority copies reading their seed (D-188) |
| Sprint 12 | COUNT-1: count people, not rates, for the outreach planner |
| Unscheduled | NAME-4 with SRC-2 and LAYER-1, one sweep over every manifest; TENURE-1; TRIBE-6; DAS-1's hypothesis; LEDGER-1 to LEDGER-3; LIN-2; the untested refusals in state.md |

Closed in this sprint: LOAM-1, KEYS-1, CON3-1, ZERO-1 (D-180), NAME-2 (D-186), AUTH-1 (D-188), SRC-1 (D-189), SEAM-1 (D-190), MAP-4 (D-191), and LIN-3, whose two receipts now carry lineage and may leave at public.

## Three lessons worth keeping

- Read the real output as its reader would. Every test passed while the firm range let Islesboro speak for a district it barely touches; only reading House 42 as an official would showed it.
- A signature's callers are found by searching for the keyword itself, and a keyword search must still be read for meaning: one word can name two things, which is the double meaning NAME-2 ended (change 13).
- A commit can say what is not in it. Twice a ledger entry was committed without its code, once when a long paste broke. Commits are now guarded, committing only if the code they name has changed, and every file is pasted on its own.
