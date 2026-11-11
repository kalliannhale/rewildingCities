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
