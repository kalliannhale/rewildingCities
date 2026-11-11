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
