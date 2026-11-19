# Building the Maine explorer by hand

The door makes every map. A person builds the app that holds them, in
Experience Builder, from this page. Then the door records the app
(`publish --adopt-app`) and `--check` reads it from then on (D-366). Every
choice made by clicking is written in the build ledger, since a click leaves
no diff (Sprint 09, session 6).

**Words.** A *lens* is the map of one lane (D-386). The *level* is the switch
between towns, House districts, Senate districts and counties. The app never
calls the level a lens.

## Before you start

- The places map is public in the explorer folder: item
  6cdfb76c64bb4a59a1ecf34de17d796d (session 5). Its six layers hold every place's
  told fields.
- Each lens is written to the explorer target: `publish maine --lens <lane> --to
  explorer --write`. `publish maine --check` reads them all as recorded.
- Sign in as RDS_NU. Make the app in the folder **rewildingCities explorer**. An
  app made anywhere else is refused at adoption.
- Never build on read_9a. It is a rehearsal (plots/maine/publish/rehearsals.yml).
- Never delete or save over a door item in Map Viewer. The app holds item ids,
  and the door owns each map whole (D-380). Opening a door map in Map Viewer
  to look is fine; close it without saving. If one is saved by mistake,
  `publish maine --check` says "changed by hand", and the same publish command
  with `--write --restore` writes the door's whole map back into the same item,
  so the app's id still works (D-395).

## Page 1: Explore

1. **Map widget** on the places map. Towns are shapes; every other level is a
   point. Tribal points are drawn on top, so a click on the dot answers the
   nation and a click on the shape around it answers the town (STACK-1).
2. **Search widget** on the places map's layers. Search every level: towns,
   counties, House and Senate districts, tribal areas, the state.
3. **Text widget** for the profile. Connect it to the Search widget's **output**
   data source (Select data, then Outputs), never to the searched layer itself
   (D-350). Read R5 again here: a click on a town shape and a Search choice
   must both move the Text.
4. In the Text, show these told fields, in this order: `name`, `level`,
   `about`, `note`, `represented`, `shares`, `needs`, each `barrier_*` field,
   `carriers`, `disagreements`, `cannot_answer`, `outreach`. Type no words of
   your own into the widget: every sentence comes from the told copy, so it
   moves when the profile moves.
5. **Level control.** Use the Map's layer list to turn levels on and off. Label
   it "Level".

## Pages 2 to 8: the lenses

One page per lens, in this order: the five CII pillars (News and Information,
Civic Participation, Equity & Justice, Health & Opportunity, Environmental
Resilience), then the two lanes of ours (Barriers measured by rewildingCities,
Carriers per 1,000 people).

1. **Map widget** on the lens item.
2. **Layer List** widget, so a reader turns a level's group on and picks one
   measure inside it.
3. **Legend** widget. The legend is the door's: darker is harder access, a
   place with no value is hatched, and every title says it is five equal steps,
   not a standard.
4. A **Text** widget above the map with one sentence, copied from the lens
   item's own description: what kind of lane it is (CII's pillar or ours) and
   how its measures were placed.
5. An empty lens holds no layer, on purpose: a dot on a map reads as data
   (D-400). Its title and description say no measure is placed there yet. Put
   that sentence in large type in the page's Text widget. An empty pillar is a
   finding about what Maine's public data reaches.
6. On the Carriers page, towns are markers sized by how many carriers each has,
   with "none listed" as its own hollow mark; counties are rates per 1,000
   people (D-399). Say so in the page's Text widget, since the two levels draw
   two kinds of number.

## Page 9: Compare

Compare reads the told fields, so the ranges have one home, the profile
(D-387). No new data.

1. Two **Search** widgets side by side, each on the places map.
2. Two **Text** widgets, each connected to one Search's output data source.
3. Show `name`, each `barrier_*` field (each states the range across the towns
   inside a district or county), and `shares`.

## Page 10: What these maps cannot show yet

1. A **Text** widget connected to the places map's state layer, showing the
   state row's `withheld` field: every kind of data this tool holds and does not
   show, and why (D-376). Its words come from the refusal record, never typed.
2. Under it, the state row's `cannot_answer` field.
3. A short line, copied from the lens items, naming the pillars that hold no
   measure yet.

## Credit and accessibility

- Copy the credit line and suggested citation from any door item's
  description into the app's footer. They name Northeastern University
  Library (D-360).
- Check every page with the keyboard alone: Search, the layer list and every
  page link must be reachable with Tab.
- Give each Map widget alt text naming the map and the level shown first.
- The ramps are colourblind-safe (RAMP-1); do not restyle them in the app.

## Publish, then record it

1. Publish the app in Experience Builder. Share it publicly.
2. Copy its item id from the address bar.
3. Read it with the door, then record it:

```
python -m canopy.cli publish maine --adopt-app <item id> --to explorer --write --by "Kalli A. Hale" --reason "the explorer, built by hand from the guide"
python -m canopy.cli publish maine --check
```

The door warns of any item the app reads that the door did not make. Each
warning is a layer the gate has not judged at this door: replace it with a
door item, or say in the ledger why it stays.

After any later publish in Experience Builder, `--check` will say the config
changed. Read what changed, write it in the ledger, then adopt the app again.
