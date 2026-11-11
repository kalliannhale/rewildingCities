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
