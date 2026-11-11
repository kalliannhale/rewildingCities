# State of the garden ~ rewildingCities

What is true now. Rewritten, never appended, at every hand-off (D-160). The
build ledger (field-guide/docs/build_ledger.md) is the history; this page is
the present. When the two disagree, the ledger and the code win, and this page
is fixed.

**Updated:** 2026-11-11, at Sprint 05's close, after change 15 and build 6.

## Where the build stands

- Branch main, pushed. Sprint 05 is closed: changes 1 to 15, build 6's decisions, Contract 3 at 1.0 and the progress report are committed, through 87aa0d9 and the close's commits after it. Confirm with `git log --oneline -5` and `git status -sb`.
- Tests: `python -m pytest -q`. 531 passed at the close. The R oracle tests (test_index_r_oracle.py, test_derive_indicator_oracle.py) run only where Rscript and rewildr are installed; run with `-rs` so a skip is named, since a skip proves nothing.
- Plan of record: the Master Plan, https://claude.ai/artifact/KpQRRSTyXr27emXnJFfL6z. Its decision table stops at D-81; check its claims against the code.
- Next decision ID: D-192. Before minting any ID, grep the ledger for it (LEDGER-3: MAP-4 was used twice).
- Next sprint, by the plan's order: Sprint 06, the place profile and the standard (profile.py, grown from canopy/wonder/place.py, D-184; thresholds from UNESCO and the IFL). Unscheduled and ready: NAME-4's sweep with SRC-2 and LAYER-1.
- On or after 2026-12-02, when the 133rd's rosters are acquired: flip available: true, TRIBE-4, SEN-1, then run maine_seats.

## Sprint 05, closed

| Change | What | Decisions |
| --- | --- | --- |
| 1 to 4 | LOAM-1: `$loam.<type>`, freshness judged before any step, seats as their own preparation | D-163 to D-167 |
| 5 | KEYS-1: graph receipts declare their key | KEYS-1 |
| 6 | places and edges as views in loam | D-168 |
| 7, 8 | values attach to places; vintages by a cited seed; agreeing tables collapse | D-169 to D-173 |
| 9 | a plot is a set of places (plot_places) | D-174, D-175 |
| 10 | district values from the ACS, keyed by chamber (maine_district_indicator_values) | D-176, D-177 |
| 11 | wonder opens its plot through open_plot and says what the graph made | D-178 |
| 12 | edge rules, declared universes, and `wonder --place` reading a district through its edges | D-179 to D-185 |
| 13 | a value's publisher is `published_by`; `authority` means only who assigns a place's code | D-186, D-187 |
| 14 | the authorities declared once, every copy held to them by a test | D-188 |
| 15 | an index carries its units' authority and never ranks across two | D-190 |
| build 6 | sources and layers declare their own keys (decided; built in NAME-4's sweep) | D-189, D-191 |

The done-when is met: `python -m canopy.cli wonder maine --place us_census_sldl:23042` reads House District 42 through its edges. The progress report is field-guide/docs/progress/information/sprint-05.md.

On real Maine data: 1,663 places, 2,693 edges, 12,526 value rows with 3,222 agreeing rows collapsed, 744 district values attached. No value file carries an `authority` column. LIN-3 is closed: derive_values and standardize_standings now carry lineage and may leave at public.

## Contracts

field-guide/docs/contracts/: 1 tiers and the gate 0.5; 2 canonical objects 0.1; 3 geography graph 1.0 (four rules in section 4; G-1 to G-11; the grove teammate's own review is owed before the handoff); 4 place profile 0.2.

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
| Every authority is declared, each level under one | seeds/authorities/authorities.yml; tests/test_authorities.py holds six copies to it (D-188) |
| District values keyed by chamber | tests/test_district_values.py (D-176) |
| Only a declared count moves along an edge | canopy/loam/edge_rules.py; tests/test_edge_rules.py (D-179) |
| Every indicator's universe is declared | seeds/universes/universes.yml; tests/test_universes.py (D-181) |
| An index never ranks across authorities | weighted_index.R; tests/test_index_r_oracle.py (D-190) |

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
| NAME-4 | manifests still name a source's publisher provenance.authority (block and inline forms), read by preview.py, recipe.py's SOURCE_FACTS and $source.authority; one sweep renames it to published_by | ledger, change 13 |
| SRC-2 | build D-189 in NAME-4's sweep: unit_authority on every indicator source, $source.unit_authority in the recipe, a run declaring its own refused; check freshness reads the receipts as fresh after | ledger, build 6 |
| LAYER-1 | build D-191: layer sources declare unit_authority and their key property (NAME-4's sweep); map.py's join by declared authority (Sprint 08); verify the district layers' property names first | ledger, build 6 |
| COUNT-1 | count people, not rates: households with a barrier are value times households over 100, allocated along an edge by D-179's rule; the outreach planner's starting point (Sprint 12) | ledger, change 12 |
| TENURE-1 | a renter share needs a renter weight on the edges; which 2020 table carries tenure by block is not yet checked | ledger, change 12 |
| KIT-1 | Sprint 10 must decide: --accept-stale, hashing primitive code, VER-1, DEPS-1. Real instance (change 13): after derive_indicator.R changed, every value receipt read fresh and was rerun by hand | ledger |
| TRIBE-6 | compare Maine's 8 tribal areas, 2024 against 2020; an unchanged one may attach values (D-171); with Kalli and Person 3 | ledger, change 7 |
| NOTE-3 | the tribal representation note (MP-77) is not written; also confirm maine_seats' tribal list | ledger |
| LEDGER-3 | MAP-4 names two entries (Sprint 02's county map check and the _UNIT_KEYS gap); a reference to MAP-4 must say which | ledger, build 6 |
| LIN-2 | provenance repeats an inherited step (no dedup in _merge_provenance); harmless | ledger |
| VER-1 | provenance version comes from the step definition, so it never signals changed code | ledger |
| NOTE-2 | descendants of places other than outlines write no row_context_notes | ledger, Sprint 04 |
| Rule 10 | places and every outline are withheld at public under rule 10 only (LIC-1?) | ledger, Sprint 04 |
| TRIBE-5 | 0115T, 2695T, 2760T outlines do not nest in the Census 2020 layers by more than water | ledger, Sprint 04 |
| PENOB-1 | the Main Stem note's wording waits on Kalli and Person 3 | ledger, Sprint 04 |
| GJSON-1 | rewildr's safe_write_sf cannot overwrite a GeoJSON holding one very large feature | ledger, Sprint 04 |
| RESOLVE-1 | sows --resolve-only and resolve_data can acquire and commit | ledger |
| DEPS-1 | geopandas and pyogrio are installed but not declared | ledger, Sprint 04 |
| SEAM-2 | outlines and overlap weights disagree on split blocks, by design; do not fix | ledger |
| DAS-1 | households without persons in block 230219603011057; disclosure avoidance hypothesis, unverified. Zero is judged by the value's universe (D-180) | ledger |
| HIST-1 | waiting on CII's reply to Kalli's Nov 10 email | ledger |
| Person 3 | D-118's tiers, ROLE-1, the draft notes, NOTE-3, D-173's review | ledger |

Closed in Sprint 05: LOAM-1, KEYS-1, CON3-1, ZERO-1, NAME-2, AUTH-1, SRC-1, SEAM-1, MAP-4, LIN-3. LIN-3's receipts carry lineage.

Also carried, look up in the ledger before relying on them: S2-1, GATE-2, GATE-3, MAP-8, MAP-9, TRIBE-4, SEN-1, LEGI-1, LEG-4, LIC-1, KEY-1, XCHK-1, COMP-1, REG-1, LOOP-1, ACQ-6, SCH-5, TAG-1, MEGIS-3, LURC-1, BAXTER-1, DISS-1, METH-1.

Untested refusals: a town in two counties, a county or district without a name, a place key used twice (build_places refuses it; untested), a reservation subdivision in two reservations, a missing vintage, derive_indicator.R's refusal of a leftover `authority` param.

## Working agreement, as it stands

- Design before code, forks one at a time with a lean, nothing chosen silently. Kalli reads, runs and commits; Claude drafts.
- No zip files. Every file comes inline as `cat > path << 'EOF'`, one file per paste: zsh takes a whole paste as one buffer, a long one can break, and Ctrl-C discards all of it.
- Every `EOF` starts at the left edge of its line; an indented `EOF` leaves the shell in an unfinished heredoc.
- Whole-file replacements, except where Kalli chooses a guarded edit script for a large file: every edit must match exactly before anything is written, and `git --no-pager diff` is read before running anything.
- Every commit block is guarded: it commits only if the code files it names have changed, and prints STOP otherwise.
- Ledger blocks appended with cat >>, each starting with a newline. No em dashes, no inline shell comments.
- Before changing a signature, search for the keyword itself across every test and caller, then read each hit for meaning.
- Read real output as its reader would before committing a telling.

## Traps

- /mnt/project in Claude's sandbox is a stale October snapshot. The repo is on Kalli's machine.
- Run a preparation with `python -m canopy.cli sows <run.yml>`; `--dry-run` only validates. Never `--resolve-only` casually: it can acquire and commit (RESOLVE-1).
- Do not run maine_seats on real data before 2026-12-02.
- `authority` means only who assigns a place's code. A value's publisher is `published_by` in value tables, run files and recipes, but still `provenance.authority` in manifests until NAME-4. Join values to places on (unit_authority, unit_code).
- preview.derive takes `published_by=`, not `authority=`; derive_indicator.R refuses an `authority` param by name.
- Freshness never judges primitive code (KIT-1): after a primitive changes, its receipts still read fresh. Rerun them by hand, and say so in the ledger.
- `$indicators.<id>` resolves to the whole declaration, so editing an indicator seed changes every derive step's params and makes its receipts stale. Facts about indicators that are not the indicator belong in a seed beside them (seeds/universes/).
- seeds/weights/ holds index weightings (`$weights.`); edge weights are declared per universe in seeds/universes/. Same word, two ideas.
- The views (places, edges, indicator_values, indicator_value_rows, place_values, plot_places) exist only in a bed opened by open_plot; Loam.snapshot() copies the catalog table alone, by design (D-168). VALUES is reserved in SQL.
- `wonder --place` takes a key, AUTHORITY:CODE, never a name: 23005 is a county, a House district and a Senate district.
- A town range is one estimate per town. Read the firm range (towns wholly here, on a sound sample) before quoting a range's ends.
- open_plot parses the manifest once and hands it to planting and the graph (P-01).
- A step's `outputs:` in a preparation gives names, not file paths. Receipts are `.envelopes/<step>_<output>.envelope.json`, one flat namespace per plot.
- Tests that fake EnvelopeBuilder.run must accept run and step. A signature change reaches every fake and every caller of it.
- A test fake that records an md5 must record the real one: freshness recomputes it.
- Progress reports live in field-guide/docs/progress/<domain>/sprint-NN.md.
- The ledger holds the Sprint 04 step 4e block twice (LEDGER-2), and MAP-4 names two entries (LEDGER-3).
- The geography graph preparation declares `vintages` twice, for graph_edges and graph_places; change both together (D-162).
- The gate runs only at exits (canopy/expose/check.py). Inside a run only the precondition gate applies.
- `sows` prints nothing until the run ends.
- R primitives: primitive_success serializes with auto_unbox, so a list of one needs as.list (C-36). rewildr's safe_read_table infers CSV types; read code columns as text.
- Vocabulary.load reads only semantic_types.yml and domains/*.yml.
- soil/_registry.yml, seeds/schemas/semantic_types.yml and seeds/notes/notes.yml each end with their one map, so appends land correctly.
- Scope every grep: quote globs, and never grep `plots` without `--include="*.yml"`.
- `git diff` opens a pager; use `git --no-pager diff` when pasting output.
- Keys live in Kalli's environment only (KEY-1). The repo is public.
- The sandbox lacks pytest, pyarrow, shapely, duckdb, jsonschema, pyogrio and R; it has pandas and yaml. Pure-Python logic can be smoke-run there with stand-ins.

## People

Kalli: Maine data and geography, profile, explorer, review of everything; acting grove teammate. Ajitesh: publish route (Sprint 08); LAYER-1, GJSON-1 and D-157's required notes argument matter for his door. Infrastructure teammate: Sprints 07 and 10; DEPS-1 and KIT-1 matter for the Docker build. Person 3: tier declarations, note wording, NOTE-3 and D-173's review.
