"""
canopy/expose/gate.py ~ the one exposure gate (Contract 1)

given an artifact's envelope, the vocabulary, the plot's consent records, the
license list, the manifest's datasets and a target's sharing level, decide
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
  9  a type's required context must travel with the artifact
  10 redistribution must be permitted at the target's sharing level
  11 publication steps are recorded: the gate carries them in its allow
     record; the exits that make them append them (Sprint 08)

lineage is read from the envelope alone: its own semantic type, and every
input type in its provenance chain, inherited entries included. ~
"""

from __future__ import annotations

from datetime import date, datetime, timezone

GATE_VERSION = "1.0.0"
TIERS = ("public", "aggregate-only", "custom", "excluded")
SHARING_LEVELS = ("private", "organization", "public")


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
           plot: str, manifest_datasets: dict, licenses: dict,
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

        # rule 9: required context
        for note in _type_extra(vocabulary, st).get("required_context") or []:
            if note.get("id") not in (meta.get("context_notes") or []):
                refuse(9, st, tier, where,
                       f"'{st}' requires the context note '{note.get('id')}' to "
                       f"travel with it, and the artifact does not carry it",
                       f"add '{note.get('id')}' to the artifact's metadata.context_notes")

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
        "context_notes": list(meta.get("context_notes") or []), "caveats": caveats,
        "publication_steps": list(meta.get("publication") or []),
        "gate_version": GATE_VERSION, "checked_at": checked_at}}


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
