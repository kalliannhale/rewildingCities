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
