# State of the garden ~ rewildingCities

What is true now. Rewritten, never appended, at every hand-off (D-160). The
build ledger (field-guide/docs/build_ledger.md) is the history; this page is
the present. When the two disagree, the ledger and the code win, and this page
is fixed.

**Updated:** 2026-11-13, at the hand-off closing Sprint 06's fourth build session.

## Where the build stands

- Branch main. Confirm with `git log --oneline -15` and `git status -sb`, and that both are pushed. Session 4's commits: "CMAP-1: carrier kinds as types, institutional_node retired; every live declaration names a current type (D-218 to D-222)" and this hand-off. Session 3's ended at its hand-off, after df74b0d.
- Tests: `python -m pytest -q -rs | tail -3`. 829 passed, no skips, at this hand-off (new in session 4: tests/test_carrier_types.py, tests/test_current_type_names.py, two cases in tests/test_registry_paths.py). The 2 warnings are Starlette and FastAPI test-client deprecations (httpx, anyio) in tests/test_unit_authority.py, not ours. The R oracle tests run only where Rscript and rewildr are installed; `-rs` names a skip, since a skip proves nothing.
- Plan of record: the Master Plan, https://claude.ai/artifact/KpQRRSTyXr27emXnJFfL6z. Its decision table stops at D-81 and its Sprint 06 tab predates the design pass (D-197 to D-200); check its claims against this page and the code. Its tab is updated at Sprint 06's close.
- Next decision ID: D-223. Before minting any ID, grep the ledger for it (LEDGER-3). Item IDs too.
- **Sprint 06 is open**, across several sessions, in the order below. Progress: field-guide/docs/progress/information/sprint-06.md.
- On or after 2026-12-02, when the 133rd's rosters are acquired: flip available: true, TRIBE-4, SEN-1, then run maine_seats.

## Sprint 06 ~ the place profile and the standard

**Goal:** every Maine place has a six-part profile, its carriers are on the map, and every barrier is judged against a stated, absolute standard.

**Decided in the design pass:** D-197 (build_profile wraps read_place), D-198 (margin-aware verdicts, derive_margins), D-199 (universal, trigger, none thresholds), D-200 (each barrier a family of registered indicators with a status).

**Decided in session 1:** D-201 to D-209. **In session 2:** D-210 to D-212. **In session 3:** D-213 to D-217. **In session 4:** D-218 to D-222, below.

**Order of work, and where each step stands:**

```
 1  P-9: read the outlet files                done      answered
 2  located_in edges + end checks             done      D-207
 3  carriers, counted per 1,000               1 of 5    libraries done end to end
      libraries (IMLS PLS FY 2024)            done      D-208 to D-212: placed, counted, closures declared
      first, by Kalli's order (session 2):
        SCHEMA-2: the method schema           done      D-213 to D-217
        CMAP-1: the carrier map as a view     started   types done (D-218, D-219); the view next
        the drift CMAP-1's walk found         done      D-220 to D-222
      schools                                 after     three candidate sources (below); INDFILE-1 first
      town offices                            blocked   no point source (see Traps); needs a geocoder
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

**Schools, read so far (session 2).** Nothing chosen; the source is a fork.

| Source | What was read | Not yet read |
| --- | --- | --- |
| Maine DOE, Data Warehouse, Schools & SAU Data | the page body loads dynamically and came back empty | everything: Kalli to open it in a browser (a file? coordinates or addresses? a state school ID?) |
| NCES EDGE, Public School Locations 2024-25 | points from the 2024-25 CCD collection; public domain; REST, CSV, GeoJSON; geocoded from the reported street address, so a point is an address match; private schools are a separate file, 2023-24 its latest | its field list, its Maine count |
| MEGIS, Maine_Schools_GeoLibrary (FeatureServer 8) | a point layer in NAD83 / UTM 19N; fields Name, Address, City, Zipcode, Source_Originator, Source_FeatureID, PointLocationType, FType/FCode, GNIS_ID, fmupddat; no state school ID, grade span, public/private flag or status; data last edited 2021-04-28 | its feature count |

The remark from session 2, to check rather than assume: as with libraries, the address may be the state's (CCD addresses are reported by state education agencies, as far as known) and the point the federal publisher's, so a receipt would name both, with MEGIS read beside it as a second authority (LIB-2's shape). Also to check: whether the Maine Indian Education schools appear in CCD at all (a TRIBE-7 cousin: unseen is never zero), and that a school's location is not whom it serves (SAUs; a SERVES-1 cousin).

**The barriers, their indicators, and where the data is** (as decided in the design pass; P-9 has changed three rows' status):

| Barrier | Indicators | Source | Grain | Status |
| --- | --- | --- | --- | --- |
| Not in the right language | limited-English persons by language; safe-harbor languages; VRA section 203 coverage | ACS language-by-ability tables; DOJ LEP guidance (2002); Census section 203 file (2021) | town | acquirable |
| Requires digital access | households with no internet subscription; no service at the FCC benchmark | ACS; FCC National Broadband Map | town | ACS acquired as a rate; counts and FCC acquirable |
| At the wrong literacy level | adults at or below Level 1 | NCES PIAAC Skills Map (pooled 2012/14/17) | county, borrowed on towns | acquirable |
| Lacking cultural cues | languages spoken against languages carriers publish in | ACS and our own observation of outlets | town | needs our observation (OBS-1): no listing carries language |
| Behind a paywall | share of local outlets free to read | our own observation (OBS-1), P-3 | town | needs our observation: no listing carries paywall status |
| Outdated | outlet publishing frequency; observed last post | Cision, the ecosystem file, Easton (frequency); Cision's Still Operates? (last post) | town | acquirable from the stack |
| Not where people look | carriers per 1,000 by type | IMLS (done), schools, health centers, town offices, outlets | every level | libraries acquired (D-209, D-211) |
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
| D-206 | `$crosswalks.<n>` resolves seeds/crosswalks/**/<n>.yml into params, so freshness sees an edit |
| D-207 | located_in edges are their own type, located_in_edges, one artifact per layer; towns from the 2024 face, districts and tribal areas from the face's 2020 block |
| D-208 | A library outlet is FSCSKEY-FSCS_SEQ; fixed outlets only; bookmobiles listed, never placed; flags kept; the outlet file is Windows-1252 by its own text |
| D-209 | A carrier is a registered indicator, role carrier, derivation located_count, in seeds/indicators/carriers.yml; every place a row, the count beside the rate; loam's statistical rule now judges ACS values only |

## Decided in session 2

| ID | One line |
| --- | --- |
| D-210 | A library outlet's structure status is declared once, code to meaning and group (open, permanent, temporary); a blank or undeclared status on a fixed outlet refuses the run; permanently closed outlets are listed, never placed (a rule). Codes from IMLS PLS FY 2024 Documentation, Appendix B; 22 left undeclared |
| D-211 | A temporary closure is a method choice, temporarily_closed (listed or placed); Maine chooses listed, following IMLS's own tables, so Atkins Memorial, Corinth, is listed and 261 fixed outlets are placed; the primitive refuses any other value |
| D-212 | A carrier's meaning lives once, in its method; docstring, run header, registry and indicator rationale point to it. A rule (the other way is simply wrong) is a test; a choice (reasonable people differ) is declared. Bookmobiles are a rule |

## Decided in session 3

| ID | One line |
| --- | --- |
| D-213 | seeds/schemas/method.schema.yml (v2.0) is the one home of a method's shape, additionalProperties false throughout. Every reader loads a method through parsing.load_method_data: an undescribed shape, a key written twice or a default outside its options is refused, every problem named. A run on a refused method is a validate() error. Options are a mapping keyed by option id; an empty value means the choice's description says it; no option carries an id of its own |
| D-214 | requires_primitives is a list of layer/name references, each resolving in its registry; a recipe uses only primitives its method declares; per-method purposes are YAML comments |
| D-215 | produces is a list, even for one output |
| D-216 | garden/methods/index.yml routes only (domain, id, path); a method's name and answers_question_types live in the method; MethodIndexEntry carries neither |
| D-217 | roots/count_by_unit deleted, never registered: count_located (D-209) is the one count of points in places |

## Decided in session 4

| ID | One line |
| --- | --- |
| D-218 | Each carrier kind is its own semantic type in the domain vocabulary, never one type with a kind field |
| D-219 | institutional_node retired with no alias; IMLS's placed outlets are library_outlet; the unbuilt Maine manifest entry removed; maine_libraries rerun (261 placed, 3 mobile and 1 temporarily closed listed, as before) |
| D-220 | A live declaration names a current type, never an alias or a state-suffixed name: state is provenance, kept in the receipt. Aliases and suffix_fallback stay to read old receipts forward |
| D-221 | Every type live work named is declared (water, forest, neighborhood boundaries; roads, nighttime_lights, population_density; measured_composition) or renamed to its existing home; check_alignment unregistered, its 0-byte file deleted |
| D-222 | The wonder composer drafts current types; the three composed drafts (e6e967, 4ade33, STUB-1's 4a8f59) deleted |

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
| A mobile or permanently closed library outlet is never placed | prepare_library_points; tests/test_library_points.py (D-208, D-210) |
| A fixed outlet's structure status is declared, or the run refuses | prepare_library_points; tests/test_library_points.py (D-210) |
| A temporary closure follows a choice its method declares | prepare_library_points; tests/test_library_points.py, tests/test_library_preparation.py (D-211) |
| Every method matches the method schema; a run on one that does not is an error | parsing.load_method_data, Orchestrator._validate_method_choices; tests/test_method_schema.py (D-213) |
| Every primitive a method names resolves in its registry; a recipe uses only declared primitives | tests/test_method_schema.py (D-214) |
| The index routes every method file once, by the method's own id and domain | tests/test_method_schema.py (D-216) |
| Each carrier kind is its own type; institutional_node is gone, with no alias | tests/test_carrier_types.py (D-218, D-219) |
| Every type a registry entry, method, manifest, preparation or experiment names is current: declared, never an alias or a state spelling | tests/test_current_type_names.py (D-220, D-221) |
| A draft wonder composes names current types | wondering._compose_steps; tests/test_current_type_names.py (D-222) |
| A registry entry points at a file that exists and holds code | tests/test_registry_paths.py (REG-6) |

## Open items

| ID | One line |
| --- | --- |
| CMAP-1 | The carrier map as a view, never a file. Types done (D-218, D-219). To go: where carrier-hood lives (lean: the indicator registry, role carrier), the bridge from an indicator's located_in layer label to its points' type, the IMLS catalogue in seeds/sources/ (census_tigerweb.yml is the model), and the view itself. No seeds/carriers/ |
| TIERREAD-1 | Vocabulary.get_tier reads extra["tier"], while every domain file declares resolution_tier, so get_tier is None for every information type. Find who reads resolution_tier before new carrier types lean on it |
| QUADRAT-1 | Whether a measured quadrat becomes a bird's-eye mask, to share falsification_test's one currency (label masks): a modeling choice for the day field data exists |
| FSCS-1 | Outlets of systems the survey does not count as public libraries (C_FSCS N; Cliff Island placed, Corinth listed) count under "Public library outlets"; IMLS keeps them in its files but out of aggregate figures. Place, list, or rename the indicator |
| CHOICE-1 | The orchestrator only warns when a run's choice is not among its method's options, or a declared choice is missing (orchestrator.py, _validate_method_choices). Lean: an error. Sharper since D-213: the method's shape is now strict while a run's choice against it still only warns |
| SCHEMA-3 | canopy/wonder (wondering.py, possibility.py) reads method YAML raw, not through load_method_data, and still accepts the retired produces and requires_primitives shapes; route it through the one loader and drop them. D-222 changed what _compose_steps writes, not how it reads |
| INTERP-1 | The thermal, perception and county_units_for_mapping methods have no top-level interpretation; required once each has one |
| OWN-1 | ownership_concentration_analysis is pre-graph: geocode_to_unit places an outlet by matching place-name strings (a silent WHERE-1 choice, against D-203, D-204), concentration_index keys by feature_id. Redesign over located_in and count_located at step 8, after WHERE-1 and GEO-1. Its institutions input still describes libraries, town halls, schools and government sites while its types hold library_outlet; widen it as each carrier type arrives |
| GEO-1 | No geocoder exists. Fork with a lean: the Census Geocoder first (free, batch 10,000, returns match type and 2020 block), ArcGIS or Maine NG911 address points beside it later as second authorities. Unblocks town offices, outlets, WHERE-1 |
| WHERE-1 | Which place meaning counts as where an outlet is (office, named town, coverage) |
| OBS-1 | Language of publication and paywall status need our own observation of each outlet, a receipt per observation |
| SRC-4 | The ecosystem file's publisher, the Still Operates? receipt, every outlet source's terms |
| TOWN-OFF-1 | Town offices: MEGIS Town Points are centroids, refused as carriers; an address list is needed (Maine Municipal Association? Secretary of State?) |
| LIB-2 | MEGIS publishes its own Libraries layer (390 points) against IMLS's 261 placed outlets: a second authority, to be read side by side |
| SERVES-1 | A carrier's location is not whom it serves; visits per person waits on a serves relation (library systems' legal service areas) |
| TRIBE-7 | The PLS does not see reservation libraries; a tribal area's carrier reads as unseen, never zero. Wording with Person 3; seeds/notes/notes.yml holds none yet |
| INDFILE-1 | An indicator file's sha256 lands in every receipt that read any indicator from it; decide one file per carrier family (lean) or rerun on every addition. carriers.yml changed in session 2 and maine_libraries was rerun, so libraries_counts is current |
| SCALE-1 | place.py writes "per 1,000" while the scale lives in the declaration; carry the scale in each value row |
| SURVEY-1 | Loam's only boundary rule is the final year of `time`; a later survey on the 2024 places must still name 2024 |
| LOAM-2 | place_values reads the ACS's levels for every publisher |
| LOC-VIEW-1 | No loam view of located_in edges yet; needed to name the libraries in a place |
| OUT-REG-1 | stack_outlet_sources' registry entry names Maine's five listings |
| CON3-2 | Contract 3 section 2 needs D-207's wording |
| SCHEMA-1 | A metadata field's type is checked only by a real run; a test could validate output_metadata against seeds/schemas |
| RECEIPT-1 | Rerun maine_counties, maine_county_units and maine_governance_units when anything reads them through $loam. (8 receipts predate D-167) |
| SRC-3, USE-1, SPEC-1, LAYER-1, COUNT-1, TENURE-1, KIT-1, TRIBE-6, NOTE-3, LEDGER-1 to LEDGER-3 | as before; look each up in the ledger |
| Person 3 | D-118's tiers, ROLE-1, the draft notes, NOTE-3, D-173's review, P-8, TRIBE-7's wording, tiers for the outlet and located_in types, and the proposed tiers for session 4's types (library_outlet, water_boundaries, forest_boundaries, neighborhood_boundaries, roads, nighttime_lights, population_density; measured_composition has none) |

Closed in session 2: STAT-1 (STATSTRU 25 is survey nonrespondent, IMLS PLS FY 2024 Documentation, Appendix B). Closed in session 3: SCHEMA-2 (D-213 to D-216). Closed in session 4: STUB-1 (D-222, retired).

Also carried, look up in the ledger first: S2-1, GATE-2, GATE-3, MAP-8, MAP-9, TRIBE-4, SEN-1, LEGI-1, LEG-4, LIC-1, KEY-1, XCHK-1, COMP-1, REG-1, LOOP-1, ACQ-6, SCH-5, TAG-1, MEGIS-3, LURC-1, BAXTER-1, DISS-1, METH-1, LIN-2, VER-1, NOTE-2, TRIBE-5, PENOB-1, GJSON-1, RESOLVE-1, DEPS-1, SEAM-2, DAS-1, HIST-1.

## Working agreement, as it stands

- Design before code, forks one at a time with a lean, nothing chosen silently. Small choices: Claude takes the lean and says so. Kalli reads, runs and commits; Claude drafts.
- Go in the plan's order unless Kalli says otherwise.
- Drift is fixed when it is found, never deferred to a later fork (Kalli, session 2). When one truth is written in several places, it gets one home and the others point to it.
- Everything in seeds/ is shared by every plot: reusable, never tailored to one project, possibly international someday. Domain logic gets no top-level seeds/ folder of its own (Kalli, session 2).
- A type is declared before anything names it, and a declaration names a current type (D-220). The walks in tests/test_current_type_names.py hold every plot to this, so drift fails a test instead of hiding.
- Rule or choice: ask whether a reasonable person could decide it the other way. No: a rule, held by a test. Yes: a choice, declared in the method and recorded in the receipt.
- Before any threshold or external claim, Claude researches and cites what a source actually says, in the vintage the build uses, and says plainly where a source gives no number.
- When Kalli says a concept is unclear, Claude explains it from the ground up, with a picture where one helps, before asking anything of it.
- Changes come as a zip of repo-relative files (Kalli's preference), unzipped from the repo root with `unzip -o ~/Downloads/<n>.zip -d .`; small files and every ledger block come inline. Inline files are `cat > path << 'EOF'`, one file per paste, every `EOF` at the left edge. A file Claude has not seen whole is changed by a guarded helper in `_sprint06/` that writes nothing unless its anchor matches once; the helper folder is deleted after.
- Whole-file replacements; `git --no-pager diff --stat` is read before anything runs.
- Every commit block is guarded and names its files: a zsh array, `git add -- $files`, then `git diff --cached --quiet -- $files` prints STOP when nothing changed, and `git commit -- $files` keeps anything else out.
- Ledger blocks appended with cat >>, each starting with a newline. Grep every new ID first. No em dashes, no inline shell comments.
- Before changing a signature, search the keyword across every caller and test, then read each hit for meaning.
- Read real output as its reader would before committing a telling. A receipt is read after every real run.
- Usage: one step per chat; state.md is the only upload at the start; long output is filtered (`| tail -3`, `| grep`); Claude names exact files and asks for whole files rather than many line ranges.

## Traps

- /mnt/project in Claude's sandbox is a partial snapshot, refreshed 2026-11-13 before session 4's edits; some files in it are empty and others are missing. The repo is on Kalli's machine, and a file to be edited is read from her copy or changed by an anchored helper.
- Run everything from the repo root. An unzip from field-guide/docs once made second copies of soil/ and tests/ there, and pytest refused the duplicate test names.
- Run a preparation with `python -m canopy.cli sows <run.yml>`; `--dry-run` only validates. `sows` prints nothing until the run ends. Never `--resolve-only` casually (RESOLVE-1).
- Do not run maine_seats on real data before 2026-12-02.
- `authority` means only who assigns a place's code; a publisher is `published_by` everywhere, manifests included.
- `$indicators.<id>` resolves to the whole declaration and carries the sha256 of the whole file it lives in. Never add an indicator to an existing indicators file whose receipts exist: a new file (as carriers.yml) leaves every hash alone.
- The indicator registry globs every seeds/indicators/*.yml as indicator declarations, names flat and global across files (registry.py, line 199). Put nothing else in that folder.
- A run's `$choices.<name>` reaches a step as the raw value. A choice outside its method's options only warns (CHOICE-1), so a primitive that depends on one refuses a bad value itself.
- A step's outputs are `name: type`; the type is a current semantic type, never `<thing>_validated` or `_checked` (D-220). Validating or reprojecting keeps the input's type. The experiment schema's example now says so.
- Vocabulary.get_tier reads `tier`, not `resolution_tier` (TIERREAD-1): do not rely on it for a type's exposure tier.
- `imls_pls_fy2024_outlets` is a located_in layer label set in maine_libraries, not a manifest dataset; the library points' type is library_outlet.
- A method is read only through parsing.load_method_data (D-213). Options are a mapping keyed by option id (an empty value allowed), requires_primitives a list of layer/name, produces a list; a field the schema does not describe is refused. canopy/wonder still reads methods raw (SCHEMA-3). A method's name lives in the method, never the index (D-216).
- `git rm` stages a deletion; a later `git add` naming that path fails the whole add and stages nothing. Name an already-deleted path in `git commit -- ...` only.
- `| tail -3` prints nothing until pytest ends, about two minutes for the full suite; the terminal is not frozen.
- Claude's sandbox shell is dash: no brace expansion, so `mkdir a/{b,c}` makes one literal folder and once shipped it in a zip. Claude uses `bash -c` or one path per argument.
- loam's `edges` view is made from exactly one `place_edges` artifact (D-163); never write a second. Point edges are `located_in_edges` (D-207).
- loam's place_values attaches a value only when seeds/vintages/boundaries.yml holds a rule for its `published_by`; it reads the ACS's `levels` for every publisher (LOAM-2).
- The 2024 faces are a zip of county zips (plots/maine/.data/maine_faces_2024.zip); build_block_spine reads their .dbf only, build_located_in their geometry.
- The IMLS outlet file is Windows-1252: declared, never sniffed. A pandas read that falls back silently would have written a control character into two names.
- The FY 2024 outlet file holds no STATSTRU 03: permanent closures are listed outside it (its documentation's Appendix C). Older files kept such records.
- `grep -c` counts lines, and a GeoJSON file is one line: a 1 means at least one match. Read features with python, never by counting.
- A test loading a soil module by file path must register it in sys.modules before exec when the module defines a dataclass.
- The envelope schema checks metadata types (a point layer's total_area_m2 is 0.0, never null); fixture tests do not see this (SCHEMA-1).
- MEGIS Maine Town Points (METWP24PT) are town centroids, not offices: refused as a carrier layer.
- Freshness never judges primitive code (KIT-1), and is judged only when a run reaches a `$loam.` input. The read-only probe: build an Orchestrator on any Maine preparation, then `judge(read_envelope(p), orch.project_root, orch._declared_params)` for each file in plots/maine/.envelopes.
- `wonder --place` takes a key, AUTHORITY:CODE, never a name. A town range is one estimate per town; read the firm range before quoting a range's ends. A carrier has no range.
- A step's `outputs:` gives names, not paths. Receipts are `.envelopes/<step>_<o>.envelope.json`.
- The geography graph preparation declares `vintages` twice; change both together (D-162).
- Scope every grep: quote globs, and never grep `plots` without `--include="*.yml"`. `git diff` opens a pager; use `git --no-pager diff`. It is `git status -sb`, one dash.
- Keys live in Kalli's environment only (KEY-1). The repo is public. garden/reference/ and **/.data/ are ignored; commercial listings never leave them.
- The sandbox lacks pytest, pyarrow, shapely, geopandas, duckdb, jsonschema, pyogrio and R; it has pandas and yaml. A small stand-in for pytest.raises lets pure-pandas tests run there.

## People

Kalli: Maine data and geography, profile, explorer, review of everything; acting grove teammate. Ajitesh: publish route (Sprint 08); LAYER-1, GJSON-1 and D-157's required notes argument matter for his door. Infrastructure teammate: Sprints 07 and 10; DEPS-1, KIT-1 and OUT-REG-1 matter for the Docker build. Person 3: tier declarations, note wording, NOTE-3, D-173's review, P-8, TRIBE-7.

## Starting the next session

Upload this file only, with a first message like the one in the hand-off. Claude reads it, confirms, and asks for exactly what the next step needs. The next step, by Kalli's order, is CMAP-1's next fork: where carrier-hood lives, and how a carrier indicator reaches its points' type. Read first: seeds/indicators/carriers.yml, plots/maine/preparations/maine_libraries.yml, canopy/indicators/registry.py, and seeds/sources/census_tigerweb.yml (the model for the IMLS catalogue). Then bring the fork with its lean.

What session 4 found, to build on: carriers.yml already says `role: carrier`, so which indicators are carriers is answerable from the registry today, and carrier-hood is a relation between a thing and a barrier, not a property of the thing (a school is a carrier here and a governance site elsewhere), so the vocabulary does not flag it. But the indicator names a located_in layer label (`imls_pls_fy2024_outlets`), not a dataset or a type, so the step from indicator to points' type is not yet a lookup. Schools follow CMAP-1: Kalli opens the Maine DOE Schools & SAU page first, and INDFILE-1 is decided before the schools indicator is declared.
