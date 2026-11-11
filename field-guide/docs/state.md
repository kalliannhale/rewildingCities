# State of the garden ~ rewildingCities

What is true now. Rewritten, never appended, at every hand-off (D-160). The
build ledger (field-guide/docs/build_ledger.md) is the history; this page is
the present. When the two disagree, the ledger and the code win, and this page
is fixed.

**Updated:** 2026-11-11, at the hand-off closing Sprint 06's first build session.

## Where the build stands

- Branch main. Confirm with `git log --oneline -15` and `git status -sb`, and that both are pushed. This session's commits, oldest first: 6fc983e (outlet stack), 887e301 (outlet groups), ad5bfad (no row-order joins), 2770bdd (place fields keep their meaning), 9997271 (outlet steps as primitives), a335cd0 (ledger D-201 to D-205; progress report opened), 377a7dd ($crosswalks, D-206), the D-206 ledger commit, 18619db (maine_outlets preparation), f1a9d6c (located_in logic), d8227b9 (located_in primitive, D-207), daabdf8 (libraries placed, D-208), cc31c52 (carriers counted, D-209), the carrier-reading commit (place.py), and this hand-off.
- Tests: `python -m pytest -q -rs | tail -3`. 643 passed, no skips, at this hand-off. The R oracle tests run only where Rscript and rewildr are installed; `-rs` names a skip, since a skip proves nothing.
- Plan of record: the Master Plan, https://claude.ai/artifact/KpQRRSTyXr27emXnJFfL6z. Its decision table stops at D-81 and its Sprint 06 tab predates the design pass (D-197 to D-200); check its claims against this page and the code. Its tab is updated at Sprint 06's close.
- Next decision ID: D-210. Before minting any ID, grep the ledger for it (LEDGER-3). Item IDs too.
- **Sprint 06 is open**, across several sessions, in the order below. Progress: field-guide/docs/progress/information/sprint-06.md.
- On or after 2026-12-02, when the 133rd's rosters are acquired: flip available: true, TRIBE-4, SEN-1, then run maine_seats.

## Sprint 06 ~ the place profile and the standard

**Goal:** every Maine place has a six-part profile, its carriers are on the map, and every barrier is judged against a stated, absolute standard.

**Decided in the design pass:** D-197 (build_profile wraps read_place), D-198 (margin-aware verdicts, derive_margins), D-199 (universal, trigger, none thresholds), D-200 (each barrier a family of registered indicators with a status).

**Decided in session 1:** D-201 to D-209, below.

**Order of work, and where each step stands:**

```
 1  P-9: read the outlet files                done      answered (below)
 2  located_in edges + end checks             done      D-207
 3  carriers, counted per 1,000               1 of 5    libraries done end to end
      libraries (IMLS PLS FY 2024)            done      maine_libraries: placed, counted, read apart
      town offices                            blocked   no point source (see Traps); needs a geocoder
      schools (Maine DOE)                     next      check for a published coordinate layer first
      health centers (HRSA)                   not yet
      outlets                                 not yet   waits on WHERE-1 and a geocoder
 4  derive_margins (D-198)                    not yet
 5  language: ACS, safe harbor, section 203   not yet
 6  literacy: PIAAC county estimates (P-7)    not yet
 7  digital access counts + FCC map (P-6)     not yet
 8  outlets reconciled                        partial   stacked, grouped, disagreements listed;
                                                        ownership and concentration to go
 9  profile.py + the standard seed            started   place.py reads carriers apart (its first piece)
10  pairing table (P-2)                       not yet
11  profiles for every place                  not yet
```

**The barriers, their indicators, and where the data is** (as decided in the design pass; P-9 has changed three rows' status):

| Barrier | Indicators | Source | Grain | Status |
| --- | --- | --- | --- | --- |
| Not in the right language | limited-English persons by language; safe-harbor languages; VRA section 203 coverage | ACS language-by-ability tables; DOJ LEP guidance (2002); Census section 203 file (2021) | town | acquirable |
| Requires digital access | households with no internet subscription; no service at the FCC benchmark | ACS; FCC National Broadband Map | town | ACS acquired as a rate; counts and FCC acquirable |
| At the wrong literacy level | adults at or below Level 1 | NCES PIAAC Skills Map (pooled 2012/14/17) | county, borrowed on towns | acquirable |
| Lacking cultural cues | languages spoken against languages carriers publish in | ACS and our own observation of outlets | town | needs our observation (OBS-1): no listing carries language |
| Behind a paywall | share of local outlets free to read | our own observation (OBS-1), P-3 | town | needs our observation: no listing carries paywall status |
| Outdated | outlet publishing frequency; observed last post | Cision, the ecosystem file, Easton (frequency); Cision's Still Operates? (last post) | town | acquirable from the stack |
| Not where people look | carriers per 1,000 by type | IMLS (done), schools, health centers, town offices, outlets | every level | libraries acquired (D-209) |
| Not from a trusted source | relational hubs, aggregate-only | consent-governed | as consented | needs_consent (Sprint 16) |

**Still open in Contract 4:** P-1 (each threshold, row by row), P-2 (pairing table), P-3 (free outlet), P-5 (a universal side for language; lean yes), P-6 (FCC benchmark), P-7 (PIAAC 2023?), P-8 (section 203 on Wabanaki places, with Person 3). P-9 is closed.

## Decided in session 1

| ID | One line |
| --- | --- |
| D-201 | Outlet sources read only as seeds/crosswalks/outlets/outlet_sources.yml declares; headers found by declared names; never_read columns refused |
| D-202 | Outlet records grouped by exact url (path kept) and name keys; never one source twice; a key one source holds twice joins nothing |
| D-203 | Place fields keep their meaning: office_* a postal address, named_* a town a source names, served_raw coverage; compared like with like |
| D-204 | An outlet's county comes from the graph through its town; a source's county is a check (Cision's reads Cook, Illinois) |
| D-205 | Outlet listings stay in garden/reference/ (ignored) and are manifest datasets with paths outside the plot |
| D-206 | `$crosswalks.<name>` resolves seeds/crosswalks/**/<name>.yml into params, so freshness sees an edit |
| D-207 | located_in edges are their own type, located_in_edges, one artifact per layer; towns from the 2024 face, districts and tribal areas from the face's 2020 block |
| D-208 | A library outlet is FSCSKEY-FSCS_SEQ; fixed outlets only; bookmobiles listed, never placed; flags kept; the outlet file is Windows-1252 by its own text |
| D-209 | A carrier is a registered indicator, role carrier, derivation located_count, in seeds/indicators/carriers.yml; every place a row, the count beside the rate; loam's statistical rule now judges ACS values only |

## Contracts

field-guide/docs/contracts/: 1 tiers and the gate 0.5; 2 canonical objects 0.1; 3 geography graph 1.0 (the grove teammate's review owed; CON3-2: section 2 still calls located_in a kind in the edges table); 4 place profile 0.3.

## Where invariants are held

| Invariant | Held by |
| --- | --- |
| Every town has one contains edge from its county | build_place_edges; tested |
| A block's county is its 2024 town's (BOUND-1) | build_block_spine; tested |
| Shares sum to 1 per chamber, per basis | build_place_edges, check_shares; tested |
| Every district touches a town | by construction (D-161); tested |
| Edge ends exist in places | build_places; tested. located_in: build_located_in refuses a `to` end not in places |
| A point's town is its face's; its districts its block's (D-207) | build_located_in; tests/test_located_in.py |
| A point counts in every area it falls in | build_located_in, count_located; tested |
| Vintages match | build_places (D-162); place_values through seeds/vintages/boundaries.yml (D-170); tested |
| Tribal places carry their note and name their area | build_places; tested |
| Every authority is declared, each level under one | seeds/authorities/authorities.yml; tests/test_authorities.py (D-188) |
| District values keyed by chamber | tests/test_district_values.py (D-176) |
| Only a declared count moves along an edge | canopy/loam/edge_rules.py (D-179) |
| Every indicator's universe is declared | seeds/universes/universes.yml (D-181) |
| A run's copy of a source fact agrees with the source | Orchestrator._validate_source_facts (D-192, D-193) |
| An outlet column not declared is never read | stack_outlet_sources; tests/test_outlet_sources.py (D-201) |
| No outlet match is chosen by row order | group_outlet_records; tests/test_outlet_groups.py (D-202) |
| A located_count asks no acquisition for anything | registry; tests/test_located_count_indicator.py (D-209) |
| A carrier is read by its method, never ranged | place.py; tests/test_place_carrier.py |

## Open items

| ID | One line |
| --- | --- |
| GEO-1 | No geocoder exists. Fork with a lean: the Census Geocoder first (free, batch 10,000, returns match type and 2020 block), ArcGIS or Maine NG911 address points beside it later as second authorities. Unblocks town offices, outlets, WHERE-1 |
| WHERE-1 | Which place meaning counts as where an outlet is (office, named town, coverage) |
| OBS-1 | Language of publication and paywall status need our own observation of each outlet, a receipt per observation |
| SRC-4 | The ecosystem file's publisher, the Still Operates? receipt, every outlet source's terms |
| TOWN-OFF-1 | Town offices: MEGIS Town Points are centroids, refused as carriers; an address list is needed (Maine Municipal Association? Secretary of State?) |
| LIB-2 | MEGIS publishes its own Libraries layer (390 points) against IMLS's 262 fixed outlets: a second authority, to be read side by side |
| SERVES-1 | A carrier's location is not whom it serves; visits per person waits on a serves relation (library systems' legal service areas) |
| TRIBE-7 | The PLS does not see reservation libraries; a tribal area's carrier reads as unseen, never zero. Wording with Person 3 |
| INDFILE-1 | An indicator file's sha256 lands in every receipt that read any indicator from it; decide one file per carrier family (lean) or rerun on every addition |
| SCALE-1 | place.py writes "per 1,000" while the scale lives in the declaration; carry the scale in each value row |
| SURVEY-1 | Loam's only boundary rule is the final year of `time`; a later survey on the 2024 places must still name 2024 |
| LOAM-2 | place_values reads the ACS's levels for every publisher |
| LOC-VIEW-1 | No loam view of located_in edges yet; needed to name the libraries in a place |
| OUT-REG-1 | stack_outlet_sources' registry entry names Maine's five listings |
| CON3-2 | Contract 3 section 2 needs D-207's wording |
| SCHEMA-1 | A metadata field's type is checked only by a real run; a test could validate output_metadata against seeds/schemas |
| STAT-1 | IMLS's meaning of STATSTRU 25 |
| RECEIPT-1 | Rerun maine_counties, maine_county_units and maine_governance_units when anything reads them through $loam. (8 receipts predate D-167) |
| SRC-3, USE-1, SPEC-1, LAYER-1, COUNT-1, TENURE-1, KIT-1, TRIBE-6, NOTE-3, LEDGER-1 to LEDGER-3 | as before; look each up in the ledger |
| Person 3 | D-118's tiers, ROLE-1, the draft notes, NOTE-3, D-173's review, P-8, TRIBE-7's wording, tiers for the outlet and located_in types |

Also carried, look up in the ledger first: S2-1, GATE-2, GATE-3, MAP-8, MAP-9, TRIBE-4, SEN-1, LEGI-1, LEG-4, LIC-1, KEY-1, XCHK-1, COMP-1, REG-1, LOOP-1, ACQ-6, SCH-5, TAG-1, MEGIS-3, LURC-1, BAXTER-1, DISS-1, METH-1, LIN-2, VER-1, NOTE-2, TRIBE-5, PENOB-1, GJSON-1, RESOLVE-1, DEPS-1, SEAM-2, DAS-1, HIST-1.

## Working agreement, as it stands

- Design before code, forks one at a time with a lean, nothing chosen silently. Small choices: Claude takes the lean and says so. Kalli reads, runs and commits; Claude drafts.
- Go in the plan's order unless Kalli says otherwise.
- Before any threshold or external claim, Claude researches and cites what a source actually says, and says plainly where a source gives no number.
- Changes come as a zip of repo-relative files (Kalli's preference), unzipped from the repo root with `unzip -o ~/Downloads/<n>.zip -d .`; small files and every ledger block come inline. Inline files are `cat > path << 'EOF'`, one file per paste, every `EOF` at the left edge. A file Claude has not seen whole is changed by a guarded helper in `_sprint06/` that writes nothing unless its anchor matches once; the helper folder is deleted after.
- Whole-file replacements; `git --no-pager diff --stat` is read before anything runs.
- Every commit block is guarded and names its files: a zsh array, `git add -- $files`, then `git diff --cached --quiet -- $files` prints STOP when nothing changed, and `git commit -- $files` keeps anything else out.
- Ledger blocks appended with cat >>, each starting with a newline. Grep every new ID first. No em dashes, no inline shell comments.
- Before changing a signature, search the keyword across every caller and test, then read each hit for meaning.
- Read real output as its reader would before committing a telling. A receipt is read after every real run.
- Usage: one step per chat; state.md is the only upload at the start; long output is filtered (`| tail -3`, `| grep`); Claude names exact files and asks for whole files rather than many line ranges.

## Traps

- /mnt/project in Claude's sandbox is a stale October snapshot. The repo is on Kalli's machine.
- Run everything from the repo root. An unzip from field-guide/docs once made second copies of soil/ and tests/ there, and pytest refused the duplicate test names.
- Run a preparation with `python -m canopy.cli sows <run.yml>`; `--dry-run` only validates. `sows` prints nothing until the run ends. Never `--resolve-only` casually (RESOLVE-1).
- Do not run maine_seats on real data before 2026-12-02.
- `authority` means only who assigns a place's code; a publisher is `published_by` everywhere, manifests included.
- `$indicators.<id>` resolves to the whole declaration and carries the sha256 of the whole file it lives in. Never add an indicator to an existing indicators file whose receipts exist: a new file (as carriers.yml) leaves every hash alone.
- loam's `edges` view is made from exactly one `place_edges` artifact (D-163); never write a second. Point edges are `located_in_edges` (D-207).
- loam's place_values attaches a value only when seeds/vintages/boundaries.yml holds a rule for its `published_by`; it reads the ACS's `levels` for every publisher (LOAM-2).
- The 2024 faces are a zip of county zips (plots/maine/.data/maine_faces_2024.zip); build_block_spine reads their .dbf only, build_located_in their geometry.
- The IMLS outlet file is Windows-1252: declared, never sniffed. A pandas read that falls back silently would have written a control character into two names.
- A test loading a soil module by file path must register it in sys.modules before exec when the module defines a dataclass.
- The envelope schema checks metadata types (a point layer's total_area_m2 is 0.0, never null); fixture tests do not see this (SCHEMA-1).
- MEGIS Maine Town Points (METWP24PT) are town centroids, not offices: refused as a carrier layer.
- Freshness never judges primitive code (KIT-1), and is judged only when a run reaches a `$loam.` input. The read-only probe: build an Orchestrator on any Maine preparation, then `judge(read_envelope(p), orch.project_root, orch._declared_params)` for each file in plots/maine/.envelopes.
- `wonder --place` takes a key, AUTHORITY:CODE, never a name. A town range is one estimate per town; read the firm range before quoting a range's ends. A carrier has no range.
- A step's `outputs:` gives names, not paths. Receipts are `.envelopes/<step>_<o>.envelope.json`.
- The geography graph preparation declares `vintages` twice; change both together (D-162).
- Scope every grep: quote globs, and never grep `plots` without `--include="*.yml"`. `git diff` opens a pager; use `git --no-pager diff`. It is `git status -sb`, one dash.
- Keys live in Kalli's environment only (KEY-1). The repo is public. garden/reference/ and **/.data/ are ignored; commercial listings never leave them.
- The sandbox lacks pytest, pyarrow, shapely, geopandas, duckdb, jsonschema, pyogrio and R; it has pandas and yaml.

## People

Kalli: Maine data and geography, profile, explorer, review of everything; acting grove teammate. Ajitesh: publish route (Sprint 08); LAYER-1, GJSON-1 and D-157's required notes argument matter for his door. Infrastructure teammate: Sprints 07 and 10; DEPS-1, KIT-1 and OUT-REG-1 matter for the Docker build. Person 3: tier declarations, note wording, NOTE-3, D-173's review, P-8, TRIBE-7.

## Starting the next session

Upload this file only, with a first message like the one in the hand-off. Claude reads it, confirms, and asks for exactly what the next step needs. The next step in order is schools (step 3); before building, find whether the Maine Department of Education publishes school locations with coordinates. If it does, the layer follows maine_libraries' path: a manifest dataset, a points step, build_located_in, count_located, and a carrier indicator. One fork comes first (INDFILE-1): carriers.yml now has a receipt that carries its hash (libraries_counts), so adding the schools indicator there makes that receipt stale. Either each carrier family gets its own file (seeds/indicators/carriers_schools.yml), or carriers.yml grows and maine_libraries is rerun, which is cheap. Lean: one file per carrier family, so no receipt is staled by a neighbour's declaration.
