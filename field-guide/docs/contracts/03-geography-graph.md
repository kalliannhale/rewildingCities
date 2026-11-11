# Contract 3 ~ The geography graph

**Status:** draft 0.2, 2026-11-10 (G-3 decided, D-103). **Owner:**
Kalli. **Built in:** Sprint 04 (the tables, by preparations), Sprint 05 (loam
learns them). **Read by:** the place profile (Contract 4), the grove's
cross-plot catalog, every district product. **Rests on:** MP-75 (towns get
values, never standings), MP-76 (split towns shown in every district they
touch), MP-72 (Wabanaki places as a qualified Census view), MP-80 (the grove
is a weighted graph), D-19 (rows keyed by authority and code), D-27 (medians
never combine).

Maine's places do not form a tree. A town can sit in two House districts, a
district can cross a county line, and a Census tribal area overlaps towns that
are not inside it. So the geography is stored as a graph: places, and edges
between them. Every plot's loam bed holds its part of the graph; the grove is
the union of every bed.

## 1. Places

One row per place, at every level. The key is `(authority, code)`, as D-19
already keys indicator rows, so a value and its place join by derivation,
never by name.

| Field | Type | Meaning |
| --- | --- | --- |
| `authority` | text | who assigns the code: `us_census_geoid`, `megis` |
| `code` | text | the code as that authority writes it, leading zeros kept: `23005`, `2300560825` |
| `level` | text | `state`, `county`, `cousub`, `sldl` (Maine House), `sldu` (Maine Senate), `aiannh` (Census tribal area), `megis_division` |
| `vintage` | text | the boundary year; it must match the ACS vintage it is joined to |
| `name` | text | as the authority publishes it |
| `flags` | list of text | from the list below; empty, never null |
| `context_note` | text or null | the note Contract 1, rule 9, requires, where one applies |

**Flags:** Census functional status (`active`, `statistical`, `fictitious`,
`nonfunctioning`), `plantation`, `unorganized_territory`, `zero_households`,
`census_construct`, `baxter_state_park`. A flag says what a place is, so a
reader never mistakes a township with no government for a town with no news.

**Counts for Maine** (Sprint 04 builds and tests them): 1 state, 16 counties,
529 county subdivisions, 151 House districts, 35 Senate districts, the Census
tribal areas inventoried from the AIANNH layer (never from a list of names),
and the 924 MEGIS civil divisions.

## 2. Edges

One row per relationship. Each end is a place key, so an edge has four key
columns.

| Field | Type | Meaning |
| --- | --- | --- |
| `from_authority`, `from_code` | text | the containing or overlapping place; for `located_in`, the point's layer (its dataset id) and its feature id |
| `to_authority`, `to_code` | text | the other place |
| `kind` | text | `contains`, `overlaps` or `located_in` |
| `weight` | number | see below |
| `source` | text | the file or method the edge came from |
| `vintage` | text | the vintage of that source |

| Kind | Means | Weight |
| --- | --- | --- |
| `contains` | clean nesting: state to county, county to town | 1 |
| `overlaps` | partial: town to district, town to tribal area | the share of the town's population inside the other place, from Census block assignments (Open, G-1) |
| `located_in` | a point (a library, an outlet) to every area it falls in | 1 |

A point inside two districts has a `located_in` edge to each, so it counts in
both (Sprint 06 test).

**Points are not places (D-103).** A library or an outlet is named only inside
its `located_in` edges, by layer and feature id; it never has a row in
`places`. `places` holds the areas a profile can be built for, exactly the
list Contract 4 enumerates. So the ends of every `contains` and `overlaps`
edge are rows in `places`, and the `to` end of every `located_in` edge is
one; the `from` end of a `located_in` edge is a feature in a declared layer.

## 3. Invariants

These are tested where the tables are built (Sprint 04):

- Every town has exactly one `contains` edge from its county.
- A town's `overlaps` weights across one chamber's districts sum to 1.
- Every district touches at least one town.
- Both ends of every `contains` and `overlaps` edge, and the `to` end of every
  `located_in` edge, exist in `places`; the `from` end of every `located_in`
  edge exists in its declared layer.
- Boundary and estimate vintages match, place by place.
- Every reservation subdivision and tribal area carries its context note.

## 4. The three rules

1. **Districts come from the ACS directly.** A district's value is the ACS's
   own legislative-district estimate, never a sum or average of its towns.
2. **Medians are never combined** across places (D-27). A median exists only
   where the publisher computed it.
3. **A larger place's value is shown with its towns' range.** A district or
   county value always travels with the minimum and maximum across the towns
   that touch it, and how many towns that is, so one number never hides the
   places inside it.

Split towns appear in every district they touch, with their share (MP-76).
Towns carry values and never standings (MP-75).

## 5. Storage

Until the grove exists, the graph lives as two Parquet tables in each plot,
`places` and `edges`, each written by a preparation from `soil/` primitives
(D-98), with an envelope. A table nobody wrote by a preparation is not part of
the graph. Loam reads them as holdings keyed by place (Sprint 05); the grove's
catalog is their union across plots.

## Open

| ID | Question | Decided in |
| --- | --- | --- |
| G-1 | The weight basis for `overlaps`: population, households, or housing units | Sprint 04 |
| G-2 | How MEGIS civil divisions join Census subdivisions where the two disagree | Sprint 04 |

## Decided in review

| ID | Decision |
| --- | --- |
| G-3 | Points stay out of `places`; they are named by layer and feature id inside their `located_in` edges (D-103) |

## Review

| Reviewer | Date | Result |
| --- | --- | --- |
| Kalli, author, acting as grove teammate | 2026-11-10 | Reviewed; G-3 decided. Reviewed by its author, not by a second person |
