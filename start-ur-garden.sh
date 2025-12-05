#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# 🌱 start-ur-garden.sh
# plants the complete directory structure and seed files for rewildingCities
# run this once to initialize a fresh garden
# ═══════════════════════════════════════════════════════════════════════════════

set -e

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "🌱 rewildingCities: starting your garden"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

# ───────────────────────────────────────────────────────────────────────────────
# soil/ — validation & data preparation
# ───────────────────────────────────────────────────────────────────────────────
echo "🌍 preparing the soil..."

mkdir -p soil/validate
mkdir -p soil/repair
mkdir -p soil/register/providers

# ───────────────────────────────────────────────────────────────────────────────
# seeds/ — schemas, crosswalks, templates, profiles
# ───────────────────────────────────────────────────────────────────────────────
echo "🌰 gathering seeds..."

mkdir -p seeds/schemas/dataset_types
mkdir -p seeds/crosswalks
mkdir -p seeds/templates

# ───────────────────────────────────────────────────────────────────────────────
# roots/ — primitives (foundational operations)
# ───────────────────────────────────────────────────────────────────────────────
echo "🌿 establishing roots..."

mkdir -p roots/geometry
mkdir -p roots/metrics
mkdir -p roots/statistics
mkdir -p roots/_shared

# ───────────────────────────────────────────────────────────────────────────────
# growth/ — recipes (composed workflows)
# ───────────────────────────────────────────────────────────────────────────────
echo "🌻 making space for growth..."

mkdir -p growth/_fragments

# ───────────────────────────────────────────────────────────────────────────────
# harvest/ — outputs
# ───────────────────────────────────────────────────────────────────────────────
echo "🍅 preparing the harvest baskets..."

mkdir -p harvest/reports
mkdir -p harvest/maps
mkdir -p harvest/exports
mkdir -p harvest/dashboards

# ───────────────────────────────────────────────────────────────────────────────
# compost/ — logs, archives, feedback
# ───────────────────────────────────────────────────────────────────────────────
echo "🍂 building the compost bin..."

mkdir -p compost/logs
mkdir -p compost/archive
mkdir -p compost/feedback

# ───────────────────────────────────────────────────────────────────────────────
# garden/ — experimental
# ───────────────────────────────────────────────────────────────────────────────
echo "🌷 fencing the experimental garden..."

mkdir -p garden/experiments
mkdir -p garden/notebooks
mkdir -p garden/tests

# ───────────────────────────────────────────────────────────────────────────────
# plots/ — city-specific data
# ───────────────────────────────────────────────────────────────────────────────
echo "🏡 marking out the plots..."

mkdir -p plots/nyc/.data
mkdir -p plots/_template

# ───────────────────────────────────────────────────────────────────────────────
# field-guide/ — documentation
# ───────────────────────────────────────────────────────────────────────────────
echo "📖 binding the field guide..."

mkdir -p field-guide/concepts
mkdir -p field-guide/tutorials
mkdir -p field-guide/species/roots
mkdir -p field-guide/species/growth

# ───────────────────────────────────────────────────────────────────────────────
# canopy/ — orchestration
# ───────────────────────────────────────────────────────────────────────────────
echo "🌳 watching the canopy emerge..."

mkdir -p canopy

# ───────────────────────────────────────────────────────────────────────────────
# terraform/ — infrastructure as code (for later)
# ───────────────────────────────────────────────────────────────────────────────
echo "🏗️  reserving space for infrastructure..."

mkdir -p terraform

# ═══════════════════════════════════════════════════════════════════════════════
# .gitkeep files so empty directories are tracked
# ═══════════════════════════════════════════════════════════════════════════════
echo "🌱 planting markers in empty beds..."

find . -type d -empty -exec touch {}/.gitkeep \;

# ═══════════════════════════════════════════════════════════════════════════════
# .gitignore
# ═══════════════════════════════════════════════════════════════════════════════
echo "📝 writing .gitignore..."

cat > .gitignore << 'EOF'
# ═══════════════════════════════════════════════════════════════════════════════
# 🌱 rewildingCities .gitignore
# ═══════════════════════════════════════════════════════════════════════════════

# city data (large files, local to each gardener)
plots/*/.data/*
!plots/*/.data/.gitkeep

# harvest outputs (regenerable)
harvest/reports/*
harvest/maps/*
harvest/exports/*
harvest/dashboards/*
!harvest/**/.gitkeep

# compost (logs accumulate locally)
compost/logs/*
compost/archive/*
!compost/**/.gitkeep

# R artifacts
.Rproj.user
.Rhistory
.RData
.Ruserdata
*.Rproj

# Terraform
terraform/.terraform/
terraform/*.tfstate
terraform/*.tfstate.backup
terraform/*.tfvars
!terraform/*.example.tfvars

# system files
.DS_Store
Thumbs.db

# environment
.env
.env.local
EOF

# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA: manifest.schema.yml
# ═══════════════════════════════════════════════════════════════════════════════
echo "📐 creating manifest schema..."

cat > seeds/schemas/manifest.schema.yml << 'EOF'
# ═══════════════════════════════════════════════════════════════════════════════
# MANIFEST SCHEMA v1.0
# A manifest declares what data a city has, what it means, and where it lives.
# ═══════════════════════════════════════════════════════════════════════════════

manifest:
  type: object
  required: [city, crs, datasets]
  properties:

    # ───────────────────────────────────────────────────────────────────────────
    # IDENTITY
    # ───────────────────────────────────────────────────────────────────────────
    city:
      type: object
      required: [name, id]
      properties:
        name: { type: string, description: "Human-readable city name" }
        id: { type: string, pattern: "^[a-z0-9_]+$", description: "Machine ID" }
        region: { type: string, description: "State/province" }
        country: { type: string, description: "ISO country code" }
        timezone: { type: string, description: "IANA timezone" }

    # ───────────────────────────────────────────────────────────────────────────
    # SPATIAL REFERENCE
    # ───────────────────────────────────────────────────────────────────────────
    crs:
      type: object
      required: [working]
      properties:
        working: { type: string, description: "EPSG code for analysis" }
        notes: { type: string, description: "Why this CRS" }

    # ───────────────────────────────────────────────────────────────────────────
    # STEWARDSHIP
    # ───────────────────────────────────────────────────────────────────────────
    stewardship:
      type: object
      properties:
        maintainers:
          type: array
          items:
            type: object
            properties:
              name: { type: string }
              contact: { type: string }
              organization: { type: string }
        initialized: { type: string, format: date }
        last_verified: { type: string, format: date }
        community_partners: { type: array, items: { type: string } }

    # ───────────────────────────────────────────────────────────────────────────
    # SCOPE (subsetting defaults)
    # ───────────────────────────────────────────────────────────────────────────
    scope:
      type: object
      properties:
        study_area:
          type: object
          properties:
            type: { type: string, enum: [full, bbox, boundary, buffer] }
            bbox: { type: array, items: { type: number }, minItems: 4, maxItems: 4 }
            boundary_dataset: { type: string }
            boundary_filter: { type: string }
            center: { type: array, items: { type: number }, minItems: 2, maxItems: 2 }
            radius_km: { type: number }
        feature_sampling:
          type: object
          properties:
            enabled: { type: boolean, default: false }
            method: { type: string, enum: [random, stratified, filtered, explicit] }
            n: { type: integer }
            seed: { type: integer }
            stratify_by: { type: string }
            n_per_stratum: { type: integer }
            filter: { type: string }
            feature_ids: { type: array, items: { type: string } }
        resolution:
          type: object
          properties:
            mode: { type: string, enum: [native, target, overview], default: native }
            target_meters: { type: number }
            overview_level: { type: integer }

    # ───────────────────────────────────────────────────────────────────────────
    # DATASETS
    # ───────────────────────────────────────────────────────────────────────────
    datasets:
      type: object
      additionalProperties:
        $ref: "#/definitions/dataset"

definitions:
  dataset:
    type: object
    required: [available]
    properties:
    
      # availability
      available: { type: boolean }
      
      # source (where to get data)
      source:
        type: object
        properties:
          type: { type: string, enum: [local, api, url] }
          path: { type: string }
          provider: { type: string, enum: [socrata, arcgis_rest, ckan, custom] }
          endpoint: { type: string, format: uri }
          query_params: { type: object }
          auth:
            type: object
            properties:
              type: { type: string, enum: [none, api_key, oauth] }
              key_env_var: { type: string }
          url: { type: string, format: uri }
      
      # cache (local storage)
      cache:
        type: object
        properties:
          path: { type: string }
          fetched_at: { type: string, format: date-time }
          refresh_policy: { type: string, enum: [manual, daily, weekly, always], default: manual }
          max_age_days: { type: integer }
      
      # semantic identity
      format: { type: string, enum: [geotiff, geojson, geopackage, shapefile, parquet, csv, feather] }
      semantic_type:
        type: string
        enum:
          - land_surface_temperature
          - land_cover
          - ndvi
          - nighttime_lights
          - population_density
          - elevation
          - park_boundaries
          - city_boundary
          - administrative_districts
          - road_network
          - water_bodies
          - building_footprints
      measurement_type: { type: string, enum: [absolute, relative, anomaly] }
      statistic: { type: string, enum: [mean, median, max, min, composite] }
      units: { type: string }
      classification_scheme: { type: string }
      num_classes: { type: integer }
      geometry_type: { type: string, enum: [point, linestring, polygon, multipoint, multilinestring, multipolygon, mixed] }
      id_field: { type: string }
      
      # temporal
      temporal:
        type: object
        properties:
          type: { type: string, enum: [snapshot, seasonal_composite, annual_average, multi_year_composite] }
          year: { type: integer }
          range:
            type: object
            properties:
              start: { type: string, format: date }
              end: { type: string, format: date }
          season: { type: string, enum: [spring, summer, fall, winter, annual] }
      
      # provenance
      provenance:
        type: object
        properties:
          source: { type: string }
          source_url: { type: string, format: uri }
          license: { type: string }
          retrieval_date: { type: string, format: date }
          processing_notes: { type: string }
      
      # quality
      quality:
        type: object
        properties:
          confidence: { type: string, enum: [high, medium, low, unknown] }
          known_issues: { type: array, items: { type: string } }
          spatial_resolution: { type: string }
          completeness: { type: string }
EOF

# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA: recipe.schema.yml
# ═══════════════════════════════════════════════════════════════════════════════
echo "📐 creating recipe schema..."

cat > seeds/schemas/recipe.schema.yml << 'EOF'
# ═══════════════════════════════════════════════════════════════════════════════
# RECIPE SCHEMA v1.0
# A recipe declares a composed workflow of primitives.
# ═══════════════════════════════════════════════════════════════════════════════

recipe:
  type: object
  required: [name, version, requires, steps]
  properties:
  
    # ───────────────────────────────────────────────────────────────────────────
    # IDENTITY
    # ───────────────────────────────────────────────────────────────────────────
    name: { type: string, description: "Human-readable recipe name" }
    version: { type: string, description: "Semantic version" }
    description: { type: string, description: "What this recipe does" }
    
    # ───────────────────────────────────────────────────────────────────────────
    # REQUIREMENTS
    # ───────────────────────────────────────────────────────────────────────────
    requires:
      type: array
      items: { type: string }
      description: "Dataset semantic_types this recipe needs"
    
    # ───────────────────────────────────────────────────────────────────────────
    # SCOPE REQUIREMENTS
    # ───────────────────────────────────────────────────────────────────────────
    scope_requirements:
      type: object
      properties:
        min_features: { type: integer }
        max_resolution_meters: { type: number }
        warn_if_sampled: { type: boolean }
    
    # ───────────────────────────────────────────────────────────────────────────
    # PARAMETERS
    # ───────────────────────────────────────────────────────────────────────────
    parameters:
      type: object
      additionalProperties:
        type: object
        properties:
          type: { type: string, enum: [integer, number, string, boolean, enum] }
          default: {}
          description: { type: string }
          options: { type: array }
    
    # ───────────────────────────────────────────────────────────────────────────
    # STEPS
    # ───────────────────────────────────────────────────────────────────────────
    steps:
      type: array
      items:
        type: object
        required: [id, primitives]
        properties:
          id: { type: string }
          primitives:
            type: array
            items:
              type: object
EOF

# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA: profiles.yml
# ═══════════════════════════════════════════════════════════════════════════════
echo "📐 creating profiles..."

cat > seeds/schemas/profiles.yml << 'EOF'
# ═══════════════════════════════════════════════════════════════════════════════
# PROFILES v1.0
# Pre-configured scope settings for different contexts
# ═══════════════════════════════════════════════════════════════════════════════

profiles:

  full:
    description: "Complete analysis, no subsetting"
    study_area:
      type: full
    feature_sampling:
      enabled: false
    resolution:
      mode: native

  dev:
    description: "Fast iteration for development"
    study_area:
      type: full
    feature_sampling:
      enabled: true
      method: stratified
      stratify_by: "auto"
      n_per_stratum: 5
      seed: 42
    resolution:
      mode: target
      target_meters: 30

  test:
    description: "Minimal subset for automated testing"
    study_area:
      type: bbox
      bbox: "auto_small"
    feature_sampling:
      enabled: true
      method: random
      n: 10
      seed: 12345
    resolution:
      mode: target
      target_meters: 100

  neighborhood:
    description: "Single neighborhood analysis"
    study_area:
      type: buffer
      radius_km: 2
    feature_sampling:
      enabled: false
    resolution:
      mode: native
EOF

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE: manifest.template.yml
# ═══════════════════════════════════════════════════════════════════════════════
echo "📝 creating manifest template..."

cat > plots/_template/manifest.template.yml << 'EOF'
# ═══════════════════════════════════════════════════════════════════════════════
# CITY MANIFEST TEMPLATE
# Copy to plots/your_city/manifest.yml and fill in
# ═══════════════════════════════════════════════════════════════════════════════

city:
  name: ""
  id: ""
  region: ""
  country: ""
  timezone: ""

crs:
  working: ""
  notes: ""

stewardship:
  maintainers:
    - name: ""
      organization: ""
  initialized: ""
  last_verified: ""
  community_partners: []

scope:
  study_area:
    type: full
  feature_sampling:
    enabled: false
  resolution:
    mode: native

datasets:

  lst_median:
    available: false
    # source:
    #   type: local | api | url
    #   path: ".data/lst_median.tif"  # for local
    #   provider: socrata              # for api
    #   endpoint: ""                   # for api
    #   url: ""                        # for url
    # cache:
    #   path: ".data/lst_median.tif"
    #   refresh_policy: manual
    # format: geotiff
    # semantic_type: land_surface_temperature
    # measurement_type: relative
    # statistic: median
    # temporal:
    #   type: seasonal_composite
    #   season: summer
    #   year: 2023
    # provenance:
    #   source: ""
    #   source_url: ""
    # quality:
    #   confidence: medium
    #   known_issues: []

  lst_mean:
    available: false

  parks:
    available: false

  land_cover:
    available: false

  ndvi:
    available: false

  nighttime_lights:
    available: false

  population:
    available: false

  roads:
    available: false
EOF

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE: setup_guide.md
# ═══════════════════════════════════════════════════════════════════════════════
echo "📝 creating setup guide..."

cat > plots/_template/setup_guide.md << 'EOF'
# 🏡 Setting Up a New City Plot

## Step 1: Create Your Plot

```bash
cp -r plots/_template plots/your_city_id
cd plots/your_city_id
mv manifest.template.yml manifest.yml
mkdir -p .data