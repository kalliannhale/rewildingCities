# State of the garden ~ rewildingCities

What is true now. Rewritten, never appended, at every hand-off (D-160). The
build ledger (field-guide/docs/build_ledger.md) is the history; this page is
the present. When the two disagree, the ledger and the code win, and this page
is fixed.

**Updated:** 2026-11-15, at the hand-off closing Sprint 06's eighth build session.

## Where the build stands

- Branch main. Confirm with `git log --oneline -15` and `git status -sb`, and that both are pushed. Session 8's commits: 14f3100 (boundary_vintage, D-231), f6eecef (health centers, D-232), the tribal-count commit (D-233), the session 8 ledger commit, and this hand-off.
- Tests: `python -m pytest -q -rs | tail -3`. 957 passed, no skips, at the D-233 commit (new in session 8: tests/test_health_center_points.py, 23; tests/test_health_center_preparation.py, 8; tests/test_tribal_counts.py, 3; new cases in test_count_located, test_loam_values and test_place_carrier). The 2 warnings are Starlette and FastAPI test-client deprecations (httpx, anyio) in tests/test_unit_authority.py, not ours. The R oracle tests run only where Rscript and rewildr are installed; `-rs` names a skip, since a skip proves nothing.
- Plan of record: the Master Plan, https://claude.ai/artifact/KpQRRSTyXr27emXnJFfL6z. Its decision table stops at D-81 and its Sprint 06 tab predates the design pass (D-197 to D-200); check its claims against this page and the code. Its tab is updated at Sprint 06's close.
- Next decision ID: D-234. Before minting any ID, grep the ledger for it (LEDGER-3). Item IDs too.
- **Sprint 06 is open**, across several sessions, in the order below. Progress: field-guide/docs/progress/information/sprint-06.md.
- On or after 2026-12-02, when the 133rd's rosters are acquired: flip available: true, TRIBE-4, SEN-1, then run maine_seats.
- HRSA's sites copy lives at plots/maine/.data/hrsa_health_center_sites_20261114.csv (ignored, sha256 08b01537...da436). A fresh copy is a new manifest entry named for its day, never an overwrite.

## Sprint 06 ~ the place profile and the standard

**Goal:** every Maine place has a six-part profile, its carriers are on the map, and every barrier is judged against a stated, absolute standard.

**Decided in the design pass:** D-197 (build_profile wraps read_place), D-198 (margin-aware verdicts, derive_margins), D-199 (universal, trigger, none thresholds), D-200 (each barrier a family of registered indicators with a status).

**Decided in session 1:** D-201 to D-209. **In session 2:** D-210 to D-212. **In session 3:** D-213 to D-217. **In session 4:** D-218 to D-222. **In session 5:** D-223 to D-226. **In session 6:** D-227 to D-229. **In session 7:** D-230. **In session 8:** D-231 to D-233, below.

**Order of work, and where each step stands:**

```
 1  P-9: read the outlet files                done      answered
 2  located_in edges + end checks             done      D-207
 3  carriers, counted per 1,000               3 of 5    libraries, schools, health centers done
      libraries (IMLS PLS FY 2024)            done      D-208 to D-212: placed, counted, closures declared
      first, by Kalli's order (session 2):
        SCHEMA-2: the method schema           done      D-213 to D-217
        CMAP-1: the carrier map as a view     done      D-218, D-219, D-223 to D-226
        the drift CMAP-1's walk found         done      D-220 to D-222
      the drift session 6 found               done      D-227 to D-229; INDFILE-1 closed
      schools (NCES EDGE 2024-25)             done      D-230: 598 placed, counted
      the year rule SURVEY-1 hid              done      D-231: boundary_vintage
      health centers (HRSA, 2026-11-14 copy)  done      D-232: 168 placed, 24 listed
      tribal areas counted beside a note      done      D-233; TRIBE-8, LOAM-2 closed
      town offices                            blocked   no point source (see Traps); needs a geocoder
      outlets                                 not yet   waits on WHERE-1 and a geocoder
 4  derive_margins (D-198)                    not yet
 5  language: ACS, safe harbor, section 203   not yet
 6  literacy: PIAAC county estimates (P-7)    not yet
 7  digital access counts + FCC map (P-6)     not yet
 8  outlets reconciled                        partial   stacked, grouped, disagreements listed;
                                                        ownership and concentration to go
 9  profile.py + the standard seed            started   place.py reads exact counts apart and
                                                        carries each value's role (D-223)
10  pairing table (P-2)                       not yet
11  profiles for every place                  not yet
```

**Schools, done (session 7).** Placed from NCES EDGE Public School Locations 2024-25 (D-230): one national release zip (sha256 9dc51ecd...cffb288, in the manifest's known_issues), its headerless text table read through seeds/crosswalks/schools/nces_edge_geocode.yml. 598 schools placed, none listed; the three Wabanaki community schools (OPSTFIPS 59, the Bureau of Indian Education) placed and flagged, one located_in edge per drawer each, Indian Island School in 2301957936 (the Penobscot County piece) and 2760R. Maine counts 598, 0.439 per 1,000 of 1,362,359 persons; Penobscot Indian Island Reservation counts 1 among 370, shown beside its note since D-233. Maine DOE's 13 exports carry no ID and no school's coordinates, so they place nothing; their name lists may serve as a check later (seeds/sources/maine_doe_schools.yml, an export source: only our copy is evidence). MEGIS's school layer carries no state or NCES school ID either. The EDGE characteristics layer (status, grade span) could not be downloaded; the CCD directory, joined on NCESSCH, is in reserve if the DOE check needs the state school ID (its public-use terms limit use to statistical purposes).

**Health centers, done (session 8).** Placed from HRSA's Health Center Service Delivery and Look-Alike Sites, the copy downloaded 2026-11-14 (D-232): a daily snapshot with no release, so the copy is the evidence, declared by its day and sha256, and every row's Data Warehouse Record Create Date is held to the day. Read through seeds/crosswalks/health_centers/hrsa_health_center_sites.yml (header names, codes; an undeclared code refuses). Maine: 192 rows, 168 placed (32 seasonal, 8 look-alikes, every setting), 24 listed (10 administrative, 9 mobile vans, 5 with no point). Maine counts 168, 0.123 per 1,000. No Wabanaki nation's clinic appears; HRSA's program does not see them.

**Tribal areas, counted beside a note (session 8, D-233).** All three carriers count the 8 Census tribal areas, each row carrying context_note: carrier_unseen_on_nations_land (libraries, health centers: all zeros) or carrier_seen_on_nations_land (schools: Indian Township, Pleasant Point and Penobscot each count 1). The notes' words are Kalli's DRAFT in seeds/notes/notes.yml, waiting on the nations' terms (P-8). Four trust lands hold 4 to 202 persons, so their rates are unstable; the count and persons travel with each rate.

**The barriers, their indicators, and where the data is** (as decided in the design pass; P-9 has changed three rows' status):

| Barrier | Indicators | Source | Grain | Status |
| --- | --- | --- | --- | --- |
| Not in the right language | limited-English persons by language; safe-harbor languages; VRA section 203 coverage | ACS language-by-ability tables; DOJ LEP guidance (2002); Census section 203 file (2021) | town | acquirable |
| Requires digital access | households with no internet subscription; no service at the FCC benchmark | ACS; FCC National Broadband Map | town | ACS acquired as a rate; counts and FCC acquirable |
| At the wrong literacy level | adults at or below Level 1 | NCES PIAAC Skills Map (pooled 2012/14/17) | county, borrowed on towns | acquirable |
| Lacking cultural cues | languages spoken against languages carriers publish in | ACS and our own observation of outlets | town | needs our observation (OBS-1): no listing carries language |
| Behind a paywall | share of local outlets free to read | our own observation (OBS-1), P-3 | town | needs our observation: no listing carries paywall status |
| Outdated | outlet publishing frequency; observed last post | Cision, the ecosystem file, Easton (frequency); Cision's Still Operates? (last post) | town | acquirable from the stack |
| Not where people look | carriers per 1,000 by type | IMLS, NCES EDGE, HRSA (done); town offices, outlets | every level | libraries, schools, health centers counted (D-209, D-230, D-232), tribal areas beside a note (D-233); on the map as loam's carriers view (D-225), adjectives and notes not yet carried (CARRY-1) |
| Not from a trusted source | relational hubs, aggregate-only | consent-governed | as consented | needs_consent (Sprint 16) |

**Still open in Contract 4:** P-1 (each threshold, row by row), P-2 (pairing table), P-3 (free outlet), P-5 (a universal side for language; lean yes), P-6 (FCC benchmark), P-7 (PIAAC 2023?), P-8 (section 203 on Wabanaki places; on the nations' terms). P-9 is closed.

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

## Decided in session 5

| ID | One line |
| --- | --- |
| D-223 | Carrier-hood lives in the indicator registry, each indicator's role; IndicatorRegistry.with_role() finds carriers. role carrier and derivation located_count are independent: the map draws carriers that are located_counts |
| D-224 | A located_count names the type it counts (derivation.counts: library_outlet), never a layer label, which a seed may not hold; the label stays in the preparation and the receipt (counted_layer). The orchestrator checks before a run that the counted points are that type, read once, from edges made in the run |
| D-225 | loam's located_in view unions every located_in_edges receipt (LOC-VIEW-1); its carriers view gives every placed point of every located_count carrier, found through the edges receipt's own provenance record. place.py reads an exact count apart by derivation and labels every value by role, reading indicators through the registry |
| D-226 | IMLS's codes (outlet types, structure statuses) are one shared crosswalk, seeds/crosswalks/libraries/imls_pls_outlets.yml, passed whole as `reading`; a release's outlet member and encoding are declared in its manifest entry and held to the run as source_facts; seeds/sources/imls_pls.yml is reference only, pointing to each fact's home |

## Decided in session 6

| ID | One line |
| --- | --- |
| D-227 | An indicator's declaration_sha256 is taken over its own mapping, canonical, without its rationale; computed when parsed, never by reopening the file. A sibling, a comment or a prose edit never stales a receipt. Weights and reliability unchanged (one declaration per file) |
| D-228 | One experiment per question: county standings answers basic_needs_and_opportunity (rent burden, vehicle access); broadband's county standing lives only in maine_broadband_access_subscription__cii_indicator_values_91b5c0, same method and choices |
| D-229 | The no-curiosity warning names only the gap; advice to become a preparation comes only from the error for a run with a preparation method (a rule, tested) |

## Decided in session 7

| ID | One line |
| --- | --- |
| D-230 | Schools from NCES EDGE 2024-25, keyed NCESSCH, columns and codes from one crosswalk; a school is in the state where NCES's point stands (STFIP), never its operator's (a rule, tested): the three BIE-operated Wabanaki community schools are placed, flagged and counted in every drawer, once each; DOE and MEGIS place nothing. Kalli's choice A, with her guard that Indian Island counts once, as the county subdivision it is |

## Decided in session 8

| ID | One line |
| --- | --- |
| D-231 | A count says which boundaries it sits on in each row's boundary_vintage, the one vintage of the edges reaching that level; loam reads it for publishers whose rule says boundary_vintage (rewildingcities), so `time` says only when. Closes SURVEY-1 |
| D-232 | Health centers from HRSA's sites file, a daily snapshot declared by day and sha256, rows held to the day; keyed BPHC Assigned Number. Rules: administrative sites, mobile units, sites with no point, withheld addresses, sites not open or elsewhere are listed. Look-alikes, seasonal sites (as an adjective) and every setting are placed (Kalli's choices); who a site serves stays SERVES-1's |
| D-233 | A Census tribal area is counted, never refused, beside the note its step names (tribal_note), carried on every tribal row (context_note); the words are Kalli's DRAFT, on the nations' terms. loam refuses only the ACS on tribal areas (D-171) and judges each publisher on its own levels (LOAM-2). A tribal code and its persons are AIANNH plus component. A level no edge reaches takes its places' vintage |

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
| An exact count is read apart by its method, never ranged; every value carries its role | place.py; tests/test_place_carrier.py (D-209, D-223, D-225) |
| Carriers are found by role, never by a type flag | IndicatorRegistry.with_role; tests/test_located_count_indicator.py (D-223) |
| A located_count's counted points are its declared type, read once, from edges made in the run | Orchestrator._validate_located_counts; tests/test_located_count_validation.py (D-224) |
| No indicator seed names a release, a plot, or a layer label | registry (a layer key refused); tests/test_located_count_indicator.py (D-224) |
| A count reads one layer's edges and names it | count_located; tests/test_count_located.py (D-224) |
| The API's description and the declaration show one derivation | Derivation.as_dict; tests/test_located_count_indicator.py |
| located_in and carriers are views, never files; a layer in two receipts, or points not found through provenance, are refused by name | canopy/loam/graph.py; tests/test_loam_carriers.py (D-225) |
| IMLS's codes are read from one shared crosswalk, never a plot | prepare_library_points.read_crosswalk; tests/test_library_points.py, tests/test_library_preparation.py (D-226) |
| A release's outlet member and encoding are declared once and the run is held to them | source_facts, Orchestrator._validate_source_facts; tests/test_library_preparation.py (D-192, D-226) |
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
| An indicator's hash covers its own mapping without its rationale: siblings, comments, key order and prose never move it; source, weight_by and scale do | IndicatorRegistry, spec_sha256; tests/test_declaration_hash.py (D-227) |
| A run with no curiosity is told it names none (D-64), and never told to become a preparation it could not be | Orchestrator._validate_kind; tests/test_preparations.py (D-229) |
| A school is placed where NCES's point stands (STFIP), never by its operator; one operated elsewhere is flagged | prepare_school_points; tests/test_school_points.py (D-230) |
| NCES's headerless table is read by declared columns with a quote-aware reader; another field count, a header row or a duplicate NCESSCH is refused; M and N are never values | prepare_school_points, seeds/crosswalks/schools/nces_edge_geocode.yml; tests/test_school_points.py (D-230) |
| A school release's member and encoding are declared once and the run is held to them | source_facts, Orchestrator._validate_source_facts; tests/test_school_preparation.py (D-192, D-230) |
| A count's boundaries travel in boundary_vintage from its edges, never its time; a level's two vintages refuse | count_located, loam place_values; tests/test_count_located.py, tests/test_loam_values.py (D-231) |
| Each publisher is judged on its own levels; only the ACS is refused on a tribal area | loam place_values; tests/test_loam_values.py (D-233, LOAM-2) |
| A tribal area is counted only beside a note that exists; its code and persons are AIANNH plus component | count_located; tests/test_count_located.py, tests/test_tribal_counts.py (D-233) |
| A count's note is said with its number | place.py; tests/test_place_carrier.py (D-233) |
| HRSA's copy is the one declared: its rows' record dates are its day | prepare_health_center_points; tests/test_health_center_points.py (D-232) |
| Administrative, mobile, pointless, withheld, closed and out-of-state sites are listed, never placed; an undeclared HRSA code refuses | prepare_health_center_points; tests/test_health_center_points.py (D-232) |

## Open items

Sorted for delivery (Kalli asked, session 8). **Delivery (Kalli, session 8):** the Maine product by 2026-12-01 to 12-11: every place's profile, all five carriers on the map with their toggles and notes (town offices and outlets included, so a geocoder is in scope), the barriers judged against the standard, the publish door, the Docker build. Claude's honest note at the hand-off: steps 4 to 11 and Sprints 07, 08 and 10 remain; at session 8's pace that does not all fit, so a cut may be needed later, and is a design choice when it comes, never a failure.

### Blocks delivery

| ID | One line |
| --- | --- |
| GEO-1 | No geocoder exists. Next session's design (see Starting the next session) |
| TOWN-OFF-1 | Town offices have no address list: MEGIS Town Points are centroids, refused. A geocoder places addresses; it cannot invent the list |
| WHERE-1 | Which place meaning counts as where an outlet is (office, named town, coverage): decided before any outlet is geocoded |
| OWN-1, SRC-4 | Ownership concentration redesigned over located_in; every outlet source's terms read before outlets are published |
| P-1, P-2 | The standard itself: each threshold, row by row, and the pairing table |
| P-5, P-6, P-7 | A universal side for language (lean yes); the FCC benchmark; PIAAC 2023 or the pooled map |
| CARRY-1 | loam's carriers view carries only feature_id, name and coordinates (graph.py, _points_sql): a point's adjectives (seasonal, look_alike, setting, flags) and a count's context_note never reach the map. One generic pass-through, for the toggles and the notes |
| Tiers | Kalli's tier declarations: public_school, school_geocode_release, health_center_site, health_center_sites_snapshot have none and fail closed, as do session 4's types and the outlet and located_in types; with NOTE-3, D-173's review and TIERREAD-1 (get_tier reads `tier`, domain files declare resolution_tier) |
| FSCS-1 | A published library count's label: outlets of systems the survey does not count as public libraries |
| SCALE-1 | place.py writes "per 1,000" while the scale lives in the declaration |
| LAYER-1, GJSON-1, D-157 | The publish door's items |
| DEPS-1, OUT-REG-1 | The Docker build: locust not installed; stack_outlet_sources' registry entry names Maine's listings |
| RECEIPT-1 | Rerun maine_counties, maine_county_units, maine_governance_units if profiles read them through $loam. |
| TRIBE-7 | The notes' wording is drafted (D-233); it is shown as a draft until the nations' terms settle it, never withheld for want of them |

### After delivery

| ID | One line |
| --- | --- |
| JOIN-1 | loam's join grammar knows a key's name, never its issuer; HRSA rows carry three issuers (BPHC, the grantee number, CMS's NPI). Nothing reads joinable() for carriers |
| KIT-2 | A shared points kit (member and encoding, state field, key, placed or listed, an issuer per key) was weighed and deferred: little gain before delivery, a retrofit's cost now |
| PLOT-2 | `city:` in preparations, manifests and sows' header ("City: Maine") should say plot: a schema key across the experiment and manifest schemas, every plot file and their readers |
| HRSA-1 | HRSA's metadata workbook is not read; the geocode's datum is unknown. HPSA, MUA/P, Health Sites and AHRF are catalogued in seeds/sources/hrsa.yml, unused; whether Health Sites sees the nations' clinics is unread |
| TRIBE-9 | The Census names 0115T "Aroostook Band of Micmac Trust Land"; as far as Claude knows the nation now calls itself the Mi'kmaq Nation. Verify, and decide on the nations' terms how a Census name and a nation's own name are shown |
| ACQ-7 | A url release declares its expected hash in source, and a fetch that does not match is refused; receipts already hash every input (md5, full_file), so a change... The rest of the line was lost in a broken paste; restate it from where it was defined |
| CHAIN-1, STAND-1, SCHEMA-1, SCHEMA-3, CHOICE-1, INTERP-1, QUADRAT-1 | As in the ledger |
| LIB-2, SERVES-1, OBS-1, P-3 | A second library authority; whom a carrier serves; our own observation of outlets; the free-outlet question |
| CON3-2, KIT-1 | Contract 3's wording; freshness never judges primitive code |
| P-8 | Section 203 on Wabanaki places, and what is shown on them: the nations' to decide, under CARE and OCAP. Never a deadline |

### Not yet sorted (look each up in the ledger)

S2-1, GATE-2, GATE-3, MAP-8, MAP-9, TRIBE-4, SEN-1, LEGI-1, LEG-4, LIC-1, KEY-1, XCHK-1, COMP-1, REG-1, LOOP-1, ACQ-6, SCH-5, TAG-1, MEGIS-3, LURC-1, BAXTER-1, DISS-1, METH-1, LIN-2, VER-1, NOTE-2, TRIBE-5, PENOB-1, RESOLVE-1, SEAM-2, DAS-1, HIST-1, SRC-3, USE-1, SPEC-1, COUNT-1, TENURE-1, TRIBE-6, LEDGER-1 to LEDGER-3, ROLE-1, the draft notes. TRIBE-4 and SEN-1 are dated (2026-12-02) and block maine_seats.

Closed in session 8: SURVEY-1 (D-231), LOAM-2 and TRIBE-8 (D-233). Opened: CARRY-1, KIT-2, PLOT-2, HRSA-1, TRIBE-9; ACQ-7 carried in from an uncommitted ledger line.

## Working agreement, as it stands

- Design before code, forks one at a time with a lean, nothing chosen silently. Small choices: Claude takes the lean and says so.
- Until the product is delivered (Kalli, session 7): Claude drafts all code, primitives included, as zips, once Kalli says go. Kalli drives the terminal herself to learn it: unzip, helpers, diffs, tests, dry runs, runs, receipt reads, guarded commits, push, each command explained in plain words. After delivery she returns to writing code.
- Diagrams carry description and fun metaphors; responses stay readable, short sections (Kalli, session 7).
- A fork lists only options that could win. An option already refused, or one nobody would choose, is not listed (Kalli, session 5).
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
- When Claude needs several repo files, it gives a `zip` command so Kalli uploads one zip (`-j` only when no two files share a name).
- A data check is a "read", never a "probe" (Kalli, session 8).

## Traps

- /mnt/project in Claude's sandbox is a partial snapshot, refreshed 2026-11-13 before session 4's edits; some files in it are empty and others are missing. The repo is on Kalli's machine, and a file to be edited is read from her copy or changed by an anchored helper.
- Run everything from the repo root. An unzip from field-guide/docs once made second copies of soil/ and tests/ there, and pytest refused the duplicate test names.
- Run a preparation with `python -m canopy.cli sows <run.yml>`; `--dry-run` only validates. `sows` prints nothing until the run ends. Never `--resolve-only` casually (RESOLVE-1).
- Do not run maine_seats on real data before 2026-12-02.
- `authority` means only who assigns a place's code; a publisher is `published_by` everywhere, manifests included.
- `$indicators.<id>` resolves to the declaration as a primitive receives it (as_declaration), with declaration_sha256 taken over the indicator's own mapping without its rationale (D-227). Adding or editing a sibling, a comment or a rationale moves no receipt; editing source, weight_by, replicates or the derivation does, and so does moving the indicator to another file (declared_in). as_declaration omits source, weight_by, replicates and rationale: the hash is what lets freshness see the first three.
- A preparation uses soil/ primitives only and a preparation method; a run with a roots/ step or an analysis method is an experiment and names its curiosity (D-98, D-228). `curiosity: ref: ""` is a warning, never a pass.
- Two functions are named read_envelope: canopy.envelope.read_envelope returns an Envelope object (what freshness's judge reads); canopy/loam/envelope_reader.read_envelope returns a dict and needs a vocabulary.
- Origin can move between sessions (session 6: four commits by other authors). Before pushing, `git fetch` and read `git --no-pager log --format='%h %an %ad %s' --date=short main..origin/main` and `git --no-pager diff --stat main...origin/main`; rebase only after reading them. Never `git add .`: in session 6 it committed a stray environment.yml edit under another commit's message.
- The indicator registry globs every seeds/indicators/*.yml as indicator declarations, names flat and global across files (registry.py, line 199). Put nothing else in that folder.
- A run's `$choices.<name>` reaches a step as the raw value. A choice outside its method's options only warns (CHOICE-1), so a primitive that depends on one refuses a bad value itself.
- A step's outputs are `name: type`; the type is a current semantic type, never `<thing>_validated` or `_checked` (D-220). Validating or reprojecting keeps the input's type. The experiment schema's example now says so.
- Vocabulary.get_tier reads `tier`, not `resolution_tier` (TIERREAD-1): do not rely on it for a type's exposure tier.
- `imls_pls_fy2024_outlets` is a located_in layer label set in maine_libraries, not a manifest dataset or a type. The indicator names `counts: library_outlet` (D-224); a `layer` key in an indicator seed is refused by name. The label reaches the receipt as count_located's counted_layer.
- IMLS's outlet types and structure statuses live in seeds/crosswalks/libraries/imls_pls_outlets.yml (D-226). A plot never declares them; a release's member and encoding go in its manifest entry under `source:` (outlet_member, outlet_encoding), and the run's copy must agree (D-192).
- seeds/sources/ is read by no code, by design (D-226): a catalogue there is reference only, and a test holds that imls_pls.yml's pointers exist.
- The carriers view needs each carrier's points file to carry its receipt's id_field and a `name` property, and finds the points through the edges receipt's own provenance record (the newest without lineage_branch). A new carrier preparation writes both (D-225).
- place.py reads indicators through IndicatorRegistry: a root with no seeds/indicators refuses, where the old raw-YAML walk returned nothing in silence.
- `git grep` and `git diff` open a pager that can cut output at "...skipping...": use `git --no-pager grep` and `git --no-pager diff`.
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
- NCES EDGE's text table has no header row; its 23 columns come from the crosswalk, and a field holding a pipe is quoted: read it with a quote-aware reader, never `split("|")`.
- Three state fields in EDGE mean three things: STATE the reported address, STFIP where NCES's point stands, OPSTFIPS who administers the school (59 BIE, 63 DoDEA). Place by STFIP (D-230).
- A located_in edge's `to_authority` is not its level: us_census_geoid holds state (2 digits), county (5) and town (10). A per-drawer check groups by authority and code length; by authority alone it reads 3 for one card per drawer.
- A dashboard export (Maine DOE) is not a release: a fresh export is a new source, and only our copy is evidence. Its file name's number is the export time in milliseconds since 1970, UTC.
- `loam`'s `joinable()` relates holdings by key name, so every carrier's feature_id looks joinable to every other (JOIN-1).
- A count's boundaries are boundary_vintage, never its time (D-231): write `time` as what the source describes (FY 2024, SY 2024-25, a snapshot's day).
- HRSA's three state fields: Site State Abbreviation (the site), State FIPS Code, Health Center Organization State (the grantee's office, never where a site stands). Rows HRSA holds with no site state read XX, with no point.
- The spine stores a tribal area as AIANNH (four digits) plus aiannh_comptyp (R, T); a place's code is the two joined (2760R). Group by the bare code and a reservation merges with its trust land.
- A count_located step at the aiannh level must name tribal_note; tests/test_tribal_counts.py walks every plot.
- `Data Warehouse Record Create Date` is the day of HRSA's copy, not of any site.
- The loam carriers view does not carry point properties beyond id, name and coordinates (CARRY-1).

## People

Kalli delivers the whole product: every sprint, the publish route (Sprint 08) and the infrastructure (Sprints 07 and 10) included. The people once named here work on other things (Kalli, session 5). bash-win and Jessica Pham are helpers Kalli recruited, who join her weekly lab sessions; their commits on 2026-11-14 brought staging Terraform, API load tests and plot locks, the Docker image and NYC fetch dates. DEPS-1 likely came with their locust tests (7afefd1); whether DEPS-1, KIT-1 or OUT-REG-1 move to them is Kalli's to say, and until she does they stay hers. Items that were theirs are hers now: LAYER-1, GJSON-1 and D-157's required notes argument for the publish door; DEPS-1, KIT-1 and OUT-REG-1 for the Docker build; the tier declarations, note wording, NOTE-3 and D-173's review. P-8 and TRIBE-7's wording wait on the Wabanaki nations' terms (open items).

## Starting the next session

Upload this file only, with a first message like the one in the hand-off. Claude reads it, confirms, and asks for exactly what the next step needs.

**Next: GEO-1, the geocoder (Kalli's choice, session 8), so town offices and outlets can be placed.** What exists today, from Claude's read of its snapshot and the repo's file list, to be confirmed on Kalli's machine first with:

```
git --no-pager grep -n -i -E "geocod|geocoder|address" -- '*.py' '*.yml' | grep -v "^tests/" | cut -c1-150 | head -60
```

- No geocoder. canopy/providers holds arcgis, base, census_acs, earthengine, maine_legislature, s3, socrata, stac and youtube; none turns an address into a point. Providers live in canopy/providers as Provider subclasses (a lesson), and fetching from a service is a provider's job.
- soil/validate/geocode_to_unit.py is not a geocoder: it matches place-name strings (with fuzzy matching) to governance units, a silent WHERE-1 choice against D-203 and D-204 (OWN-1). It places no point and should not be the base.
- build_located_in already places any point layer with coordinates and a feature_id, through the 2024 faces and the 2020 spine. So a geocoder's job ends at a point layer with a receipt; everything after it exists.
- prepare_library_points already reads a source's own geocode quality (IMLS's GEOMTYPE, flagged manual_geocode), the pattern for carrying how a point was made.

Questions the next session answers, one at a time with a lean:

1. Which geocoder: GEO-1's lean is the Census Geocoder first (free, no key, batch files, returns match type and the 2020 block), with ArcGIS or Maine NG911 address points as second authorities later. Claude researches and cites the Census Geocoder's current documentation (batch size, benchmark and vintage, what each match field means) before anything is designed, since the batch call runs only on Kalli's machine (the sandbox has no network).
2. What a geocode is in the codebase: a provider that fetches, a soil primitive that turns the response into points (and lists the unmatched with their reasons, as every carrier does), and a type for the response, declared first.
3. How match quality travels: exact, non-exact and tie as declared codes; whether a non-exact match is placed, flagged or listed is a choice for the method.
4. The address lists themselves: outlets have office addresses (D-203's office_*), but WHERE-1 decides whether an office address is where an outlet is; town offices need a list from a source with an ID (TOWN-OFF-1: Maine Municipal Association? the Secretary of State?). A geocoder unblocks neither alone.

What session 8 found, to build on: a rule written for one source travels to the next unless it names its reason without naming the source (the tribal refusal said "reservation libraries" inside every carrier's count); a column with two meanings hides behind a coincidence until a third source breaks it (`time` meant both when and which boundaries); a daily snapshot has no release, but it states its own day, and the copy can be held to its own words; and refusing a place hides it, where a number with its note shows it in its context (Kalli).
