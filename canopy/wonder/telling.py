"""
canopy/wonder/telling.py

telling ~ a place profile in plain sentences, for the explorer (Sprint 09)

the explorer shows each place in Experience Builder's widgets, which read
short text fields. this module turns one profile (Contract 4) into those
fields. it builds every sentence from the profile's structured parts (a
status, a source, a count, a share) and never passes the profile's working
text through: a ledger id such as D-271 or OBS-1 means nothing to a reader,
so none is printed. a share and a count are said the way
canopy/wonder/place.py says them, so the explorer and `wonder` agree.

the register lives in seeds/language/plain_language.yml: technical but
plain, about a ninth-grade reading level, showing what the data says rather
than describing it. tests/test_telling.py holds every sentence to it.

  TellingContext.load(doc, root)   what every row needs from the whole
                                   document: names by key, which county holds
                                   each town, the standard's measures, the
                                   notes and their status
  tell(profile, ctx)               one place's fields, every value a string
  tell_all(doc, root, refusals)    every place the explorer shows; with the
                                   plot's refusal record, the state's row also
                                   says what the tool holds and does not show
  tell_withheld(record, ctx)       that field, in plain words (D-376, D-378)

the explorer shows six levels: the state, counties, towns, House and Senate
districts, and Census tribal areas. MEGIS civil divisions are how towns join
their sources (D-122); most share a town's name, so they stay in the
profiles and out of the explorer.

a tribal area is told on the Census Bureau's terms and says so: its note
travels with it, a draft note says it is a draft, and it carries no value
the profile does not (D-171). it reads and writes nothing. ~
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .place import _count, _pct

LEVELS = {
    "state": "State",
    "county": "County",
    "cousub": "Town or city",
    "sldl": "Maine House district",
    "sldu": "Maine Senate district",
    "aiannh": "Census tribal area",
}
EXPLORER_LEVELS = tuple(LEVELS)

KINDS = {
    "state": "state", "county": "county", "town": "town", "city": "city",
    "plantation": "plantation", "unorganized_territory": "unorganized territory",
    "reservation_subdivision": "reservation (as a Census county subdivision)",
    "gore": "gore", "house_district": "House district", "senate_district": "Senate district",
    "tribal_reservation": "reservation (Census tribal area)",
    "tribal_trust_land": "trust land (Census tribal area)",
}

# what each flag on a place means (D-128, D-130), in plain words
FLAGS = {
    "lurc": "Part or all of this place lies where Maine's Land Use Planning Commission, "
            "not a town government, sets land use rules.",
    "lurc_mixed": "Only part of this place lies where Maine's Land Use Planning Commission "
                  "sets land use rules.",
    "zero_population": "The 2020 Census counted no residents here.",
    "zero_households": "The 2020 Census counted no households here.",
    "no_block_points": "No 2020 Census block is centered here, so this place has no "
                       "counts built from Census blocks.",
}

CARRIERS = {
    "municipal_clerk_office": ("municipal clerk office", "municipal clerk offices"),
    "library_outlet": ("public library", "public libraries"),
    "public_school": ("public school", "public schools"),
    "health_center_site": ("health center site", "health center sites"),
    "news_outlet": ("local news outlet", "local news outlets"),
}

# the order a barrier's headline is chosen in: a finding first, then what the
# data cannot settle, then what has no line, then what cannot be judged
HEADLINE = ("below", "crosses", "as_published", "within_margin", "does_not_cross",
            "no_threshold", "cannot_judge")

STATUS_WORDS = {
    "acquirable": "Not yet added. Source: {source}.",
    "needs_our_model": "No published source records this yet.",
    "needs_consent": "This needs the consent of the community it describes.",
}

ROSTER_WORDS = ("The new Legislature's member lists come out on or after {date}. Who "
                "represents this place will be added then.")

REPRESENTATION_NOTE = "tribal_representation_legislature"

DISTRICT_NAME = re.compile(r"^State (House|Senate) District (\w+).*$")
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December")


@dataclass
class Language:
    ceiling: float
    claim_words: tuple
    working_ids: re.Pattern
    kinds: dict = field(default_factory=dict)   # a kind of data, in plain words (PLAINWORDS-1)

    @classmethod
    def load(cls, root: str | Path) -> "Language":
        path = Path(root) / "seeds" / "language" / "plain_language.yml"
        doc = yaml.safe_load(path.read_text()) or {}
        return cls(ceiling=float(doc["reading_grade_ceiling"]),
                   claim_words=tuple(str(w).lower() for w in doc["claim_words"]),
                   working_ids=re.compile(doc["working_ids"]),
                   kinds={str(k): " ".join(str(v).split())
                          for k, v in (doc.get("kinds") or {}).items()})

    def kind(self, semantic_type: str | None) -> str:
        """a kind of data as a reader would name it: its plain words when the
        register gives them, else its type with the underscores taken out."""
        st = str(semantic_type or "")
        if st in self.kinds:
            return self.kinds[st]
        return self.strip(st.replace("_", " ")) or "a kind of data"

    def strip(self, text: str) -> str:
        """a sentence with every working id taken out, with the brackets,
        commas and spaces it leaves behind."""
        out = self.working_ids.sub("", text)
        out = re.sub(r"\(\s*[,;\s]*\)", "", out)
        out = re.sub(r"\s+([,;.:)])", r"\1", out)
        out = re.sub(r"\(\s+", "(", out)
        return re.sub(r"\s{2,}", " ", out).strip(" ;,")


@dataclass
class TellingContext:
    names: dict                     # key -> place name
    county_of: dict                 # town key -> county name
    notes: dict                     # note id -> {text, status, ...}
    language: Language
    profile_version: str = ""
    built_at: str = ""
    skipped: dict = field(default_factory=dict)

    @classmethod
    def load(cls, doc: dict, root: str | Path) -> "TellingContext":
        from canopy.expose.records import load_notes
        names, county_of = {}, {}
        for p in doc.get("places") or []:
            place = p["header"]["place"]
            names[p["place_key"]] = place["name"]
        for p in doc.get("places") or []:
            place = p["header"]["place"]
            if place["level"] != "county":
                continue
            for inner in (p.get("represented") or {}).get("inside") or []:
                if inner.get("level") == "cousub":
                    county_of[f"{inner['authority']}:{inner['code']}"] = place["name"]
        return cls(names=names, county_of=county_of,
                   notes=load_notes(Path(root) / "seeds" / "notes"),
                   language=Language.load(root),
                   profile_version=str(doc.get("profile_version") or ""),
                   built_at=str(doc.get("built_at") or ""))


# ── small sayings ─────────────────────────────────────────────────────────────
def _sentence(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    return text if text.endswith((".", "?", "!")) else text + "."


def _date(text: str) -> str | None:
    m = ISO_DATE.search(text or "")
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    return f"{MONTHS[mo - 1]} {d}, {y}"


def short_name(name: str) -> str:
    """a district's Census name, said as a reader would: 'State House District
    105 (2024); Maine' is 'House District 105'. every other name is kept."""
    m = DISTRICT_NAME.match(name or "")
    return f"{m.group(1)} District {m.group(2)}" if m else name


def amount(value, unit: str | None, said_in: str = "") -> str:
    """a value with its unit, in words. a percent is said to one place, a
    share is turned into a percent, a rate per 1,000 to two places, a count
    whole. a percent's base is left out when the measure's own name already
    says it (said_in), so no sentence says it twice."""
    if value is None:
        return "no value"
    unit = unit or ""
    if unit.startswith("percent_of_"):
        base = unit[len('percent_of_'):].replace('_', ' ')
        if base.lower() in said_in.lower():
            return f"{value:.1f}%"
        return f"{value:.1f}% of {base}"
    if unit.startswith("percent"):
        return f"{value:.1f}%"
    if unit.startswith("share_of_"):
        return f"{value * 100:.1f}% of {unit[len('share_of_'):].replace('_', ' ')}"
    if unit.startswith("per_1000_"):
        return f"{value:.2f} per 1,000 {unit[len('per_1000_'):].replace('_', ' ')}"
    return f"{value:,.0f} {unit.replace('_', ' ')}".strip()


def _measure_name(entry: dict) -> str:
    name = str(entry.get("name") or entry.get("measure") or "a measure")
    if "_" in name and " " not in name:
        name = name.replace("_", " ")
    return name[0].upper() + name[1:]


def _unheld(profile: dict) -> dict:
    """every measure this place's profile says is not held, with its status
    and source, from part 6 (the standard as the profile was built on it)."""
    return {m["measure"]: m for m in (profile.get("cannot_answer") or {}).get("not_acquired") or []
            if m.get("measure")}


# ── the parts ─────────────────────────────────────────────────────────────────
def _about(profile: dict, ctx: TellingContext) -> str:
    place = profile["header"]["place"]
    kind = KINDS.get(place["kind"], place["kind"].replace("_", " "))
    bits = [f"{place['name']} is a {kind} in Maine."]
    county = ctx.county_of.get(profile["place_key"])
    if county:
        bits[0] = f"{place['name']} is a {kind} in {county}."
    rep = profile.get("represented") or {}
    pop, hh = rep.get("population") or {}, rep.get("households") or {}
    if pop.get("count") is not None:
        bits.append(f"{_count(pop['count'])} people lived here in the 2020 Census.")
    if hh.get("count") is not None:
        when = re.sub(r"\s*\(.*\)", "", str(hh.get("release") or "")).strip()
        bits.append(f"The Census Bureau's survey estimates {_count(hh['count'])} households"
                    + (f" for {when}." if when else "."))
    for flag in profile["header"].get("flags") or []:
        bits.append(FLAGS.get(flag, f"A flag is set for this place: {flag}."))
    return " ".join(bits)


def _note(profile: dict, ctx: TellingContext) -> str:
    note = profile["header"].get("context_note")
    if not note:
        return ""
    status = (ctx.notes.get(note.get("id")) or {}).get("status")
    text = ctx.language.strip(str(note.get("text") or ""))
    return ("Draft wording: " if status == "draft" else "") + text


def _shares(profile: dict) -> str:
    """the places this one overlaps, with the share of residents in each: a
    town in every district it touches, a district with every town (D-76)."""
    me = profile["header"]["place"]
    level = me["level"]
    lines = []
    for o in (profile.get("represented") or {}).get("overlapping") or []:
        if o.get("level") not in EXPLORER_LEVELS:
            continue
        edge = o.get("edge") or {}
        share = edge.get("weight_population")
        name = short_name(o.get("name") or "")
        if edge.get("from", {}).get("code") == me["code"]:
            lines.append((o["level"], f"{name}: {_pct(share)} of the people here."))
        else:
            lines.append((o["level"], f"{name}: {_pct(share)} of its people live here."))
    if not lines:
        return ""
    out = []
    for lvl in ("sldl", "sldu", "cousub", "aiannh", "county"):
        group = [text for lv, text in lines if lv == lvl]
        if not group:
            continue
        label = {"sldl": "House districts", "sldu": "Senate districts", "cousub": "Towns",
                 "aiannh": "Census tribal areas", "county": "Counties"}[lvl]
        if level in ("sldl", "sldu") and lvl == "cousub":
            label = "Towns in this district"
        out.append(f"{label}. {' '.join(group)}")
    return " ".join(out)


def _represented(profile: dict, ctx: TellingContext) -> str:
    leg = (profile.get("represented") or {}).get("legislators") or {}
    if leg.get("status") == "not_held":
        when = _date(str(leg.get("why") or "")) or "a date not yet known"
        said = ROSTER_WORDS.format(date=when)
    else:
        said = "See the full profile for who represents this place."
    if profile["header"]["place"]["level"] in ("aiannh", "state"):
        note = ctx.notes.get(REPRESENTATION_NOTE)
        if note:
            said += " " + ("Draft wording: " if note.get("status") == "draft" else "") + \
                ctx.language.strip(note["text"])
    return said


def _needs(profile: dict, ctx: TellingContext) -> str:
    """the two needs the profile reads beside the barriers (part 1): a value,
    an open-ended value in the source's own words, or why there is none."""
    out = []
    for n in (profile.get("represented") or {}).get("needs") or []:
        name = _measure_name(n)
        if n.get("bound"):
            out.append(f"{name}: {n['bound']} (the source publishes only this bound).")
        elif n.get("value") is not None:
            out.append(f"{name}: {amount(n['value'], n.get('unit'), said_in=name)}.")
        else:
            out.append(f"{name}: no estimate. The Census Bureau published none for this place.")
    return " ".join(out)


def _unacquired(m_id: str, unheld: dict, ctx: TellingContext) -> str | None:
    m = unheld.get(m_id) or {}
    words = STATUS_WORDS.get(m.get("status"))
    if not words:
        return None
    return words.format(source=ctx.language.strip(str(m.get("source") or "a source not named")))


def _says(entry: dict, unheld: dict, ctx: TellingContext) -> str:
    """one measure's verdict, said. a measure not yet acquired is said from its
    status and source; any other verdict in its own reader's sentence (every
    verdict carries one, D-272), with working ids taken out."""
    v = entry.get("verdict") or {}
    if v.get("verdict") in ("cannot_judge", "no_threshold") and entry.get("value") is None:
        said = _unacquired(entry.get("measure"), unheld, ctx)
        if said:
            return said
        if v.get("verdict") == "no_threshold":
            return "No line is set for this, and this place has no value for it."
        return "This cannot be judged here: this place has no value for it."
    if v.get("verdict") == "no_threshold":
        return f"{amount(entry.get('value'), entry.get('unit'))}. No line is set for this, " \
               f"so the value is shown and not judged."
    return _sentence(ctx.language.strip(str(v.get("says") or "")))


def _barrier(b: dict, unheld: dict, ctx: TellingContext) -> str:
    judged = [e for e in b.get("indicators") or [] if (e.get("verdict") or {}).get("verdict")]
    if not judged:
        return "Nothing here judges this barrier yet."
    rank = {v: i for i, v in enumerate(HEADLINE)}
    judged.sort(key=lambda e: rank.get(e["verdict"]["verdict"], len(HEADLINE)))
    lead = judged[0]
    said = f"{_measure_name(lead)}: {_sentences(_says(lead, unheld, ctx))}"
    rest = judged[1:]
    if rest:
        tally: dict = {}
        for e in rest:
            key = _tally_word(e)
            tally[key] = tally.get(key, 0) + 1
        said += " Other measures: " + "; ".join(
            f"{n} {word}" for word, n in sorted(tally.items(), key=lambda kv: -kv[1])) + "."
    return said


def _sentences(text: str) -> str:
    return _sentence(text)


def _tally_word(entry: dict) -> str:
    v = entry["verdict"]["verdict"]
    if entry.get("value") is None and v in ("cannot_judge", "no_threshold"):
        return "not yet added or with no value here"
    return {"below": "show people short of the line",
            "crosses": "cross a line",
            "as_published": "are the publisher's own determination",
            "within_margin": "the data cannot settle",
            "does_not_cross": "stay below every line",
            "no_threshold": "have no line set",
            "cannot_judge": "cannot be judged here"}.get(v, v.replace("_", " "))


def _carriers(profile: dict, ctx: TellingContext) -> str:
    """the institutions that carry information here, counted. a count of zero
    is what the listings hold, said as 'none listed', never a missing count."""
    parts, notes = [], []
    for c in profile.get("carriers") or []:
        one, many = CARRIERS.get(c.get("type"), (str(c.get("type")), str(c.get("type"))))
        n = c.get("count")
        if n is None:
            parts.append(_sentence(f"{many}: not available"))
        elif n == 0:
            parts.append(_sentence(f"{many}: none listed"))
        else:
            parts.append(_sentence(f"{_count(n)} {one if n == 1 else many}"))
        note = c.get("context_note")
        if note and note.get("id") not in [x[0] for x in notes]:
            status = (ctx.notes.get(note.get("id")) or {}).get("status")
            notes.append((note.get("id"), ("Draft wording: " if status == "draft" else "")
                          + ctx.language.strip(str(note.get("text") or ""))))
    said = " ".join(parts) if parts else "No carriers are counted here."
    return " ".join([said] + [n for _id, n in notes])


def _disagreements(profile: dict) -> str:
    d = profile.get("disagreements") or {}
    n = len(d.get("entries") or [])
    if not n:
        return "No measure here has more than one publisher, so no sources disagree."
    return f"{n} measure{'s' if n != 1 else ''} here {'have' if n != 1 else 'has'} more than " \
           f"one publisher, and their values differ. Both are shown, and neither is picked."


def _cannot_answer(profile: dict, ctx: TellingContext) -> str:
    part = profile.get("cannot_answer") or {}
    unheld = _unheld(profile)
    lines = []
    for g in part.get("gaps") or []:
        if g.get("holding") == "seats":
            continue                                    # said in `represented`
        if g.get("measure"):
            said = _unacquired(g["measure"], unheld, ctx)
            lines.append(said or f"{_measure_name(g)}: the standard counts on it, and this "
                                 f"plot holds no values for it.")
    sources = {}
    for m in part.get("not_acquired") or []:
        said = _unacquired(m.get("measure"), unheld, ctx)
        if said:
            sources[said] = sources.get(said, 0) + 1
    for said, n in sources.items():
        lines.append(f"{n} measure{'s' if n != 1 else ''}: {said}" if n > 1 else said)
    for r in part.get("refusals") or []:
        what = str(r.get("semantic_type") or r.get("receipt") or "a layer").replace("_", " ")
        reasons = [ctx.language.strip(str(x.get("reason") or ""))
                   for x in r.get("refusals") or []] or ["it may not leave"]
        lines.append(f"Withheld: {what}. " + " ".join(_sentence(x) for x in reasons if x))
    if not lines:
        return "Nothing is missing for this place."
    return " ".join(_sentence(x) if not x.endswith(".") else x for x in lines)


def _outreach(profile: dict) -> str:
    pairs = (profile.get("channels") or {}).get("pairings") or []
    if not pairs:
        return "Outreach suggestions are not written yet."
    return f"{len(pairs)} outreach suggestions, labelled as standard practice, not findings."


# ── one place, every place ────────────────────────────────────────────────────
def tell(profile: dict, ctx: TellingContext) -> dict:
    """one place's fields, every value a string, none ever empty."""
    place = profile["header"]["place"]
    row = {
        "key": profile["place_key"], "authority": place["authority"], "code": place["code"],
        "name": place["name"], "level": LEVELS.get(place["level"], place["level"]),
        "about": _about(profile, ctx),
        "note": _note(profile, ctx) or "No context note.",
        "shares": _shares(profile) or "This place does not overlap a district or town.",
        "represented": _represented(profile, ctx),
        "needs": _needs(profile, ctx) or "No needs are read for this place.",
    }
    unheld = _unheld(profile)
    for b in profile.get("barriers") or []:
        row[f"barrier_{b['barrier']}"] = f"{_sentence(b['words'])} {_barrier(b, unheld, ctx)}"
    row.update({
        "carriers": _carriers(profile, ctx),
        "disagreements": _disagreements(profile),
        "cannot_answer": _cannot_answer(profile, ctx),
        "outreach": _outreach(profile),
        "profile_version": ctx.profile_version,
        "built_at": ctx.built_at,
    })
    return row


# why a kind of data stays in, by the gate's rule (Contract 1), in plain words
WITHHELD_WORDS = {
    1: "its declaration needs correcting",
    2: "its kind of data is not declared yet",
    3: "this kind of data is never shown",
    4: "nothing records how it was made",
    5: "it names or locates its members, so it is shown only as counts for each place",
    6: "it is shown only with the consent of the community it describes",
    9: "it must carry a context note that it does not carry yet",
    10: "its license does not allow sharing it publicly",
}


def tell_withheld(record: dict, ctx: TellingContext) -> str:
    """what the plot holds and does not show, from its refusal record: each kind
    of data once, with why, never a member of it (Contract 1, rule 8). told on
    the state's row, the one place the whole plot is (D-376)."""
    kinds: dict = {}
    for w in record.get("withheld") or []:
        what = ctx.language.kind(w.get("semantic_type"))
        why = kinds.setdefault(what, [])
        for r in w.get("refusals") or []:
            said = WITHHELD_WORDS.get(r.get("rule"), "the exposure gate keeps it in")
            if said not in why:
                why.append(said)
    if not kinds:
        return "Nothing this tool holds is kept from this map."
    n = len(kinds)
    lines = [f"This tool holds {n} kind{'s' if n != 1 else ''} of data that this map "
             f"does not show."]
    for what, why in sorted(kinds.items()):
        lines.append(_sentence(f"{what}: {'; '.join(why) or 'the exposure gate keeps it in'}"))
    return " ".join(lines)


def tell_all(doc: dict, root: str | Path,
             refusals: dict | None = None) -> tuple[list[dict], TellingContext]:
    """every place the explorer shows, told; the others counted by level in
    ctx.skipped, so a reader of the run sees what was left out. with the
    plot's refusal record, the state's row carries `withheld` (D-376)."""
    ctx = TellingContext.load(doc, root)
    rows = []
    for p in doc.get("places") or []:
        level = p["header"]["place"]["level"]
        if level not in EXPLORER_LEVELS:
            ctx.skipped[level] = ctx.skipped.get(level, 0) + 1
            continue
        row = tell(p, ctx)
        if refusals is not None and level == "state":
            row["withheld"] = tell_withheld(refusals, ctx)
        rows.append(row)
    return rows, ctx


# ── the register, measured ────────────────────────────────────────────────────
def _syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(n, 1)


def reading_grade(text: str) -> float:
    """the Flesch-Kincaid grade of a text: 0.39 words per sentence plus 11.8
    syllables per word, less 15.59. a rough, standard measure, enough to keep
    sentences short and words plain."""
    sentences = [s for s in re.split(r"[.!?]+(?:\s|$)", text) if s.strip()]
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    if not sentences or not words:
        return 0.0
    syllables = sum(_syllables(w) for w in words)
    return 0.39 * len(words) / len(sentences) + 11.8 * syllables / len(words) - 15.59
