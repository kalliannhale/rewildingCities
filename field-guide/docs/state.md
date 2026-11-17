# State of the garden ~ rewildingCities

What is true now. Rewritten, never appended, at every hand-off (D-160). The
build ledger (field-guide/docs/build_ledger.md) is the history; this page is
the present. When the two disagree, the ledger and the code win, and this page
is fixed.

**Updated:** 2026-11-17, at Sprint 08's first hand-off. Session 1 held the door's consultation and zip 8a: the publish door is built and run, and its first item is a web map owned by RDS_NU that reads the clerk offices' display copy by URL. A second push owed nothing. Sprint 08 stays open: its choropleth half, a second target, and zip 3b's list are zip 8b's. The plan is in Starting the next session.

## Where the build stands

- Branch main. Confirm with `git log --oneline -15` and `git status -sb`, and that both are pushed. Sprint 08's: c67a67a (zip 8a, the publish door, D-326 to D-334), then this hand-off's commit. Sprint 07's commits: 7dcd3f0 (zip 7a, the stack), a000d62 (the old stacks removed; its message names a ledger block it does not hold), 7158e6f (7a's ledger block), then session 2's one commit: zip 7b with zip7b2 and zip7b3, its ledger block, this page and Sprint 07's progress report. Sprint 06's last: 1497bfa, 106f721, 02e9b87.
- Tests: `python -m pytest -q -rs | tail -3`. 1,332 passed at zip 8a: 1,313 less the retired tests/test_publish_latch.py's 15, plus tests/test_publish_door.py (22, a fake portal that keeps items in memory and records every call), tests/test_webmap_json.py (7) and tests/test_map_stays_local.py (5). New in Sprint 07: tests/test_canonical_write.py (42 tests, a fake client that keeps the bucket's overwrite lock and fails on any removal; one test converts a real GeoJSON with geopandas) and tests/test_display_copy.py (24 tests, five drawing real geometry: two NAD83 towns keep one shared edge, the same bytes twice, overlapping towns refused, points simplify nothing, dates written as text). `-q` prints a dot per test; `-rs` lists skips only, with reasons. The full suite runs about two and a half minutes; `-rs` summarizes skips only and hides FAILED lines, so a failing run is reread with `python -m pytest -q --lf 2>&1 | tail -8`. The 2 warnings are Starlette and FastAPI test-client deprecations in tests/test_unit_authority.py, not ours. The R oracle tests run only where Rscript and rewildr are installed.
- Profiles: `python -m canopy.cli profile maine` builds all 1,663 places in about five minutes, a progress line every 50, into plots/maine/.data/place_profile_profiles.json and its receipt; `--place AUTHORITY:CODE` prints one and writes nothing. The build reads 21 receipts and withholds none at public (session 16); the outlet counts, the clerk counts, the clerk office points and place_profile_profiles all judge allow.
- Plan of record: the Master Plan, https://claude.ai/artifact/KpQRRSTyXr27emXnJFfL6z. Its decision table points to the ledger. Its Sprint 08 tab predates D-301 to D-334 and cites D-67 and D-71 where it means MP-67 and MP-71; this page's Sprint 08 section says what is true. Check its claims against this page and the code.
- Next decision ID: D-335. Before minting any ID, grep the ledger for it (LEDGER-3). Item IDs too.
- **Sprint 07 is closed** (session 2, after a reopening): the stack (zip 7a, D-301 to D-311), the canonical write (zip 7b, D-312 to D-320) and display copies (zip 7c, D-321 to D-325). Progress: field-guide/docs/progress/infrastructure/sprint-07.md.
- **The canonical bucket.** Kalli's account, us-east-2 (D-301). REWILDING_CANONICAL_BUCKET and REWILDING_CANONICAL_DOMAIN are set in the rewilding env (`conda env config vars`), never in the repo, since the bucket's name holds the account id; the write assumes rewilding-canonical-writer through the rewilding-writer profile in ~/.aws/config. CloudFront: dvk5mp17wovwb.cloudfront.net. `terraform output` in canopy/terraform prints the rest.
- **Canonical objects written:** clerk_offices_points_points, version 0b91cb0caae7, allow record 33ce1ddb61dc, 392 offices, with its display copy `web` (2026-11-17); outline_towns_outline, version eda591d0d3ba, allow record a19b45afae02, 528 towns, its display copy refused until COVER-1. The dry run judges 37 of Maine's 58 receipts may leave. Every write is public and permanent: dry-run first, write one artifact at a time, read the pointer and the data back after.
- **The first web map** (Kalli's ArcGIS Online, 2026-11-17): item 5fcd410b007a49aaa279e6a2b548f507, made by hand in Map Viewer by Add layer from URL (D-325). It sits outside the door's record: the door made its own (ADOPT-1, answered). Experience Builder is untried.
- **The door's first item** (2026-11-17): 143923c7e8174f709a87425f02c43f82 in nu.maps.arcgis.com, owned by RDS_NU, folder rewildingCities test, private, reading clerk_offices_points_points at version 0b91cb0caae7 by URL; recorded in plots/maine/publish/published.yml. Kalli has explicit permission to publish as RDS_NU for this project; its password is typed at the door's prompt and never stored, logged or committed.
- **Sprint 06 is closed** (Kalli, session 16), its order below. Carried forward, not done: step 7b, the FCC map (P-6, the first cut); step 10, the pairing table (P-2, after delivery); OWN-1's ledger check. Progress: field-guide/docs/progress/information/sprint-06.md.
- **Delivery, as Kalli set it in session 16:** the door, the kit and the canonical files in S3 for December; the explorer (Sprint 09) after. Clerk offices as points and outlets at their towns on the map, the aggregate counts kept for analyses. The cloud stack is tested on Kalli's own AWS account and handed to the library as code; the library's account is set aside.
- On or after 2026-12-02, when the 133rd's rosters are acquired: flip available: true, TRIBE-4, SEN-1, then run maine_seats.
- HRSA's sites copy lives at plots/maine/.data/hrsa_health_center_sites_20261114.csv (ignored, sha256 08b01537...da436). A fresh copy is a new manifest entry named for its day, never an overwrite.
- The Section 203 release lives at plots/maine/.data/sec203_puf_2021_12_01.zip (sha256 2d6b21e9...22d6, cp1252 though documented as ASCII) and the PIAAC Skills Map workbook at plots/maine/.data/SAE_website_dataset.c15d59a2d7e219fcb6d1.xlsx (sha256 b6745055...34b5, downloaded 2026-11-15). Both are U.S. government works.
- The Census key is set in the rewilding env (`conda env config vars`), loaded on activate; it was pasted into chat and shell history on 2026-11-16, so it is replaced (KEY-1).
- The clerk list lives at plots/maine/.data/sos_clerk_info_20261114.csv (sha256 abdaef75...fedee816) and the 911 file at plots/maine/.data/e911_agol_20260827.gdb.zip (212 MB, sha256 ec153095...b7a692, named for its information cutoff). Since D-298 and D-299 the list is factual_directory and the 911 file maine_geolibrary_public, both public; the courtesy ask to the GeoLibrary goes in the wrap-up. The 911 file holds home addresses; it never leaves .data, and the door publishes canonical harvests only, never a manifest dataset (a test to write in zip 8b).

## Sprint 08 ~ the publish door (open)

**Goal:** one door publishes every result: through the gate, from the canonical store, to each target a plot declares, updating in place and carrying its provenance.

**Zip 8a, the door (session 1, D-326 to D-334).** `python -m canopy.cli publish <plot> <artifact> --to <target>`, a dry run unless `--write` with `--by` and `--reason`; `--to` repeats; `--adopt <item>`, `--replace`, `--display` (D-326). It reads the harvest's `current`, allow record, receipt and display copy through CloudFront and needs no AWS credentials. Targets are declared by each plot in plots/<plot>/publish/targets.yml, read loudly; the door alone writes published.yml beside it, each item naming the sha256 and allow record it shows (D-327). The door owns, in a web map item, only the layer's URL and fields, the description (the notes travel in it) and the credits; a person's style is kept on every move. A new version moves the URL and the description, a new allow record the description alone; a missing item waits for --replace, a hand-edited URL or description is refused; a new item is recorded unshared before it is shared (D-328). REST through requests, no Esri package; generateToken with a prompted password, then community/self must name the target's owner (D-329). Institutional owners; a personal one is warned about on every run (D-330). The web map follows the specification 2.38: fields typed from the copy's values, a plain popup, the copy's bbox as the extent; the description holds no time, so the same records write the same words (D-333). The publish route assignment's F3, F7, F8, R1 to R6 and R9 were not found and are not reconstructed (D-334). `map --publish` signposts the door and exits 2; visuals.py's upload latch and introspect's arcgis row are gone.

**Decided, built in zip 8b (D-331):** choropleths by `canonical <plot> <table> --display --join <outline>` (not built yet), joining (unit_authority, unit_code) to (authority, code) in one canopy/choropleth.py that map.py imports; one wide copy per table version and outline version, every indicator's columns, empty kept empty, derived_from both, two lineage branches, the join's counts; the door colours one indicator per map with a classBreaks renderer: standings in fixed national quintiles, other values by a declared standard or in equal steps said so, no value hatched and labelled.

**The done-when, as it stands:** one item made by the door, naming its version, allow record and URL: done (143923c7). A second push leaves one item: done (unchanged, nothing owed, no sign-in). Two targets, one item each: waits on a `library` target (folder, sharing, groups). Broadband as a choropleth: zip 8b, then the canonical writes of county_standardize_standings (1b9c5a6e8d71), county_count_derive_values (fe7922079828) and outline_counties_outline (ee88e4f41db3), all three judged may-leave at public in session 1 and not yet written.

**Confirmed against a real portal (session 1):** generateToken, community/self, a user's folders, createFolder, addItem and Share. Update is not yet exercised; the first version move checks it.

## Sprint 07 ~ storage outside AGOL (closed)

**Goal:** the truth that leaves is written once, outside AGOL, in a bucket that cannot overwrite it, readable by URL from anywhere.

**Zip 7a, the stack (session 1, D-301 to D-311).** One Terraform stack in canopy/terraform (D-306): a private, versioned bucket, TLS-only, SSE-S3 with SSE-C blocked, Block Public Access on, noncurrent versions kept (D-307); CloudFront with origin access control reading harvests/* alone, CORS for any origin, versions cached long and current never (D-302, D-310); the writer role, put, get and list under harvests/, every delete denied, no access key (D-308); the bucket policy as the overwrite lock for every principal (D-309); access logs; the budget switched by create_budget (D-311). Applied on Kalli's account in us-east-2, the project's assigned region, because an organization policy refuses S3 in us-east-1; the committed default stays us-east-1 for the handover. The README holds the order of apply and the handover addendum.

**Zip 7b, the canonical write (session 2, D-312 to D-320).** canopy/aws/s3.py and `python -m canopy.cli canonical`. A receipt from the plot's .envelopes, its data in the plot's own .data (D-312), is judged by the gate at canonical, public (D-315). The receipt travels byte for byte as envelope.json; the allow record lives beside it, versioned by its own content (D-313, D-320). Parquet and JSON are written as they are; GeoJSON becomes GeoParquet, converted twice and refused if the two differ, the change recorded as format_changed by the canonical write (D-314). A custom tier is refused until O-6. The command is a dry run unless --write, which takes one artifact with --by and --reason (D-316). Data is put last; current moves with If-Match (D-317). A harvest's name is its artifact's (D-318).

**Zip 7c, display copies (session 2, reopened, D-321 to D-325).** canopy/aws/display.py and `canonical <plot> <artifact> --display`: drawn from the current version's own bytes read back from the bucket and checked against its sha256, written under the version's display/ (D-321); points named web, polygons web_<tolerance>m, a name never given new bytes (D-322); an envelope inheriting the version's lineage, notes and chain, with its own make_display_copy entry recording simplified, rounded and format_changed, schema-checked and judged by the gate (D-323); polygons simplified as one coverage in EPSG:26919, 25 m by default, an invalid coverage or an emptied geometry refused; points simplify nothing, said with count 0; six decimals; GeoJSON in EPSG:4326 naming pyproj's operation; dates as ISO 8601 text, each such field named (D-324). In ArcGIS Online a copy is referenced through Map Viewer's Add layer from URL; the Content route imports GeoJSON and is not used (D-325).

**The dry run (session 2):** 37 of 58 may leave, 21 withheld, 0 unjudged. Withheld: rule 5 for the outlet listings, groups and stacks; rule 9 for all five carriers' located_in_edges (EDGE-NOTE-1); rule 10 for the old outlets_* receipts, which still carry Cision from before D-294; rule 4 for eight receipts with no lineage (RECEIPT-1's chain); literacy and section 203's CSVs by format (both reach the public through the profile). May leave: every outline, every carrier's counts and points, every indicator table, the profile.

## Sprint 06 ~ the place profile and the standard (closed in session 16)

**Goal:** every Maine place has a six-part profile, its carriers are on the map, and every barrier is judged against a stated, absolute standard.

**Decided in the design pass:** D-197 (build_profile wraps read_place), D-198 (margin-aware verdicts, derive_margins), D-199 (universal, trigger, none thresholds), D-200 (each barrier a family of registered indicators with a status).

**Decided in session 1:** D-201 to D-209. **In session 2:** D-210 to D-212. **In session 3:** D-213 to D-217. **In session 4:** D-218 to D-222. **In session 5:** D-223 to D-226. **In session 6:** D-227 to D-229. **In session 7:** D-230. **In session 8:** D-231 to D-233. **In session 9:** D-234 to D-239. **In session 10:** D-240 to D-246. **In session 11:** D-247 to D-252. **In session 12:** D-253 to D-257. **In session 13:** D-258 to D-269. **In session 14:** D-270 to D-282. **In session 15:** D-283 to D-293. **In session 16:** D-294 to D-300, below.

**Order of work, and where each step stands:**

```
 1  P-9: read the outlet files                done      answered
 2  located_in edges + end checks             done      D-207
 3  carriers, counted per 1,000               done      libraries, schools, health centers, clerks' offices, outlets
      libraries (IMLS PLS FY 2024)            done      D-208 to D-212: placed, counted, closures declared
      first, by Kalli's order (session 2):
        SCHEMA-2: the method schema           done      D-213 to D-217
        CMAP-1: the carrier map as a view     done      D-218, D-219, D-223 to D-226
        the drift CMAP-1's walk found         done      D-220 to D-222
      the drift session 6 found               done      D-227 to D-229; INDFILE-1 closed
      schools (NCES EDGE 2024-25)             done      D-230: 598 placed, counted
      the year rule SURVEY-1 hid              done      D-231: boundary_vintage
      health centers (HRSA, 2026-11-14 copy)  done      D-232: 168 placed, 24 listed
      tribal areas counted beside a note      done      D-233; TRIBE-8, LOAM-2 closed
      clerks' offices (GEO-1)                 done      D-234 to D-239: 390 offices, 458 of 560 rows
        GEO-4: reviewed matches               done      D-240: 392 offices, 468 rows; 1575R reads 1
      outlets, placed by town (WHERE-1)       done      D-241 to D-246: 460 placed, 65 listed
        closed, local news, where             done      D-247 to D-252: 90 placed, 435 listed
        read whole, reviewed with sources     done      D-253 to D-257: 97 placed, 405 listed;
                                                        OUTCONF-1 before publishing
 4  derive_margins (D-198)                    done      D-258 to D-260: inside derive_indicator,
                                                        R and Python, oracle-held; the count kind
 5  language: ACS, safe harbor, section 203   done      D-261, D-263, D-264, D-267: C16001 at five
                                                        levels; section 203 read as published
 6  literacy: PIAAC county estimates (P-7)    done      D-265, D-268: Skills Map, 17 rows
 7  digital access counts + FCC map (P-6)     7a done   D-262: the rate's own complement;
                                                        7b (FCC) not yet, the first cut
 8  outlets reconciled                        mostly    stacked, grouped, reviewed (D-253 to D-257);
                                                        ownership concentration exists (Kalli,
                                                        session 12); check OWN-1 in the ledger
 9  profile.py + the standard seed            done      D-270 to D-293 (sessions 14, 15),
                                                        b3426b1: the standard, verdicts.py,
                                                        profile.py, the profile command
10  pairing table (P-2)                       after     part 6 ships present and empty, its
                                                        reason said (D-285, Kalli's cut)
11  profiles for every place                  done      1,663 places, every level (D-292);
                                                        the gate first (D-284, D-293)
```

**Schools, done (session 7).** Placed from NCES EDGE Public School Locations 2024-25 (D-230): one national release zip (sha256 9dc51ecd...cffb288, in the manifest's known_issues), its headerless text table read through seeds/crosswalks/schools/nces_edge_geocode.yml. 598 schools placed, none listed; the three Wabanaki community schools (OPSTFIPS 59, the Bureau of Indian Education) placed and flagged, one located_in edge per drawer each, Indian Island School in 2301957936 (the Penobscot County piece) and 2760R. Maine counts 598, 0.439 per 1,000 of 1,362,359 persons; Penobscot Indian Island Reservation counts 1 among 370, shown beside its note since D-233. Maine DOE's 13 exports carry no ID and no school's coordinates, so they place nothing; their name lists may serve as a check later (seeds/sources/maine_doe_schools.yml, an export source: only our copy is evidence). MEGIS's school layer carries no state or NCES school ID either. The EDGE characteristics layer (status, grade span) could not be downloaded; the CCD directory, joined on NCESSCH, is in reserve if the DOE check needs the state school ID (its public-use terms limit use to statistical purposes).

**Health centers, done (session 8).** Placed from HRSA's Health Center Service Delivery and Look-Alike Sites, the copy downloaded 2026-11-14 (D-232): a daily snapshot with no release, so the copy is the evidence, declared by its day and sha256, and every row's Data Warehouse Record Create Date is held to the day. Read through seeds/crosswalks/health_centers/hrsa_health_center_sites.yml (header names, codes; an undeclared code refuses). Maine: 192 rows, 168 placed (32 seasonal, 8 look-alikes, every setting), 24 listed (10 administrative, 9 mobile vans, 5 with no point). Maine counts 168, 0.123 per 1,000. No Wabanaki nation's clinic appears; HRSA's program does not see them.

**Clerks' offices, done (session 9).** Town offices became the municipal clerk's office (D-236): where a person registers, asks for a record and puts a question to the town. The list is the Secretary of State's clerk CSV (560 rows, MEGIS GeoCode, five column names twice, read by position; names and phones never read). Each street address is matched exactly to Maine's 911 address points (the GeoLibrary FGDB, NG_ADDRESSES, 798,422 points, EPSG:26919) on house number, street and ZIP, the street spelled through USPS Publication 28 on both sides (D-234, D-235, D-238). One point per distinct office, named by the 911 point's SITE_UID; the rows naming it ride on it as the municipalities it answers for (D-237). Ties: one building settles on its bare point (a rule); a campus settles on its one Government - Municipal point when campus_ties says municipal_class, Kalli's choice (D-239). A person's reading of an address no exact match places is a reviewed match (GEO-4, D-240): seeds/crosswalks/clerks/maine_sos_reviewed.yml, keyed by the list's address as written, naming one standing 911 point by SITE_UID with its evidence, day and reader; it applies only to a row the run would otherwise list and refuses the run when no longer needed. Maine: 392 offices for 468 rows (352 exact, 6 building_point, 32 municipal_class, 2 reviewed); listed 64 no_match, 20 tie, 7 no_street_address, 1 number_not_read. Penobscot Nation's office stands in 2760R, Pleasant Point's in 2850R, and Indian Township's, by review (8 Kennebasis Road written, 8 Kennebasis St in the file), in 1575R, which now reads 1. 7 Minden, nine rows, stands on the 911 point labelled Greenville Police Department; these sources do not say whether the clerk shares it, and CARRY-1 keeps landmark and place_type off the map. The note is carrier_seen_on_nations_land (TRIBE-10). pyproj 3.8.0 does not report its operation for 26919 to 4326; the receipt says so.

**Outlets, placed by town (session 10, D-241 to D-246).** Only Local News Catalyst (30 records) and the Maine Media Ecosystem file (81) name a town, 111 of 926 records, which reopened WHERE-1 the day it was decided. maine_outlet_carriers restacks and regroups the five listings under its own step ids, then prepare_news_outlets writes one outlet per group (type news_outlet), its id made from its members in the declaration's source_order, never row order (D-243). A named town places it and always wins; when none is named, Maine's choice town_fallback: office_town places it by Cision's office town name, flagged (D-242). Towns are matched by name after the Census suffixes in seeds/crosswalks/places/census_name_suffixes.yml come off; two towns, no match, two matches or no town are listed (D-244). Operating status comes from operating_vocabulary in outlet_sources.yml; Maine's ceased_outlets: listed (D-245). build_town_located_in places each outlet at town, county and state only, never a district or tribal area (D-246); loam's carriers view leaves the table out by name. Reviews (merges, towns) go in seeds/crosswalks/outlets/outlet_reviews.yml, keyed by source and name as written; none yet. Maine: 460 placed (388 office_town, 72 named_town), listed 28 no_town_given, 21 ceased, 11 no_town_match, 3 towns_disagree, 2 ambiguous_town; operating 312, not_given 141, last_post 7. Portland city counts 121 and Bangor city 67, Cumberland County 191 of 460: the office fallback concentrates outlets where publishers keep offices (OFFTOWN-1), and Cision's types include trade press and blogs (MEDIUM-1). The listings are undated, so the count's time reads undated (UNDATED-1).

**Outlets asked closed, local news, where (session 11, D-247 to D-252).** prepare_news_outlets now asks each outlet three things in order. Closed: operating_vocabulary, and a status written in another column through operating_elsewhere (the ecosystem file writes CLOSED in its Medium, D-251). Local news: source_kinds declares Local News Catalyst, the ecosystem file and Easton local_news_lists, whose membership is the evidence, and both Cision pulls media_databases (D-247); an outlet only a database holds is judged by media_database_types (all 20 Cision types declared, two axes, medium and audience; an undeclared type refuses; 0 declared unknown) under the choice database_alone, Maine: newspapers; a program never counts (D-248). The medium is judged before the town, so no review can place an outlet listed for its medium. Where: a named town wins; a name in statewide_names places an outlet in the state alone, scope state, one edge (D-249: Amjambo Africa); else town_fallback, Maine: office_town_unshared, where an office address two or more outlets give, compared as normalized street plus five-digit ZIP with leading zeros a spreadsheet dropped given back, is a publisher's office and the outlet is listed office_shared (D-250). Every listing declares source.collected "2026-08" in the manifest and the count's time reads "collected 2026-08", held there by a test (D-252, SRCFACT-2). Each outlet row carries scope, vouched_by, database_class and medium_as_written. Maine: 90 placed (70 named_town, 19 office_town, 1 named_state; 74 on a list's say, 16 Cision newspapers alone), 435 listed (327 medium_not_counted, 32 office_shared, 23 ceased, 23 medium_unknown, 19 no_town_given, 6 no_town_match, 3 towns_disagree, 2 ambiguous_town), 525 in all. Portland 18 (17 named), Cumberland County 29 of 90: what concentration remains is the lists' own. Turner's ten Fern Street weeklies and the Maine Trust for Local News' Portland address (20 outlets) are publishers' offices; the 32 office_shared hold publishers, one paper listed several times (Lincoln County News four times) and sections listed as outlets (The Maine Campus), which is OUTREV-1's queue and EDITION-1's question.

**Outlets read whole and reviewed (session 12, D-253 to D-257).** group_outlet_records now reads a trailing ", The" as the name written inverted (D-253: Cision's "Star-Herald, The"), and joins one source's records alike in name key, url key and office address as one record written twice, its key held once, every copy saying same_record_as (D-254). The office address comparison has one home, group_outlet_records.office_key, which prepare_news_outlets imports. Before D-254, Lincoln County News stood as six groups: Cision's copies held its key twice, so the key joined nothing for anyone (D-202). A reviewed merge may hold one source twice only when it says editions, in words (D-255); a review names a record written twice once. office_reads (keep, town, state, list with a reason) read an outlet placed by its office town alone; an unread one stays placed, flagged office_town_unread (D-256). A town review may say state: true in place of a town_code (D-257). seeds/crosswalks/outlets/outlet_reviews.yml holds 5 merges (the Press Herald with its Sunday edition and site; The County with the Star-Herald, folded in January 2025; the Castine Patriot's two list records; Maine Wire twice; the Boothbay Register / Wiscasset Newspaper, one paper from 97 Townsend Ave.), 23 towns and 12 office reads. Claude read them from cited pages; read_by says so, and Kalli confirms each (OUTCONF-1). Every reading places an outlet where its newsroom, office or broadcast license is; the towns it covers stay SERVES-1's. Three papers had been on the map more than once (the Press Herald, the Castine Patriot, the Boothbay Register in three towns), and Cision lists papers that no longer stand apart (the Coastal Journal, into The Forecaster; The Free Press, into the Midcoast Villager). Maine: 97 placed (65 named_town, 26 reviewed, 5 office_town, 1 named_state), 405 listed (326 medium_not_counted, 23 ceased, 23 medium_unknown, 21 office_shared, 8 office_read_listed, 4 no_town_given); 4 edition merges; 4 office towns unread (The Cryer, USM's Free Press, Rolling Thunder Express, Twin City Times); no towns disagreeing. Portland counts 19.

**Zip 3a, counts go public (session 16, D-294 to D-300).** Cision's two exports are their own type, commercial_outlet_listing, excluded, and maine_outlet_carriers stacks only the three lists, named in stack_outlet_sources' use parameter: Cision stays declared in the shared crosswalk and is left out by name (D-294). Choices database_alone none and town_fallback none. outlet_listing, outlet_stack, outlet_groups and news_outlet are aggregate-only (D-295, D-297); indicator_values and place_profile declare aggregates: true (D-296: rule 5's way out had been unreachable). The clerk types are public (D-297). Terms: the 911 file maine_geolibrary_public (D-298); the clerk list factual_directory and Easton's and LNC's lists factual_compilation_counts, which carries requires_tier: aggregate-only, enforced in rule 10 (D-299, Kalli's readings of Feist, not a lawyer's); the ecosystem file project_own_work (D-300). Reviews: Cision's 10 office reads and Rumford Falls Times removed; Maine Morning Star became a town review (state); The County's merge keeps editions (the ecosystem file lists both papers); the Castine Patriot's merge removed (its records now join by name). Maine: 90 outlets placed, 12 listed (10 no_town_given, 2 ceased). Named outlets wait for OUTCONF-1 and the lists' makers' word: every outlet type in the lineage binds, so the lists' tiers and terms move too. The map's outlet layer is two artifacts joined at the town: the counts (aggregate, leaving now) and the listing (news_outlet, leaving later), one GeoJSON display copy per town marker (session 16, for zip 3b).

**Zip 1, the measures (session 13, D-258 to D-269).** Ratio margins are derived inside derive_indicator, in R and in preview.py, the arithmetic's one Python home canopy/indicators/margins.py, held equal by the oracle (D-258): never as a second indicator_values artifact, which loam would refuse (D-172). Every ratio declares relation: proportion or ratio (D-259), by the Census's 2025 statistical testing instructions: ratio fallback flagged in moe_formula, sums by root-sum-of-squares, a controlled part's margin 0; a proportion of exactly 1 is not_derived (D-269). A count kind adds and subtracts cells (D-260). The language family is C16001 at state, county, cousub and both chambers, 26 indicators in seeds/indicators/language.yml (D-261); households_without_broadband is cii_broadband's own complement (D-262). Section 203's 2021 public use file is read as published into section203_records (D-263): 516 Census towns matched, 12 of ours without a record, Penobscot Indian Island (57936) held whole across its county line, and six Census towns no longer ours (Atkinson, Bancroft, Cary, Codyville, Drew, Magalloway: deorganization between the maps) held under census_s203_mcd (D-267); five tribal areas under Census's own codes, attached to no place (D-264); 0 covered. Literacy is literacy_estimates from the Skills Map workbook (D-265, D-268): 17 rows, none flagged, left_out as NCES computes it, modelled partly from race, poverty and education, never combined with its predictors. First read: Aroostook's French, Haitian or Cajun share is 2.29% plus or minus 0.40 of persons 5 and over, about 85% of its limited English and about 1,465 persons; Androscoggin's limited English is 3.35%, two thirds in other groups.

**Tribal areas, counted beside a note (session 8, D-233).** All three carriers count the 8 Census tribal areas, each row carrying context_note: carrier_unseen_on_nations_land (libraries, health centers: all zeros) or carrier_seen_on_nations_land (schools: Indian Township, Pleasant Point and Penobscot each count 1). The notes' words are Kalli's DRAFT in seeds/notes/notes.yml, waiting on the nations' terms (P-8). Four trust lands hold 4 to 202 persons, so their rates are unstable; the count and persons travel with each rate.

**The barriers, their indicators, and where the data is** (as decided in the design pass; P-9 changed three rows' status, session 13 acquired three, session 14 set their standard):

| Barrier | Indicators | Source | Grain | Status |
| --- | --- | --- | --- | --- |
| Not in the right language | limited-English persons by C16001 group (26 indicators); limited-English households; section 203 coverage | ACS C16001 at five levels (D-261); DOJ 2002 safe harbor as our own line (D-271); Census section 203 file (2021, D-263) | every level | acquired |
| Requires digital access | households with no internet subscription (the judged count, D-262, D-272); the rate; no service at the FCC benchmark | ACS; FCC National Broadband Map | count at every level; rate at town and district | ACS acquired; FCC acquirable (7b) |
| At the wrong literacy level | adults 16 to 74 at or below Level 1 | NCES PIAAC Skills Map (pooled 2012/14/17, D-265) | county and state, borrowed elsewhere (D-276) | acquired |
| Lacking cultural cues | languages spoken against languages carriers publish in | ACS and our own observation of outlets | town | needs our observation (OBS-1): no listing carries language |
| Behind a paywall | share of local outlets free to read | our own observation (OBS-1), P-3 | town | needs our observation: no listing carries paywall status |
| Outdated | outlet publishing frequency; observed last post | Cision, the ecosystem file, Easton (frequency); Cision's Still Operates? (last post) | town | acquirable from the stack |
| Not where people look | carriers per 1,000 by type | IMLS, NCES EDGE, HRSA, the Secretary of State's clerk list through Maine's 911 points, the outlet listings by town (done) | every level; outlets at town, county and state | libraries, schools, health centers, clerks' offices counted (D-209, D-230, D-232, D-239, D-240), outlets by town (D-246), tribal areas beside a note (D-233); on the map as loam's carriers view (D-225), adjectives and notes not yet carried (CARRY-1) |
| Not from a trusted source | relational hubs, aggregate-only | consent-governed | as consented | needs_consent (Sprint 16) |

**Still open in Contract 4:** P-2 (pairing table, after delivery, D-285), P-3 (free outlet), P-6 (FCC benchmark, with 7b), P-8 (section 203 on Wabanaki places; on the nations' terms), GAPS-1 (part 5 in the method authors' words). P-1 and P-5 closed in session 14 (D-271); P-7 and P-9 before.

## Decided in Sprint 06, session 1

| ID | One line |
| --- | --- |
| D-201 | Outlet sources read only as seeds/crosswalks/outlets/outlet_sources.yml declares; headers found by declared names; never_read columns refused |
| D-202 | Outlet records grouped by exact url (path kept) and name keys; never one source twice; a key one source holds twice joins nothing |
| D-203 | Place fields keep their meaning: office_* a postal address, named_* a town a source names, served_raw coverage; compared like with like |
| D-204 | An outlet's county comes from the graph through its town; a source's county is a check (Cision's reads Cook, Illinois) |
| D-205 | Outlet listings stay in garden/reference/ (ignored) and are manifest datasets with paths outside the plot |
| D-206 | `$crosswalks.<n>` resolves seeds/crosswalks/**/<n>.yml into params, so freshness sees an edit |
| D-207 | located_in edges are their own type, located_in_edges, one artifact per layer; towns from the 2024 face, districts and tribal areas from the face's 2020 block |
| D-208 | A library outlet is FSCSKEY-FSCS_SEQ; fixed outlets only; bookmobiles listed, never placed; flags kept; the outlet file is Windows-1252 by its own text |
| D-209 | A carrier is a registered indicator, role carrier, derivation located_count, in seeds/indicators/carriers.yml; every place a row, the count beside the rate; loam's statistical rule now judges ACS values only |

## Decided in Sprint 06, session 2

| ID | One line |
| --- | --- |
| D-210 | A library outlet's structure status is declared once, code to meaning and group (open, permanent, temporary); a blank or undeclared status on a fixed outlet refuses the run; permanently closed outlets are listed, never placed (a rule). Codes from IMLS PLS FY 2024 Documentation, Appendix B; 22 left undeclared |
| D-211 | A temporary closure is a method choice, temporarily_closed (listed or placed); Maine chooses listed, following IMLS's own tables, so Atkins Memorial, Corinth, is listed and 261 fixed outlets are placed; the primitive refuses any other value |
| D-212 | A carrier's meaning lives once, in its method; docstring, run header, registry and indicator rationale point to it. A rule (the other way is simply wrong) is a test; a choice (reasonable people differ) is declared. Bookmobiles are a rule |

## Decided in Sprint 06, session 3

| ID | One line |
| --- | --- |
| D-213 | seeds/schemas/method.schema.yml (v2.0) is the one home of a method's shape, additionalProperties false throughout. Every reader loads a method through parsing.load_method_data: an undescribed shape, a key written twice or a default outside its options is refused, every problem named. A run on a refused method is a validate() error. Options are a mapping keyed by option id; an empty value means the choice's description says it; no option carries an id of its own |
| D-214 | requires_primitives is a list of layer/name references, each resolving in its registry; a recipe uses only primitives its method declares; per-method purposes are YAML comments |
| D-215 | produces is a list, even for one output |
| D-216 | garden/methods/index.yml routes only (domain, id, path); a method's name and answers_question_types live in the method; MethodIndexEntry carries neither |
| D-217 | roots/count_by_unit deleted, never registered: count_located (D-209) is the one count of points in places |

## Decided in Sprint 06, session 4

| ID | One line |
| --- | --- |
| D-218 | Each carrier kind is its own semantic type in the domain vocabulary, never one type with a kind field |
| D-219 | institutional_node retired with no alias; IMLS's placed outlets are library_outlet; the unbuilt Maine manifest entry removed; maine_libraries rerun (261 placed, 3 mobile and 1 temporarily closed listed, as before) |
| D-220 | A live declaration names a current type, never an alias or a state-suffixed name: state is provenance, kept in the receipt. Aliases and suffix_fallback stay to read old receipts forward |
| D-221 | Every type live work named is declared (water, forest, neighborhood boundaries; roads, nighttime_lights, population_density; measured_composition) or renamed to its existing home; check_alignment unregistered, its 0-byte file deleted |
| D-222 | The wonder composer drafts current types; the three composed drafts (e6e967, 4ade33, STUB-1's 4a8f59) deleted |

## Decided in Sprint 06, session 5

| ID | One line |
| --- | --- |
| D-223 | Carrier-hood lives in the indicator registry, each indicator's role; IndicatorRegistry.with_role() finds carriers. role carrier and derivation located_count are independent: the map draws carriers that are located_counts |
| D-224 | A located_count names the type it counts (derivation.counts: library_outlet), never a layer label, which a seed may not hold; the label stays in the preparation and the receipt (counted_layer). The orchestrator checks before a run that the counted points are that type, read once, from edges made in the run |
| D-225 | loam's located_in view unions every located_in_edges receipt (LOC-VIEW-1); its carriers view gives every placed point of every located_count carrier, found through the edges receipt's own provenance record. place.py reads an exact count apart by derivation and labels every value by role, reading indicators through the registry |
| D-226 | IMLS's codes (outlet types, structure statuses) are one shared crosswalk, seeds/crosswalks/libraries/imls_pls_outlets.yml, passed whole as `reading`; a release's outlet member and encoding are declared in its manifest entry and held to the run as source_facts; seeds/sources/imls_pls.yml is reference only, pointing to each fact's home |

## Decided in Sprint 06, session 6

| ID | One line |
| --- | --- |
| D-227 | An indicator's declaration_sha256 is taken over its own mapping, canonical, without its rationale; computed when parsed, never by reopening the file. A sibling, a comment or a prose edit never stales a receipt. Weights and reliability unchanged (one declaration per file) |
| D-228 | One experiment per question: county standings answers basic_needs_and_opportunity (rent burden, vehicle access); broadband's county standing lives only in maine_broadband_access_subscription__cii_indicator_values_91b5c0, same method and choices |
| D-229 | The no-curiosity warning names only the gap; advice to become a preparation comes only from the error for a run with a preparation method (a rule, tested) |

## Decided in Sprint 06, session 7

| ID | One line |
| --- | --- |
| D-230 | Schools from NCES EDGE 2024-25, keyed NCESSCH, columns and codes from one crosswalk; a school is in the state where NCES's point stands (STFIP), never its operator's (a rule, tested): the three BIE-operated Wabanaki community schools are placed, flagged and counted in every drawer, once each; DOE and MEGIS place nothing. Kalli's choice A, with her guard that Indian Island counts once, as the county subdivision it is |

## Decided in Sprint 06, session 8

| ID | One line |
| --- | --- |
| D-231 | A count says which boundaries it sits on in each row's boundary_vintage, the one vintage of the edges reaching that level; loam reads it for publishers whose rule says boundary_vintage (rewildingcities), so `time` says only when. Closes SURVEY-1 |
| D-232 | Health centers from HRSA's sites file, a daily snapshot declared by day and sha256, rows held to the day; keyed BPHC Assigned Number. Rules: administrative sites, mobile units, sites with no point, withheld addresses, sites not open or elsewhere are listed. Look-alikes, seasonal sites (as an adjective) and every setting are placed (Kalli's choices); who a site serves stays SERVES-1's |
| D-233 | A Census tribal area is counted, never refused, beside the note its step names (tribal_note), carried on every tribal row (context_note); the words are Kalli's DRAFT, on the nations' terms. loam refuses only the ACS on tribal areas (D-171) and judges each publisher on its own levels (LOAM-2). A tribal code and its persons are AIANNH plus component. A level no edge reaches takes its places' vintage |

## Decided in Sprint 06, session 9

| ID | One line |
| --- | --- |
| D-234 | Maine's 911 address points place an address first, the Census Geocoder second: Census interpolates potential ranges, misses non-residential addresses, withholds in sparse places, and matches one batch differently twice |
| D-235 | The 911 points come from the GeoLibrary FGDB, declared by its information cutoff and sha256, never paged from the live service (whose count and schema differ) |
| D-236 | Town offices are the Secretary of State's clerk list; the carrier is the clerk's office. The 911 classes cannot list them (default Residential) |
| D-237 | One point per distinct office, placed where the matched point stands, named by its SITE_UID; GeoCode a check and serves-key, never a placer (a rule) |
| D-238 | Exact match: house number, street, ZIP; the street spelled through USPS Pub 28 (C1 suffixes, 233 directionals) on both sides; no suffix guessed; ZIP over town |
| D-239 | A tie in one building settles on its bare point (a rule); a campus tie follows campus_ties (Maine: municipal_class, flagged tie_broken_by_class); every settled point carries its candidate count and spread |

## Decided in Sprint 06, session 10

| ID | One line |
| --- | --- |
| D-240 | A reviewed clerk match lives in a seed beside the clerk crosswalk, keyed by the list's address as written; it names a standing 911 point by SITE_UID with evidence, day and reader; placed_by reviewed. Kalli's choice C |
| D-241 | An outlet is where a listing names its town; Cision's office address an attribute; Easton's coverage SERVES-1's; reopened the same session by D-242 |
| D-242 | A named town places an outlet first and always wins; town_fallback (none, office_town) says whether the office town name may place one no listing names, flagged; Maine: office_town |
| D-243 | One outlet per exact-key group, its id from its first member by source_order, never row order; reviewed merges keyed by source and name as written |
| D-244 | Towns matched by name after declared Census suffixes come off; towns_disagree, no_town_match, ambiguous_town and no_town_given listed (a rule); a reviewed town settles only a listed outlet |
| D-245 | Operating status through operating_vocabulary: operating, ceased, last_post (counted, words kept), unmapped (counted); ceased_outlets (listed, counted); Maine: listed |
| D-246 | An outlet is placed by its town code at town, county and state only, each edge with its place's own vintage; never a district or tribal area. Outlets then edges keeps D-224's check; loam leaves a table layer out of the carriers view by name |

## Decided in Sprint 06, session 11

| ID | One line |
| --- | --- |
| D-247 | source_kinds: a local news list's membership is the evidence an outlet is local news; a media database's declared type judges only an outlet no list holds; every type declared, an undeclared one refuses; 0 is unknown, never a class |
| D-248 | database_alone (none, newspapers, print_and_web), default none, Maine newspapers (Kalli's go); a program never counts (a rule); the medium is judged before the town; one counted and one uncounted known type is medium_conflict |
| D-249 | A name in statewide_names places an outlet in the state alone (scope state, one edge, build_town_located_in's scope_field); a named town wins, flagged statewide_also |
| D-250 | An office address two or more outlets give is a publisher's office: flagged office_shared, listed under office_town_unshared (Maine's choice). Street normalized, ZIP five digits, a dropped leading zero given back (a rule) |
| D-251 | A status a source writes outside its operating column is read through operating_elsewhere by declared words (the ecosystem file's CLOSED) |
| D-252 | Each outlet listing declares source.collected in the manifest (2026-08, Kalli); the count's time is "collected 2026-08", held to the manifest by a test until SRCFACT-2 |

## Decided in Sprint 06, session 12

| ID | One line |
| --- | --- |
| D-253 | A trailing ", The" is a name written inverted; the name key drops it (a rule) |
| D-254 | One source's records alike in name key, url key and office address are one record written twice: they join first, the key held once, same_record_as on each copy (a rule); office_key's one home is group_outlet_records |
| D-255 | A reviewed merge may hold one source twice only when it says editions in words; editions where no source is twice refuses; a review names a record written twice once |
| D-256 | office_reads keep, move to a town or the state, or list (reason in words) an outlet placed by its office town alone; refused otherwise; unread ones stay placed, flagged office_town_unread |
| D-257 | A town review names a town_code or says state: true, never both |

## Decided in Sprint 06, session 13

| ID | One line |
| --- | --- |
| D-258 | Ratio margins computed inside derive_indicator (R and Python, oracle-held), never a second values artifact; supersedes D-198's own step, its verdict rule stands |
| D-259 | Every ratio declares relation: proportion or ratio; Census 2025 formulas; fallback flagged; controlled margin 0; every derived margin an approximation; no zero-estimate rule |
| D-260 | A count kind: cells added and subtracted, the sum formula; a one-cell count carries its published margin |
| D-261 | Language from C16001 at five levels, 26 indicators, groups in Census's words; B16001 a named gap |
| D-262 | The digital count is B28002_001 minus _004, the rate's own complement |
| D-263 | Section 203 read as published: cp1252, keyed by LANCOUNT, flags as evidence, towns by five-digit MCD; its own artifact; no stated confidence, so cannot_judge |
| D-264 | Section 203 tribal rows never a town's value, attached to no place, shown on the nations' terms (P-8) |
| D-265 | Literacy from the Skills Map workbook, grpName all, 95% credible bounds and flags, left_out by NCES's recipe; modelled from race, poverty and education, never combined with its predictors; P-7 closed |
| D-266 | The ACS pinned at 2020-2024 |
| D-267 | A Census town split at a county line, or no longer ours, is held whole under census_s203_mcd and attached to nothing; both listed |
| D-268 | Literacy is its own artifact, literacy_estimates, read by zip 2's profile |
| D-269 | A proportion of exactly 1 is not_derived |

## Decided in Sprint 06, session 14

| ID | One line |
| --- | --- |
| D-270 | The standard lives in seeds/standards/information_barriers.yml, its shape in seeds/schemas/standard.schema.yml, generic so another domain can declare its own. Each barrier lists sides; a side has a kind (universal, trigger, none), a statement, a source and who declared it, and names the indicators or artifact measures it judges. Barrier membership has its one home there; the registry keeps only role. The pairing table (P-2) is its own seed |
| D-271 | P-1, row by row (P-1 and P-5 closed). Language trigger: the DOJ 2002 safe harbor as rewildingcities' own line, rescinded 2025-03-21, per C16001 group, residents 5 and over: translate at 1,000, or at 5% with 50 or more; written notice of free interpretation at 5% under 50; else nothing written. Section 203 as published, its four-group limit said. Language universal (P-5): every limited-English resident, our line, UNESCO's 2003 multilingualism Recommendation as its principle. Digital universal: every household, the ITU and UN Envoy 2030 household target, the subscription-versus-access gap said. FCC 100/20 terrestrial declared, acquirable until 7b. Literacy universal: every adult 16 to 74 at Level 2 or above, UIS's level for SDG 4.6.1, our line beyond target 4.6's own words. Cultural cues, paywall, outdated, where people look, trusted source: none |
| D-272 | A universal side is judged once, on its left_out count against zero: below when the count less its margin is above zero, within_margin otherwise; meets is unreachable for an estimate, and says so. Literacy by its credible bounds. The side's other indicators carry judged_on, naming the count. D-269's proportion of 1 never reaches a verdict |
| D-273 | Trigger verdicts: crosses, within_margin, does_not_cross, cannot_judge, margin-aware per group; the safe harbor says which tier. A published determination's verdict is as_published: the publisher decided it, we report it. D-263 stands: no verdict of ours rests on section 203's margins |
| D-274 | Profiles are built by a canopy command, never a sows run ($loam names one artifact, D-163; values live in many receipts): one place_profile artifact with its own receipt, listing every receipt it read. place_profile is tier public (Kalli); the gate binds its whole lineage. The profile's own allow record is decided at the publish door (zip 3), never written inside the file it judges; part 5 carries its inputs' refusals |
| D-275 | loam gains views over the literacy_estimates and section203_records receipts' files, keyed by (unit_authority, unit_code), each row naming its receipt; never through place_values (D-268 stands) |
| D-276 | borrowed_from is a list: every coarser place a value comes from, each with its share of residents from the graph's edges (residents, never adults 16 to 74); no verdict and no left_out on a borrowed value |
| D-277 | An uncertainty's confidence comes from its indicator's declared uncertainty (acs_moe: 0.90), held once; a row's own confidence wins (literacy's 0.95) |
| D-278 | left_out means the people short of a universal line, everywhere a reader sees it; place.py's towns-out-of-range property becomes out_of_range (two lines in test_place_reading.py); graph.py's report key stays |
| D-279 | cii_rent_burden, cii_no_vehicle and their cii_pub twins take role need (Contract 4 part 1; neither is an IFL barrier). Only labels and the carriers view read role; the hashes move, so the cousub, district and county runs and the county standings rerun, no fetch |
| D-280 | Part 1's population is the 2020 Census count from the block spine, what every per_1000 divides by; the households' source is read in the build before it is chosen |
| D-281 | Contract 4 moves to draft 0.4 in zip 2, carrying D-258, D-263 and D-270 to D-280 |
| D-282 | Part 4 pairs one measure only: CII's average literacy score and PIAAC's share at or below Level 1 are different measures, shown side by side in the literacy family, never as a disagreement |

## Decided in Sprint 06, session 15

| ID | One line |
| --- | --- |
| D-283 | Tiers: public for the school, health center, section 203 and literacy types and their releases (U.S. government works), and for located_in_edges (adds no limit; points bind through lineage). Outlet and clerk types stay undeclared |
| D-284 | The gate first: a receipt's values enter a profile only if it may leave at public; a withheld one's refusal does; the receipt's inputs are exactly what entered. judge_receipts is the one home of judging a plot |
| D-285 | Part 6 ships present and empty until P-2 |
| D-286 | Part 1's households are the ACS's, the digital count's denominator; its margin is not carried, said so |
| D-287 | A small sample never stops a verdict: the margin decides; the reliability note travels beside it |
| D-288 | Part 4 subtracts only matching units or two percents of one measure; otherwise both shown, no difference |
| D-289 | A trigger is judged over every value its margins allow (verdicts.tiers_within), never only its two ends |
| D-290 | Maine's town and county boundaries take maine_geolibrary_public: 5 M.R.S.A. sections 2004 and 2005, attribution required; the section 1995 reading is Kalli's |
| D-291 | count_located's receipt names the notes its rows carry, so rule 9 binds exactly those |
| D-292 | Every level is profiled: Contract 4's six first, then the MEGIS divisions, as groundwork, saying so |
| D-293 | The places and edges receipts are inputs of every profile; when withheld, the whole file cannot leave, said |

## Decided in Sprint 06, session 16

| ID | One line |
| --- | --- |
| D-294 | Cision is commercial_outlet_listing, excluded; maine_outlet_carriers stacks the three lists by name (use); database_alone none, town_fallback none; Cision's reviews removed (Kalli's cut) |
| D-295 | outlet_listing is aggregate-only |
| D-296 | indicator_values and place_profile declare aggregates: true |
| D-297 | news_outlet, outlet_stack, outlet_groups aggregate-only; municipal_clerk_office, municipal_clerk_list, address_point_release public; the 911 release never a publish target |
| D-298 | The 911 file takes maine_geolibrary_public by D-290's reading; courtesy ask in the wrap-up |
| D-299 | factual_directory (every member, no selection: the clerk list, public) and factual_compilation_counts (a chosen list: counts only, requires_tier aggregate-only, enforced in rule 10); Kalli's readings of Feist |
| D-300 | The ecosystem file is project_own_work, credited to the project; to confirm with Dr. Mittal |

## Decided in Sprint 07

| ID | One line |
| --- | --- |
| D-301 | Kalli's own account, applied fresh, handed to the library as code; us-east-2 on her account, us-east-1 the committed default; the account id out of the repo |
| D-302 | CloudFront with origin access control in front of a private bucket; it reads harvests/* alone (O-1) |
| D-303 | GeoParquet canonical, GeoJSON display copies, GeoPackage on request (O-2) |
| D-304 | Referenced GeoJSON layers for December; a Parquet feature layer a recorded read after (O-3) |
| D-305 | Tests through an injected fake client, no moto; boto3 in environment.yml; old harvests regenerated, never moved |
| D-306 | One stack, canopy/terraform; storage.tf and the December 2025 stack removed |
| D-307 | Noncurrent versions kept |
| D-308 | The writer role: put, get, list under harvests/; every delete denied; no access key (DEPLOY-1 retires the deployer's) |
| D-309 | The bucket policy is the overwrite lock: versions need If-None-Match, current If-None-Match or If-Match |
| D-310 | CORS for any origin, reads only; range headers exposed for DuckDB |
| D-311 | create_budget switches the budget; false on Kalli's account |
| D-312 | The write takes a receipt by name, its data in the plot's own .data, alone |
| D-313 | The allow record beside the receipt, never inside; the receipt byte for byte |
| D-314 | Parquet and JSON as they are; GeoJSON to GeoParquet, twice, format_changed by the canonical write; other formats refused by name |
| D-315 | Target canonical at public; a custom tier refused until O-6 |
| D-316 | The canonical command: a dry run by default; --write one artifact with --by and --reason; bucket and domain from the env |
| D-317 | Data put last; current moved with If-Match; a revert is a move; versions cached a year, current no-cache |
| D-318 | A harvest's name is its receipt's artifact name |
| D-319 | batch.py and docker-compose.yml removed |
| D-320 | Allow records versioned inside their version, named by content less their times |
| D-321 | Display copies drawn by canonical --display from the current version's bucket bytes, under its display/; the canonical command writes them, the door references them |
| D-322 | A copy's name: web for points, web_<tolerance>m for polygons; a name never gets new bytes |
| D-323 | A copy's envelope inherits the version's lineage, notes and chain, records derived_from and its allow record, and its own entry's publication steps; the gate judges it |
| D-324 | Coverage simplification in EPSG:26919 (25 m default); invalid coverage or emptied geometry refused; points count 0; six decimals; EPSG:4326; dates as ISO text, named |
| D-325 | In ArcGIS Online a copy is referenced by URL through Map Viewer and saved in a web map; the Content route imports and is not used |

## Contracts

field-guide/docs/contracts/: 1 tiers and the gate 0.6 (the canonical write as an exit, D-314, D-315); 2 canonical objects 0.3 (D-312 to D-324; open: O-4, O-5 for Sprint 08, O-6 after delivery); 3 geography graph 1.0 (the grove teammate's review owed; CON3-2: section 2 still calls located_in a kind in the edges table); 4 place profile 0.4 (D-281, carrying D-258, D-263, D-270 to D-293).

## Where invariants are held

| Invariant | Held by |
| --- | --- |
| Every town has one contains edge from its county | build_place_edges; tested |
| A block's county is its 2024 town's (BOUND-1) | build_block_spine; tested |
| Shares sum to 1 per chamber, per basis | build_place_edges, check_shares; tested |
| Every district touches a town | by construction (D-161); tested |
| Edge ends exist in places | build_places; tested. located_in: build_located_in refuses a `to` end not in places |
| A point's town is its face's; its districts its block's (D-207) | build_located_in; tests/test_located_in.py |
| A point counts in every area it falls in | build_located_in, count_located; tested |
| Vintages match | build_places (D-162); place_values through seeds/vintages/boundaries.yml (D-170); tested |
| Tribal places carry their note and name their area | build_places; tested |
| Every authority is declared, each level under one | seeds/authorities/authorities.yml; tests/test_authorities.py (D-188) |
| District values keyed by chamber | tests/test_district_values.py (D-176) |
| Only a declared count moves along an edge | canopy/loam/edge_rules.py (D-179) |
| Every indicator's universe is declared | seeds/universes/universes.yml (D-181) |
| A run's copy of a source fact agrees with the source | Orchestrator._validate_source_facts (D-192, D-193) |
| An outlet column not declared is never read | stack_outlet_sources; tests/test_outlet_sources.py (D-201) |
| No outlet match is chosen by row order | group_outlet_records; tests/test_outlet_groups.py (D-202) |
| A located_count asks no acquisition for anything | registry; tests/test_located_count_indicator.py (D-209) |
| An exact count is read apart by its method, never ranged; every value carries its role | place.py; tests/test_place_carrier.py (D-209, D-223, D-225) |
| Carriers are found by role, never by a type flag | IndicatorRegistry.with_role; tests/test_located_count_indicator.py (D-223) |
| A located_count's counted points are its declared type, read once, from edges made in the run | Orchestrator._validate_located_counts; tests/test_located_count_validation.py (D-224) |
| No indicator seed names a release, a plot, or a layer label | registry (a layer key refused); tests/test_located_count_indicator.py (D-224) |
| A count reads one layer's edges and names it | count_located; tests/test_count_located.py (D-224) |
| The API's description and the declaration show one derivation | Derivation.as_dict; tests/test_located_count_indicator.py |
| located_in and carriers are views, never files; a layer in two receipts, or points not found through provenance, are refused by name | canopy/loam/graph.py; tests/test_loam_carriers.py (D-225) |
| IMLS's codes are read from one shared crosswalk, never a plot | prepare_library_points.read_crosswalk; tests/test_library_points.py, tests/test_library_preparation.py (D-226) |
| A release's outlet member and encoding are declared once and the run is held to them | source_facts, Orchestrator._validate_source_facts; tests/test_library_preparation.py (D-192, D-226) |
| A mobile or permanently closed library outlet is never placed | prepare_library_points; tests/test_library_points.py (D-208, D-210) |
| A fixed outlet's structure status is declared, or the run refuses | prepare_library_points; tests/test_library_points.py (D-210) |
| A temporary closure follows a choice its method declares | prepare_library_points; tests/test_library_points.py, tests/test_library_preparation.py (D-211) |
| Every method matches the method schema; a run on one that does not is an error | parsing.load_method_data, Orchestrator._validate_method_choices; tests/test_method_schema.py (D-213) |
| Every primitive a method names resolves in its registry; a recipe uses only declared primitives | tests/test_method_schema.py (D-214) |
| The index routes every method file once, by the method's own id and domain | tests/test_method_schema.py (D-216) |
| Each carrier kind is its own type; institutional_node is gone, with no alias | tests/test_carrier_types.py (D-218, D-219) |
| Every type a registry entry, method, manifest, preparation or experiment names is current: declared, never an alias or a state spelling | tests/test_current_type_names.py (D-220, D-221) |
| A draft wonder composes names current types | wondering._compose_steps; tests/test_current_type_names.py (D-222) |
| A registry entry points at a file that exists and holds code | tests/test_registry_paths.py (REG-6) |
| An indicator's hash covers its own mapping without its rationale: siblings, comments, key order and prose never move it; source, weight_by and scale do | IndicatorRegistry, spec_sha256; tests/test_declaration_hash.py (D-227) |
| A run with no curiosity is told it names none (D-64), and never told to become a preparation it could not be | Orchestrator._validate_kind; tests/test_preparations.py (D-229) |
| A school is placed where NCES's point stands (STFIP), never by its operator; one operated elsewhere is flagged | prepare_school_points; tests/test_school_points.py (D-230) |
| NCES's headerless table is read by declared columns with a quote-aware reader; another field count, a header row or a duplicate NCESSCH is refused; M and N are never values | prepare_school_points, seeds/crosswalks/schools/nces_edge_geocode.yml; tests/test_school_points.py (D-230) |
| A school release's member and encoding are declared once and the run is held to them | source_facts, Orchestrator._validate_source_facts; tests/test_school_preparation.py (D-192, D-230) |
| A count's boundaries travel in boundary_vintage from its edges, never its time; a level's two vintages refuse | count_located, loam place_values; tests/test_count_located.py, tests/test_loam_values.py (D-231) |
| Each publisher is judged on its own levels; only the ACS is refused on a tribal area | loam place_values; tests/test_loam_values.py (D-233, LOAM-2) |
| A tribal area is counted only beside a note that exists; its code and persons are AIANNH plus component | count_located; tests/test_count_located.py, tests/test_tribal_counts.py (D-233) |
| A count's note is said with its number | place.py; tests/test_place_carrier.py (D-233) |
| HRSA's copy is the one declared: its rows' record dates are its day | prepare_health_center_points; tests/test_health_center_points.py (D-232) |
| Administrative, mobile, pointless, withheld, closed and out-of-state sites are listed, never placed; an undeclared HRSA code refuses | prepare_health_center_points; tests/test_health_center_points.py (D-232) |
| The clerk list is read by position under its exact header; names and phones never read | prepare_clerk_office_points; tests/test_clerk_office_points.py (D-236) |
| An office is placed only where a matched 911 point stands, once, by its SITE_UID; a row's code never places | prepare_clerk_office_points; tests/test_clerk_office_points.py (D-237) |
| A match is exact on number, Pub 28 street and ZIP; a C1 form in two groups refuses unless the seed resolves it | prepare_clerk_office_points, seeds/crosswalks/addresses/usps_pub28.yml; tests/test_clerk_office_points.py (D-238) |
| A tie settles only by the building rule or the declared campus choice, and says so on the point | prepare_clerk_office_points; tests/test_clerk_office_points.py, tests/test_clerk_office_preparation.py (D-239) |
| A reviewed match names a standing point, only for a row the run would list, and refuses when no longer needed | prepare_clerk_office_points; tests/test_clerk_office_points.py (D-240) |
| An outlet's id comes from its members, never row order; two that would share one add a line, flagged | prepare_news_outlets; tests/test_news_outlets.py (D-243) |
| A named town always wins; an office town places only by the declared choice and says so | prepare_news_outlets; tests/test_news_outlets.py, tests/test_outlet_carriers_preparation.py (D-242) |
| A town is matched only by declared names; two towns, none, two matches or no town are listed, never placed | prepare_news_outlets; tests/test_news_outlets.py (D-244) |
| A review is keyed by source and name as written, and refuses when its words change or the run no longer needs it | prepare_news_outlets; tests/test_news_outlets.py (D-240, D-243, D-244) |
| An outlet is counted at town, county and state only | build_town_located_in, maine_outlet_carriers; tests/test_news_outlets.py, tests/test_outlet_carriers_preparation.py (D-246) |
| A layer placed by town is left out of the carriers view by name | canopy/loam/graph.py _drawable; tests/test_outlet_carriers_preparation.py (D-246) |
| Every source has a kind; a database type is declared or the run refuses; a program and an unknown class count under nothing | prepare_news_outlets; tests/test_news_outlets.py (D-247, D-248) |
| The medium is judged before the town; a review cannot place an outlet listed for its medium | prepare_news_outlets; tests/test_news_outlets.py (D-248) |
| A statewide outlet is placed in the state alone; a state row naming a town refuses | prepare_news_outlets, build_town_located_in; tests/test_news_outlets.py (D-249) |
| A shared office address lists or flags by the declared choice; ZIPs compared as five digits | prepare_news_outlets; tests/test_news_outlets.py (D-250) |
| A missing value is judged one value at a time, across the csv the run writes between steps | prepare_news_outlets, build_town_located_in; tests/test_news_outlets.py (round-trip tests) |
| The outlet count's time is the listings' declared collected month | tests/test_outlet_carriers_preparation.py (D-252) |
| A name written inverted is one name | group_outlet_records.name_key; tests/test_outlet_groups.py (D-253) |
| One source's record written twice is one record, its key held once, across the csv between steps | group_records; tests/test_outlet_groups.py (D-254) |
| An office address is compared in one place | group_outlet_records.office_key, imported by prepare_news_outlets (D-250, D-254) |
| One source twice in an outlet only by a person's edition merge, said in words | prepare_news_outlets.apply_merges; tests/test_news_outlets.py (D-255) |
| An office read applies only to an outlet placed by its office town; an unread one says so | prepare_news_outlets; tests/test_news_outlets.py (D-256) |
| A town review names a town or the state, never both | prepare_news_outlets; tests/test_news_outlets.py (D-257) |
| Every review is keyed by source and name as written and names its evidence, day and reader | tests/test_outlet_carriers_preparation.py |
| A run leaves a declared source out only by naming the ones it uses | stack_outlet_sources.read_use; tests/test_outlet_sources.py (D-294) |
| Maine's outlets never stack a commercial_outlet_listing, and no review rests on a source the run leaves out | tests/test_outlet_carriers_preparation.py (D-294) |
| A term with requires_tier holds only for a dataset whose own type declares that tier; a requires_tier that is no tier refuses at load | gate.decide, records.load_licenses; tests/test_gate.py (D-299) |
| Outlet counts and profiles leave; named outlets and anything with Cision in its lineage do not; a clerk office leaves as a point | tests/test_tiers_and_terms.py (D-294 to D-300) |
| Every ratio declares its relation; a count adds and subtracts declared cells | registry; tests/test_indicators.py, tests/test_derived_margins.py (D-259, D-260) |
| R and Python derive the same margins to the last bit | margins.py, derive_indicator.R; tests/test_derive_indicator_oracle.py (D-258) |
| A negative radicand takes the ratio formula and says so | tests/test_indicator_preview.py (D-259) |
| The language family is 26 indicators, the "less than very well" cells, under the API's 50 | tests/test_derived_margins.py (D-261) |
| Section 203 is read in its declared encoding, keyed by LANCOUNT, flags copied; an AIAN/MCD row is never a town's value | prepare_section203; tests/test_section203.py (D-263, D-264) |
| A split or vanished Census town is held whole, attached to nothing | prepare_section203; tests/test_section203.py (D-267) |
| A literacy share never travels without its bounds; no index or model takes literacy_estimates | prepare_piaac_skills_map; tests/test_piaac_skills_map.py (D-265) |
| The standard matches its schema, and every barrier indicator has one home in it | canopy/standards.py; tests/test_standard.py (D-270) |
| A universal side is below only when its count less its margin is above zero; never meets | canopy/wonder/verdicts.py; tests/test_verdicts.py (D-272) |
| A trigger names only tiers a value inside its margins could be in | verdicts.tiers_within; tests/test_verdicts.py (D-289) |
| Every profile has all six parts; every barrier value its households_behind; every universal verdict its left_out; every margin its confidence; no standing | canopy/wonder/profile.py; tests/test_place_profile.py (Contract 4) |
| A withheld receipt's values never enter a profile; places and edges are always its inputs | profile.py; tests/test_place_profile.py (D-284, D-293) |
| Literacy and section 203 records are views keyed by place, never place_values | canopy/loam/graph.py _plant_records; tests/test_loam_records.py (D-275) |
| A count's receipt names its rows' notes | count_located.output_metadata; tests/test_count_located.py (D-291) |
| The boundaries' license term permits public with attribution | seeds/licenses; tests/test_license_geolibrary.py (D-290) |
| Only an allowed receipt is written, from the plot's own .data, by its own name | canopy/aws/s3.py prepare; tests/test_canonical_write.py (D-312, D-315) |
| A version is written once; current moves only with If-Match; nothing is ever removed | the bucket policy (D-309), s3.write; tests/test_canonical_write.py (D-317), which also reads s3.py's source |
| The same data judged the same way sends nothing; a changed allow record is written alone | s3.allow_identity, s3.write; tests/test_canonical_write.py (D-320) |
| A GeoJSON converts to the same bytes twice, or is refused | s3.convert_stably; tests/test_canonical_write.py (D-314) |
| A custom tier never reaches the canonical bucket | s3._judge; tests/test_canonical_write.py (D-315, O-6) |
| A display copy comes from its version's own bucket bytes, checked against the sha256 | s3.prepare_display; tests/test_display_copy.py (D-321) |
| A display copy records every change, its points' simplification included, and the gate judges it | canopy/aws/display.py; tests/test_display_copy.py (D-323, D-324) |
| Neighbouring polygons keep one shared edge; an invalid coverage or a vanished geometry is refused | display.draw; tests/test_display_copy.py (D-324) |
| A display name never gets new bytes | s3.write_display; tests/test_display_copy.py (D-322) |

## Open items

Sorted for delivery (Kalli asked, session 8). **Delivery (Kalli, session 8):** the Maine product by 2026-12-01 to 12-11: every place's profile, all five carriers on the map with their toggles and notes (town offices and outlets included, so a geocoder is in scope), the barriers judged against the standard, the publish door, the Docker build. Claude's honest note at session 12's hand-off: step 3 is done, outlets through OUTREV-1; steps 4 to 11 and the door remain, with 16 to 26 days to the window. Kalli's shape (session 12): three zips, each designed in a short consultation, then built whole (see Starting the next session). Step 8's ownership concentration exists (Kalli); the FCC measure (step 7b) is the first cut if the window tightens. The cut is Kalli's to make. Session 13: zip 1 built and run (steps 4, 5, 6, 7a); zips 2 and 3 remain.

### Blocks delivery

| ID | One line |
| --- | --- |
| COVER-1 | The towns outline is not a valid coverage: Gray (2300528870) and Windham (2300586025) disagree along about 75 m near 43.8457 N, 70.3746 W, neither overlapping, each valid alone. Hypothesis, not a finding: Little Sebago Lake's shore after water was clipped (D-142). Repair in build_place_outlines, then a new version of the towns; their display copy and every choropleth on them wait for it. Before Sprint 08's choropleths |
| OUTCONF-1 | Before named outlets publish (counts already may): Kalli confirms the Claude-read reviews still in the seed (read_by): the Castine Patriot and the Boothbay Register placed by newsroom (Castine, Wiscasset count none of their own); whether the Peaks Islander still publishes; Gorham Times, Islesboro Island News, The Irregular, Maine Biz and Maine Wire placed by name. Cision's reads left with Cision (D-294). With the makers' word on Easton's and LNC's lists, named outlets move their tiers and terms (D-297, D-299) |
| WATERFRONT-1 | The Working Waterfront's reading (Rockland, where the Island Institute makes it) waits for a town review naming Rockland's code; until then it is listed no_town_given |
| TRIBE-10 | The clerk note is carrier_seen_on_nations_land (Kalli's draft); the state names two nations' offices as voting districts, and the 911 file spells Passamaquoddy as Pasamaquoddy: both shown only on the nations' terms |
| OWN-1, SRC-4 | OWN-1: ownership concentration exists (Kalli, session 12); confirm against the ledger's OWN-1 and close it. SRC-4 narrowed to named outlets (D-299, D-300): Jo Easton's and Local News Catalyst's word, asked in the wrap-up (to Molly Meller or with the professor's delivery package) |
| P-6 | The FCC benchmark, with 7b: 100/20 terrestrial is declared (D-271); the values wait |
| CARRY-1 | loam's carriers view carries only feature_id, name and coordinates (graph.py, _points_sql): a point's adjectives (seasonal, look_alike, setting, flags) and a count's context_note never reach the map. One generic pass-through, for the toggles and the notes |
| Tiers | Declared in session 16 for the outlet and clerk types (D-297); still none: outlet_disagreements and owner_crosswalk, with NOTE-3, D-173's review and TIERREAD-1 |
| EDGE-NOTE-1 | located_in_edges receipts do not name their rows' notes, so the libraries', schools' and health centers' edges fail rule 9: the carriers map cannot leave until build_located_in writes row_context_notes (D-291's twin) |
| FSCS-1 | A published library count's label: outlets of systems the survey does not count as public libraries |
| SCALE-1 | place.py writes "per 1,000" while the scale lives in the declaration |
| LAYER-1, GJSON-1, D-157 | LAYER-1 closes with D-331's keyed join (zip 8b); GJSON-1 still bounds any reader of the state outline; D-157's notes now travel in the door's descriptions |
| DOORSAY-1 | After a write the door still prints its plan ("would create a web map") above the true outcome line; a finished write should say what it did. Zip 8b |
| DOORCHECK-1 | `unchanged` means the record and the bucket agree; with nothing owed the door signs in nowhere, so a deleted or hand-edited item goes unseen until the next move. A `publish --check` that signs in, reads every recorded item and writes nothing. Zip 8b, if Kalli wants it |
| NAMES-1 | placed_by and review_read_by put a reviewer's name on every public clerk row; Kalli decides before handover |
| DEPS-1, OUT-REG-1 | The Docker build: locust not installed; stack_outlet_sources' registry entry names Maine's listings (Cision's two optional since D-294) |
| RECEIPT-1 | Rerun maine_counties, maine_county_units, maine_governance_units if profiles read them through $loam. |
| E911-1 | Publishing no longer waits on it (D-298); the courtesy ask to the GeoLibrary goes in the wrap-up package |
| TRIBE-7 | The notes' wording is drafted (D-233); it is shown as a draft until the nations' terms settle it, never withheld for want of them |

### After delivery

| ID | One line |
| --- | --- |
| OAUTH-1 | An OAuth sign-in kind for ArcGIS Enterprise portals, where generateToken is no longer the default (D-329) |
| CATALOG-1 | The open catalog target kind (DCAT or STAC) for the open data hub, Sprint 13 (D-326) |
| O-6 | How a version is withdrawn: a person's own removal, a tombstone, a CloudFront invalidation, on the terms of the people the data describes. Until then the canonical write refuses custom tiers (D-315) |
| DEPLOY-1 | Retire the deployer IAM user's access key; deploy from expiring logins after |
| CANON-1 | The old outlets_* receipts (Cision in their lineage) and the eight receipts with no lineage sit in .data and .envelopes, withheld; rerun or remove them |
| CLIDOC-1 | canopy/cli/__init__.py's docstring lists neither map nor acquire |
| BCAST-1 | A media database's radio and television stations count only where a local news list holds them; an FCC authority could say which air local news. Said in the method's interpretation |
| SRCFACT-2 | D-192 holds a run to one input's source facts; the outlet count's time is held to its five listings by a test until a many-input step can be held the same way |
| JOIN-1 | loam's join grammar knows a key's name, never its issuer; HRSA rows carry three issuers (BPHC, the grantee number, CMS's NPI). Nothing reads joinable() for carriers |
| GEO-2 | The Census Geocoder as second authority; the first read of the 74 misses leans against it (suites, highway names, suffix-less streets) |
| GEO-3 | D-237's GeoCode check needs a MEGIS GEOCODE to Census GEOID link; not built |
| ARC-1 | canopy/providers/arcgis.py pages by offset with no orderByFields and no held-still guard; off the clerk path since D-235 |
| KIT-2 | A shared points kit (member and encoding, state field, key, placed or listed, an issuer per key) was weighed and deferred: little gain before delivery, a retrofit's cost now |
| PLOT-2 | `city:` in preparations, manifests and sows' header ("City: Maine") should say plot: a schema key across the experiment and manifest schemas, every plot file and their readers |
| HRSA-1 | HRSA's metadata workbook is not read; the geocode's datum is unknown. HPSA, MUA/P, Health Sites and AHRF are catalogued in seeds/sources/hrsa.yml, unused; whether Health Sites sees the nations' clinics is unread |
| TRIBE-9 | The Census names 0115T "Aroostook Band of Micmac Trust Land"; as far as Claude knows the nation now calls itself the Mi'kmaq Nation. Verify, and decide on the nations' terms how a Census name and a nation's own name are shown |
| ACQ-7 | A url release declares its expected hash in source, and a fetch that does not match is refused; receipts already hash every input (md5, full_file), so a change... The rest of the line was lost in a broken paste; restate it from where it was defined |
| CHAIN-1, STAND-1, SCHEMA-1, SCHEMA-3, CHOICE-1, INTERP-1, QUADRAT-1 | As in the ledger |
| LIB-2, SERVES-1, OBS-1, P-3 | A second library authority; whom a carrier serves; our own observation of outlets; the free-outlet question |
| CON3-2, KIT-1 | Contract 3's wording; freshness never judges primitive code |
| P-8 | Section 203 on Wabanaki places, and what is shown on them: the nations' to decide, under CARE and OCAP. Never a deadline |
| P-2 | The pairing table: cited research, then Kalli's table; part 6 ships empty until then (D-285) |
| LIC-2 | The boundary layers' own item metadata (METWP24P, CNTY24P) is unread; D-290 rests on the statute and another GeoLibrary layer's credit line |
| GAPS-1 | Part 5's gaps in the method authors' own words, from readiness and possibility |
| NOTHR-1 | A no_threshold verdict says "this value is shown" when the entry is empty or withheld |
| PROF-1 | read_place loads the registry three times a call: most of a full build's five minutes |

### Not yet sorted (look each up in the ledger)

S2-1, GATE-2, GATE-3, MAP-8, MAP-9, TRIBE-4, SEN-1, LEGI-1, LEG-4, LIC-1, KEY-1, XCHK-1, COMP-1, REG-1, LOOP-1, ACQ-6, SCH-5, TAG-1, MEGIS-3, LURC-1, BAXTER-1, DISS-1, METH-1, LIN-2, VER-1, NOTE-2, TRIBE-5, PENOB-1, RESOLVE-1, SEAM-2, DAS-1, HIST-1, SRC-3, USE-1, SPEC-1, COUNT-1, TENURE-1, TRIBE-6, LEDGER-1 to LEDGER-3, ROLE-1, the draft notes. TRIBE-4 and SEN-1 are dated (2026-12-02) and block maine_seats.

Closed in session 8: SURVEY-1 (D-231), LOAM-2 and TRIBE-8 (D-233). Opened: CARRY-1, KIT-2, PLOT-2, HRSA-1, TRIBE-9; ACQ-7 carried in from an uncommitted ledger line.

Closed in session 9: GEO-1 (D-234 to D-239), TOWN-OFF-1 (D-236). Opened: E911-1, GEO-2, GEO-3, GEO-4, ARC-1, TRIBE-10.

Closed in session 10: GEO-4 (D-240), WHERE-1 (D-241, reopened and settled by D-242 to D-246). Opened: MEDIUM-1, OFFTOWN-1, OUTREV-1, UNDATED-1.

Closed in session 11: MEDIUM-1 (D-247, D-248), OFFTOWN-1 (D-250), UNDATED-1 (D-252). Opened: EDITION-1, BCAST-1, SRCFACT-2. OUTREV-1 carried with its queue.

Closed in session 12: EDITION-1 (D-255), OUTREV-1 (D-253 to D-257, the reviews seed). Opened: OUTCONF-1.

Closed in session 13: P-7 (D-265). KEY-1 now carries the key's replacement.

Closed in session 14: P-1, P-5 (D-271).

Closed in Sprint 08 session 1: CLIDOC-1, ADOPT-1 (the door made its own item), O-4 (D-327), O-5 (D-328), F1, F2, F4, F5, F6 in the shape the door has (D-326 to D-333; the joined copies' counts with D-331). Opened: OAUTH-1, CATALOG-1, NAMES-1, DOORSAY-1, DOORCHECK-1.

Closed in session 15: the boundaries' terms (D-290), the counts' rule 9 gap (D-291); Tiers in part (D-283). Opened: LIC-2, GAPS-1, EDGE-NOTE-1, NOTHR-1, PROF-1.

## Working agreement, as it stands

- Never build against a schema or part of the codebase not yet read (Kalli, session 13): before any code, Claude lists every contract it must satisfy (envelope and metadata schemas, method, experiment and manifest schemas, registries, the readers downstream of what it writes), reads each as it is in the repo, reads every test and caller of what it changes, and says in the consultation what it read and what it could not see.
- Design before code, nothing chosen silently. Small choices: Claude takes the lean and says so.
- Small fixes come inline as guarded helpers in _sprint06/; zips are for builds (session 13).
- Sessions are consultations for a zip (Kalli, session 12): a short consultation per step (what the zip holds, forks with leans, what only Kalli or her machine supplies), then one ambitious zip that builds it all on her go. A zip can hold any amount of code; it cannot hold data her machine must fetch, her decisions, or terms not yet read, and each consultation names those three.
- Claude may read public sources and draft reviews from them (session 12): each cites the page read, read_by says Claude read it, and Kalli confirms before publishing. Claude's guesses are never evidence; a page read and cited is.
- Four forks to a decision tree (Kalli, session 10): Claude reads what the forks rest on first, lays out the tree with a lean, the problems and how to make each better, workshops it with what the reads show, then drafts one holistic zip that fixes everything found, on Kalli's go. A fork that rests on data waits for its read. The guards stay: diff-stat counts, guarded helpers, a receipt read after every real run.
- Questions only when the build needs the answer (Kalli, session 10).
- Until the product is delivered (Kalli, session 7): Claude drafts all code, primitives included, as zips, once Kalli says go. Kalli drives the terminal herself to learn it: unzip, helpers, diffs, tests, dry runs, runs, receipt reads, guarded commits, push, each command explained in plain words. After delivery she returns to writing code.
- Diagrams carry description and fun metaphors; responses stay readable, short sections (Kalli, session 7).
- A fork lists only options that could win. An option already refused, or one nobody would choose, is not listed (Kalli, session 5).
- Go in the plan's order unless Kalli says otherwise.
- Drift is fixed when it is found, never deferred to a later fork (Kalli, session 2). When one truth is written in several places, it gets one home and the others point to it.
- Everything in seeds/ is shared by every plot: reusable, never tailored to one project, possibly international someday. Domain logic gets no top-level seeds/ folder of its own (Kalli, session 2).
- A type is declared before anything names it, and a declaration names a current type (D-220). The walks in tests/test_current_type_names.py hold every plot to this, so drift fails a test instead of hiding.
- Rule or choice: ask whether a reasonable person could decide it the other way. No: a rule, held by a test. Yes: a choice, declared in the method and recorded in the receipt.
- Before any threshold or external claim, Claude researches and cites what a source actually says, in the vintage the build uses, and says plainly where a source gives no number.
- When Kalli says a concept is unclear, Claude explains it from the ground up, with a picture where one helps, before asking anything of it.
- Changes come as a zip of repo-relative files (Kalli's preference), unzipped from the repo root with `unzip -o ~/Downloads/<n>.zip -d .`; small files and every ledger block come inline. Inline files are `cat > path << 'EOF'`, one file per paste, every `EOF` at the left edge. A file Claude has not seen whole is changed by a guarded helper in `_sprint06/` that writes nothing unless its anchor matches once; the helper folder is deleted after.
- Whole-file replacements; `git --no-pager diff --stat` is read before anything runs.
- Every commit block is guarded and names its files: a zsh array, `git add -- $files`, then `git diff --cached --quiet -- $files` prints STOP when nothing changed, and `git commit -- $files` keeps anything else out.
- Ledger blocks appended with cat >>, each starting with a newline. Grep every new ID first. No em dashes, no inline shell comments.
- Before changing a signature, search the keyword across every caller and test, then read each hit for meaning.
- Read real output as its reader would before committing a telling. A receipt is read after every real run.
- Usage: one step per chat; state.md is the only upload at the start; long output is filtered (`| tail -3`, `| grep`); Claude names exact files and asks for whole files rather than many line ranges.
- When Claude needs several repo files, it gives a `zip` command so Kalli uploads one zip (`-j` only when no two files share a name). The zip is written to ~/Downloads, never the repo root: the repo is public, and session 10's two context zips sat untracked there until deleted.
- A data check is a "read", never a "probe" (Kalli, session 8).
- Every long paste runs alone, and after any heredoc append the expected line count is read in `git --no-pager diff --stat` before committing (session 9: one paste lost its middle, one landed twice).

## Traps

- /mnt/project in Claude's sandbox is a partial snapshot, refreshed 2026-11-13 before session 4's edits; some files in it are empty and others are missing. The repo is on Kalli's machine, and a file to be edited is read from her copy or changed by an anchored helper.
- Run everything from the repo root. An unzip from field-guide/docs once made second copies of soil/ and tests/ there, and pytest refused the duplicate test names.
- Run a preparation with `python -m canopy.cli sows <run.yml>`; `--dry-run` only validates. `sows` prints nothing until the run ends. Never `--resolve-only` casually (RESOLVE-1).
- Do not run maine_seats on real data before 2026-12-02.
- A canonical write is public and permanent. Dry-run it, write one artifact, then read the pointer with curl and the data with DuckDB, using the two commands the write prints.
- Output saved to a file is buffered while errors are not, so a traceback can sit far above where a run died, and `tail -1` shows the last line printed. canonical --all prints line by line; other commands may not.
- In ArcGIS Online, adding a GeoJSON through Content, New item, imports it: an uploaded copy, a hosted feature layer offered. A display copy goes in through Map Viewer's Add layer from URL and is saved in a web map (D-325).
- A curl -sI answer names no URL: the URL is the one given to curl, and the one the display write prints.
- A block Claude draws that is not a command is drawn so it cannot run. One pasted diagram reached zsh in session 2 and was refused whole, harmlessly.
- `authority` means only who assigns a place's code; a publisher is `published_by` everywhere, manifests included.
- `$indicators.<id>` resolves to the declaration as a primitive receives it (as_declaration), with declaration_sha256 taken over the indicator's own mapping without its rationale (D-227). Adding or editing a sibling, a comment or a rationale moves no receipt; editing source, weight_by, replicates or the derivation does, and so does moving the indicator to another file (declared_in). as_declaration omits source, weight_by, replicates and rationale: the hash is what lets freshness see the first three.
- A preparation uses soil/ primitives only and a preparation method; a run with a roots/ step or an analysis method is an experiment and names its curiosity (D-98, D-228). `curiosity: ref: ""` is a warning, never a pass.
- Two functions are named read_envelope: canopy.envelope.read_envelope returns an Envelope object (what freshness's judge reads); canopy/loam/envelope_reader.read_envelope returns a dict and needs a vocabulary.
- Origin can move between sessions (session 6: four commits by other authors). Before pushing, `git fetch` and read `git --no-pager log --format='%h %an %ad %s' --date=short main..origin/main` and `git --no-pager diff --stat main...origin/main`; rebase only after reading them. Never `git add .`: in session 6 it committed a stray environment.yml edit under another commit's message.
- The indicator registry globs every seeds/indicators/*.yml as indicator declarations, names flat and global across files (registry.py, line 199). Put nothing else in that folder.
- A run's `$choices.<name>` reaches a step as the raw value. A choice outside its method's options only warns (CHOICE-1), so a primitive that depends on one refuses a bad value itself.
- A step's outputs are `name: type`; the type is a current semantic type, never `<thing>_validated` or `_checked` (D-220). Validating or reprojecting keeps the input's type. The experiment schema's example now says so.
- Vocabulary.get_tier reads `tier`, not `resolution_tier` (TIERREAD-1): do not rely on it for a type's exposure tier.
- `imls_pls_fy2024_outlets` is a located_in layer label set in maine_libraries, not a manifest dataset or a type. The indicator names `counts: library_outlet` (D-224); a `layer` key in an indicator seed is refused by name. The label reaches the receipt as count_located's counted_layer.
- IMLS's outlet types and structure statuses live in seeds/crosswalks/libraries/imls_pls_outlets.yml (D-226). A plot never declares them; a release's member and encoding go in its manifest entry under `source:` (outlet_member, outlet_encoding), and the run's copy must agree (D-192).
- seeds/sources/ is read by no code, by design (D-226): a catalogue there is reference only, and a test holds that imls_pls.yml's pointers exist.
- The carriers view needs each carrier's points file to carry its receipt's id_field and a `name` property, and finds the points through the edges receipt's own provenance record (the newest without lineage_branch). A new carrier preparation writes both (D-225). A carrier placed by town (outlets) is a table, and the view leaves it out by name (D-246).
- pandas reserves `.flags` on a Series and a DataFrame: a column named flags is read by key, `row["flags"]`, never as an attribute.
- group_outlet_records numbers groups by row order (g0001...): a group id is never an identity. Outlets are keyed by their members (D-243), reviews by source and name as written.
- The outlet stack, groups and outlets are CSV in plots/maine/.data; the edges and counts are parquet. maine_outlets and maine_outlet_carriers each stack and group under their own step ids.
- outlet_sources.yml changed in session 10 (source_order, operating_vocabulary), so maine_outlets' own receipts read stale until it is rerun; nothing reads them.
- place.py reads indicators through IndicatorRegistry: a root with no seeds/indicators refuses, where the old raw-YAML walk returned nothing in silence.
- `git grep` and `git diff` open a pager that can cut output at "...skipping...": use `git --no-pager grep` and `git --no-pager diff`.
- A method is read only through parsing.load_method_data (D-213). Options are a mapping keyed by option id (an empty value allowed), requires_primitives a list of layer/name, produces a list; a field the schema does not describe is refused. canopy/wonder still reads methods raw (SCHEMA-3). A method's name lives in the method, never the index (D-216).
- `git rm` stages a deletion; a later `git add` naming that path fails the whole add and stages nothing. Name an already-deleted path in `git commit -- ...` only.
- `| tail -3` prints nothing until pytest ends, about two minutes for the full suite; the terminal is not frozen.
- Claude's sandbox shell is dash: no brace expansion, so `mkdir a/{b,c}` makes one literal folder and once shipped it in a zip. Claude uses `bash -c` or one path per argument.
- loam's `edges` view is made from exactly one `place_edges` artifact (D-163); never write a second. Point edges are `located_in_edges` (D-207).
- loam's place_values attaches a value only when seeds/vintages/boundaries.yml holds a rule for its `published_by`; it reads the ACS's `levels` for every publisher (LOAM-2).
- The 2024 faces are a zip of county zips (plots/maine/.data/maine_faces_2024.zip); build_block_spine reads their .dbf only, build_located_in their geometry.
- The IMLS outlet file is Windows-1252: declared, never sniffed. A pandas read that falls back silently would have written a control character into two names.
- The FY 2024 outlet file holds no STATSTRU 03: permanent closures are listed outside it (its documentation's Appendix C). Older files kept such records.
- `grep -c` counts lines, and a GeoJSON file is one line: a 1 means at least one match. Read features with python, never by counting.
- A test loading a soil module by file path must register it in sys.modules before exec when the module defines a dataclass.
- The envelope schema checks metadata types (a point layer's total_area_m2 is 0.0, never null); fixture tests do not see this (SCHEMA-1).
- MEGIS Maine Town Points (METWP24PT) are town centroids, not offices: refused as a carrier layer.
- Freshness never judges primitive code (KIT-1), and is judged only when a run reaches a `$loam.` input. The read-only probe: build an Orchestrator on any Maine preparation, then `judge(read_envelope(p), orch.project_root, orch._declared_params)` for each file in plots/maine/.envelopes.
- `wonder --place` takes a key, AUTHORITY:CODE, never a name. A town range is one estimate per town; read the firm range before quoting a range's ends. A carrier has no range.
- A step's `outputs:` gives names, not paths. Receipts are `.envelopes/<step>_<o>.envelope.json`.
- The geography graph preparation declares `vintages` twice; change both together (D-162).
- Scope every grep: quote globs, and never grep `plots` without `--include="*.yml"`. `git diff` opens a pager; use `git --no-pager diff`. It is `git status -sb`, one dash.
- Keys live in Kalli's environment only (KEY-1). The repo is public. garden/reference/ and **/.data/ are ignored; commercial listings never leave them.
- The sandbox lacks pytest, pyarrow, shapely, geopandas, duckdb, jsonschema, pyogrio and R; it has pandas and yaml. A small stand-in for pytest.raises lets pure-pandas tests run there.
- NCES EDGE's text table has no header row; its 23 columns come from the crosswalk, and a field holding a pipe is quoted: read it with a quote-aware reader, never `split("|")`.
- Three state fields in EDGE mean three things: STATE the reported address, STFIP where NCES's point stands, OPSTFIPS who administers the school (59 BIE, 63 DoDEA). Place by STFIP (D-230).
- A located_in edge's `to_authority` is not its level: us_census_geoid holds state (2 digits), county (5) and town (10). A per-drawer check groups by authority and code length; by authority alone it reads 3 for one card per drawer.
- A dashboard export (Maine DOE) is not a release: a fresh export is a new source, and only our copy is evidence. Its file name's number is the export time in milliseconds since 1970, UTC.
- `loam`'s `joinable()` relates holdings by key name, so every carrier's feature_id looks joinable to every other (JOIN-1).
- A count's boundaries are boundary_vintage, never its time (D-231): write `time` as what the source describes (FY 2024, SY 2024-25, a snapshot's day).
- HRSA's three state fields: Site State Abbreviation (the site), State FIPS Code, Health Center Organization State (the grantee's office, never where a site stands). Rows HRSA holds with no site state read XX, with no point.
- The spine stores a tribal area as AIANNH (four digits) plus aiannh_comptyp (R, T); a place's code is the two joined (2760R). Group by the bare code and a reservation merges with its trust land.
- A count_located step at the aiannh level must name tribal_note; tests/test_tribal_counts.py walks every plot.
- `Data Warehouse Record Create Date` is the day of HRSA's copy, not of any site.
- The loam carriers view does not carry point properties beyond id, name and coordinates (CARRY-1).
- The ledger is field-guide/docs/build_ledger.md, underscore. A grep on a misspelled path prints nothing, exactly like a clean grep.
- The 911 FGDB and the live FeatureServer are not one dataset: 798,422 points against 801,786, older field names (STREETNAME, SUFFIX) against NENA's (ST_FULLNAME). Only the file is read.
- PLACE_TYPE in the 911 file defaults to Residential and is set town by town: never evidence of a use. Government - Municipal holds salt sheds and a snowmobile club.
- The Secretary of State's clerk CSV names five columns twice; pandas renames the second copies (.1). The primitive reads by position with the csv module.
- pyogrio opens the .gdb.zip directly; leave the zip whole, it is the evidence.
- The clerk list's GeoCode means the row's own town on most rows and its serving town on three; it is blank on 17.
- pandas 3 reads a column of text and blanks as str, and Series.map over it turns a returned None back into NaN: never test a mapped Series value with `is None`. Judge each value with _text, one at a time. A test that hands a table from one step to the next in memory never sees this; round-trip it through the csv the run writes.
- Cision's ZIPs lost their leading zero in a spreadsheet (Maine's 04282 reads 4282) on some rows; compare ZIPs as five digits, and never take the first five digits of a stripped ZIP+4.
- The carriers' own stack and groups are carriers_stack_stack.csv and carriers_groups_groups.csv: a glob for *outlet* misses them and finds maine_outlets' stale copies (926 records either way; session 10's 924 was a miscount).
- Session 10's hand-off wrote state.md to a root file named PATH: a heredoc's path is read in the diff-stat before it is trusted.
- _sprint06/ holds read helpers only; delete it at the session's end, never commit it.
- Listed outlets live in the receipt (metadata.listed_outlets), never the csv, which holds placed outlets only. Session 12's first read helper looked in the csv and read "absent" for "listed".
- A read of the outlet csv taken before a sows run reads the old run: the review checker's watch list did, and showed the Boothbay paper twice after it was merged.
- A review names a record by source and name as written; a name a source writes twice alike (same_record_as) is named once, and a name the run shows is its first member's by source_order (local_news_catalyst, then maine_media_ecosystem, before cision).

- Every receipt's metadata carries crs (null for a table): the envelope schema requires it, and fixture tests never see it (SCHEMA-1).
- R's derive_indicator grows `needed` with the rests_on cells partway through its loop: a count's margin and emptiness read the count's own cells only.
- Section 203's town rows write county 000: towns join by the five-digit MCD; its map is 2019-era, so towns since deorganized appear under old codes.
- The Skills Map file writes Lit_P1, not LIT_P1; its State sheet carries fewer flag columns than its County sheet.
- acs_state_2024 and acs_state_2024_language hold all 52 states: the API's state level cannot be narrowed; only Maine's row attaches.
- macOS sed edits in place with `sed -i ''`.
- A receipt is named for its step and output (`county_language_derive_values`), never its type: find receipts by the semantic_type inside them, never by a pattern on the type's name (session 14's first find missed ten).
- Claude's sandbox python glob skips dot folders: `glob('**/*.json')` never sees `.envelopes`. Glob inside the folder.
- `left_out` meant three things before D-278: towns out of a range (place.py), receipts out of a view (graph.py's report) and people short of a line (literacy). Read which before using the word.
- CII's literacy is an average score; PIAAC's is a share at or below Level 1. Same subject, different measures (D-282).
- loam views only indicator_values; literacy_estimates and section203_records have no view until D-275 is built.
- A shell export pasted across two lines exports a different name: check with `python -c "import os; print(bool(os.environ.get('CENSUS_API_KEY')))"`.

- A declared outlet source is left out of a run by stack_outlet_sources' use, never by dropping its input: the stack refuses a used source with no input and an input it does not use (D-294). maine_outlets still stacks all five and is stale; nothing reads it.
- `"cision"` in a carriers receipt is expected: the shared declaration rides in as params and the stack warns which declared sources it left out. Read input types and data_resolution for lineage, never a text search.
- A merge needed only because one source held a record twice refuses as no longer needed once that source leaves (D-240): remove it then, never before.
- The profile command prints its progress to stderr and its summary to stdout; `> file` keeps only the summary. `--place` prints one profile's JSON and writes nothing.
- The gate reads the manifest's licenses at judging time: a license change needs no rerun; a receipt's own metadata does.
- A level outside Contract 4 is profiled with place.level_note (D-292); a test counting profiles counts every level.

## People

Kalli delivers the whole product: every sprint, the publish route (Sprint 08) and the infrastructure (Sprints 07 and 10) included. The people once named here work on other things (Kalli, session 5). bash-win and Jessica Pham are helpers Kalli recruited, who join her weekly lab sessions; their commits on 2026-11-14 brought staging Terraform, API load tests and plot locks, the Docker image and NYC fetch dates. DEPS-1 likely came with their locust tests (7afefd1); whether DEPS-1, KIT-1 or OUT-REG-1 move to them is Kalli's to say, and until she does they stay hers. Items that were theirs are hers now: LAYER-1, GJSON-1 and D-157's required notes argument for the publish door; DEPS-1, KIT-1 and OUT-REG-1 for the Docker build; the tier declarations, note wording, NOTE-3 and D-173's review. P-8 and TRIBE-7's wording wait on the Wabanaki nations' terms (open items).

## Starting the next session

Upload this file only. Claude reads it whole, the retrospectives first, confirms, and asks for what the next step's design needs.

**Next: zip 8b, Sprint 08's second half.** One consultation, then one build:

- D-331's choropleth: canopy/choropleth.py (the join moved from map.py, keyed by declared authority, closing LAYER-1), `canonical --display --join`, the wide copy, and the door's classBreaks renderer. Then the three county receipts written canonically, their joined copy drawn, and broadband published to `test`.
- A `library` target in plots/maine/publish/targets.yml: its folder, sharing level and groups are Kalli's to name; the owner is RDS_NU.
- Zip 3b's list: CARRY-1 with EDGE-NOTE-1, the two-artifact outlet layer, the test that no manifest dataset reaches the door, DEPS-1, OUT-REG-1, NOTHR-1, PROF-1 if cheap.
- DOORSAY-1, and DOORCHECK-1 if Kalli wants it.
- COVER-1 before any town choropleth.

**Zip 8b's consultation needs.** No zip command for zip 3b's reads was ever recorded (825e32e holds only the ledger and this page), so the list is built by `git --no-pager grep -l` on each identifier the change touches, never a keyword or two: `_points_sql` and canopy/loam/graph.py (CARRY-1); build_located_in and row_context_notes (EDGE-NOTE-1); the outlet counts and news_outlet (the outlet layer); Dockerfile, environment.yml and locust (DEPS-1); soil/_registry.yml's stack_outlet_sources (OUT-REG-1); no_threshold in canopy/wonder/verdicts.py (NOTHR-1); read_place in canopy/wonder/place.py (PROF-1); `_join_and_color`, `long_form_view` and `_UNIT_KEYS` (D-331); canopy/aws/display.py, canopy/aws/s3.py, canopy/cli/canonical.py and the door's files as they stand; seeds/standards/information_barriers.yml for the renderer's declared breaks.

## Sprint 08 session 1's notes (the door's consultation; zip 8a built and run)

- What went right: the reads came before every lean that rested on them (the code, the contracts, the ledger, the hand-made web map's own JSON, the dry runs, Esri's documentation); the door was tested against a fake portal before it met a real one, and the real one answered every call the way the fake did; the first write made one item and the second owed nothing.
- Wrong hypotheses: that the door would use Esri's arcgis package; that it might own a layer item beside the web map; that targets belong at repo level; that the door's gate decides exposure; that Map Viewer's JSON was the shape to copy; that the P items needed a new prefix; that an unhosted layer could not be saved; that a flag not yet built could sit in a runnable block (`--join` was run and refused).
- Lessons: label a command that is not built yet as after its zip and never draw it runnable; read the hand-made thing before writing its shape, and keep what a person chose; a referenced layer is as public as its URL; a broken button can be a stale page, so read the console first; a pointer that moves can be mirrored by every place that shows it, each mirror moving the same way.
- Session shape: one long chat held the plan, three reads zips, the contracts, the ledger, the ArcGIS reads, the consultation, the build, the run and this hand-off. The hand-off rule stands: zip 8b starts fresh from this page.

## Sprint 07 session 2's notes (zips 7b and 7c built and run; the first canonical object; the first web map)

- The reopening: Claude called Sprint 07 closed (d67ccb3) against this page's audit table, not the Master Plan tab's done-when, and wrote "closed" into this page and the progress report. Kalli asked "are you sure?"; the tab was read; the web-map half was missing, and Kalli chose to reopen and finish rather than move it to Sprint 08. A sprint closes against its own tab's done-when.
- Zip 7c's first dry run crashed on a Timestamp the clerk points carry (review_read_on): the display path had not inherited zip7b2's "an error is a refusal" fix. The same lesson twice: a new path inherits the old fixes or repeats the old crash.
- The towns' guard worked: the coverage check refused the copy rather than draw a crack between Gray and Windham (COVER-1).
- The whole suite was skipped four times before permanent writes in this session; nothing broke, and it stays the rule.

- What went right: the reads came before every lean that rested on them (the receipts' formats, the real envelope schema, two real receipts); the dry run was read before any write, and it found a crash and a design gap while both were still free to fix; the first write wrote exactly four keys in order and read back 392 through CloudFront.
- Wrong hypotheses: that a writer refusing all but Parquet stays useful; that a traceback's place in a saved file is where the run died; that tail -1 shows how a run ended; that an allow record could be written once per version.
- Lessons: read what a writer will meet before deciding what it refuses; an identity names only what cannot change without the thing changing; a batch read reports each surprise and goes on; run the whole suite before anything permanent.
- Session shape: one chat held the repo check, both reads zips, three builds, two dry runs, the first write and the hand-off. The hand-off rule stands: a long build starts fresh from state.md.

## Session 16's notes (zip 3a, built and run; Sprint 07 audited)

- What went right: the reads came before code twice (zip 3a's surface, then the ledger's own shape); the gate's three locks were found by reading decide() rather than by a failed publish; every refusal the run gave was loud and named its review.
- Wrong hypotheses: that Cision alone made The County's merge need editions; that named outlets would be one tier change; that a read after a failed run shows the new run (it showed the last good one, twice).
- Lessons: a read reports whatever ran last, so check a receipt's time against the run first; keep a merge whose need is in doubt, since it refuses loudly when no longer needed; a stack that refuses a missing input needs a named way to leave a source out.
- Session shape: one long chat held the plan, the Sprint 07 audit, zip 3a's consultation, build, two fixes and commit. The hand-off rule stands: a long build starts fresh from state.md.

## Session 15's notes (zips 2 and 2b, built and run)

- What went right: the consultation read 217 files before any code; the pure rules (verdicts, the standard's name checks) ran in the sandbox before the zip; the bed-backed tests were modelled on test_loam_values' own beds; 69 new and moved tests passed on their first run.
- Wrong hypotheses: that the full build hung (it was silent); that place_values' view made reads slow (0.0s); that a trigger's two margin ends bound its tiers (D-289); that only the outlets would be withheld (one license held the whole graph); that Contract 4's levels needed no filter.
- Lessons: a long command prints its progress; an input is anything a file holds, names and shares included; read the law's own text for a license and name a reading as a reading; `tail -60` can hide the line that matters, so filter for the lines wanted.
- Session shape: one chat held a consultation, two builds, two runs and the license research, and reached its tool limit once mid-build. The hand-off rule stands: a long build starts fresh from state.md.

## Before a build: session 13's retrospective

Every failure of session 13, sorted by cause, so the next build avoids them.

- Contracts unread (preventable): a receipt lacked crs (the envelope schema requires it; SCHEMA-1 warned); the oracle's row count assumed three indicators; test_district_values' table list and test_honest_values' D-18 premise were never read. Fix: the reads zip names every schema the output passes through and every test found by `git grep -l` on each identifier the change touches (module, function, field, manifest entry, preparation, and each decision whose premise changes), never a keyword or two.
- Untestable code read too lightly: R's needed grew with the rests_on cells and was reused for a count's margin. Fix: Claude reads every R branch it writes against its Python twin line by line, since the sandbox has no R; Kalli runs the oracle first.
- Documentation trusted over the file: cp1252 not ASCII, LANGUAGE text, Lit_P1 casing, county 000 on towns. Fix: read the file's bytes and rows before declaring anything; documentation is a hypothesis.
- Refusals decided without their real cases: unmatched Census towns refused though the file's 2019-era map was known. Fix: for each refusal rule, name the real rows that would hit it, from a read, before choosing refuse or hold.
- Numbers stated, not computed: 1,148 tests (1,166), a 58-line ledger block (44). Fix: compute in the sandbox or say about.
- Reads that hid their answer: head(20) cut a list; -rs hid FAILED lines; a one-liner printed a character count. Fix: count, then list; hunt failures with `python -m pytest -q --lf 2>&1 | tail -8`; one-liners print explicit words.
- Terminal and files: uploads not attached (say "attach X to your next message"); file names guessed (run find first); a missing package (check imports before a read); a key export split across two lines (keys live in conda env config vars, never pasted).
- Session shape: a long consultation chat hit the tool limit mid-build. Fix: the consultation ends by naming its reads zip; a long build starts fresh from state.md.
