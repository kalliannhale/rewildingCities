# Build Ledger ~ rewildingCities

One ledger for the whole build. Every finding, decision, lesson and wrong
hypothesis is recorded here with an ID, what it implies, and what would
reverse it, so any of them can be revisited without archaeology.

## How IDs work here

- **This ledger's IDs never change.** Decisions are D-n, lessons L-n, and
  findings carry a topic prefix (CII-, MAP-, ACS-, WON-, and so on). New
  decisions continue from **D-98**, lessons from **L-78**.
- **Master Plan decisions are MP-67 to MP-81.** The plan numbered them D-67
  to D-81, which this ledger had already used (D-93). Cite them as MP-n.
- **The infrastructure plan's D-1 to D-12 and the publish route's P-1 to P-5**
  are defined in those documents, not here. Cite them as "infrastructure D-n"
  and "publish route P-n" so they are never read as this ledger's.
- **Cited but not defined in this file:** D-1 to D-15, L-1 to L-73, P-22,
  C-65, COR-1, COR-2 (LED-1). D-51 and D-52 were never assigned.

## Where this file came from

Merged in Sprint 00 (2026-11-10) from `build_ledger.md`, which held only the
Civic Sprint 2a delta, and `ledger_civic_sprint_2a.md`, which held that delta
and everything through 2026-10-08. Every entry from both is kept with its ID
and its words. The 2a delta's open, findings, closed, correction and lessons
blocks, which had drifted to the end of the file, now sit with the rest of 2a.

---

## CIVIC SPRINT 2a ~ demo prep

Every decision below was made by Claude without consultation, at Kalli's
request ("go with what you lean toward").


### DECISIONS

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


### OPEN ~ add

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

### FINDINGS ~ add

| ID | item |
| --- | --- |
| **CII-3** | The registry's `cii_broadband.replicates.column` was "Percent of households with broadband of any type", from the report's prose. The published header is "Percent of households with broadband". Fixed, and a test now asserts every `replicates.column` is an exact header in the file. The sixth instance of L-69's family, and the first one a test now guards |
| **CII-4** | The build guide says volunteer rate is 19.9 in every Maine county. The published file says **34.9**, in all sixteen. The finding (a state value broadcast to counties, unflagged) stands; the number in the guide was wrong |
| **CII-5** | Published column names, copied from the header for the two unverified entries: `Percent of income spent on rent` (one decimal, consistent with B25071's published precision) and `Percent with no vehicle available` (about 8 decimals, consistent with a derived ratio) |
| **CII-6** | 318 of 3 144 FIPS codes are four digits, with the leading zero lost (states 01 to 09). `normalise_fips` restores them; any join that skips this silently drops nine states |

### CLOSED ~ add

| ID | item |
| --- | --- |
| **CII-7** | **Three CII indicators reproduced from the repo, 48 of 48 county values.** Broadband 16/16 at 7 decimals (max diff 4.7e-8); rent burden 16/16 at 1 decimal (diff 0.0 everywhere); no-vehicle 16/16 at 8 decimals (max diff 4.6e-9). All at ACS 2020-2024, all correlation 1. Each now carries `replicates` |
| **D-28r** | Resolved: CII's no-vehicle indicator is B08201 (household size by vehicles available). B25044 not needed |
| **ACQ-4w** | Workaround used and worked: old parquet moved aside to `acs_county_2024_before_2a.parquet`, `available: false` set by hand, acquire fetched 20 variables and recorded 2 changelog entries. The real fix (staleness from `variables_requested`) stays open as ACQ-4. Which of the two steps the engine needed is unknown |
| **PRV-3** | Agreement was judged at each row's written decimals, so a row written `30` (a spreadsheet dropping `.0`) got a tolerance of 0.5 and 30.4 would have agreed with it. Seen in real output: rent burden showed `[0, 1]` decimals. No result was affected (every rent difference was 0.0), but the check was looser than it claimed on two rows. Precision is now the column's: the most decimals any row shows. Mutation-checked. My own earlier test had encoded the loose rule and was corrected |
| **PRV-2** | `compare` with a missing published file raised a raw pandas `FileNotFoundError` traceback instead of a refusal. Now refused as `not_found`, naming the path and the directory it was resolved from. Found on first real use |
| **D-17v** | Verified on Kalli's machine: `plots/maine/.data/acs_county_2024.parquet` exists, so plot-relative cache resolution is correct |
| **API-1** | Router mounted at the end of `canopy/api/app.py`. Checked every existing route: nothing shadows `/plots/{plot}/indicators`, and CORS already allows GET |

### CORRECTION ~ add to "Withdrawn"

| ID | claimed | actually |
| --- | --- | --- |
| **COUNT-2** | Adding rent burden and no-vehicle takes the acquisition from 14 to 22 variables | **20.** The no-vehicle weight is its own denominator and is deduplicated. Verified by `resolve_variables` (21 in the request with NAME). Plausible arithmetic stated as fact; the fifth instance of L-69's family |

### LESSONS ~ add

**L-74 ~ A preview that says it is a preview is honest; one that does not is a
lie with good formatting.** The label has to be on every row, not only on the
response, because rows get copied out of responses.

**L-75 ~ `x and y` as a comprehension source is a riddle, not a condition.**
Written once tonight, caught on reread, replaced with an explicit branch. A
line that needs a second read to know what it iterates over will eventually
be read once.

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


## AFTER 2026-10-08 ~ the commits the October ledger never recorded

Written in Sprint 00 from `git show --stat`, commit messages and the code
comments each change left behind. Where a commit's intent cannot be read from
its files, the line says so and leaves it to Kalli rather than guessing.

### ID collisions found in code comments

The code reused four IDs the October ledger had already given to other
things. The code comments are left as they are for now; the ledger gives each
code meaning a fresh ID and says which comment it answers to.

| ledger ID | code comment says | what the October ledger meant by that ID |
| --- | --- | --- |
| **MAP-5** | MAP-2 (`map.py`, 6c8ffeb) | MAP-2: `map` colored by the first numeric column (fixed by D-40, D-41) |
| **MAP-6** | MAP-3 (`map.py`, 6c8ffeb) | MAP-3: dissolved counties need a GEOID (open) |
| **MAP-7** | MAP-4 (`map.py`, 6c8ffeb) | MAP-4: the end-to-end county map should draw (expected result) |
| **ACS-8** | ACS-6 (`census_acs.py`, 6f1fa76) | ACS-6: `-333333333` labelled "not applicable", unverified |

### DECISIONS

| ID | commit | decision | implication | reverse if |
| --- | --- | --- | --- | --- |
| **D-82** | 035b89a | `dissolve_by_field.R` fails, never warns, when the groups do not each get their own geometry or two groups come out the same shape (GEO-1) | A dissolve that hands every unit one geometry stops the run instead of producing sixteen counties that are each the whole state. Tested against the real R primitive; skipped without R | Never; the reduction lying about itself is the bug |
| **D-83** | 035b89a | `demo/render_choropleth.py` draws a harvest GeoJSON to a readable PNG | The demo image is a rendering of a harvest, so it is regenerable from one | A rendering is wanted from the publish door instead |
| **D-84** | 6c8ffeb | Scientific lineage is attached to every envelope **before** its receipt is written; gap scars, known only after the run, are rewritten into the scarred receipts in place, and a failed rewrite is reported (LIN-1) | Receipts on disk and the harvests read from them carry lineage instead of `lineage: null`, and a caveat the run earned reaches the harvest | Never |
| **D-85** | 6c8ffeb | A choropleth keeps every unit of its layer: a unit with no row is drawn empty and counted, never dropped (MAP-5). Unmatched rows are split by GEOID state prefix into rows outside this place (expected) and rows of this place that failed to join (a defect) | A town the source never measured stays on the map. A join defect can no longer hide inside the national reference population's unjoined count | A second unit authority needs its own scope rule: add it beside the GEOID one |
| **D-86** | 6c8ffeb | The result's processing chain and warnings travel inside the harvest as `rewilding:provenance` (MAP-6); the layer is part of the harvest's name, `map_<indicator>__<layer>.geojson` (MAP-7) | A published layer can say what produced it and what the run warned about. County and town maps of one indicator no longer overwrite each other | Never |
| **D-87** | 6c8ffeb | Towns are the Census's county subdivisions: `acs_cousub_2024` and `governance_unit_cousub` (TIGERweb, layer 1), 529 units, not the 924 civil divisions in Maine's own GIS | Values exist at the grain the ACS publishes. Unorganized townships are grouped as the Census groups them | Maine's 924-division geography is needed: a crosswalk, built as a preparation |
| **D-88** | 6f1fa76 | Census annotations are matched as numbers, whatever decimals they are written with (ACS-8) | `-666666666.0` on a median is recognised like `-666666666` on a count. Maine towns without renters no longer carry a rent burden of minus 666 million on the town map | Never |
| **D-89** | 4692b72 | Codes the provider empties are kept in a `<variable>_annotation` column; `-333333333` and `-222222222` relabelled | Which cell was emptied, and why, is no longer lost. Closes ACS-5 and the October ACS-6. A source acquired before this has no annotation column, and preview says so and asks for a re-acquire | The Census API's `_EA`/`_MA` variables prove cleaner |
| **D-90** | a607c53 | A passthrough derivation may declare `open_ended: {lower, upper}`, the edges of its distribution's end categories; an open-ended median (`-333333333` on its margin) is reported as a bound in words, never as a number, by both `preview.py` and `derive_indicator.R` | `cii_rent_burden` declares 10 and 50. Its value for those units sorts correctly but is an encoding, and the row says to read `bound` | Never for an end category |
| **D-91** | a607c53 | `cii_indicator_values` declares `aggregation_unit_level` as a choice: county (default), county subdivision, tract | The grain of a value is stated, never assumed. Finer grains carry wider margins, and the method says so | Never |
| **D-92** | e1c925b, 224efb7 | Publishing to ArcGIS is opt-in (MP-67); every publish that was asked for and could not happen raises `PublishError`, and `rewilding map` exits 1. Written by Ajitesh, reviewed and merged by Kalli | Nothing leaves for AGOL without `--publish`. 11 tests, a fake ArcGIS, the network refused | Never |

### FINDINGS

| ID | item |
| --- | --- |
| **LED-1** | `field-guide/docs/build_ledger.md` was created in 5ab2875 as the Civic Sprint 2a delta and was never the master ledger. `ledger_civic_sprint_2a.md` held all of it plus everything through 2026-10-08. Neither defines D-1 to D-15, L-1 to L-73, P-22, C-65, COR-1 or COR-2, though both cite them, and D-51 and D-52 were never assigned. `git log -S "L-69"` touches 66be662, fe52842 and 5ab2875; **whether 66be662 holds the master ledger is unverified** |
| **COM-1** | 5ab2875 committed the work this ledger had already recorded on 2026-10-08 (D-73's `assign_geoid` and county preparation, WON-9f's `test_reading_acquired.py`, DEMO-1's page and DEMO-2's experiment), the Maine harvests (about 350 MB, raw), and also a YouTube provider, three comment soil scripts (`normalize_yt_comments`, `stratify_comments`, `window_comments`), `tests/llm_pilot.py`, `tests/pilot_pull.py`, `r_rev_codebook_v1.yml`, and the deletion of `tests/sprinting/test_injection_points.py`. **Intent of these: to be stated by Kalli.** |
| **DEMO-1c** | DEMO-1 names the page `demo/civic.html`; the file is `demo/index.html` |

## SPRINT 00 ~ clear the ground, 2026-11-10

### DECISIONS

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-93** | Master Plan decisions are cited as **MP-67 to MP-81**. The plan numbered them D-67 to D-81, which this ledger had already used for other decisions, and code cites this ledger's D-67. This ledger's IDs never change; new decisions continue from D-82 | One ID means one thing. The plan doc's tables still say D-67 to D-81 until they are relabelled | Never; renumbering the ledger would break the code's citations |
| **D-94** | Plot harvests leave git: `plots/*/harvest/` in `.gitignore`, removed from the index, kept on disk. Their canonical home becomes S3 (Sprint 07) | `git ls-files` lists no harvest outputs. A fresh clone has no `map_cii_broadband.png`, so the demo page's figure is missing there until it is regenerated with D-83 | Never |
| **D-95** | `garden/reference/` leaves git: in `.gitignore`, removed from the index, kept on disk | CII's file is no longer redistributed by new commits. The two tests that read it skip by name when it is absent, so a fresh clone passes. The analysis path reads `.data/cii_2026_published.csv`, already ignored | CII's terms allow redistribution, and committing the file is wanted |
| **D-96** | `rewilding map` exits 1 when `--publish` is given for a choropleth, after writing the map locally, with the descriptor path's words (`not published:`). Two tests: without the flag it exits 0; with it, online and credentialed, it exits 1, writes, names the path, and never signs in | A publish that was asked for and did not happen is never a quiet success. 13 tests pass | The publish door publishes choropleths: then the flag goes through it |
| **D-97** | The stray backups `canopy/indicators/preview.py.save` (tracked) and `canopy/providers/base.py.save` (untracked) are deleted | One copy of each module | Never |

### FINDINGS

| ID | item |
| --- | --- |
| **GIT-1** | The harvest rules (`harvest/maps/*` and the rest) contain a slash, so git anchors them to the root: they matched the top-level `harvest/` and never `plots/*/harvest/`. The Terraform section of the same file already explains this exact rule |
| **REPO-1** | The GitHub repository is **public** (checked 2026-11-10) |
| **CII-18** | **CII's full published file is in public history.** `garden/reference/cii_2026.csv` (3 144 counties, all 27 indicators) was committed in fe52842. `demo/index.html`, still tracked, embeds CII's published values and percentiles for Maine's 16 counties on three indicators, and the 27-indicator rule table |
| **CII-19** | No published terms of use or license for the CII data file was found. The 2026 edition is co-created by Listening Post Collective (Internews) and the Information Futures Lab (Brown); one trade article names the Civic News Company as publisher, so the licensor is uncertain. **Asked 2026-11-10** (to Listening Post's communications contact, Information Futures Lab copied): who holds the rights, whether the file may be kept in a repository, whether values computed from the ACS with CII's method may be published with attribution, and whether the demo's excerpt is acceptable. **Awaiting reply** |
| **CII-20** | No harvest file holds CII's data. The `cii_` prefix names this system's replication indicators: town maps carry `authority: us_census_acs`, and county standings are computed from `acs_us_county_2024` with CII's rule, matching CII's published percentiles to seven decimals. Whether a reproduced number counts as redistributing the publisher's number is part of the question asked in CII-19 |
| **AGOL-1** | The layers uploaded to Northeastern's ArcGIS Online from the `__upload` harvests are shared **private or organization**, not public. Nothing needed narrowing |
| **F4** | (from the publish route assignment) `introspect.has_credentials("arcgis")` checks `ARCGIS_API_KEY` or `ARCGIS_USERNAME`; the login is `GIS("home")`, which ignores both. `test_publish_online_with_credentials_uploads_once` encodes this as expected and now says so in a comment. Resolved by per-target identity in the publish door |
| **GIT-2** | The local pack is 7.54 GiB, but the largest reachable objects are the harvests at about 6 MB each on disk. **Hypothesis, unverified:** the bulk is unreachable local objects (old stashes, reflog, interrupted writes; two `tmp_obj` garbage files were reported), not shared history |

### OPEN

| ID | item |
| --- | --- |
| **HIST-1** | Rewrite history with `git filter-repo` to remove `garden/reference/cii_2026.csv` (and the harvests) from the public history, or not. Every teammate re-clones if so. Waits on CII-19's answer and on the team's timing |
| **COM-1a** | Kalli states the intent of 5ab2875's YouTube, comment and pilot files and the deleted injection-points test |
| **PLAN-1** | Relabel the Master Plan doc's decision tables from D-67 to D-81 to MP-67 to MP-81 (D-93) |
| **TAG-1** | Rename the code comments MAP-2, MAP-3, MAP-4 and ACS-6 to their ledger IDs MAP-5, MAP-6, MAP-7 and ACS-8 |

### LESSONS

**L-76 ~ A rule written down once in one section of a file is not yet a rule
for the file.** The Terraform block of `.gitignore` explained anchoring; the
harvest block above it broke the same rule, and 350 MB went to a public
repository through the gap.

**L-77 ~ An ID is a promise that it means one thing.** The plan, and later
the code, reused IDs the ledger had spent. Search the ledger before taking a
number.

## SPRINT 04, STEP 1 ~ the graph summary, 2026-11-10

`tests/debug/graph_summary.py` (read-only) checked the graph against Contract 3. Confirmed: 47 138 blocks, 1 362 359 persons, 16 counties, 151 House and 35 Senate districts, every district touched by a town. 46 towns touch more than one House district (at most 8); 5 touch more than one Senate district.

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-125** | Census tribal areas are keyed by the Census GEOID, AIANNH plus its component type (`2760R`, `2760T`), in the edges as in `places`. A reservation and its off-reservation trust land are two places | Maine's 8 Census legal areas are 8 places, and the edges' keys match layers 38 and 39 (D-123) | Consultation asks otherwise, or ACS keys tribal values differently (check when tribal values are joined) |

| ID | item |
| --- | --- |
| **TRIBE-1** | The edges keyed tribal areas by AIANNH alone: 6 keys for the Census's 8 areas. Houlton Maliseet (1530) and Penobscot (2760) each had reservation and trust land merged into one edge. The spine held both; the grouping dropped the component. Caught by the summary's key check |
| **MEGIS-2** | Contract 3 said 924 MEGIS civil divisions; MEGIS holds 923 distinct GEOCODEs in 924 polygons, as the manifest has said since 2026-09-18. Withdrawn: "924 divisions". MEGIS-1's one-character GEOCODEs do not appear after the dissolve; why is open |
| **DISS-1** | LURC (values y, n) varies within 13 GEOCODEs, so `dissolve_by_field` refused to carry it, correctly. Step 2's LURC flag cannot come from the dissolved layer |
| **TOWN-1** | The spine has 530 towns, ACS 2024 has 529. In 2020 only: 2301742835 (45 persons), 2301918580 (26), 2302913610 (13). In 2024 only: Drew UT 2301918582, Codyville UT 2302913612. Hypothesis, unverified: deorganizations after 2020. Contract 3's vintage invariant fails for towns: boundaries 2020, values 2024 |
| **DAS-1** | Households without persons: block 230219603011057 (2 households, 0 persons), town 2301978015, 31 division edges. Hypothesis, unverified: 2020 disclosure avoidance. Bears on D-121's null rules |
| **ZERO-1** | Overlaps with a population share of exactly 0 (land, no residents): 3 House, 1 Senate, 11 tribal, 50 division. MP-76's "every district they touch" would list a town under a legislator who represents none of its residents. Display rule open |
| **MEGIS-3** | Cove Point Twp and Kineo Twp hold no block internal point, so no edge; they are still places. 10 unplaced blocks hold 1 person. Of 65 divisions touching two Census towns, 3 disagree about people (Parlin Pond Twp 0.80, Tomhegan Twp 0.98, Greenbush 0.99); 62 are empty-block slivers |

**LESSON** ~ The summary's first run crashed on a keep_field it assumed had survived the dissolve. A probe that assumes a field exists repeats the bug it was written to find.

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-126** | Maine's towns are 2024 county subdivisions, from the 2024 TIGER/Line topological faces (16 county zips, combined into one). Each 2020 block goes whole to the town holding most of its land; split blocks are logged with their persons | The spine's 529 towns match ACS 2024 exactly. Tribal areas and civil divisions keep their own vintages, declared on every edge | The Census publishes a 2024 block-to-town relationship file |
| **D-127** | A block's county follows its 2024 town. The 2020 county stays as `county_2020`, and every block that changes county is listed | Counts by county match 2024 county boundaries, as ACS does | Never |

| ID | item |
| --- | --- |
| **TOWN-1** | Closed by D-126. The 2020 spine had 530 towns against ACS's 529: three 2020-only subdivisions, and two UTs ACS has that the spine lacked |
| **BOUND-1** | Waldo and Knox redrew their line in Penobscot Bay under P.L. 2023, c. 1 (LD 119), after the Census flagged a discrepancy in 2020. Three 2020 blocks in Knox are in Waldo's town 2302735240 in 2024: 230139711003030 (0 persons), 230139711003032 (9 persons, 2 households), 230139711003033 (0). The archipelago is the likely match; confirm on a map |
| **LWFLAG-1** | The 2024 faces carry L (89,101), P (18,376) and I (15). The Census counts G, I, L and S as land and P as perennial water (TIGER/Line user note 7). The first version counted only L and undercounted intermittent water |
| **FACE-1** | The Census's technical documentation says 2020 blocks never cross a boundary of an entity it tabulates. That holds for 2020 geography. After a 2024 boundary change, the faces show a block's land in another county. Contract 3 never stated the rule; contract 0.6 now carries the change instead |

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-128** | A place's `kind` comes from its 2024 LSAD (town, plantation, city, UT, reservation subdivision, gore); FUNCSTAT is kept verbatim in `census_funcstat` and never shown as a word | Portland reads as a city, not "fictitious". An unknown LSAD is refused | The Census changes its LSAD codes |
| **D-129** | A reservation subdivision is found by geometry (every block in a Census reservation) and names its tribal area in `part_of`. Penobscot Indian Island's two subdivisions are both part of 2760R | One place without inventing a code; a mismatch between LSAD and geometry is refused | Consultation asks otherwise |
| **D-130** | A MEGIS division is LURC if any polygon says so, and `lurc_mixed` if its polygons disagree; a town is LURC if any of its blocks is in a LURC division, with its population share | The rule is visible on every row it touches | MEGIS corrects the 13 mixed divisions |

| ID | item |
| --- | --- |
| **PLACES-1** | The places table built green: 1,663 places (1 state, 16 counties, 529 towns, 151 House, 35 Senate, 8 tribal areas, 923 divisions). Town kinds: 430 towns, 42 UTs, 29 plantations, 23 cities, 4 reservation subdivisions, 1 gore. 12 places carry the census_tribal_area note |
| **FUNC-2** | Maine's 23 cities are FUNCSTAT F (LSAD 25). The seed's F gloss missed them; corrected |
| **RES-1** | Geometry finds exactly the four LSAD 86 subdivisions. Houlton, Littleton and Old Town are partly in R areas: overlap edges, no flag |
| **LURC-1** | MEGIS: 451 divisions all y, 460 all n, 13 mixed (listed in the places probe), mostly islands with one n polygon |
| **NAME-1** | Matching names for "UT" found 55 places, including Yarmouth town; LSAD says 42. Codes, never names |
| **BAXTER-1** | Baxter State Park is not a Census subdivision and is in neither file; no flag until a source is chosen |
| **REVERT-1** | The commit after D-127 held the D-126 spine. The run that closed TOWN-1 used the D-127 code, so its findings stand; the D-127 spine was restored and committed here. Cause unconfirmed: likely the earlier full-file paste of the D-126 spine. Lesson: zips only, and `git diff --stat HEAD` before every commit |

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-131** | A value names whose codes key its units. `derive_indicator.R` requires `unit_authority`, one of Contract 3's five (section 1), with no default, and refuses a missing or unknown one by name. Every caller declares it: three methods, the cousub preparation and two experiments | A House district's 23001 can no longer key as Androscoggin County. The orchestrator does not enforce registry options, so the primitive does | The five move to one seed file both languages read (AUTH-1) |
| **D-132** | `measurement_id` is `indicator:unit_authority:code` | Ids stay unique when the grove reads tables from different levels together. Nothing joins on it; joins stay on (`unit_authority`, `unit_code`), as D-19 says | Never |
| **D-133** | The preview requires `unit_authority` everywhere, with no default: `derive()`, `preview()`, `compare()`, the CLI's `--unit-authority` and the API's `unit_authority` query parameter | A preview of `acs_sldl_2024` cannot label districts as counties. An API call without it is a 422 before anything is read. Kalli confirmed nothing else calls the endpoint | A manifest source declares its own (SRC-1) |

| ID | item |
| --- | --- |
| **TWIN-1** | The hand-off named `canopy/indicators/oracle.py` as derive_indicator's Python twin. It is `preview.py`: the agreement test calls `ip.derive`. `oracle.py` holds impute and weighted_index, never keys a unit, and is unchanged |
| **TWIN-2** | `preview.derive` read `r["GEOID"]` and `r["NAME"]` directly while the R honors `unit_column`, `unit_pad` and `name_column`. The twins agreed only because every source names its column GEOID. The preview now takes all three and refuses repeated codes as the R does. `read_table` still requires GEOID for a manifest source (SRC-1) |
| **SEAM-1** | `roots/indicators/weighted_index.R` builds `measurement_id` as `index:code`, without the authority. Safe while composites are county-only; it needs D-132 before any non-county composite |
| **AUTH-1** | The five unit authorities are written in four places: Contract 3 section 1, `build_places.py`, `derive_indicator.R`, `preview.py`. Their eventual home is one seed file. Contract 3 names `us_census_geoid` for state, county and town; tracts use it too (11 digits, no collision), and the contract should say so |
| **SRC-1** | Should a manifest source declare its own `unit_authority` and unit column? An SLDL acquisition is SLDL codes by nature. Proposed for Sprint 05 |
| **MAP-4** | `map.py`'s `_UNIT_KEYS` knows only `us_census_geoid`. District keys wait until a district value table is first mapped and the district layers' property names are verified. Until then map refuses the authority by name (line 106) |
| **COMP-1** | No CLI writes a composed experiment; `wonder` only explores. The `_91b5c0` experiment was edited by hand with the line its method now writes, a literal, so composition would write the same. Its suffix is a hash, so a recomposition may write a new file name |
| **REG-6** | Two soil registry entries pointed at no file: `validate_boundaries` at an .R never written (removed; `registry.py`'s docstring examples now name `repair_geometry`), and `fetch_dataset` at .R when the file is .py (fixed). The orchestrator checks a path only when a step uses it. `tests/test_registry_paths.py` now checks every entry in soil and roots |
| **REG-1** | Ten soil files are not registered: `filter/mask_raster_by_class.R`, `scope/clip_to_boundary.R`, `register/verify_manifest.py`, `validate/calibrate_from_stills.py`, `validate/normalize_yt_comments.py`, `validate/stratify_comments.py`, `validate/window_comments.py`, and `classify/rgb_landcover_features.py`, `classify/deep_backbone.py`, `register/manifest_utils.py`, which look like helpers. Which are primitives is open |
| **NAME-2** | Kalli would rather not use "authority" (`named_by` and `published_by` were considered). The word lives in Contract 3's four key fields, D-19, the places and edges tables, derive, preview, map and standardize. Deferred to a refactor of its own |

**LESSON** ~ zsh expands an unquoted `--include=*.py` as a glob and the grep never runs. Quote every glob.

**LESSON** ~ `grep -r` over `plots` crawls the binaries in `.data` and looks stalled. Scope it with `--include="*.yml"`.

**LESSON** ~ The ledger had no trailing newline, so a block appended with `cat >>` would join its last row. A ledger block starts with a newline.

| ID | item |
| --- | --- |
| **REF-1** | `test_indicator_references.py` expected rent burden's derivation without `open_ended`, which ACS-7 added to its declaration. It failed at 37e89ad, before step 3, so step 2's "green" carried one known red. Fixed by expecting the declaration as it stands. A red test left standing hides the next one behind it |

## SPRINT 04, STEP 4a ~ legislators: which source is the record, 2026-11-11

Sources read: LegiScan API User Manual v1.91 (revision 20250317); legiscan.com/ME/datasets; the Maine House's ExportActiveMembers CSV and member pages (legislature.maine.gov/house, fetched 2026-11-11); the Legislature's convening schedule for the 133rd.

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-134** | The Maine Legislature is the record for seats and who holds them; LegiScan is a second authority, carried for `people_id` and checked against the record, its disagreements shown, never collapsed | Every seat is a row, including the three tribal seats and vacancies; contact comes from the Legislature; LegiScan links a holder to sponsorship and votes | The Legislature stops publishing a member list a preparation can read, or LegiScan begins publishing seats rather than activity |

| ID | item |
| --- | --- |
| **LEG-1** | LegiScan's getSessionPeople lists people with sponsor or vote activity in a session, not seats. A vacant seat is absent, a seat that changed hands is two people, and a new session is near empty until bills and votes begin. Withdrawn: the plan's "one row per seat, vacant" from LegiScan |
| **LEG-2** | LegiScan person records carry name, party, role, district and third-party ids (FollowTheMoney, VoteSmart, KnowWho, Ballotpedia); no email, phone or address |
| **LEG-3** | LegiScan person records reflect current status; viewed in a prior session they may show a different role, district or party. A pull of a past session is not that session's truth |
| **LEG-4** | LegiScan districts are written `HD-063`, `SD-015` in the manual's examples (other states). Maine's strings are unverified until a key exists; the mapping to the graph would be `23` plus the number padded to 3 |
| **LEG-5** | The House publishes a real-time member export, CSV and Excel (ExportActiveMembers): Name, Party, District, County, Seat, Email, Phone, Residence, City, Zip, Position, Committees. District is a bare integer; County can list several; City and Zip were empty; the Speaker sits at seat 0, Position "Ex Officio". It names no Legislature number and no date, so `as_of` is the fetch time |
| **LEG-6** | No Senate export found; the Senate publishes HTML lists (by name, by district, by municipality). Unverified that none exists. The two chambers' sources are not symmetric |
| **TRIBE-2** | The House's three tribal seats (Penobscot Nation, Passamaquoddy Tribe, Houlton Band of Maliseet Indians) have seat numbers and no district, so they cannot join the graph by district code. Terms reported to end September and October 2026; no tribal representative was in the House export on 2026-11-11. Absence from an active list is not a statement about the nations. Secondary sources disagree on which seats were filled; MP-77 stays verified against the Legislature's own pages |
| **LIC-1** | LegiScan's legislative datasets are CC BY 4.0 per its datasets page; the API terms themselves are not yet read. The Legislature's site states no license that I found; open before anything from it is published |
| **KEY-1** | census_acs.py reads `source_config.get("api_key")` before CENSUS_API_KEY. The key never reaches provenance (`_public_request` strips it), but the path invites a key into a public manifest. New providers read the environment only; close this path in census_acs later |
| **TIME-1** | The 133rd convenes and is sworn in Wednesday 2026-12-02. Until then three answers are true: the 132nd in office, members-elect, and (per one post-election report) two House races uncalled. Open: which one step 4 builds first |
| **XCHK-1** | The House publishes its own town-to-district listing (642 towns and municipalities, 151 districts). It is a third, independent account of what build_place_edges derives from blocks, and could check the overlaps edges by town. Open; not in step 4 |

**WRONG** ~ The repo had no LegiScan provider; the API's shape had been checked once and never became code.

**LESSON** ~ A source's word for a thing is not ours. LegiScan's "people" are people who acted, not seats that exist, and a table shaped by one would have called every quiet seat vacant.

## SPRINT 04, STEP 4b ~ legislators: timing and the tribal seats, 2026-11-11

Sources read: 3 MRSA §1 and §601 (Revisor's text, extracted 2026-10-05); the Law and Legislative Reference Library's summary of PL 2025, c. 705 (LD 785); 3 MRSA §602 PDF (copyright notice).

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-135** | Step 4 builds the preparation now and acquires the 133rd Legislature after it is sworn in (2026-12-02). Today's House export is a test fixture, never a harvest | No published artifact names a legislator about to leave office or one not yet seated; step 4 closes after Dec 2, with steps 5 and 6 worked in between | An organizer or official needs the 132nd or the members-elect before Dec 2, and the artifact can say which it is |
| **D-136** | A tribal seat is keyed by the nation's name as 3 MRSA §601(1)(A) defines the Wabanaki Nations: Passamaquoddy Tribe, Penobscot Nation, Houlton Band of Maliseet Indians, Mi'kmaq Nation. `seat_kind: tribal`, no place link. Where §1 words a nation differently ("Penobscot Indian Nation"), that wording is kept verbatim in `statute_wording`. The set of tribal seats is declared per Legislature with its statute citation, never hardcoded | A tribal seat is a row with no district and no geometry, so the Census's tribal areas are never read as the nations' constituencies (D-123); nothing joins on the name, it only identifies the row | Consultation with the nations asks otherwise, or the statute's definition changes |

| ID | item |
| --- | --- |
| **TRIBE-3** | Corrects TRIBE-2: the 132nd had three tribal seats; PL 2025, c. 705 lets the Mi'kmaq Nation elect a representative beginning with the First Regular Session of the 133rd, so the 133rd has four. 3 MRSA §1 now names the Mi'kmaq Nation's Representative-elect. Withdrawn: "the House's three tribal seats" as a standing fact |
| **NAME-3** | 3 MRSA §1 writes "Penobscot Indian Nation"; §601(1)(A), §602 and the Legislature's pages write "Penobscot Nation". One nation, two statutory strings; D-136 keys by §601 and keeps §1's form |
| **LIC-1** | Addendum: the State of Maine claims copyright in its codified statutes and asks republishers to carry its disclaimer. Seats carry four names and a citation, not statutory text; record the claim, decide before publishing whether the disclaimer is owed |
| **PEN-2** | I described PEN-1 as teaching "never mint a code". It teaches using an authority's published code where one exists (2760R, via part_of). It says nothing where no authority publishes a code, which is the tribal-seat case. The fork was decided on the corrected reading |

**LESSON** ~ The seat set is law, and law moves between Legislatures. A count that is true of the 132nd was about to become a constant in the 133rd's contract.

## SPRINT 04, STEP 4c ~ the seats table, 2026-11-11

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-137** | Seats are a third graph table, `seats`, keyed `(legislature, chamber, seat_kind, seat_ref)`; Contract 3 section 6 (draft 0.8). District seats are generated from `places`, tribal seats from a declared list, holders from the record | A vacancy is a stated fact, a seat with no holder; a holder with no district place is refused | The grove's catalogue needs seats keyed some other way |
| **D-138** | No phone numbers in `seats`; contact is `email` (the House export) and `profile_url` (the Senate listing) | A public harvest never republishes members' own cell phones; the two chambers give different contact, honestly asymmetric | Members or the Legislature ask that phones be carried |

| ID | item |
| --- | --- |
| **LEG-7** | The Senate's district listing is one line per district, `District N (Map) - Senator Name (P-County)`, all 35; no email or phone on the page. Corrects LEG-6's "fragile": one pattern parses every line |

## SPRINT 04, STEP 4d ~ seats, built (preparation pending), 2026-11-11

Built: canopy/providers/maine_legislature.py (House CSV, Senate listing, phones never read), soil/transform/build_seats.py, tests/test_seats.py (14 tests; shim-run in the sandbox, 14 passed, each refusal checked for its own reason), registry entry, semantic types legislature_roster and seats, manifest datasets legislature_133_house and legislature_133_senate (available: false).

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-139** | Seats tests use synthetic fixtures in the exact shapes fetched 2026-11-11, not the real export. Refines D-135 | No member's phone enters the public repo through a fixture (D-138) | A phone-free copy of a real export is wanted as a regression fixture |
| **D-140** | build_seats takes `sworn_in` and refuses a roster fetched before it | D-135 is a refusal, not a habit: the previous Legislature cannot be built by accident | A product needs the outgoing Legislature and says so |

| ID | item |
| --- | --- |
| **TRIBE-4** | The House export names no nation, so a tribal representative cannot be matched to a seat from it. build_seats refuses a House row with no district until the 133rd's export shows how tribal representatives appear; tribal seats are vacant by the record until then |
| **SEN-1** | The Senate listing was verified at autodiscover.legislature.maine.gov; whether legislature.maine.gov serves the same page is unchecked |
| **PREP-1** | How one preparation reads another's output (places into build_seats) is not known in this chat; the seats preparation waits on it |
| **LEGI-1** | LegiScan columns exist in `seats` and stay empty until a key is held and the provider is built |

## SPRINT 04, STEP 4e ~ the seats preparation waits for loam, 2026-11-11

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-141** | No seats preparation until loam (Sprint 05) lets one preparation read another's output. Not a step in maine_geography_graph (unavailable rosters would block the graph), not a local copy of places (it would go stale silently) | Step 4 is built and tested but not run; it runs when loam reads places and the 133rd's rosters exist (after 2026-12-02) | Seats are needed before loam lands |

| ID | item |
| --- | --- |
| **PREP-1** | Resolved by D-141. Preparations run through the orchestrator; a step's output is `plots/<plot>/.data/<step>_<output>.<ext>` with its receipt at `.envelopes/<step>_<output>.envelope.json` (places: `.data/graph_places_places.parquet`). Steps reach each other only inside one run; no CLI command runs a preparation |
| **LOAM-1** | Sprint 05: loam must let a preparation read another preparation's output by semantic type, with staleness. First consumer: build_seats reading places |

## SPRINT 04, STEP 4e ~ the seats preparation waits for loam, 2026-11-11

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-141** | No seats preparation until loam (Sprint 05) lets one preparation read another's output. Not a step in maine_geography_graph (unavailable rosters would block the graph), not a local copy of places (it would go stale silently) | Step 4 is built and tested but not run; it runs when loam reads places and the 133rd's rosters exist (after 2026-12-02) | Seats are needed before loam lands |

| ID | item |
| --- | --- |
| **PREP-1** | Resolved by D-141. Preparations run through the orchestrator; a step's output is `plots/<plot>/.data/<step>_<output>.<ext>` with its receipt at `.envelopes/<step>_<output>.envelope.json` (places: `.data/graph_places_places.parquet`). Steps reach each other only inside one run; no CLI command runs a preparation |
| **LOAM-1** | Sprint 05: loam must let a preparation read another preparation's output by semantic type, with staleness. First consumer: build_seats reading places |

| ID | item |
| --- | --- |
| **TIME-2** | Corrects D-135's framing and the step 4 close. The build is timeless: build_seats takes `legislature` and `sworn_in` and builds any Legislature on any day. Acquiring one Legislature's rosters is a run, not a build step. D-135 governs which Legislature a published artifact carries; it never gated the build. Withdrawn: "step 4 closes after 2026-12-02". Step 4 closes on a dependency: loam reads places into build_seats (LOAM-1, Sprint 05) |

**WRONG** ~ I turned a data-freshness concern into a build date. The plan is ordered by dependency, never by the calendar.

## SPRINT 04, STEP 5a ~ publication records travel in provenance, 2026-11-11

Step 5 asked for coastline-clipped display geometry, recorded as a publication step. Reading the code first changed the question twice. The graph holds no geometry at all (`build_block_spine` reads faces .dbf bytes only; `build_places` reads properties only), so step 5 is not a clip of the places but a new family of display outlines beside the graph. And nothing could carry a publication step to an exit: Contract 1, rule 11, says the record lives in provenance, but the gate read `metadata.publication`, and `_merge_provenance` copies no metadata. So 5a moves the record to where the contract already said it goes; 5b builds the outlines.

| ID | decision | implication | reverse if |
| --- | --- | --- | --- |
| **D-142** | Display outlines come from the 2024 TIGER/Line topological faces (D-126), land faces only, by the spine's own `LAND_FLAGS` (G, I, L, S; LWFLAG-1), dissolved by state, county, town, House and Senate district. Tribal areas are dissolved through each face's 2020 block and that block's `aiannh_geoid` (D-125), so they are 2020 places, as `places` keys them. Each outline carries `authority` and `code`. Making them is a `clipped` publication step; they are never an input to analysis. Weighed and set aside: the Census 2024 cartographic boundary files, 1:500,000 (verified to exist for Maine SLDL and SLDU, CC0, but generalized), and TIGER/Line clipped to an outside water layer | Outlines share every edge with the blocks the weights rest on. Perennial water is removed, ocean and lakes alike: Moosehead and Sebago are holes in their towns. MEGIS divisions are not outlined (no faces code) | A reader needs lakes filled and a source that tells ocean from lake is found; or an analysis needs a polygon, which must then be the legal boundary, never these |
| **D-143** | Rule 11's records live in the provenance entry of the step that made them (Contract 1 0.4, E-7). A primitive prints `step`, `detail` and `count`; the builder stamps `by` and `at` from the entry, and refuses a primitive that stamps either. `provenance.schema.json` holds the seven steps, enforced when a receipt is written. The gate gathers every record in the chain, in chain order, each once by (`by`, `at`, `step`, `detail`), with the `lineage_branch` it was found through. `metadata.publication` is never read or written | A record made once reaches every descendant, and no exit has to re-derive history it did not make. Receipts written before D-143 read as having no records | An exit must record a change no primitive made; that record is `by: the gate`, written at the exit |

| ID | item |
| --- | --- |
| **GATE-3** | Withdrawn: the gate's reader of `metadata.publication`. Contract 1 said provenance; the gate read metadata; nothing wrote either, so the drift was invisible until a step needed a record to travel |
| **MAP-8** | `map.py` joins only `us_census_geoid` on `GEOID` (`_UNIT_KEYS`), so a district value cannot be drawn. All five boundary layers share `semantic_type: governance_unit`, so `joins_to` cannot tell them apart and `--layer` is the only choice; given the House layer, a county value's `23001` matches House District 1 (GRAPH-1 at the map exit). D-142's outlines carry `authority` and `code`, which closes it on their layers; `map.py` itself is unchanged |
| **MAP-9** | `map.py`'s choropleth writes `map.geojson` outside the envelope builder, so it has no chain to carry rule 11's records. Harmless while `map` refuses to publish choropleths; the publish door (Sprint 08) must not repeat it |
| **SEAM-2** | Town and district outlines follow the exact 2024 boundaries; the `overlaps` weights give a 2020 block split by a 2024 boundary whole to the town or district holding most of its land (D-126, `faces_sldl`, `faces_sldu`). For those blocks the outline and the counts disagree about who holds a sliver. By design: display and counting are different jobs. Do not fix one to match the other. Tribal outlines built from blocks have no such seam, if blocks nest (TRIBE-5) |
| **TRIBE-5** | 2020 blocks should nest exactly in 2020 Census tribal areas: FACE-1 records the Census's documentation that 2020 blocks never cross a boundary of an entity it tabulates, and 2020 is the vintage both share. Documented, not yet checked on Maine's data. 5b tests it by comparing each block-built outline with `tribal_reservations_2020` and `tribal_trust_lands_2020`; if they nest, the only difference is water |
| **FACE-2** | `maine_faces_2024.zip` is a zip of 16 county zips (the manifest builds it with `zip -j`). GDAL cannot open it, and nothing in the repo reads face geometry yet; 5b needs a reader that opens zip-in-zip |
| **SIZE-1** | Outline size is unknown. 5b records bytes and vertex count in provenance; simplification, if needed, is its own `simplified` record |
| **HASH-2** | `Envelope.to_dict` drops a hash's `value` when it is null (the `test` profile's skipped hash), but `from_dict` reads `value` unconditionally and the schema requires it, so a test-profile envelope cannot round-trip or validate. Found by 5a's tests, which use the `dev` profile instead. Not fixed in 5a; may be what HASH-1 tracks |

**WRONG HYPOTHESIS** ~ Step 5 began as "clip the places' geometry to the coast." The places carry no geometry.

**WRONG HYPOTHESIS** ~ The first fork offered cartographic boundary files or a clip of our own; the faces the graph already rests on were the better source and were missed until the question was asked as "most thorough and accurate."

**LESSON** ~ The faces probe (`geopandas.read_file` on `maine_faces_2024.zip`) failed because it assumed a flat zip. A probe that assumes a file's shape repeats step 1's lesson about assuming a field.

Files: `seeds/schemas/provenance.schema.json`, `canopy/envelope.py`, `canopy/expose/gate.py`, `field-guide/docs/contracts/01-tiers-and-the-gate.md` (0.4), `tests/test_publication_steps.py` (new). Next decision ID: D-144.

## Sprint 04 step 5b: display outlines from the 2024 faces (D-144 to D-148)

**D-144. The outlines are one R primitive, soil/transform/build_place_outlines.R (sf).** Keys are derived from the face codes, never matched: state STATEFP; county STATEFP + COUNTYFP; town STATEFP + COUNTYFP + COUSUBFP; districts state_fips + the three-digit SLDLST or SLDUST, as the spine does; tribal areas through each face's 2020 block and that block's aiannh + aiannh_comptyp in the spine, as build_places does. The land rule has two homes, LAND_FLAGS in build_block_spine.py and in the R file, and a test holds them equal. Every other twin risk is caught at run time: a wrong key is not in places, and swapped chambers give 35 outlines where places has 151. Refuses a key not in places and a place at the level with no land face, both by name; together they make the per-level count rule, which names the levels it covers (MEGIS is not one). Set aside: Python (geopandas), which would have imported LAND_FLAGS and the faces walker directly.

**D-145. One primitive, six steps, two registry entries.** outline_state, outline_counties, outline_towns, outline_house, outline_senate and outline_tribal join maine_geography_graph.yml, because they need the spine and places from the same run (PREP-1). Each step has its own refusals, counts and clipped record. The registry does not read semantic types, so build_place_outlines and build_tribal_outlines point at the same R file, each with its own output type, which is right whether or not something downstream checks it. Both stamp `by: build_place_outlines` (the builder names a record by the file); the step id tells them apart. Cost accepted: the faces are unpacked six times. Set aside: one step and one file for every level, which would need per-row context the gate cannot read yet (D-123, step 6); a shared land-faces intermediate, which would be a geometry output with no publication-only guard.

**D-146. Two new types, place_outline and census_tribal_outline, both public.** Not governance_unit: analysis primitives take it, so an outline under that type could be routed into analysis, and it would be a sixth layer in MAP-8. census_tribal_outline requires census_tribal_area by id alone: the gate reads only the id (rule 9), and the text stays on census_tribal_area. Every outline row carries authority, code, level, name, context_note (copied from places) and water_clipped, so Penobscot Indian Island's two reservation subdivisions keep their note when drawn among towns. Every outline artifact lists census_tribal_area in metadata.context_notes, because every outline descends from places (NOTE-2). Tests: no primitive in either registry takes an outline type; every required note id has exactly one text.

**D-147. GeoJSON, in the source CRS (NAD83, EPSG:4269).** It is what every vector type, map.py and the publish door read. Reprojection is not one of rule 11's seven steps; if the door needs WGS84, it is decided there. Set aside: parquet (geoparquet from sf needs packages the environment does not have), gpkg.

**D-148. SIZE-1: size_bytes and vertex_count go in the output metadata,** declared as optional fields in metadata.vector.schema.json. provenance.schema.json has no field for measurements and allows none; the vector metadata schema allows extra properties, and declaring them gives the values a defined home.

**TRIBE-5, method.** At level aiannh, each block-built outline is compared with tribal_reservations_2020 and tribal_trust_lands_2020: the outline's area outside the Census layer, and the layer's area outside the outline, beside the perennial water left out of its blocks. A difference beyond water warns and is never refused: the 2024 database may have realigned edges since 2020, and refusing would refuse the Census for updating its own map. Tolerance 0 on the first run, so every difference is reported; the tolerance is set from what Maine's data shows. Results: to be recorded after the first run.

**FACE-2, updated.** The nested zip was already walked: read_faces in build_block_spine.py opens a zip of county zips, for the .dbf only. The gap was geometry. The R primitive unpacks both levels into a temporary folder and reads each _faces.shp.

**DEPS-1. geopandas 1.2.0 and pyogrio 0.13.0 are installed on Kalli's machine but not declared in environment.yml.** Nothing in 5b uses them. If any committed file imports them, the Docker build breaks. Open: grep for imports.

**NOTE-1. Nothing in canopy or soil wrote metadata.context_notes before 5b.** _build_metadata passes a primitive's metadata through whole, so a primitive that prints context_notes is heard, but none did. Rule 9 would therefore refuse places, and everything descended from it, at every exit. The outlines are the first artifacts to carry a note.

**NOTE-2. Rule 9 binds a note across the whole lineage (D-101).** graph_places reads two census_tribal_area inputs, so every artifact descended from places, county maps included, must carry a note written for a handful of its rows. Kept for 5b: a note on too much is safe, a missing one is not. For step 6: narrow it to the rows it describes.

**S2-1. Outlines are unioned with s2 off.** TIGER faces share their edges exactly, so a planar union is exact, and s2 on complex coastlines is slow (L-61, dissolve_by_field). TRIBE-5's areas are measured with s2 on.

**C-36, again.** primitive_success serializes with auto_unbox, so a one-element vector prints as a string. context_notes as a string would still pass the gate's `in` test, by substring. The primitive writes it with as.list, as extract_vector_metadata does.

**Lesson. rewildr's safe_read_table infers CSV types,** so a code column of "001" arrives as 1. The outline primitive reads every CSV column as text. Any R primitive reading codes from CSV needs the same.

Files: `soil/transform/build_place_outlines.R` (new), `soil/_registry.yml` (build_place_outlines, build_tribal_outlines), `seeds/schemas/semantic_types.yml` (place_outline, census_tribal_outline), `seeds/schemas/metadata.vector.schema.json` (size_bytes, vertex_count), `plots/maine/preparations/maine_geography_graph.yml` (six outline steps), `tests/test_place_outlines.py` (new). Next decision ID: D-149.

**D-149. One id, one note: the places table's note is census_tribal_places.** test_place_outlines found census_tribal_area with two texts in semantic_types.yml: the places type's, about a table ("This table includes Census tribal areas and the town records that coincide with reservations..."), and census_tribal_area's, about one boundary ("This boundary is the U.S. Census Bureau's..."). Both are right for what they describe; one id cannot name both. The gate reads ids only, so no reader was shown the wrong text, but anything resolving the id to its text (a legend, the publish door) would have had to guess. The places type now requires census_tribal_places; census_tribal_area stays the boundary note; every places row keeps context_note census_tribal_area, because a row's note is about that row's boundary. Outlines list both ids in context_notes (amends D-146; NOTE-2 still holds, and step 6 narrows it). Set aside: one merged wording, which would put a note on one of the two that does not describe it. Files: `seeds/schemas/semantic_types.yml` (places' note id), `soil/transform/build_place_outlines.R`, `tests/test_place_outlines.py`. Next decision ID: D-150.

## Sprint 04 step 5b: the first run of the outline steps (D-150 to D-152)

### Findings
- A preparation runs through the same orchestrator as an experiment: `parse_experiment` reads `kind: preparation`, and `python -m canopy.cli sows <path>` runs it. The exposure gate is never called inside a run; only the precondition gate is. Rule 9 binds at exits (`check_envelope`, `read_exposure`), never mid-run.
- Every run writes `compost/logs/<run_id>.yml`. Three runs of maine_geography_graph on 2026-11-11 (041928, 043526, 043757) each finished seven steps and name no outline step, so the outlines had never run on real Maine before this one. Whether those stamps are local time or UTC is not settled; a fresh run made it moot.
- Two CLI doors reach the orchestrator, `sows` (canopy/cli/sows.py) and canopy/cli/experiment.py, with the same --dry-run and --resolve-only flags. Whether this is what CLI-1 to CLI-3 recorded is not checked.
- RESOLVE-1: `--resolve-only` says "check data without running", but it calls `resolve_data()`, which acquires missing datasets and commits manifest changes. Only `dry_resolve()` is read-only. Harmless on this run (13 of 13 available). Open.
- First run of the outlines: 10 of 12 steps completed; stopped at outline_towns.

| level | outlines | clipped | size_bytes | vertex_count |
|---|---|---|---|---|
| state | 1 | 1 | 27,173,437 | 1,191,643 |
| county | 16 | 16 | 27,898,507 | 1,223,335 |
| sldl | 151 | 149 | 29,713,677 | 1,301,604 |
| sldu | 35 | 35 | 28,220,938 | 1,237,274 |

- The coast is nearly every vertex: counties add about 3% over the state outline, senate about 4%, house about 9%. If a layer must get lighter, simplify the coast (SIZE-1).
- No key refusal at sldl or sldu, so no land face carries an undefined district code (no 23ZZZ).
- The envelope's `count` is the clipped count, not the outline count; outlines were counted from the GeoJSON features.
- Maine's 2024 faces carry three LWFLAG values: L 89,101, P 18,376, I 15. G and S never occur here.
- WATER-1: outline_towns refused 2300357936 Penobscot Indian Island Reservation, "no land face". Probe (tests/debug/indian_island_faces.py): county subdivision 57936 has one face in county 003 (Aroostook), flag P, and 118 L and 45 P faces in county 019 (Penobscot). The refused place is the Aroostook piece, a single perennial water face. Tribal area 2760 spans counties 003, 007, 019 and 021 and nine county subdivision codes, ten county pieces.
- PENOB-1: D-142 clips perennial water from every outline. For the Penobscot Nation this matches one side of a lawsuit: the en banc First Circuit (2021, 3 to 2) held that the reservation does not include the waters of the Main Stem; the dissent cited the river's place in the Nation's culture, language and historic sovereign rights. The Nation petitioned the Supreme Court (No. 21-838); the outcome is not verified here. The census puts water inside this place. A context note saying the water was left out for display and that the river's status is contested belongs at the town and tribal levels. Open, for step 6.

### Wrong hypotheses
- That the outline run would stop at rule 9 before giving numbers (NOTE-1). The gate does not run inside the orchestrator.
- That the earlier graph outputs came from direct primitive calls. They came from orchestrator runs.
- That Indian Island's land faces carry a flag outside LAND_FLAGS. They are L.
- That its land faces carry a different county subdivision code. They carry 57936; the refused key was another county's piece.

### Decisions
- D-150: a place whose faces are all water is let through only when the run declares it in a new `water_only` param of build_place_outlines (default empty). It is named in a `water_only` publication record (detail naming each place, count) and not drawn, so an outline stays land and the place stays present (rule 8). Any undeclared place with no land face is still refused.
- D-151: a declaration is refused by name if its key is not a place at the level, if the place has land faces (a stale declaration), or if it has no face at all. The third was not in the design shown; without it a key with no faces would be excused silently.
- D-152: outline_towns declares water_only: ["2300357936"], the Aroostook piece of Penobscot Indian Island Reservation. Registry declares the param as an array, not required, default []. Primitive version not bumped.
- Tests: the fixture gains town 00300, one water face in block 1003. Four new R tests: a declared water-only place is named, not drawn; and each refusal of D-151 fires for its own reason. The undeclared case is the existing Gamma test, which now also asserts "1 of them have only water faces".

### Lessons
- Read the run path before predicting how a run fails: both mid-run predictions here were wrong, and the code answered them in one read.
- A refusal that names a place by key and name made a four-county story findable in two probes.

### Sprint 04 step 5b, second run (D-153, D-154)
- D-153 corrects D-150: the record of a declared water-only place is publication step `held_out`, not `water_only`. provenance.schema.json enumerates publication steps (held_out, field_dropped, renamed, rounded, format_changed, simplified, clipped), so `water_only` would have failed envelope validation at outline_towns. held_out already means a thing kept out of the drawing and named; no schema change. The detail names WATER-1 and each place.
- GJSON-1: the second run stopped at outline_state, "Failed to write vector data ... Creation failed". Cause, reproduced outside the run: `safe_write_sf` calls `write_sf(delete_dsn = TRUE)`, so GDAL first opens the old file to delete it. The whole-state outline is one feature too large for GDAL to parse at its defaults ("GeoJSON object too complex/large", OGR_GEOJSON_MAX_OBJ_SIZE), the delete fails, and the GeoJSON driver does not overwrite. The first run worked only because no file existed. Counties, house and senate rewrote because each of their features is smaller.
- Wrong hypotheses for GJSON-1: a lock (lsof: nothing open), a full disk (170 GB free), the macOS com.apple.provenance attribute (all four files carry it).
- D-154: build_place_outlines removes its own output before writing. Narrow on purpose: the general bug is in rewildr's safe_write_sf, where any GeoJSON holding one large feature cannot be overwritten. Open in GJSON-1.
- GJSON-1, also open: the state outline cannot be read by GDAL at default settings, so any reader (loam, the publish route, QGIS) may need OGR_GEOJSON_MAX_OBJ_SIZE raised, or the outline made lighter (SIZE-1).

### Sprint 04 step 5b, third run: all 12 steps (D-155)
- The graph preparation ran end to end: 12 of 12 steps. D-154 worked: outline_state rewrote its file.

| level | outlines | clipped | held out | size_bytes | vertex_count |
|---|---|---|---|---|---|
| cousub | 528 | 517 | 1 | 31,064,310 | 1,357,329 |
| aiannh | 8 | 6 | 0 | 721,936 | 31,552 |

- cousub: 528 outlines plus 2300357936 held out (WATER-1). The towns layer is the heaviest of the six, about 14% more vertices than the state.
- aiannh: 8 outlines, every places row at the level. The 6 clipped are exactly the 6 with water left out of their blocks.
- TRIBE-5, all 8 warned at tolerance 0. A = outline outside the Census 2020 layer, B = layer outside the outline, W = perennial water left out of its blocks (m2). A nest is A near 0 and B near W.

| area | A | B | W | B minus W |
|---|---|---|---|---|
| 0115T Aroostook Band of Micmac Trust Land | 175,681 | 69,504 | 0 | 69,504 |
| 1530R Houlton Maliseet Reservation | 1,034 | 23,630 | 22,653 | 977 |
| 1530T Houlton Maliseet Off-Reservation Trust Land | 1,280 | 1,277 | 0 | 1,277 |
| 1575R Indian Township Reservation | 1,395 | 17,828,071 | 17,867,564 | -39,493 |
| 2695T Passamaquoddy Trust Land | 24,549 | 15,416,780 | 15,428,674 | -11,894 |
| 2760R Penobscot Reservation | 33 | 38,124,198 | 38,211,558 | -87,360 |
| 2760T Penobscot Off-Reservation Trust Land | 6,212,606 | 22,608,247 | 20,006,248 | 2,601,999 |
| 2850R Pleasant Point Reservation | 618 | 1,053,880 | 1,055,604 | -1,724 |

- Two clusters. Noise: every residual at or under 1,395 m2 (A for six areas, B minus W for 1530R and 1530T). Negative B minus W is also noise: W sums the Census's ATOTAL while A and B are areas sf computes, so the two measures differ slightly. Not noise: 0115T (A 175,681), 2760T (A 6.2 km2, B minus W 2.6 km2), and 2695T (A 24,549), 17 times the largest noise value.
- D-155: tribe_tolerance_m2 = 2000, at the natural break between 1,395 and 24,549, so the next run should warn for 0115T, 2695T and 2760T only. Not 25,000, which would be fitted to let 2695T pass. Not rerun after the change: the tolerance changes warnings only.
- TRIBE-5 stays open for 0115T, 2695T and 2760T: block-built outlines that do not nest in the Census 2020 layers by more than water, against FACE-1's premise. Causes not known. Candidates to test, not assume: trust land changed between the 2020 tabulation and the 2020 layer; the 2024 faces' edges moved; blocks split by a tribal boundary.
- PENOB-1, now measured: 2760R nests almost exactly (A 33 m2), and the Census 2020 reservation layer holds about 38.1 km2 that the outline leaves out, matching the 38.2 km2 of water in its blocks. So the Census's own reservation boundary includes the river water around the islands that D-142 clips and that the 2021 en banc ruling excluded. The context note must say this plainly. Step 6.
- tests/debug/indian_island_faces.py is committed as the WATER-1 evidence. It imports pyogrio (DEPS-1); tests/debug is not collected by pytest.

## Sprint 04 step 6: the gate learns row-level context (D-156 to D-160)

### Findings
- LEDGER-1: D-98 to D-124 are cited throughout but have no entries in this ledger, and the Master Plan's decision table stops at D-81. Where some are written down: D-101 and D-102 in Contract 1 (E-1, E-2); D-121 and D-122 in Contract 3 (G-1, G-2); D-123 in soil/transform/build_places.py's docstring and the census_tribal_area type's comment (tribal places are the Census's 2020 legal areas only, keyed by GEOID, each carrying the census_tribal_area note, a qualified Census view under MP-72); D-118 in semantic_types.yml's PROPOSED tier comments. The rest are not located. None was reconstructed from citations.
- HASH-1 is HASH-2's earlier name. tests/test_preparations.py line 90 cites HASH-1 for exactly HASH-2's bug: a skipped hash's `value` is dropped by Envelope.to_dict and the schema then requires it. HASH-1 was never recorded on its own. Cite HASH-2.
- NOTE-1, confirmed in code: build_places' primitive_success metadata had no context_notes, so the places table was refused at rule 9 at every exit. Closed by D-158.
- Contract 1 is stricter in code than in words. Rule 3 says lineage ("every ancestor's tier"); rule 9 says a note "must travel with it"; section 6 says an artifact "of that type" carries it. The gate bound notes across the lineage only because the rule 9 check sat inside the tier loop. Neither reading worked for Maine: own type only drops the note from town outlines (place_outline requires none), lineage puts both tribal notes on every county map (NOTE-2).
- Why Houlton, Littleton and Old Town carried no note: build_places gave the note only to a town whose every block lies in a reservation (R), so a town partly in a reservation, or holding trust land (T), could never carry one.
- C-36 at the gate: rule 9 tested `id in context_notes`, which on a string is a substring test, so a string context_notes would have passed. Now refused (D-156).
- Vocabulary.load reads only semantic_types.yml's types map and domains/*.yml, so a note file elsewhere is neither picked up nor rejected by it. The gate loads notes itself (D-157).
- PENOB-1, now verified: the Supreme Court denied certiorari in Penobscot Nation v. Frey (No. 21-838) and United States v. Frey (No. 21-840) on April 18, 2022 (supremecourt.gov docket, SCOTUSblog case pages). The en banc First Circuit ruling stands: the reservation is the island uplands, without the Main Stem's waters. D-142's water clip follows that ruling; the Census boundary includes the water; the Penobscot Nation and the United States as its trustee disputed the ruling. Whether the Nation pursues the question elsewhere today is not verified here. The note says none of what is not verified.

### Wrong hypotheses
- That NOTE-2's lineage-wide binding was decided by D-101. D-101 (E-1) decides that rule 3 is a conjunction of tiers. It says nothing about notes. The binding came from the loop rule 9 shared with the tiers.
- That D-123 was never written down. It is in code (above).
- That merged places get their notes in build_place_outlines. Outline rows copy their note from places; a county's note is decided in build_places, which has the spine.
- That the Indian Island town keys had to be declared. Reservation subdivisions already carry part_of_code 2760R (PEN-1), so the display note follows that.

### Decisions
- D-156: rule 9 binds by row. An artifact always carries its own type's required notes. If its metadata has row_context_notes (a list, empty included), it also carries every note there, and no ancestor's type binds a note. If the field is absent, every note any type in its lineage requires binds, as before: silence is not a claim, so a primitive that never learned rows over-notes and never fails open. context_notes and row_context_notes must be lists of ids; a string is refused (C-36). The allow record gains context_scope (rows or lineage). Contract 1 to 0.5, E-8. Set aside: own type only (drops notes from town outlines); lineage only (NOTE-2's over-noting).
- D-157: every note's text lives in seeds/notes/notes.yml, beside seeds/licenses: id, text, optional when_merged. Types require notes by id alone; places and census_tribal_area lost their texts to it, unchanged. canopy/expose/records.py loads it loudly (an id declared twice, which safe_load would hide; no text; an unknown field; a when_merged naming no note or itself) and check_required_notes refuses a type requiring an id the file lacks, or carrying a text of its own, when the gate's context loads. The gate refuses a carried or required note with no text, since it cannot travel, and the allow record carries each note's text as context_text. decide() takes notes as a required argument, so no caller can skip the text check. Set aside: attaching row-only notes to some type's required_context, which would make a type require notes it does not need.
- D-158: contains_census_tribal_area, census_tribal_area's merged form (when_merged), on every place that is not itself a tribal boundary and holds any 2020 tribal block, R or T, at every level: state, county, town, House and Senate district, MEGIS civil division (through division_blocks). Houlton, Littleton and Old Town now carry it. Tribal areas and reservation subdivisions keep census_tribal_area; every row still has at most one note. No share threshold: "all or part" is true of a sliver, and a sliver that is boundary noise (TRIBE-5) is a finding about the edges, not a judgment buried in a threshold. build_places refuses census_tribal_area on any other place, and writes context_notes (its rows' notes and census_tribal_places) and row_context_notes. The note id is a constant in the primitive, held equal to the notes file by test_places. Draft text, for Kalli and Person 3. Set aside: notes passing up unchanged (a county carrying a note that says it is a tribal boundary, against D-149); notes stopping at the merge (a county silent about the reservation it holds); a threshold.
- D-159: outlines list exactly the notes their rows carry, in context_notes and row_context_notes; the hard-coded pair (census_tribal_area, census_tribal_places) on every outline is gone (amends D-146, D-149). A new param, display_notes, maps a note id to Census tribal area keys, for a note about how an outline is drawn. At aiannh it lands on the areas named; at cousub, on reservation subdivisions whose part_of_code names them, so no town key is typed. A new outline column, display_note. Refused: at any level but cousub and aiannh; a key that is not a tribal area in places; a declaration that lands on no drawn outline; one that lands on an outline whose water was not removed (the note would be false there); two display notes on one outline; part_of_code absent at cousub. outline_towns and outline_tribal declare penobscot_main_stem_waters: ["2760R"] (PENOB-1). Draft text, for Kalli and Person 3. No when_merged: nothing merges outline rows, and the counties carry the contains note. The outline_tribal comment that still said tolerance 0 now says 2000 (D-155).
- D-160: field-guide/docs/state.md, a living page of what is true now, rewritten (never appended) at every hand-off: where the build stands, open items with where each is defined, IDs defined outside this ledger, and traps. The ledger stays the history. Before each hand-off both are updated.

### Still open
- NOTE-2, narrowed: places and outlines now bind by row. Every other descendant of places (indicator maps, joined values) still writes no row_context_notes, so it falls back to lineage and carries both tribal notes, safely too many. Each primitive that writes place rows learns row notes when it is next touched.
- The note texts for contains_census_tribal_area and penobscot_main_stem_waters are drafts. Wording is Kalli's and Person 3's, and touches what consultation (MP-72) would ask.
- Contract 3 still describes the places table's context_note without the contains note; it was not opened in step 6.
- Contract 1's Open table still lists E-3, E-4 and E-5, which records.py and gate.py implement (consent folder D-115, license list D-116, the exposure_tier reader GATE-1). Not changed here.

### Lessons
- Context is scattered across the ledger, the contracts, docstrings and test comments. Four probes this step went to finding where an ID was written down. That is what state.md is for (D-160).
- A behavior that comes from where a check sits in a loop is a decision nobody made. When code is stricter or looser than its contract, find which line made it so before citing a decision for it.

### Sprint 04 step 6, tests and the run
- pytest: 415 passed (385 before, 30 new). The first run failed one new R test, my own: it asserted on the refusal's title, but the protocol response's `message` is the detail, and the title travels separately. Fixed in the test; the refusal was right.
- maine_geography_graph ran, 12 of 12 steps. Every outline step accepted its notes; outline_towns and outline_tribal accepted the Penobscot display note, so both Indian Island's drawn piece and 2760R are water-clipped, as WATER-1's faces suggested. Verified by the run, not assumed.
- row_context_notes, as written by the primitives: places [census_tribal_area, contains_census_tribal_area]; counties [contains_census_tribal_area]; towns [census_tribal_area, contains_census_tribal_area, penobscot_main_stem_waters]; tribal [census_tribal_area, penobscot_main_stem_waters]. NOTE-1 is closed. NOTE-2 is closed for places and outlines: a county outline no longer carries the boundary note or the table's note.
- read_exposure at public: all seven graph artifacts (places and six outlines) are withheld under rule 10 only. None under rule 9. Which dataset's license refuses was not read in this step; it may be what LIC-1 tracks. Check before Sprint 08.

### Lessons
- An R refusal test asserts on the detail, never the title: `message` in the protocol response is the detail.

## Sprint 04 step 7: the remaining graph invariants (D-161, D-162)

Contract 3's eight invariants, checked against build_place_edges and build_places. Six were already refused there or in build_block_spine. Two were not.

- D-161: every district touches at least one town holds by construction. District places come from the spine, and the spine refuses a counted block without a 2024 House or Senate assignment, so the spine's districts are the equivalency files' districts. No reverse check against the ACS tables: an ACS row the spine lacks is either a vintage mismatch or a not-defined row, and a refusal would trip on the second. build_seats refuses a holder whose district has no place, so only a missing district that is also vacant could pass all three. tests/test_places.py guards the construction.
- D-162: build_places refuses an edge family whose vintage differs from the vintage its own params declare: contains against town, overlaps to sldl, sldu and aiannh against those, overlaps from megis against division. The two steps in maine_geography_graph.yml declare vintages apart and agree today. The test_places fixture disagreed (division "M") and now uses one mapping. located_in is not checked until Sprint 06 writes it.
- Not changed, by the step's scope: refusals with no test that triggers them (town in more than one county, county or district without a name, key used twice, reservation subdivision in two reservations, missing vintage).
- Carried to LOAM-1: places hold the 2020 tribal legal areas (D-123); if ACS 2024 tribal estimates are on 2024 boundaries, invariant 6 cannot hold for aiannh places once values join. Not decided here.
- Found, not fixed: Contract 3's context_note field still says a note's text lives in seeds/schemas; since D-157 it lives in seeds/notes/notes.yml.
- Contract 3 to 0.9. pytest: 417 passed.

## Sprint 04 step 8: the sprint closes, 2026-11-11

Report: field-guide/docs/progress/information/sprint-04.md. Progress reports live by domain, one per sprint. The done-when is met as a table query for all 151 House and 35 Senate districts; as a loam query it arrives in Sprint 05.

Vintages used: blocks 2020 P.L. 94-171; towns, counties and the state 2024 (TIGER/Line faces and county subdivisions, D-126, D-127); House and Senate districts 2024 block equivalency files; Census tribal areas 2020 legal areas and block assignment (D-123); civil divisions MEGIS METWP24P; district and county names ACS 2024; legislators as test fixtures only, shapes fetched 2026-11-11 (D-139).

| ID | item |
| --- | --- |
| **NOTE-3** | The plan's item 6 asks for a short, verified note on tribal representation (MP-77). It is not written: neither draft in seeds/notes/notes.yml is it. It belongs on the seats type, worded by Kalli and Person 3, before seats are published |
| **LEDGER-2** | The step 4e block appears twice above, word for word. One decision, D-141, recorded twice; left in place, since the ledger is history |

Carried: LOAM-1 (with the aiannh vintage question), SRC-1 and running build_seats to Sprint 05; located_in to Sprint 06; rule 10's license and GJSON-1 to Sprint 08; the rest as listed in the report.

## Sprint 05 ~ loam learns the graph

### Step 1: reading, reconciling, and LOAM-1's design (2026-11-11)

Order of work, reconciled with Sprint 04: LOAM-1 first (it is not in the plan's build list and comes before it), then the plan's builds 1, 2 and 3, then builds 4 and 5 designed together as one rule for what crosses an edge, then build 6 with the grove keys (NAME-2, AUTH-1, SRC-1, SEAM-1, MAP-4) decided before any handoff. Two tests added to the plan's four: a place key used twice, and a missing vintage.

| ID | Decision | Why | Reverse if |
| --- | --- | --- | --- |
| **D-163** | A preparation reads another's output by semantic type, written `$loam.<type>`. The resolver refuses when it finds none or several, naming them, as recipe.py's bind_requirements does | LOAM-1's own wording; the vocabulary stays the contract; a renamed step breaks nothing | A consumer needs a type made more than once (place_outline is made five times); then add a qualifier |
| **D-164** | `$loam.` is answered by the plot's loam bed, rebuilt fresh from the receipts, reading tended and gathered rows only. An arrived holding is refused by name, pointing to `$manifest.`. A preparation may not read a type it produces itself. Claude's lean, accepted by Kalli | One reader of receipts (P-01); retired names read forward; the grove federates the same beds | Replanting the bed on every run becomes too slow |
| **D-165** | A `$loam.` read compares the producer's recorded input hashes, deduplicated and recomputed by the method each records (skipped means cannot tell), and every entry's params against its own run's declaration. Primitive code is not judged, and every message says so | The vintage decisions of this sprint live in params; input hashes alone would miss an edited declaration | KIT-1 adds hashing of primitive code |
| **D-166** | A stale read refuses before any step runs, checked after resolve_data so the disk is as the steps will find it, naming what differs and which preparation to rerun. Cannot tell warns into each consuming step's envelope, once. A missing input file is cannot tell. No override yet (KIT-1). The resolution report lists each `$loam.` input with its verdict | D-141 refused a local copy because it would go stale silently; this answers that directly | A use needs to run on knowingly stale ground; then the override in KIT-1 |
| **D-167** | Every provenance entry names its `run` and `step`, optional in provenance.schema.json and carried on every inherited copy | A step id alone would judge an inherited entry against the consumer's preparation; with its run, any entry is judged against its own declaration | Never expected |

| ID | Finding |
| --- | --- |
| **HASH-2** | Resolved by Sprint 05 change 1. A skipped hash dropped its required null value on write, so a test-profile receipt could neither validate nor load. The value is now always written; from_dict tolerates its absence in older receipts |
| **KEYS-1** | The places envelope declares no id_field, id_fields or spatial_unit, so loam's join grammar is empty for the table everything joins on. Fix upstream in build_places, and build_place_edges for its four key columns, before the plan's builds 1 and 2 |
| **LIN-2** | `_merge_provenance` concatenates input chains with no deduplication; places carries the build_block_spine entry twice. Harmless for staleness, which deduplicates; not fixed |
| **VER-1** | Every provenance entry says version 1.0.0. The version comes from the step definition, not the primitive, so it is not a signal of changed code |
| **KIT-1** | What the community kit (Sprint 10) must decide before someone else's machine runs it: the `--accept-stale` override (D-166), hashing primitive code (D-165), VER-1, DEPS-1. Carried in the Sprint 05 report and state.md |

Noted, not numbered: an envelope records no hash of its own output, so a file replaced after its build cannot be detected. PREP-1 says no CLI command runs a preparation, while state.md's traps describe a geography graph run through sows; one of them is out of date. In readiness.py "Holding" already means what loam holds of one type, which the plan's build 2 would reuse for place-keyed values.

Change 1 (D-167, HASH-2): canopy/envelope.py, canopy/orchestrator/orchestrator.py, seeds/schemas/provenance.schema.json, tests/test_provenance_identity.py (7 tests), tests/test_preparations.py (the fake builder takes run and step; 1 test that a receipt names them). Lesson: a signature change reaches every fake of it; search for stand-ins before handing over the change.

### Change 2: the `$loam.` reference (D-163, D-164)

canopy/loam/reach.py (new) opens the plot's bed once per run, on first need, from the folder the run's manifest lives in, and returns the one tended or gathered artifact of a type with its receipt read back as an Envelope, so a `$loam.` input inherits provenance and meets the precondition gate exactly as a `$steps.` input does. Refusals name their reason: none (listing what is made here and any receipt the bed could not read), several (naming each receipt), manifest-only (pointing to `$manifest.`), an unknown type. canopy/orchestrator/references.py resolves `$loam.<type>` for inputs and refuses it in params. canopy/orchestrator/orchestrator.py hands the resolver its reach and refuses, in validate, a run that reaches for a type it makes itself. canopy/wonder/session.py: open_plot takes an optional directory, because the orchestrator's tests place a plot outside the project root and open_plot could only find plots under it; every existing caller is unchanged. tests/test_loam_reach.py: 11 tests. Staleness is change 3.

Correction to change 2: tests/test_loam_reach.py held 10 tests, not 11.

### Change 3: freshness, judged before any step runs (D-165, D-166)

canopy/loam/freshness.py (new): judge() gives fresh, stale or cannot_tell for one reached receipt. Each recorded input is re-hashed by the method it was hashed with, deduplicated (LIN-2's doubled spine is checked once); each step's params are re-resolved from its run's declaration today, found by id among the plot's preparations/ and experiments/, exactly as a run resolves them, and compared with what was recorded. Stale names what changed and which runs to rerun. Cannot tell names what could not be checked: an unhashed input, a missing file, a missing declaration, or steps recorded before D-167, collapsed into one line. Every verdict ends "primitive code is not checked (D-165)". canopy/orchestrator/orchestrator.py: phase 2.5, after resolve_data and before the first step, reaches and judges every `$loam.` input once; stale fails the run as "Stale input" before anything is written; cannot tell is written into the receipt of each step that read it, once; every receipt's lineage gains loam_inputs with each verdict, which is where D-166's listing lives. tests/test_loam_reach.py: the fake records real hashes, since a fake md5 now reads as a changed input; 7 tests (17 in the file). Expected on Maine: places predates D-167, so its params read as cannot tell until maine_geography_graph is rerun once.

### Change 4: seats as their own preparation; LOAM-1 closed; Sprint 04 step 4 closed

garden/methods/information/legislative_seats.yml (new) and its entry in garden/methods/index.yml: a preparation method for one Legislature's seats, places critical and read through loam, rosters critical and read as acquired. plots/maine/preparations/maine_seats.yml (new): `$loam.places`, `$manifest.legislature_133_house`, `$manifest.legislature_133_senate`; legislature 133, sworn_in 2026-12-02 (D-135), state_fips 23; the four tribal seats copied from tests/test_seats.py's TRIBAL list, which matches TRIBE-3 and NAME-3, and held equal to it by a test. A later Legislature is an edit of legislature, sworn_in, the two rosters and the tribal list. tests/test_seats_preparation.py: 3 tests. The real build_seats primitive runs through the real orchestrator on places reached through loam, with a fresh verdict, and places' own provenance entry (run and step) travels into the seats receipt, which proves D-167 end to end. With rosters unavailable the run refuses at data resolution, naming both, and writes nothing.

LOAM-1 is closed by changes 1 to 4. Sprint 04 step 4 is closed on its dependency (TIME-2): build_seats runs on places another run made. Carried: the 133rd's rosters after 2026-12-02 (TRIBE-4, SEN-1); NOTE-3, and confirmation of the tribal list by Kalli and Person 3, before anything is published. Do not run maine_seats on real data before 2026-12-02: the rosters are auto-acquirable, and resolution can acquire and commit (RESOLVE-1), so a run could write the outgoing Legislature's roster into the manifest before build_seats refuses it.

### Plan build 1, fork, and change 5: KEYS-1

| ID | Decision | Why | Reverse if |
| --- | --- | --- | --- |
| **D-168** | Places, edges and later place-keyed values live in loam as DuckDB views over the Parquet files its receipts point at, never as copies. Claude's lean, accepted by Kalli | Loam holds no truth of its own. And Loam.snapshot() writes the whole bed as a shareable Parquet: values copied into the bed would leave through it without ever meeting the gate, which runs only at exits | A query is too slow over files; then materialize behind the gate, never in the bed |

| ID | Finding |
| --- | --- |
| **KEYS-1** | Resolved by change 5. build_places, build_place_edges and build_seats declare KEY and SPATIAL_UNIT and build their receipt metadata in output_metadata(): places (authority, code), a place; edges their two ends, an edge; seats (legislature, chamber, seat_kind, seat_ref), a seat. build_place_edges now refuses an edge key used twice. Receipts carry the key once the geography graph is rerun |
| **CON3-1** | Contract 3 section 2 defines each weight as a share of "the `from` town's" population. build_place_edges defines it as a share of the `from` place's, and MEGIS divisions are the `from` end of their edges. The code is right; the contract's wording is to be widened at the close |

Change 5: soil/transform/build_places.py, soil/transform/build_place_edges.py, soil/transform/build_seats.py, tests/test_graph_keys.py (5 tests).

### The geography graph rerun, after change 5 (2026-11-11)

`python -m canopy.cli sows plots/maine/preparations/maine_geography_graph.yml` ran all 12 steps. The places receipt now declares id_fields [authority, code] and spatial_unit place (1,663 rows), and every provenance entry names run maine_geography_graph and its step. Asked phase 2.5's question alone (Orchestrator on maine_seats.yml, `_judge_loam_inputs`, which resolves no data and touches no roster), `$loam.places` was reached and judged fresh, with nothing changed and nothing untold: the first real `$loam.` read on Maine data.

| ID | Finding |
| --- | --- |
| **PREP-1** | Corrected: `python -m canopy.cli sows <run.yml>` runs a preparation, since sows builds an Orchestrator for any run file. PREP-1's "no CLI command runs a preparation" was out of date; state.md's trap was right |

### Change 6: plan build 1, places and edges as views in loam (D-168)

canopy/loam/graph.py (new): plant_graph() makes two DuckDB views in the bed, places and edges, over the file of the one tended or gathered receipt of type places or place_edges, resolved from the project root. No view, and a reason in the report, when there are none, several (naming each, as D-163), a receipt that declares no key (KEYS-1), a file not on disk, or a file without its declared key columns. A plot with no graph opens normally. canopy/wonder/session.py: open_plot calls it as its fifth motion and reports report["graph"]. tests/test_loam_graph.py: 8 tests, among them the plan's rebuild test (delete and rebuild the bed: the same places, edges and catalog rows) and a snapshot carrying no graph values, which is D-168's reason held as a test.

Noted for plan build 5: canopy/cli/wonder.py plants and tills inline rather than through open_plot, the drift session.py's own docstring warns of, so `wonder` does not yet see the graph views.

### Plan build 2: values at places (changes 7 and 8)

| ID | Decision | Why | Reverse if |
| --- | --- | --- | --- |
| **D-169** | A value is keyed (unit_authority, unit_code, indicator, time). Its level always comes from joining places, never from the value | One fact in one place: a value for a place the graph does not hold has no level, which shows instead of hiding. Value tables already carry no level | Never expected |
| **D-170** | A declared, cited seed, seeds/vintages/boundaries.yml, says which boundaries a publisher's values sit on. For the ACS: the final year of the estimate period; legal areas on January 1 of it, legislative districts on its session year, statistical areas on the decennial census. Loam checks Contract 3's vintage invariant through it. A publisher with no rule attaches nothing | Values say when they were estimated, not on which boundaries; a parsing rule in code would be a silent choice | SRC-1 lets a value carry its own boundary vintage, written at derivation |
| **D-171** | No ACS value attaches to a Census tribal area while places hold the 2020 legal areas; a reading says so in one plain line. Kalli's decision | ACS 2024 is on 2024 boundaries. Showing a number on a nation's area with a skippable caveat is the opposite of MP-72's qualified view | TRIBE-6 shows an area unchanged from 2020 to 2024 |
| **D-172** | Value tables that give the same key agree when value, moe and households match within 1e-9, null and NaN alike meaning none. Agreement is one fact, kept once with every receipt that says it (recorded_in). Any disagreement means no view, naming only the receipts that disagree and an example key | Maine's real receipts held 3,222 county broadband values twice, identical, from an old receipt and a new one; refusing every value over the same fact recorded twice was too strict | A reader needs to choose between disagreeing tables; then a declared precedence, never an implicit one |

| ID | Finding |
| --- | --- |
| **TRIBE-6** | Open. Acquire the Census 2024 tribal area layer, compare each of Maine's 8 areas with its 2020 legal area, and record an unchanged area as a declared equivalence so its values may attach. Reviewed with Kalli and Person 3 beside NOTE-3 before anything about tribal areas is published |
| **KIT-1** | A real instance: the town values receipt carried measurement_id indicator:code, though derive_indicator.R has built indicator:unit_authority:code since D-132. The receipt predated the code, and freshness would have called it fresh, because primitive code is not judged (D-165). Rerunning maine_cousub_indicator_values fixed the receipt |
| **NAME-2** | Met in the values table: `authority` there is the publisher (us_census_acs) and `unit_authority` the place-code authority, while in places `authority` is the place-code authority. A join on the bare word would be wrong. Weighs toward settling NAME-2 before the grove |
| **LIN-3** | plots/maine/.envelopes/derive_values.envelope.json has no lineage, so it predates D-84 and can be judged neither fresh nor stale. Its 3,222 county broadband values equal the experiment maine_county_indicator_standings' exactly. It is the derive step of maine_broadband_access_subscription__cii_indicator_values_91b5c0; rerunning that experiment would give it lineage. Under D-172 it blocks nothing and stays visible in recorded_in |

Change 7: seeds/vintages/boundaries.yml (new); canopy/loam/graph.py, indicator_values and place_values views (VALUES is reserved in SQL, so the view is named for its type), every place_values row carrying status, attached and why; tests/test_loam_values.py. Found on the first real run: the duplicate-key refusal fired on Maine's receipts, and its message named every included receipt, the innocent town table among them. Change 8: D-172; every value row names its receipt (value_receipt) and every receipt that gives it (recorded_in); the raw rows are the indicator_value_rows view; a refusal names only the receipts that disagree. tests/test_loam_values.py: 12 tests.

### Plan build 3: a plot is a set of places (change 9)

| ID | Decision | Why | Reverse if |
| --- | --- | --- | --- |
| **D-174** | A manifest may declare `places:`, a list whose entries are a place key alone, or a place key `with: contained` (it and everything it contains, followed down contains edges) or `with: touching` (it and everything an overlaps edge joins it to). The plot's places are the union, in the plot_places view, each with included_by. Declaring nothing means every place in the graph. An unknown key or a malformed entry means no view, naming every problem | The plan's own examples (every town in a county, every town touching a district) as rules over the graph, so a declaration stays true when the graph is rebuilt; a plot never claims a place its graph does not hold | A plot needs a place the graph cannot hold; then the graph grows, never the declaration |
| **D-175** | There is no parent key. A sub-plot, when one exists, relates to its parent through contains edges between their places | No sub-plot relationship exists in the code (a grep of parsing, models, the manifest schema and Delton's manifest finds none), so the plan's "sub-plot inheritance becomes contains edges" is a future, not a migration | Never expected |

Change 9: canopy/orchestrator/models.py and parsing.py (Manifest.places, carried as written); canopy/wonder/session.py (the manifest parsed once and handed to planting and the graph, P-01); canopy/loam/graph.py (the plot_places view, resolved with a recursive walk of contains edges and both directions of overlaps); seeds/schemas/manifest.schema.yml (places documented); tests/test_plot_places.py (10 tests, among them the rebuild test for plot places).

### D-173, and the mid-sprint hand-off (2026-11-11)

| ID | Decision | Why | Reverse if |
| --- | --- | --- | --- |
| **D-173** | The four reservation subdivisions' values attach in loam, carrying their census_tribal_area note (rule 9), and are held for Person 3 and the client-led consultation (MP-72) before any is exposed. D-171 covers Census tribal areas, the aiannh level, only. Claude's judgment, delegated by Kalli | They are county subdivisions, legal areas on 2024 boundaries like any town, so D-171's reason, boundaries that do not match, does not apply; withholding sound numbers from the nations and those working with them would be a silent paternalism. Computing is not exposing: what leaves is the gate's and the consultation's to govern | Person 3 or the consultation says these values should not be computed, or not shown |

On real Maine data after change 9: plot_places holds all 1,663 places (Maine declares none); place_values attaches 1,996 values, 168 attached unchecked (the 42 unorganized territories, all census_funcstat S, confirming D-170's seed), 9,618 with no place (other states' counties), and 3,222 agreeing rows collapsed (LIN-3's ghost). No sldl or sldu value exists yet: district values are to be derived in builds 4 and 5. state.md rewritten for the hand-off (D-160).

### Change 10: district values from the ACS, keyed by chamber (plan builds 4 and 5, D-176, D-177)

plots/maine/preparations/maine_district_indicator_values.yml (new): two derive steps, sldl_derive on acs_sldl_2024 and sldu_derive on acs_sldu_2024, the same four indicators, time, authority and reliability as the cousub preparation, each keyed by its chamber's authority. No repair step: derive_indicator only records joins_to in metadata (line 415). garden/methods/information/indicator_values.yml: state legislative district added to aggregation_unit_level's options, with one sentence of description; the orchestrator refuses a choice not among the options (orchestrator.py line 509), so a literal spatial_unit was never possible. Freshness reads no method, so the cousub receipts stay fresh. tests/test_district_values.py (new): 5 tests, among them each district step keyed by its chamber's authority, checked before anything runs, and one code under three authorities attaching as three places and three facts. joins_to stays governance_unit as the method writes it: map.py and visuals.py read it as the layer a table draws on, and whether a district map finds governance_unit_sldl_2024 under that type is for the publish door (Sprint 08) to check.

| ID | Decision | Why | Revisit when |
| --- | --- | --- | --- |
| **D-176** | District values are derived by their own preparation, maine_district_indicator_values, one step per chamber, keyed us_census_sldl and us_census_sldu. Claude's lean, accepted by Kalli | Contract 3 rule 1: a district's value is the ACS's own. A GEOID is unique only within its level (GRAPH-1): keyed us_census_geoid, House District 5's value would attach to Cumberland County and pass its vintage rule. A separate file leaves the cousub receipts and their header's town-grain story untouched | A third chamber-like level appears, or the cousub and district preparations must share a run |
| **D-177** | One grain, state legislative district, names both chambers; the chamber is named by unit_authority. Claude's lean, accepted by Kalli | A value's level is its place's, never its own (D-169), so spatial_unit only describes the grain and the authority carries the chamber without loss. One file, one choice | A reader needs the chamber from spatial_unit alone, without the place |

On real Maine data, after change 10: place_values holds 604 sldl rows and 140 sldu rows, all attached (151 and 35 districts, 4 indicators each); no district row collapsed into another receipt's. indicator_values reads 12,526 rows, 3,222 collapsed, the collapsed rows all from receipts older than this change. 485 tests pass.

### Change 11: wonder opens its plot through open_plot, and says what the graph made (plan builds 4 and 5, D-178)

canopy/cli/wonder.py: run() opens the plot with open_plot instead of planting and tilling inline, so wonder sees the graph's views for the first time (the noted, unnumbered gap in state.md, closed). PlotNotFound prints the init hint, exit 2, as before; a folder with no manifest.yml is now refused rather than read, matching plot_names. The planted and tilled lines are unchanged, built from open_plot's report. _say_graph (new) says what the graph made: one line for a plot with no places, else one line naming every view made with its size, then a line for every view not made and every value receipt left out, each with why. The full report stays in open_plot's return. tests/test_wonder_graph_voice.py (new): 4 tests.

| ID | Decision | Why | Revisit when |
| --- | --- | --- | --- |
| **D-178** | wonder says what the graph made: views made with their sizes in one line, every view not made and every value receipt left out with why, and a plot with no graph in one line. Option A of fork 11a, Claude's lean, chosen by Kalli | A view not made is why a reading through it comes back empty, so leaving it unsaid is a silent choice; printing the whole report (agreeing lists, collapsed counts) would bury the possibilities a person came to read | A reader needs the agreeing or collapsed detail every time; then a --graph flag, never a longer default |

On real Maine data, after change 11: wonder maine says "graph: places (1,663), edges (2,693), indicator_values (12,526), place_values (12,526), plot_places (1,663)", with no view refused and no value receipt left out; wonder nyc says it has no graph, once. 489 tests pass.

### Change 12: edge rules, declared universes, and a district read through its edges (plan builds 4 and 5, D-179 to D-185)

seeds/universes/universes.yml (new): which edge weight counts what each indicator's value rests on, keyed by the rests_on.counts phrase; households and persons equal their weights (D-121 declared, not assumed), renter households with rent burden computed is contained by households. canopy/loam/edge_rules.py (new): load_universes, zero_here, share_of, may_allocate, allocate_count; pure, stores nothing (D-168). canopy/wonder/place.py (new): read_place measures one place through its edges, say_place speaks it (P-03); part_level defaults to cousub. canopy/cli/wonder.py: --place AUTHORITY:CODE reads one place instead of the plot's possibilities. readiness.py is unchanged on purpose: it reads types against methods, and a place is not a type; the plan's "readiness and wonder can read a district" is met by wonder alone. No indicator in the repo declares aggregation: sum, so allocation refuses every indicator today and accepts only a raw count; the contract sits above the seed, so population_weighted_mean never licenses a move along an edge. tests: test_edge_rules.py (13), test_universes.py (5), test_place_reading.py (14). On real data, House District 42 reads its own ACS value for four indicators, its 7 towns with both shares, every town's value most-here first, the range, the towns wholly here, the towns its line splits (Owls Head, 80.1% of its 669 households; Islesboro, 0.7% of its 330), and a firm range of the towns wholly here on a sound sample. Islesboro, which first topped the firm broadband range though almost all its households are in another district, now sets no end of any range but the full one, where its share and count are said. 521 tests pass.

| ID | Decision | Why | Revisit when |
| --- | --- | --- | --- |
| **D-179** | Allocation is built as a tested rule and used by no reading yet: only a measure whose seed declares aggregation: sum, only by a weight that equals its universe, always with a warning naming the weight and that the figure is computed on read. Option B of fork 12b, Claude's lean, chosen by Kalli | The rule should be held by tests before anything relies on it; the first figure a person sees about a district should be the ACS's own; a 2020 weight times a 2024 count mixes vintages and deserves a use that decides how to say so | The outreach planner (Sprint 12) needs counts in places; see COUNT-1 |
| **D-180** | ZERO-1: a town with none of a value's universe in a place is listed under it and kept out of its range, with the reason; zero is judged by the weight the value's universe declares, and representation by the population weight. Kalli's decision, on Claude's lean (B) | MP-76's honesty about geography is kept, and no town's numbers speak for a district it has no people in. DAS-1's households without persons are why zero follows the value's universe | A use needs zero-share towns ranged, or the display rule changes for representation |
| **D-181** | Which edge weight counts what a value rests on is declared in seeds/universes/universes.yml, keyed by the counts phrase, with equals or contains; a phrase not declared has no share and no zero test. Kalli chose C (declare it in a seed); Claude placed it beside the indicators rather than in them | $indicators resolves to the whole declaration, so a field in rests_on would make every value receipt stale; seeds/weights/ holds index weightings ($weights.), a different idea under the same word. A test holds every indicator's phrase to the seed | A renter weight is built on the edges (TENURE-1), or a universe needs a weight neither edge carries |
| **D-182** | A contained universe shows its count and no share: rent burden's towns show their renter households, never the household share relabeled. Claude's lean, accepted by Kalli once its reason was explained | A town's renters can sit unevenly across a district line, so its household share beside its rent burden is a true number about the wrong people | A renter weight exists (TENURE-1) |
| **D-183** | Statistical areas attached unchecked and values on small samples enter the range, and every end of every range says what it rests on; a firm range is read beside it, of the towns wholly here without them. Claude's judgment, delegated by Kalli and refined with her twice | Leaving shaky values out would hide real places; naming them beside the range was not enough, because a shaky value could set an end unseen. The firm range first included split towns, and Islesboro topped it on real data, so it was narrowed to the towns wholly here | A reliability rule other than acs_small_sample is declared |
| **D-184** | A place is read by canopy/wonder/place.py, read_place to measure and say_place to speak, kept small so the place profile (Contract 4, Sprint 06) grows from it; wonder takes --place by key, never by name (GRAPH-1). Option A of fork 12a, Claude's lean, chosen by Kalli | The first reader keyed by place rather than by type; one measurement, many renderings (P-03); a name can mean three places | Sprint 06 builds profile.py; friendly names for --place land with the explorer's search (Sprint 09) |
| **D-185** | Towns wholly inside a place are ranged apart from towns its line splits, by the universe's own weight (all of it here, or not); a split town is named one by one with its share and the count it is of; each indicator's towns are listed most-here first; a range whose ends are one is said once. Claude's proposal, accepted by Kalli after she twice asked for better | The real reading showed Islesboro, with 0.7% of its 330 households in House 42, setting an end of the firm broadband range. A whole town's value describes this place's people and a split town's does not; the boundary is the data's own, so no threshold is chosen | A use needs a split town's value weighed rather than listed; then COUNT-1 |

| ID | Open item | Defined |
| --- | --- | --- |
| **COUNT-1** | Count people, not rates: for a ratio indicator, the households with the barrier are value times households over 100, exactly; allocated along an edge by D-179's rule, they answer who needs to be reached, and a split town's rate stops mattering. The outreach planner's starting point (Sprint 12) | change 12 |
| **TENURE-1** | A renter share needs a renter weight on the edges, from tenure counts by block; which 2020 table carries tenure at the block level is not yet checked | change 12 |

Change 12, completed: fdc8c20 committed place.py and test_place_reading.py one revision early, without the firm range narrowed to the towns wholly here or equal ends said once, while its ledger entry described both. Found by reading House 42's range lines on real data after the commit; the check's first pattern could not see the old firm line, which began "without". This commit carries the revision the entry describes: House 42's firm broadband range reads 87.2 (Rockland city) to 93.7 (North Haven town), across 2, Islesboro sets no firm end, and limited English reads all 0.0. 521 tests pass.

### Change 13: a value's publisher is published_by (build 6, NAME-2, D-186, D-187)

soil/transform/derive_indicator.R takes the publisher as published_by and writes it as a published_by column, and refuses a leftover authority param by name, since read it would leave every value with no publisher and no boundary rule. canopy/indicators/preview.py, its twin, takes and writes published_by; it still reads the publisher from a manifest source's provenance.authority, which this change leaves alone. canopy/loam/graph.py chooses each value's boundary rule (D-170) by published_by. The param is renamed in five run files (cousub, the district preparation twice, county standings, the CII experiment) and the key in three method recipes (published_by: $source.authority). In places, edges, plot_places, the place reading and the grove, authority now means only who assigns a place's code. Every value receipt was rerun: cousub, both districts, county values and standings, and the CII experiment's derive_values and standardize_standings (LIN-3's two receipts; whether they now carry lineage is read at the close). This is KIT-1's first real instance: freshness does not judge primitive code, so after derive_indicator.R changed, every old receipt still read fresh while its file held the old column; the reruns were made by hand, on purpose. On real data: no value file carries an authority column; indicator_values reads 12,526 rows, 3,222 collapsed, as before; no value lacks a publisher; no ACS value at a ruled level lands as no_rule. 521 tests pass. Edits were made by a guarded script that changed nothing unless every edit matched exactly, with git diff read before anything ran, in place of whole-file replacements of a 979-line and a 418-line file; Kalli's call, for this change.

Two lessons, both from this change. A signature's callers are found by searching for the keyword itself, not a value it happens to carry: renaming preview.derive's authority= keyword broke 25 tests in five files that a search for us_census_acs could not see, which the working agreement (search the tests for every fake of a signature) already said. And a keyword search must still be read for meaning: the fix's first pattern also renamed test_plot_places.py's key(code, authority=GEOID), whose authority is the place-code one, the double meaning NAME-2 exists to end; that file was restored from the last commit.

| ID | Decision | Why | Revisit when |
| --- | --- | --- | --- |
| **D-186** | NAME-2: authority means only who assigns a place's code; the publisher of a value is published_by. Option C, Kalli's decision, made knowing it keeps the word authority she would rather not use | It removes the one wrong join, a word with two meanings, with the smallest change; clarity of meaning over replacing the word | A refactor of its own renames authority itself (named_by was considered) |
| **D-187** | The rename reaches value tables, run files and method recipes, and stops at manifests. Option B of fork 13a, Claude's lean, chosen by Kalli | It is the vocabulary a person reads and writes when making a run, and every value receipt reran anyway; manifests write provenance inline as well as in blocks and reach the resolver, so they are a sweep of their own (NAME-4) | NAME-4 is taken |

| ID | Open item | Defined |
| --- | --- | --- |
| **NAME-4** | Manifests still name a source's publisher provenance.authority, which preview.py and recipe.py's SOURCE_FACTS read and the method recipes reach as $source.authority. One sweep renames it to published_by across every plot's manifest, block and inline forms, with the resolver | change 13 |

### Change 14: the place-code authorities have one declared home (build 6, AUTH-1, D-188)

seeds/authorities/authorities.yml (new): each authority that may assign a place's code, its levels, each level's code width, and one real example, measured from Maine's places (923 MEGIS divisions at 5, 8 Census tribal areas at 5, 529 towns at 10, 16 counties at 5, 151 House and 35 Senate districts at 5, the state at 2); tracts declared under us_census_geoid at the Census's width of 11, marked as not measured, since no plot's graph holds them yet. AUTH-1 named four copies of the list; there are six: preview.py, derive_indicator.R, build_places.py, build_place_edges.py, build_place_outlines.R's level map, and build_seats.py's chambers. tests/test_authorities.py (new, 8 tests) holds every copy to the seed, importing the Python ones and reading the R ones as text, and checks that each level belongs to exactly one authority and every example has its level's width. 529 tests pass.

| ID | Decision | Why | Revisit when |
| --- | --- | --- | --- |
| **D-188** | AUTH-1: the authorities are declared once, in seeds/authorities/authorities.yml, and every copy in the code is held to it by a test; the copies stay, and the grove reads the seed. Option B of fork 6b, Claude's lean, chosen by Kalli | Silent drift between six copies becomes a failing test that names the file, with no runtime change and no rerun. Making the copies read the seed (option A) would let a seed edit change what a primitive does unseen by freshness (KIT-1) | Sprint 10 settles KIT-1; then the copies can read the seed |

### Build 6, SRC-1 decided (D-189)

A source's unit authority is a fact about the source: an SLDL acquisition is SLDL codes by nature. The method recipe already takes unit_column, unit_pad and name_column from the source; unit_authority was the one unit fact a run declared, which is where change 10's Androscoggin trap lived. Decided now, before the grove handoff, and built with NAME-4, since both touch every manifest source: one sweep, not two.

| ID | Decision | Why | Revisit when |
| --- | --- | --- | --- |
| **D-189** | SRC-1: each manifest source declares its own unit_authority, checked against seeds/authorities/authorities.yml (D-188); runs take it as $source.unit_authority, and a run that also declares one is refused, since two declarations of one fact can disagree. Option A of fork 6c, Claude's lean, chosen by Kalli | The fact lives where it is true, so a preparation cannot mislabel its source, and all four unit facts come from the source | A source holds units under more than one authority; then it is two sources |

| ID | Open item | Defined |
| --- | --- | --- |
| **SRC-2** | Build D-189 in NAME-4's sweep: unit_authority on every indicator source in every plot's manifest, the recipe's $parameters.unit_authority becomes $source.unit_authority, a run declaring its own is refused, and D-176's test is kept as a second guard. Resolved params stay the same strings, so freshness should read the existing receipts as fresh; check that before trusting it | build 6 |

### Change 15: an index carries its units' authority (build 6, SEAM-1, D-190)

roots/indicators/weighted_index.R: every pillar and composite row carries unit_authority, and its measurement_id is index:unit_authority:code, as every value's is (D-132). Standings with no unit_authority column, or rows naming none, are refused by name; so is an index across more than one authority, naming each. impute_nearest_neighbor.R is unchanged: it builds its output from its input (out <- df), so the authority passes through the chain. Maine holds no index receipts, so nothing was rerun. tests/test_index_r_oracle.py: the fixture's standings carry us_census_geoid; the chain test checks the authority and the id on pillar and composite rows; 2 new tests, a missing authority refused and an index across us_census_geoid and us_census_sldl refused by name. 531 tests pass.

| ID | Decision | Why | Revisit when |
| --- | --- | --- | --- |
| **D-190** | SEAM-1: an index carries its units' unit_authority, ids it index:authority:code, and refuses to rank units of more than one authority, or of none. Option A of fork 6d, widened from the id alone when the code showed the rows carried no authority at all; Claude's proposal, accepted by Kalli | A row without its authority cannot be joined to a place, so fixing the id alone would put an authority in the id that the row does not hold; and ranking counties beside districts compares units never measured beside each other. With no index receipts in Maine, it costs no rerun now | A composite across levels is wanted on purpose; then it is a new method, not this one |

Change 15, completed: d355aba committed the ledger entry for change 15 without its code, as fdc8c20 did for change 12. A long paste broke partway, and zsh discards a whole pasted buffer when it is cancelled, so neither file block ran. Found by the commit's own summary, 1 file changed. This commit carries weighted_index.R and tests/test_index_r_oracle.py as the entry describes; 531 tests pass. From here, every commit block is guarded, committing only if the code files it names have changed, and every file is pasted on its own.

### Build 6, MAP-4 decided, and build 6 closed (D-191)

A map layer is a source like any table, so D-189's rule answers MAP-4: the layer declares whose codes it holds and where. With this, every key the grove will federate is decided: NAME-2 (D-186, D-187), AUTH-1 (D-188), SRC-1 (D-189), SEAM-1 (D-190) and MAP-4 (D-191).

| ID | Decision | Why | Revisit when |
| --- | --- | --- | --- |
| **D-191** | MAP-4: a map layer source declares its unit_authority and the property holding its codes, as D-189 has indicator sources declare theirs; map.py joins a table's (unit_authority, unit_code) to the layer that declares that authority, and _UNIT_KEYS goes away. Option B of fork 6e, Claude's lean, chosen by Kalli | One rule for every source, table or layer; map.py would otherwise hold a seventh copy of authority knowledge outside D-188's test. District maps were waiting on the publish door anyway | A layer holds codes under more than one authority; then it is two layers |

| ID | Open item | Defined |
| --- | --- | --- |
| **LAYER-1** | Build D-191: unit_authority and the key property on every layer source, in NAME-4's sweep with SRC-2; map.py's join by declared authority, with the publish door (Sprint 08). Verify the district layers' property names on real data first | build 6 |
| **LEDGER-3** | MAP-4 names two entries: Sprint 02's county map check and Sprint 04's _UNIT_KEYS gap, which D-191 settles. An ID used twice is a ledger fault; a later reference to MAP-4 must say which one | build 6 |

### Sprint 05 closed

The done-when is met: wonder reads any Maine district through its edges (changes 10 to 12). Contract 3 is at 1.0, with CON3-1 applied and G-4 to G-11 recorded. Every grove key is decided (build 6, D-186 to D-191). The progress report is field-guide/docs/progress/information/sprint-05.md; state.md is rewritten for the hand-off (D-160), including the working agreement as it now stands. 531 tests pass. Next decision ID: D-192.

## Between Sprints 05 and 06: NAME-4's sweep, change 1 (D-192 to D-196)

D-189 could not be built as written. Preparations are hand-written with literal params and never pass through recipe.py, and compose writes plain values into every experiment by design, so "a run that also declares one is refused" would refuse every composed experiment and still never compare a hand-written step with its source. The rule became agreement, held by the orchestrator before any step runs.

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-192** | Amends D-189: a run may write unit_authority or published_by, and Orchestrator.validate() refuses any step whose written value, resolved as the run resolves it, differs from its input dataset's declaration, or whose source declares none. Steps reading $steps or $loam are not checked; their facts arrive in receipts. Claude's lean, chosen by Kalli's delegation | The source's word is the fact and the run's is a record of it; this catches change 10's Androscoggin trap in every kind of run, and no run file changes, so receipts stay fresh | A fact needs to differ between run and source on purpose; then it is not a source fact |
| **D-193** | Which params repeat a source fact is declared per primitive, as source_facts in its layer registry (input, and param to source.<key> or provenance.<key>); registry.py refuses a malformed declaration. derive_indicator is the first. Claude's lean, chosen by Kalli's delegation | One check for every primitive that opts in; Sprint 06's carrier counting can use it without new orchestrator code | A fact lives somewhere other than source or provenance |
| **D-194** | A retired word makes only its dataset underspecified, never the whole plot. parsing.declaration_problems holds the one rule: parse_manifest records it, compose and preview refuse a source that has it, and the agreement check refuses a step reading an underspecified source. First entry: provenance.authority, now provenance.published_by. Claude's lean, chosen by Kalli's delegation | A community plot written against older docs still opens and says what to change, which P-01's underspecified already allowed | Retired words multiply; then a reader of history, as Vocabulary has |
| **D-195** | The manifest has one parser: preview.load_manifest and wondering._manifest_datasets read through parse_manifest and keep the raw document, signatures unchanged. Claude's lean, chosen by Kalli | Three readers could see two different files in one; the rule in D-194 lives once | Preview or wonder needs the dataset model rather than raw declarations |
| **D-196** | unit_authority sits in a dataset's source block, beside unit_column, unit_pad and name_column; the publisher stays in provenance. Option A, Claude's lean, chosen by Kalli | All unit facts together, and provenance keeps its one meaning (D-186) | Never expected |

Findings and wrong hypotheses:

- NAME-2's rename stopped short of soil/_registry.yml: derive_indicator still declared its publisher param as `authority` and described rows as carrying authority. Fixed here.
- Wrong hypothesis: manifest.schema.yml declares provenance.authority. It does not; every schema hit is the place key (authority, code), and source provenance is checked by no schema at all.
- Wrong hypothesis: there was one manifest loader, then three readers counting loam's. loam delegates to parse_manifest. The readers were parse_manifest, preview.load_manifest and wondering._manifest_datasets, the last found only by reading compose's caller.
- The ACS provider reads only the source keys it names, so source.unit_authority is ignored at acquisition.
- 558 passed with -rs, no skips. Four Maine runs derive, and all four agree with their sources.

| ID | One line | Defined |
| --- | --- | --- |
| **NAME-4** | Closed: manifests name a source's publisher provenance.published_by, block and inline forms | change 1 |
| **SRC-2** | Closed in D-192's form: unit_authority on all six Maine indicator sources, $source.unit_authority in the method recipes, a disagreeing run refused. Freshness predicted fresh, since no run's params changed; not yet checked | change 1 |
| **LAYER-1** | Carried to Sprint 08 with map.py's join: Sprint 06's carriers are points counted over located_in edges, not layers joined by code | change 1 |
| **SRC-3** | Some sources name no publisher: the two MEGIS layers and the two legislature rosters. Whether every source must declare published_by is undecided | change 1 |
| **USE-1** | A run does not honor underspecified in general: _resolve_manifest_ref checks available and the file only. D-192 refuses it for source-fact steps; going wider needs its own look at older plots | change 1 |
| **SPEC-1** | models.py defines a second PrimitiveSpec, without preconditions or source_facts; registry.py's is the one used | change 1 |

## Sprint 06 opened: the design pass, Contract 4 at 0.3 (D-197 to D-200)

Sprint 03's state: the ledger holds no Sprint 01, 02 or 03 headings, which is LEDGER-1 (D-98 to D-124 never ledgered); the work happened and the record did not. The gate exists: rules 1, 2, 4, 9, 10 and 11 appear in canopy/expose/gate.py, refusal records in canopy/expose/records.py. So part 5 can carry real refusals.

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-197** | profile.py composes read_place: build_profile wraps a PlaceReading in a PlaceProfile with six parts, and the other parts come from their own readers. Option A of fork 1, Claude's lean, chosen by Kalli | read_place stays one measurement (D-184, P-03); the profile is a document that leaves through the gate, which a reading never does; wonder --place and its tests are unchanged | A reader other than the profile needs carriers or disagreements per place; then they become readings of their own |
| **D-198** | Verdicts are margin-aware (meets, below, within_margin, cannot_judge with its reason, no_threshold). Ratio margins come from a new soil primitive, derive_margins, one more step in each indicator preparation, writing margins keyed by measurement_id, with each indicator's formula (proportion, ratio, summed numerator) declared in a seed beside the indicators and cited to the ACS handbook; place_values joins them. Claude's combined lean, chosen by Kalli | derive_indicator.R keeps no component margins, so deriving them there would rerun every value receipt by hand (KIT-1); a separate step adds receipts and changes none, keeps lineage on every margin, and lets preview carry the formula as an oracle | A publisher's margins for a ratio become available directly; then they pass through |
| **D-199** | The standard declares three kinds of threshold: universal (the right is everyone's; the profile reports how many fall short, from the place's own estimate), trigger (a legal or published line that creates an obligation; the profile lists what crosses it), none (stated plainly, the value still shown). Option C of fork 3, chosen by Kalli | The Information Futures Lab and UNESCO's ROAM-X give a frame and no numbers; the absolute numbers that exist are universal (ITU and UN 2030 targets) or legal triggers (DOJ safe harbor, VRA section 203), and a relative benchmark would break D-74 | A source sets a graded absolute standard that is neither universal nor a trigger |
| **D-200** | Each IFL barrier is a family of registered indicators, each a computable layer at its own grain, with a status (acquired, acquirable, needs_our_model, needs_consent) in place of "not yet measurable". CII's measures are reused as values; only its standings are relative. Kalli's direction, shaped as fork 5 | Every barrier should be something to compute with and to map; a gap in our data is not a gap in the world's (literacy has county estimates in the PIAAC Skills Map) | A barrier has no defensible measure at any grain; then its status says so, by name |

Findings and wrong hypotheses:

- Wrong hypothesis (corrected the same session): Sprint 06's households test needs COUNT-1. households_behind is the value's denominator, already in place_values. COUNT-1 returns for a different reason under D-199: for a universal threshold, the count left out is the finding. It needs no allocation, since every profiled place has its own estimate; allocation along edges stays with Sprint 12.
- TENURE-1 stays out of Sprint 06: rent burden is a need, not an IFL barrier, and gets no universal threshold.
- The IFL's barriers come from its South Florida pilot (We Are Más, 25 navigators, November to December 2023): a taxonomy, not thresholds.
- VRA section 203 coverage is determined and published by the Census Director (latest file December 8, 2021), and needs a fifth-grade-education condition we could not compute well; it is passed through as a published determination. It applies to listed language minority groups only and has an Indian reservation provision (P-8, with Person 3).
- The DOJ safe harbor (2002) is per language group and counts persons: min(5%, 1,000) of those eligible to be served, with a 50-person carve-out. It is guidance for federal funding recipients, not a right, and the seed must say so.
- The PIAAC Skills Map gives county-level hierarchical Bayes estimates of adult literacy and numeracy (ages 16 to 74) for every county, from pooled 2012/14/17 data; a copy is preserved on DataLumos (2026-04-19). County is its finest grain, so a town profile shows it as its county's.
- Contract 4 at 0.2 predated Sprint 05: it named the publisher authority, knew no whole, split or firm ranges, and called the profile a PlotReading. 0.3 fixes all three.

## garden/experiments/in-the-cloud removed, 2026-11-11

Kalli removed garden/experiments/in-the-cloud/ from the repo: a vendored pyyaml (twice, with compiled cpython-313-darwin .so files), validator.zip, a Lambda validator, deploy scripts and an early Terraform pipeline. Not needed, and not fit for a public repo. The infrastructure work lives in terraform/ and canopy/terraform/ (Sprints 07 and 10). The files remain in git history; nothing in them was found to be a secret.

## Sprint 06 session 1: P-9, SRC-2's check, the outlet stack (D-201 to D-205)

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-201** | Outlet sources are read only as seeds/crosswalks/outlets/outlet_sources.yml declares: a header is found by its declared column names, an undeclared column is never read, and a never_read column cannot be declared (Easton's Contact, the SimilarWeb figures) | P-9 found headers on line 2 or 3 and a column naming people; position or a default would read both wrong | A source arrives whose layout no column names can find |
| **D-202** | Stacked records are grouped by exact url (path kept) and name keys, never fuzzy. A group never holds one source twice, and a key value one source holds twice joins nothing. Claude's lean | A missed match leaves a visible duplicate; a wrong one hands one outlet's owner to another. The first run let row order choose 204 matches | A matching method with its own receipt per match is built |
| **D-203** | Place fields keep their meaning (office_* a postal address, named_* a town a source names, served_raw coverage) and are compared only like with like | Cision's address is the publisher's office: it puts Norway's Advertiser Democrat in South Portland | A source says which meaning its place field has |
| **D-204** | An outlet's county comes from the graph through its town; a source's county is a check, never an input. Claude's lean, a small choice | Cision's Outlet County reads Cook (Illinois) on 235 of 353 rows, across every outlet type, so no Cision county can be told right from lucky | Never for Cision; for another source, if its counties check clean against the graph |
| **D-205** | The outlet files stay in garden/reference/ (ignored, line 86) and will be read as manifest datasets whose paths reach outside the plot. Kalli's choice over copying them into plots/maine/.data | One copy of each reference; nothing duplicated | The community kit needs a plot to carry its own references |

Findings and wrong hypotheses:

- P-9 answered: frequency is carried by three sources in three shapes (Cision declared; the ecosystem file's Print for print media only; Easton's Format as free text). Language of publication and paywall status are carried by none. Cision's Outlet Language reads English on every row and omits Amjambo Africa, which publishes in seven languages.
- SRC-2's check: 28 Maine receipts, 20 fresh, 8 cannot_tell, none stale. The 8 are maine_counties, maine_county_units and maine_governance_units, recorded before D-167. Left until something reads them through $loam.
- Wrong hypothesis: every receipt would read fresh. The 8 cannot_tell predate NAME-4.
- Wrong hypothesis: the 353-row Cision file is the 412-row export filtered. They are separate pulls: 297 names in both, 115 and 56 apart.
- Wrong hypothesis: Cision's Cook county was a default on most rows. It is on 235 of 353, across every outlet type, with no pattern.
- Cision's Still Operates? is a hand-added observation (323 yes, 21 ceased, 9 a last-post date) and is stronger evidence for "outdated" than any declared frequency. Who checked, and when, is not recorded.
- The aggregated-signals file is a survey about which data exists, with respondent files; it is kept out of the outlet layer.

| ID | One line | Defined |
| --- | --- | --- |
| **P-9** | Closed: what the outlet files carry, as above | this session |
| **SRC-2's check** | Closed: nothing checkable changed; the 8 untellable receipts carried as RECEIPT-1 | this session |
| **RECEIPT-1** | Rerun maine_counties, maine_county_units and maine_governance_units when anything reads them through $loam. | this session |
| **OBS-1** | Language and paywall need our own observation of each outlet, a receipt per observation: a status under D-200 | this session |
| **WHERE-1** | Which place meaning counts as where an outlet is, for located_in | this session |
| **SRC-4** | The ecosystem file's publisher, the Still Operates? receipt, and every outlet source's terms | this session |

## Sprint 06 session 1, continued: the maine_outlets preparation (D-206)

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-206** | `$crosswalks.<name>` resolves the one file seeds/crosswalks/**/<name>.yml into a step's params, refused as an input, refused when none or two files share the name. Claude's lean, option A | Seeds reach runs as params ($weights, $reliability, $indicators), so a receipt records what was read and freshness sees an edit as a changed param; a path param would let a seed change silently | A crosswalk grows too large to carry in every receipt's params |

Built: maine_outlets (stack, groups, disagreements) as a preparation over five outlet_listing manifest datasets in garden/reference/ (D-205); method outlet_reconciliation; types outlet_listing (excluded), outlet_stack, outlet_groups and outlet_disagreements (tiers left to Person 3). 595 passed with -rs.

| ID | One line | Defined |
| --- | --- | --- |
| **OUT-REG-1** | stack_outlet_sources' registry entry names Maine's five listings as inputs, so a plot with other listings needs its own entry; the community kit must decide how a primitive takes a declared set of inputs | this session |

## Sprint 06 step 2: located_in (D-207)

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-207** | located_in edges are their own type, located_in_edges, one artifact per point layer, in place_edges' columns and key; state, county and town from the 2024 face a point falls in; districts, tribal areas and divisions from that face's 2020 block through the spine. A point in a split block is placed by its face and listed; one in no face, on a line between disagreeing faces, or without coordinates is listed as unplaced. Refined option A, Claude's lean, chosen by Kalli | loam's edges view needs exactly one place_edges artifact (D-163), so a second would cost every plot its edges; each level comes from what it is defined on, so a point never contradicts its block's overlaps edges and a split block never misplaces a town | loam reads several edge artifacts as one view |

| ID | One line | Defined |
| --- | --- | --- |
| **CON3-2** | Contract 3 section 2 still calls located_in a kind in the edges table; it needs D-207's wording | step 2 |
| **SERVES-1** | A carrier's location is not whom it serves: a library system serves a legal jurisdiction, and a town with no building may be served by contract. A serves relation is separate from located_in | step 2 |

## Sprint 06 step 3: libraries, the first carrier (D-208)

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-208** | A library outlet is FSCSKEY-FSCS_SEQ; only fixed outlets (CE, BR) are points; mobile outlets (BS, BM) are listed in the receipt and never placed; a hand-placed geocode, a structure status other than 00 (with IMLS's meaning or `unknown`) and a non-FSCS system are flagged, never dropped; the outlet file's encoding is declared, Windows-1252, from its own text. Claude's leans, small choices | FSCSKEY repeats across a system's outlets; every Maine bookmobile wears its home library's coordinates, so as a point it would count a second library where it is garaged (SERVES-1); 0x96 appears twice, each a dash between words | IMLS publishes a bookmobile's stops, or names its file's encoding |

Findings:

- maine_libraries: 262 fixed outlets placed, none unplaced, no split blocks, 1,572 edges (6 each). IMLS's CENBLOCK agrees with our face block for 261 of 262; ME0292-002 differs by a neighbouring block in one Waldo County block group.
- CENBLOCK is a 2020 block, shown by the check; the README does not say so.
- Declared Latin-1, the step refused the outlet file on byte 0x96 rather than read a control character into two branch names (Virginia, Washington). The first probe's silent fallback to Latin-1 would have read it wrong without a word.
- Wrong hypothesis: a point layer's total_area_m2 could be null. The envelope schema requires a number; a point layer's area is 0.0, measured.
- Status 25 has no meaning in IMLS's status-structure training; flagged unknown on one Maine outlet.

| ID | One line | Defined |
| --- | --- | --- |
| **TRIBE-7** | No Maine library in the survey stands in a Census tribal area: the PLS has long not collected systematically from libraries on reservations, so a tribal area's carrier count must read as unseen, never zero. Wording with Person 3 | step 3 |
| **SCHEMA-1** | A metadata field's type is checked only when a real run writes an envelope; fixture tests of a primitive cannot see it. A test could validate output_metadata against seeds/schemas/ | step 3 |
| **STAT-1** | Find IMLS's definition of STATSTRU 25 in the FY 2024 documentation | step 3 |
- ME0292-002's two blocks (230270470001044, ours; 230270470001053, IMLS's) share a town, a House district and a Senate district, so the disagreement places it the same at every level counted.

## Sprint 06 step 3, continued: carriers counted (D-209)

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-209** | A carrier is a registered indicator (role carrier) with a third derivation kind, located_count: one layer's located_in edges per place, over the place's own 2020 persons or households, every place a row, zeros included, the count beside the rate. It reads no source table, so it asks no acquisition for anything; preview refuses it by name; it lives in seeds/indicators/carriers.yml. Our counts get a boundary rule (publisher rewildingcities). Loam's statistical-area rule now judges ACS values only. Option A, chosen by Kalli | D-200: each barrier is a family of registered indicators. A separate file, because a declaration carries its file's sha256 and one more entry in rewilding.yml would stale every receipt that read from it | A carrier needs a margin, or loam learns per-publisher levels |

- Wrong hypothesis: loam's place_values judged each publisher by its own rule. It read the ACS's levels and its statistical class for every publisher; the statistical class would have marked our counts in unorganized territories unchecked with the ACS's reason.

| ID | One line | Defined |
| --- | --- | --- |
| **SURVEY-1** | Loam's only boundary rule is the final year of `time`; a count's boundaries are the graph's, so a later survey counted on the 2024 places must still name 2024, or it reads as a mismatch | step 3 |
| **LOAM-2** | place_values reads the ACS's `levels` for every publisher; a publisher with other levels needs loam to read its own | step 3 |

## Sprint 06 session 1: hand-off

Built since D-209: place.py reads a carrier apart (count first, its persons, its maker, no town range), tests/test_place_carrier.py. 643 passed with -rs.

- Wrong hypothesis: a MEGIS town office layer exists. The only MEGIS town point layer (METWP24PT) is town centroids by its own description, so as carriers it would give every town exactly one office; refused by name.
- MEGIS publishes a Libraries point layer of 390 features against IMLS's 262 fixed outlets; the difference is unread.
- Nothing in the repo geocodes: soil/validate/geocode_to_unit.py, in the October snapshot, matches place names to units with fuzzy matching and produces no coordinate (check the current file).

| ID | One line | Defined |
| --- | --- | --- |
| **GEO-1** | No geocoder exists. Lean: the Census Geocoder first (free, batch 10,000, match type and 2020 block per address, interpolated along street centerlines), with ArcGIS World Geocoding (credits, KEY-1) or Maine NG911 address points beside it as second authorities, never merged | hand-off |
| **TOWN-OFF-1** | Town offices need an address list to geocode; the MEGIS centroid layer is refused as a carrier | hand-off |
| **LIB-2** | MEGIS Libraries (390) against IMLS fixed outlets (262): a second authority, read side by side | hand-off |
| **INDFILE-1** | carriers.yml's hash is in libraries_counts' receipt; one file per carrier family (lean) or rerun on every addition | hand-off |
| **SCALE-1** | place.py writes "per 1,000" while the scale lives in the declaration; carry it in each value row | hand-off |
| **LOC-VIEW-1** | No loam view of located_in edges; needed to name the carriers in a place | hand-off |

## Sprint 06 session 2: closures declared, meaning in one home (D-210 to D-212)

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-210** | A library outlet's structure status is declared once, code to meaning and group: open (placed), permanent (listed, never placed: a rule) or temporary (the D-211 choice). A blank or undeclared status on a fixed outlet refuses the run; a mobile outlet's status is never judged. Maine declares every code the FY 2024 outlet layout holds except 22, whose meaning for a point is unsettled, and declares 03, which FY 2024 lists outside its files, so an older file is read by the same rule | An undeclared status was placed with the flag unknown, which assumed the outlet open, while an undeclared outlet type was refused; the two now agree. Codes and meanings from IMLS, PLS FY 2024 Data File Documentation and User's Guide (June 2026), Appendix B | A later layout adds a code, or 22 appears on a fixed outlet |
| **D-211** | A temporary closure (STATSTRU 23) is a method choice, temporarily_closed: listed or placed. Maine chooses listed, so Atkins Memorial Library, Corinth (ME0054-002), is named in the receipt and counted nowhere, and 261 fixed outlets are placed. The primitive refuses a value outside the two, since the orchestrator only warns (CHOICE-1). Claude's lean, handed over by Kalli | IMLS leaves temporarily closed outlets out of its own tables and frame (76 outlet records in FY 2024), and a closed building is not where people look. Reasonable people could place it, so it is a choice, not a rule | A closure is known to have ended within the fiscal year, or a reader needs the building counted |
| **D-212** | A carrier's meaning lives once, in its method's description and choices. The primitive's docstring says only how; the run header, the registry entry and the indicator rationale point to the method. A rule (the other way is simply wrong) is a test; a choice (reasonable people differ) is declared. Bookmobiles are a rule, D-208 unchanged | The bookmobile and SERVES-1 reasoning was written in five places, and choices: {} hid a meaning-changing decision in params | A method needs a reading its description cannot hold |

- Wrong hypothesis: the fixed and mobile split lived in code. It was declared params all along; the drift was in the meaning, restated five times.
- Wrong hypothesis: Maine's FY 2024 fixed outlets carried no status flags. A grep over .data returned nothing, for a reason unread; the points file holds two, Corinth (23) and Cliff Island (25).
- Closed: STAT-1. STATSTRU 25 is survey nonrespondent (FY 2024 Documentation, Appendix B). Maine had 255 respondents among 256 libraries (its Table 1); Cliff Island Library, flagged 25, is likely that one, not checked against a list. It stays placed, flagged status_25:survey nonrespondent.
- Code 03 does not occur in the FY 2024 outlet file: permanent closures are listed in its Appendix C, outside the data files. Older files kept such records (FY 2017: 96 outlet records closed or temporarily closed).
- LIB-2 now reads 261 placed IMLS outlets against MEGIS's 390.

| ID | One line | Defined |
| --- | --- | --- |
| **FSCS-1** | Corinth and Cliff Island are outlets of systems the survey does not count as public libraries (C_FSCS N), and both counted under "Public library outlets" until D-211 listed Corinth. IMLS keeps such libraries in its files but out of aggregate figures and national totals, and warns of overcoverage. Place, list, or rename the indicator | session 2 |
| **CHOICE-1** | The orchestrator only warns when a run's choice is not among its method's options, or a declared choice is missing; a meaning-changing choice can pass on a warning. Lean: an error | session 2 |
| **SCHEMA-2** | Ten methods share a house shape (options as a list, primitives as a list, produces as an object) that seeds/schemas/method.schema.yml does not describe, interpretation is not in it, and nothing validates a method against it. Lean: the schema follows the ten, then a test validates every method | session 2 |
| **CMAP-1** | The carrier map as a view, never a file: carrier kinds as semantic types in the domain vocabulary, sources as national catalogues in seeds/sources/, the map a query over them. Everything in seeds/ is shared by every plot, so no seeds/carriers/. Waits on reading seeds/schemas/domains/information.yml | session 2 |

## Sprint 06, session 3: SCHEMA-2

| **D-213** | seeds/schemas/method.schema.yml is the one home of a method's shape, v2.0, additionalProperties false throughout. Every reader loads a method through parsing.load_method_data, which refuses a shape the schema does not describe, a key written twice (REG-5) and a default outside its options, naming every problem. A run on a refused method is a validate() error. Options are a mapping keyed by option id; an empty value means the choice's description says it; an option carries no id of its own | Three shapes were in use and the parser held none of them; a parse failure became a skipped warning and _load_method_data returned {}. A list of options drops meaning; per-option text would write the information methods' comparative prose twice (D-212). nyc_heat_island chose raster, an option's second name | A method outside the commons must match the schema too |
| **D-214** | requires_primitives is a list of layer/name references, each resolving in its registry (tested); a recipe uses only primitives its method declares. The older methods' per-method purposes are YAML comments | One reference form, the one a step already uses. hot_cold's hotspot_analysis named no registered primitive; it is local_gi_star and classify_clusters | |
| **D-215** | produces is a list, semantic_type and data_category required, name optional | Thermal methods make several outputs | |
| **D-216** | garden/methods/index.yml routes only: domain, id, path. A method's name and answers_question_types live in the method; MethodIndexEntry carries no name or answers. The test holds every file routed once, by its own id and domain | The index had drifted: one method missing, one under the wrong domain, a name differing, a missing comma | A catalog reads names from the methods |
| **D-217** | roots/count_by_unit is not registered and is deleted; ownership_concentration_analysis no longer declares it | Found by D-214's test: the method named an unregistered primitive. count_located (D-209) already counts points in places over located_in edges, every place a row, zeros included; registering a second count would give one truth two homes. The method promises no unit counts, and concentration_index reports outlet counts itself | OWN-1 redesigns the method |

| ID | One line |
| --- | --- |
| SCHEMA-2 | Closed by D-213 to D-216 |
| SCHEMA-3 | canopy/wonder (wondering.py, possibility.py) reads method YAML raw, not through load_method_data, and still accepts the retired produces and requires_primitives shapes; route it through the one loader and drop them |
| INTERP-1 | The thermal, perception and county_units_for_mapping methods have no top-level interpretation; required once each has one |
| OWN-1 | ownership_concentration_analysis is pre-graph: geocode_to_unit places an outlet by matching place-name strings (a silent WHERE-1 choice, against D-203, D-204), and concentration_index keys by feature_id. Redesign over located_in and count_located at step 8, after WHERE-1 and GEO-1 |
| STUB-1 | plots/maine/experiments/maine_information_access__ownership_concentration_analysis_4a8f59.yml is a thermal template: raster validation and a last step naming roots/analysis, which is no primitive. It fails validate() if run. Retire or rewrite with OWN-1 |

## Sprint 06, session 4: CMAP-1's types, and the drift the walk found (D-218 to D-222)

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-218** | Each carrier kind is its own semantic type in the domain vocabulary, never one type with a kind field | A type names a kind of artifact. Under one type, receipts from IMLS, NCES and HRSA would share a name across different terms and vintages, and a kind column is invisible to the loader's checks. A view can merge kinds into one layer at harvest without the vocabulary pretending they are one thing | A publish door needs one layer a view cannot give it |
| **D-219** | institutional_node is retired with no alias. IMLS's placed outlets are library_outlet (vector, geojson, public). The unbuilt Maine manifest entry of the same name (available false, manual, multi-kind) is removed; build_located_in accepts library_outlet and formal_outlet by name; ownership_concentration_analysis reads library_outlet until OWN-1. maine_libraries rerun: 261 placed, 3 mobile and 1 temporarily closed listed, as before | An alias is global and permanent: it would tell every plot that institutional_node means library points, true of the receipts and false of what the name was coined for. "Outlet" is IMLS's word for a library building; the type's description says so beside formal_outlet | |
| **D-220** | A live declaration (registry entry, method, manifest, preparation, experiment, and the experiment schema's example) names a current type, never an alias or a state-suffixed name. Validating, repairing or reprojecting changes a dataset's state, never what it is: state is provenance, kept in the receipt. Aliases and suffix_fallback stay, so old receipts still read forward | resolve() lets a retired name run, right for a receipt and wrong for a declaration. sample_features listed park_boundaries five times; assign_feature_id's receipts were born under an alias; the experiment schema's own example taught the pattern | |
| **D-221** | Every type live work named is declared: water_boundaries and forest_boundaries (thermal); neighborhood_boundaries (base, a statistical unit unless a neighborhood governs); roads, nighttime_lights, population_density (base; the last a modeled estimate, never a count of anyone); measured_composition (perception, a quadrat's recorded fractions). Renamed to existing homes: the perception method's outputs to composition_validity and segmentation_metrics, and census_tracts dropped for governance_unit (tigerweb's tract). check_alignment is unregistered and its 0-byte file deleted (D-217's precedent); alignment_report goes with it | The walk found ten names in use and never declared. Declaring keeps each method's reach honest (blue and green cooling; the measured_quadrat option). A second name for an artifact already declared would give one truth two homes | Person 3 confirms the proposed tiers |
| **D-222** | The wonder composer drafts current types: a conformed output keeps its requirement's type, an analysis output takes its product's declared semantic_type. The three composed drafts (e6e967, 4ade33, and STUB-1's 4a8f59) are deleted; wonder recomposes on demand | The experiment drift had one source: _compose_steps minted <role>_validated and used a product's name as its type. Each draft also named a method or primitive that does not exist (buffer_gradient_analysis, roots/statistics/hotspot_analysis, roots/analysis), so fixing their types would only have turned the walk green over files that cannot run | |

- Wrong hypothesis (state.md, session 3): the libraries' placed points had no type of their own. They were institutional_node, from prepare_library_points.
- Wrong hypothesis: imls_pls_fy2024_outlets is a dataset with a type. It is a label on located_in edges, set by the preparation, so the bridge from a carrier indicator to its points' type is not a lookup yet (CMAP-1).
- Wrong hypothesis: the park_boundaries_* aliases would pass the walk. They resolve, but the walk asks for current names, by design.
- REG-6's test now also refuses a registry entry over an empty file: check_alignment.R was 0 bytes and passed the existence check.
- Registry versions are not bumped for declaration-only changes (D-152's precedent; VER-1).
- The manifest entry was removed by a guarded edit, never a whole-file replacement (D-50). The surgeon has no removal and its changelog records acquisitions, so no changelog line.
- Kept from the retired manifest entry: a library that hosts information differs from one that originates it (OBS-1's cousin).
- Comment drift fixed: vocabulary headers said the loader stamps `module`; it stamps `domain`.
- Tests: 710 to 829. New: tests/test_carrier_types.py (D-218, D-219), tests/test_current_type_names.py (the walks over every registry, method, manifest, preparation and experiment, and the composer), two REG-6 cases.

| ID | One line | Defined |
| --- | --- | --- |
| **CMAP-1** | Still open. Types done (D-218, D-219). To go: where carrier-hood lives (lean: the indicator registry, role carrier), the bridge from an indicator's located_in layer label to its points' type, the IMLS catalogue in seeds/sources/, and the view itself | session 2 |
| **STUB-1** | Closed by D-222: retired | session 3 |
| **TIERREAD-1** | Vocabulary.get_tier reads extra["tier"], while every domain file declares resolution_tier, so get_tier is None for every information type. Find who reads resolution_tier before new carrier types lean on it | session 4 |
| **QUADRAT-1** | Whether a measured quadrat becomes a bird's-eye mask, to share falsification_test's one currency (label masks): a modeling choice for the day field data exists | session 4 |
| **OWN-1** | Addition: the method's institutions input still describes libraries, town halls, schools and government sites while its type list holds library_outlet; widen it as each carrier type arrives | session 3 |
| **SCHEMA-3** | Still open: D-222 changed what _compose_steps writes, not how wonder reads methods | session 3 |
| **Person 3** | Addition: tiers for library_outlet, water_boundaries, forest_boundaries, neighborhood_boundaries, roads, nighttime_lights and population_density (each proposed public), and measured_composition (none yet) | session 4 |

## Sprint 06, session 5: where carrier-hood lives, and the bridge to the points' type (D-223, D-224)

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-223** | Carrier-hood lives in the indicator registry, as each indicator's role: carrier. IndicatorRegistry.with_role() finds them. Never on a type, in a method, or in seeds/carriers/. role carrier and derivation located_count are independent: the carrier map draws carriers whose derivation is located_count, and a carrier from a published table is read in the profile with nothing to draw | role is already required, one per indicator (D-107). A thing is a carrier for one claim and something else for another (a library in a heat or broadband analysis), so a flag on its type would be false elsewhere. The method says what is placed and why (D-212), not which barrier its count serves. seeds/carriers/ would hold a second copy of the role, and seeds gets no domain folder (session 2) | A carrier needs more than one role |
| **D-224** | A located_count names the type it counts, derivation.counts (library_outlet), never a layer label; a layer key in a seed is refused by name. The label (imls_pls_fy2024_outlets) stays in the preparation as the edges' from_authority, and so in the receipt. count_located reads one layer's edges and names it as counted_layer. The orchestrator checks the chain before the run (_validate_located_counts): the count step reads one located_in_edges input made in this run, and the step that made it reads exactly one input of the counted type. Edges reached through $loam or $manifest are refused. carriers.yml no longer names maine_libraries as its source dataset | The label carried three facts: what is counted (the seed's), whose points (the method's and the receipt's), and which release (the receipt's only: registry.py keeps vintage out of an indicator). In the seed, each fiscal year would change carriers.yml's hash and stale every receipt that read it (INDFILE-1). Edges carry no type and primitives never see an input's type, so the check reads the declarations. Two sources of one type (LIB-2) become two receipts of one indicator, compared | Edges must be read from another run, whose points' type would have to come from receipts |

- Wrong hypothesis (session 5): the layer label did no work. count_located refused edges from any other layer; the guard was kept, narrowed to one layer, and the type check moved to the orchestrator.
- Drift fixed: preview.describe built a derivation apart from Indicator.as_declaration and dropped a passthrough's open_ended. Both now read Derivation.as_dict(), held by a test over every indicator.
- Drift fixed: build_located_in's docstring called layer the layer's dataset id, the sentence behind session 4's wrong hypothesis.
- Drift fixed: carriers.yml named a Maine preparation (source.dataset) in a shared seed. Nothing read it.
- Found: no code reads seeds/sources/. census_tigerweb.yml is reference only, and an IMLS catalogue would be too unless a reader is built.
- maine_libraries rerun; receipt read: counted_layer imls_pls_fy2024_outlets, counts library_outlet.
- Tests: 829 to 841. New: tests/test_located_count_validation.py; cases in tests/test_located_count_indicator.py, tests/test_count_located.py, and tests/test_current_type_names.py (every located_count's counts is a current type). Commit 9b7716a.

| ID | One line | Defined |
| --- | --- | --- |
| **CMAP-1** | Still open. Types (D-218, D-219), carrier-hood (D-223) and the bridge (D-224) done. To go: the IMLS catalogue in seeds/sources/ (reference only: no code reads the folder) and the view itself | session 2 |

## Sprint 06, session 5 (continued): the carrier views and the IMLS catalogue (D-225, D-226); CMAP-1 closed

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-225** | loam plants two more views over receipts' files, never copies: located_in, every located_in_edges receipt carrying the edge key, unioned, each row naming its receipt; and carriers, one row per placed point of every carrier indicator whose derivation is located_count, giving the indicator, the type it counts, the layer, and the point's id, name and coordinates. The points are found through the edges receipt's own provenance record (the newest without lineage_branch): exactly one input of the counted type, whose path is the points file, whose receipt declares its id_field. A layer in two receipts means no located_in view; a carrier whose points cannot be found this way is left out by name. place.py reads an exact count apart by its method (located, never ranged), labels every value by its role from the registry, and reads indicators through IndicatorRegistry | The map is a query, never a file (CMAP-1), and loam's views are how queries are made here (D-168). The runtime path mirrors D-224's check before a run. place.py's word carrier named the role while it meant the derivation, wrong both ways under D-223, and its raw YAML walk skipped every refusal the registry makes | Reading LIB-2's second authority, when two edges receipts of one type must both be drawn |
| **D-226** | IMLS's outlet types (C_OUT_TY: fixed or mobile) and structure statuses (STATSTRU: meaning and group) are one shared crosswalk, seeds/crosswalks/libraries/imls_pls_outlets.yml, passed whole to prepare_library_points as reading through $crosswalks; no plot declares them. A release's outlet member and encoding are declared in its manifest entry (source.outlet_member, source.outlet_encoding), and prepare_library_points' registry entry holds the run's copies to them as source_facts. seeds/sources/imls_pls.yml is reference only: publisher, identifiers, files, what Maine measured, and a pointer to each fact's home, restating none; a test holds that its pointers exist. prepare_library_points 1.2.0; maine_libraries rerun, unchanged (261 placed, 3 mobile and 1 temporarily closed listed) | The codes are IMLS's, the same in every state, and lived in Maine's plot file; outlet_sources.yml is the precedent for how a source is read living in seeds/crosswalks. The encoding was written in the manifest's prose and the run's params, held together by nothing (D-192's case). The map became a query over the registry and loam (D-223 to D-225), so a catalogue's job is reference, not reading | A second release reads differently, or code comes to need the catalogue |

- Found (D-225's real read): 1,566 located_in rows, exactly 261 placed outlets times six places each; 261 carriers. House District 42 names North Haven and Rockland, and its count row holds 2: the view and the count agree.
- Found: receipts repeat inherited provenance records; the libraries edges receipt's chain holds 19, graph_repair_towns five times (CHAIN-1).
- Drift fixed: place.py's carrier, CARRIER_METHOD, _is_carrier and _say_carrier renamed to the exact count they meant; its unused yaml import removed.
- Drift fixed: the IMLS catalogue's first draft repeated the manifest's url, member and encoding; trimmed to a pointer before it shipped.
- People: Kalli delivers the whole product, every sprint included; the teammates once named in state.md work on other things. Their items are Kalli's. P-8 and TRIBE-7's wording wait on the Wabanaki nations' terms.
- Tests: 841 to 856. New: tests/test_loam_carriers.py; cases in tests/test_place_carrier.py, tests/test_library_points.py, tests/test_library_preparation.py. Commits 2f389f4, 42dc694.

| ID | One line | Defined |
| --- | --- | --- |
| **CMAP-1** | Closed by D-218, D-219, D-223 to D-226 | session 2 |
| **LOC-VIEW-1** | Closed by D-225 | hand-off |
| **CHAIN-1** | Receipts repeat inherited provenance records; find where inheritance appends without deduplicating | session 5 |
| **Person 3** | Retired: the items are Kalli's; P-8 and TRIBE-7's wording wait on the nations' terms | session 5 |

## Sprint 06, session 6: the declaration hash, one experiment per question (D-227 to D-229); INDFILE-1 closed

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-227** | An indicator's declaration_sha256 is taken over its own mapping, canonical (keys sorted at every depth, fixed separators, lists in order), without its rationale (UNHASHED). It is computed when the indicator is parsed and kept on the Indicator (spec_sha256); declaration() never reopens the file, and a registry built in memory hashes too. as_declaration takes no argument. Weights and reliability are unchanged: each of their files holds exactly one declaration, so their whole-file hash already is the declaration's | A receipt hashes what its run read. The whole-file hash staled every receipt that read any indicator in a file when a sibling or a comment changed (INDFILE-1). Freshness already compares the resolved params whole, so the hash earns its place only by covering what as_declaration does not hand over: source, weight_by, replicates. Rationale is prose that points to the method (D-212) and changes no number | A field outside the mapping comes to change what numbers mean, rationale starts carrying meaning, or a weights or reliability file holds more than one declaration |
| **D-228** | One experiment per question. maine_county_indicator_standings answers basic_needs_and_opportunity (its rent_burden and vehicle_access sub-questions, so no single sub_question is named), with cii_rent_burden and cii_no_vehicle; its choices and id are unchanged, and it was edited by hand, not recomposed. Broadband's county standing lives only in maine_broadband_access_subscription__cii_indicator_values_91b5c0, which uses the same method and the same choices (sample sd, nation_50_states_dc, county) | It named no curiosity (D-64), and kind: preparation could not fit it: county_standardize is a roots/ step and cii_indicator_values an analysis method, two errors. Naming civic_health_overall would let three indicators stand in for a question about five pillars and an overall score, the borrowing the cousub preparation refuses. Broadband's standing was computed twice. The "Counties, Ranked" panels its header cited have no reader in the repo | A reader needs these standings and broadband's in one receipt, or civic_health_overall's standing_among_nation is built |
| **D-229** | The no-curiosity warning names only the gap: write or choose the curiosity the run answers. It never advises kind: preparation; that advice comes only from the error for a run whose method is a preparation method, which could pass as one. A rule, held by tests/test_preparations.py | The warning is raised for runs with an analysis method too, and for those the advice traded a warning for two errors. County standings followed it to the edge of that | The rules for a preparation change (D-98) |

- Found: the eight receipts that recorded a declaration_sha256 went stale once at D-227's switch. The probe (_sprint06/probe_freshness.py, read-only, deleted at hand-off) walked recorded and current params path by path: every difference was a declaration_sha256. Rerun: maine_libraries, maine_cousub_indicator_values, maine_district_indicator_values, maine_county_indicator_standings, maine_broadband_access_subscription__cii_indicator_values_91b5c0. All eight then read fresh.
- Found: maine_libraries' $loam inputs (block_spine, places, block_division_assignment) judged fresh; libraries_counts_values names counted_layer imls_pls_fy2024_outlets, 732 place rows, one per-declaration hash; libraries_points holds 261 placed outlets, as before.
- Found: maine_broadband_access_subscription__cii_indicator_values_91b5c0 is a live composed experiment (curiosity broadband_access, sub_question subscription), not a D-222 leftover. Kept and rerun.
- Found: the libraries counts receipt carries 34 provenance records (CHAIN-1, seen again).
- Found: Maine DOE's Schools & SAU Data is an AWS QuickSight dashboard (P20W+ SLDS), school years 2021-22 to 2025-26. Its metadata: a state school ID exists; opened, closed, renamed and repurposed are inferred from a change in name or ID between years; School ID 2117 and non-Maine schools are excluded, yet the map shows points near Albany and Boston; nothing says where coordinates come from.
- Found: origin carried four commits made after session 5's hand-off, by bash-win and Jessica Pham (staging Terraform; API load tests and plot locks; the Docker image and environment.yml; NYC fetch dates). D-227 was rebased onto them; no file overlapped. A local environment.yml edit, committed by mistake under another message, was dropped in the rebase: origin already held its lines, and matplotlib besides.
- Found: canopy/api/locustfile.py imports locust, which environment.yml does not install (DEPS-1).
- Drift fixed: tests/test_indicator_references.py held the whole-file hash as an invariant; replaced by tests/test_declaration_hash.py.
- Drift fixed: maine_county_indicator_standings' header cited panels with no reader; rewritten to say what it answers and why broadband lives elsewhere.
- Tests: 856 to 867. New: tests/test_declaration_hash.py (ten cases); two cases in tests/test_preparations.py; one removed from tests/test_indicator_references.py. Commits 718dcc1 (D-227), a95aa8d (D-228, D-229).

| ID | One line | Defined |
| --- | --- | --- |
| **INDFILE-1** | Closed by D-227: a file's layout no longer moves any receipt. Moving an indicator to another file still changes declared_in, which is provenance, not drift | earlier |
| **STAND-1** | Two runs in the Maine plot write indicator_standings (county standings, 91b5c0), so $loam.indicator_standings would have to choose; nothing reads it today | session 6 |

## Sprint 06, session 7: schools as the second carrier (D-230); JOIN-1 and TRIBE-8 opened

| ID | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| **D-230** | Schools are placed from NCES EDGE Public School Locations 2024-25: one national release zip, its headerless pipe-separated text table read in UTF-8 through seeds/crosswalks/schools/nces_edge_geocode.yml (23 columns in order, M and N markers, operating codes 59 and 63), keyed NCESSCH. A school is in the state where NCES's point stands (STFIP), never where its operator sits (OPSTFIPS): a rule, held by tests/test_school_points.py. Maine's three Wabanaki community schools, Indian Township School, Sipayik Elementary School and Indian Island School (OPSTFIPS 59, the Bureau of Indian Education), are placed, flagged with their operator, and given one located_in edge in every drawer, a Census tribal area included. Kalli's choice A (place and count everywhere now), with her guard that Indian Island counts once, as the county subdivision it is: its school lands in 2301957936, the Penobscot County piece, never the water-only Aroostook piece. Maine DOE's exports and MEGIS place nothing: neither carries a school ID. prepare_school_points 1.0.0; seeds/sources/nces_edge_geocode.yml and seeds/sources/maine_doe_schools.yml are reference only | An operator filter would erase the three schools without an error, unseen read as zero (TRIBE-7). EDGE is the only source with an ID and documented points; a release can be fetched again and hashed, where a dashboard export cannot. The characteristics layer (status, grade span) could not be downloaded. Computing is not exposing (D-173) | The nations, under P-8, ask otherwise; NCES publishes a characteristics release for a matching year; the DOE check needs the state school ID (the CCD directory, joined on NCESSCH) |

- Found: 1bd4dfa, Kalli's, made on a local branch (cli-sows-parity) and fast-forwarded onto main: sows shares one run path with experiment.py (canopy/cli/_run.py new, canopy/cli/main.py deleted); init validates plot names. 867 passed on the branch before the merge.
- Found: Maine DOE's dashboard exports number 13, not eleven. The school and SAU location exports are coordinates with counts, no ID and no name (44 SAUs share one point; out-of-state points near Quincy, MA and Bennington, VT); the name lists carry no state school ID. A dashboard export is not a release: only our copy is evidence, and a file name's number is its export time in milliseconds since 1970, UTC.
- Found: the EDGE text table holds 102,178 rows, 23 fields each when read with its quotes (three names hold a quoted pipe, none in Maine), valid UTF-8, all SCHOOLYEAR 2024-2025. 598 Maine rows by STATE, 595 by OPSTFIPS 23; all 598 stand in Maine by STFIP, with coordinates. Zip sha256 9dc51ecd5cdf6e38bdb679f7ac95e2bf73ee3fb48718b8612cf830800cffb288.
- Found: NCES's geography is TIGER in NAD83, its vintage the start year of the academic year. Loam's final-year rule would read 2024-2025 as 2025, so maine_schools writes SY 2024-25, which reads 2024. DOE's 2025-26 would read as its start: one rule, two meanings, by the string's shape (SURVEY-1).
- Found: loam's join grammar (id_field, id_fields, unit_key) and joinable() match key names, never issuers; every carrier writes feature_id (JOIN-1).
- Found (run read): 598 schools placed, none listed; one located_in edge per drawer across all 598. Indian Township School reaches 1575R, Sipayik Elementary School 2850R, Indian Island School 2760R. Maine counts 598, 0.439 per 1,000 of 1,362,359 persons; Penobscot Indian Island Reservation counts 1 among 370, 2.70 per 1,000.
- Wrong hypothesis (session 7): a name is never a key. D-202 groups by name keys, guarded: a key one source holds twice joins nothing.
- Wrong hypothesis (session 7): 2025-26 would read as 2026. The regex takes the last four-digit run, 2025.
- Wrong hypothesis (session 7): the tabular contract has no time. D-169's value key carries time.
- Wrong hypothesis (session 7): a probe read 3 cards in one drawer. It grouped by to_authority, and us_census_geoid holds state, county and town; grouped by authority and code length, the most is 1.
- Drift fixed: tests/test_school_points.py's INDIAN_ISLAND fixture mixed the release's fields with invented ones; a comment now says which.
- Working agreement: until delivery, Claude drafts all code as zips and Kalli drives the terminal, every command explained.
- Tests: 867 to 896. New: tests/test_school_points.py (13), tests/test_school_preparation.py (9); 7 more from existing walks over new files, not traced. Commits 1bd4dfa, 754d2f7.

| ID | One line | Defined |
| --- | --- | --- |
| **JOIN-1** | loam's join grammar matches key names, never issuers: every carrier's id_field is feature_id, so joinable() relates IMLS's and NCES's points, and a crosswalk between two issuers cannot be said. Places solved this with authority; carrier keys have none | session 7 |
| **TRIBE-8** | count_located refuses Census tribal areas (TRIBE-7's rule, made because the library survey does not see reservation libraries). NCES sees the three schools and their edges reach 1575R, 2760R and 2850R, so public_schools_per_1000 has no tribal-area value yet. Revisit the refusal per layer, with D-171, D-173 and P-8 beside it | session 7 |

## Sprint 06, session 8 (2026-11-14): boundary_vintage, health centers, tribal areas beside their notes

| ID | Decided | Session |
| --- | --- | --- |
| **D-231** | A count says which boundaries it sits on in each row's boundary_vintage, the one vintage of the edges reaching that level. loam reads it for publishers whose rule says boundary_vintage (rewildingcities), so `time` says only when: FY 2024, SY 2024-25, or a snapshot's day. Closes SURVEY-1. Commit 14f3100 | session 8 |
| **D-232** | Health centers from HRSA's Health Center Service Delivery and Look-Alike Sites, a daily snapshot declared by its day and sha256 (the copy of 2026-11-14), every row's record date held to the day; keyed BPHC Assigned Number; read through seeds/crosswalks/health_centers/hrsa_health_center_sites.yml. Rules: administrative sites (Form 5B: no clinical work), mobile units, sites with no point, withheld addresses, sites not open and sites in another state are listed. Kalli's choices: look-alikes counted, seasonal sites placed with seasonal as an adjective, every setting placed (A), who a site serves left to SERVES-1. Maine: 168 placed, 24 listed. Commit f6eecef | session 8 |
| **D-233** | A Census tribal area is counted beside a note, never refused (Kalli): the step names tribal_note and every tribal row carries it as context_note. carrier_unseen_on_nations_land for libraries and health centers, carrier_seen_on_nations_land for schools, Kalli's DRAFT words in seeds/notes/notes.yml, on the nations' terms. loam refuses only the ACS on a tribal area (D-171) and judges each publisher on its own levels (LOAM-2). A tribal code and its persons are AIANNH plus component (R, T). A level no edge reaches takes its places' vintage. Closes TRIBE-8, LOAM-2 | session 8 |

| ID | Opened | Defined |
| --- | --- | --- |
| **CARRY-1** | loam's carriers view carries only feature_id, name and coordinates (graph.py, _points_sql): a point's adjectives and a count's context_note never reach the map. One generic pass-through, for the toggles and the notes | session 8 |
| **KIT-2** | A shared points kit (member and encoding, state field, key, placed or listed, an issuer per key) was weighed and deferred until after delivery; rewildr and pr_io already hold the contract part | session 8 |
| **PLOT-2** | `city:` in preparations, manifests and sows' header ("City: Maine") should say plot: a schema key across the experiment and manifest schemas, every plot file and their readers. After delivery | session 8 |
| **HRSA-1** | HRSA's metadata workbook is not read and the geocode's datum is unknown. HPSA, MUA/P, Health Sites and AHRF are catalogued in seeds/sources/hrsa.yml, unused; whether Health Sites sees the nations' clinics is unread | session 8 |
| **TRIBE-9** | The Census names 0115T "Aroostook Band of Micmac Trust Land"; as far as known the nation now calls itself the Mi'kmaq Nation. Verify, and decide on the nations' terms how a Census name and a nation's own name are shown | session 8 |
| **ACQ-7** | A url release declares its expected hash in source, and a fetch that does not match is refused. Receipts already hash every input (md5, full_file), so a change... The rest of the line was lost in a broken paste before it was committed; restate it from where it was defined | before session 8 |

Closed in session 8: SURVEY-1 (D-231), TRIBE-8 and LOAM-2 (D-233).

Lessons:

- A rule written for one source travels to the next unless it names its reason without naming its source: count_located's tribal refusal said "reservation libraries" inside every carrier's count.
- A column with two meanings hides behind a coincidence: `time` meant both when and which boundaries until a daily snapshot broke the match.
- A snapshot with no release still states its own day; hold the copy to its own words.
- Refusing a place hides it. A number with its note shows it in its context (Kalli).
- A guard that refuses an empty level refuses exactly the unseen case; the empty level takes its places' own vintage, said aloud.

## Sprint 06, session 9 (2026-11-15): GEO-1, clerks' offices placed through Maine's 911 points (D-234 to D-239)

| ID | Decided | Session |
| --- | --- | --- |
| **D-234** | An address is placed first by Maine's 911 address points (site and structure points with their own placement code), the Census Geocoder second. The Census Geocoder interpolates along potential address ranges, often misses non-residential addresses, withholds some in sparse places (Title 13), and can match one batch differently twice (its FAQ, 2024-05-15). Kalli's choice B | session 9 |
| **D-235** | The 911 points are read from the GeoLibrary's file geodatabase, a copy declared by its information cutoff and sha256 (e911_agol_20260827.gdb.zip), never paged from the live service. First decided as filtered live pulls; reopened before it was written, when matching by address made the haystack the whole state (801,786 points, past the provider's 500,000 stop). Kalli's choice B | session 9 |
| **D-236** | Town offices come from the Secretary of State's municipal clerk list (CSV, 560 rows, with MEGIS GeoCode), and the carrier is the clerk's office: where a person registers, asks for a record, and puts a question to the town. The 911 file's classes cannot list them: the default is Residential, and Government - Municipal holds salt sheds, a landfill and a snowmobile club. Names and phones never read; Address Line 2 a note. Kalli's choice B | session 9 |
| **D-237** | One point per distinct office, placed where the matched address point stands and named by its SITE_UID; the rows that name it are the municipalities it answers for (SERVES-1). The GeoCode is a check and a serves-key, never a placer: three townships carry their serving town's code. A rule, as D-230 | session 9 |
| **D-238** | An exact match is house number, street and ZIP, the street spelled through USPS Publication 28 (October 2024) on both sides: directional words to abbreviations (233), a street's last word, if it follows a name, to C1's primary suffix name; the five forms C1 lists twice are resolved by name in seeds/crosswalks/addresses/usps_pub28.yml. No suffix is guessed. ZIP over town, because the GeoCode is blank on 17 rows and means two things on three. Kalli's choice A | session 9 |
| **D-239** | A tie inside one building settles on its one candidate with no unit, building, floor or room (a rule: a suite is inside its address; placed_by building_point). A campus tie, several structures under one civic address, follows the method's choice campus_ties: Maine chooses municipal_class, its one Government - Municipal candidate placed and flagged tie_broken_by_class; otherwise listed. Every settled point carries its candidate count and spread in metres. The class never finds an office, only chooses among points one address named. Kalli's choice C | session 9 |

- Found (run read): 390 offices placed for 458 of 560 rows, 42 shared: 352 exact, 6 building_point, 32 municipal_class (spreads 0.0 to 117.6 m). Listed: 74 no_match, 20 tie, 7 no_street_address, 1 number_not_read. 1,584 of 798,422 address points carry no readable key.
- Found: of the 352 exact matches, 152 are Government - Municipal, 103 unclassed, 44 Residential, 21 Fire Station, 16 municipal police: matching by class would have lost about half.
- Found: the clerk list names Indian Township, Penobscot Nation Voting District and Pleasant Point Voting District. Penobscot's office stands in 2760R and Pleasant Point's in 2850R; Indian Township is no_match, its list saying 8 Kennebasis Road where the 911 file holds 8 Kennebasis St (Government - Municipal, landmark Pasamaquoddy Tribal Office, the publisher's spelling). 1575R's zero is our miss.
- Found: the misses read so far are suites on the street line, highway names (US Route One, State Hwy 193), a number letter set apart (165 B Main Street) and streets with no suffix (7 Minden, nine rows, one office): spelling on our side more than a second geocoder.
- Found: pyproj 3.8.0 (PROJ 9.8.1) does not report the operation it chose for EPSG:26919 to EPSG:4326; the receipt says so, with the versions.
- Found: the 911 file is not the service: 798,422 points against 801,786, older field names, blank placements and one Sturcture - Rooftop.
- Wrong hypothesis (session 9): town offices could be read from the 911 file's classes. Its default is Residential, and Abbot's clerk's address is a Residential point beside a Municipal driveway point.
- Wrong hypothesis (session 9): the clerk list would need a town-name crosswalk. It carries MEGIS GEOCODE.
- Wrong hypothesis (session 9): the file and the live service held the same points. They do not.
- Wrong hypothesis (session 9): most ties would be duplicates. Most are campuses: a town office and a fire station under one address.
- Drift fixed: the manifest told readers soil/geocode_to_unit geocodes; build_located_in's registry listed two point types while four carriers pass through it.
- Tests: 957 to 994 at the first run; the tie work adds 8 primitive cases and 1 preparation case. Commit: GEO-1's (D-234 to D-239).

| ID | Opened | Defined |
| --- | --- | --- |
| **E911-1** | The GeoLibrary page reads No License Provided, Request permission to use. Ask the publisher's permission for a public, attributed, derived clerk office layer; both copies are terms_unknown, so the gate withholds until then | session 9 |
| **GEO-2** | The Census Geocoder as second authority, decided from the listed rows; the first read leans against it | session 9 |
| **GEO-3** | D-237's GeoCode check is not built: whether each office stands in the town its row names or its serving town needs a MEGIS GEOCODE to Census GEOID link | session 9 |
| **GEO-4** | Person-reviewed matches: a declared row per municipality naming the SITE_UID a person read, with its evidence, placed_by reviewed. First: Indian Township (8 Kennebasis St) and 7 Minden (nine rows). Before publishing, since 1575R's zero is ours | session 9 |
| **ARC-1** | canopy/providers/arcgis.py pages by offset with no orderByFields and no guard that the layer held still. Off this path since D-235 | session 9 |
| **TRIBE-10** | The clerk list sees the nations' offices, so the note is carrier_seen_on_nations_land, Kalli's draft words. Two of the nations' offices are named by the state as voting districts, the state's frame; and the 911 file spells Passamaquoddy as Pasamaquoddy. Both shown only on the nations' terms | session 9 |

Lessons:

- A default value is a silent classifier: a class a record falls into when nobody chose one is never evidence of a use.
- Match by address, never by class: an address does not care how its point was filed.
- A read that cannot come back positive proves nothing: a grep on a misspelled path prints exactly what a clean grep prints.
- When a decision's premise moves before the decision is written, reopen it then, not after.
- A long paste can lose its middle and keep its ends: check what landed before trusting it.

## Sprint 06, session 10 (2026-11-15): GEO-4, reviewed clerk matches; WHERE-1, where an outlet is (D-240, D-241)

| ID | Decided | Session |
| --- | --- | --- |
| **D-240** | A person's reviewed match lives in a seed beside the clerk crosswalk (seeds/crosswalks/clerks/maine_sos_reviewed.yml), keyed by the list's address as written, so a review lapses when the list writes the address differently. A review names a 911 point that already stands, by SITE_UID, never typed coordinates, with the evidence read, the day and who read it. The point carries placed_by reviewed with review_evidence, review_read_on and review_read_by, beside exact, building_point and municipal_class. First two: Indian Township (the list's 8 Kennebasis Road, the 911 file's 8 Kennebasis St) and 7 Minden, Greenville (nine rows, one office). Kalli's choice C | session 10 |
| **D-241** | An outlet is where a source names its town: named_town, from Local News Catalyst and the Maine Media Ecosystem file. Cision's office address rides on the outlet as an attribute and is never counted (Cision puts the Advertiser Democrat, a Norway paper, in South Portland); Jo Easton's served_raw waits for SERVES-1. A named town matches a town in the geography graph exactly after trimming and case, within the named county when one is given; a miss is listed with its reason. An outlet no source names a town for is listed no_named_town and never placed from its office. D-238's address matcher is not used for outlets. Kalli's choice (named town) | session 10 |

- Found (run read): 392 offices placed for 468 of 560 rows: 352 exact, 6 building_point, 32 municipal_class, 2 reviewed. Listed 92: 64 no_match, 20 tie, 7 no_street_address, 1 number_not_read. All ten reviewed rows came from no_match.
- Found: 1575R reads 1, 1.316 per 1,000 of 760 persons, beside carrier_seen_on_nations_land. The zero that was ours is gone.
- Found: 7 Minden's one point is classed Law Enforcement -Municipal, landmark Greenville Police Department; these sources do not say whether the clerk shares the building. When CARRY-1 passes point properties to the map, landmark and place_type stay off: they would put a police department's name on a clerk's office and the publisher's spelling of a nation's name in public.
- Tests: 1003 to 1013; the two clerk test files hold 49. Commit: GEO-4's (6fad8ca).

Closed: GEO-4 (D-240), WHERE-1 (D-241).

Lessons:

- A review keyed by what a source wrote lapses the day the source changes its words, so it never silently outlives its need.

## Sprint 06, session 10, continued (2026-11-15): outlets placed by town (D-242 to D-246)

| ID | Decided | Session |
| --- | --- | --- |
| **D-242** | Reopens D-241, whose premise moved before anything was built on it: only Local News Catalyst (30 records) and the Maine Media Ecosystem file (81) name a town, 111 of 924. A named town still places an outlet first and always wins. When no listing names one, the method's choice town_fallback says whether the publisher's office town may place it, by its town name only, never its street address, flagged office_town_not_named, with placed_by on every outlet. Default none; Maine chooses office_town. Kalli's choice | session 10 |
| **D-243** | One outlet per exact-key group, its id made from its members: outlet:SOURCE:NAME_KEY of its first member by the declaration's source_order (the two town-naming listings first), never from row order, since group_outlet_records numbers groups by row. Two groups that would share an id add their first member's line, flagged id_by_line. A missed merge is a reviewed merge in seeds/crosswalks/outlets/outlet_reviews.yml, keyed by each record's source and name as written | session 10 |
| **D-244** | A town is matched by name on both sides after the declared Census suffixes come off (seeds/crosswalks/places/census_name_suffixes.yml: city, town, plantation; County): lowercase, periods and apostrophes dropped, a hyphen read as a space, nothing else forgiven. A named county narrows the match; an office county never does. Two towns are towns_disagree, no match no_town_match, two matches with no county ambiguous_town, none no_town_given: each listed, never placed (a rule). A reviewed town, keyed like a merge, settles only an outlet the run would otherwise list, and refuses when the run no longer needs it | session 10 |
| **D-245** | Operating status is read through operating_vocabulary in outlet_sources.yml: operating (yes), ceased (Ceased Operations), last_post (a value opening Last post, counted and kept with its words); a value in no list stays counted and says so. ceased_outlets is a choice, listed or counted; the default and Maine's is listed. Only Cision's 353-row file carries the column, hand-added, its author and day unrecorded | session 10 |
| **D-246** | An outlet has no point, so build_town_located_in places it by its town code at town, county (its first five digits) and state (its first two) only, each edge carrying its place's own vintage from places; never a House or Senate district, tribal area or division. Outlets (prepare_news_outlets, type news_outlet) then edges keeps D-224's check as written. loam's carriers view leaves a table layer out by name: counted on its places, no point to draw | session 10 |

- Found (run read): 460 outlets placed, 388 by office_town and 72 by named_town. Listed 65: 28 no_town_given, 21 ceased, 11 no_town_match, 3 towns_disagree, 2 ambiguous_town. Operating 312, not_given 141, last_post 7.
- Found: the office fallback carries the map. Portland city counts 121 and Bangor city 67; Cumberland County holds 191 of Maine's 460. Mostly where publishers keep offices: chains, broadcasters, statewide outlets (OFFTOWN-1).
- Found: Cision's outlet types run wider than local news: trade press (Fish Farming News, Commercial Fisheries News) and personal blogs sit beside newspapers, and nothing filters by medium (MEDIUM-1).
- Found: the name rules listed rather than guessed. Blue Hil (a typo for Blue Hill, in both Cision pulls) and Hulls Cove (a village in Bar Harbor) are no_town_match; a ceased record is named only Maine (OUTREV-1).
- Found: 454 of 546 places at state, county and town hold no placed outlet.
- Found: none of the five listings says what day it describes; the count's time reads undated (UNDATED-1).
- Wrong hypothesis (session 10): a reviewed seed could key on group ids. They follow row order.
- Wrong hypothesis (session 10): an outlet placed by town would need the orchestrator's D-224 check changed. Two steps, outlets then edges, satisfy it as written.
- Drift fixed: D-240's line omits the rule its seed and method hold: a review for an address the run places on its own, or that no row gives, refuses the run.
- Tests: 1013 to 1065: tests/test_news_outlets.py 33, tests/test_outlet_carriers_preparation.py 11, the rest from walks over new files. Commit: the outlet carriers (D-242 to D-246).

| ID | Opened | Defined |
| --- | --- | --- |
| **MEDIUM-1** | Which outlet types count as local news: Cision's types include trade press and personal blogs. A declared medium vocabulary and a method choice, decided before the outlet count is published | session 10 |
| **OFFTOWN-1** | The office-town fallback places 388 of 460 outlets and concentrates them where publishers keep offices (Portland 121, Bangor 67). Whether town_fallback stays office_town, read beside MEDIUM-1 | session 10 |
| **OUTREV-1** | The first outlet reviews: Blue Hil (Blue Hill), Hulls Cove (Bar Harbor), the 3 towns_disagree and 2 ambiguous_town outlets; and the ceased record named only Maine | session 10 |
| **UNDATED-1** | No outlet listing declares the day it describes: record each export's day in its manifest entry, and give the count a time | session 10 |

Closed: WHERE-1, reopened and settled (D-242 to D-246).

Lessons:

- Count before you lean: a decision about where things are rests on how many records carry a where at all.
- A number row order hands out is never an identity: key a person's reading by what the source wrote.
- A fallback that is honest and flagged can still carry the map: read the tallies as well as the rule.

## Sprint 06, session 11 (2026-11-15): the outlet carrier's last tree

Commits: the outlet tree (D-247 to D-252, state.md back from PATH), and the hand-off. Tests 1065 to 1091.

### Decisions

- D-247: source_kinds. Local News Catalyst, the Maine Media Ecosystem file and Easton are local_news_lists, whose membership is the evidence an outlet is local news; both Cision pulls are media_databases. An outlet only a database holds is judged by media_database_types: all 20 Cision types declared, two axes (medium, audience); an undeclared type refuses the run; 0 is a placeholder, declared unknown, never a class.
- D-248: the choice database_alone (none, newspapers, print_and_web), default none; Maine chooses newspapers (Kalli's go), since Cision's "Online, consumer" holds Trailspace.com, a gear-review site. A program never counts under any option (a rule: it airs on a station). The medium is judged before the town; one counted and one uncounted known type is medium_conflict; types that say nothing are medium_unknown.
- D-249: a name in statewide_names (Statewide) places an outlet in the state alone, scope state, one edge; a named town wins, flagged statewide_also. build_town_located_in gains scope_field. Amjambo Africa, P-9's seven-language example, now counts for Maine.
- D-250: an office address two or more outlets give is a publisher's office, flagged office_shared; listed under the new option office_town_unshared, Maine's choice. Street normalized as a name is, ZIP five digits, a leading zero a spreadsheet dropped given back (a rule; no US ZIP is shorter). Closes OFFTOWN-1.
- D-251: operating_elsewhere reads a status a source writes outside its operating column, by declared words: the ecosystem file's CLOSED in Medium (2 records).
- D-252: each outlet listing declares source.collected "2026-08" (Kalli: collected at the end of summer 2026); the count's time is "collected 2026-08", held to the manifest by a test. A compiled list describes a day before it. Closes UNDATED-1.

### Found

- Cision's Outlet Type mixes medium and audience, lists radio and TV programs beside their stations and sections beside their papers, and holds non-media values (Maine.gov, Industry research organization) and a placeholder 0 on 23 rows.
- 382 of session 10's 460 placed outlets were held by Cision alone: MEDIUM-1 and OFFTOWN-1 were one question, what a database alone may do.
- The ecosystem file writes CLOSED in its Medium column.
- Maine: 90 placed (70 named_town, 19 office_town, 1 named_state; 74 on a list's say, 16 Cision newspapers alone), 435 listed (327 medium_not_counted, 32 office_shared, 23 ceased, 23 medium_unknown, 19 no_town_given, 6 no_town_match, 3 towns_disagree, 2 ambiguous_town); 525 in all, as in session 10. Portland 121 to 18 (17 named); Cumberland County 29 of 90; Turner 11 to 0.
- Turner's 11 were Turner Publications' free weeklies, all at one Fern Street address with ZIP 4282. The Maine Trust for Local News' Portland address holds 20 outlets.
- A shared address means a publisher, one paper listed several times (Lincoln County News four times), or sections listed as outlets (The Maine Campus).
- The stack holds 926 records (353 + 412 + 50 + 30 + 81); session 10's 924 was a miscount.
- Session 10's hand-off wrote state.md to a root file named PATH; field-guide/docs/state.md still held session 9's words.

### Wrong hypotheses

- That the first run's tests covered statewide outlets: they handed the table from one step to the next in memory. The run writes a csv between the steps; pandas 3 reads text and blanks as str, and Series.map turned a returned None back into NaN, so a missing town read as "nan". The same trap let a blank vintage through silently in build_town_located_in.
- That Turner's publisher wrote its address several ways: it wrote it one way, and the ZIP had lost its leading zero, so _zip5 (five digits or nothing) never compared it. The test fixtures held "04106", a shape imagined, not read.
- That about 125 outlets would place: 105, then 90 once ZIPs compared.
- That D-202's "one source never lists one outlet twice" held for a media database: Cision lists editions and name variants separately (EDITION-1).

### Opened and closed

- Closed: MEDIUM-1 (D-247, D-248), OFFTOWN-1 (D-250), UNDATED-1 (D-252).
- Opened: EDITION-1 (a reviewed merge of one source's editions collides with D-202; a decision, with OUTREV-1), BCAST-1 (stations no list holds are not counted; an FCC authority could say which air local news), SRCFACT-2 (D-192 holds one input's facts; the outlet time is held by a test until a many-input step can be held).
- Carried: OUTREV-1, now 11 town readings and 32 office_shared outlets, codes read for the town readings.

### Lessons

- Test the shapes the data holds, never the shapes imagined: a four-digit ZIP, a blank beside text, a csv between steps.
- A test that never crosses the file the run crosses cannot fail the way the run fails.
- A list's membership is stronger evidence than a database's label.
- Count before closing a fork: Turner reopened one that looked done.

## Sprint 06, session 12 (2026-11-15): the outlet carrier's last door

Commits: 3b79798 (D-253 to D-256), then the reviews commit (D-257, OUTREV-1). Correction: session 11's build commit (a40a57e) landed after its hand-off (6683421); state.md's line putting the outlet tree first is fixed at this hand-off.

Decided:
- D-253: a trailing ", The" is a name written inverted, so the name key drops it (a rule).
- D-254: one source's records alike in name key, url key and office address are one record written twice; they join first, their key held once, same_record_as on each copy (a rule). office_key has one home, group_outlet_records; prepare_news_outlets imports it.
- D-255: a reviewed merge may hold one source twice only when it says editions in words; editions where no source is twice refuses. A review names a record written twice once.
- D-256: office_reads (keep, town, state, list with a reason) for an outlet placed by its office town alone, refused otherwise; an unread one stays placed, flagged office_town_unread.
- D-257: a town review may say state: true in place of a town_code, never both.
- Every reading places an outlet where its newsroom, office or broadcast license is; the towns it covers stay SERVES-1's.

Found:
- Lincoln County News stood as six groups: Cision's copies held its name key twice, so the key joined nothing for anyone (D-202).
- Cision writes names inverted ("Star-Herald, The"); most of the groups that joined this session joined through D-253.
- Three papers were on the map more than once: the Press Herald (Portland twice), the Castine Patriot (Blue Hill and Castine), the Boothbay Register / Wiscasset Newspaper (three towns).
- Cision lists papers that no longer stand apart: The County combined four Aroostook weeklies (January 2025); the Coastal Journal went into The Forecaster; The Free Press went into the Midcoast Villager (September 2024).
- Maine: 97 placed, 4 edition merges, 12 office reads, 4 office towns unread, 4 outlets with no town, no towns disagreeing; Portland 19.

Wrong hypotheses:
- That merges ran after the shared-office count: prepare already merged first.
- That the poisoned key was the main leak: the inverted ", The" joined far more.
- That Portland would read 17: two outlets placed there by review were forgotten.
- That the Wiscasset Newspaper is a Wiscasset outlet: it is made with the Boothbay Register as one paper.
- Session 12's first read helper looked for listed outlets in the csv; they live in the receipt.

Lessons:
- A missing review kind shows only when the real queue is read (state: true).
- Read a merge's neighbours: each double count found led to another.
- A review records who read what, where: Claude's readings cite pages and say so in read_by.

Closed: EDITION-1 (D-255), OUTREV-1 (D-253 to D-257 and the reviews seed).
Opened: OUTCONF-1: before publishing, Kalli confirms the Claude-read reviews (read_by) and decides: student papers listed; the Castine Patriot and Boothbay Register placed by newsroom (Castine, Wiscasset count none of their own); whether the Kennebunk Post, South Portland Sentry and Peaks Islander still publish; Gorham Times, Islesboro Island News, The Irregular, Maine Biz and Maine Wire placed by name. Unread office towns: The Cryer, USM's Free Press, Rolling Thunder Express, Twin City Times. Listed with no reading: The Local News Online, The Rising Tide, two records naming several outlets.

## Sprint 06, session 13 (2026-11-15): zip 1's consultation, the measures

Decided:
- D-258: ratio margins are computed inside derive_indicator, in R and in preview.py, held equal by the oracle test; never as a second indicator_values artifact, since loam refuses a key two receipts tell differently (D-172). Supersedes D-198's "own preparation step"; D-198's verdict rule stands.
- D-259: every ratio declares relation: proportion or ratio. Formulas from Census's 2025 Instructions for Applying Statistical Testing to ACS Data: a proportion falls back to the ratio formula when the value under the root is negative, flagged; sums by root-sum-of-squares; a controlled part's margin (-555555555) is 0; a part whose margin is not computable (-222222222) leaves the margin absent with its reason; every derived margin is labelled an approximation without covariance. No zero-estimate rule: the 2025 instructions carry none.
- D-260: a derivation kind count adds and subtracts cells, its margin by the sum formula; a one-cell count's derived margin equals the published one (tested).
- D-261: language from C16001 at state, county, cousub, sldl and sldu: 12 group counts, 12 group shares, the total count and share, 26 indicators in seeds/indicators/language.yml, groups named in Census's words; each level its own manifest entry (27 variables, under the API's 50). Codes read from the 2024 groups API on 2026-11-15. B16001 is a named gap: county and tract tables ended in 2016, and the state's 86 variables need the provider split.
- D-262: the digital access count is B28002_001 minus B28002_004, the complement of cii_broadband, so the count beside the rate is its own left_out.
- D-263: section 203 read from the 2021 public-use zip (sha256 2d6b21e9...22d6), cp1252 declared; keyed by LANCOUNT, never LANGUAGE text; the flags are the evidence, never recomputed from rounded values; a town joined by its 5-digit MCD to the last five digits of our town GEOID, refused if ambiguous; our towns with no record listed by name; its own artifact type, never loam's ACS values. Its margins state no confidence, so a verdict resting on them is cannot_judge.
- D-264: section 203 tribal rows: an AIAN/MCD row is never a town's value (whole-area estimates); an AIAN-area row (0115, 1530, 1575, 2760, 2850) spans reservation and trust land and attaches to no single place; held whole and shown only on the nations' terms (P-8). A margin of 0 on these totals reads as not given.
- D-265: literacy from the PIAAC Skills Map workbook (sha256 b6745055...34b5, downloaded 2026-11-15), County and State sheets, grpName all, Lit_P1 with 95 percent credible bounds and its out-of-bound and CV flags carried. left_out is POP_DOMAIN times the share and each bound, with NCES's note that the interval is too narrow. The entry says the estimate is modelled partly from race, poverty and education; it is never combined with its own predictors in any index (a rule, tested). openpyxl declared in environment.yml.
- D-266: the ACS is pinned at 2020-2024; Census lists the 2021-2025 release as TBD (schedule updated 2026-10-29).

Found:
- loam's D-172 would have refused the whole values view if derive_margins wrote a second indicator_values artifact.
- The provider already fetches every margin column for an acs_moe indicator, so no reacquisition is needed for margins.
- Freshness never judges primitive code (KIT-1); D-259's new key moves each ratio's hash, so the reruns show.
- The DOJ's 2002 LEP guidance, the safe harbor's source, was rescinded on 2025-03-21; no replacement had appeared by late 2026.
- Section 203 covers four groups only (American Indian, Alaska Native, Asian American, Spanish heritage); Maine's largest limited-English communities can never cross it. Next determinations expected December 2026. No Maine place was determined in 2021.
- The section 203 file differs from its documentation three ways: cp1252 where it says ASCII, LANGUAGE text unlike the documented labels, and the nation's illiteracy rate 1.3200 where the flag rule says 1.31.
- Section 203 holds 522 Maine towns, every one with county 000, and no Maine county rows.
- The Skills Map file writes Lit_P1 where NCES's guide writes LIT_P1. No 2023-cycle county estimates exist; P-7 closes on the pooled map.
- Against "every adult at Level 2 or above", every Maine county reads below; left_out runs about 9,800 to 30,000 adults per county. The verdict cannot tell counties apart; left_out can.
- The FCC's 2026 Section 706 report kept 100/20 and dropped the long-term goal; counting satellite makes service near universal, so step 7b must declare terrestrial only as a choice.
- The acquire command was recorded nowhere in the docs: python -m canopy.cli acquire <plot> --type <semantic_type> senses only; --fetch acquires.

Wrong hypotheses:
- That D-198's separate step could write indicator_values: loam would refuse the view.
- That the safe harbor is a live federal standard: rescinded 2025.
- That B16001 serves towns: not published below the state since 2016.
- That rewilding.yml's B16002 French variant could follow: C16001's French, Haitian or Cajun group is the path.
- That section 203's town key is ST, CNTY and MCD: county is 000 on every Maine town row.
- That an empty grep of the tribal-area file meant nothing for Maine: it searched names; the areas are named and coded differently.
- That the Census files are ASCII because their documentation says so.

Lessons:
- A read that prints head(20) can cut off its own answer: count first, then list.
- Documentation and file disagreed three times in one session: key every reader on the file as read, never on its documentation.
- A sha256 of e3b0c442...b855 is an empty file.
- Where a law withdraws a standard, the project that keeps the line signs its own name to it, as acs_small_sample.yml does.

Closed: P-7 (D-265).
Carried into P-1 (zip 2): the safe harbor's numbers only as rewildingcities' own declared line; section 203's four-group limit said in words; universal verdicts that cannot tell places apart, with left_out leading.

## Sprint 06, session 13 (2026-11-15): zip 1 built and run

Decided:
- D-267: a Census town Section 203 writes once that we hold in pieces (Penobscot Indian Island Reservation, 57936, split at a county line), or that matches none of our towns (the file's 2019-era map; Atkinson, Bancroft, Cary, Codyville, Drew, Magalloway), is held whole under census_s203_mcd and attached to nothing; both are listed. An old town's determination is never mapped onto today's unorganized territory.
- D-268: literacy is its own artifact, literacy_estimates, read by zip 2's profile, like section203_records; neither passes through loam's ACS values.
- D-269: a proportion of exactly 1 is not_derived: the Census's special-case formula was not in the text read.

Found:
- Cumberland's broadband radicand is zero on paper and -4.5e-13 in floating point, so it takes the ratio fallback, as the Census instructions say.
- Bancroft, Codyville and Drew stand in the Section 203 file as town or plantation and in ours as unorganized territory under a new code: deorganization between the two maps.
- 12 of our towns have no Section 203 record (unorganized territories, a gore, small islands); 516 Census towns matched; 0 covered; 38,962 rows.
- Literacy: 17 rows, none flagged; the State sheet carries POP_DOMAIN.
- The oracle caught R counting the households margin twice: needed grows with the rests_on cells partway through the block.
- The envelope schema requires crs on every receipt's metadata, null for a table; both new primitives lacked it.
- The full suite counts 1,166, not 1,148: repo-wide walks gain a case per new file.

Wrong hypotheses:
- That R's needed held only a derivation's cells.
- That two of our towns sharing five digits could only be an error: it is one town split at a county line.
- That every Census town in the file is one of ours: the file's map is older.
- That a ratio still had no CV: test_honest_values held D-18's premise, which D-258 reversed.

Lessons:
- Never build against a schema or part of the codebase not yet read: first read every contract the code must satisfy (schemas, registries, every test and caller) as it really is in the repo (Kalli, session 13).
- Three of this session's five round trips were preventable by that rule; two were real data the runs had to show.
- A variable that grows partway through a block is not safe to reuse below the growth.

Still open: the four ACS runs (the key is not in this shell), the two county experiments, the push, the hand-off.

## Sprint 06, session 14 (2026-11-16): zip 2's consultation, the standard

Decided:
- D-270: the standard lives in seeds/standards/information_barriers.yml, its shape in seeds/schemas/standard.schema.yml, generic for any domain. Each barrier lists sides; a side has a kind (universal, trigger, none), a statement, a source and who declared it, and names what it judges. Barrier membership has its one home there; the registry keeps only role. The pairing table (P-2) is its own seed.
- D-271: P-1, row by row; P-1 and P-5 closed. Language trigger: the DOJ 2002 safe harbor as rewildingcities' own line (rescinded 2025-03-21, the Department's Federal Register notice 2025-06366), per C16001 group, residents 5 and over: translate at 1,000, or at 5% with 50 or more; written notice of free interpretation at 5% under 50 (the guidance's paragraph (b), as quoted in DOL's 2003 Federal Register guidance, 03-13125); else nothing written. Section 203 as published, its four-group limit said. Language universal (P-5): every limited-English resident, our line, UNESCO's 2003 Recommendation concerning the Promotion and Use of Multilingualism and Universal Access to Cyberspace as its principle. Digital universal: every household, the ITU and UN Envoy 2030 target that all households have Internet access; the ACS counts subscriptions, so a household with access and no subscription is in our left_out, said in the statement. FCC 100/20 terrestrial declared, acquirable until 7b. Literacy universal: every adult 16 to 74 at Level 2 or above, UIS's level for SDG 4.6.1; target 4.6 promises all youth and a substantial proportion of adults, so the line is ours. Cultural cues, paywall, outdated, where people look, trusted source: none.
- D-272: a universal side is judged once, on its left_out count against zero: below when the count less its margin is above zero, within_margin otherwise; meets is unreachable for an estimate and says so. Literacy by its credible bounds. Other indicators of the side carry judged_on. D-269's proportion of 1 never reaches a verdict.
- D-273: trigger verdicts crosses, within_margin, does_not_cross, cannot_judge, margin-aware per group, the safe harbor's tier named. A published determination's verdict is as_published. D-263 stands.
- D-274: profiles are built by a canopy command into one place_profile artifact with its own receipt listing every receipt read; never a sows run, since $loam names one artifact (D-163) and values live in many receipts. place_profile is tier public (Kalli). The profile's own allow record is decided at the publish door (zip 3), never inside the file; part 5 carries its inputs' refusals.
- D-275: loam gains views over the literacy_estimates and section203_records receipts' files, keyed by (unit_authority, unit_code), each row naming its receipt; never through place_values (D-268 stands).
- D-276: borrowed_from is a list of every coarser place a value comes from, each with its share of residents from the graph's edges; no verdict, no left_out on a borrowed value.
- D-277: an uncertainty's confidence comes from its indicator's declared uncertainty (acs_moe: 0.90), held once; a row's own confidence wins (literacy 0.95).
- D-278: left_out means people short of a universal line wherever a reader sees it; place.py's property becomes out_of_range (two lines in test_place_reading.py); graph.py's report key stays.
- D-279: cii_rent_burden, cii_no_vehicle and their cii_pub twins take role need. Only place.py's label and the carriers view read role (grepped); the hashes move, so the cousub, district and county runs and the county standings rerun, no fetch.
- D-280: part 1's population is the 2020 Census count from the block spine, what every per_1000 divides by; the households' source is read in the build before it is chosen.
- D-281: Contract 4 moves to draft 0.4 in zip 2, carrying D-258, D-263 and D-270 to D-280.
- D-282: part 4 pairs one measure only. CII's literacy is an average score; PIAAC's is a share at or below Level 1: shown side by side, never as a disagreement.

Found:
- Contract 4 in the repo was still draft 0.3, naming D-198's derive_margins step that D-258 superseded.
- loam views only indicator_values; literacy_estimates and section203_records have no reader yet.
- $loam.<type> resolves to one artifact; the values live in eleven receipts, so a profile cannot be a run's input.
- The value receipts carry no confidence column.
- Coverage: the 26 language indicators and households_without_broadband exist at all five levels; cii_broadband and limited_english_households at town and both chambers only; rent burden and vehicle access at county, town and both chambers. county_derive_values is the national county set, 6,444 rows.
- Section 203: one flag5 in the file, Nashville plantation, Chinese, values suppressed, not covered.
- Literacy's universe is adults 16 to 74 (population_16_74), not every adult.
- Receipts are named by step and output, not type: the first find for barrier values found none.

Wrong hypotheses:
- That CII's literacy and PIAAC's are one measure for part 4: an average score and a share (D-282).
- That the safe harbor is 5% or 1,000 alone: it has a 50-person tier.
- That a universal verdict reads the rate: the count reads every level and never meets D-269.
- That a profile could be a sows run.
- That a profile's allow record could sit in its own header: the gate judges the envelope that holds it.
- That the barrier values' receipts carry "barrier_values" in their names.

Lessons:
- A rule taken from a summary misses its edges: read the source's own text for every tier before declaring a line.
- An artifact cannot carry the verdict on itself; a judgment of the whole lives outside it.
- Find receipts by the type inside them, not by a guess at their names.

Closed: P-1, P-5 (D-271).
Owed before code: P-2's cited research, if part 6 is to be filled; part 6 may ship present but empty, its reason said (Kalli's cut).

## Sprint 06, session 15 (2026-11-16): zips 2 and 2b built, the standard

Decided:
- D-283: tiers, Kalli's: public for public_school, health_center_site, school_geocode_release, health_center_sites_snapshot, section203_public_use_file, section203_records, piaac_skills_map_workbook and literacy_estimates (U.S. government works), and for located_in_edges (it adds no limit of its own; each layer's points bind through lineage, D-101). news_outlet, the clerk types and the outlet working types stay undeclared: SRC-4 and E911-1 decide them.
- D-284: the gate first. Every receipt a value would come from is judged at public before its value enters a profile; a withheld receipt's values never enter, its refusal does (rules 7 and 8), and the receipt's inputs are exactly the receipts whose values entered. One home for judging a plot's receipts: canopy.expose.check.judge_receipts, which read_exposure now calls.
- D-285: part 6 ships present and empty until the pairing table (P-2) is written (Kalli's cut).
- D-286: part 1's households are the ACS's, the denominator of households_without_broadband; the values file does not carry that count's margin, and the profile says so.
- D-287: a small sample does not stop a verdict: the margin decides, and the reliability note travels beside the value. Contract 4 0.3 listed it as a cannot_judge reason; 0.4 does not.
- D-288: part 4 takes a difference when two values' units match, or both are percents of the one measure; any other pair is shown with no difference and says why.
- D-289: a trigger is judged over every value its margins allow (canopy/wonder/verdicts.tiers_within): the margins' ends and every tier number between them, in every combination. One tier reachable, crosses or does_not_cross; several, within_margin naming each.
- D-290: Maine's town and county boundaries take maine_geolibrary_public (seeds/licenses): 5 M.R.S.A. section 2005 forbids copyright or licensing restrictions on data made available through the GeoLibrary, section 2004 removes liability, and the GeoLibrary's layer metadata asks that the source be credited, so attribution is required. Section 1995 (licensing agreements) sits in the Office of GIS subchapter and reads as its services to state agencies: Kalli's reading; the GeoLibrary Board is the authority to ask. Read 2026-11-16 at legislature.maine.gov.
- D-291: count_located's receipt names the notes its rows carry (row_context_notes, context_notes), so rule 9 binds exactly those.
- D-292: every level of the graph is profiled, Contract 4's six first, then any other (Maine's 923 MEGIS civil divisions), each saying in place.level_note that it is groundwork for later analyses (Kalli).
- D-293: the places and edges receipts are inputs of every profile, whatever the gate says of them; when withheld, the command says the whole file cannot leave.

Built (b3426b1, 27 files): seeds/schemas/standard.schema.yml and seeds/standards/information_barriers.yml (8 barriers, 44 measures); canopy/standards.py (shape by schema, then names: every barrier indicator one home); canopy/wonder/verdicts.py (every rule as a function of numbers); canopy/wonder/profile.py and the profile command; loam's literacy_estimates and section203_records views; the ACS confidence held once in the registry; out_of_range (D-278); the role change (D-279); the tiers; the GeoLibrary term; Contract 4 draft 0.4. Tests: 1,221 passed at zip 2; zip 2b's run passed, its count not recorded.

Found:
- The first full build profiled 1,663 places over several minutes and printed nothing until the end; it was read as a hang.
- Only 21 of 58 receipts could leave: graph_places and graph_edges were refused under rule 10, since governance_unit_town and governance_unit_county were terms_unknown, so no profile could leave at all. After D-290 and D-291 and the five count reruns, 36 of 58.
- Every carrier count failed rule 9: count_located wrote each tribal row's note but never listed them in the receipt.
- The profile read places and edges for every name, contents list, overlap and borrowed share without listing them as inputs.
- The section 203 records file holds the whole nation, 38,962 rows; about 74 per Maine town.
- Profiled now: 1,663 places in 303s (state, counties and towns in 27s; each district, tribal area and MEGIS division about 0.24s, nearly all in read_place). Verdicts: 351 below, 2,081 within_margin, 10 crosses, 7,607 does_not_cross, 516 as_published, 16,630 no_threshold, 17,706 cannot_judge. Withheld: the outlet counts and the clerk counts only.
- Aroostook's own literacy and its tribal note travel; its population read null until the counts could leave.

Wrong hypotheses:
- That the full build hung: it was slow and silent.
- That place_values, a view, made each place's values read slow: the read showed 0.0s.
- That a trigger's two margin ends bound its tiers: 950 plus or minus 100 at a 1% share reached written notice, which needs 5% (D-289).
- That only the outlets would be withheld: the graph itself was, by one license.
- That profiling Contract 4's levels needed no filter: the MEGIS divisions came along, which Kalli then chose to keep (D-292).

Lessons:
- A long command prints its progress, or its silence will be read as a hang.
- A bound taken from the ends of a box holds only when every value between lands in a tier the ends reach; check the box's own corners and the thresholds inside it.
- What a file's structure rests on is lineage too: an input is anything the file holds, names and shares included.
- Read the law's own text for a license, and name the reading as a reading.

Closed: SRC terms for the boundaries (D-290); the rule 9 gap on counts (D-291).
Opened: LIC-2, the boundary layers' own item metadata, unread. GAPS-1, part 5's gaps in the method authors' own words from readiness and possibility. EDGE-NOTE-1, located_in_edges receipts do not name their rows' notes, so the libraries', schools' and health centers' edges fail rule 9 (the carriers map, zip 3). NOTHR-1, a no_threshold verdict says "this value is shown" when the entry is empty or withheld. PROF-1, read_place loads the registry three times a call, most of a build's time.
Still open: zip 3, the door.

## Sprint 06, session 16 (2026-11-16): zip 3a, counts go public

Decided:
- D-294: Cision's two exports take their own type, commercial_outlet_listing, excluded: a commercial database's terms do not permit redistribution of what it holds. maine_outlet_carriers stacks only the three lists, named in stack_outlet_sources' new use parameter; Cision stays declared in the shared crosswalk and is left out by name, never by a dropped input. Choices: database_alone none, town_fallback none (the office addresses were Cision's). Reviews resting on Cision records removed: 10 office reads, the Rumford Falls Times town review, Cision's records in two merges; Maine Morning Star's office read became a town review (state). Kalli's cut.
- D-295: outlet_listing (Easton, Local News Catalyst, the ecosystem file) is aggregate-only.
- D-296: indicator_values and place_profile declare aggregates: true, so an aggregate-only ancestor may leave through them as values per place (rule 5). No type had declared it, so rule 5's way out had been unreachable.
- D-297: news_outlet, outlet_stack and outlet_groups are aggregate-only; municipal_clerk_office, municipal_clerk_list and address_point_release are public. Named outlets wait for OUTCONF-1 and the lists' makers' word: every outlet type in the lineage binds, so naming outlets moves the lists' tiers and terms too, never news_outlet's alone. The 911 release is never a publish target; only its matched points leave.
- D-298: the 911 file takes maine_geolibrary_public, by D-290's reading of 5 M.R.S.A. section 2005: it was made available through the GeoLibrary. The courtesy ask goes in the wrap-up (E911-1).
- D-299: two terms from Feist v. Rural Telephone (499 U.S. 340, 1991), Kalli's readings, not a lawyer's. factual_directory: a list of every member in an obvious order holds no original selection (the Secretary of State's clerk list), public. factual_compilation_counts: a list whose makers chose its members (Easton's, Local News Catalyst's), counts only, held by requires_tier: aggregate-only, which rule 10 now enforces against the dataset's own type and the loader checks is a tier.
- D-300: the Maine Media Ecosystem file is the project's own work, project_own_work, credited to the project; to confirm with Dr. Mittal in the wrap-up.

Built (zip 3a, 16 files): the tiers (seeds/schemas/domains/information.yml, semantic_types.yml); three terms (seeds/licenses/licenses.yml); requires_tier in rule 10 (canopy/expose/gate.py) and at load (records.py); the manifest's types and terms; use in stack_outlet_sources and its registry entry (Cision's inputs optional, commercial_outlet_listing); maine_outlet_carriers' choices and inputs; the reviews; tests/test_tiers_and_terms.py (the real gate on the real seeds) and new tests in test_gate, test_outlet_sources and the outlet and clerk preparation tests. 1,247 passed. Two review fixes after runs, below.

Found:
- The stack refused any declared source with no input, so leaving Cision out meant naming what a run uses.
- Without Cision: 90 outlets placed (was 97), 12 listed, 10 no_town_given and 2 ceased (was 405, 326 of them records not counted for their medium).
- The County's merge still needs editions: the ecosystem file lists both The County and the Star Herald (merge 2 refused without it; restored).
- The Castine Patriot's two list records join on their own name key now (merge 3 refused as no longer needed; removed). The Press Herald and Boothbay merges still hold.
- The gate allows the outlet counts, the clerk counts, the clerk office points and the profile; the profile withholds nothing at public (session 15 withheld the outlet and clerk counts).
- "cision" in the counts receipt sits only in the declaration passed as params and in the stack's own warning that it left Cision out by use.
- Two manifest provenance mappings held unquoted commas, read as extra keys; quoted.
- The information types' header still called tiers advisory until a gate exists; corrected.

Wrong hypotheses:
- That Cision alone made The County's merge need editions.
- That named outlets would be one tier change.
- That a read after a failed run shows the new run: it showed the last good run, twice.

Lessons:
- A read reports whatever ran last: check the receipt's time against the run before reading its numbers.
- Keep a merge whose need is in doubt: no longer needed, it refuses loudly; removed early, a double count could pass in silence.

Closed: Tiers (D-297); E911-1 for publishing (D-298), the courtesy ask kept for the wrap-up.
Narrowed: SRC-4, to named outlets (D-299, D-300); OUTCONF-1, Cision's reads gone.
Opened: WATERFRONT-1, The Working Waterfront's reading (Rockland, the Island Institute's) waits for a town review naming Rockland's code; until then it is listed no_town_given.
Still open: zip 3b, the door (Sprint 08), with CARRY-1 and EDGE-NOTE-1.

## Sprint 07, session 1: zip 7a, the stack

- D-301: Sprint 07 runs on Kalli's own AWS account, applied fresh, and is handed to the library as code (MP-70 as amended in Sprint 06's session 16); state local on her machine. The account is a new-experience project, so its region is the project's assigned one, us-east-2, set in her local kalli.auto.tfvars; the committed default stays us-east-1 for the handover. The account's id stays out of the repo.
- D-302: O-1 closed. CloudFront with origin access control in front of a private bucket; Block Public Access declared on in code, not left to S3's defaults; the bucket policy lets the distribution read harvests/* alone.
- D-303: O-2 closed. GeoParquet canonical, GeoJSON display copies, GeoPackage only on request.
- D-304: O-3 closed. Referenced GeoJSON layers for December; a Parquet feature layer is a recorded read after.
- D-305: The canonical write's tests reach S3 through an injected fake client, no moto; boto3 joins environment.yml (zip 7b). Old harvests are regenerated through the canonical write, never moved.
- D-306: One stack, canopy/terraform/ (infrastructure D-3): staging/ moved up and renamed canonical, environment production; canopy/terraform/storage.tf (the per-city cache bucket) deleted; the December 2025 terraform/ stack (AWS Academy's LabRole, force_destroy true, versioning off) recorded here as an experiment and removed. Git history keeps all three.
- D-307: Noncurrent versions are kept. Only a current pointer is ever overwritten, so expiring noncurrent versions would erase the history of pointer moves; multipart cleanup stays.
- D-308: The canonical write assumes the role rewilding-canonical-writer through an AWS profile: put, get and list under harvests/, every delete denied, no access key. The deployer is an IAM user with AdministratorAccess on Kalli's account, its key retired after delivery (DEPLOY-1).
- D-309: The bucket policy is the overwrite lock, for every principal: a put to harvests/*/versions/* without If-None-Match is refused, and a put to harvests/*/current without If-None-Match or If-Match is refused. Copies into harvests/ are refused with it; nothing copies.
- D-310: CORS for any origin, reads only (GET, HEAD, OPTIONS), range headers exposed for DuckDB; S3 answers preflights, CloudFront's response headers policy sets the origin header on every response. Versions cache long; current is never cached.
- D-311: create_budget switches the budget. Kalli's account keeps its console budget (false); the handover sets true with an alert address. Where a budget is made, it is applied first. The email check is a precondition on the budget, so a budget never made is never checked.

Built (zip 7a, 12 files): canopy/terraform/ (versions, providers, variables, bucket, access_logging, budget, cloudfront, writer, outputs, the provider lock, README with the handover addendum); Contract 2 at draft 0.2. Two inline fixes after the first plan: variables.tf and budget.tf (the precondition); the README after the apply, delivered as a file. Applied on Kalli's account: 20 resources, 3 in a first apply refused partway, 17 in the second. Committed as 7dcd3f0 (the stack) and a000d62 (the old stacks' removal; its message names this block, which lands in the commit after it).

Found:
- The account is a member of an organization AWS made through its new sign-up experience, owned by Kalli's own management login. Two service control policies bind it: one keeps it in the US East regions (us-west-1 and us-west-2 refused a log group), the other refused S3 CreateBucket and KMS TagResource in us-east-1. In us-east-2 every resource was made.
- Global resources (the writer role, the origin access control, the response headers policy) were made in us-east-1's refused apply; regional ones were refused. The second apply made the other 17 and left those three as they were.
- conda stored TF_VAR_create_budget (its name is in the env's list) and never exported it on activate; the setting moved to kalli.auto.tfvars, ignored by **/*.tfvars.
- A resource that fails its precondition drops out of the plan's count: 20 to add was the stack without the budget, not a budget turned off.
- CloudFront's distribution took about three minutes.
- The acceptance reads passed as the writer: put under harvests/; read through CloudFront, 200 with access-control-allow-origin *; a version put without If-None-Match refused by the bucket policy; with it, made once and refused the second time (PreconditionFailed); delete refused by the role's own policy. Two small files stay under harvests/_read/. The re-plan read No changes.

Wrong hypotheses:
- That Kalli's account was a standalone account.
- That 20 to add meant create_budget had reached the plan as false.
- That the variable validation misjudged create_budget: the variable had never loaded.
- That a project's assigned region is the only region open: us-east-1 allowed a log group and refused a bucket.

Lessons:
- An explicit deny in a service control policy names its policy and organization: ask whose organization first (aws organizations describe-organization works from a member account).
- A region is read with a free write that cleans up after itself, one region at a time, before planning against it.
- Read the screen as well as the file: a plan's error goes to the screen, its plan to the file.
- A file holding its own code fence is delivered as a download, never pasted from chat: the chat's fence closes at the inner one and the heredoc arrives cut.
- A commit's message is read against its stat before pushing: a000d62 names a ledger block it does not hold.

Closed: O-1, O-2, O-3 (D-302 to D-304); Sprint 07's audit rows for the write identity, one stack, lifecycle and public reach.
Opened: DEPLOY-1, retire the deployer IAM user's access key after delivery, and deploy from expiring logins after.
Still open: zip 7b, the canonical write (canopy/aws/s3.py and its four tests), after rereading canopy/envelope.py and canopy/expose/check.py.

## Sprint 07, session 2: zip 7b, the canonical write

- D-312: The canonical write takes a receipt in the plot's own .envelopes, by its artifact name, and never a manifest dataset. Its data file is resolved against the garden's root (receipts write paths through preparations/..) and must sit inside the plot's own .data, travelling alone: a receipt naming secondary files is refused until Contract 2 says how they travel.
- D-313: The gate's allow record lives beside the receipt, never inside it (D-274 stands). The receipt is uploaded byte for byte as envelope.json and the envelope schema is unchanged.
- D-314: Formats (A3, Kalli's choice): Parquet is written as it is; JSON is a document and written as it is (the place profile); GeoJSON is converted by the canonical write to GeoParquet with geopandas, no index column, converted twice and refused if the two files differ. The change is a format_changed record appended to the allow record's publication steps, by the canonical write, naming the libraries and their versions, the crs, the feature count and the source file's sha256 (Contract 1 section 8 amended: an exit records its own changes, the gate or the canonical write). CSV, GeoPackage, rasters and Arrow are refused by name. A library upgrade can make new bytes from the same content, and so a new version; Contract 2 says so. A1, the receipt's own format, was the fallback and was not chosen.
- D-315: The target is canonical at public, because CloudFront makes everything under harvests/ readable by anyone. A lineage holding a custom tier is refused by the writer even when the gate allows it, until O-6 decides how a version is withdrawn.
- D-316: python -m canopy.cli canonical <plot> <artifact> is a dry run by default and touches no AWS; --all is a dry run only, reads every receipt through any error, and exits 1 if one could not be judged; --write takes one artifact at a time and needs --by and --reason. The bucket and the CloudFront domain come from REWILDING_CANONICAL_BUCKET and REWILDING_CANONICAL_DOMAIN in the env (the bucket's name holds the account id, D-301), the profile from REWILDING_CANONICAL_PROFILE, rewilding-writer when unset.
- D-317: A version is whole when its data file exists, and the data file is put last, each version file with If-None-Match, so a write cut off partway finishes on the next try. The pointer is created with If-None-Match and moved with If-Match; a pointer moved by another writer meanwhile is left as they set it, said. A move back to an existing version is a revert, with its reason. Versions are cached a year, immutable; current is no-cache.
- D-318: A harvest's name is its receipt's artifact name. A version's URL is a citation forever, so a rename makes a new harvest and never moves an old one. map.py's map_<indicator>__<layer> files are not receipts and are not written.
- D-319: canopy/aws/batch.py and docker-compose.yml removed, both 0 bytes: the NYC Batch pilot is after delivery (E5's quota question unanswered) and nothing composes before the API image split. Git history keeps their place.
- D-320: The allow record is versioned inside its version: versions/<sha256>/allow/<allow-sha256>.json, named by the sha256 of its content less its times (the gate's checked_at, the write's own steps' at, prepared_at) and less which receipt was read. The same data judged the same way writes nothing, not even a refused put; the same data with a changed allow record (a note's text settled on the nations' terms, TRIBE-7, P-8; a license read again) writes that record alone and moves current, which names sha256, allow, previous and previous_allow. Old records stay readable as history. Found before the first write, so nothing migrates.

Built (zip 7b, then zip7b2 and zip7b3 after the dry runs): canopy/aws/s3.py, the canonical write; canopy/cli/canonical.py, registered in canopy/cli/__init__.py; tests/test_canonical_write.py, 42 tests through an injected fake client that keeps the bucket's overwrite lock and fails on any removal; boto3>=1.36 in environment.yml (1.43.67 installed); Contract 1 at 0.6, Contract 2 at 0.3. Removed: canopy/aws/batch.py, docker-compose.yml. Tests: 1,289 passed.

Written: the first canonical object. clerk_offices_points_points, version 0b91cb0caae7, allow record 33ce1ddb61dc, 392 offices as GeoParquet, moved by Kalli A. Hale on 2026-11-17 01:02 UTC. Read back: curl of current through CloudFront showed the pointer; DuckDB's read_parquet over the CloudFront URL counted 392.

Found:
- Maine holds 58 receipts: 28 Parquet, 21 GeoJSON, 8 CSV, 1 JSON. A writer that refused all but Parquet would have refused the clerk points, every carrier's points, every outline and the profile.
- The dry run: 37 of 58 may leave, 21 withheld, 0 that could not be judged. Withheld: rule 5, the outlet listings, groups and stacks (aggregate-only); rule 9, all five carriers' located_in_edges (EDGE-NOTE-1); rule 10, the old outlets_* receipts, which still carry Cision under terms_unknown from before D-294 (the carriers_* stack is clean of it); rule 4, eight receipts with no lineage (dissolve_counties_dissolved and the repair_*, units_* and validate_* chain RECEIPT-1 names); by format, literacy and section 203's CSVs. Every outline, carrier count and carrier point, every indicator table and the profile may leave.
- GDAL's GeoJSON reader refuses one object past its size limit, and outline_state_outline, Maine whole in one feature, is past it. OGR_GEOJSON_MAX_OBJ_SIZE 0 lifts it for the process; it bounds the reader's memory, not the bytes written.
- Hashes held across separate processes, not only within one: the senate outline, the clerk points and the outlet counts named the same sha256 in two dry runs.
- An allow record carries what can change while data does not (note texts, license terms, tiers). With identity on data alone, the first write would have frozen the DRAFT tribal notes at a citable URL forever.
- boto3 was already in the env; mamba installed nothing.

Wrong hypotheses:
- That the writer could refuse every non-Parquet receipt and stay useful (fork A's first lean).
- That where a traceback sits in a saved file is where the run died: stdout to a file is buffered and stderr is not, so the traceback landed after receipt 19 while the run died on receipt 37.
- That tail -1 of a saved run shows how it ended: it showed the last line printed before the crash.
- That an allow record could be written once per version.
- That a rerun with the same allow record would send nothing while it still tried the put: a refused put is still a request.

Lessons:
- Read the formats a writer will meet before deciding what it refuses.
- A command whose output is saved prints line by line, so the file's order is the true order.
- A batch read reports each item's surprise and goes on; one error never hides the rest.
- An identity names only what cannot change without the thing changing; whatever can change on its own gets its own identity.
- A diagram in a command's box gets pasted: diagrams that are not commands are drawn so they cannot run.
- Run the whole suite before anything permanent, not only the new file's tests.

Closed: Sprint 07's audit rows for the canonical write, the four tests, DuckDB through CloudFront and batch.py; D-274's question of where the profile's allow record lives (beside it, D-313, D-320).
Opened: O-6, how a version is withdrawn, on the terms of the people the data describes (Contract 2; after delivery). CANON-1, the old outlets_* receipts and the eight lineage-less receipts sit in .data and .envelopes, withheld; rerun or remove them after delivery. CLIDOC-1, canopy/cli/__init__.py's docstring lists neither map nor acquire.
Still open: Sprint 08, the publish door, with display copies (Contract 2 section 4), reference layers by URL (D-304), CARRY-1 and EDGE-NOTE-1. DEPLOY-1 after delivery. Reading by URL in Map Viewer and Experience Builder, Kalli as the ArcGIS admin.

## Sprint 07, session 2 (reopened): zip 7c, display copies and the first web map

Reopened: d67ccb3 called Sprint 07 closed against state.md's audit table. The Master Plan tab's done-when, "a Maine layer shows in a web map using no AGOL feature storage, and DuckDB queries its canonical file in S3", was met only in its DuckDB half, and its build list held display copies and reading by URL. Kalli chose to reopen and finish over moving the web-map half to Sprint 08.

- D-321: Display copies are drawn by python -m canopy.cli canonical <plot> <artifact> --display from the current version's own bytes, read back from the bucket and checked against their sha256, never a local copy; written under versions/<sha256>/display/ by the writer role, a dry run unless --write, no --by or --reason since no pointer moves. Contract 2 section 6 amended: the canonical command writes display copies, the door references them.
- D-322: A copy is named web for points and web_<tolerance>m for polygons, so another tolerance is another copy. The envelope is put first and the GeoJSON last, each with If-None-Match; the same bytes write nothing; other bytes under a standing name are refused, never replaced.
- D-323: A copy's envelope inherits the version's metadata (lineage, notes, row notes) less what it redraws (total_area_m2, geometry_type_native), its provenance under the branch version and its warnings; records derived_from, the allow record current when drawn, display_of and display_name; adds its own entry, make_display_copy 1.0.0, whose publication list holds every change. It is checked against the envelope schema and judged by the gate at canonical, public; a custom tier is refused. The GeoJSON carries no note text: a note settled later moves the allow record, not the copy.
- D-324: Polygons are simplified as one coverage with shapely's coverage_simplify, in EPSG:26919, 25 m by default, so neighbours keep one shared edge; a coverage invalid before simplifying, or a geometry left empty after, is refused. Points simplify nothing, recorded as simplified with count 0. Coordinates are rounded to six decimal places. The copy is GeoJSON (RFC 7946) in EPSG:4326, its format_changed record naming the transformation pyproj chose; dates and times are written as ISO 8601 text, a missing one as null, each such field named; every property is kept.
- D-325: In ArcGIS Online a display copy is referenced through Map Viewer's Add layer from URL and saved in a web map, so the only item is the web map and the layer is read from CloudFront each time. The Content route (New item from a URL) imports a GeoJSON as a copy and offers a hosted feature layer, and is not used. The web map item's description carries the layer's account and its notes until Sprint 08's door writes items.

Built (zip 7c, then zip7c2): canopy/aws/display.py; prepare_display and write_display in canopy/aws/s3.py; --display and --tolerance in canopy/cli/canonical.py; tests/test_display_copy.py, 24 tests, five drawing real geometry; Contract 2 section 4 rewritten and section 6 amended. Tests: 1,313 passed.

Written: outline_towns_outline, version eda591d0d3ba, allow record a19b45afae02, 528 towns. The clerk offices' display copy web under version 0b91cb0caae7, 392 points, 265,905 bytes, served by CloudFront as application/geo+json, cached a year, immutable. Drawn: the first web map, Kalli's, in ArcGIS Online's Map Viewer, from that URL.

Found:
- The clerk points carry review_read_on, a date GeoJSON cannot type; geopandas' to_json raised on its Timestamp.
- The towns outline is not a valid coverage: Gray (2300528870) and Windham (2300586025) disagree along about 75 m near 43.8457 N, 70.3746 W, neither overlapping the other, each valid alone. Hypothesis, unconfirmed: Little Sebago Lake's shore after perennial water was clipped (D-142).
- Maine's town outlines are NAD83 (EPSG:4269); the display copy reprojects and names the operation.
- A curl -sI answer carries S3's md5 as its etag, never the version's sha256 (HASH-2), and names no URL.

Wrong hypotheses:
- That Sprint 07 was closed at zip 7b: judged against the audit table, not the tab's done-when.
- That the display path would refuse rather than crash on a drawing error: zip7b2's fix for --all had not been carried into it.
- That ArcGIS Online's Content route could reference a GeoJSON by URL without importing it.

Lessons:
- A sprint closes against its own tab's done-when, read from the tab.
- A new path inherits the old fixes, or repeats the old crash.
- A guard that refuses is the build working: the coverage check kept a crack off the first map of Maine's towns.

Closed: Sprint 07, its done-when met; the Master Plan tab's display-copy and reading-by-URL build items, Experience Builder excepted.
Opened: COVER-1, the Gray and Windham edge: repair in build_place_outlines, then a new version of the towns and their display copy; before Sprint 08's choropleths.
Still open: Sprint 08, the publish door; Experience Builder by URL; O-6, DEPLOY-1, CANON-1, CLIDOC-1 after delivery.

## Sprint 08, session 1 (2026-11-17): the door's consultation, zip 8a

The publish route assignment was looked for and not found: the ledger holds only F4 (line 376) and EXP-1, and the Master Plan cites the assignment without its text. Kalli: the repo's contracts are the record. So F1, F2, F5 and F6 are read from the Sprint 08 tab's build items, F4 from this ledger, R7, R8, R10 and R11 from the tab; F3, F7, F8, R1 to R6 and R9 are not recovered, and nothing is written in their place.

- D-326: One door, `python -m canopy.cli publish <plot> <artifact> --to <target>`, a dry run unless `--write`, which needs `--by` and `--reason`; `--to` repeats. Targets have kinds behind one interface and a registry (`canopy/expose/targets/`), mirroring the providers; the first kind is `arcgis_webmap`, and an open catalog record (DCAT or STAC) for Sprint 13's hub is the next named, so a community without an ArcGIS license still has a door. `map --publish` is retired: `map` draws locally and offline, and `--publish` names the door and exits 2, drawing nothing. The upload latch in `canopy/visuals.py` is deleted. This reverses D-96 on its own condition (the door publishes choropleths, after zip 8b) and supersedes MP-67's flag.
- D-327: A plot declares its own targets in `plots/<plot>/publish/targets.yml`: kind, portal (any https portal, ArcGIS Online or Enterprise), owner, owner_kind, folder, sharing, groups, sign_in; read loudly, an unknown field refused by name. The door alone writes `plots/<plot>/publish/published.yml`, committed: per target and artifact, the item, its layer, the display copy and URL, the `sha256` and `allow` it shows (as `current` does), the description's sha256, sharing, the gate's decision, who and why, and the previous pair. loam may read it someday and never writes it. Closes Contract 2's O-4.
- D-328: No features are updated, because none are stored. The door owns web map items and, in them, only the layer's URL and fields, the description and the credits; a person's renderer, popup, basemap and title are kept on every move. A new version moves the URL and the description; a new allow record moves the description alone, which is how a settled note reaches the map; new sharing moves the sharing. Before writing, the door reads the item: one that is gone waits for `--replace` (F2); a layer URL or description changed by hand is refused, naming it. ArcGIS has no If-Match, so the guard is read, compare, write, and a race between the read and the write is possible. A new item is recorded, unshared, before it is shared, so a share that fails leaves a record that owes the share and never a second item. At the door the gate judges the display copy's envelope at the target's sharing level, and every note it binds must read as the canonical allow record holds it, or the door refuses. Closes Contract 2's O-5.
- D-329: The door speaks ArcGIS's REST API with `requests`; no Esri package, so nothing is added to the env or the Docker image, and the same code serves any portal. Sign-in is `generateToken` for a 60-minute token, the password typed at a prompt once per portal and account and never stored, logged or committed; the door then asks `community/self` who it is and refuses before writing anything if that is not the target's owner (F4). Every item records the REST version the portal reports (F5's record, in the shape this door has). `introspect`'s `arcgis` credentials row is removed. Kalli has explicit permission to publish as RDS_NU for this project.
- D-330: Items are owned by the account a target declares, an institution's wherever one exists, so items outlive the person who made them; a target with `owner_kind: personal` is published with a warning on every run (R7). Maine's targets are owned by RDS_NU, Research & Data Services.
- D-331: Decided, built in zip 8b. A choropleth is drawn by `canonical <plot> <table> --display --join <outline>`, joining a long table's `(unit_authority, unit_code)` to the outline's `(authority, code)`, never a GEOID or a name, through one join in `canopy/choropleth.py` that `map.py` imports (LAYER-1, G-11). One wide copy per table version and outline version holds every indicator's columns, empty kept empty; its envelope inherits both chains under two branches so rule 3 binds both, records `derived_from` as a list and the join's empty and unjoined counts (F6); its name carries the outline's version. The door colours one indicator per map with a classBreaks renderer: standings in fixed national quintiles of the percentile, other values by a declared standard where one exists or in equal steps said so in the legend and the description, and no value as a hatched default symbol labelled "no value", never like zero (MP-74).
- D-332: `--adopt <item>` takes a hand-made web map into the record, with `--write` and one target: its owner must be the target's, exactly one of its layers must read this harvest, and the door moves that layer to the current version, writes the fields and the description, and keeps every other part.
- D-333: The web map follows Esri's web map specification 2.38: one GeoJSON layer per item, its id `rewilding-<artifact>`, its `url` version-pinned; `layerDefinition.fields` typed from the display copy's own values (a whole number an integer, any other number a double, everything else text at least as long as its longest value), with `__OBJECTID` declared as Map Viewer declares it; a popup titled by `name`, every field shown, attachments off; the Topographic basemap the first map holds; the initial extent from the copy's `bbox` in Web Mercator; `authoringApp` rewildingCities. The description holds the notes' texts, the sharing line ("This layer reads a public URL..."), the version, receipt, allow record and copy URLs, the lineage, the license terms, caveats and warnings and every publication step, and no time, so the same records always write the same words. Credits name every license term whose attribution is required.
- D-334: The publish route assignment's F3, F7, F8, R1 to R6 and R9 are recorded as not recovered; nothing is reconstructed in their place.

Built (zip 8a): `canopy/expose/publish.py`; `canopy/expose/targets/` (`__init__.py`, `base.py`, `arcgis_webmap.py`); `canopy/cli/publish.py`, registered in `canopy/cli/__init__.py`, whose docstring now lists map and acquire (CLIDOC-1); `canopy/cli/map.py`, `canopy/visuals.py` and `canopy/introspect.py` without the latch; `plots/maine/publish/targets.yml` with the `test` target; `tests/test_publish_door.py` (22), `tests/test_webmap_json.py` (7), `tests/test_map_stays_local.py` (5), replacing `tests/test_publish_latch.py`; Contract 1 to 0.7, Contract 2 to 0.4, Contract 4 to 0.5.

Found:
- The arcgis package was never installed in the rewilding env and no ARCGIS variables were set, so the latch never published from this laptop; its tests passed against fakes. `GIS("home")` means something only inside ArcGIS Notebooks or Pro.
- The first web map, item 5fcd410b007a49aaa279e6a2b548f507, holds one GeoJSON layer pinned to version 0b91cb0caae7, no itemId, so the web map is the only item. Map Viewer guessed its schema: review_read_on a date, rows_served and tie_candidates doubles, every text 255 long, attachments on. Read anonymously it answers 403, while its data is public: sharing hides the map, not the data.
- Map Viewer's Save did nothing because its own modules answered 404: a cached page from an earlier Map Viewer release (Calcite build of 2026-11-04). A hard reload is the fix.
- `canopy/providers/s3.py` is the ESA WorldCover fetcher, unrelated to the canonical write.
- Dry runs at public: county_standardize_standings (broadband) may leave, sha256 1b9c5a6e8d71, allow record 8112cd69219e, so CII-19 is not in its lineage; county_count_derive_values may leave, fe7922079828, f278d116b315; outline_counties_outline may leave, GeoJSON to GeoParquet, 16 features, ee88e4f41db3, 513d0d01678e. None written yet.
- The counties outline carries `authority` and `code`; long value tables carry `unit_authority` and `unit_code`; table receipts list no columns in metadata.
- `maine_geolibrary_public` requires attribution.
- Esri's REST documentation, read this session: generateToken exchanges a case-sensitive username and password for a token, over HTTPS only, 60 minutes by default; in ArcGIS Enterprise it is superseded by OAuth. addItem takes an item's JSON as text, makes the folder's owner the item's owner and leaves it private until Share Item; Update and Share are user item operations. The web map specification's GeoJSON layer references a public file and keeps the reference; a classBreaks renderer takes a field, its break infos, and a default symbol and label for what cannot be classed. community/self, a user's folders and createFolder are used as portals answer them and are checked by the first write.
- Contract 1's Open table still listed E-3 to E-5 as open (ledger line 739 noticed it and left it); Contract 4's gate row said the door decides the profile's allow record; Contract 2 offered the door "push or reference". Fixed here.
- The Sprint 08 tab cites D-67 and D-71 for what are MP-67 and MP-71 (D-93).

Wrong hypotheses:
- That the door would use Esri's arcgis package, and record its version for F5.
- That the door might own a standalone layer item beside the web map.
- That targets would be declared once, at repo level.
- That the door's gate decides exposure at the item's sharing level: exposure was decided at the canonical write.
- That Map Viewer's JSON was the shape to copy: it guessed types.
- That the publish route's P items needed a new prefix: lines 14 to 16 already say "publish route P-n".
- That a layer not hosted could not be saved in a web map.
- That a command for a flag not yet built could sit in a runnable block: `--join` was run and refused.

Lessons:
- A command that is not built yet is labelled as after its zip and never drawn as runnable.
- Read the hand-made thing before writing its shape, and keep what a person chose.
- A referenced layer is as public as its URL; an item's sharing is about finding, not reading.
- A broken button can be a stale page: read the console before the data.
- An identity a pointer moves can be mirrored by every place that shows it, and each mirror moves the same way.

Opened: OAUTH-1, an OAuth sign-in for ArcGIS Enterprise portals, the door's next piece. CATALOG-1, the open catalog target kind (DCAT or STAC), Sprint 13. NAMES-1, placed_by and review_read_by put a reviewer's name on every public clerk row: Kalli decides before handover. ADOPT-1, item 5fcd410b's owner: adopting it into `test` needs RDS_NU to own it.
Still open: zip 8b (D-331's join and colours, CARRY-1 with EDGE-NOTE-1, the two-artifact outlet layer, DEPS-1, OUT-REG-1, NOTHR-1, PROF-1), COVER-1 before town choropleths, Experience Builder by URL; O-6, DEPLOY-1, CANON-1 after delivery.

Run (zip 8a, session 1, 2026-11-17): the reads found the old latch only in the three files zip 8a replaced or removed, and no new ID in use. Tests: 34 passed for the new files, 1,332 for the suite (1,313, less the latch's 15, plus 34). The dry run judged the clerk offices may leave at private, no notes binding them, and owed a new web map reading version 0b91cb0caae7's display copy. The write signed in as RDS_NU, made item 143923c7e8174f709a87425f02c43f82 in the folder rewildingCities test, shared it private and recorded it in plots/maine/publish/published.yml. A second push was unchanged: nothing owed, no sign-in. Committed c67a67a. Kalli read the item and found it fine.

Found:
- Against nu.maps.arcgis.com, generateToken, community/self, a user's folders, createFolder, addItem and Share answered as the fake portal does. Update is not yet exercised.
- After a write the door still prints its plan ("would create a web map") above the outcome line, which says published (DOORSAY-1).
- With nothing owed the door signs in nowhere, so `unchanged` cannot see a deleted or hand-edited item (DOORCHECK-1).
- The clerk points bind no note.
- Commit 825e32e holds only the ledger and state.md: no zip command for zip 3b's reads was ever recorded.

Closed: CLIDOC-1; ADOPT-1 (the door made its own item; the hand-made map stays outside the record); F1, F2, F4, F5 and F6 in the shape this door has, F6's joined counts with D-331; R7, R8, R10 and R11; the done-when's first two parts.
Opened: DOORSAY-1, DOORCHECK-1.
Still open: zip 8b (D-331, a library target, zip 3b's list, DOORSAY-1, DOORCHECK-1 if wanted), COVER-1, Experience Builder by URL, OAUTH-1, CATALOG-1, NAMES-1; O-6, DEPLOY-1, CANON-1 after delivery.

## Sprint 08, session 2 ~ zip 8b, the door's second half (D-335 to D-347)

Built from state.md, three reads zips (reads8b, topup8b, last8b) and four dry runs. Before any write the reads found that state.md had labelled two county receipts wrongly: 1b9c5a6e8d71 is county_standardize_standings, rent burden and vehicle access; fe7922079828 is county_count_derive_values, households without broadband. Broadband's standing was standardize_standings, fd9fdf0a4a0a, a name the method's recipe gives every experiment composed from it.

| ID | One line |
| --- | --- |
| D-335 | A receipt that names its run is written only if that run declares the step and output that make its name; an orphan is refused. A test holds one receipt name per run per plot, known pairs named with reasons and refused when stale |
| D-336 | The broadband experiment's steps are broadband_derive and broadband_standardize, its harvest broadband_standardize_standings; the two old receipts move to plots/maine/.data/retired, never deleted, since loam unions every receipt left in .envelopes |
| D-337 | The canonical write never sends a manifest dataset's cached file, matched by resolved path or by file name in the plot's .data. Its first real run found two: validate_counties_checked and validate_towns_checked pass MEGIS's fetched layers through, so their data files are the sources themselves; both are refused before the gate is asked |
| D-338 | canopy/choropleth.py holds the one keyed join: (unit_authority, unit_code) to (authority, code), wide as <indicator>__<column>, every row counted by declared widths, a duplicate, a keyless place, two authorities or a clash refused. map.py imports it; a long-form table draws locally on a place outline only. Closes LAYER-1 |
| D-339 | A joined copy lives under the table's version, named <outline>_<outline sha12>_web_<n>m; derived_from the table, joined_to the outline's version, allow record, authority, level and lineage; both chains under the branches table and outline; row notes from the drawn places |
| D-340 | Markers: one point on each place's surface in EPSG:26919, nothing simplified, recorded as marked, named _markers; COVER-1 does not bind them |
| D-341 | canonical --display --local draws from the bytes a write would send, needs no AWS and can never be written; its copy sha256 must equal the bucket draw's before that is written |
| D-342 | Rule 10 reads joined_to.lineage too; nothing without joined_to is judged differently, so gate_version stays and no allow record moves. Contract 1 at 0.8 |
| D-343 | The door's choropleth: --join, --indicator, --markers; record key <table>/<outline>/<indicator>; a new version or allow record of either parent owed; notes checked against both allow records, which may not word one note differently; credits from both; a dataset the gate names that neither holds refused; a choropleth never adopted |
| D-344 | A choropleth's renderer is the door's: a standing in fixed fifths of its named reference population, higher better; counts as markers in equal steps, zero "none listed"; other values in equal steps, said so; no value hatched or crossed and labelled; a colour field with no number refused; a hand restyle put back on a move and said |
| D-345 | DOORSAY-1: plan lines read "owed: ...", true before and after a write. DOORCHECK-1: publish <plot> --check signs in, reads every recorded item, writes nothing |
| D-346 | The library target: nu.maps.arcgis.com, RDS_NU, folder press-forward, sharing organization, no groups (Kalli) |
| D-347 | Zip 8b publishes broadband's standing only; the count is written canonically with no copy until it has an honest map; rent burden and vehicle access wait; zero towns are drawn; CARRY-1 and EDGE-NOTE-1 move to Sprint 09 (no December reader); OUT-REG-1 and PROF-1 after delivery |

Closed: LAYER-1 (D-338), DOORSAY-1, DOORCHECK-1 (D-345), NOTHR-1 (no_threshold says when there is no value to show), DEPS-1 (pytest, httpx and locust in environment.yml's testing section). Contract 2 at 0.5 (sections 4a, 4b).
Opened: RUNNAMES-1 (two runs writing one receipt name, found by the test's first run: maine_counties and maine_governance_units share validate_counties_checked, repair_counties_repaired and dissolve_counties_dissolved; nyc_thermal_landscape and nyc_park_cooling_pedestrian share validate_lst_checked and crop_lst_cropped; each receipt holds whichever ran last), STEPNAME-1 (wonder composes a method's recipe step ids verbatim, so every experiment from cii_indicator_values writes standardize_standings; the step-name test holds the line until wonder prefixes them).
Wrong hypotheses: that state.md's labels matched its hashes; that a receipt matching a manifest dataset would be a false positive (a validate's receipt is its source); that renaming one experiment cured the collision (the recipe makes it); that the orphan guard made the old receipts harmless (loam still reads them); that a union of both parents' notes was right (it would carry a national table's other places' notes); that only two readers of the outline needed changing (description_of's credits made three).
Lessons: read a receipt's own indicators before trusting its label; a name that goes public is forever, so look at what makes it before the first write; every reader of a parent must learn about a second parent, and a quiet one (credits) is worse than a loud one (notes).

| D-348 | Rule 11's closed set gains joined (columns added from another table) and marked (a place drawn as one point on its surface), in the provenance schema and Contract 1 section 8: renaming them to an existing step would have recorded a false change. Found by step 8's local dry run; the sandbox tests had stubbed the schema check, so a test now holds every step display.py records to the schema's set |

| D-349 | The door reads each item back after it writes and records description_seen_sha256, the hash of what the portal stores: ArcGIS Online decodes the entities html.escape writes (&#x27; became ', read 2026-11-17), so the sent text's hash called every item hand-edited. An item written before the read-back owes "reseen": its description rebuilt from the same records must hash to what was sent and differ from the stored text only in how characters are written, and only then is the stored hash recorded; a hand edit is refused. Found by publish --check's first run (DOORCHECK-1), before any move was refused for it |

## Sprint 08, session 2 ~ zip 8b's run, and Sprint 08 closed

Run (2026-11-17): zip 8b, with zip8b2 (the passthrough finding, RUNNAMES-1), fc773e3 (D-348), 2ba91e7 (pyproj's placeholder said in words) and zip 8c (D-349). Tests 1,410, then 1,415. The broadband experiment rerun under its new step names wrote 3,222 rows with the same reference population (3,144, mean 86.2292, sd 5.7993); the old two receipts moved to plots/maine/.data/retired. `canonical maine --all`: 37 of 58 may leave. Local copies: the counties a valid coverage, 16 of 16 joined, 3,206 rows outside, sha 10e23ac0...; the towns' markers 528 of 528, 1 row outside (2300357936, Penobscot Indian Island Reservation's Aroostook code, count 0, INDIAN-1), 17 at another level, sha c8b87ff3.... Written: broadband_standardize_standings fd9fdf0a4a0a, outline_counties_outline ee88e4f41db3, county_count_derive_values fe7922079828, carriers_counts_values 33d9b4d7b9b5 (546 rows), each read back through CloudFront; both copies drawn from the bucket printed their local sha256s and were written. Published: broadband to test and library, outlet markers to test, clerk offices to library. The first `--check` found every description "changed by hand" (ArcGIS decodes &#x27;) and two items deleted in ArcGIS (143923c7, dd56fefa); zip 8c, two remakes (0c0a156a, 8bc72001) and three "reseen" writes followed. Broadband pushed a second time: unchanged at both targets. `--check`: 5 of 5 as recorded.

Sprint 08 closed against its own tab's done-when. Not done: MCF and partner targets (no portal or account given); F3, F7, F8 (D-334); a real update call (UPDATE-1).
Opened: RAMP-1, UPDATE-1, SIZE-2, MANIFEST-2, DOORSAY-2, SIGNIN-1, INDIAN-1.

## Sprint 09, session 1 ~ zip 9a, the explorer's ground (D-350 to D-359)

Built from state.md, four reads zips (reads9a to reads9d), Experience Builder's own docs, a scratch app owned by RDS_NU (read_9a, made private after), two coverage reads and the rebuilt profiles (built 2026-11-18 01:18 UTC). Every lean was read against the code it touches before it was built.

| ID | One line |
| --- | --- |
| D-350 | Experience Builder draws a door web map's referenced GeoJSON layer, and no widget can read it (the data panel says "No layer"; Esri's supported data list, 2026-11-10, names feature collections, not GeoJSON). Search reads a feature collection, and a selection reaches Text and Embed only through the Search widget's own output data source, never the searched data. So the explorer stays in Experience Builder (D-68 stands), and its places come from a feature collection the door pushes (zip 9b), which is file storage, not feature storage |
| D-351 | canopy/wonder/telling.py tells each profile as text fields for the explorer, built from the profile's structured parts and never its working text. Six levels, 740 places; MEGIS civil divisions stay out, since most share a town's name. On the real profiles: 3.2 KB a row at the median, 6.7 KB at most, 2.5 MB in all |
| D-352 | The public register lives in seeds/language/plain_language.yml (Kalli): about ninth grade (Flesch-Kincaid, each field's median place, names masked), claim words refused (truth, honest), and no working id (a ledger id, a step, a rule number, a Census table code). The door's heading is "Where the data is stored"; the range statement says sampling error makes a range wider where samples are small |
| D-353 | RAMP-1: darker always means harder access. A standing's lowest fifth is the darkest. A value is darker in the direction its indicator declares worse, recorded in a joined copy's envelope (join.directions) from the registry when the copy is drawn; a copy with no direction is refused rather than guessed. No value stays hatched, never a ramp colour |
| D-354 | owed() owes a restyle when the door's renderer differs from the one recorded, by the move's own path; the first is broadband's, which makes UPDATE-1's first real update |
| D-355 | plots/<plot>/publish/credit.yml holds the credit line, the citation (its {title}, {version} and {url} filled per item) and the data guide line; every item carries them; a missing or unknown field is refused. The data guide is Sprint 13's, so the line says it is coming |
| D-356 | COVER-1 decided: the crack is a pinch. At Gray and Windham, and House 113 and 116, two places' holes (removed water) touch one shared border point, so GEOS's coverage check refuses a shape whose every border matches (a toy reproduces it; make_valid and 1 cm precision do not help). The display copy moves only those hole vertices 0.1 m into their holes and records `opened`, a new word in rule 11's closed set; the canonical outlines keep the pinch, and the towns' version stands |
| D-357 | The standard: the CII published measures are acquirable, waiting on terms of use (CII-19), since no receipt in the plot holds them; Cision leaves the outlet sources (D-294), and the last post, which only Cision recorded, needs our own model |
| D-358 | A note may carry status: draft. The four Wabanaki drafts are marked, and the telling writes "Draft wording" before them (TRIBE-7). tribal_representation_legislature is added as a draft: four nonvoting House seats from the 133rd (LD 785, P.L. 2025, c. 705); which nations send representatives as of March 2026, from Maine Public |
| D-359 | The explorer target is public, in the folder rewildingCities explorer, owned by RDS_NU (Kalli); test and library are unchanged |

Closed: COVER-1 (D-356), when its copies are drawn.
Corrected: state.md said split towns need EDGE-NOTE-1; their shares are on the overlaps edges every profile carries.
Opened: none. RAMP-1 and UPDATE-1 close when the restyle runs and --check reads it.
Wrong hypotheses: that the towns' crack was a sliver of missing land; that the dissolve ran in s2; that Experience Builder could not let a search steer an Embed (the widgets listened to the wrong data source); that voice.py spoke for places; that profiles carried refusals per place (none does: what is withheld belongs to the plot).
Lessons: a test with a noisy setup is not a test (an empty URL box and a page that may refuse framing); read the real output as its reader would (D-271 appeared 18,293 times in public-bound text); a contract's line can be reversed for a reason, but out loud.

| D-360 | The credit line and the suggested citation name Northeastern University Library, whose project account owns every item (Kalli) |

## Sprint 09, session 1 ~ zip 9a's run

Profiles rebuilt on the fixed standard (1,663 places, 303.6 s, no input withheld at public). Every write was dry-run first; every bucket draw printed the local draw's sha256 before it was written.

| What | Result |
| --- | --- |
| UPDATE-1 | broadband's test item (8bc72001) restyled by the door's first real update; --check read 3 of 3 test items as recorded. ArcGIS stores a renderer exactly as sent, unlike a description (D-349) |
| RAMP-1 | the library item (2ebb4f3e) restyled; --check read 2 of 2 library items as recorded. The south coast is now light and the far north and Washington County dark |
| COVER-1 | the towns' copy written (4a33d5a173f3, 9.5 MB), opened at 2 places; the towns' version eda591d0d3ba unchanged |
| Outlines written | House 146e0ca3ac11 (151), Senate c603add2e7f6 (35), Census tribal areas 57e9ac56a143 (8); their copies ed297340651a (opened at 4 places), 93700774267d (2), 6250b7647584 (none) |
| Profiles written | place_profile_profiles 824e79d23b1d, allow record cfeaf7315c54, JSON as built |

Closed: UPDATE-1, RAMP-1, COVER-1.
Seen again: SIGNIN-1. A mistyped password at --check refused the item it was asked for and moved on, so two items read refused for a typo; the door should ask again for the same item.

## Sprint 09, sessions 2 and 3 (2026-11-17 to 18): the forks settled, the places as one web map

Repo at 75595fd, clean, at session 3's start. No product code changed in either session; this hand-off commits state.md, this block and the rehearsal scripts (tests/rehearsals/sprint-09/).

### Reads

- Session 2 (reads_9b, 74 files; canonical maine --all; three receipt reads). The 21 receipts that may not leave: rule 5 outlet types (carriers_outlets, carriers_groups, carriers_stack); rule 9 tribal edges (five located_in_edges, EDGE-NOTE-1); rules 5 and 10 on the stale outlets_* (3); rule 4, no lineage (6, where state.md said eight); and four refused by the canonical write, not the gate: literacy and Section 203 as CSV, validate_counties and validate_towns as fetched sources (D-337). The last four reach the public another way. Once the stale nine are set aside, two kinds of data are kept from the public: named news outlets with their source lists, and the links between points and places.
- Session 2: the profile's receipts_withheld and structure_withheld are empty; outline_state_outline (c15851b5bb9b) may leave and was never written, and GJSON-1 does not bind the canonical path; no values table is in the bucket; a target has one kind, read in 3 places in the door and 7 in the tests; a canonical refusal record cannot pass today's gate as an artifact (rules 4 and 10); our measures fill two of CII's five pillars.
- Session 3 (reads_9c, 14 files; reads_9d, 4): arcgis_webmap.py already projects to Web Mercator (_mercator, WEB_MERCATOR, extent_of); the kind is built around one layer read by URL (build, moved's operationalLayers[0], layer_url, adoptable_layer); fields are typed from their own values, strings max(256, longest); profiles carry no geometry, and display.py's _markers puts a point on each place's own surface; the door reads versions through CloudFront with no AWS credentials. No rehearse_places.py exists anywhere on Kalli's machine: it sat in _sprint06/, which is deleted at a session's end. The ledger names no source for test_telling.py's ITEM_BYTES = 4,000,000 (LIMIT-1).

### Rehearsals

- Session 2: a Feature Collection item of the towns' told rows, 1,684,160 bytes sent and 1,651,605 stored, parsed identical. Search, Text (from Search's output) and Table worked; the Map widget takes only web maps; Map Viewer saved a web map of it (5dcd073073f24f3398cb2a5514e22517) with empty operationalLayers. Both items were found public though made private.
- Session 3: rehearse_places_webmap.py tells the profile's current version (824e79d23b1d) and places each row on its level's current outline (counties ee88e4f41db3, Senate c603add2e7f6, House 146e0ca3ac11, towns eda591d0d3ba, tribal 57e9ac56a143), each checked against its sha256. Dry run: 16, 35, 151, 528 and 8 placed, as predicted; the state (no canonical outline) and 2300357936 (INDIAN-1) left out and named; 923 MEGIS divisions not shown; longest field a Senate district's shares, 3,039 characters (SHARES-1); 2,351,368 bytes, canonical sha256 f640fc4e8897.
- Session 3: sent private to rewildingCities test as 000c5dcf102f4b878562a0494b6ee7fa. Stored 2,351,336 bytes, 5 of 5 layers, every count back; ArcGIS added typeKeywords (ArcGIS Online, Explorer Web Map, Map, Online Map, Web Map) and the extent. diff_places_webmap.py rebuilt the map to f640fc4e8897 and found 16 differences, all whole coordinates sent as N.0 and stored as N: two characters each, the whole 32 bytes. A town and a tribal area share one point (STACK-1).
- Session 3, by hand in read_9a: a Map widget on the web map works, and a Search choice moves the map, Text and Table (Kalli). `--check` after R2: private, stored map unchanged (b53a56044938), so Experience Builder's work did not change sharing.

### Decided

- D-361. The places live inside one door web map, one feature collection layer per level; no separate places item is made. Search, the profile panel and the Map widget read that one map, so the places have one home. Rests on session 3's rehearsal (Kalli).
- D-362. A places map's canonical form writes every whole float as an integer; the door sends that form, records its hash and checks the stored map against it. ArcGIS stores 5615270.0 as 5615270, so a hash of anything else reports a hand edit that never happened (D-349's lesson, for numbers).
- D-363. Fork 1, the withheld table (Kalli: go with the intuition, revised). A canonical refusal record of the gate's refusals only, never the canonical write's, whose content reaches the public another way. It lives under harvests/ (the only prefix the writer and CloudFront reach) with a name no receipt can take (D-318), versioned by its content like the allow record. `--check` reruns the judgment and says stale when it no longer matches. The public table's rows are kinds of data, each with whose rule holds it back and what would change it; no reason names a withheld outlet. Before the record is written, the nine stale receipts are moved to .data/retired, never deleted, unless the exact-name read finds a live reader, whose receipt is rerun to earn its lineage instead. Predicted after: 8 gate refusals, 4 write refusals.
- D-364. Fork 2, targets (Kalli). A target names a portal account; each recorded entry names its own kind, and an entry with none is refused, never defaulted; the five recorded entries get theirs written, with a test that every entry names a known kind. A feature collection layer moves by its collections' hash, never a URL. The description names the profile version's sha256 and the told copy's canonical hash. The door's opening line ("never uploads features") is rewritten: the places are copied into the map's JSON as file storage, with no hosted feature layer, and Contract 4 says so.
- D-365. Fork 3, the lens maps (Kalli). Five lens maps always, since an app holds item ids and a map made later means rewiring by hand; an empty pillar holds the orientation outlines and says plainly that no measure is drawn. "Measured, told in each place's description, not yet drawn on a map" (literacy, a CSV) is told apart from "not yet measured", and both come from one home shared with the profile's list. Every value drawn declares a direction (D-353). Values only, never standings. The crosswalk seed is national; whether one indicator may sit in two pillars is read first. Every values table is written canonically and joined before any lens.
- D-366. Fork 4, the app (Kalli). `publish --adopt-app` records the hand-built app and refuses one not owned by RDS_NU, outside the explorer folder, or read_9a's id. `--check` reads its published config/config.json and says so, since an unpublished edit does not show there, and compares every recorded item's and the app's sharing with its target's.

### Opened

- EXPLORE-1. Exploring by the map (Kalli): two ways in, one selection. R5 by hand: Text wired to the places layer's selected features, moved by a map click and by a Search choice. Points let a reader click only a dot, so the intuition is polygons inside the map, if they fit; a `--polygons` dry run reports bytes per level at 100, 250 and 500 m and any place emptied.
- LIMIT-1. ITEM_BYTES = 4,000,000 has no named source; 2,351,336 bytes is the largest stored.
- STACK-1. A reservation counted as both a county subdivision and a tribal area gets one point in each layer, on one spot.
- SHARES-1. A Senate district's shares field, 3,039 characters, may read as a wall in Text.
- HUB-1. The Hub site's owner (pressforwardmaine-nu.hub.arcgis.com).

### Wrong hypotheses

- That the state.md uploaded at session 3's start was session 2's: it was session 1's, with session 2's notes later appended to a copy, header unchanged.
- That rehearse_places.py survived somewhere on disk.
- That Map Viewer might misplace points sent in EPSG:4326: the door sends 102100, so the question never arose.
- That the 32-byte miss was the extent's long decimals: it was 16 whole coordinates.
- Session 2's, recorded there: a read that matched names as substrings; a runnable command with a hand-filled blank; an item sent without keywords or extent; calling the whole dry run "what the gate withholds".

### Lessons

- A rehearsal is evidence: it is committed with the record of what it sent, in tests/rehearsals/<sprint>/ beside tests/debug/, never in a folder deleted at a session's end (Kalli: rehearsals belong with the tests). It is run by hand against the live portal; what it finds becomes a fake and a test, so the suite guards it offline.
- A portal stores numbers its own way, so the door's canonical form follows the portal's.
- A kind built for one shape keys its checks on that shape's fields; a new shape breaks them in silence, so the checks are read before the shape is added.
- A state page is rewritten whole at a hand-off, or its header says something false.
- A working agreement spread over several lines drifts: the zip workflow had three lines that disagreed (ledger blocks inline, appended with cat >>, and inside a zip). It now has one home, state.md's How files move, and the other lines point to it (Kalli).

## Sprint 09, session 4 (2026-11-18): the polygon read, the towns as shapes, 9b designed

Repo at 9a69de8, clean, at the session's start; level with origin. No product code changed. Two strays at the repo root were removed: reads_9c.zip and _sprint08/, which held run_8b.md (8 KB, written 2026-11-18 01:38), deleted with it; Sprint 08's run record was committed in 07111bf, and whether run_8b.md held anything else is not known.

### Reads

- reads_9e (canopy/aws/display.py, canopy/expose/targets/arcgis_webmap.py, whole). `_simplify_coverage` refuses only a place emptied whole; a place that loses an island and keeps its mainland passes. Esri JSON winds outer rings clockwise and holes counterclockwise, the opposite of RFC 7946. Each level is simplified as its own coverage.
- The polygon read, twice (tests/rehearsals/sprint-09/polygons_read_9e.txt, polygons_read_9e2.txt): the rehearsal's `--polygons`, the door's own `_simplify_coverage`, the door's `_mercator`, rings wound Esri's way, bytes in D-362's form, only places with a told row measured. The points map read 2,351,368 bytes, f640fc4e8897, both times (the refactor of `build()` changed nothing), and 2,351,336 in D-362's form: exactly what ArcGIS stored in session 3.
  - Bytes, every level shaped, at 1 m: 29,884,615 (25 m), 11,604,012 (100 m), 7,792,156 (250 m), 6,740,278 (500 m). Towns alone shaped, every other level a point: 9,543,127, 4,779,523, 3,791,371, 3,512,660. At 0.1 m: 3,791,371 becomes 4,061,663 at 250 m.
  - No place lost a part at any tolerance. Area shrinks instead: the least kept among towns is Penobscot Indian Island Reservation (94.3%) at 100 m and Muscle Ridge Islands UT (75.5%, 56.6%) at 250 and 500 m; among tribal areas, Penobscot Reservation (2760R) keeps 74.9% at 500 m.
  - Validity: every canonical outline valid; every shape valid after simplifying, the door's 25 m included; 1 to 4 per level invalid after rounding to 1 m (self-intersections), all valid at 0.1 m but York County at 500 m. Towns at 250 and 500 m are valid at 1 m. One point near Lewiston fails in Androscoggin County, Senate District 21, House District 94 and Lewiston city: levels that share a border share its flaw.
- reads_9f (35 files, 9,168 lines; canonical_all_9f.txt): all five recorded entries already name `kind: arcgis_webmap`; `publish()` reads one artifact with one parquet parent (`_current` refuses data.json); `check()` keys on a layer URL and compares sharing with the record, not the target; pillar membership lives only in seeds/weights/cii_2026_equal_chips.yml, keyed on CII's published indicators, each of the 27 in exactly one pillar; TellingContext.load reads the standard, the notes and plain_language.yml beside the profile. The dry run names the stale nine: outlets_disagreements, outlets_groups and outlets_stack (rule 10); dissolve_counties, repair_counties, repair_towns, units_dissolve, units_geoid and units_repair (rule 4).
- The exact-name read (WITHHELD-1): no live reader. The outlets_* and units_* receipts name only each other; dissolve_counties and repair_counties appear in tests/test_receipt_names.py's known pairs and test_map_indicators.py's fixture dict; units_repair in test_preparations.py's tmp-plot fixtures; units_geoid in demo/index.html's old console figure.

### Rehearsals

- The shapes map, sent private to rewildingCities test as 7079e2b4d1234db48f12ac1dcbe51478 (places_polygons_sent.json): towns as shapes at 250 m rounded to 1 m, every other level a point, layer order county, sldu, sldl, cousub, aiannh (the last drawn on top). 3,791,371 bytes sent in D-362's form; `--polygons --check` read it private, 3,791,371 bytes, canonical sha256 4927ecdb6d44, SAME as sent, 5 of 5 layers, every count back. D-362 holds at the moment of sending. R5 has not yet been read on it.

### Decided (Kalli: revise against error and drift, then go with the intuitions)

- D-367. The places map draws towns as shapes at 250 m and every other level as a point; tribal points drawn last (STACK-1). Rests on R5, and reopens if a click on a shape does not move Text.
- D-368. Never send an invalid shape: a shaped level rounds to 1 m; any place invalid, emptied or with a ring collapsed sends the whole level to 0.1 m, so neighbours keep one edge; a failure there refuses the level, named. Held by a test.
- D-369. The towns' shapes come from a canonical display copy, web_250m; the door only projects, rounds, winds and applies D-368, and says so in the description.
- D-370. The told rows are a canonical display document under the profile's version, told_<inputs sha12>.json with its envelope, named by the hash of every input the telling reads, so a changed seed is a new name (D-322). A `told` step joins rule 11's closed set; Contract 2's section 4 admits a document copy. The door reads the told copy, never the profile.
- D-371. The places map is its own door path (`publish <plot> --places`), entry kind arcgis_places_map, key `places`, owed a move when the told copy, an outline or the towns' copy moves. A target's `kind` names the portal it speaks to (arcgis); an entry's `kind` names what the door made; an entry with none is refused. Revises D-364's mechanism.
- D-372. `check()` compares a places map by the D-362 hash of its stored JSON, and every item's sharing with its target's.
- D-373. The nine stale receipts move to plots/maine/.data/retired with their data files. Held after: 49 receipts, 37 may leave, 12 withheld (8 gate, 4 write); a profile rebuild still 824e79d23b1d.
- D-374. The pillar crosswalk is national: membership by `replicates` alone; any other placement a declared row with its reason, defined_by rewildingcities, told as ours. Placements wait for language.yml and carriers.yml (9b2).
- D-375. 9b is two zips, 9b1 and 9b2, each consulted briefly and built in a fresh chat.

### Opened

- WTABLE-1. Where the withheld table is shown: a web map table inside the places map, if Experience Builder's Table widget reads one; otherwise a told field.
- DEMO-2. demo/index.html shows an old run naming units_geoid_with_geoid.
- ROUND-2. The published display copies round to six decimals of a degree; validity after that rounding is unread.

### Wrong hypotheses

- That islands would lose parts at coarse tolerances: none did; they shrink.
- That the first read's label, "made invalid by the rounding", was earned: it was right, and unproven until validity was read before the rounding too.
- That the five recorded entries needed their kind written: they already named it.
- That _sprint08/ held only helpers: it held run_8b.md.
- That the door could carry the places map as a flag: it reads one parquet parent, and the profile is a document.

### Lessons

- Read a shape's validity at every stage it passes, or a failure is laid at the wrong step.
- A border's flaw appears in every level that shares it.
- Name a derived copy by every input that can change it, not only its parent.
- A folder named for helpers is read before it is deleted.
- The explorer's weight is a digital-access barrier of its own; the told text, not the shapes, is most of it (2.35 of 3.79 MB).
