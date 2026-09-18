"""
canopy/cli/_common.py

~ shared helpers for the rewilding CLI.
"""

from __future__ import annotations

from pathlib import Path

from canopy.paths import project_root


def find_root(start: Path | None = None) -> Path:
    """
    the project root ~ the nearest ancestor holding seeds/ and garden/.

    delegates to canopy.paths.project_root(), which searches from the
    installed package rather than only from the cwd, and RAISES rather than
    returning Path.cwd() when the garden cannot be found. the old fallback
    looked like it worked from a checkout and silently returned an unrelated
    directory anywhere else. C-04. ~
    """
    if start is not None:
        resolved = Path(start).resolve()
        for parent in [resolved, *resolved.parents]:
            if (parent / "seeds").is_dir() and (parent / "garden").is_dir():
                return parent
    return project_root()
