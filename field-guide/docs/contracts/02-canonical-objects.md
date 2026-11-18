# Contract 2 ~ Canonical objects

**Status:** draft 0.6, 2026-11-18, for review (0.6 carries zip 9b1: an outline's markers copy, the told copy (a display copy that is a document), the refusal record and the places map, D-363, D-370 to D-372, D-376 to D-381; 0.5 carries zip 8b: joined copies, markers, local dry runs and the two guards on what may be written, D-335 to D-341; 0.4 carries zip 8a's publish door, D-326 to D-332; 0.2 earlier on 2026-11-16, at zip 7a; 0.1, 2026-11-10). 0.3 carries zip 7b's canonical write, D-312 to D-320, and zip 7c's display copies, D-321 to D-324. **Owner:**
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
| **Data** | GeoParquet for features, Parquet for tables, JSON for documents such as the place profile (D-303, D-314). Nothing else is written; a CSV, GeoPackage, raster or Arrow receipt is refused by name |
| **Identity** | the sha256 of the data file's bytes. Two files with one hash are one object. A library upgrade can make new bytes from the same content, and so a new version; that is said, never hidden (D-314) |
| **Envelope** | the receipt, byte for byte, as the run wrote it: lineage (kind, run, method, choices, and curiosity for experiments), the provenance chain, warnings, context notes. The gate's allow record (the license checked, the tiers, the notes carried, every publication step) lives beside it under `allow/`, never inside the file it judges (D-274, D-313), versioned by its own content (D-320); the envelope schema is unchanged |
| **Mutability** | a version never changes once written. Only the `current` pointer moves |

**Hash, today:** envelopes hash their inputs with md5 (`Hasher` in
`canopy/envelope.py`). A canonical object's identity is sha256. The two can
coexist (one fingerprints inputs for provenance, the other names objects), but
the canonical write computes sha256 itself and never reuses an md5 (HASH-2).

**What a write takes (D-312).** Only a receipt in the plot's own
`.envelopes`, named by its artifact name; never a manifest dataset. Its data
file must sit inside the plot's own `.data` (receipts write paths through
`preparations/..`, resolved against the garden's root) and travel alone: a
receipt naming secondary files is refused until this contract says how they
travel.

**Conversion at the write (D-314).** A receipt whose data is GeoJSON is
converted by the canonical write to GeoParquet with geopandas, no index
column. It is converted twice and refused if the two files differ, so a
version's hash names its content and not the moment it was made. The change
is a `format_changed` record (Contract 1, rule 11) appended to the allow
record's publication steps, `by` the canonical write, naming
the libraries and their versions, the crs, the feature count and the source
file's own sha256. Parquet and JSON are written as they are, with no record,
because nothing changes.

## 2. The key layout

In one bucket, the canonical bucket that `canopy/terraform/` makes:

```
harvests/<plot>/<harvest>/versions/<sha256>/data.parquet      (or data.json, a document)
harvests/<plot>/<harvest>/versions/<sha256>/envelope.json     (the receipt, byte for byte)
harvests/<plot>/<harvest>/versions/<sha256>/allow/<allow-sha256>.json   (one per distinct allow record)
harvests/<plot>/<harvest>/versions/<sha256>/display/<n>.geojson
harvests/<plot>/<harvest>/versions/<sha256>/display/<n>.envelope.json
harvests/<plot>/<harvest>/current
harvests/<plot>/_refusals/versions/<sha256>/data.json            (the refusal record, section 4c)
harvests/<plot>/_refusals/current
```

- `<plot>` is the plot name (`maine`), validated as D-22 validates plot names.
- `<harvest>` is the receipt's artifact name (D-318), as in
  `clerk_offices_points_points`. The name says what the object is; the hash
  says which version. A version's URL is a citation forever, so a rename
  makes a new harvest and never moves an old one. `map.py`'s
  `map_<indicator>__<layer>` files (MAP-7) are not receipts and are not
  written here.
- Writing bytes whose sha256 already exists, judged the same way, writes
  nothing and records nothing new. One version, not two (Sprint 07 test). A
  newer receipt for the same bytes leaves the first version's envelope as it
  was.
- **The allow record is versioned inside its version (D-320).** What the gate
  says can change while the data does not: a note's text settled on the
  nations' terms (TRIBE-7, P-8), a license term read again. So each allow
  record is named by the sha256 of its own content, less the times it was
  made at (the gate's `checked_at`, the write's own steps' `at`, when it was
  prepared) and less which receipt was read. The same data with a changed
  allow record writes that record alone and moves `current` to the pair; the
  old record stays readable, as history. A library's version in a
  conversion's detail is content, so an upgrade makes a new allow record,
  loudly.
- A version is whole when its data file exists. The data file is put last, so
  a write cut off partway finishes on the next try, each file put with
  If-None-Match.
- Harvests made before the canonical write are regenerated through it, never
  moved into this layout (D-305).

The infrastructure plan's `snapshots/` prefix is not part of this layout: the
static snapshot is superseded by MP-68.

## 3. The `current` pointer

A small JSON object, the only thing in the layout that is ever overwritten:

| Field | Meaning |
| --- | --- |
| `sha256` | the version that is current |
| `allow` | the allow record that is current, by its sha256 (D-320) |
| `previous` | the version it replaced, or null; the same version when only the allow record moved |
| `previous_allow` | the allow record it replaced, or null |
| `data` | the version's data file name, `data.parquet` or `data.json` |
| `moved_at`, `moved_by` | when, and by which run or person |
| `reason` | in plain words: a new vintage, a correction, a method change |

A move to a version that already exists (a revert) is a move like any other,
with its reason. A pointer moved by another writer while a write runs is left
as they set it: the move is put with If-Match, and a refused move says so.
`moved_by` is the person, given by name; `reason` is required (D-317).

Moving the pointer never deletes a version. Older versions stay readable at
their own keys forever, so a link to a version is a citation. Every pointer
the bucket ever held stays too, as a noncurrent S3 version, so the history of
moves is never lost (D-307).

## 4. Display copies

A display copy is a GeoJSON drawn for a web map. It is a derivative, never a
second truth (D-321):

- It is drawn by `python -m canopy.cli canonical <plot> <artifact> --display`
  from the current version's own bytes, read back from the bucket and checked
  against their sha256, never from a local copy. A dry run unless `--write`.
- It lives under its source version's `display/` prefix, so it cannot outlive
  or be confused with the version it came from:
  `versions/<sha256>/display/<name>.geojson` and `<name>.envelope.json`. Points
  are named `web`; polygons `web_<tolerance>m`, so a copy at another tolerance
  is another copy, and a name is never given new bytes (D-322).
- Its envelope keeps the version's lineage, notes and provenance (inherited
  under the branch `version`), records `derived_from: <sha256>` and the allow
  record current when it was drawn, and adds its own entry whose publication
  list holds every change (Contract 1, rule 11): `simplified`, `rounded`,
  `format_changed` (D-323), and `opened` first where a pinch had to be
  opened (D-356). It matches the envelope schema and is judged by the
  gate as the version was, a custom tier refused (D-315).
- **Polygons are simplified as one coverage** (shapely's `coverage_simplify`),
  so neighbours keep one shared edge and no crack opens between towns; in
  meters in UTM zone 19N (EPSG:26919), 25 m by default. A coverage that is
  not valid before simplifying, or a geometry left empty after, is refused:
  a town missing from the map, or a crack between two, would be a lie.
  **Points** simplify nothing, said with count 0. Coordinates are rounded to
  6 decimal places of a degree; the copy is GeoJSON (RFC 7946) in EPSG:4326,
  its `format_changed` record naming the transformation pyproj chose
  (Maine's outlines are NAD83). Every property is kept (D-324).
- The copy carries no note text inside it. A note settled later moves the
  allow record (D-320) without a new copy; the notes reach a map through its
  item's description, which the publish door rewrites when the allow record
  moves (D-328).
- It is regenerable from its source version and is never edited by hand. The
  hand-made `__public` and `__upload` files of October are what this rule
  exists to end (CII-20, D-94).
- GeoPackage copies are made only on request (D-303).

## 4a. Joined copies (D-331, D-339 to D-341)

A choropleth's copy is a long-form table drawn on an outline. It has two
parents, and says so:

- It is drawn by `canonical <plot> <table> --display --join <outline>` from
  both current versions' own bytes, each checked against its sha256. The join
  is canopy/choropleth.py's: (unit_authority, unit_code) to (authority, code),
  never a name or a code alone (LAYER-1). One feature per place of the
  outline, every indicator's columns beside it as `<indicator>__<column>`; a
  place with no row stays, its columns empty and `joined` false. Every row is
  counted: in the outline, outside it at its level, at another level, under
  another authority, by the widths seeds/authorities declares.
- It lives under the **table's** version, named for the outline's version:
  `versions/<table sha>/display/<outline>_<outline sha12>_web_<n>m.geojson`,
  or `..._markers.geojson`. A new outline version is a new copy and never new
  bytes under one name (D-322).
- Its envelope records `derived_from: <table sha>` and `joined_to`: the
  outline's harvest, version, allow record, authority, level and lineage. Both
  chains are inherited, under the branches `table` and `outline`; its own entry
  names both inputs by sha256 and holds every change, `joined` among them. Its
  `row_context_notes` are the notes its drawn places carry (Contract 1, 0.8).
- **Markers** are one point on each place's own surface (shapely's
  `point_on_surface` in EPSG:26919), simplifying nothing, recorded as `marked`.
  So a coverage that is not valid (COVER-1) never stops them.
- **A local dry run**, `--display --local`, draws a copy from the exact bytes a
  write would send, from the plot's own files. It needs no AWS and can never be
  written. It prints the copy's sha256, which the copy drawn from the bucket
  must print before it is written, so nothing permanent happens before the
  whole copy has been drawn, joined and judged once.

## 4c. The explorer's copies (zip 9b1)

**Markers (D-377).** `canonical <plot> <outline> --display --markers` draws an
outline as one point on each place's own surface, simplifying nothing,
recorded `marked`, named `markers` under the outline's version. The places map
reads every level but the towns from one.

**Rounding, said (ROUND-2, D-379).** A polygon copy's `rounded` record names
every shape its rounding leaves invalid, by id, or says every shape is valid.
It is never refused for it: the door refuses to send an invalid shape (D-368),
and a copy's dry run is where one is first seen.

**The told copy (D-370, D-378, D-381).** A display copy may be a document.
`canonical <plot> place_profile_profiles --told` tells every place the explorer
shows (canopy/wonder/telling.py) from the profile's current version, read back
from the bucket and checked against its sha256, and the current refusal record.
It lives under the profile's version:
`versions/<sha256>/display/told_<sha12>.json` and its envelope, named by the
hash of every file that can change its bytes (canopy/aws/told.py, telling.py,
place.py, the notes and plain_language.yml; the standard reaches it only
through the profile's version) and of the refusal record's version, so a
changed seed or a new judgment is a new name and never new bytes under one
(D-322). Its envelope keeps the profile's metadata, lineage, notes and chain
under the branch `version`, describes its rows as told rows, and adds a `told`
record; the refusal record is named in its params, never as an input. It is
judged as the profile was. `--local` tells the plot's own files and never
writes.

**The refusal record (D-363).** The gate's refusals for every receipt in a
plot (Contract 1, section 7), written by `canonical <plot> --refusals --write`
as a document with no time in it, versioned by its own bytes, its pointer
moved as any pointer is. `_refusals` is a name no receipt can take, since an
artifact name never begins with `_`. The bucket policy's locks already match
it, so the infrastructure is unchanged.

## 4b. What may be written at all (D-335, D-337)

- A receipt that names its run is written only if that run still declares the
  step and output that make its name. A receipt left behind by a renamed step
  is an orphan and is refused. A test holds that no two runs of a plot write one
  receipt name, the known pairs named with their reasons.
- A receipt's data file is never a manifest dataset's cached file: a source the
  plot fetched never reaches the bucket by being named in a receipt (D-297).

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
- Versions are put with `Cache-Control: public, max-age=31536000, immutable`,
  the pointer with `no-cache` (D-317).
- The bucket's name holds the account id, which stays out of the repo (D-301):
  the write reads it from `REWILDING_CANONICAL_BUCKET`, the CloudFront domain
  from `REWILDING_CANONICAL_DOMAIN`, and the profile from
  `REWILDING_CANONICAL_PROFILE`, `rewilding-writer` when unset (D-316).

## 6. Who writes, who reads

| Who | May |
| --- | --- |
| The canonical write (`canopy/aws/s3.py`, run as `python -m canopy.cli canonical`), as the role `rewilding-canonical-writer` | write a version and move `current`, only after the gate allows at target `canonical`, sharing level `public`, because CloudFront makes `harvests/` readable by anyone (D-315); never delete (D-308). A dry run is the default and touches no AWS; `--write` takes one artifact at a time, with `--by` and `--reason` (D-316). A lineage holding a `custom` tier is refused until O-6 |
| The canonical command's `--display`, as the same role | write display copies under a version, only after the gate allows (D-321) |
| The publish door (`canopy/expose/publish.py`, `python -m canopy.cli publish`) | reference display copies in ArcGIS by URL, reading the bucket only through CloudFront, so it needs no AWS credentials; never write the bucket (D-326). The one place it stores features is the places map (`publish <plot> --places`, D-371): the told copy's rows on each level's display copy, copied into one web map's own JSON, never a hosted feature layer, the door owning the whole map (D-380) |
| ArcGIS, the explorer, DuckDB, the community kit | read by URL through CloudFront, from any origin; never write (D-310) |

A write the gate has not allowed is refused by the writer itself, not by
convention (Sprint 07 test). An overwrite is refused by the bucket itself.

## Open

| ID | Question | Decided in |
| --- | --- | --- |
| O-1 | How the public reaches files | Decided: CloudFront in front of a private bucket (D-302) |
| O-2 | GeoParquet alone, or with GeoPackage copies | Decided: GeoParquet canonical, GeoJSON display copies, GeoPackage on request (D-303) |
| O-3 | Referenced GeoJSON layers or Parquet feature layers for the explorer | Decided: referenced GeoJSON layers for December; a Parquet feature layer is a recorded read after (D-304) |
| O-4 | Where the per-target identity record lives | Decided: `plots/<plot>/publish/published.yml`, written by the door alone, each item naming the `sha256` and `allow` it shows, as `current` does; the targets beside it in `targets.yml` (D-327) |
| O-5 | How an ArcGIS layer is updated in place | Decided: no features are updated, because none are stored. The door owns web map items: a new version moves the layer's URL and the description, a new allow record the description alone, each only from the state the record names (D-328) |
| O-6 | How a version is withdrawn. A version stays readable forever and the writer can never remove one, yet Contract 1 says a withdrawn consent admits nothing from the day it is withdrawn. Withdrawal would need a person's own removal of the version, a tombstone at its key, and a CloudFront invalidation, recorded and done on the terms of the people the data describes (CARE, OCAP). Until it is decided, the write refuses any lineage holding a `custom` tier (D-315) | After delivery |
