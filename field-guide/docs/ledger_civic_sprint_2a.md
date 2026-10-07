# Build Ledger ~ additions for Civic Sprint 2a (demo prep)

A delta for `build_ledger.md`. Every decision below was made by Claude without
consultation, at Kalli's request ("go with what you lean toward"). Each says
what was decided, what it implies, and what would reverse it, so any of them
can be revisited without archaeology.

---

## DECISIONS ~ add to "Decisions made"

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-16** | Preview derivation in Python (`canopy/indicator_preview.py`), labelled `status: preview`, `envelope: null`, `method: preview:<kind>` on every row | Breaks roots-are-R for display only, never for an artifact. Nothing writes `indicator_values`. When `derive_indicator.R` lands, this becomes its test oracle: two implementations of one declaration that must agree exactly | The R primitive exists and the API reads its enveloped output instead. Keep the module as the oracle; retire its API route |
| **D-17** | Cache paths resolve against the plot directory (`plots/<plot>/.data/...`), from `project_root()` | **Likely, still unverified.** Evidence: `app.py` resolves receipts as `plots/<plot>/.envelopes`, plot-relative. If the cache lives elsewhere, every preview returns `unavailable` naming the path it tried. Verify with `ls plots/maine/.data` | The cache lives at the repo root: change one line in `indicator_sources` |
| **D-18** | No margin of error derived for ratios; component margins served instead. Passthrough margins served as published | A row never shows a plausible wrong uncertainty. The cost: broadband and no-vehicle show no derived MOE in the demo | IND-3 lands (`proportion` kind) and `derive_indicator.R` implements the Census formulas |
| **D-19** | Long-form rows: `(unit, indicator, value, authority, method, time)`, with `unit` itself `(authority, code)` | Settles the fork from last session in favour of long-form, for the preview. A second authority's claim about the same county fits without a schema change. Consumers pivot for maps | You decide the R primitive should emit wide. The preview can follow either way |
| **D-20** | Registry and manifest read on every request; no cache | A preview can never disagree with the files on disk. Cost is a few milliseconds per call | Request volume makes it matter, which is not soon. C-65 is the real concurrency problem |
| **D-21** | More than one source listing an indicator is refused as `ambiguous` (409) until `dataset=` names one | Matches the acquire report's stance: a choice, not a lookup. Becomes live the day a 2025 release is acquired beside 2024 | Never, probably. A default would be a silent choice |
| **D-22** | Plot names must match `^[a-z0-9][a-z0-9_-]*$` | A plot name becomes a path, so `../` is refused before any filesystem call. Stricter than the rest of the read face, which passes the name to `open_plot` unvalidated. If an existing plot name has capitals or dots, these routes cannot reach it | An existing plot breaks the rule: widen the pattern, never drop it. Whether the other routes should validate the same way is a separate question (API-3) |
| **D-23** | Router is thin; all logic lives in the preview module | Every decision is testable without a server or FastAPI installed | Never |
| **D-24** | HTTP mapping: not_found 404, ambiguous 409, unavailable 409, malformed 422, registry 500. Detail is a plain string, matching every other route on the read face (revised after reading `app.py`; the first version used a dict) | `ambiguous` and `unavailable` share 409 and are told apart by their message. The demo page's `fail()` shows `status path` only, so it will not show either message unless the page reads the body | A client needs to branch on the kind without parsing prose: add a structured detail across the whole read face, not here alone |
| **D-25** | The hand check (`compare`) lives in the preview module as a CLI subcommand, not as an API route | The comparison uses exactly the derivation the API serves. It is labelled a hand check in every result and never becomes an artifact | Replication becomes a method with an envelope (Sprint 2 proper), and the check becomes a test |
| **D-26** | New registry entries carry no `replicates` block until checked; the column name is copied from CII's file, never typed from memory | `replicates` now means verified. The CII file header must be pasted, not recalled | Never. This is L-69 applied |
| **D-27** | `cii_rent_burden` declared `aggregation: none` | A median refuses to combine. Rolling up to a larger unit needs recomputation from the binned distribution (B25070), a separate acquisition | Never for a median |
| **D-29** | The indicator routes are a declared exception to "every read is a projection of PlotReading", stated in `app.py`'s docstring and at the mount point. Mounted as a router in `canopy/api/indicators.py`, tagged `read` like the rest of the face | The CLI and the API still agree, because both call `indicator_preview`; but `/plots/maine/holdings` will list `acs_county_2024` as declared-unconformed while `/plots/maine/indicators` lists its indicators as derivable. Both are true, of different things | `derive_indicator.R` writes `indicator_values` into loam: the values route then reads loam and the exception is withdrawn |
| **D-30** | `indicator_preview` resolves the root through `canopy.paths.project_root()`, not its own file location | One root for the garden; a second derivation of it could disagree the day the package moves | Never |
| **D-31** | The published CII file lives at `garden/reference/cii_2026.csv`, not in `.data/`, which holds this plot's acquisitions. A reference a method is checked against is not a holding | The header test skips when the file is absent, so a fresh clone still passes. Its 3 144 rows are not redistributed by the repo unless you commit them; check CII's terms before you do | A grove-level reference area exists |
| **D-32** | Agreement is judged at the publisher's precision: ours agrees if it is within half a unit of the column's last published decimal (revised by PRV-3; it was per row) | The demo claim becomes "agrees at the precision CII published" rather than "difference 0", which full precision cannot print against a 7-decimal file. A real difference still shows as DIFFERS | Never; it is what "matches" means against a rounded publication |
| **D-28** | `cii_no_vehicle` assumes B08201; B25044 recorded as the second hypothesis in its rationale | The hand check decides. A mismatch is a finding, not a failure | The check fails and B25044 matches: change two codes |

## SPRINT 2b ~ the pipeline path (added after the demo-prep commit 66be662)

### DECISIONS

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-33** | A new reference type, `$indicators.<id>`, resolved by `ReferenceResolver` in params only, to the indicator's declaration from the registry | R never reads YAML; a variable code is written in one place. The full declaration lands in the step's provenance params, so every envelope records the definition that produced it. `$indicators` as an input is refused by name | A second consumer needs a different shape: add a method beside `as_declaration`, never a second parser |
| **D-34** | `IndicatorRegistry.declaration(id)` carries the sha256 of the file the indicator is declared in | An edit to `cii_2026.yml` changes the hash, so two envelopes made from different versions of a definition are distinguishable even where the values agree | A per-indicator hash is wanted rather than per-file: hash the canonical JSON of the declaration instead |
| **D-35** | `time`, `authority`, `spatial_unit` reach `derive_indicator` as experiment params, written in the experiment | **A duplication**: the vintage is already in the manifest. Accepted for one experiment; the fix is a `$sources.<dataset>.<field>` reference so the experiment points at the manifest instead of restating it | That reference exists |
| **D-36** | `derive_indicator.R` refuses declarations that arrive as a data.frame (inline JSON) instead of half-parsing them | ARG-1 is contained at this primitive; hand-testing must pass params as a file, which is what the oracle test does | ARG-1 is fixed in `args.R` |
| **D-37** | The oracle test runs the primitive through `Rscript` with params as a file, exactly as the orchestrator does, and compares value, moe, moe_status and empty_reason to the Python preview | The preview is now used as what D-16 said it was. Skipped where Rscript or rewildr is absent, so it is silent in CI without R | Never |

| **D-38** | The method `cii_indicator_values` requires only `indicator_source`, and says in its own words that it produces raw values, not scores | A value from this method cannot be read as a rank or a standard, because the method declares it is neither |  Never |
| **D-39** | `map` refuses a choice it used to make: more than one candidate result or layer is refused with their names, chosen with `--result` / `--layer` (fixes MAP-1) | **Behaviour change.** A command that worked by luck now asks. If the NYC flow relied on first-by-filename, it will now name its candidates and stop | Never; the luck was the bug |
| **D-40** | A long-form table maps one indicator at a time (`--indicator`), joined on its declared key: `unit_authority: us_census_geoid` means the layer's `GEOID`. A layer without it is refused by name | No county is ever matched by name. Each indicator writes its own `harvest/map_<indicator>.geojson` | A second unit authority appears: add it to `_UNIT_KEYS` |
| **D-41** | An empty value is drawn grey at lower opacity, counted in `rewilding:map.empty_values`, and never placed on the color ramp | A gap reads as a gap, not as the lowest value. NaN no longer breaks the ramp for the whole map | Never |
| **D-42** | `soil/transform/assign_geoid.R` derives GEOID as state FIPS + county code zero-padded, refusing non-numeric codes, codes wider than declared, duplicate GEOIDs, and an existing output field | The join the manifest called derivable becomes a recorded step with an envelope. Refusing duplicates keeps an undissolved layer from multiplying joined rows | A layer arrives already carrying an authoritative GEOID: skip the step |

### FINDINGS

| ID | item |
| --- | --- |
| **MAP-1** | `map` keyed envelopes by semantic type and kept the first by filename. Maine's counties and towns are both `governance_unit`; counties won because "c" sorts before "t". Fixed by D-39 |
| **MAP-2** | `map` colored by the first numeric column when nothing was declared, and refused to color at all if any value was empty, since one NaN failed the all-numeric check. Fixed by D-40 and D-41 |
| **EXP-1v** | Verified on Kalli's machine: `visuals.render` calls `_publish_arcgis` whenever `_arcgis_reachable()`, lines 162 to 164. Her `visuals.py` differs from the project copy (sha 4814f98 vs 21ac8aa), so the fix waits for the current file. **Until then, the descriptor path of `rewilding map` publishes to ArcGIS Online whenever credentials are present** |
| **REG-5** | `roots/_registry.yml` declares ten primitives twice. YAML keeps the second silently. All ten pairs differ: most in description, `score_composition` in inputs, outputs and params, `space_cooling_potential` in version and params. The vocabulary refuses this loudly; the registry loader does not. Left untouched tonight |
| **COR-3** | `correlation_analysis.R` emits no `crs`, which `envelope.schema.json` requires, so its envelope would fail validation. It is also absent from `roots/_registry.yml`, so nothing can run it. Joins COR-1 and COR-2 |
| **EXP-1** | **From the project-folder copy of `canopy/visuals.py`, possibly stale; verify.** `render()` publishes to ArcGIS Online whenever the machine is online and `GIS("home")` has credentials, with no gate and no confirmation, and swallows any publish error. The choropleth path in `map.py` never publishes; only the descriptor fallback does. If current, this is the publish P-22 exists to prevent |
| **TPL-1** | `method_template.yml` and `experiment_template.yml` in the project folder are empty files |
| **API-4** | `derive_indicator.R` was written without R in the sandbox. **First execution, on Kalli's machine: the oracle test passed.** R and Python agree exactly on every value, margin, status and empty reason |
| **API-5** | `assign_geoid.R` was written without R in the sandbox and has not run. It needs a soil registry entry, which waits for the current `soil/_registry.yml` |

## SPRINT 2c ~ standing among the nation

### FINDINGS

| ID | item |
| --- | --- |
| **CII-8** | **CII's per-indicator percentile rule, recovered from CII's own file.** Average rank of the oriented value (negated for the 12 reversed indicators), divided by the **largest rank**, times 100, over the counties that have a value. Reproduces **26 of 27** percentile columns across all 3 144 counties to CII's rounding (max difference 5e-8). The textbook `rank / n` differs only when the top value is tied, and then badly: 22 points for total news outlets, 17 for high-poverty neighbourhoods, 0.14 for no-vehicle (ten counties tied at 0%). Each indicator's reference population is its own: rent burden ranks 3 129 counties, not 3 144, so missing values are excluded, not imputed, at this stage |
| **CII-9** | The 27th, journalist equivalents, fails by 0.68 because CII's published raw values are rounded to 8 decimals while its percentiles were computed unrounded: about 100 Illinois counties show an identical `0.05545795`, yet CII ranks Clark County above the rest. A lossy publication, not a different rule. **Hypothesis, unverified:** a whole state sharing one per-capita value looks like a state figure broadcast to counties, as volunteer rate is |

### DECISIONS

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-43** | The Maine plot holds a national acquisition, `acs_us_county_2024` (`state: "*"`), because CII's reference population is the nation and Maine is a view onto it | 3 222 rows, Puerto Rico's 78 included. Belongs in the grove; lives here, declared, until the grove exists. `indicator_preview` and `compare` now need `--dataset` for these indicators, since two sources list them (D-21 working as designed) | The grove holds reference populations |
| **D-44** | Puerto Rico is excluded from the reference population by a declared param (`exclude_state_fips: ["72"]`), never by filtering the acquisition | The data stays whole; the population is a stated choice; an excluded unit keeps its row with no standing and the reason | Never |
| **D-45** | One primitive, `standardize_indicator.R`, gives an oriented z-score and CII's percentile per unit and indicator | The percentile is checkable against CII and checked; the z is not, and says so | Pillar composition needs z separately: split then |
| **D-46** | The z-score's SD convention is a required choice (`sd: sample` or `population`), with no default anywhere in the primitive | CII does not publish z-scores, so its convention cannot be recovered; making it a choice keeps an unrecoverable fact from becoming a silent one. At n of about 3 000 the two differ by under 0.02 percent | CII publishes its z-scores or documents the convention |
| **D-47** | A new semantic type, `indicator_standings`, named for what it is: a relative standing. Its description states it cannot express a standard | Nothing downstream can read a percentile as sufficiency without contradicting its own type | Never |
| **D-48** | The experiment's `curiosity.ref` is empty, because no civic-information curiosity exists in the curiosity space yet | **Unverified** whether the resolution engine or lineage enrichment requires one. If the run complains, the fix is a curiosity file, not a workaround | A curiosity is written |
| **D-49** | `map` colors a long-form table by `percentile` when it has one, else by `value` | A standings map shows standing. Joined to Maine's 16, the other 3 206 rows are reported as unjoined, which is expected and printed | A `--color-by` option is wanted |
| **D-50** | The national manifest block is delivered as an append file, not a whole-manifest replacement | The live manifest has been edited by the surgeon since it was last shared; replacing it would undo recorded acquisition state | Never for the manifest |

### OPEN

| ID | item |
| --- | --- |
| **API-6** | `standardize_indicator.R` has not run; `tests/test_standardize_oracle.py` is its first execution |
| **CII-10** | Run `compare --percentile --dataset acs_us_county_2024 --exclude-states 72` for each indicator once the national source is acquired: ours against CII's percentile columns, all 3 144 counties |

## DEMO ~ 2026-10-08

| ID | item |
| --- | --- |
| **DEMO-1** | `demo/civic.html`: a sibling to `index.html`. The agreement matrix is computed in the browser from the live API against CII's published Maine values, embedded with their original strings so precision is the column's. Simulated against Kalli's real values from 2026-10-07: 48 of 48. Registry and sources are live; the 409 refusal to choose between two sources is shown live. The 27-indicator rule table and the findings are static and labelled static |
| **DEMO-2** | `garden/experiments/demo_precondition_gate.yml`, wrong on purpose: raw ACS into `standardize_indicator`. The real `check_preconditions` was run against it: refused with "provenance_contains: derive_indicator not satisfied"; the correctly wired input is approved with both approvals recorded as notes |
| **DEMO-3** | `demo/RUN_OF_SHOW.md`: 25 minutes, nine moments, a do-not-claim list |
| **TMP-1** | Temporal tracking, located: the manifest schema's `temporal` block (snapshot, seasonal, annual, multi-year composite; year; range; season), carried on `ManifestDataset.temporal` but read by nothing found so far; the provider's `vintage_window`; the append-only `.manifest_changelog.yml`; `time` on every derived row; D-21's refusal to mix vintages. Not built: series across vintages |

## NATIONAL CHECK ~ 2026-10-08

| ID | item |
| --- | --- |
| **ACQ-5** | `acs_us_county_2024` acquired: 3 222 counties (Puerto Rico's 78 included), 10 variables, 2 changelog entries. The acquire report named both indicator_source holdings as "a choice for you, not for the engine" |
| **PRV-4** | The column-precision rule from PRV-3 was wrong for CII's percentile columns, which are written to a fixed **width** of 10 characters, not fixed decimals: `92.3664122` (7 dp), `5.08905852` (8 dp), `0.03180662` (8 dp). It reported 593 of 3 144 agreeing for broadband when every difference was under 5e-8. Precision is now inferred from the format: where at least 75 percent of rows share one width, each row is held to the decimals a full-width rendering would have, so a short row with dropped zeros is held strictly (this also covers PRV-3: "30" in a width-4 column is 30.0). Otherwise, the column's most decimals. Validated by feeding CII's own raw values through `compare`: 3 144, 3 129 and 3 144 agree. A real 1e-6 difference still fails |
| **CII-11** | **CII left rent burden blank for 15 counties the ACS publishes**: Hancock GA, West Feliciana LA, Esmeralda and Eureka NV, Harding NM, Harding SD, Borden, Briscoe, Glasscock, Kenedy, King, Loving, McMullen and Terrell TX, Webster WV. Among the smallest counties in the country (Loving: 33 people). Ranking 3 144 counties instead of CII's 3 129 shifts every percentile by up to 0.25 points. **Why CII dropped them is unknown.** Hypothesis: the ACS median sits in an open-ended interval there ("50.0+" or "10.0-"), which ACS-6 also points at. Check by printing our values for those 15 |
| **D-53** | `compare --match-published-population` ranks only the units the publisher has a value for, so a check of the percentile rule is not confounded by a difference in who was ranked. Units left out are listed by name. A replication setting, not an analytical one: the experiment's own population stays the declared one |
| **CMP-1** | `compare` listed the 78 Puerto Rico municipios as `only_ours` though they were excluded by declaration. Now counted separately as outside the population by declaration |

## SPRINT 2d ~ CII's method, end to end

### FINDINGS

| ID | item |
| --- | --- |
| **CII-12** | **Who CII imputes, and who gets an index, recovered from its file.** Exactly 461 counties miss one indicator, and every one has all five pillars and an overall index: those are the imputed. The 163 missing two or more have no overall index and keep only the pillars with no missing component: a pillar with a gap is dropped, never averaged over what remains. Reproduced exactly by the oracle for all five pillars and the overall |
| **CII-13** | **Environmental Resilience is three indicators, not five:** household energy burden, disaster damages, heat wave days. The build guide's membership (adding unemployment and rent burden, "each in two pillars") was wrong. In all 13 multi-gap counties missing rent burden, CII still publishes this index, which is impossible if rent burden were a member; and these three on equal weights reproduce CII's ordering at Spearman 0.9993. With the correction, the 27 indicators partition the five pillars exactly, 7 + 6 + 4 + 7 + 3. This is the pillar the documentation-discrepancy finding said has no source documentation |
| **CII-14** | **Equal chips nearly reproduce CII's ordering.** Spearman against CII's published indices: News 0.990, Civic 0.988, Equity 0.999, Health 0.992, Environmental 0.999, Overall 0.987. The remaining gap is the unpublished advisory-group weights. Maine's overall percentiles land within 0 to 12 points of CII's |
| **RWR-1** | `safe_read_table` read CSV with R's default `check.names = TRUE`, which silently rewrote any column name with a space or punctuation: `Percent of households with broadband` became `Percent.of.households.with.broadband`, so a declaration naming the published column could never find it. Fixed with `check.names = FALSE`. **rewildr must be reinstalled for it to take effect** |
| **IDX-1** | The oracle treated only `None` as missing, so a `NaN` (what every value read back from parquet becomes) passed as present and poisoned the composite: overall Spearman fell to 0.099. Now `None`, `NaN` and `pd.NA` are all missing |
| **MAN-1** | The manifest append file for the national acquisition still began with `acs_us_county_2024`, already appended. Appending it again would have duplicated the key and YAML would have kept the second silently. Split into a file with only the new datasets |

### DECISIONS

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-54** | CII's published file is an authority in the system: `cii_2026_published`, an `indicator_source`, with 27 passthrough indicators generated from its header (`seeds/indicators/cii_2026_published.yml`) | CII's full method runs today. Three of the 27 share `measures` with this system's Census derivations, so `registry.measuring()` returns both authorities side by side | Providers exist for the original sources: the published passthroughs remain as the replication reference |
| **D-55** | `$weights.<id>` resolves a declared weighting with its sha256, as `$indicators` does. Weightings live in `seeds/weights/`, loaded by `canopy/weights.py`, which refuses a missing `is_publishers_weighting`, an undeclared indicator, or a CII chip budget spent wrongly | Every index records whose weights produced it and which version of the file | Never |
| **D-56** | Tonight's weighting is `cii_2026_equal_chips`: CII's budget (10 x n within, 50 across), spent evenly, declared `is_publishers_weighting: false` | `weighted_index` warns on every run that the weighting is not CII's | CII publishes its allocation: add it as a second file |
| **D-57** | `derive_indicator` reads a unit key other than GEOID (`unit_column`, `unit_pad`, `name_column`), refusing codes that are not digits, wider than declared, or duplicated | A published file that lost leading zeros (CII-6) is repaired by declaration, and the padding is recorded as an info warning | Never |
| **D-58** | `impute_nearest_neighbor.R`: only units missing exactly one; donors are complete units; stage one is the k = 10 smallest sums of absolute z differences across the other indicators, stage two the nearest by great-circle distance (mean Earth radius 6371.0088 km). Ties break on similarity then GEOID in C-locale order. The donor's z is copied; each imputed row records donor, similarity, distance and shortlist | Exact agreement with the oracle is designed for: sequential sums in declared order, `s * s` squares. Percentiles are not recomputed for imputed values, since CII's precede imputation | CII documents a different similarity or donor rule |
| **D-59** | `weighted_index.R` serves both levels: pillars from z-scores, composite from pillar percentiles, all components required at both | One rule, used twice, held to one oracle | CII's composite turns out to average pillar scores rather than percentiles: the presence check could not tell, and the 0.987 suggests percentiles are right |
| **D-60** | `unit_locations` is stored as parquet, and `impute_nearest_neighbor` refuses a numeric GEOID | CSV read by R would turn 01001 into 1001 and silently match nothing in nine states | Never |
| **D-61** | A method of its own, `cii_full_method`, declaring locations as critical and naming what their absence costs: no county is imputed, and 461 lose their overall index | The experiment's lineage names the method that actually describes it | Never |

### OPEN

| ID | item |
| --- | --- |
| **API-7** | `impute_nearest_neighbor.R` and `weighted_index.R` have not run; `tests/test_index_r_oracle.py` is their first execution |
| **MAP-3** | The end-to-end map still needs the dissolved Maine counties to carry a GEOID: `assign_geoid.R` needs its soil registry entry and the county chain from the ownership experiment |
| **GUIDE-1** | The CII replication build guide's pillar table is wrong for Environmental Resilience (CII-13) and its volunteer rate is wrong (CII-4). Correct both before it travels |

## THE CURIOSITY SPACE ~ 2026-10-08

### CORRECTIONS, from the 2026 CII report itself

| ID | claimed | actually |
| --- | --- | --- |
| **CII-13r** | Environmental Resilience was "the pillar with no source documentation", and its three-member composition a discovery | The report lists exactly those three indicators (p. 14) and every pillar's membership (pp. 15-19). The build guide was wrong; CII was not. What remains true: the data file's documented-sources table omits the pillar's sources |
| **CII-4r** | Volunteer rate is a state value broadcast to counties, unflagged | The report labels it "percent of state residents" (p. 16). Unflagged in the data file and dashboard, disclosed in the report |

### FINDINGS

| ID | item |
| --- | --- |
| **CII-15** | **CII's "Total news outlets" column holds only 0, 1 or 2**, integers, for every county in the nation. The report describes "total news outlets per 10,000 population" (p. 15). Cumberland is 2; Androscoggin, home of the Sun Journal, is 0. Likely an ordinal class (perhaps Medill's news-desert categories) rather than a count or rate. **Hypothesis: verify against Medill's coding.** If true, it explains why CII-8's `rank / n` ran 22 points off for this column: three values, enormous ties |
| **CII-16** | The report gives mental health providers per 100 000 on p. 14 and per 10 000 on pp. 18 and 39; the data column says per 10 000, and Maine's values (32 to 89) fit per 10 000 |
| **CII-17** | CII lists its own missing indicators: multilingual media, newsroom diversity, power-building organisations, belonging, civic education and attitudes, representation, community priorities, historical news deserts, cost of voting, working two or more jobs, walkability. Each is a curiosity with no method yet |
| **WON-1** | `possibility._candidate_methods` treats `compatible_methods: []` like an absent key and falls back to every method in the domain. A curiosity declaring "no method yet" would be offered every information method, including ownership concentration for "how does information move through my community". Absent should fall back; empty should mean none. Not fixed: the current `possibility.py` is needed |

### DECISIONS

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-62** | Canopy reorganisation, agreed in principle, not yet done: `canopy/indicators/` (registry, weights, preview, oracle), `canopy/core/` (envelope, primitive, pr_io, vocabulary, introspect, paths), `canopy/render/` (visuals), `canopy/infra/` (aws, terraform) | Every import moves; the grep of current imports comes first so no move is guessed | |
| **D-63** | Fifteen brainstorm curiosities in `garden/curiosity-space/information/`, v0.1.0. Each is one question; its sub-questions name their indicators in a proposed `indicated_by` field; four declare `compatible_methods: []` on purpose | All 31 registry indicators are asked about by some curiosity. `indicated_by` is read by nothing yet; compose needs it to bind a curiosity's indicators into the experiment it writes | The field is rejected: move the bindings into methods |
| **D-64** | The experiments written by hand earlier (`maine_cii_standings_2024`, `cii_full_method_2026`) predate the curiosity space and carry empty `curiosity.ref`. They should be recomposed by wonder once compose reads `indicated_by` | Hand-written experiments are scaffolding, not the design | |

## CURIOSITY SCHEMA v1.1 ~ 2026-10-08

| ID | item |
| --- | --- |
| **D-65** | `seeds/schemas/curiosity.schema.yml` v1.1 declares `compatible_methods` (array of `{ref, fit, description, sub_questions}`, `fit` in direct, complementary, partial) and `indicated_by` on sub-questions. An empty `compatible_methods` declares "no method yet"; omitting it falls back to the domain. Refs name a method by its index `id`. The schema stays open; closing it waits until existing curiosities conform. `partial` and `sub_questions` are new; `direct` and `complementary` were already in use |
| **D-66** | The 15 information curiosities, v0.2.0, use the object form: 11 bind methods with an honest fit, 4 declare none. All valid under v1.1, cross-references included (methods in the index, sub-question keys real, indicators in the registry) |
| **WON-2** | `possibility._candidate_methods` does `str(ref).split("/")[-1]` on each entry, which on the established object form produces a fragment of a dict's repr and matches nothing. The thermal curiosity's explicit bindings have never been used; it has always fallen back to every thermal method, which looked plausible and so was invisible. Fix: read `entry["ref"]` when an entry is a mapping |
| **WON-3** | `thermal_landscape_analysis` refers to `$methods/thermal/thermal_gradient_analysis`, the method's file name; its id is `buffer_gradient_analysis`. With WON-2 fixed, this binding would still miss. Fix the ref, and have the loader refuse a ref that names no indexed id |
| **SCH-1** | In the project-folder copy (possibly stale), `thermal_landscape_analysis` did not conform to v1.0 either: `name` instead of the required `question`, sub-questions without `question`, and a `requires` data block in a curiosity, which the schema says declares no data. Worth checking the live file |
| **WON-4** | A curiosity loader should check what JSON Schema cannot: a method's `sub_questions` are keys of the curiosity, `depends_on` names real keys, `indicated_by` ids are declared indicators, refs name indexed methods. The validation script used tonight does all four and could become `canopy/wonder/curiosities.py`'s loader |

## WONDER BINDING ~ 2026-10-08

| ID | item |
| --- | --- |
| **SCH-1v** | Verified on Kalli's machine with jsonschema: `thermal_landscape_analysis.yml` fails v1.1 and v1.0 alike (no top-level `question`; three sub-questions without one). `image_composition_validity` and `park_cooling_effect` are valid |
| **SCH-2** | `information_access.yml` writes `compatible_methods` as a bare string, `information/ownership_concentration_analysis`. Both shapes exist in the garden. v1.1 declares only the object form; the reader accepts both (L-70), and the file should migrate once its `fit` is chosen by its author |
| **WON-1f, WON-2f** | `possibility._candidate_methods` now reads both shapes through `method_id_of`, treats `[]` as no method and an absent field as the domain fallback, and de-duplicates. **Not yet verified as the live path:** `explore()` binds through `reading.read_plot`, and nothing in `possibility.py` calls `_candidate_methods`; whether `reading.py` imports it is unknown until that file is read |
| **WON-3c** | Consequence of honest binding: `thermal_landscape_analysis`'s complementary method, referenced by file name, used to appear through the domain fallback and now does not. The fix is the ref (`buffer_gradient_analysis`), not a fallback |
| **WON-5** | Both loaders, `possibility._load_dir` and `wondering._load_by_id`, swept every `*.yml` and loaded `curiosity-space/index.yml` as a curiosity named `index`. Both now skip `index.yml` |
| **WON-6** | `compose` could not draft an indicator experiment: a string `requires_primitives` entry fell through to the placeholder `roots/analysis`; a tabular input was given `soil/validate_vector` and a reprojection, against the frame law; and no params were bound. The first two are fixed. **The third is a design fork:** compose has no way to fill a primitive's params, such as `indicators`, from the curiosity's `indicated_by` |

## RECIPES ~ option A, 2026-10-08

| ID | item |
| --- | --- |
| **D-67** | A method may declare a `recipe:`, its own steps. `compose` fills compose-time references and writes plain values into the experiment: `$requires.<name>` (bound dataset), `$curiosity.indicated_by` (the chosen sub-question's indicators the bound source can serve), `$weighting.<id>.components`, and `$source.<fact>` (authority, vintage, unit_column, unit_pad, name_column, read from the manifest). `$choices`, `$steps`, `$weights`, `$indicators` and literals pass through for the orchestrator. Implemented in `canopy/wonder/recipe.py`, wired into `wondering.compose`; a method without a recipe gets the old draft |
| **D-68** | Binding a requirement: chosen, or the only candidate, or none (left visibly missing). Two or more candidates is a refusal naming them. A chosen dataset that cannot serve the requirement is refused |
| **D-69** | An indicator the curiosity names but the bound source cannot serve becomes a guidance note naming the dataset that can, never a silent drop and never averaged in. One question with two authorities composes as two experiments |
| **D-70** | A compose-time parameter that resolves to nothing is left out of the experiment, so the primitive's default applies and the file never claims a null |
| **D-71** | `cii_2026_published` declares `unit_column: FIPS`, `unit_pad: 5`, `name_column: Name` and `temporal.label: CII 2026 edition` in the manifest. The unit repair and vintage are said once, by the source. Retires D-35's hand-typed duplication for composed experiments |
| **D-72** | Hand-written experiments `maine_cii_standings_2024` and `cii_full_method_2026` are superseded: compose now writes the same chains with real curiosity and method refs. Keep them until a composed run has succeeded, then retire them |
| **WON-7** | `wondering._manifest_types` keeps the first dataset of each semantic type, so the generic draft would bind `acs_county_2024` over `acs_us_county_2024` in silence (MAP-1's pattern). The recipe path uses `_manifest_datasets` and refuses instead; the generic draft still has the old behaviour |
| **SCH-3** | `recipe` is not declared in the method schema. Needs the current `method_schema.yml` |

Verified in the sandbox against a copy of the real seeds, curiosities and methods: broadband's `subscription` composes to `cii_broadband` from the ACS and `cii_pub_broadband` from CII's file, each naming the other; `civic_health_overall` composes CII's five-step chain with 27 indicators; every composed parameter resolves through the real `ReferenceResolver`, and no compose-time reference reaches an experiment. 11 recipe tests, 10 binding tests.

## D-62, PART ONE ~ canopy/indicators/

| ID | item |
| --- | --- |
| **D-62a** | `canopy/indicators/` is a package: `registry.py` (was `canopy/indicators.py`), `preview.py` (was `canopy/indicator_preview.py`), `oracle.py` (was `canopy/index_oracle.py`), `weights.py` (was `canopy/weights.py`). `__init__.py` exports `Derivation`, `Indicator`, `IndicatorRegistry`, so `from canopy.indicators import IndicatorRegistry` is unchanged everywhere, including `census_acs.py`. 26 references rewritten across code, tests and docs; none of the old paths remain. The hand check is now `python -m canopy.indicators.preview`. 107 Python tests pass in the new layout |
| **REORG-1** | The move was started by hand without an `__init__.py`, so Python treated the folder as a namespace package and `canopy.indicators` exported nothing ("unknown location"). It surfaced in one test because only that one imported the registry in that run |
| **REORG-2** | The hand-moved `indicator_preview.py` (30 725 bytes) was older than the latest (34 079): it lacked PRV-4's format-aware precision and `--match-published-population`. The finished package carries the latest |
| **D-62 remaining** | `canopy/core/`, `canopy/render/`, `canopy/infra/` still to move, each after its own import grep |

## FIRST COMPOSED RUN, AND WHAT WONDER WOULD HAVE SAID ~ 2026-10-08

| ID | item |
| --- | --- |
| **RUN-1** | **The first composed experiment ran end to end**: `maine_broadband_access_subscription__cii_indicator_values_91b5c0`, composed by `wonder.compose` from `broadband_access.subscription` and the `cii_indicator_values` recipe, bound to `acs_us_county_2024`. Two steps, two envelopes, 3 222 rows. All 16 Maine percentiles agree with CII's published broadband percentiles to the four decimals printed (max 0.00005) |
| **WON-1v, WON-2v** | Verified as the live path: `reading.read_plot` imports `_candidate_methods` from `possibility`, so the binding fix governs `wonder` |
| **WON-8** | A method's `reference_population` choice does not constrain which source binds. Binding `acs_county_2024` under the default `nation_50_states_dc` would label a Maine-only percentile as national. The choice should constrain the binding, or the binding should set the choice |
| **WON-9f** | `reading._read_method` met requirements only from conformed tiers, so a raw indicator source, which a derivation reads as it arrived, could never be met and every civic method read as blocked. A requirement may now declare `as_acquired: true`; it is met when the manifest marks the dataset available and its file is on disk, and the reading labels it `as_acquired`. Declared-but-unfetched stays a gap. Both civic methods declare it on their source (and the full method on its locations). `compose` still counts any tier as present, a looser reading than this; the two should converge |
| **WON-10** | `compose`'s guidance lists every sub-question under "what you will learn" even when composed for one. It should name the chosen sub-question and list the rest as needing other data |
| **WON-11** | `explore` emitted one possibility per method, so a curiosity declaring `compatible_methods: []` vanished from `wonder`. It is now rendered with the verdict `unanswered`, last in order, saying no method answers it yet |
| **WON-12** | `read_plot` skips any curiosity without a `question`, silently. `thermal_landscape_analysis` (SCH-1) is therefore absent from `wonder`. Correct to skip, wrong to be silent: the reading should report what it could not read |
| **D-73** | `assign_geoid` registered in `soil/_registry.yml`. A preparation method, `county_units_for_mapping`, carries the county chain as a recipe (repair, dissolve on COUNTY after filtering ISLAND n and LAND y, GEOID from CNTYCODE). A hand-written experiment, `plots/maine/experiments/maine_county_units.yml`, runs it with `units_*` step ids so the ownership experiment's county artifacts are not overwritten. Preparation answers no curiosity, so it is not composed from one |
| **MAP-4** | With the GEOID'd counties, `rewilding map maine indicator_standings --indicator cii_broadband --layer units_geoid_with_geoid` should draw Maine's 16 counties colored by national percentile, reporting the other 3 206 rows as unjoined. The publish latch (EXP-1) is still not built; the map writes geojson only |

## OPEN ~ add

| ID | item |
| --- | --- |
| **IND-3** | Add `proportion` to `DERIVATION_KINDS`, so a ratio whose numerator sits inside its denominator can carry the Census proportion MOE formula and its ratio-formula fallback |
| **ACS-5** | The provider empties Census annotation values and keeps only their count, so *which* cell was emptied, and why, is lost. In an `_M` column `-555555555` means controlled (zero sampling error by design), and emptying it turns known into unknown. The API exposes `_EA` and `_MA` annotation variables, which may be the clean fix. Verify before designing |
| **ACS-6** | `JAM_VALUES` labels `-333333333` "not applicable". Census documentation, as I understand it, uses that code for a median's margin when the median falls in an open-ended interval. Matters for `cii_rent_burden`, which is a median. **Unverified: check the Census annotation reference before changing it** |
| **ACQ-4** | A source whose declaration changed after it was acquired is not seen as stale. Adding two indicators to `acs_county_2024` left `acquire --type indicator_source --fetch` reporting "you already have this ~ it has never been run" and fetching nothing, so the parquet still lacks the new variables. Staleness is derivable: the changelog records `variables_requested`, and the registry resolves what the declaration needs now. A mismatch should read as "declared differently than acquired," never as "already have" |
| **API-3** | The rest of the read face passes plot names to `open_plot` and builds paths like `plots/<plot>/.envelopes` without validating the name. Probably harmless while bound to localhost; worth one shared validator before anything is reachable from elsewhere |
| **API-2** | The router is untested against a live server. FastAPI is absent from the sandbox it was written in. First run is the test |
| **TST-1** | `test_indicator_preview.py` (31 cases, CSV fixtures) passed in the sandbox through a pytest shim, not pytest itself. Run it under real pytest. Check whether any existing registry test asserts exactly two indicators; it now finds four |
| **ARG-1** | (carried from last session) `args.R` parses params from a file with `read_json` and inline with `fromJSON(simplifyVector = TRUE)`, so a list param arrives as a list under the orchestrator and a vector by hand |

## FINDINGS ~ add

| ID | item |
| --- | --- |
| **CII-3** | The registry's `cii_broadband.replicates.column` was "Percent of households with broadband of any type", from the report's prose. The published header is "Percent of households with broadband". Fixed, and a test now asserts every `replicates.column` is an exact header in the file. The sixth instance of L-69's family, and the first one a test now guards |
| **CII-4** | The build guide says volunteer rate is 19.9 in every Maine county. The published file says **34.9**, in all sixteen. The finding (a state value broadcast to counties, unflagged) stands; the number in the guide was wrong |
| **CII-5** | Published column names, copied from the header for the two unverified entries: `Percent of income spent on rent` (one decimal, consistent with B25071's published precision) and `Percent with no vehicle available` (about 8 decimals, consistent with a derived ratio) |
| **CII-6** | 318 of 3 144 FIPS codes are four digits, with the leading zero lost (states 01 to 09). `normalise_fips` restores them; any join that skips this silently drops nine states |

## CLOSED ~ add

| ID | item |
| --- | --- |
| **CII-7** | **Three CII indicators reproduced from the repo, 48 of 48 county values.** Broadband 16/16 at 7 decimals (max diff 4.7e-8); rent burden 16/16 at 1 decimal (diff 0.0 everywhere); no-vehicle 16/16 at 8 decimals (max diff 4.6e-9). All at ACS 2020-2024, all correlation 1. Each now carries `replicates` |
| **D-28r** | Resolved: CII's no-vehicle indicator is B08201 (household size by vehicles available). B25044 not needed |
| **ACQ-4w** | Workaround used and worked: old parquet moved aside to `acs_county_2024_before_2a.parquet`, `available: false` set by hand, acquire fetched 20 variables and recorded 2 changelog entries. The real fix (staleness from `variables_requested`) stays open as ACQ-4. Which of the two steps the engine needed is unknown |
| **PRV-3** | Agreement was judged at each row's written decimals, so a row written `30` (a spreadsheet dropping `.0`) got a tolerance of 0.5 and 30.4 would have agreed with it. Seen in real output: rent burden showed `[0, 1]` decimals. No result was affected (every rent difference was 0.0), but the check was looser than it claimed on two rows. Precision is now the column's: the most decimals any row shows. Mutation-checked. My own earlier test had encoded the loose rule and was corrected |
| **PRV-2** | `compare` with a missing published file raised a raw pandas `FileNotFoundError` traceback instead of a refusal. Now refused as `not_found`, naming the path and the directory it was resolved from. Found on first real use |
| **D-17v** | Verified on Kalli's machine: `plots/maine/.data/acs_county_2024.parquet` exists, so plot-relative cache resolution is correct |
| **API-1** | Router mounted at the end of `canopy/api/app.py`. Checked every existing route: nothing shadows `/plots/{plot}/indicators`, and CORS already allows GET |

## CORRECTION ~ add to "Withdrawn"

| ID | claimed | actually |
| --- | --- | --- |
| **COUNT-2** | Adding rent burden and no-vehicle takes the acquisition from 14 to 22 variables | **20.** The no-vehicle weight is its own denominator and is deduplicated. Verified by `resolve_variables` (21 in the request with NAME). Plausible arithmetic stated as fact; the fifth instance of L-69's family |

## LESSONS ~ add

**L-74 ~ A preview that says it is a preview is honest; one that does not is a
lie with good formatting.** The label has to be on every row, not only on the
response, because rows get copied out of responses.

**L-75 ~ `x and y` as a comprehension source is a riddle, not a condition.**
Written once tonight, caught on reread, replaced with an explicit branch. A
line that needs a second read to know what it iterates over will eventually
be read once.