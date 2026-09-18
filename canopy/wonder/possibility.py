"""

canopy/wonder/possibility.py

possibility ~ what this ground can wonder about, and what it would take

the honest, teaching heart of wonder. a person arrives with a question
about their community and this shows them, in plain words: here is the
data we were able to gather for your place, here is what you can ask of it
right now, and here is what is still missing and what its absence costs
your answer. ♡

the commitments, made into structure:
  ~ no silent choices ~ every requirement, gap, and decision is named in
    the open, so the person co-authors the science
  ~ all data, no failure ~ a missing dataset is the next question, not a
    dead end; the gap loops to acquiring
  ~ start where you are ~ whatever is present, we surface the question it
    can already answer, so everyone runs something today
  ~ the teaching is the tool ~ the words are the `role` and
    `uncertainty_without` you wrote into each method and the `significance`
    you wrote into each curiosity; wonder only surfaces the pedagogy
    already planted in the seeds

it reads what is present from the loam (never the filesystem), matches it
to the curiosities a community could explore and the methods that answer
them, and renders each possibility warmly enough for a child and truthfully
enough for a scientist. one reading serves both; depth is emergent, not a
separate mode. this is the light exploratory read ~ at commit time your
ResolutionEngine does the authoritative resolve-and-acquire. ~

"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from canopy.loam.readiness import holdings_by_type


def _root() -> Path:
    """
    the garden's root ~ delegated to canopy.paths, which raises rather than
    falling back to Path.cwd(). the old fallback meant a failed search
    returned an unrelated directory and every read came back empty, with no
    error to show for it. C-04. ~
    """
    from canopy.paths import project_root
    return project_root()


def _load_dir(folder: Path) -> dict[str, dict]:

    out: dict[str, dict] = {}

    if not folder.is_dir():
        return out
    
    for f in sorted(folder.rglob("*.yml")):
        try:
            doc = yaml.safe_load(f.read_text()) or {}
        except Exception:
            continue
        cid = doc.get("id") or f.stem
        doc["_path"] = str(f)
        out[cid] = doc

    return out


def present_types(loam, plot: str) -> set[str]:
    """
    the canonical types this plot actually holds, conformed. ~
    """

    have: set[str] = set()

    for tier in ("tended", "gathered"):
        for row in loam.find(plot=plot, tier=tier):
            if row.get("semantic_type"):
                have.add(row["semantic_type"])

    return have


def present_holdings(loam, plot: str, holdings=None) -> dict[str, str]:
    """
    what this ground holds, in plain words; from the projected metadata ~
    coverage, what each row is, the scheme it was classified under, its frame.
    
    the data-aware read: loam's projected columns spoken aloud, not just names
    listed. a field loam does not carry is simply left unsaid ~ honest, because
    the primitive has not emitted it yet. ~
    """

    out: dict[str, str] = {}

    for tier in ("tended", "gathered"):
        for row in loam.find(plot=plot, tier=tier):
            st = row.get("semantic_type")
            if not st or st in out:
                continue
            bits: list[str] = []
            # coverage is spoken as the RANGE across every artifact wearing
            # this name, never whichever row happened to come first. one
            # thin artifact among four should be visible, not decisive. ~
            h = holdings.get(st) if holdings else None
            if h is not None and h.best_coverage is not None:
                if h.count > 1 and h.worst_coverage != h.best_coverage:
                    bits.append(f"coverage {h.worst_coverage:.0%}-{h.best_coverage:.0%} "
                                f"across {h.count} artifacts")
                else:
                    bits.append(f"{h.best_coverage:.0%} coverage")
            unit = row.get("unit_key")
            if unit:
                bits.append(f"one row per {unit}")
            scheme = row.get("conformed_by")
            if scheme:
                bits.append(f"{scheme} scheme")
            crs = row.get("crs")
            if crs:
                bits.append(f"in {crs}")
            out[st] = st + (f" ({', '.join(bits)})" if bits else "")

    return out


def _candidate_methods(curiosity: dict, methods: dict[str, dict]) -> list[dict]:
    """
    the methods that could answer this curiosity ~ 
    the ones it names, or, failing an explicit list, 
    the ones sharing its domain. ~
    """

    named = []

    for ref in curiosity.get("compatible_methods", []) or []:
        mid = str(ref).split("/")[-1]
        if mid in methods:
            named.append(methods[mid])

    if named:
        return named
    
    dom = curiosity.get("domain")

    return [m for m in methods.values() if m.get("domain") == dom]


@dataclass
class Gap:
    """
    a datum we could not gather, and what its absence costs 
    ~ the words are the method author's own. ~
    """

    label: str
    why_it_matters: str      # the method's `role`
    what_you_lose: str       # the method's `uncertainty_without`
    critical: bool


@dataclass
class MethodPossibility:
    """
    one honest possibility 
    ~ a question this ground could explore, by one
    method, given what is present. carries the human framing so it can be
    said to anyone. ~
    """
    plot: str
    curiosity_id: str
    curiosity_question: str
    significance: str
    method_id: str
    method_name: str
    verdict: str                       # ready ~ partial ~ not_yet
    sub_questions: list[tuple[str, str]] = field(default_factory=list)
    present: list[str] = field(default_factory=list)
    present_detail: dict[str, str] = field(default_factory=dict)
    gaps: list[Gap] = field(default_factory=list)
    choices: list[tuple[str, str]] = field(default_factory=list)

    def say(self) -> str:
        """
        render this possibility in plain, warm words 
        ~ for a child or an elder or a scientist, the same truth. ~
        """

        head = {
            "ready": "🌱 you can explore this today",
            "partial": "🌤 you can start this, with one honest caveat",
            "not_yet": "🌰 not yet ~ but here is what it would take",
        }[self.verdict]
        lines = [f"{head}", f'   your question: "{self.curiosity_question}"']
        if self.significance:
            lines.append(f"   why it matters: {self.significance.strip().splitlines()[0]}")
        lines.append(f"   the way in: {self.method_name}")
        if self.sub_questions:
            lines.append("   things you could actually ask:")
            for _name, q in self.sub_questions[:4]:
                lines.append(f"     ~ {q}")
        if self.present:
            said = [self.present_detail.get(t, t) for t in self.present]
            lines.append(f"   what your community already has: {'; '.join(said)}")
        for g in self.gaps:
            lines.append(f"   what's missing: {g.label}")
            if g.why_it_matters:
                lines.append(f"     it's for: {g.why_it_matters.splitlines()[0]}")
            if g.what_you_lose:
                lines.append(f"     without it: {g.what_you_lose.splitlines()[0]}")
        if self.choices:
            lines.append("   choices that would be yours to make:")
            for name, desc in self.choices[:3]:
                d = desc.strip().splitlines()[0] if desc else name
                lines.append(f"     ~ {name}: {d}")
        return "\n".join(lines)


_VERDICT_ORDER = {"ready": 0, "partial": 1, "not_yet": 2}


def _weigh(method: dict, present: set[str],
           holdings=None, floor: float = 0.5) -> tuple[str, list[str], list[Gap]]:
    """
    weigh a method against this ground ~ what it needs, what is held, and
    whether what is held is full enough to answer anything. a type can be
    present by name and empty in fact; thin ground never blocks, it only
    steps a possibility down from ready to partial, saying why. ~
    """
    hits: list[str] = []
    gaps: list[Gap] = []
    thin: list[str] = []
    for req in method.get("requires_data", []) or []:
        types = req.get("semantic_types") or ([req["type"]] if req.get("type") else [])
        hit = next((t for t in types if t in present), None)
        if hit:
            hits.append(hit)
            h = holdings.get(hit) if holdings else None
            if h is not None and h.is_thin(floor):
                thin.append(hit)
        else:
            gaps.append(Gap(
                label=(types[0] if types else req.get("name", "?")),
                why_it_matters=(req.get("role") or "").strip(),
                what_you_lose=(req.get("uncertainty_without") or "").strip(),
                critical=req.get("critical", True)))
    for t_name in thin:
        h = holdings[t_name]
        gaps.append(Gap(
            label=f"{t_name} (present but thin)",
            why_it_matters="Held, but too empty to answer confidently.",
            what_you_lose=(
                f"The fullest of {h.count} artifact(s) covers only "
                f"{h.best_coverage:.0%}, below the floor of {floor:.0%}. "
                f"An answer can still be grown here, but it will be uncertain."),
            critical=False))

    if any(g.critical for g in gaps):
        verdict = "not_yet"
    elif gaps:
        verdict = "partial"
    else:
        verdict = "ready"
    return verdict, hits, gaps


def _choices_of(method: dict) -> list[tuple[str, str]]:
    out = []
    for name, spec in (method.get("choices") or {}).items():
        out.append((name, (spec or {}).get("description", "")))
    return out


def explore(loam, plot: str, question: str | None = None,
            root: str | Path | None = None) -> list[MethodPossibility]:
    """what can this ground wonder about? ~ read the loam, match it to the
    curiosities and their methods, and return every honest possibility,
    readiest first so a person starts where they are. an optional plain
    question ranks the curiosities by simple word-overlap; without one, we
    show everything this place can ask. ~

    this is now a RENDERING of the read-model rather than a second
    measurement of the same ground. it used to weigh requirements itself,
    which meant the CLI and anything else that asked would each compute an
    answer and drift. read_plot measures once; this speaks. P-03. ~
    """
    from .reading import read_plot

    reading = read_plot(loam, plot, root=root)
    holdings = present_holdings(loam, plot, holdings_by_type(loam, plot))

    # the read-model speaks in verdicts; the warm telling speaks in weather.
    weather = {"runnable": "ready",
               "runnable_with_uncertainty": "partial",
               "blocked": "not_yet"}

    q_words = set((question or "").lower().split())
    possibilities: list[tuple[float, MethodPossibility]] = []

    for cur in reading.curiosities:
        text = " ".join([cur.question, cur.description, cur.significance,
                         " ".join(cur.tags)]).lower()
        relevance = len(q_words & set(text.split())) if q_words else 0

        for m in cur.methods:
            gaps: list[Gap] = []
            for req in m.requirements:
                if not req.satisfied_by:
                    gaps.append(Gap(
                        label=req.accepts[0],
                        why_it_matters=req.role,
                        what_you_lose=req.uncertainty_without,
                        critical=req.critical))
                elif req.thin:
                    gaps.append(Gap(
                        label=f"{req.satisfied_by} (present but thin)",
                        why_it_matters="Held, but too empty to answer confidently.",
                        what_you_lose=next(
                            (u for u in m.uncertainties
                             if u.startswith(req.satisfied_by)), ""),
                        critical=False))

            possibilities.append((relevance, MethodPossibility(
                plot=plot,
                curiosity_id=cur.curiosity_id,
                curiosity_question=cur.question,
                significance=cur.significance,
                method_id=m.method_id,
                method_name=m.method_name,
                verdict=weather.get(m.verdict, "not_yet"),
                sub_questions=[(q, q) for q in cur.sub_questions],
                present=m.present,
                present_detail=holdings,
                gaps=gaps,
                choices=[(c["name"], c["description"]) for c in m.choices])))

    possibilities.sort(key=lambda pair: (-pair[0], _VERDICT_ORDER[pair[1].verdict],
                                         pair[1].curiosity_id, pair[1].method_id))
    return [p for _rel, p in possibilities]
