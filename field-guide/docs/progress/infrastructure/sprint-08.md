# Sprint 08 progress report ~ the publish door

**Closed:** 2026-11-17, in two sessions. **Commits:** c67a67a, 060bcdd (session 1); 1ba3098, fc773e3, 2ba91e7, 07111bf, 98e4295, d87f324 and the hand-off (session 2). **Decisions:** D-326 to D-349. **Tests:** 1,332 to 1,415.

## What the sprint set out to do

One door publishes every result: through the gate, from the canonical store, to each target a plot declares, updating in place and carrying its provenance. Done when Maine broadband published twice to a test target leaves one layer, pushing to two targets gives one layer in each, and each names the canonical hash.

## What was built

The door is `python -m canopy.cli publish`. It reads a harvest's current version, allow record, receipt and display copy through CloudFront, needs no AWS credentials and no Esri package, judges the copy at each target's sharing level, and makes or moves a web map item over ArcGIS's REST API. Each plot declares its own targets, so a community starting a plot anywhere names its own portal and owner without asking anyone; the door alone keeps the record of what it made, each item mirroring the bucket's pointer the way `current` does. A dry run signs in nowhere. A second push that owes nothing does nothing. `publish <plot> --check` signs in and reads every recorded item against the record, writing nothing.

The second half drew the choropleth. A long-form table now joins a plot's places only by who assigns their codes and what the codes are, never by a name or a code alone, in one module that the local map and the published map share. A joined copy has two parents and says so: it lives under the table's version, is named for the outline's version, carries both provenance chains, and its notes are the notes of the places it draws. Markers draw one point inside each place and simplify nothing, so the outlet counts reached the map before the towns' coverage is repaired. A local dry run draws the exact bytes a write would send, so nothing permanent happened before each copy had been drawn, joined and judged once, and the copy drawn from the bucket had to print the same sha256 before it was written.

## What was published

Broadband's county standing, in fixed fifths of the 3,144 counties with a value, in the test folder and in the library's press-forward folder, shared with the organization. Local news outlets by town, as markers sized in equal steps with "none listed" its own class, in test. The clerk offices in both. Six canonical objects and three display copies hold the truth behind them in the bucket. On the close, `--check` read all five items as recorded.

## What the run found

Every guard built for this run fired on a real case before anything was permanent:

- Two of state.md's receipt labels were wrong: the hash called broadband's was rent burden and vehicle access. Broadband's standing would have gone public forever as `standardize_standings`, the name the method's recipe gives every experiment composed from it. Its steps were renamed and two guards added: a test that no two runs of a plot write one receipt name, which found five such pairs (RUNNAMES-1), and the refusal of an orphaned receipt.
- The guard against a manifest dataset leaving found two receipts whose data files are MEGIS's own fetched layers, passed through by a validate step.
- Rule 11's closed set of publication steps had no word for a join or a marker; it gained two rather than recording a false change.
- The door's first `--check` found that ArcGIS rewrites an item's description as it stores it, so the record of what was sent called every item hand-edited. Zip 8a's design would have refused the first real move of every item. The door now reads each description back and compares what the portal stores.

## Not done, and why

- **MCF and partner targets.** None is declared: neither has given a portal and an owning account. A target is a few lines of targets.yml when one does, and if MCF only needs to see the maps, a share from the library's org does that now.
- **F3, F7 and F8** of the publish route assignment were never found and are not reconstructed (D-334).
- **ArcGIS has never answered a real update.** Every item was made by addItem. The first move is the test (UPDATE-1).

## Going into Sprint 09

The explorer's maps are the door's items, and an Experience Builder app holds them by item id. Because the door moves an item in place when the truth moves, an app built on it never needs rebuilding; an item deleted by hand breaks it, so the explorer is built only on items `--check` reads as recorded. Its layers are joined copies and markers, so every map already carries both parents' provenance and credits, and none uses AGOL feature storage.

Three things the door does not yet do come first. The Maine plan's symbology says darker always means harder access, and the door draws darker as the better standing (RAMP-1), so the ramp turns and a renderer change becomes something the door owes. Every level becomes a lens: counties draw now, towns wait on COVER-1, and the House, Senate and tribal outlines are built but not yet in the bucket. And the profile panel rests on the profiles reaching the bucket as a document, rebuilt first, with the gate's own refusals traveling beside them as what is withheld and why. The credit line and citation are the door's own fields, so one change reaches every item at once.
