# Sprint 06 ~ the place profile and the standard: progress report

**Open.** Domain: information. Contract: 4, draft 0.3. Tests: 643 passed at session 1's hand-off. Decisions so far: D-197 to D-209.

## Session 1: P-9, located_in, the outlet stack, and the first carrier

### SRC-2's check

Read-only probe over plots/maine/.envelopes: 28 receipts, 20 fresh, 8 cannot_tell, none stale. NAME-4 changed nothing that could be checked. The 8 are every receipt of maine_counties, maine_county_units and maine_governance_units, whose steps were recorded before D-167 and name no run or step. Left as they are; rerun those three when anything reads them through `$loam.` (RECEIPT-1).

### P-9: what the outlet files carry

| File | Language of publication | Publishing frequency | Paywall status |
| --- | --- | --- | --- |
| Cision (353) | a column, English on every row; uninformative | yes, declared | no |
| Cision raw export (412) | the same column | yes, declared | no |
| Maine Media Ecosystem (82) | no | yes for print only, in Print, which holds a station's format for radio | no |
| Jo Easton (~50) | no | free text in Format, mixed with medium | no |
| Local News Catalyst (30) | no | no | no |
| Aggregated signals | not an outlet file | not an outlet file | not an outlet file |

Frequency is carried by three sources in three shapes. Language of publication and paywall status are carried by none. Amjambo Africa, monthly, free, and published in seven languages, is in Easton's list and the ecosystem file and absent from Cision, the one file with a language column.

### Built

| Step | Commit | What |
| --- | --- | --- |
| 8 | 6fc983e, 887e301, ad5bfad, 2770bdd, 9997271 | the outlet stack: every listing read as declared (D-201), grouped by exact keys with no row-order matches (D-202), place fields by meaning (D-203), counties from the graph (D-204), as pr_io primitives |
| 8 | 377a7dd, 18619db | `$crosswalks.<name>` (D-206); the maine_outlets preparation over five manifest listings in garden/reference/ (D-205); three receipts, all fresh |
| 2 | f1a9d6c, d8227b9 | located_in as its own edges, towns from the 2024 face, districts from the 2020 block (D-207) |
| 3 | daabdf8 | maine_libraries: 262 fixed IMLS outlets placed, none unplaced, 1,572 edges; 261 of 262 agree with IMLS's own block, and the one that does not lands in the same town and districts; bookmobiles listed, never placed (D-208) |
| 3 | cc31c52 | carriers counted as registered indicators: located_count, carriers.yml, a boundary rule for our counts, count_located (D-209) |
| 9 | the carrier-reading commit | place.py reads a carrier apart: the count first, its persons, who counted it, no range |

### Found

- Cision's Outlet County reads Cook (Illinois) on 235 of 353 rows, across every outlet type; its address is the publisher's office (the Advertiser Democrat of Norway sits in South Portland).
- The two Cision files are separate pulls: 297 names in both, 115 only in the raw export, 56 only in the 353.
- Cision's Still Operates? is a hand-added observation (323 yes, 21 ceased, 9 a last-post date), stronger evidence for "outdated" than any declared frequency.
- The IMLS outlet file is Windows-1252: its one byte in 0x80 to 0x9F, 0x96, is a dash between words in two branch names (Virginia, Washington). Declared Latin-1, the step refused the file; a silent fallback would have read it wrong.
- No Maine library in the PLS stands in a Census tribal area: the survey has long not collected systematically from reservation libraries (TRIBE-7).
- MEGIS Town Points are town centroids, so no town office layer exists in the plan's named source (TOWN-OFF-1). MEGIS does publish its own Libraries layer, 390 points against IMLS's 262 (LIB-2).
- Loam's statistical-area rule, the ACS's, was applied to every publisher's values; it now judges ACS values only (D-209).
- House District 42, read as an official would: the first carrier telling hid the count, ranged the towns and called our count the publisher's estimate. place.py now reads carriers apart.

### Carried forward

GEO-1 (a geocoder, lean the Census Geocoder first), INDFILE-1, WHERE-1, OBS-1, SRC-4, TOWN-OFF-1, LIB-2, SERVES-1, TRIBE-7, SCALE-1, SURVEY-1, LOAM-2, LOC-VIEW-1, OUT-REG-1, CON3-2, SCHEMA-1, STAT-1, RECEIPT-1. Each is in state.md's open items and the ledger.

### Lessons

- A probe that guesses a field's name misses the field: the first regex caught "Subjects" for "sub" and missed Biz Model, Print and Digital. Read the values.
- A receipt is read after every real run. Two problems this session (the Cook county, the hidden carrier count) passed every test and showed only in real output.
- An indicator file's hash lands in every receipt that read from it, so a new kind of indicator goes in a new file.

## Session 3: SCHEMA-2, the method schema

Tests: 710 passed, no skips (57 new). Decisions: D-213 to D-217. Commit: df74b0d.

### Found

- 14 methods (10 information, 3 thermal, 1 perception) in three shapes; parse_method read only id, name, kind and each choice's options and description, so the schema described a shape nothing held.
- A method that failed to parse became a skipped warning, and _load_method_data returned {}, so the resolution engine saw a method needing nothing.
- hot_cold_spot_analysis gave three options a second name in an id field, and the NYC heat-island run chose by it (raster, not classified_raster).
- The index had drifted: land_cover_cooling_differential unrouted, the perception method under thermal, a name differing, a missing comma making two answers one string.
- D-214's test found roots/count_by_unit unregistered: the pre-graph twin of count_located, keyed by geocode_to_unit's place-name matching (OWN-1).
- The Maine ownership_concentration experiment is a thermal template naming roots/analysis (STUB-1).

### Built

| Commit | What |
| --- | --- |
| df74b0d | method.schema.yml v2.0 as the one home of a method's shape (D-213); load_method_data, through which every method is read and refused; invalid methods an error in validate(); requires_primitives as layer references (D-214); produces as a list (D-215); the index as a router only (D-216); count_by_unit deleted (D-217); tests/test_method_schema.py |

### Carried forward

CMAP-1 (next), CHOICE-1 (sharper now), SCHEMA-3, INTERP-1, OWN-1, STUB-1, and every item session 2 carried. Each is in state.md's open items and the ledger.

### Lessons

- A validator that passes everything proves nothing: the new schema was run against the old files first, and refused every retired shape.
- A test that resolves every declared reference finds drift no run reaches: within minutes it found a primitive nobody could run.
- Where options are compared with each other, the comparison is the meaning; it stays in the choice's description, once, and an option may add nothing.

## Session 5: CMAP-1, closed

Tests: 856 passed, no skips (27 new). Decisions: D-223 to D-226. Commits: 9b7716a, the D-223/D-224 ledger commit, 2f389f4, 42dc694.

### Built

| Commit | What |
| --- | --- |
| 9b7716a | carriers found by role, IndicatorRegistry.with_role (D-223); a located_count names the type it counts, `counts: library_outlet`, and a layer label in a seed is refused; count_located reads one layer and names it in its receipt; the orchestrator checks, before a run, that the counted points are that type, read once, from edges the run makes (D-224); describe and the declaration share Derivation.as_dict |
| 2f389f4 | loam's located_in view (LOC-VIEW-1) and carriers view, found through each edges receipt's own provenance record; place.py reads an exact count apart by derivation, carries each value's role, and reads indicators through the registry (D-225) |
| 42dc694 | IMLS's outlet types and structure statuses as one shared crosswalk; the release's outlet member and encoding declared in the manifest and held to the run as source_facts; prepare_library_points 1.2.0; seeds/sources/imls_pls.yml as reference (D-226) |

### Found

- The layer label `imls_pls_fy2024_outlets` held three facts in one string: what is counted, whose points, and which release. Only the first belongs in a shared seed; the year would have changed carriers.yml's hash every fiscal year.
- The label did real work: count_located refused edges from any other layer. The guard was kept, narrowed to one layer, and the type check moved to the orchestrator.
- No code reads seeds/sources/. Session 2 wanted catalogues so the map could be a query over them; the map became a query over the registry and loam, so a catalogue's job is reference.
- preview.describe built a derivation apart from the declaration and dropped a passthrough's open_ended.
- place.py called an exact count a carrier, and read indicator YAML raw, skipping every refusal the registry makes.
- The encoding was written in the manifest's prose and the run's params, held together by nothing.
- carriers.yml named a Maine preparation in a shared seed; IMLS's national codes lived in Maine's preparation.
- Receipts repeat inherited provenance records: 19 records in the libraries edges receipt, graph_repair_towns five times (CHAIN-1).
- Read on Maine's real bed: 1,566 located_in rows, exactly 261 placed outlets times six places each; 261 carriers; House District 42 names North Haven and Rockland, and its count row holds 2.
- Kalli delivers the whole product; the teammates once named in state.md work on other things.

### Carried forward

CHAIN-1 (new), TIERREAD-1, QUADRAT-1, FSCS-1, CHOICE-1, SCHEMA-3, INTERP-1, OWN-1, GEO-1, WHERE-1, OBS-1, SRC-4, TOWN-OFF-1, LIB-2, SERVES-1, TRIBE-7, INDFILE-1, SCALE-1, SURVEY-1, LOAM-2, OUT-REG-1, CON3-2, SCHEMA-1, RECEIPT-1, and the items now Kalli's. Each is in state.md's open items and the ledger.

### Lessons

- Read the code before calling a thing decorative: the label looked like a name and was a guard.
- A fork lists only options that could win; restating refused ones is padding.
- Before writing a reference file, say what no other home holds. The first draft of the catalogue copied the manifest's url, member and encoding, the drift it was written to prevent.
- A whole-file move is checked by diffing the parsed result against the original, not by reading: one dropped param (temporarily_closed) was caught that way.
- A view that agrees with its count on one real place (House District 42: two names, a count of 2) is checked; one that only passes fixtures is not.
- A built file is not delivered until it is presented.

## Session 6: the drift under the carrier layer, cleared

Tests: 867 passed, no skips (12 new, 1 removed). Decisions: D-227 to D-229. INDFILE-1 closed, STAND-1 opened. Commits: 718dcc1, a95aa8d, the session 6 ledger commit, and this hand-off.

### Built

| Commit | What |
| --- | --- |
| 718dcc1 | an indicator's declaration_sha256 taken over its own mapping, canonical, without its rationale, computed when parsed; declaration() never reopens the file; a registry built in memory hashes too; tests/test_declaration_hash.py replaces the whole-file test (D-227) |
| a95aa8d | county standings answers basic_needs_and_opportunity on rent burden and vehicle access, broadband's standing left to its own composed experiment (D-228); the no-curiosity warning names only the gap and never advises a kind the run could not pass (D-229) |

### Found

- Maine DOE's Schools & SAU page is a QuickSight dashboard: school years 2021-22 to 2025-26, a state school ID, status inferred from changes in name or ID, ID 2117 and non-Maine schools excluded (yet points near Albany and Boston), no word on where coordinates come from.
- Weights and reliability hash whole files too, but hold one declaration per file, so only indicators were wrong.
- as_declaration hands a primitive everything but source, weight_by, replicates and rationale. Freshness compares params whole, so the hash's only job is those three.
- The eight receipts that recorded the old hash went stale once; walked path by path, every difference was a declaration_sha256. Five reruns made all eight fresh. libraries_points still holds 261 placed outlets.
- maine_broadband_access_subscription__cii_indicator_values_91b5c0 is a live composed experiment, not a D-222 leftover.
- The D-64 warning told county standings to become a preparation; the code would have refused it twice (a roots/ step, an analysis method).
- County standings and the broadband experiment both computed broadband's county standing; the panels cited as the reason for one receipt have no reader in the repo.
- Origin gained four commits by bash-win and Jessica Pham between sessions; nothing overlapped. A local environment.yml edit, committed by `git add .` under another message, was dropped in the rebase.
- canopy/api/locustfile.py imports locust, which environment.yml does not install.

### Carried forward

STAND-1 (new), CHAIN-1 (34 records in libraries_counts_values), TIERREAD-1, QUADRAT-1, FSCS-1, CHOICE-1, SCHEMA-3, INTERP-1, OWN-1, GEO-1, WHERE-1, OBS-1, SRC-4, TOWN-OFF-1, LIB-2, SERVES-1, TRIBE-7, SCALE-1, SURVEY-1, LOAM-2, OUT-REG-1, CON3-2, SCHEMA-1, RECEIPT-1, DEPS-1 (locust noted), and the items now Kalli's. Who bash-win and Jessica Pham are waits on Kalli. Each is in state.md's open items and the ledger.

### Lessons

- A receipt hashes what its run read. Hashing the file looked safe and tied every indicator to its siblings.
- Before deciding what a hash covers, list what the params already carry: the hash is for what they leave out.
- Read every loader before claiming a problem's scope. Claude first said three registries were wrong; reading load() showed one.
- A verdict says stale; a path-by-path diff says why. Without the diff, "only the hash moved" would have been a guess.
- A warning's advice is code too: check it against the rules it names.
- Read origin before pushing, and commit through guarded blocks only: `git add .` put one commit's file under another commit's message.
- One experiment per question: a receipt that borrows a bigger question says something its numbers do not.

## Session 7: schools as the second carrier

Written in session 9 from the build ledger: session 7's own entry never landed in this file.

### Built

| Commit | What |
| --- | --- |
| 1bd4dfa | Kalli's: sows shares one run path with experiment.py, and init validates plot names (cli-sows-parity, fast-forwarded onto main) |
| 754d2f7 | schools from NCES EDGE 2024-25: 598 Maine public schools placed where each stands (STFIP), operator flagged; the three Wabanaki community schools placed and counted once in every drawer (D-230) |

### Found

- Maine DOE's 13 dashboard exports carry no school ID, and its location exports no names: a dashboard export is not a release, and only our copy is evidence.
- EDGE's text table holds 102,178 rows, 23 fields each when read with its quotes, valid UTF-8; all 598 Maine rows stand in Maine by STFIP.
- loam's join grammar matches key names, never issuers, so every carrier's feature_id looks joinable to every other (JOIN-1).

### Carried forward

JOIN-1, TRIBE-8 (closed in session 8 by D-233), and state.md's open items.

### Lessons

- A name is never a key.
- Three state fields can mean three things: where an address says, where the point stands, and who operates the school.

## Session 8: boundary_vintage, health centers, tribal areas beside their notes

### Built

| Commit | What |
| --- | --- |
| 14f3100 | boundary_vintage on every count row, from its edges; loam reads it for our counts, so `time` says only when (D-231, SURVEY-1 closed); libraries and schools rerun |
| f6eecef | health centers from HRSA's 2026-11-14 copy: 168 Maine sites placed, 24 listed with reasons; seasonal and look-alike as adjectives; seeds/sources/hrsa.yml (D-232) |
| the D-233 commit | tribal areas counted beside a note on every row; loam refuses only the ACS there and judges each publisher on its own levels; all three carriers rerun (TRIBE-8, LOAM-2 closed) |

### Found

- No Wabanaki nation's clinic appears in HRSA's file, by name or by town; the PLS sees no reservation library; NCES sees the three BIE schools, each now counted on its reservation.
- HRSA's 10 administrative Maine sites carry setting Unknown or All Other Clinic Types; Form 5B asks no setting of an administrative site.
- The 5 Maine rows with site state XX are service sites with no address or point, not withheld shelters.
- loam's carriers view drops every point property but id and name (CARRY-1).

### Carried forward

CARRY-1 (blocks the map), the tiers, the Contract 4 questions, and every item in state.md's open items, now sorted for delivery.

### Lessons

- A rule written for one source travels unless it names its reason without its source.
- A column with two meanings hides behind a coincidence until a third source breaks it.
- Refusing a place hides it; a number with its note shows it in context.


## Session 9: GEO-1, clerks' offices placed through Maine's 911 points

### Built

| Commit | What |
| --- | --- |
| 8c6c645 | clerks' offices as carriers: the Secretary of State's clerk list matched exactly to Maine's 911 address points through USPS Publication 28; 390 offices for 458 of 560 rows; ties settled by the building rule and Kalli's campus choice (D-234 to D-239) |
| adfb469 | the session 9 ledger: D-234 to D-239; E911-1, GEO-2, GEO-3, GEO-4, ARC-1, TRIBE-10 opened |

### Found

- The 911 file's classes cannot list town offices: its default is Residential, and of the 352 exact matches only 152 are Government - Municipal (44 Residential, 21 fire stations, 16 police).
- Most ties are campuses, a town office and a fire station under one civic address, tens of metres apart; 66 ties became 20 under the building rule and the campus choice.
- Penobscot Nation's and Pleasant Point's offices are placed on their reservations; Indian Township is missed by Road against St, so 1575R reads zero until a reviewed match (GEO-4).
- The 74 misses read so far are spelling on our side (suites, highway names, a detached number letter, streets with no suffix) more than a case for a second geocoder (GEO-2).
- The GeoLibrary file and the live 911 service are not one dataset: different counts, different field names.

### Carried forward

GEO-4 (before publishing), E911-1, TRIBE-10, GEO-2, GEO-3, ARC-1, and state.md's open items.

### Lessons

- A default value is a silent classifier: a class is never evidence of a use.
- Match by address, never by class.
- A read that cannot come back positive proves nothing.
- A long paste can lose its middle or land twice: read its line count before trusting it.

## Session 10: GEO-4, and outlets placed by town

Tests: 1003 to 1065, no skips. Decisions: D-240 to D-246. Commits: 6fad8ca (GEO-4), the session 10 ledger (D-240, D-241), the outlet carriers, their ledger, the hand-off.

### Built

| Step | Commit | What |
| --- | --- | --- |
| 3 | 6fad8ca | GEO-4: reviewed clerk matches in seeds/crosswalks/clerks/maine_sos_reviewed.yml, keyed by the list's address as written; Indian Township and 7 Minden placed, placed_by reviewed (D-240) |
| 3 | the outlet carriers commit | maine_outlet_carriers: prepare_news_outlets and build_town_located_in, the outlet_carriers method, the census_name_suffixes and outlet_reviews seeds, news_outlets_per_1000 and the news_outlet type; loam's carriers view leaves a table layer out by name (D-242 to D-246) |

### Found

- Clerks: 392 offices for 468 of 560 rows; 1575R reads 1, so the zero that was ours is gone. 7 Minden stands on the point labelled Greenville Police Department, so CARRY-1 keeps landmark and place_type off the map.
- Outlets: only 111 of 924 records name a town, which reopened WHERE-1 the day it was decided.
- Outlets: 460 placed (388 office_town, 72 named_town), 65 listed; Portland 121, Bangor 67, Cumberland County 191 of 460.
- Cision's types include trade press and blogs; nothing filters by medium yet. None of the listings is dated.

### Carried forward

MEDIUM-1, OFFTOWN-1, OUTREV-1 and UNDATED-1 (the next tree), E911-1, TRIBE-10, CARRY-1, OWN-1, SRC-4, and every item session 9 carried. Each is in state.md's open items and the ledger.

### Lessons

- Read before the tree when a fork rests on data: one count reopened a decision written that morning.
- Four forks, workshopped, then one holistic build: one zip, 44 new tests and a clean first run. It is the way of working from here (Kalli).
