"""
canopy/orchestrator/preconditions.py

The precondition gate. Reads an input's envelope (its provenance chain and its
warnings) and decides whether a primitive is allowed to run. This is where
pipeline-ordering guarantees live now that state is carried by provenance rather
than by type suffixes.

Predicates (declared per-primitive in _registry.yml under `preconditions:`):
  - provenance_contains: <primitive_name>   # some input was produced/touched by that step
  - no_unresolved_critical: true            # no input carries a critical-level warning

The gate is a hard block on failure, and it records each satisfied predicate as
an info note so its judgments are auditable. No silent choices, including no
silent approvals.

Inputs are duck-typed: anything with `.envelope.provenance[*].primitive` and
`.envelope.warnings[*].level` works, so this module has no import dependency on
the envelope module (and no circular import).
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PreconditionOutcome:
    ok: bool
    failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _provenance_primitives(inputs) -> set[str]:
    """Union of primitive names across every input's provenance chain."""
    seen: set[str] = set()
    for inp in inputs:
        env = getattr(inp, "envelope", None)
        if env is None:
            continue
        for entry in getattr(env, "provenance", None) or []:
            name = getattr(entry, "primitive", None)
            if name:
                seen.add(name)
    return seen


def _warning_levels(inputs) -> list[str]:
    """All warning levels across every input's envelope."""
    levels: list[str] = []
    for inp in inputs:
        env = getattr(inp, "envelope", None)
        if env is None:
            continue
        for w in getattr(env, "warnings", None) or []:
            lvl = getattr(w, "level", None)
            if lvl:
                levels.append(lvl)
    return levels


def check_preconditions(preconditions, inputs) -> PreconditionOutcome:
    """
    Evaluate a primitive's declared preconditions against its inputs' envelopes.

    Args:
        preconditions: list of single-key dicts, e.g.
            [{"provenance_contains": "validate_vector"}, {"no_unresolved_critical": True}]
        inputs: list of EnvelopeInput-like objects, each optionally carrying an
            `.envelope` with `.provenance[*].primitive` and `.warnings[*].level`.

    Returns:
        PreconditionOutcome(ok, failures, notes). `ok` is True only if every
        predicate passed; `failures` collects all failures (not just the first)
        so a caller sees the whole picture; `notes` records satisfied predicates.
    """
    failures: list[str] = []
    notes: list[str] = []

    if not preconditions:
        return PreconditionOutcome(ok=True)

    prov = _provenance_primitives(inputs)

    for rule in preconditions:
        if not isinstance(rule, dict) or len(rule) != 1:
            failures.append(f"malformed precondition (expected exactly one key): {rule!r}")
            continue

        (predicate, value), = rule.items()

        if predicate == "provenance_contains":
            if value in prov:
                notes.append(f"precondition provenance_contains: {value} satisfied")
            else:
                failures.append(
                    f"provenance_contains: {value} not satisfied "
                    f"(no input was produced by '{value}')"
                )

        elif predicate == "no_unresolved_critical":
            has_critical = "critical" in _warning_levels(inputs)
            if bool(value) and has_critical:
                failures.append(
                    "no_unresolved_critical: an input carries an unresolved critical warning"
                )
            else:
                notes.append("precondition no_unresolved_critical satisfied")

        else:
            failures.append(f"unknown precondition predicate: '{predicate}'")

    return PreconditionOutcome(ok=(len(failures) == 0), failures=failures, notes=notes)
