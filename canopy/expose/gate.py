"""
canopy/expose/gate.py ~ the one exposure gate (Contract 1)

given an artifact's envelope, the vocabulary, the plot's consent records, the
license list, the context notes, the manifest's datasets and a target's
sharing level, decide
whether the artifact may leave. the answer is an allow record or a list of
refusal records, and both are content: an allowed artifact can always say why
it was allowed, and a refused one says what would admit it.

the eleven rules, as this module applies them:

  1  tier values are a closed set; anything else is an error, never a guess
  2  an undeclared type fails closed
  3  every tier in the lineage binds at once (D-101); any excluded stops all
  4  no lineage, no publication; an empty curiosity passes as a caveat (D-102)
  5  aggregate-only leaves only as counts over a declared unit
  6  custom leaves only with an active consent record for this plot and target
  7  every refusal names the type, tier, ancestor and what would admit it
  8  presence before contents: a refusal says a kind of data exists and is
     withheld, and why, without showing it
  9  a note must travel with what it describes: the notes the artifact's own
     type requires, and the notes its rows carry. an artifact that does not
     say what its rows carry is bound by every note in its lineage (D-156)
  10 redistribution must be permitted at the target's sharing level
  11 publication steps are recorded in provenance, by the step that made
     them; the gate gathers every one in the chain into its allow record (D-143)

lineage is read from the envelope alone: its own semantic type, and every
input type in its provenance chain, inherited entries included. so are its
rows' notes: the primitive that wrote the rows lists them in
metadata.row_context_notes. the gate never opens a data file. ~
"""

from __future__ import annotations

from datetime import date, datetime, timezone

GATE_VERSION = "1.0.0"
TIERS = ("public", "aggregate-only", "custom", "excluded")
SHARING_LEVELS = ("private", "organization", "public")
_ABSENT = object()


def _is_id_list(value) -> bool:
    """a list of note ids. a bare string is not one: `in` on a string matches
    any substring, so "census_tribal_area" would pass for "census_tribal" (C-36)."""
    return isinstance(value, list) and all(isinstance(v, str) and v for v in value)


# ── reading tiers (GATE-1, E-5) ──────────────────────────────────────────
def exposure_tier(vocabulary, semantic_type: str) -> str | None:
    """the declared `resolution_tier` of a type, or None if it declares none.

    this is the gate's own reader. Vocabulary.get_tier() reads `tier`, the
    loam maturity, a different meaning of the word (GATE-1). a value outside
    the closed set is an error (rule 1): a misspelling is never a tier."""
    if not vocabulary.knows_name(semantic_type):
        return None
    value = vocabulary.get(semantic_type).extra.get("resolution_tier")
    if value is None:
        return None
    if value not in TIERS:
        raise ValueError(
            f"semantic type '{semantic_type}' declares resolution_tier "
            f"'{value}', which is not one of: {', '.join(TIERS)} (rule 1)")
    return value


def _type_extra(vocabulary, semantic_type: str) -> dict:
    if not vocabulary.knows_name(semantic_type):
        return {}
    return vocabulary.get(semantic_type).extra


# ── reading the artifact ─────────────────────────────────────────────────
def lineage_types(envelope: dict) -> list[tuple[str, str]]:
    """(semantic_type, where) for the artifact and every ancestor in its
    provenance chain, in order, each type once. `where` names the step that
    read it, so a refusal can say which ancestor set its tier."""
    seen: dict[str, str] = {}
    own = (envelope.get("metadata") or {}).get("semantic_type")
    if own:
        seen[own] = "the artifact itself"
    for entry in envelope.get("provenance") or []:
        for inp in entry.get("inputs") or []:
            st = inp.get("semantic_type")
            if st and st not in seen:
                branch = entry.get("lineage_branch")
                seen[st] = (f"input '{inp.get('name')}' of {entry.get('primitive')}"
                            + (f" (via {branch})" if branch else ""))
    return list(seen.items())


def publication_steps(envelope: dict) -> list[dict]:
    """every rule 11 record in the artifact's provenance chain, in chain
    order, each once (D-143). a record lives in the provenance entry of the
    step that made it and is inherited with that entry, so a clip made by a
    preparation reaches every map drawn from it. an ancestor reached through
    two inputs appears twice in the chain; its records are carried once.
    metadata.publication is never read: rule 11 says provenance."""
    seen: set[tuple] = set()
    out: list[dict] = []
    for entry in envelope.get("provenance") or []:
        for r in entry.get("publication") or []:
            key = (r.get("by"), r.get("at"), r.get("step"), r.get("detail"))
            if key in seen:
                continue
            seen.add(key)
            out.append(dict(r, lineage_branch=entry.get("lineage_branch")))
    return out


def lineage_datasets(envelope: dict, manifest_datasets: dict) -> list[str]:
    """the manifest datasets an artifact came from: those its run's resolution
    report names, and any provenance input whose file is a dataset's cache."""
    names: list[str] = []
    res = ((envelope.get("metadata") or {}).get("lineage") or {}).get("data_resolution") or {}
    for key in ("datasets_available", "datasets_acquired"):
        for n in res.get(key) or []:
            if n in manifest_datasets and n not in names:
                names.append(n)
    by_file = {}
    for n, d in manifest_datasets.items():
        cache = ((d.get("cache") or {}).get("path") or "")
        if cache:
            by_file[cache.rsplit("/", 1)[-1]] = n
    for entry in envelope.get("provenance") or []:
        for inp in entry.get("inputs") or []:
            n = by_file.get(str(inp.get("path") or "").rsplit("/", 1)[-1])
            if n and n not in names:
                names.append(n)
    return names


# ── the decision ─────────────────────────────────────────────────────────
def decide(envelope: dict, *, target: str, sharing_level: str, vocabulary,
           plot: str, manifest_datasets: dict, licenses: dict, notes: dict,
           consents: list[dict] | None = None, today: date | None = None) -> dict:
    """allow, with an allow record, or refuse, with one refusal record per
    rule and tier that refuses. raises only on an error in the declarations
    themselves (rule 1, an unknown sharing level)."""
    if sharing_level not in SHARING_LEVELS:
        raise ValueError(f"sharing level must be one of {', '.join(SHARING_LEVELS)}; "
                         f"got {sharing_level!r}")
    consents = consents or []
    today = today or date.today()
    checked_at = datetime.now(timezone.utc).isoformat()
    meta = envelope.get("metadata") or {}
    own_type = meta.get("semantic_type")
    refusals: list[dict] = []

    def refuse(rule, semantic_type, tier, ancestor, reason, would_admit):
        refusals.append({
            "decision": "refuse", "rule": rule, "semantic_type": semantic_type,
            "tier": tier, "ancestor": ancestor, "target": target,
            "sharing_level": sharing_level, "reason": reason,
            "would_admit": would_admit, "gate_version": GATE_VERSION,
            "checked_at": checked_at})

    # rule 4: lineage
    lineage = meta.get("lineage")
    caveats: list[str] = []
    if not lineage or not lineage.get("method"):
        refuse(4, own_type, None, "the artifact itself",
               "it carries no lineage, so nothing can say how it was made",
               "re-run it through the orchestrator, which writes lineage on every receipt")
    elif lineage.get("kind", "experiment") == "experiment" and not lineage.get("curiosity"):
        caveats.append("this result names no curiosity, so it cannot say what "
                       "question it answers (D-64, D-102)")

    # rules 1, 2, 3, 5, 6: every tier in the lineage binds (D-101)
    tiers_bound: list[dict] = []
    consents_cited: list[str] = []
    own_aggregates = bool(_type_extra(vocabulary, own_type).get("aggregates")) if own_type else False
    for st, where in lineage_types(envelope):
        tier = exposure_tier(vocabulary, st)           # rule 1 raises here
        if tier is None:
            refuse(2, st, None, where,
                   f"'{st}' declares no exposure tier, so it does not leave (rule 2)",
                   f"declare resolution_tier for '{st}' in seeds/schemas")
            continue
        tiers_bound.append({"semantic_type": st, "tier": tier, "ancestor": where})
        if tier == "excluded":
            refuse(3, st, tier, where,
                   f"'{st}' is excluded: data of this kind exists here and is "
                   f"withheld, and nothing descended from it leaves",
                   "nothing short of changing its tier, which is Person 3's to declare")
        elif tier == "aggregate-only":
            if not own_aggregates or st == own_type:
                refuse(5, st, tier, where,
                       f"'{st}' leaves only as counts or rates over a declared unit, "
                       f"never as named or located members",
                       f"aggregate it to a type that declares `aggregates: true`")
        elif tier == "custom":
            match = _consent_for(consents, plot, target, sharing_level, st, today)
            if match is None:
                refuse(6, st, tier, where,
                       f"'{st}' leaves only with a consent record for plot "
                       f"'{plot}' and target '{target}' at {sharing_level}",
                       f"an active consent record in plots/{plot}/consent/ covering '{st}'")
            elif match["id"] not in consents_cited:
                consents_cited.append(match["id"])

    # rule 9: required context (D-156, D-157)
    carried, scope = _rule_9(envelope, vocabulary, notes, tiers_bound, refuse)

    # rule 10: license, for every dataset in the lineage
    licenses_checked: list[dict] = []
    datasets = lineage_datasets(envelope, manifest_datasets)
    if not datasets and sharing_level != "private":
        refuse(10, own_type, None, "the artifact itself",
               "no manifest dataset can be identified in its lineage, so no "
               "license can be checked",
               "run it through the orchestrator so its receipts name their datasets")
    for name in datasets:
        term_id = (manifest_datasets.get(name) or {}).get("license")
        term = licenses.get(term_id) if term_id else None
        if term is None:
            refuse(10, (manifest_datasets.get(name) or {}).get("semantic_type"), None,
                   f"dataset '{name}'",
                   (f"dataset '{name}' declares no license" if not term_id else
                    f"dataset '{name}' declares license '{term_id}', which is not "
                    f"on the controlled list"),
                   f"declare a term from seeds/licenses/licenses.yml on '{name}'")
            continue
        licenses_checked.append({"dataset": name, "term": term_id})
        if sharing_level not in term.get("permits", []):
            refuse(10, (manifest_datasets.get(name) or {}).get("semantic_type"), None,
                   f"dataset '{name}'",
                   f"'{name}' is under '{term_id}', which permits "
                   f"{', '.join(term['permits'])}, not {sharing_level}",
                   "a license that permits this sharing level, or a lower level")

    if refusals:
        return {"decision": "refuse", "refusals": refusals}
    return {"decision": "allow", "record": {
        "decision": "allow", "target": target, "sharing_level": sharing_level,
        "tiers": tiers_bound, "consent": consents_cited, "license": licenses_checked,
        "context_notes": carried, "context_scope": scope,
        "context_text": {n: notes[n]["text"] for n in carried}, "caveats": caveats,
        "publication_steps": publication_steps(envelope),
        "gate_version": GATE_VERSION, "checked_at": checked_at}}


def _rule_9(envelope, vocabulary, notes, tiers_bound, refuse):
    """which notes must travel, and does the artifact carry them.

    required: the notes the artifact's own type declares, always. then, if
    metadata.row_context_notes is present (an empty list included), the notes
    its rows carry, and nothing else: an ancestor's type binds no note, since
    the primitive that wrote the rows has said what they hold. if it is
    absent, every note any type in the lineage declares, as before step 6,
    because silence about rows is not a claim that they hold none (D-156).

    every note required or carried must have its text in seeds/notes, since a
    note that cannot be read cannot travel (D-157). returns the carried ids
    and the scope that bound them: "rows" or "lineage"."""
    meta = envelope.get("metadata") or {}
    own = meta.get("semantic_type")
    tier_of = {t["semantic_type"]: t["tier"] for t in tiers_bound}
    required: dict[str, tuple[str, str]] = {}      # note id -> (semantic type, where)

    def need(note_id, semantic_type, where):
        if note_id and note_id not in required:
            required[note_id] = (semantic_type, where)

    if own:
        for note in _type_extra(vocabulary, own).get("required_context") or []:
            need(note.get("id"), own, "the artifact itself")

    rows = meta.get("row_context_notes", _ABSENT)
    scope = "lineage" if rows is _ABSENT else "rows"
    if scope == "rows":
        if not _is_id_list(rows):
            refuse(9, own, tier_of.get(own), "the artifact itself",
                   "its metadata.row_context_notes is not a list of note ids, so the "
                   "gate cannot tell which notes its rows carry",
                   "write row_context_notes as a list of ids (as.list in R, C-36)")
            rows = []
        for note_id in rows:
            need(note_id, own, "a row of the artifact")
    else:
        for st, where in lineage_types(envelope):
            for note in _type_extra(vocabulary, st).get("required_context") or []:
                need(note.get("id"), st, where)

    carried = meta.get("context_notes", [])
    if not _is_id_list(carried):
        refuse(9, own, tier_of.get(own), "the artifact itself",
               "its metadata.context_notes is not a list of note ids; a single "
               "string would seem to carry any note it contains (C-36)",
               "write context_notes as a list of ids (as.list in R)")
        carried = []
    carried = list(dict.fromkeys(carried))

    for note_id in carried:
        if note_id not in notes:
            refuse(9, own, tier_of.get(own), "the artifact itself",
                   f"it carries the note '{note_id}', which has no text in "
                   f"seeds/notes/notes.yml, so the note cannot travel",
                   f"declare '{note_id}' in seeds/notes/notes.yml, or stop carrying it")
    for note_id, (st, where) in required.items():
        if note_id not in notes:
            refuse(9, st, tier_of.get(st), where,
                   f"the note '{note_id}' is required here but has no text in "
                   f"seeds/notes/notes.yml, so it cannot travel",
                   f"declare '{note_id}' in seeds/notes/notes.yml")
        elif note_id not in carried:
            whose = (f"a row of the artifact carries the note '{note_id}'"
                     if where == "a row of the artifact" else
                     f"'{st}' requires the context note '{note_id}'")
            refuse(9, st, tier_of.get(st), where,
                   f"{whose}, so it must travel with the artifact, and the "
                   f"artifact does not carry it",
                   f"add '{note_id}' to the artifact's metadata.context_notes")
    return [n for n in carried if n in notes], scope


def _consent_for(consents, plot, target, sharing_level, semantic_type, today):
    """an active, unexpired consent record that opens exactly this: this plot,
    this target, this sharing level or a wider one, covering this type. no
    wildcard is honoured (Contract 1, section 5)."""
    order = {lv: i for i, lv in enumerate(SHARING_LEVELS)}
    for c in consents:
        if c.get("status") != "active":
            continue
        if c.get("plot") != plot or c.get("target") != target:
            continue
        if order.get(c.get("sharing_level"), -1) < order[sharing_level]:
            continue
        if semantic_type not in (c.get("covers") or []):
            continue
        expires = c.get("expires_on")
        if expires is not None and expires < today:
            continue
        return c
    return None
