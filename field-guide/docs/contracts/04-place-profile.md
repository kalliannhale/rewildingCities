# Contract 4 ~ The place profile

**Status:** draft 0.2, 2026-11-10 (P-4 decided, D-104). **Owner:** Kalli. **Built in:**
Sprint 06 (`canopy/wonder/profile.py`). **Read by:** the explorer (Sprint 09),
district briefs (11), the outreach planner and Compare (12), the open data hub
(13). **Rests on:** MP-73 (the explorer is the front door; briefs follow from
the same profile), MP-74 (barriers judged against an absolute standard),
MP-75 (towns get values, never standings), Contracts 1 and 3.

One structured object per place, which every product renders. Products cannot
disagree about a place, because none of them computes it: they all read the
profile. The profile is a `PlotReading` scoped to one place, with geography
and channels added.

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
| `population`, `households` | each with its ACS release and margin |
| `legislators` | for a district, who represents it; for a town, the legislators of every district it touches, with shares |
| `inside` | places this one contains (`contains` edges) |
| `overlapping` | places this one overlaps, each with its weight (`overlaps` edges) |

## 2. Barriers

One entry per barrier indicator:

| Field | Meaning |
| --- | --- |
| `indicator`, `measures` | the registry id and what it measures |
| `value`, `unit` | the place's value, at full precision |
| `moe`, `moe_status` | the margin, or why there is none (`not_derived`, `open_ended`, `controlled`) |
| `bound` | for an open-ended median, the bound in words; then `value` is not a measurement |
| `households_behind` | **the count of households (or persons) in the value's denominator, from the same release.** A rate over 14 households is a different fact from a rate over 14 000, and the profile always says which |
| `towns_range` | for a county or district: `min`, `max` and `n_towns` across the towns that touch it (Contract 3, rule 3) |
| `threshold` | the absolute threshold from the standard, with its `source`, stated in plain words; or null where the standard has none (MP-74) |
| `against_threshold` | `meets`, `below`, or `no_threshold` |
| `authority`, `vintage`, `method` | who published it, which release, which preparation produced it (`lineage.run`) |

**A profile shows values, never standings (D-104).** Towns have none
(MP-75), and a county's standing stays in its experiment's own products, such
as the standings maps. A barrier is judged here against the absolute standard
(MP-74); a relative rank beside an absolute threshold would invite a reader to
mix them, and the rank is the easier number to read.

## 3. Carriers

One entry per carrier type (libraries, outlets, town offices, schools, health
centers):

| Field | Meaning |
| --- | --- |
| `type` | the carrier's semantic type |
| `count` | points `located_in` this place |
| `per_1000` | per 1 000 people, with the population it divided by |
| `source`, `vintage` | where the points came from |

## 4. Where sources disagree

One entry per measure that more than one authority publishes:

| Field | Meaning |
| --- | --- |
| `measures` | the shared measure (as `registry.measuring()` returns it) |
| `values` | each authority's value, with its vintage |
| `difference` | the difference, in the measure's unit |
| `reason` | why, if known; otherwise `unknown`, never omitted |

Both values are shown. The profile never picks one.

## 5. What cannot be answered

| Field | Meaning |
| --- | --- |
| `gaps` | each missing holding with the method author's own words on what its absence costs (`readiness`, `possibility`) |
| `refusals` | every refusal record the gate returned for this place's artifacts (Contract 1, rule 7): type, tier, ancestor, reason, what would admit it |
| `not_yet_measurable` | barriers the standard names but nothing measures yet: lacking cultural cues, at the wrong literacy level |

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
- No threshold appears without its source (Sprint 06 test).
- A tribal area's profile carries its context note (Sprint 06 test).
- No profile carries a standing, percentile or z-score (D-104).
- The profile is enumerable: the state, 16 counties, 529 towns, 151 House and
  35 Senate districts, and the tribal areas as a qualified Census view. Every
  one is built; none is built on demand.

## Decided in review

| ID | Decision |
| --- | --- |
| P-4 | Profiles show values only; standings stay in their experiments' own products (D-104) |

## Open

| ID | Question | Decided in |
| --- | --- | --- |
| P-1 | Each threshold, and its source | Sprint 06 |
| P-2 | The pairing table's contents | Sprint 06 |
| P-3 | What counts as a free outlet (for "behind a paywall") | Sprint 06 |
