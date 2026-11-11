# Contract 2 ~ Canonical objects

**Status:** draft 0.1, 2026-11-10, for review. **Owner:** Kalli. **Built in:**
Sprint 07 (the infrastructure teammate), Sprint 08 (the publish door).
**Read by:** the publish route, the explorer, the community kit, the grove.
**Rests on:** MP-68 (two doors; the static snapshot is superseded), MP-69
(DuckDB behind both doors), MP-70 (the library's AWS account, tested first on
Kalli's), MP-71 (feature data outside AGOL, layers by URL), D-94 (harvests out
of git).

A canonical object is the truth that leaves. Everything outside the machine
that shows a result (an ArcGIS layer, the explorer, a download) reads a
canonical object or a recorded derivative of one. Nothing is pushed anywhere
that is not first written here, and nothing is written here that the gate
(Contract 1) has not allowed.

## 1. What a canonical object is

One harvest, as an open data file, with its envelope beside it.

| Part | Rule |
| --- | --- |
| **Data** | GeoParquet (Sprint 07). Non-spatial results are Parquet |
| **Identity** | the sha256 of the data file's bytes. Two files with one hash are one object |
| **Envelope** | the harvest's full envelope, as written by the run and then by the gate: lineage (kind, run, method, choices, and curiosity for experiments), the provenance chain, warnings, context notes, the license checked, the publication steps, and the gate's allow record |
| **Mutability** | a version never changes once written. Only the `current` pointer moves |

**Hash, today:** envelopes hash their inputs with md5 (`Hasher` in
`canopy/envelope.py`). A canonical object's identity is sha256. The two can
coexist (one fingerprints inputs for provenance, the other names objects), but
the canonical write computes sha256 itself and never reuses an md5 (HASH-2).

## 2. The key layout

In one bucket, in the library's AWS account:

```
harvests/<plot>/<harvest>/versions/<sha256>/data.parquet
harvests/<plot>/<harvest>/versions/<sha256>/envelope.json
harvests/<plot>/<harvest>/versions/<sha256>/display/<name>.geojson
harvests/<plot>/<harvest>/versions/<sha256>/display/<name>.envelope.json
harvests/<plot>/<harvest>/current
```

- `<plot>` is the plot name (`maine`), validated as D-22 validates plot names.
- `<harvest>` is the harvest's stable name: today `map_<indicator>__<layer>`
  (MAP-7). The name says what the object is; the hash says which version.
- Writing bytes whose sha256 already exists writes nothing and records nothing
  new. One version, not two (Sprint 07 test).

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
their own keys forever, so a link to a version is a citation.

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

## 5. The bucket

- Versioning on; `force_destroy` off. The December stack's `force_destroy =
  true` is retired with it (Sprint 07).
- A budget alarm before any other resource, a least-privilege IAM identity,
  and project and environment tags on everything.
- One Terraform stack, in `canopy/terraform/` (infrastructure D-3).

## 6. Who writes, who reads

| Who | May |
| --- | --- |
| The canonical write (`canopy/aws/s3.py`) | write a version and move `current`, only after the gate allows |
| The publish door | write display copies; push or reference them in ArcGIS |
| ArcGIS, the explorer, DuckDB, the community kit | read by URL; never write |

A write the gate has not allowed is refused by the writer itself, not by
convention (Sprint 07 test).

## Open

| ID | Question | Decided in |
| --- | --- | --- |
| O-1 | How the public reaches files: a public prefix with CORS for ArcGIS, or CloudFront in front of the bucket | Sprint 07 |
| O-2 | GeoParquet alone, or GeoParquet with GeoPackage copies for ArcGIS Pro users | Sprint 07 |
| O-3 | Referenced GeoJSON layers or Parquet feature layers for the explorer, and whether the latter use AGOL feature storage | Sprint 07 |
| O-4 | Where the per-target identity record lives (manifest, a sidecar in the plot, or loam) | Sprint 08 |
| O-5 | How an ArcGIS layer is updated in place: overwrite the source, or truncate and append | Sprint 08 |
