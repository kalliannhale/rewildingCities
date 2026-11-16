# Contract 2 ~ Canonical objects

**Status:** draft 0.2, 2026-11-16, for review (0.1, 2026-11-10). **Owner:**
Kalli. **Built in:** Sprint 07 (the stack, on bash-win's staging rails; the
canonical write), Sprint 08 (the publish door). **Read by:** the publish
route, the explorer, the community kit, the grove. **Rests on:** MP-68 (two
doors; the static snapshot is superseded), MP-69 (DuckDB behind both doors),
MP-70 as Kalli amended it in Sprint 06's session 16 (tested and run on Kalli's
own AWS account, handed to the library as code: D-301), MP-71 (feature data
outside AGOL, layers by URL), D-94 (harvests out of git).

A canonical object is the truth that leaves. Everything outside the machine
that shows a result (an ArcGIS layer, the explorer, a download) reads a
canonical object or a recorded derivative of one. Nothing is pushed anywhere
that is not first written here, and nothing is written here that the gate
(Contract 1) has not allowed.

## 1. What a canonical object is

One harvest, as an open data file, with its envelope beside it.

| Part | Rule |
| --- | --- |
| **Data** | GeoParquet. Non-spatial results are Parquet (D-303) |
| **Identity** | the sha256 of the data file's bytes. Two files with one hash are one object |
| **Envelope** | the harvest's full envelope, as written by the run and then by the gate: lineage (kind, run, method, choices, and curiosity for experiments), the provenance chain, warnings, context notes, the license checked, the publication steps, and the gate's allow record |
| **Mutability** | a version never changes once written. Only the `current` pointer moves |

**Hash, today:** envelopes hash their inputs with md5 (`Hasher` in
`canopy/envelope.py`). A canonical object's identity is sha256. The two can
coexist (one fingerprints inputs for provenance, the other names objects), but
the canonical write computes sha256 itself and never reuses an md5 (HASH-2).

## 2. The key layout

In one bucket, the canonical bucket that `canopy/terraform/` makes:

```
harvests/<plot>/<harvest>/versions/<sha256>/data.parquet
harvests/<plot>/<harvest>/versions/<sha256>/envelope.json
harvests/<plot>/<harvest>/versions/<sha256>/display/<n>.geojson
harvests/<plot>/<harvest>/versions/<sha256>/display/<n>.envelope.json
harvests/<plot>/<harvest>/current
```

- `<plot>` is the plot name (`maine`), validated as D-22 validates plot names.
- `<harvest>` is the harvest's stable name: today `map_<indicator>__<layer>`
  (MAP-7). The name says what the object is; the hash says which version.
- Writing bytes whose sha256 already exists writes nothing and records nothing
  new. One version, not two (Sprint 07 test).
- Harvests made before the canonical write are regenerated through it, never
  moved into this layout (D-305).

The infrastructure plan's `snapshots/` prefix is not part of this layout: the
static snapshot is superseded by MP-68.

## 3. The `current` pointer

A small JSON object, the only thing in the layout that is ever overwritten:

| Field | Meaning |
| --- | --- |
| `sha256` | the version that is current |
| `previous` | the version it replaced, or null |
| `moved_at`, `moved_by` | when, and by which run or person |
| `reason` | in plain words: a new vintage, a correction, a method change |

Moving the pointer never deletes a version. Older versions stay readable at
their own keys forever, so a link to a version is a citation. Every pointer
the bucket ever held stays too, as a noncurrent S3 version, so the history of
moves is never lost (D-307).

## 4. Display copies

A display copy is a simplified GeoJSON made for a web map. It is a derivative,
never a second truth:

- It lives under its source version's `display/` prefix, so it cannot outlive
  or be confused with the version it came from.
- Its envelope records `derived_from: <sha256>` and every change as a
  publication step (Contract 1, rule 11): the simplification tolerance,
  fields dropped, rounding, coastline clipping.
- It is regenerable from its source version and is never edited by hand. The
  hand-made `__public` and `__upload` files of October are what this rule
  exists to end (CII-20, D-94).
- GeoPackage copies are made only on request (D-303).

## 5. The bucket

- One Terraform stack, in `canopy/terraform/` (infrastructure D-3, D-306);
  its README holds the order of apply and the handover addendum.
- Versioning on; noncurrent versions kept; `force_destroy` off. The December
  2025 stack's `force_destroy = true` is retired with it.
- Private, Block Public Access declared on. The public reaches it only through
  CloudFront, which may read `harvests/*` alone (O-1, D-302).
- The bucket policy is the overwrite lock: a put to a version without
  If-None-Match is refused, and a put to `current` without If-None-Match (its
  first write) or If-Match (a move) is refused, for every principal (D-309).
  Copies into `harvests/` are therefore refused too; nothing copies.
- A budget alarm before any other resource: on Kalli's account, the console
  budget it already had; where the stack makes one, it is applied first
  (D-311). Project and environment tags on everything.

## 6. Who writes, who reads

| Who | May |
| --- | --- |
| The canonical write (`canopy/aws/s3.py`), as the role `rewilding-canonical-writer` | write a version and move `current`, only after the gate allows; never delete (D-308) |
| The publish door | write display copies; push or reference them in ArcGIS |
| ArcGIS, the explorer, DuckDB, the community kit | read by URL through CloudFront, from any origin; never write (D-310) |

A write the gate has not allowed is refused by the writer itself, not by
convention (Sprint 07 test). An overwrite is refused by the bucket itself.

## Open

| ID | Question | Decided in |
| --- | --- | --- |
| O-1 | How the public reaches files | Decided: CloudFront in front of a private bucket (D-302) |
| O-2 | GeoParquet alone, or with GeoPackage copies | Decided: GeoParquet canonical, GeoJSON display copies, GeoPackage on request (D-303) |
| O-3 | Referenced GeoJSON layers or Parquet feature layers for the explorer | Decided: referenced GeoJSON layers for December; a Parquet feature layer is a recorded read after (D-304) |
| O-4 | Where the per-target identity record lives (manifest, a sidecar in the plot, or loam) | Sprint 08 |
| O-5 | How an ArcGIS layer is updated in place: overwrite the source, or truncate and append | Sprint 08 |
