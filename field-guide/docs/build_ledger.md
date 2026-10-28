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