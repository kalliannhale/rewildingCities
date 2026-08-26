# seeds/schemas — what each file is

This drawer currently holds three *different kinds* of thing plus a couple of
strays. That mix is why it feels confusing. Nothing here is broken; it is just
un-sorted. This guide names each file by kind. No files need to move for the
code to keep working (the loaders read them by exact path), so treat any
reorganization as optional and incremental.

## Kind 1 — Runtime data contracts (JSON Schema)

These validate the actual data artifacts your pipeline produces. `envelope.py`
reads them on every read/write.

| File | Validates |
|------|-----------|
| `envelope.schema.json` | The whole Envelope: `data`, `metadata`, `provenance`, `warnings`. |
| `provenance.schema.json` | One provenance entry (primitive, version, inputs, params). Referenced by the envelope schema. |
| `warning.schema.json` | One warning (`level`, `primitive`, `message`). Referenced by the envelope schema. |
| `metadata.raster.schema.json` | The `metadata` block when the data category is raster (CRS, resolution, units...). |
| `metadata.vector.schema.json` | The `metadata` block for vector data. |
| `metadata.tabular.schema.json` | The `metadata` block for tabular data. |

## Kind 2 — Authoring meta-schemas (YAML)

These validate the YAML files *you write by hand* in `garden/` and `plots/`.
They are the schema-for-your-config.

| File | Validates the shape of |
|------|------------------------|
| `curiosity.schema.yml` | curiosity files in `garden/curiosity-space/<domain>/` |
| `method.schema.yml` | method files in `garden/methods/<domain>/` |
| `experiment.schema.yml` | experiment files in `garden/experiments/` |
| `manifest.schema.yml` | plot manifests in `plots/<place>/manifest.yml` |

## Kind 3 — The vocabulary (not a schema)

| File | What it is |
|------|-----------|
| `semantic_types.yml` | The type registry / dictionary. This is the thing being split into **base + per-domain module files** (see below). Not a validator; a vocabulary. |

## Strays (config that wandered into the schemas drawer)

| Item | What it is | Where it probably belongs |
|------|-----------|---------------------------|
| `profiles.yml` | Run-context presets (`full`, `dev`...): study-area scope, feature sampling, resolution mode. **Config, not a schema.** | `seeds/profiles/` (which already exists — this looks like a duplicate/misplacement to reconcile). |
| `dataset_types/` | Unknown from here — not in the working copy that was reviewed. **Open question: what lives in this directory, and is it vocabulary, config, or schema?** | TBD once its contents are known. |

## The one real change: base + module vocabulary

The domains you already run (`thermal`, `perception`, `information` under
`garden/curiosity-space/` and `garden/methods/`) become the organizing spine for
the vocabulary too:

```
seeds/schemas/
  semantic_types.yml        # BASE: types reused across every domain
  modules/
    thermal.yml             # park/cooling types
    perception.yml          # segmentation / falsification types
    information.yml         # Maine information-ecosystem types
```

- Base holds only what a second domain would genuinely reuse (ML scaffolding,
  generic spatial nouns, generic perception primitives).
- Each module file holds that domain's specific nouns.
- Names stay **flat**; each type carries an explicit `module:` field so its
  origin is visible, and the loader errors loudly on any cross-domain name
  collision. (Visible origin, legible names, loud conflicts.)
- The `_state` types (`*_checked`, `*_reprojected`, ...) are deleted; state is
  now carried by provenance. This triggers a one-time re-run to regenerate the
  NYC envelopes under the new scheme.

Only the semantic-type loader changes (to merge base + `modules/*.yml`). The
Kind 1 and Kind 2 schemas above are left exactly where they are.
