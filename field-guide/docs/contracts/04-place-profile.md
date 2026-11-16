# Contract 4 ~ The place profile

**Status:** draft 0.4, 2026-11-16 (D-258, D-263, D-270 to D-282 and D-283 to
D-293, built in zips 2 and 2b; 0.3 was D-197 to D-200). **Owner:** Kalli. **Built in:**
Sprint 06 (`canopy/wonder/profile.py`, `canopy/wonder/verdicts.py`,
`canopy/standards.py`; the command `python -m canopy.cli profile <plot>`).
**Read by:** the explorer (Sprint 09), district briefs (11), the outreach
planner and Compare (12), the open data hub (13). **Rests on:** MP-73 (the
explorer is the front door; briefs follow from the same profile), MP-74
(barriers judged against an absolute standard), MP-75 (towns get values,
never standings), Contracts 1 and 3, D-104, D-183, D-185, D-186.

One structured object per place, which every product renders. Products cannot
disagree about a place, because none of them computes it: they all read the
profile.

The profile is a document assembled from measurements (D-197).
`build_profile(loam, authority, code, *, context)` calls `read_place`
(canopy/wonder/place.py) and wraps its `PlaceReading`; carriers,
disagreements, gaps, gate refusals and channels come from their own readers.
`context` is a `ProfileContext`, read once per build: the registry, the
standard, the notes and the gate's answer for every receipt. `read_place`
stays one measurement and is not grown into the profile (D-184). The profile
decides how to read each level: a district or county reads its towns, the
state reads its counties, a town has no parts.

Profiles are built by a canopy command, never a sows run (D-274): one
`place_profile` artifact holding every place, with its own receipt. **The
gate is asked first (D-284).** Every receipt a value would come from is
judged at `public` before its value enters. A withheld receipt's values never
enter the file; its refusal does, in part 5, saying the data exists and why
it stays (Contract 1, rules 7 and 8). The receipt's inputs are exactly the
receipts whose values entered, so the door's gate binds exactly what the file
holds; every withheld receipt is named in its params, never an input. The
one exception is the graph itself: every profile's names, contents, overlaps
and borrowed shares come from the places and edges receipts, so they are
always inputs, and when the gate withholds them the command says plainly that
the whole file cannot leave until they may (D-293).

Every rule a verdict follows lives in `verdicts.py` as a function of numbers,
so it can be read and tested without a bed.

## 0. Header

| Field | Meaning |
| --- | --- |
| `place` | the place's key, `(authority, code)`, and its `level`, `name`, `vintage` (Contract 3) |
| `flags`, `context_note` | from the places table, shown first, never hidden behind a click |
| `built_at`, `built_by` | when, and which profile version built it |
| `gate` | `record: null` with why: the allow record is decided at the publish door, never written inside the file it judges (D-274) |

## 1. Who is represented

| Field | Meaning |
| --- | --- |
| `population`, `households` | each with its release, margin and `published_by`. Population is the 2020 Census count every per_1000 divides by, read from a carrier count that may leave (D-280). Households are the ACS's, the denominator of the digital count, whose margin the values file does not carry, said so (D-286) |
| `needs` | every indicator whose role is need (rent burden and vehicle access among them, D-279): values with margins, never judged against a threshold here |
| `legislators` | for a district, who represents it; for a town, the legislators of every district it touches, with shares. Until the 133rd's rosters are acquired (on or after 2026-12-02), this says so, by name of the missing holding |
| `inside` | places this one contains (`contains` edges) |
| `overlapping` | places this one overlaps, each with both weights (`overlaps` edges, D-121) |

## 2. Barriers

Organized by the Information Futures Lab's barriers (MP-74), as the standard
declares them: `seeds/standards/information_barriers.yml`, shaped by
`seeds/schemas/standard.schema.yml` (D-270). Barrier membership lives there
alone; the registry keeps only role, and every indicator whose role is barrier
is named by exactly one barrier. A measure is a registered indicator, a
measure inside an artifact (literacy_estimates, section203_records), or a
measure not yet held, each with its status (D-200).

### 2a. One entry per barrier

| Field | Meaning |
| --- | --- |
| `barrier` | the IFL barrier, in its words: not in the right language, requires digital access, at the wrong literacy level, lacking cultural cues, behind a paywall, outdated, not where people look, not from a trusted source |
| `indicators` | the entries of 2b |
| `sides` | the barrier's thresholds, each of one kind (D-199): `universal`, `trigger` or `none`, with `statement` in plain words, its `source` and who declared it; never a number without both. A universal side names the count it `judges` and carries `meets`, saying why an estimate never meets it. A trigger of ours carries its `groups` (each with its verdict) and `crosses`; a published determination names the measure it is `as_published` in |

### 2b. One entry per indicator

| Field | Meaning |
| --- | --- |
| `measure`, `indicator`, `measures` | the standard's measure id, the registry id (or `artifact`), and what it measures |
| `status` | `acquired`, `acquirable` (its source named), `needs_our_model` or `needs_consent` (Sprint 16). Anything but `acquired` also appears in part 5 |
| `estimate_kind` | `survey` (ACS), `model_based` (for example PIAAC small-area estimates), `administrative` (counts of carriers), `inventory` (an outlet attribute), `published_determination` (for example a Census section 203 determination), `computed` (from other indicators, its method named) |
| `value`, `unit` | at full precision |
| `grain` | the level the value is published at |
| `borrowed_from` | when the value is a coarser place's (a county's literacy estimate on a town's profile): a list, every place it comes from, each with its share of this place's residents from the graph's edges (residents, never adults 16 to 74), and its own value. `value` here stays null: a borrowed value is always the other place's, never this place's own (D-276) |
| `uncertainty` | the margin or interval, its `confidence` and its `method`: `published`, `derived` (inside derive_indicator, with its formula, D-258), `credible_interval`, or why there is none (`open_ended`, `absent`). Confidence comes from the indicator's declared uncertainty, held once in the registry (acs_moe: 0.90); a row's own wins (literacy's 0.95) (D-277) |
| `bound` | for an open-ended median, the bound in words; then `value` is not a measurement |
| `households_behind` | the count of households (or persons) in the value's denominator, from the same release. A rate over 14 households is a different fact from a rate over 14 000, and the profile always says which |
| `left_out` | on the measure a `universal` side judges: the people short of the line, the count with its lower and upper bounds and their confidence; `count: null` with why when there is no own value (borrowed, withheld, not acquired). `left_out` means only this, everywhere a reader sees it (D-278). Never allocated along edges here; allocation is the outreach planner's (Sprint 12, COUNT-1) |
| `verdict` | see the rule below; every verdict carries `says`, one plain sentence, and names its `side` |
| `judged_on` | for a measure no side judges itself: the measure in this barrier that carries the verdict (a rate beside its count, a share beside its group's count) |
| `towns` | for a county or district: the towns wholly here and their range, the split towns named one by one with how much of each is here, and the firm range (D-183, D-185), with place.py's range statement |
| `published_by`, `vintage`, `method` | who published it (D-186), which release, which run produced it (`lineage.run`) |

### The verdict rule (D-198, D-272, D-273)

A verdict compares the place's own value with the threshold, at the
uncertainty's stated confidence:

- **universal**, judged once, on its count of people short of the line,
  against zero (D-272): `below` when the count less its margin is above zero;
  `within_margin` otherwise, which never means the line is met. `meets` is
  unreachable for an estimate, and every universal side says so. A model's
  count is judged by its credible bounds the same way (literacy)
- **trigger of ours**, per group, over every value its margins allow (D-273,
  D-289): `crosses` a tier when every such value lands in it,
  `does_not_cross` when every one is below every tier, `within_margin`
  naming each tier a value inside could truly be in. Tiers use only at-least
  conditions, so the margins' ends and the tiers' own numbers between them
  find every reachable tier
- **published determination**: `as_published`; the publisher decided it, we
  report it, and no margin of ours touches it (D-263, D-273)
- `cannot_judge`: with its reason, in plain words: no margin to judge with,
  an unchecked statistical area, an open-ended bound, a borrowed value, a
  value withheld by the gate, a measure not acquired
- `no_threshold`: the barrier's side is of kind `none`

A small sample does not stop a verdict: the margin decides, and the value's
reliability note travels beside it (D-287). A town range is never judged,
only the place's own value. A small town's wide margin decides by itself
what can be judged; no rule singles towns out.

**A profile shows values, never standings (D-104).** Towns have none (MP-75),
and a county's standing stays in its experiment's own products. A verdict is
against an absolute, cited threshold, never against other places.

## 3. Carriers

One entry per carrier type (libraries, outlets, town offices, schools, health
centers):

| Field | Meaning |
| --- | --- |
| `type` | the carrier's semantic type |
| `count` | points `located_in` this place (Contract 3; built in Sprint 06) |
| `per_1000` | per 1 000 people, with the population it divided by and that population's release |
| `use` | where the source records it, for example library visits per person |
| `published_by`, `vintage` | where the points came from |

## 4. Where sources disagree

One entry per measure that more than one publisher publishes:

| Field | Meaning |
| --- | --- |
| `measures` | the shared measure (as `registry.measuring()` returns it) |
| `values` | each publisher's value, with its unit, vintage and receipt |
| `difference` | for two values whose units match, or which are both percents of the one measure: the first less the second, named in `difference_is` (D-288); otherwise null with `difference_why` |
| `reason` | why, if known; otherwise `unknown`, never omitted |

Both values are shown. The profile never picks one. One measure only: two
measures of one subject (CII's average literacy score and PIAAC's share at or
below Level 1) are shown side by side in their barrier, never here (D-282).

## 5. What cannot be answered

| Field | Meaning |
| --- | --- |
| `gaps` | each missing holding (the 133rd's seats until they are acquired), and each measure declared acquired that this plot holds no values for. The method authors' own words from `readiness` and `possibility` are not yet read in (GAPS-1) |
| `not_acquired` | every indicator of part 2 whose status is not `acquired`: its status, its named source, and what acquiring it needs |
| `cannot_judge` | every verdict of `cannot_judge`, with its reason |
| `refusals` | every receipt the gate withheld whose values this place would have shown, with each refusal record (Contract 1, rule 7): type, tier, ancestor, reason, what would admit it. Presence before contents (rule 8): never a value |

This part is never empty by omission. If nothing is missing, it says so in
`nothing_missing`.

## 6. Suggested channels

| Field | Meaning |
| --- | --- |
| `pairings` | barrier to channel, from the declared pairing table in `seeds/` |
| `label` | always "standard outreach practice, not a finding" |
| `source` | the pairing table's file and version |

Until the pairing table is written (P-2), this part ships present and empty,
`pairings: []` with `empty_because` saying so (D-285).

## Rules

- Every part is present for every place, even when empty, and an empty part
  says why (tests/test_place_profile.py: all six parts, always).
- Every barrier value carries `households_behind` (Sprint 06 test).
- Every verdict against a `universal` threshold carries `left_out` (Sprint 06 test).
- No threshold appears without its kind and its source (Sprint 06 test).
- A borrowed value names the place it belongs to, and no verdict is given on it (Sprint 06 test).
- Every uncertainty states its confidence (Sprint 06 test).
- A tribal area's profile carries its context note (Sprint 06 test).
- No profile carries a standing, percentile or z-score (D-104).
- No value from a receipt the gate withholds at public enters the file, and
  the receipt never lists one as an input (D-284).
- The profile is enumerable: the state, 16 counties, 529 towns, 151 House and
  35 Senate districts, and the tribal areas as a qualified Census view. Every
  one is built; none is built on demand.
- Every other level a plot's graph holds is profiled after these (Maine's 923
  MEGIS civil divisions), as groundwork for later analyses, each saying so in
  `place.level_note` (D-292).
- A long build reports its progress (tests/test_place_profile.py).

## Decided in review

| ID | Decision |
| --- | --- |
| P-4 | Profiles show values only; standings stay in their experiments' own products (D-104) |
| D-197 | The profile composes read_place rather than extending PlaceReading |
| D-198 | Verdicts are margin-aware; ratio margins come from their own preparation step, derive_margins, joined on measurement_id |
| D-199 | Three kinds of threshold: universal, trigger, none (P-1's shape) |
| D-200 | Each barrier is a family of registered indicators, each a layer at its grain, with a status instead of "not yet measurable" |
| D-258 | Ratio margins are derived inside derive_indicator, never a second values artifact; supersedes D-198's own step |
| D-270 | The standard is its own seed and schema, generic; barrier membership lives there; the registry keeps role |
| D-271 | P-1 row by row, and P-5: each barrier's sides and sources |
| D-272 | A universal side is judged on its count against zero; meets is unreachable for an estimate |
| D-273 | Trigger verdicts per group, margin-aware; a published determination as_published |
| D-274 | Profiles by a canopy command, one place_profile artifact, tier public; the allow record at the door |
| D-275 | loam views over literacy_estimates and section203_records |
| D-276 | borrowed_from is a list, shares of residents, no verdict or left_out on a borrowed value |
| D-277 | Confidence from the declared uncertainty, held once; a row's own wins |
| D-278 | left_out means the people short of a universal line, everywhere |
| D-280 | Part 1's population is the 2020 Census count every per_1000 divides by |
| D-282 | Part 4 pairs one measure only |
| D-284 | The gate first: a withheld receipt's values never enter; its refusal does |
| D-285 | Part 6 ships present and empty until P-2 |
| D-286 | Households are the ACS's, the digital count's denominator |
| D-287 | A small sample travels beside a verdict; the margin decides |
| D-288 | Part 4 subtracts two percents of one measure; other units are shown apart |
| D-289 | A trigger is judged over every value its margins allow, never only its two ends |
| D-290 | Maine's town and county boundaries take maine_geolibrary_public: 5 M.R.S.A. sections 2004 and 2005, source credited; the section 1995 reading is Kalli's |
| D-291 | A count's receipt names the notes its rows carry, so rule 9 binds exactly those |
| D-292 | Levels outside this contract are profiled after its own, as groundwork, and say so |
| D-293 | The places and edges receipts are inputs of every profile; when withheld, the whole file cannot leave, said plainly |

## Open

| ID | Question | Decided in |
| --- | --- | --- |
| P-2 | The pairing table's contents | after delivery (D-285) |
| P-3 | What counts as a free outlet (for "behind a paywall") | Sprint 06 |
| P-6 | The FCC availability benchmark's values, with step 7b; 100/20 terrestrial is declared (D-271) | if the window allows |
| P-8 | Section 203 rows on Wabanaki places: the nations' to decide, under CARE and OCAP | never a deadline |
| GAPS-1 | Part 5's gaps in the method authors' own words, from readiness and possibility | after delivery |

Closed: P-1 and P-5 (D-271), P-7 (D-265), P-9 (session 13's read).
