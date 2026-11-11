"""
canopy/loam/freshness.py

freshness ~ whether what a run reached is still what its makers declared

a receipt remembers how its artifact was made: every step that touched it,
each step's inputs with their hashes, and each step's params. this asks two
questions of that memory, without trusting it blindly (D-165):

  ~ inputs   is every recorded input still the file it was? each hash is
             recomputed the way it was first taken (full_file or metadata);
             a skipped hash, or a file no longer on disk, cannot be told
  ~ params   would each step be declared the same way today? the step's run
             is found by its id in the plot's preparations/ and experiments/,
             and its params are resolved now exactly as the orchestrator
             resolves them, then compared with what was recorded. an entry
             from before D-167 names no run or step, and cannot be told

three verdicts, never two (D-166):

  ~ fresh        everything checked is unchanged
  ~ stale        something checked differs: the run that reads it refuses,
                 naming what differs and which runs to rerun
  ~ cannot_tell  nothing checked differs, but something could not be
                 checked: the run proceeds, and says so in its receipts

primitive code is not judged, and every verdict says so, so the gap is seen
rather than implied away (D-165, KIT-1). a verdict reads; it never writes. ~
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

FRESH = "fresh"
STALE = "stale"
CANNOT_TELL = "cannot_tell"

NOT_JUDGED = "primitive code is not checked (D-165)"


@dataclass
class Verdict:
    """what was found about one reached artifact."""
    status: str
    changed: list[str] = field(default_factory=list)       # why it is stale
    untold: list[str] = field(default_factory=list)        # what could not be told
    rerun: list[str] = field(default_factory=list)         # runs that would refresh it
    checked_inputs: int = 0
    checked_steps: int = 0

    def summary(self, asked: str, receipt: str) -> str:
        name = Path(receipt).name
        if self.status == STALE:
            text = (f"$loam.{asked} ({name}) is stale: " + "; ".join(self.changed)
                    + f". rerun {', '.join(self.rerun) or 'the run that made it'} first.")
        elif self.status == CANNOT_TELL:
            text = (f"$loam.{asked} ({name}): freshness cannot be fully told: "
                    + "; ".join(self.untold) + ". everything that could be checked is unchanged.")
        else:
            text = (f"$loam.{asked} ({name}) is fresh: {self.checked_inputs} input(s) and "
                    f"{self.checked_steps} step declaration(s) unchanged.")
        return f"{text} {NOT_JUDGED}"

    def as_record(self, asked: str, receipt: str) -> dict:
        return {"type": asked, "receipt": str(receipt), "verdict": self.status,
                "changed": list(self.changed), "untold": list(self.untold),
                "not_judged": "primitive code"}


def _rehash(path: Path, method: str):
    from ..envelope import Hasher
    profile = {"full_file": "full", "metadata": "dev"}[method]
    return Hasher(profile=profile).hash_file(path).value


def _entry_label(entry) -> str:
    if entry.run and entry.step:
        return f"step {entry.step} of {entry.run}"
    return f"{entry.primitive} (a step from before D-167)"


def judge(envelope, project_root: str | Path,
          declared_params: Callable[[str, str], tuple[dict | None, str | None]]) -> Verdict:
    """
    judge one reached envelope. `declared_params(run, step)` returns the
    step's params as declared and resolved today, or (None, why) when they
    cannot be found or resolved. the orchestrator supplies it, so the
    comparison resolves params exactly as a run would. ~
    """
    root = Path(project_root)
    changed, untold, rerun = [], [], []
    inputs_seen, steps_seen = set(), set()
    checked_inputs = checked_steps = 0
    unnamed = 0

    for entry in envelope.provenance:
        label = _entry_label(entry)

        for record in entry.inputs:
            key = (record.path, record.hash.method, record.hash.value)
            if key in inputs_seen:
                continue                      # LIN-2: one input, recorded twice
            inputs_seen.add(key)
            if record.hash.method == "skipped" or not record.hash.value:
                untold.append(f"input {record.name} of {label} was not hashed "
                              f"({record.hash.reason or 'skipped'})")
                continue
            path = Path(record.path)
            path = path if path.is_absolute() else root / path
            if not path.is_file():
                untold.append(f"input {record.name} of {label} is no longer on disk "
                              f"({record.path})")
                continue
            checked_inputs += 1
            if _rehash(path, record.hash.method) != record.hash.value:
                changed.append(f"input {record.name} ({record.path}) has changed since "
                               f"{label} used it")
                if entry.run and entry.run not in rerun:
                    rerun.append(entry.run)

        if not (entry.run and entry.step):
            unnamed += 1
            continue
        step_key = (entry.run, entry.step, json.dumps(entry.params, sort_keys=True, default=str))
        if step_key in steps_seen:
            continue
        steps_seen.add(step_key)
        now, why = declared_params(entry.run, entry.step)
        if now is None:
            untold.append(f"{label}: {why}")
            continue
        checked_steps += 1
        before = json.loads(json.dumps(entry.params, sort_keys=True, default=str))
        after = json.loads(json.dumps(now, sort_keys=True, default=str))
        if before != after:
            keys = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
            changed.append(f"{label} is now declared with different params "
                           f"({', '.join(keys)})")
            if entry.run not in rerun:
                rerun.append(entry.run)

    if unnamed:
        untold.append(f"{unnamed} step(s) were recorded before D-167 and name no run "
                      f"or step, so their params cannot be compared with a declaration")

    status = STALE if changed else (CANNOT_TELL if untold else FRESH)
    return Verdict(status=status, changed=changed, untold=untold, rerun=rerun,
                   checked_inputs=checked_inputs, checked_steps=checked_steps)
