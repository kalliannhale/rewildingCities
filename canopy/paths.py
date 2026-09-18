"""
canopy/paths.py

paths ~ finding the garden, once, for everyone

the garden is a directory tree (seeds/, garden/, plots/, roots/, soil/), and
every reader needs to know where it is. three separate finders used to answer
that question, and all three ended the same way: `return Path.cwd()` when the
search failed.

that fallback is the whole bug. from the repo root it happens to be right, so
it looks like it works. from a server process, or a scheduled job, or a
container with a different working directory, it silently returns somewhere
unrelated and every read comes back empty ~ no error, just a vocabulary with
no types and a garden with no curiosities. the same silent degradation as a
missing domains directory, and the same answer: refuse rather than guess. ♡

the search, in order:
  ~ REWILDING_ROOT. in any real deployment this is THE mechanism, not a
    nicety: once canopy is installed into site-packages the garden lives
    somewhere else entirely and no amount of walking upward will find it.
  ~ upward from this package's own file ~ a development checkout, where the
    code sits inside the garden. stable whatever the cwd, which is the point.
  ~ upward from the cwd ~ the same case, reached differently.
  ~ nothing found -> raise, naming what was looked for and where.

this module DISCOVERS a root. it is the right shape for a CLI and for
development, and the wrong shape for a server, where the garden's location
is configuration rather than something to be found. when the API entry point
exists it should resolve the root once and pass it down, and the constructors
that currently discover for themselves should require it instead. P-17. ~
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# a directory is the garden when it holds these. seeds/ carries the vocabulary
# and the schemas; garden/ carries the curiosities and methods. both are
# required, because either alone is a different tree that happens to share a
# name.
_MARKERS = ("seeds", "garden")

ENV_VAR = "REWILDING_ROOT"


class GardenNotFound(RuntimeError):
    """Raised when no directory holding seeds/ and garden/ can be located."""


def _is_root(candidate: Path) -> bool:
    return all((candidate / marker).is_dir() for marker in _MARKERS)


def _walk_up(start: Path) -> Path | None:
    start = start.resolve()
    for parent in [start, *start.parents]:
        if _is_root(parent):
            return parent
    return None


@lru_cache(maxsize=1)
def project_root() -> Path:
    # cached because it cannot change within a process ~ but a test that
    # builds a temp garden needs to say so: project_root.cache_clear().
    """
    The garden's root. Cached, because it cannot change within a process.

    Raises:
        GardenNotFound: if no candidate holds both seeds/ and garden/.
    """
    declared = os.environ.get(ENV_VAR)
    if declared:
        candidate = Path(declared).expanduser().resolve()
        if _is_root(candidate):
            return candidate
        raise GardenNotFound(
            f"{ENV_VAR} is set to {candidate}, which does not hold "
            f"{' and '.join(m + '/' for m in _MARKERS)}."
        )

    from_package = _walk_up(Path(__file__).parent)
    if from_package is not None:
        return from_package

    from_cwd = _walk_up(Path.cwd())
    if from_cwd is not None:
        return from_cwd

    raise GardenNotFound(
        "could not locate the garden: no ancestor of "
        f"{Path(__file__).parent} or {Path.cwd()} holds "
        f"{' and '.join(m + '/' for m in _MARKERS)}.\n"
        f"  set {ENV_VAR} to the directory that does, or run from inside a "
        f"rewildingCities checkout."
    )


def schemas_dir() -> Path:
    """seeds/schemas ~ the vocabulary and the envelope contract."""
    return project_root() / "seeds" / "schemas"


def garden_dir() -> Path:
    """garden/ ~ curiosities, methods, experiments."""
    return project_root() / "garden"


def plot_dir(plot: str) -> Path:
    """one community's plot."""
    return project_root() / "plots" / plot


def loam_bed(plot: str) -> Path:
    """a plot's re-derivable mart. gitignored; rebuilt from the receipts."""
    return plot_dir(plot) / ".loam" / "loam.duckdb"


def envelopes_dir(plot: str) -> Path:
    """a plot's receipts."""
    return plot_dir(plot) / ".envelopes"
