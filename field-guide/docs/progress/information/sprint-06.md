# Sprint 06 ~ the place profile and the standard: progress report

**Open.** Domain: information. Contract: 4, draft 0.3.

## Session 1: P-9, SRC-2's check, and the outlet stack

### SRC-2's check

Read-only probe over plots/maine/.envelopes: 28 receipts, 20 fresh, 8 cannot_tell, none stale. NAME-4 changed nothing that could be checked. The 8 are every receipt of maine_counties, maine_county_units and maine_governance_units, whose steps were recorded before D-167 and name no run or step. Left as they are; rerun those three preparations when anything reads them through `$loam.`.

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

### Found in the files

- Cision's Outlet County reads Cook, a county in Illinois, for Maine outlets.
- Cision's address is the publisher's office: it puts the Advertiser Democrat (Norway) and the Livermore Falls Advertiser in South Portland.
- The two Cision files are separate pulls: 297 names in both, 115 only in the raw export, 56 only in the 353.
- Cision's Still Operates? is a hand-added observation: 323 yes, 21 ceased, 9 a last-post date. Who checked, and when, is not recorded.
- Easton's Contact column names people and is never read. Her SimilarWeb figures are a third party's estimates and are not read.
- The aggregated-signals file is a survey about which data exists, with respondent files; it is not an outlet list and is kept out of the outlet layer.
- The outlet files live in garden/reference/, ignored by .gitignore line 86, so none reach the public repo.

### Built

| Commit | What |
| --- | --- |
| 6fc983e | seeds/crosswalks/outlets/outlet_sources.yml and soil/transform/stack_outlet_sources.py: every source read as declared, stacked one row per record |
| 887e301 | soil/transform/group_outlet_records.py: records grouped by exact url and name keys, never one source twice; disagreements listed |
| ad5bfad | a key one source holds twice joins nothing, so no match is chosen by row order |
| 2770bdd | place fields keep their meaning (office, named, served); counties outside Maine flagged, never fixed |

### Carried forward

- Language and paywall need our own observation of each outlet, with a receipt per observation: a status question under D-200.
- Which place meaning counts as where an outlet is, for located_in: office, named town, or coverage.
- Both outlet steps as registered primitives in one preparation, writing receipts.
- The ecosystem file's publisher, the Still Operates? receipt, and every source's terms.
