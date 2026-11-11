"""
canopy/loam/reach.py

reach ~ how one run reads what another run made (LOAM-1)

a step names what it needs by kind, `$loam.<semantic_type>`, never by who
made it (D-163). loam answers. the plot's bed is rebuilt fresh from its
receipts, and exactly one tended or gathered artifact of that kind must be
there (D-164):

  ~ one       its receipt is read back as an Envelope, so the step inherits
              its provenance and the precondition gate reads it, exactly as
              it would read the output of an earlier step in the same run
  ~ several   refused, naming each receipt, because which one is a choice,
              not a lookup
  ~ none      refused, naming the kinds that are here, and any receipt the
              bed could not read, since a missing kind is often a receipt
              that failed to settle
  ~ arrived   refused: a manifest dataset already has a name, $manifest.,
              and one dataset with two names is two routes that can disagree

reaching reads. it never writes a receipt and never moves a file. whether
what it reached is still current is judged separately (D-165, D-166). ~
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CONFORMED_TIERS = ("tended", "gathered")


class ReachRefusal(ValueError):
    """a $loam. read declines, naming why and what would let it proceed."""


@dataclass
class Reached:
    """one artifact a run reached for, and the receipt it was read from."""
    asked: str           # the type as the step wrote it
    semantic_type: str   # what it means today, through the vocabulary
    path: str            # the data, as its receipt records it
    receipt: str         # the receipt the envelope was read from
    envelope: object     # canopy.envelope.Envelope


class LoamReach:
    """
    the plot's bed, opened once per run, on first need.

    `directory` is the plot's own folder (the one its manifest lives in), so
    a run reads exactly the plot it belongs to, wherever that plot sits. ~
    """

    def __init__(self, plot: str, directory: str | Path, project_root: str | Path):
        self.plot = plot
        self.directory = Path(directory)
        self.project_root = Path(project_root)
        self._opened = None
        self.reached: dict[str, Reached] = {}

    def _open(self):
        if self._opened is None:
            from ..wonder.session import open_plot
            self._opened = open_plot(self.plot, root=self.project_root,
                                     directory=self.directory)
        return self._opened

    def reach(self, asked: str, context: str = "") -> Reached:
        if asked in self.reached:
            return self.reached[asked]
        where = f" (in {context})" if context else ""
        vocab, loam, report = self._open()

        resolution = vocab.resolve(asked)
        canonical = getattr(resolution, "canonical", None)
        if not canonical:
            raise ReachRefusal(
                f"$loam.{asked}{where}: the vocabulary has no type '{asked}', "
                f"so loam cannot say what would satisfy it")

        conformed = [row for tier in CONFORMED_TIERS
                     for row in loam.find(semantic_type=canonical, plot=self.plot, tier=tier)]

        if len(conformed) > 1:
            receipts = sorted(Path(r["receipt_path"] or "?").name for r in conformed)
            raise ReachRefusal(
                f"$loam.{asked}{where}: {len(conformed)} artifacts in plot "
                f"'{self.plot}' are {canonical}: {', '.join(receipts)}. which one "
                f"is a choice, not a lookup (D-163). remove the receipt that no "
                f"longer stands, or wait for a qualifier, which is not built yet")

        if not conformed:
            arrived = loam.find(semantic_type=canonical, plot=self.plot, tier="arrived")
            if arrived:
                raise ReachRefusal(
                    f"$loam.{asked}{where}: plot '{self.plot}' holds {canonical} "
                    f"only as a manifest dataset, not as anything a run made. "
                    f"read it as $manifest.<dataset> instead (D-164)")
            here = sorted({r["semantic_type"] for tier in CONFORMED_TIERS
                           for r in loam.find(plot=self.plot, tier=tier)
                           if r.get("semantic_type")})
            unread = [f"{r['receipt']} ({r['why']})" for r in report.get("tilled_refused") or []]
            message = (f"$loam.{asked}{where}: no run in plot '{self.plot}' has made "
                       f"{canonical}. made here: {', '.join(here) or 'nothing yet'}.")
            if unread:
                message += f" receipts loam could not read: {'; '.join(unread)}."
            raise ReachRefusal(message + " run the preparation that makes it first")

        row = conformed[0]
        from ..envelope import read_envelope
        receipt = row["receipt_path"]
        envelope = read_envelope(receipt, project_root=self.project_root)
        reached = Reached(asked=asked, semantic_type=canonical,
                          path=envelope.data.get("path") or row["data_path"],
                          receipt=receipt, envelope=envelope)
        self.reached[asked] = reached
        return reached
