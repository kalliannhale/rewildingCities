# State of the garden ~ rewildingCities

What is true now. Rewritten, never appended, at every hand-off (D-160). The
build ledger (field-guide/docs/build_ledger.md) is the history; this page is
the present. When the two disagree, the ledger and the code win, and this page
is fixed.

**Updated:** 2026-11-11, mid Sprint 05, after change 9 (plan build 3) and D-173.

## Where the build stands

- Branch main, pushed. Sprint 05's changes 1 to 9 are committed (8a5a881 to 1c78c9d), with D-173 and this page in the commit after. Confirm with `git log --oneline -3` and `git status -sb`.
- Tests: `python -m pytest -q`. 480 passed after change 9.
- Plan of record: the Master Plan, https://claude.ai/artifact/KpQRRSTyXr27emXnJFfL6z. Its decision table stops at D-81; check its claims against the code.
- Next decision ID: D-176. Before minting any other ID, grep the ledger for it.
- Current: Sprint 05, loam learns the graph. Done: LOAM-1 (changes 1 to 4), KEYS-1 (change 5), plan builds 1 (change 6), 2 (changes 7 and 8) and 3 (change 9). Next: builds 4 and 5 together, then build 6, then the close.
- On or after 2026-12-02, when the 133rd's rosters are acquired: flip available: true, TRIBE-4, SEN-1, then run maine_seats.

## Sprint 05 so far

| Change | What | Decisions |
| --- | --- | --- |
| 1 | Provenance entries name their run and step; HASH-2 fixed | D-167 |
| 2 | `$loam.<type>`: one run reads another's output by semantic type, through the plot's bed (canopy/loam/reach.py) | D-163, D-164 |
| 3 | Freshness judged before any step runs: fresh, stale (refuses) or cannot tell (warns into the receipt) (canopy/loam/freshness.py) | D-165, D-166 |
| 4 | Seats as their own preparation, plots/maine/preparations/maine_seats.yml, reading `$loam.places`; Sprint 04 step 4 closed | |
| 5 | places, edges and seats declare KEY and SPATIAL_UNIT in their receipts; edge key used twice refused | KEYS-1 |
| 6 | places and edges are DuckDB views in loam over their receipts' files (canopy/loam/graph.py), made by open_plot | D-168 |
| 7, 8 | indicator_values and place_values views; boundary vintages by a cited seed (seeds/vintages/boundaries.yml); agreeing value tables collapse | D-169 to D-172 |
| 9 | a plot is a set of places: the manifest's optional `places:`, by key or `with: contained` / `with: touching`, resolved in the plot_places view; no parent key | D-174, D-175 |

D-173: the four reservation subdivisions' values attach with their note, held for Person 3 and the client-led consultation before any exposure.

On real Maine data: Maine declares no places, so plot_places holds all 1,663; `$loam.places` reads fresh; House District 42 lists its 7 towns with shares through loam; place_values attaches 1,996 values, 168 unchecked statistical (the 42 unorganized territories, funcstat S, as the seed assumes), 9,618 with no place (other states' counties).

## What is left in Sprint 05

- **Builds 4 and 5, together.** First: derive district values (acs_sldl_2024 and acs_sldu_2024 are in the manifest for names only; no sldl or sldu value exists yet), and move canopy/cli/wonder.py onto open_plot (it plants inline and does not see the views). Forks: whether to allocate counts before a use needs it (an allocated count is a fact about an edge and is computed on read, never stored, D-168); whether zero-share towns sit in a district's range (ZERO-1, DAS-1, Kalli's to decide). Contract 3 section 4 holds: a district's value is the ACS's own, shown with its towns' min, max and count. Islesboro's 1.5% share of House 42 is the kind of small share the display rule must handle.
- **Build 6, the grove keys,** decided before any handoff: NAME-2, AUTH-1, SRC-1, SEAM-1, MAP-4.
- **The close:** progress report field-guide/docs/progress/information/sprint-05.md with D-163 onward and KIT-1 under Sprint 10; Contract 3 widened for CON3-1 and given its new G-rows; this page rewritten.

## Contracts

field-guide/docs/contracts/: 1 tiers and the gate 0.5; 2 canonical objects 0.1; 3 geography graph 0.9 (section 6 Seats; CON3-1 pending); 4 place profile 0.2.

## Where Contract 3's invariants are held

| Invariant | Held by |
| --- | --- |
| Every town has one contains edge from its county | build_place_edges refuses a town in two counties; tested |
| A block's county is its 2024 town's (BOUND-1) | build_block_spine; tested |
| Shares sum to 1 per chamber, per basis | build_place_edges, check_shares; tested |
| Every district touches a town | by construction from the spine (D-161); tested |
| Edge ends exist in places | build_places; tested. located_in not until Sprint 06 |
| An edge's two ends name one edge | build_place_edges, check_key (KEYS-1); tested |
| Vintages match | edges to places, build_places (D-162); values to places, place_values through seeds/vintages/boundaries.yml (D-170); tested |
| Tribal places carry their note and name their area | build_places; tested |
| Towns equal the 2024 layer | build_places; tested |

## IDs defined outside the ledger

The ledger has no entries for D-98 to D-124 (LEDGER-1). Where some live:

| ID | Where | What |
| --- | --- | --- |
| D-101 | Contract 1, E-1 | rule 3 is a conjunction of tiers |
| D-102 | Contract 1, E-2 | an empty curiosity passes rule 4 as a caveat |
| D-118 | semantic_types.yml comments | PROPOSED tiers, for Person 3 |
| D-121 | Contract 3, G-1 | both weights on every overlaps edge |
| D-122 | Contract 3, G-2 | MEGIS divisions join towns through block points |
| D-123 | build_places.py docstring; census_tribal_area's comment | tribal places are the Census 2020 legal areas, each with census_tribal_area |
| HASH-1 | tests/test_preparations.py | HASH-2's earlier name; HASH-2 is resolved |
| MP-67 to MP-81 | Master Plan | the plan's own D-67 to D-81 |

## Open items

| ID | One line | Defined |
| --- | --- | --- |
| TRIBE-6 | compare Maine's 8 tribal areas, 2024 against 2020; an unchanged one may attach values (D-171); with Kalli and Person 3 | ledger, change 7 |
| NOTE-3 | the tribal representation note (MP-77) is not written; also confirm maine_seats' tribal list | ledger, Sprint 04 close and change 4 |
| KIT-1 | Sprint 10 must decide: --accept-stale, hashing primitive code, VER-1, DEPS-1. Real instance: a receipt older than its primitive reads fresh | ledger, step 1 and change 7 |
| LIN-2 | provenance repeats an inherited step (no dedup in _merge_provenance); harmless | ledger, step 1 |
| LIN-3 | derive_values.envelope.json has no lineage; rerun maine_broadband_access_subscription__cii_indicator_values_91b5c0 to give it one | ledger, change 8 |
| VER-1 | provenance version comes from the step definition, so it never signals changed code | ledger, step 1 |
| CON3-1 | Contract 3 says weights are the from town's share; they are the from place's (MEGIS divisions are from ends) | ledger, change 5 |
| NAME-2 | "authority" means the place-code authority in places and the publisher in values; settle before the grove | ledger |
| NOTE-2 | descendants of places other than outlines write no row_context_notes | ledger, Sprint 04 |
| Rule 10 | places and every outline are withheld at public under rule 10 only (LIC-1?) | ledger, Sprint 04 |
| TRIBE-5 | 0115T, 2695T, 2760T outlines do not nest in the Census 2020 layers by more than water | ledger, Sprint 04 |
| PENOB-1 | the Main Stem note's wording waits on Kalli and Person 3 | ledger, Sprint 04 |
| GJSON-1 | rewildr's safe_write_sf cannot overwrite a GeoJSON holding one very large feature | ledger, Sprint 04 |
| RESOLVE-1 | sows --resolve-only and resolve_data can acquire and commit | ledger |
| DEPS-1 | geopandas and pyogrio are installed but not declared | ledger, Sprint 04 |
| SEAM-2 | outlines and overlap weights disagree on split blocks, by design; do not fix | ledger |
| HIST-1 | waiting on CII's reply to Kalli's Nov 10 email | ledger |
| Person 3 | D-118's tiers, ROLE-1, the draft notes, NOTE-3, D-173's review | ledger |

Noted, not numbered: an envelope records no hash of its own output; canopy/cli/wonder.py plants inline rather than through open_plot.

Also carried, look up in the ledger before relying on them: S2-1, GATE-2, GATE-3, MAP-4, MAP-8, MAP-9, TRIBE-4, SEN-1, LEGI-1, LEG-4, LIC-1, KEY-1, XCHK-1, SEAM-1, AUTH-1, SRC-1, COMP-1, REG-1, LOOP-1, ACQ-6, SCH-5, TAG-1, DAS-1, ZERO-1, MEGIS-3, LURC-1, BAXTER-1, DISS-1, METH-1.

Untested refusals: a town in two counties, a county or district without a name, a place key used twice (build_places refuses it; untested), a reservation subdivision in two reservations, a missing vintage.

## Traps

- /mnt/project in Claude's sandbox is a stale October snapshot. The repo is on Kalli's machine.
- Run a preparation with `python -m canopy.cli sows <run.yml>`; `--dry-run` only validates. Never `--resolve-only` casually: it can acquire and commit (RESOLVE-1).
- Do not run maine_seats on real data before 2026-12-02: its rosters are auto-acquirable, and a run could write the outgoing Legislature's roster into the manifest before build_seats refuses it.
- To ask freshness alone, without resolving data: build an Orchestrator on a run file and call `_judge_loam_inputs([])`.
- The views (places, edges, indicator_values, indicator_value_rows, place_values, plot_places) exist only in a bed opened by open_plot; Loam.snapshot() copies the catalog table alone, by design (D-168). VALUES is reserved in SQL, which is why the values view is indicator_values.
- In value tables, `authority` is the publisher and `unit_authority` the place-code authority (NAME-2). Join values to places on (unit_authority, unit_code).
- open_plot parses the manifest once and hands it to planting and the graph (P-01); plant_graph takes declared_places from Manifest.places.
- A step's `outputs:` in a preparation gives names, not file paths. Receipts are `.envelopes/<step>_<output>.envelope.json`, one flat namespace per plot.
- Tests that fake EnvelopeBuilder.run must accept run and step (tests/test_preparations.py, test_loam_reach.py, test_seats_preparation.py). A signature change reaches every fake of it.
- A test fake that records an md5 must record the real one: freshness recomputes it.
- Progress reports live in field-guide/docs/progress/<domain>/sprint-NN.md, one per sprint, by domain.
- The ledger holds the Sprint 04 step 4e block twice, word for word (LEDGER-2).
- The geography graph preparation declares `vintages` twice, for graph_edges and graph_places; change both together (D-162).
- The gate runs only at exits (canopy/expose/check.py). Inside a run only the precondition gate applies.
- `sows` prints nothing until the run ends. To see a running R step: `ps aux | grep "[b]uild_place_outlines"`.
- R primitives: primitive_success serializes with auto_unbox, so a list of one needs as.list (C-36). rewildr's safe_read_table infers CSV types; read code columns as text.
- Vocabulary.load reads only semantic_types.yml and domains/*.yml. Note texts live in seeds/notes/notes.yml.
- `soil/_registry.yml`, `seeds/schemas/semantic_types.yml` and `seeds/notes/notes.yml` each end with their one map, so appends land correctly.
- Scope every grep: quote globs, and never grep `plots` without `--include="*.yml"`, because `.data` holds large binaries.
- Keys live in Kalli's environment only (KEY-1). The repo is public.
- The sandbox lacks pytest, pyarrow, shapely, duckdb, jsonschema, pyogrio and R; it has pandas and yaml. Pure-Python logic can be smoke-run there with stand-ins; anything using DuckDB cannot.

## People

Kalli: Maine data and geography, profile, explorer, review of everything; acting grove teammate. Ajitesh: publish route (Sprint 08); GJSON-1 and D-157's required notes argument matter for his door. Infrastructure teammate: Sprints 07 and 10; DEPS-1 and KIT-1 matter for the Docker build. Person 3: tier declarations, note wording, NOTE-3 and D-173's review.
