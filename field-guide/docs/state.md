# State of the garden ~ rewildingCities

What is true now. Rewritten, never appended, at every hand-off (D-160). The
build ledger (field-guide/docs/build_ledger.md) is the history; this page is
the present. When the two disagree, the ledger and the code win, and this page
is fixed.

**Updated:** 2026-11-11, at the close of Sprint 04 step 6.

## Where the build stands

- Branch main. Step 6 is committed on top of 239cfd5. Read `git log --oneline -1` for its hash.
- Tests: `python -m pytest -q`. 415 passed at the close of step 6.
- Plan of record: the Master Plan, https://claude.ai/artifact/KpQRRSTyXr27emXnJFfL6z. Its decision table stops at D-81; check its claims against the code.
- Next decision ID: D-161. Before minting any other ID, grep the ledger for it.
- Current: Sprint 04. Next is step 7, the remaining invariant tests, only where build_place_edges and build_places do not already refuse. Step 4 closes when loam reads places into build_seats (LOAM-1, Sprint 05). On or after 2026-12-02, when the 133rd's rosters are acquired: flip available: true, TRIBE-4, SEN-1.

## Contracts

field-guide/docs/contracts/: 1 tiers and the gate 0.5; 2 canonical objects 0.1; 3 geography graph 0.8 (section 6 Seats); 4 place profile 0.2.

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
| HASH-1 | tests/test_preparations.py line 90 | HASH-2's earlier name; cite HASH-2 |
| MP-67 to MP-81 | Master Plan | the plan's own D-67 to D-81 |

## Open items

| ID | One line | Defined |
| --- | --- | --- |
| NOTE-2 | descendants of places other than outlines write no row_context_notes, so they carry both tribal notes by lineage | ledger, step 5b and 6 |
| Rule 10 | places and every outline are withheld at public under rule 10 only; the refusing dataset is not yet read (LIC-1?) | ledger, step 6 run |
| TRIBE-5 | 0115T, 2695T, 2760T outlines do not nest in the Census 2020 layers by more than water; causes unknown | ledger, step 5b |
| PENOB-1 | the Main Stem note is drafted and declared; its wording waits on Kalli and Person 3 | ledger, steps 5b and 6 |
| GJSON-1 | rewildr's safe_write_sf cannot overwrite a GeoJSON holding one very large feature; the state outline is unreadable by default GDAL readers | ledger, step 5b |
| RESOLVE-1 | `--resolve-only` can acquire and commit; only dry_resolve() is read-only | ledger |
| DEPS-1 | geopandas and pyogrio are installed but not declared; tests/debug imports pyogrio | ledger, step 5b |
| HASH-2 | a test-profile envelope cannot round-trip or validate | ledger, step 5a |
| SEAM-2 | outlines and overlap weights disagree on split blocks, by design; do not fix | ledger |
| HIST-1 | waiting on CII's reply to Kalli's Nov 10 email | ledger |
| Person 3 | D-118's tiers, ROLE-1, and the two draft notes | ledger |

Also carried, look up in the ledger before relying on them: S2-1, GATE-2, GATE-3, MAP-4, MAP-8, MAP-9, TRIBE-4, SEN-1, LEGI-1, LEG-4, LIC-1, KEY-1, XCHK-1, LOAM-1, SEAM-1, AUTH-1, SRC-1, COMP-1, REG-1, NAME-2, LOOP-1, ACQ-6, SCH-5, TAG-1, DAS-1, ZERO-1, MEGIS-3, LURC-1, BAXTER-1, DISS-1, METH-1. CLI-1 to CLI-3 are not in the ledger under those strings; they may be about the two CLI doors (sows and experiment).

## Traps

- /mnt/project in Claude's sandbox is a stale October snapshot. The repo is on Kalli's machine.
- A step's `outputs:` in a preparation gives names, not file paths.
- Notes for merged places (counties, districts, the state) are decided in build_places, which has the spine, not in the outlines.
- The gate runs only at exits (canopy/expose/check.py). Inside a run only the precondition gate applies.
- `sows` prints nothing until the run ends; a full geography graph run takes a while. To see a running R step: `ps aux | grep "[b]uild_place_outlines"`.
- R primitives: primitive_success serializes with auto_unbox, so a list of one needs as.list (C-36). rewildr's safe_read_table infers CSV types; read code columns as text. safe_write_sf fails to overwrite a one-large-feature GeoJSON (GJSON-1).
- Vocabulary.load reads only semantic_types.yml and domains/*.yml. Note texts live in seeds/notes/notes.yml, loaded by the gate.
- `soil/_registry.yml`, `seeds/schemas/semantic_types.yml` and `seeds/notes/notes.yml` each end with their one map, so appends land correctly. The geography graph preparation's `steps:` list is its last key.
- Scope every grep: quote globs, and never grep `plots` without `--include="*.yml"`, because `.data` holds large binaries.
- Keys live in Kalli's environment only (KEY-1). The repo is public.
- The sandbox lacks pytest, pyarrow, shapely, duckdb, jsonschema, pyogrio and R.

## People

Kalli: Maine data and geography, profile, explorer, review of everything; acting grove teammate. Ajitesh: publish route (Sprint 08); GJSON-1 and D-157's required notes argument matter for his door. Infrastructure teammate: Sprints 07 and 10; DEPS-1 matters for the Docker build. Person 3: tier declarations and note wording.
