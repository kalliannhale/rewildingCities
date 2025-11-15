# 🦋 rewildingCities
a modular toolkit that powers a modern data platform designed to support predictive analytics, policy insight, and community storytelling around green infrastructure and climate resilience.

## 🌱 overview
this project lays the foundation for a structured, spatially aware data pipeline to support equity-centered urban ecological analytics. it serves three core audiences:

policy researchers exploring correlations between canopy cover, demographic patterns, and environmental risk
municipal planners verifying and supplementing local tree inventories
community organizers + citizen scientists engaging in neighborhood-level data storytelling

## 🧬 project architecture

this repo supports a multi-phase initiative:

Data Mart Construction

unify municipal tree data, census layers, environmental indices, and zoning/flood overlays
prepare geospatial joins and block-level summaries
Operational Community Database

format outputs for use by community organizers and citizen-science tools
Interactive Dashboard

visualize spatial equity gaps and green infrastructure resilience
support ML-driven insights on intervention priorities


- **architecture goals**:
    - 🌱 modular ETL + derivation pipeline (in R)
    - 📐 statistical inference compatibility
    - 💡 machine learning–readiness, *have to think about this idea of learning readiness*
    - ✨ community narrative integration
    - 🌿 sustainable compute logic
 

# 🌿 design features (what's built into the model)

| **Dimension** | **Key Fields / Features** | **Notes** |
| --- | --- | --- |
| **identity & location** | `tree_id`, `parcel_id`, `lat/lon`, `block_id`, `land_use_type` | canonical spatial anchors |
| **structural context** | `distance_to_building`, `shading_building_area_m2`, `built_form_type`, `biophilic_index` | architecture ↔ tree interface |
| **species ecology** | `species`, `native_status`, `drought_tolerance`, `pollen_score`, `canopy_width` | for local climate resilience |
| **maintenance** | `last_maintained`, `estimated_lifespan`, `planned`, `maintenance_cost_est`,  `remove` | supports forecasting + labor planning |
| **green labor link** | `responsible_entity`, `green_job_classification` | supports economic justice analytics |
| **economic value** | `estimated_cooling_savings`, `property_value_change`, `stormwater_savings`, `CO₂_sequestered_value` | **public benefit modeling (!)** |
| **community ecology** | `narrative_field`, `community_reported`, `memorial_tag` | stories, meaning, neighborhood priorities |
| **public health link** | `respiratory_risk_index`, `greenspace_access_score`, `nearest_air_monitor` | links to sacrifice zones; burdens of injustice |
| **climate resilience** | `UHI_buffer`, `resilience_zone`, `stormwater_retention` | index fields & model targets |
| **political geography** | `council_district`, `zoning_code`, `EJ_zone`, `redlined_status`, `CRS` | allows ***policy traceability*** |
| **hydrology interface** | `watershed`, `floodplain_status`, `impervious_surface_pct` | linked to water quality + urban drainage |
| **species suitability** | `climate_zone`, `soil_type`, `expected_mortality_2050` | for future species planning |
| **cost/responsibility** | `cost_to_plant`, `funding_source`, `labor_hours` | supports budget modeling + equity |
| **ML-ready fields** | `tree_vector_embedding`, `feature_imputed`, `predictive_cluster_id` | for supervised + unsupervised tasks |

---

# 🧮 field tagging for mathematical modeling

| **Type** | **Meaning** | **Example Fields** |
| --- | --- | --- |
| `measured` | directly observed | `species`, `dbh`, `planted_date` |
| `derived` | computed from others | `canopy_area`, `shade_score` |
| `indexed` | normalized composite scores | `cooling_index`, `EJ_score` |
| `categorical` | qualitative labels | `condition`, `land_use_type` |
| `temporal` | sequential or periodic | `last_inspection`, `planted_year` |
| `spatial` | point, buffer, or join-based | `geometry`, `distance_to_building` |
| `latent` | model-inferred | `vulnerability_zone`, `risk_cluster_id` |
| `economic` | monetized outputs | `cooling_cost_saved`, `maintenance_cost` |

---

# 🛠 logic + governance features

| Category | ***Implementation Suggestion*** |
| --- | --- |
| **schema validation** | per-layer `.yaml` schemas + R validators using custom rules |
| **state tracking** | versioned time-aware logs (e.g. `tree_state_log`) for changelogs |
| **model metadata** | store `model_version`, `prediction_timestamp`, `observed_outcome`, `interval_coverage` |
| **data provenance** | include `source`, `ingestion_date`, `transformation_log` per record |
| **cross-layer joins** | use a `layer_index.yaml` to declare canonical IDs and join methods |
| **schema relationships** | define relational rules and validate (e.g. tree → parcel via geometry match) |
| **narrative governance** | add `narrative_visibility`, `community_consent_status`, and `contributor_org` fields; for example, imagine this is being used by a child and they don’t understand what is vulnerable and sensitive information |
| **uncertainty tracking** | store `confidence_interval`, `feature_imputed`, `data_confidence_note` per key variable |
| **semantic enrichment** | allow optional tags like `tree_symbolism`, `heritage_marker`, `healing_landscape_type` |
| **evaluation hooks** | tag fields with `cv_fold_id`, `train_test_split_id`, `evaluation_metric_target` where needed |

---

### 🌱 environmental commitment (embedded)

- runs **locally**, minimizing compute and cloud dependence
- uses **efficient formats** (`feather`, `parquet`, `geojson`)
- minimizes **redundant derivations** with caching + modularity
- embeds **community governance** + narrative care
- designs for **climate-aligned computation + interpretability**

---

formerly, towardTreeEquity: https://github.com/kalliannhale/towardTreeEquity
