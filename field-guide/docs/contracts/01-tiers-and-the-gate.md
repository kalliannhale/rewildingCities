# Contract 1 ~ Tiers and the one exposure gate

**Status:** draft 0.8, 2026-11-17, for review (0.8: a joined copy's second parent binds rule 10 as its first does, D-342, and the door checks notes and credits against both parents' allow records, D-343; 0.7: the publish door as the exit to ArcGIS, D-326 to D-330, and E-3 to E-5 recorded as built, D-115, D-116, GATE-1; 0.6: the canonical write as an exit, D-314, D-315; E-1 and E-2 decided, D-101, D-102; E-7, rule 11's records live in provenance, D-143; E-8, notes bind by row, D-156, D-157). **Owner:** Kalli. **Built in:**
Sprint 03 (`canopy/expose/gate.py`, the publish-route teammate; tier
declarations, Person 3). **Read by:** everyone who writes an exit.
**Rests on:** MP-67 (publishing is opt-in; its `map --publish` is superseded by the publish door, D-326), MP-72 (Wabanaki places as a
qualified Census view), D-31 (CII's terms), D-98 (preparations).

The system may compute with anything. What leaves it is governed here, by one
function, at every exit. There is no second implementation of tier logic
anywhere: an exit that needs a decision calls the gate.

## 1. What counts as leaving

An artifact leaves when it is written anywhere outside the plot's own machine
or shown to anyone who is not running the plot. Today and planned:

| Exit | Where | Status |
| --- | --- | --- |
| `map --publish` | `canopy/cli/map.py` | retired: `map` draws locally and `--publish` names the door (D-326) |
| The publish door | `canopy/expose/publish.py`, run as `python -m canopy.cli publish`, to each target a plot declares | built in Sprint 08 (zip 8a, D-326 to D-330) |
| The canonical write | `canopy/aws/s3.py` (Contract 2), target `canonical` at `public` | built in Sprint 07 (zip 7b, D-315) |
| The explorer's layers and profiles | read from canonical files | Sprints 06, 09 |
| Exports from the community kit | the kit's local page | Sprint 10 |

A layer an ArcGIS item reads by URL left at the canonical write, which judged
it at `public`: an item's sharing decides who finds the map, never who can read
the data. So at the door the gate judges what can differ by target: the
license at the item's sharing level (rule 10), consent named for that target
(rule 6), and the notes that must travel (rule 9), each of whose text must
match the canonical allow record's, so a map never says what the bucket does
not (D-328).

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
| 9 | Required context: a note must travel with what it describes. An artifact carries the notes its own type requires and the notes its rows carry; one that does not say what its rows carry is bound by every note in its lineage. Publication without a bound note, or with a note that has no text, is refused (D-156, D-157) |
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
| `context_scope` | `rows` if the artifact said what its rows carry, `lineage` if it did not (D-156) |
| `context_text` | each carried note's text, by id, so the text leaves with the artifact (D-157) |
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

**One home for every note's text (D-157).** Every note lives in
`seeds/notes/notes.yml`, with an `id`, its `text`, and optionally
`when_merged`, the note a place carries instead when it holds this note's
place in whole or part. A semantic type requires a note by id alone, in its
`required_context`. The notes file is loaded loudly: an id declared twice, a
note without text, a `when_merged` naming no note, or a type requiring an id
the file lacks, is an error when the gate's context is loaded, before any
artifact is judged.

**What binds an artifact (D-156).** Two sources, and the artifact says which:

| The artifact's metadata | Notes it must carry |
| --- | --- |
| has `row_context_notes` (a list, empty included) | its own type's required notes, and every note in `row_context_notes` |
| has no `row_context_notes` | its own type's required notes, and every note any type in its lineage requires |

`row_context_notes` is written by the primitive that wrote the rows, which is
the only step that knows what they hold; the gate never opens a data file. An
empty list is a claim: no row here carries a note. A missing field is silence,
and silence binds the whole lineage, so a primitive that has not learned to
list its rows' notes over-notes and never fails open. `context_notes` and
`row_context_notes` must each be a list of ids; a bare string is refused,
because a string would seem to carry any note it contains (C-36).

**The notes in use (Sprint 04).** `census_tribal_area` on every Census tribal
area and reservation subdivision: the boundary is the Census Bureau's, small
estimates are uncertain, and the nations' own data would describe these places
on their own terms. `contains_census_tribal_area`, its merged form, on every
other place that holds any tribal block, at every level (D-158).
`census_tribal_places` on the places table itself (D-149). A display note,
`penobscot_main_stem_waters`, on the Penobscot Reservation's outlines, because
the display leaves out water the Census boundary includes (D-159, PENOB-1).

## 7. The license

Each dataset in a manifest declares its license from a short controlled list,
so the gate can read it (Open, E-4). An undeclared license fails closed at the
`public` level, as an undeclared tier does. CII's published file has no
published terms yet (CII-19), so anything carrying CII's own values is refused
at `public` until it does.

### A copy with two parents (D-342, zip 8b)

A joined display copy (Contract 2, section 4a) is a table drawn on an outline.
Its `metadata.lineage` is the table's; its `metadata.joined_to.lineage` is the
outline's, and rule 10 reads both, so the outline's datasets (the boundaries
and their attribution) bind as the table's do. Both provenance chains travel,
under the branches `table` and `outline`, so rules 1 to 6 bind every type in
either. Rule 9 reads the copy's own `row_context_notes`: the notes its drawn
places carry, never the notes of a national table's other rows. Nothing
without `joined_to` is judged differently, so the gate's version is unchanged
and no allow record moves.

The door holds a map to both parents: every note the gate binds must read in
one of the two canonical allow records as it reads in seeds/notes, the two may
not word one note differently, the item's credits come from both, and a
dataset the gate names at the target that neither record holds is refused
(D-343).

## 8. The publication record (rule 11)

| Field | Meaning |
| --- | --- |
| `step` | `held_out`, `field_dropped`, `renamed`, `rounded`, `format_changed`, `simplified`, `clipped`, `joined` (columns added from another table, D-339), `marked` (a place drawn as one point on its surface, D-340) |
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
written. A change an exit itself makes is recorded by that exit, `by` naming
it: the gate, or the canonical write, which records its GeoJSON to GeoParquet
conversion in the version's allow record (D-314, D-320).

## Decided in review

| ID | Decision |
| --- | --- |
| E-1 | Rule 3 is a conjunction, not a ranking: `aggregate-only` limits form and `custom` limits permission, so neither outranks the other and both bind (D-101) |
| E-2 | An experiment with an empty curiosity passes rule 4: its method, choices and run make it traceable, and its missing question is carried as a caveat rather than blocking it (D-102) |
| E-7 | Rule 11's records live in the provenance entry of the step that made them; the builder stamps `by` and `at`; the schema holds the closed set; the gate gathers them through the chain (D-143) |
| E-3 | Consent records live one file each in `plots/<plot>/consent/` (D-115) |
| E-4 | Licenses are a short controlled list in `seeds/licenses/licenses.yml` that the gate reads; an unverified term permits `private` only (D-116) |
| E-5 | The gate reads `resolution_tier` through its own reader, apart from `get_tier()` (GATE-1) |
| E-8 | Rule 9 binds by row when the artifact lists `row_context_notes`, and by lineage when it does not; every note's text lives in `seeds/notes/notes.yml` and leaves in the allow record (D-156, D-157) |

## Open

| ID | Question | Decided in |
| --- | --- | --- |
| E-6 | The empty-curiosity warning is printed by `validate()` but not written into receipts, so today it would not reach the gate. Write it into the envelope's warnings when the receipt is written, so the caveat in rule 4 has something to carry | Sprint 03 |
