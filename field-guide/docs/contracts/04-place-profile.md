# Contract 4 ~ The place profile

**Status:** draft 0.3, 2026-11-11 (D-197 to D-200, after Sprint 05 and NAME-4's
change 1). **Owner:** Kalli. **Built in:** Sprint 06 (`canopy/wonder/profile.py`).
**Read by:** the explorer (Sprint 09), district briefs (11), the outreach
planner and Compare (12), the open data hub (13). **Rests on:** MP-73 (the
explorer is the front door; briefs follow from the same profile), MP-74
(barriers judged against an absolute standard), MP-75 (towns get values,
never standings), Contracts 1 and 3, D-104, D-183, D-185, D-186.

One structured object per place, which every product renders. Products cannot
disagree about a place, because none of them computes it: they all read the
profile.

The profile is a document assembled from measurements (D-197).
`build_profile(loam, authority, code)` calls `read_place` (canopy/wonder/
place.py) and wraps its `PlaceReading`; carriers, disagreements, gaps, gate
refusals and channels come from their own readers. `read_place` stays one
measurement and is not grown into the profile (D-184). The profile decides how
to read each level: a district or county reads its towns, the state reads its
counties, a town has no parts.

## 0. Header

| Field | Meaning |
| --- | --- |
| `place` | the place's key, `(authority, code)`, and its `level`, `name`, `vintage` (Contract 3) |
| `flags`, `context_note` | from the places table, shown first, never hidden behind a click |
| `built_at`, `built_by` | when, and which profile version built it |
| `gate` | the allow record under which the profile left (Contract 1) |

## 1. Who is represented

| Field | Meaning |
| --- | --- |
| `population`, `households` | each with its release, margin and `published_by` |
| `needs` | older adults living alone, disability, poverty, rent burden: values with margins, never judged against a threshold here |
| `legislators` | for a district, who represents it; for a town, the legislators of every district it touches, with shares. Until the 133rd's rosters are acquired (on or after 2026-12-02), this says so, by name of the missing holding |
| `inside` | places this one contains (`contains` edges) |
| `overlapping` | places this one overlaps, each with both weights (`overlaps` edges, D-121) |

## 2. Barriers

Organized by the Information Futures Lab's barriers (MP-74), each measured by
one or more registered indicators (D-200). Every indicator is a layer at its
own grain: something to compute with and to map, never a placeholder.

### 2a. One entry per barrier

| Field | Meaning |
| --- | --- |
| `barrier` | the IFL barrier, in its words: not in the right language, requires digital access, at the wrong literacy level, lacking cultural cues, behind a paywall, outdated, not where people look, not from a trusted source |
| `indicators` | the entries of 2b |
| `threshold` | the barrier's threshold, of one kind (D-199): `universal`, `trigger` or `none`, with `statement` in plain words and its `source`; never a number without both |

### 2b. One entry per indicator

| Field | Meaning |
| --- | --- |
| `indicator`, `measures` | the registry id and what it measures |
| `status` | `acquired`, `acquirable` (its source named), `needs_our_model` or `needs_consent` (Sprint 16). Anything but `acquired` also appears in part 5 |
| `estimate_kind` | `survey` (ACS), `model_based` (for example PIAAC small-area estimates), `administrative` (counts of carriers), `inventory` (an outlet attribute), `published_determination` (for example a Census section 203 determination), `computed` (from other indicators, its method named) |
| `value`, `unit` | at full precision |
| `grain` | the level the value is published at |
| `borrowed_from` | when the value is a coarser place's (a county's literacy estimate on a town's profile): that place's key. A borrowed value is always labelled as the other place's, never stated as this place's own |
| `uncertainty` | the margin or interval, its `confidence` (the ACS publishes 90%; a model states its own), and its `method`: `published`, `derived` (by derive_margins, with the formula's citation, D-198), `credible_interval`, or why there is none (`open_ended`, `absent`) |
| `bound` | for an open-ended median, the bound in words; then `value` is not a measurement |
| `households_behind` | the count of households (or persons) in the value's denominator, from the same release. A rate over 14 households is a different fact from a rate over 14 000, and the profile always says which |
| `left_out` | for a `universal` threshold: how many households (or persons) fall short of it, from this place's own estimate and release, with its uncertainty. Never allocated along edges here; allocation is the outreach planner's (Sprint 12, COUNT-1) |
| `crosses` | for a `trigger` threshold: what crosses it (each language over the DOJ safe harbor, each section 203 coverage), with the count behind each |
| `verdict` | see the rule below |
| `towns` | for a county or district: the towns wholly here and their range, the split towns named one by one with how much of each is here, and the firm range (D-183, D-185), with place.py's range statement |
| `published_by`, `vintage`, `method` | who published it (D-186), which release, which run produced it (`lineage.run`) |

### The verdict rule (D-198)

A verdict compares the place's own value with the threshold, at the
uncertainty's stated confidence:

- `meets`: the value, less its margin, clears the threshold
- `below`: the value, plus its margin, falls short
- `within_margin`: the threshold lies inside the margin, so the data cannot
  say which side the place is on
- `cannot_judge`: with its reason, in plain words: no uncertainty to judge
  with, a small sample under the declared rule, an unchecked statistical
  area, an open-ended bound, a borrowed value
- `no_threshold`: the barrier's threshold is of kind `none`

A town range is never judged, only the place's own value. A small town's
wide margin decides by itself what can be judged; no rule singles towns out.

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
| `values` | each publisher's value, with its vintage |
| `difference` | the difference, in the measure's unit |
| `reason` | why, if known; otherwise `unknown`, never omitted |

Both values are shown. The profile never picks one.

## 5. What cannot be answered

| Field | Meaning |
| --- | --- |
| `gaps` | each missing holding with the method author's own words on what its absence costs (`readiness`, `possibility`) |
| `not_acquired` | every indicator of part 2 whose status is not `acquired`: its status, its named source, and what acquiring it needs |
| `cannot_judge` | every verdict of `cannot_judge`, with its reason |
| `refusals` | every refusal record the gate returned for this place's artifacts (Contract 1, rule 7): type, tier, ancestor, reason, what would admit it |

This part is never empty by omission. If nothing is missing, it says so.

## 6. Suggested channels

| Field | Meaning |
| --- | --- |
| `pairings` | barrier to channel, from the declared pairing table in `seeds/` |
| `label` | always "standard outreach practice, not a finding" |
| `source` | the pairing table's file and version |

## Rules

- Every part is present for every place, even when empty, and an empty part
  says why (Sprint 06 test: all six parts, always).
- Every barrier value carries `households_behind` (Sprint 06 test).
- Every verdict against a `universal` threshold carries `left_out` (Sprint 06 test).
- No threshold appears without its kind and its source (Sprint 06 test).
- A borrowed value names the place it belongs to, and no verdict is given on it (Sprint 06 test).
- Every uncertainty states its confidence (Sprint 06 test).
- A tribal area's profile carries its context note (Sprint 06 test).
- No profile carries a standing, percentile or z-score (D-104).
- The profile is enumerable: the state, 16 counties, 529 towns, 151 House and
  35 Senate districts, and the tribal areas as a qualified Census view. Every
  one is built; none is built on demand.

## Decided in review

| ID | Decision |
| --- | --- |
| P-4 | Profiles show values only; standings stay in their experiments' own products (D-104) |
| D-197 | The profile composes read_place rather than extending PlaceReading |
| D-198 | Verdicts are margin-aware; ratio margins come from their own preparation step, derive_margins, joined on measurement_id |
| D-199 | Three kinds of threshold: universal, trigger, none (P-1's shape) |
| D-200 | Each barrier is a family of registered indicators, each a layer at its grain, with a status instead of "not yet measurable" |

## Open

| ID | Question | Decided in |
| --- | --- | --- |
| P-1 | Each barrier's threshold and source, row by row (the shape is D-199) | Sprint 06 |
| P-2 | The pairing table's contents | Sprint 06 |
| P-3 | What counts as a free outlet (for "behind a paywall") | Sprint 06 |
| P-5 | Whether the language barrier also has a `universal` side counting every limited-English person beside the trigger list (lean: yes, kept apart) | Sprint 06 |
| P-6 | The FCC availability benchmark, verified before it enters a seed | Sprint 06 |
| P-7 | Whether county PIAAC estimates exist for the 2023 cycle; until then, the 2012/14/17 pooled estimates, with their vintage said | Sprint 06 |
| P-8 | Section 203 rows on Wabanaki places, with Person 3 | before release |
| P-9 | Whether the outlet inventory carries language of publication, publishing frequency and paywall status; read the files before relying on any | Sprint 06 |
