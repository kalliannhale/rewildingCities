# Sprint 07 ~ storage outside AGOL: progress report

**Closed:** 2026-11-17, after zip 7a (session 1) and zip 7b with its two fixes (session 2). **Domain:** infrastructure. **Contracts:** 1 at 0.6, 2 at 0.3.
**Tests:** 1,289 passed. **Decisions:** D-301 to D-320.

## The goal, and the answer

The audit's last row: "DuckDB reads the canonical GeoParquet through CloudFront." It does. `python -m canopy.cli canonical maine clerk_offices_points_points --write` asked the gate, converted Maine's clerk offices from GeoJSON to GeoParquet twice and got one sha256, and wrote four keys in order, the data last. `curl` read the pointer through CloudFront: version 0b91cb0caae7, allow record 33ce1ddb61dc, moved by Kalli A. Hale with her reason. DuckDB's `read_parquet` over the CloudFront URL counted 392 offices. The feature storage that AGOL could not hold now lives in a bucket that cannot overwrite what it holds and that anyone can read by URL.

## Built, against the audit

| Row | What exists | Decisions |
| --- | --- | --- |
| A least-privilege identity for the canonical write | the role rewilding-canonical-writer, assumed through the rewilding-writer profile: put, get and list under harvests/, every delete denied, no access key | D-308 |
| One stack | canopy/terraform, staging moved up; storage.tf and the December 2025 stack removed, kept in git history | D-306 |
| Lifecycle | noncurrent versions kept, so every pointer move stays as history; multipart cleanup only | D-307 |
| Public reach | CloudFront with origin access control in front of a private bucket; CORS for any origin, reads only, range headers for DuckDB | D-302, D-310 |
| The overwrite lock | the bucket policy, for every principal: a version needs If-None-Match, the pointer If-None-Match or If-Match | D-309 |
| The canonical write | canopy/aws/s3.py and the canonical command: receipts only, the gate at canonical and public, formats by name, data last, the pointer by If-Match | D-312 to D-318 |
| The tests | tests/test_canonical_write.py, 42 tests through a fake client that keeps the lock and fails on any removal | D-305 |
| batch.py, docker-compose.yml | removed, both empty | D-319 |
| DuckDB through CloudFront | read, 392 | |

## Where the plan changed, and why

- The account was a project inside an organization AWS made through its new sign-up, with a policy refusing S3 in us-east-1. Kalli's copy runs in us-east-2; the committed default stays us-east-1 for the library (D-301).
- GeoParquet stayed canonical (A3, Kalli's choice) once the receipts were read: 21 of Maine's 58 are GeoJSON, among them every outline and every carrier's points. The write converts, twice, and records the conversion (D-314).
- The allow record became versioned inside its version, found before the first write: a version named by its data alone would have frozen the DRAFT tribal notes at a citable URL forever, though TRIBE-7 says they show as drafts until the nations settle them (D-320).
- A custom tier is refused by the writer even when the gate allows it. A version stays readable forever and the writer can never remove one, so a consent withdrawn later could not be honoured. How a version is withdrawn is O-6, decided on the terms of the people the data describes (D-315).
- The first dry run crashed on Maine's state outline, one feature past GDAL's GeoJSON size limit, and its traceback sat 18 receipts above where it died. The limit is lifted for the conversion; failures are refusals; the batch read goes on through any error and prints line by line.

## The numbers

58 receipts in Maine: 28 Parquet, 21 GeoJSON, 8 CSV, 1 JSON. The dry run: 37 may leave, 21 withheld, 0 unjudged. Withheld by rule 5 (the outlet listings, groups and stacks), rule 9 (five carriers' located_in_edges, EDGE-NOTE-1), rule 10 (the old outlets_* receipts, Cision in their lineage), rule 4 (eight with no lineage) and by format (two CSVs). One canonical object written: 392 clerk offices. 20 AWS resources in the stack.

## Carried forward

| Waiting on | Items |
| --- | --- |
| Sprint 08 | display copies (Contract 2, section 4); reference layers by URL (D-304); O-4, the per-target identity record; O-5, how a layer moves to a new version; EDGE-NOTE-1 and CARRY-1; the choropleth, which joins two versions |
| Kalli, as the ArcGIS admin | reading the canonical files by URL in Map Viewer and Experience Builder |
| After delivery | O-6, withdrawal; DEPLOY-1, the deployer's key; CANON-1, the withheld old receipts; CLIDOC-1; the library's own apply, from expiring logins |

## Three lessons worth keeping

- Read what a writer will meet before deciding what it refuses. The first lean would have refused most of December.
- An identity names only what cannot change without the thing changing. A note's text can change while the data does not, so the allow record has an identity of its own.
- A dry run of something permanent is a design review. Both of this sprint's real findings came from reading one, before anything was written.
