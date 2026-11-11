# State of the garden ~ rewildingCities

What is true now. Rewritten, never appended, at every hand-off (D-160). The
build ledger (field-guide/docs/build_ledger.md) is the history; this page is
the present. When the two disagree, the ledger and the code win, and this page
is fixed.

**Updated:** 2026-11-11, after NAME-4's change 1 and Sprint 06's design pass.

## Where the build stands

- Branch main. Commits since Sprint 05's close: 190d856 (NAME-4 change 1, D-192 to D-196), d63fd12 (Contract 4 at 0.3, D-197 to D-200), the removal of garden/experiments/in-the-cloud, and this page. Confirm with `git log --oneline -5` and `git status -sb`, and that they are pushed.
- Tests: `python -m pytest -q -rs`. 558 passed, no skips. The R oracle tests (test_index_r_oracle.py, test_derive_indicator_oracle.py) run only where Rscript and rewildr are installed; `-rs` names a skip, since a skip proves nothing.
- Plan of record: the Master Plan, https://claude.ai/artifact/KpQRRSTyXr27emXnJFfL6z. Its decision table stops at D-81; check its claims against the code.
- Next decision ID: D-201. Before minting any ID, grep the ledger for it (LEDGER-3).
- **Sprint 06 is open**: the design pass is done (Contract 4 at 0.3); acquisition and building come next, across several sessions, in the order below.
- On or after 2026-12-02, when the 133rd's rosters are acquired: flip available: true, TRIBE-4, SEN-1, then run maine_seats.

## Since Sprint 05

| Commit | What | Decisions |
| --- | --- | --- |
| 190d856 | NAME-4 change 1: manifests name a source's publisher provenance.published_by; six indicator sources declare source.unit_authority; the orchestrator holds every run's copy of a source fact to the source; one rule for retired words; one manifest parser | D-192 to D-196 |
| d63fd12 | Sprint 06 design pass: Contract 4 at 0.3 | D-197 to D-200 |

Closed: NAME-4, SRC-2 (in D-192's form). LAYER-1 moved to Sprint 08. Sprint 05 itself: field-guide/docs/progress/information/sprint-05.md.

## Sprint 06 ~ the place profile and the standard

**Goal:** every Maine place has a six-part profile, its carriers are on the map, and every barrier is judged against a stated, absolute standard.

**Decided in the design pass:**

- D-197: `build_profile(loam, authority, code)` composes `read_place` and wraps its PlaceReading; read_place is not grown.
- D-198: verdicts are margin-aware: meets, below, within_margin, cannot_judge (with its reason), no_threshold. Ratio margins come from a new soil primitive, derive_margins, one more step in each indicator preparation, keyed by measurement_id, formulas declared in a seed beside the indicators (never inside them: the `$indicators` trap) and cited to the ACS handbook. No value receipt reruns.
- D-199: three kinds of threshold: `universal` (report how many fall short, from the place's own estimate), `trigger` (list what crosses a legal or published line), `none` (said plainly, value still shown).
- D-200: each IFL barrier is a family of registered indicators, each a layer at its grain, with a status: acquired, acquirable, needs_our_model, needs_consent. CII's measures are reused as values; only its standings are relative.

**The barriers, their indicators, and where the data is:**

| Barrier | Indicators | Source | Grain | Status |
| --- | --- | --- | --- | --- |
| Not in the right language | limited-English persons by language; safe-harbor languages, min(5%, 1,000) with the 50-person carve-out; VRA section 203 coverage | ACS language-by-ability tables; DOJ LEP guidance (2002); Census section 203 determination file (2021), passed through | town | acquirable |
| Requires digital access | households with no internet subscription; households with no service at the FCC benchmark | ACS; FCC National Broadband Map | town | ACS acquired as a rate; counts and FCC acquirable |
| At the wrong literacy level | adults at or below Level 1 literacy and numeracy | NCES PIAAC Skills Map (pooled 2012/14/17; copy on DataLumos) | county, borrowed on town profiles | acquirable |
| Lacking cultural cues | languages spoken against languages local carriers publish in (a proxy for one part of cultural fit, and said so) | ACS and the outlet inventory | town | depends on P-9 |
| Behind a paywall | share of local outlets free to read | outlet inventory (P-3) | town | depends on P-9 |
| Outdated | outlet publishing frequency | outlet inventory | town | depends on P-9 |
| Not where people look | carriers per 1,000 by type; library visits per person | IMLS PLS, MEGIS town offices, Maine DOE schools, HRSA health centers, the outlet files | town | acquirable |
| Not from a trusted source | relational hubs, aggregate-only | consent-governed | as consented | needs_consent (Sprint 16) |

Needs (part 1, values only, never judged): population, households, older adults living alone, disability, poverty, rent burden (ACS, SAIPE).

**Order of work, one session or more each:**

1. Read the outlet files for P-9: do they carry language of publication, publishing frequency, paywall status? Read, never assume.
2. `located_in` edges for points, with their end checks (carried from Sprint 04).
3. Carriers: acquire each point layer by a preparation, declare its semantic type, count it over located_in, per 1,000. A point inside two districts counts in both.
4. derive_margins (D-198): the formula seed, the primitive (R or Python is a small fork; lean R beside derive_indicator, oracle in preview.py), one step per indicator preparation, the place_values join.
5. Language: the ACS tables, the safe-harbor trigger, the section 203 file.
6. Literacy: the PIAAC county estimates (P-7).
7. Digital access counts and the FCC map (P-6).
8. Outlets reconciled: every source's record side by side, ownership by resolve_ownership, concentration by concentration_index.
9. `canopy/wonder/profile.py` and the standard seed in seeds/.
10. The pairing table (P-2).
11. Profiles for every place: the state, 16 counties, 529 towns, 151 House and 35 Senate districts, tribal areas as a qualified Census view.

**Still open in Contract 4:** P-1 (each barrier's threshold, row by row), P-2 (pairing table), P-3 (free outlet), P-5 (a universal side for language; lean yes, kept apart), P-6 (FCC benchmark, verify), P-7 (PIAAC 2023 county estimates?), P-8 (section 203 on Wabanaki places, with Person 3), P-9 (what the outlet inventory carries).

## Contracts

field-guide/docs/contracts/: 1 tiers and the gate 0.5; 2 canonical objects 0.1; 3 geography graph 1.0 (the grove teammate's own review is owed before the handoff); 4 place profile 0.3.

## Where invariants are held

| Invariant | Held by |
| --- | --- |
| Every town has one contains edge from its county | build_place_edges; tested |
| A block's county is its 2024 town's (BOUND-1) | build_block_spine; tested |
| Shares sum to 1 per chamber, per basis | build_place_edges, check_shares; tested |
| Every district touches a town | by construction from the spine (D-161); tested |
| Edge ends exist in places | build_places; tested. located_in not until Sprint 06 |
| An edge's two ends name one edge | build_place_edges, check_key (KEYS-1); tested |
| Vintages match | build_places (D-162); place_values through seeds/vintages/boundaries.yml (D-170); tested |
| Tribal places carry their note and name their area | build_places; tested |
| Towns equal the 2024 layer | build_places; tested |
| Every authority is declared, each level under one | seeds/authorities/authorities.yml; tests/test_authorities.py (D-188) |
| District values keyed by chamber | tests/test_district_values.py (D-176) |
| Only a declared count moves along an edge | canopy/loam/edge_rules.py; tests/test_edge_rules.py (D-179) |
| Every indicator's universe is declared | seeds/universes/universes.yml; tests/test_universes.py (D-181) |
| An index never ranks across authorities | weighted_index.R; tests/test_index_r_oracle.py (D-190) |
| A run's copy of a source fact agrees with the source | Orchestrator._validate_source_facts, from source_facts in the layer registry; tests/test_source_facts.py (D-192, D-193) |
| A retired word makes only its dataset unusable | parsing.declaration_problems; tests/test_source_facts.py, test_recipe.py, test_indicator_preview.py (D-194) |
| Every Maine indicator source declares published_by and unit_authority | tests/test_source_facts.py |

## IDs defined outside the ledger

The ledger has no entries for D-98 to D-124 (LEDGER-1), which is why it has no Sprint 01, 02 or 03 headings. Where some live:

| ID | Where | What |
| --- | --- | --- |
| D-101 | Contract 1, E-1 | rule 3 is a conjunction of tiers |
| D-102 | Contract 1, E-2 | an empty curiosity passes rule 4 as a caveat |
| D-118 | semantic_types.yml comments | PROPOSED tiers, for Person 3 |
| D-121 | Contract 3, G-1 | both weights on every overlaps edge |
| D-122 | Contract 3, G-2 | MEGIS divisions join towns through block points |
| D-123 | build_places.py docstring; census_tribal_area's comment | tribal places are the Census 2020 legal areas |
| HASH-1 | tests/test_preparations.py | HASH-2's earlier name; resolved |
| MP-67 to MP-81 | Master Plan | the plan's own D-67 to D-81 |
| P-1 to P-9 | Contract 4 | the profile's open questions |

## Open items

| ID | One line | Defined |
| --- | --- | --- |
| SRC-2's check | freshness after NAME-4 is predicted fresh (no run's params changed) and not yet checked; the probe is in Traps | ledger, change 1 |
| SRC-3 | the two MEGIS layers and the two legislature rosters name no publisher; whether every source must is undecided | ledger, change 1 |
| USE-1 | a run does not honor underspecified in general (_resolve_manifest_ref); D-192 refuses it for source-fact steps only | ledger, change 1 |
| SPEC-1 | models.py defines a second PrimitiveSpec; registry.py's is the one used | ledger, change 1 |
| LAYER-1 | layer sources declare unit_authority and their key property; map.py joins by declared authority; with the publish door (Sprint 08). Verify the district layers' property names first | ledger, build 6 |
| COUNT-1 | Sprint 06 counts people left out from each place's own estimate (D-199); allocating counts along edges stays with the outreach planner (Sprint 12) | ledger, change 12; D-199 |
| TENURE-1 | a renter share needs a renter weight on the edges; not needed in Sprint 06 | ledger, change 12 |
| KIT-1 | Sprint 10 must decide: --accept-stale, hashing primitive code, VER-1, DEPS-1 | ledger |
| TRIBE-6 | compare Maine's 8 tribal areas, 2024 against 2020 | ledger, change 7 |
| NOTE-3 | the tribal representation note (MP-77) is not written; confirm maine_seats' tribal list | ledger |
| LEDGER-1 to LEDGER-3 | missing D-98 to D-124; the step 4e block twice; MAP-4 names two entries | ledger |
| LIN-2, VER-1, NOTE-2, Rule 10, TRIBE-5, PENOB-1, GJSON-1, RESOLVE-1, DEPS-1, SEAM-2, DAS-1, HIST-1 | as before; look each up in the ledger before relying on it | ledger |
| Person 3 | D-118's tiers, ROLE-1, the draft notes, NOTE-3, D-173's review, P-8 | ledger |

Also carried, look up in the ledger first: S2-1, GATE-2, GATE-3, MAP-8, MAP-9, TRIBE-4, SEN-1, LEGI-1, LEG-4, LIC-1, KEY-1, XCHK-1, COMP-1, REG-1, LOOP-1, ACQ-6, SCH-5, TAG-1, MEGIS-3, LURC-1, BAXTER-1, DISS-1, METH-1.

Untested refusals: a town in two counties, a county or district without a name, a place key used twice, a reservation subdivision in two reservations, a missing vintage, derive_indicator.R's refusal of a leftover `authority` param.

## Working agreement, as it stands

- Design before code, forks one at a time with a lean, nothing chosen silently. Kalli reads, runs and commits; Claude drafts.
- Before any threshold or external claim, Claude researches and cites what a source actually says, and says plainly where a source gives no number.
- A change may come as a zip of repo-relative files, unzipped with `unzip -o ~/Downloads/<name>.zip -d .`; small files and every ledger block come inline. Inline files are `cat > path << 'EOF'`, one file per paste, every `EOF` at the left edge.
- Whole-file replacements; `git --no-pager diff` is read before anything runs.
- Every commit block is guarded and names its files: a zsh array, `git diff --quiet -- $files` prints STOP when nothing changed, and `git commit -- $files` keeps anything else out.
- Ledger blocks appended with cat >>, each starting with a newline. No em dashes, no inline shell comments.
- Before changing a signature, search the keyword itself across every test and caller, then read each hit for meaning.
- Read real output as its reader would before committing a telling.

## Traps

- /mnt/project in Claude's sandbox is a stale October snapshot. The repo is on Kalli's machine.
- Run a preparation with `python -m canopy.cli sows <run.yml>`; `--dry-run` only validates. Never `--resolve-only` casually (RESOLVE-1).
- Do not run maine_seats on real data before 2026-12-02.
- `authority` means only who assigns a place's code. A publisher is `published_by` everywhere, manifests included (provenance.published_by). A manifest still writing provenance.authority makes that dataset underspecified, and compose and preview refuse it.
- A source's unit facts live in its `source:` block: unit_authority, unit_column, unit_pad, name_column. A run may write unit_authority or published_by, and validate() refuses it if it disagrees with the source.
- preview.derive takes `published_by=`; preview refuses a unit_authority that disagrees with the source's.
- Freshness never judges primitive code (KIT-1), and is judged only when a run reaches a `$loam.` input. To judge every receipt by hand, run the read-only probe: build an Orchestrator on any Maine preparation, then `judge(read_envelope(p), root, orch._declared_params)` for each file in plots/maine/.envelopes.
- `$indicators.<id>` resolves to the whole declaration, so editing an indicator seed makes every derive receipt stale. Facts about indicators belong in a seed beside them (seeds/universes/, and derive_margins' formula seed).
- seeds/weights/ holds index weightings; edge weights are declared per universe in seeds/universes/.
- The views exist only in a bed opened by open_plot; Loam.snapshot() copies the catalog alone (D-168). VALUES is reserved in SQL.
- `wonder --place` takes a key, AUTHORITY:CODE, never a name.
- A town range is one estimate per town. Read the firm range before quoting a range's ends.
- open_plot parses the manifest once (P-01). preview and wondering read through parse_manifest too (D-195).
- A step's `outputs:` in a preparation gives names, not paths. Receipts are `.envelopes/<step>_<output>.envelope.json`.
- Tests that fake EnvelopeBuilder.run must accept run and step. A test fake that records an md5 must record the real one.
- Progress reports live in field-guide/docs/progress/<domain>/sprint-NN.md.
- The geography graph preparation declares `vintages` twice; change both together (D-162).
- The gate runs only at exits (canopy/expose/check.py). Inside a run only the precondition gate and validate() apply.
- `sows` prints nothing until the run ends.
- R primitives: a list of one needs as.list (C-36); read code columns as text.
- Vocabulary.load reads only semantic_types.yml and domains/*.yml.
- soil/_registry.yml, seeds/schemas/semantic_types.yml and seeds/notes/notes.yml each end with their one map.
- Scope every grep: quote globs, and never grep `plots` without `--include="*.yml"`.
- `git diff` opens a pager; use `git --no-pager diff`. It is `git status -sb`, one dash.
- Keys live in Kalli's environment only (KEY-1). The repo is public.
- The sandbox lacks pytest, pyarrow, shapely, duckdb, jsonschema, pyogrio and R; it has pandas and yaml. Pure-Python logic can be smoke-run there with stand-ins.

## People

Kalli: Maine data and geography, profile, explorer, review of everything; acting grove teammate. Ajitesh: publish route (Sprint 08); LAYER-1, GJSON-1 and D-157's required notes argument matter for his door. Infrastructure teammate: Sprints 07 and 10; DEPS-1 and KIT-1 matter for the Docker build. Person 3: tier declarations, note wording, NOTE-3, D-173's review, P-8.
