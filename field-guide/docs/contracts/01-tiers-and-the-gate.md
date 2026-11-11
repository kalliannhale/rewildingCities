# Contract 1 ~ Tiers and the one exposure gate

**Status:** draft 0.4, 2026-11-11, for review (E-1 and E-2 decided, D-101, D-102; E-7, rule 11's records live in provenance, D-143). **Owner:** Kalli. **Built in:**
Sprint 03 (`canopy/expose/gate.py`, the publish-route teammate; tier
declarations, Person 3). **Read by:** everyone who writes an exit.
**Rests on:** MP-67 (publishing is opt-in), MP-72 (Wabanaki places as a
qualified Census view), D-31 (CII's terms), D-98 (preparations).

The system may compute with anything. What leaves it is governed here, by one
function, at every exit. There is no second implementation of tier logic
anywhere: an exit that needs a decision calls the gate.

## 1. What counts as leaving

An artifact leaves when it is written anywhere outside the plot's own machine
or shown to anyone who is not running the plot. Today and planned:

| Exit | Where | Status |
| --- | --- | --- |
| `map --publish` | `canopy/cli/map.py` to ArcGIS Online | built (MP-67); gate wired in Sprint 03 |
| The publish door | `canopy/expose/publish.py` | Sprint 08 |
| The canonical write | `canopy/aws/s3.py` (Contract 2) | Sprint 07 |
| The explorer's layers and profiles | read from canonical files | Sprints 06, 09 |
| Exports from the community kit | the kit's local page | Sprint 10 |

Writing to the plot's own `.data/`, `.envelopes/` and `harvest/` is not
leaving. Committing to git is leaving, which is why harvests are out of git
(D-94).

## 2. The tier

Every semantic type declares `resolution_tier` in `seeds/schemas/`. The set is
closed:

| Tier | May leave as |
| --- | --- |
| `public` | anything, subject to the other rules |
| `aggregate-only` | counts or rates over a declared unit, never named or located members |
| `custom` | only with a consent record for this plot and this target (section 5) |
| `excluded` | nothing; the gate may still say the data exists and is withheld (rule 8) |

**The field the gate reads is `resolution_tier`.** `Vocabulary.get_tier()`
reads a different field, `tier` (the loam maturity: tended, gathered), which
no type declares, and nothing reads `resolution_tier` today (GATE-1). The gate
gets its own reader; the two meanings of "tier" are never read by one
function.

At 2026-11-10, 16 of 57 semantic types declare `resolution_tier`. The other
41 fail closed until Person 3 declares them.

## 3. The eleven rules

From the infrastructure plan's Part 3, with three additions from the fusion.

| # | Rule |
| --- | --- |
| 1 | Tier values are a closed set: `public`, `aggregate-only`, `custom`, `excluded`. Any other value is an error, never a guess |
| 2 | An undeclared type fails closed: it does not leave |
| 3 | Every tier in the lineage binds. The artifact's own type and every ancestor's tier must each be satisfied at once, so an artifact descended from an `aggregate-only` and a `custom` ancestor leaves only as counts and only with consent. Any `excluded` ancestor stops everything (D-101) |
| 4 | No lineage, no publication. Lineage means a recorded kind, run, method and choices. A preparation's lineage names no curiosity and is complete. An experiment with an empty curiosity passes, but its missing question travels with it as a caveat in the allow record and in every product that shows it (D-102) |
| 5 | `aggregate-only` leaves only as counts over a declared unit, never as named or located members |
| 6 | `custom` leaves only with a named consent record for this plot and this target, cited in provenance |
| 7 | Refusals are content: every refusal names the type, the tier, the ancestor that set it, and what would let it through |
| 8 | Presence before contents: the gate may say that a kind of data exists and is withheld, and why, without showing it |
| 9 | Required context: a type may declare a note that must travel with it; publication without the note is refused |
| 10 | License: redistribution must be permitted at the target's sharing level |
| 11 | Every step that changes what leaves (a unit held out, a field dropped, a rename, rounding, a format change, simplification, clipping) is recorded in provenance, in the entry of the step that made it, and every descendant carries the record (D-143) |

## 4. What the gate is given, and what it returns

**Given:** the artifact's envelope (with its lineage and provenance chain), the
vocabulary, the plot's consent records, the datasets' declared licenses, and
the target with its sharing level (`private`, `organization`, `public`).

**Returns:** either an *allow record* or a *refusal record*. Both are written
into the outgoing artifact's envelope, so an allowed artifact can always say
why it was allowed.

### The allow record

| Field | Meaning |
| --- | --- |
| `decision` | `allow` |
| `target`, `sharing_level` | where it went, at what level |
| `tiers` | every tier that bound the artifact, each with the ancestor that set it (rule 3) |
| `consent` | the consent record cited, if rule 6 applied |
| `license` | the license term checked under rule 10 |
| `context_notes` | the note ids carried under rule 9 |
| `caveats` | what the artifact lacks but may leave without, in plain words; today, an experiment that names no curiosity (rule 4) |
| `publication_steps` | every rule 11 record in the artifact's provenance chain, in chain order, each once, each with the `lineage_branch` it was found through (D-143) |
| `gate_version`, `checked_at` | which gate decided, and when |

### The refusal record

| Field | Meaning |
| --- | --- |
| `decision` | `refuse` |
| `rule` | the rule number that refused |
| `semantic_type`, `tier` | what was refused, under which tier |
| `ancestor` | the envelope or dataset in the lineage that set that tier; if several tiers refuse, one refusal record each |
| `target`, `sharing_level` | where it was headed |
| `reason` | in plain words, written for the person who asked |
| `would_admit` | what would let it through: a declaration, a consent record, an aggregation, a note, a license |
| `gate_version`, `checked_at` | which gate decided, and when |

A refusal is shown wherever the artifact would have been: in `wonder`, in a
profile's "what cannot be answered" (Contract 4), and in the CLI.

## 5. The consent record

One record per plot, target and consented subject. It lets a `custom` holding
through, and nothing else.

| Field | Meaning |
| --- | --- |
| `id` | stable id, cited in provenance |
| `plot`, `target`, `sharing_level` | what it opens, exactly; no wildcard |
| `covers` | the semantic types or datasets it covers |
| `granted_by` | the named person or body that consented |
| `on_behalf_of` | the community or nation the information describes |
| `granted_on`, `expires_on` | dates; no expiry means it must be renewed by review, not assumed |
| `terms` | the conditions, in the grantor's words or a link to them |
| `status` | `active` or `withdrawn`; a withdrawn record admits nothing from the day it is withdrawn |

Sovereign and relational information enters only on the terms of the people it
describes. A consent record is how those terms are kept; it is never inferred.

## 6. The context note

A semantic type may declare `required_context`: one or more notes, each with an
`id` and its text. An outgoing artifact of that type carries the note ids in
`metadata.context_notes`, and the text travels with the artifact. Missing is a
refusal under rule 9.

The Census tribal-area type and reservation subdivisions declare one (Sprint
04): the boundary is the Census Bureau's, small estimates are uncertain, and
the nations' own data would describe these places on their own terms.

## 7. The license

Each dataset in a manifest declares its license from a short controlled list,
so the gate can read it (Open, E-4). An undeclared license fails closed at the
`public` level, as an undeclared tier does. CII's published file has no
published terms yet (CII-19), so anything carrying CII's own values is refused
at `public` until it does.

## 8. The publication record (rule 11)

| Field | Meaning |
| --- | --- |
| `step` | `held_out`, `field_dropped`, `renamed`, `rounded`, `format_changed`, `simplified`, `clipped` |
| `detail` | what exactly: which units, which field, to what precision, which tolerance |
| `count` | how many units or fields it touched |
| `by` | the primitive or the gate |
| `at` | when |

**Where the record lives (D-143).** In the provenance entry of the step that
made it, as that entry's `publication` list, empty when the step changed
nothing. A primitive prints `step`, `detail` and `count` in its stdout
metadata; the envelope builder lifts them into its provenance entry and stamps
`by` (the entry's primitive) and `at` (the entry's timestamp). A primitive that
stamps `by` or `at` itself is refused, never corrected, because a record that
misnames its step would travel to every descendant. The step names are a
closed set enforced by `provenance.schema.json` when the receipt is written,
so a misspelled step is refused there, as a misspelled tier is under rule 1.

The record is inherited with its entry, so a clip made by a preparation reaches
every map drawn from it, and no exit has to know what happened upstream. The
gate gathers every record in the chain into its allow record, each once
(keyed by `by`, `at`, `step` and `detail`, since an ancestor reached through two
inputs appears twice in the chain). `metadata.publication` is never read or
written. `by: the gate` is for a change the exit itself makes, recorded there.

## Decided in review

| ID | Decision |
| --- | --- |
| E-1 | Rule 3 is a conjunction, not a ranking: `aggregate-only` limits form and `custom` limits permission, so neither outranks the other and both bind (D-101) |
| E-2 | An experiment with an empty curiosity passes rule 4: its method, choices and run make it traceable, and its missing question is carried as a caveat rather than blocking it (D-102) |
| E-7 | Rule 11's records live in the provenance entry of the step that made them; the builder stamps `by` and `at`; the schema holds the closed set; the gate gathers them through the chain (D-143) |

## Open

| ID | Question | Decided in |
| --- | --- | --- |
| E-3 | Where consent records live: a folder in each plot, or a block in the manifest | Sprint 03 |
| E-4 | How licenses are declared: free text checked by a person, or a short controlled list the gate can read. This contract assumes the list | Sprint 03 |
| E-5 | The gate's own reader for `resolution_tier`, and what becomes of `get_tier()` (GATE-1) | Sprint 03 |
| E-6 | The empty-curiosity warning is printed by `validate()` but not written into receipts, so today it would not reach the gate. Write it into the envelope's warnings when the receipt is written, so the caveat in rule 4 has something to carry | Sprint 03 |
