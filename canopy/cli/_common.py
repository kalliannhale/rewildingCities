"""
canopy/cli/_common.py 

~ shared helpers for the rewilding CLI.
"""

from __future__ import annotations

from pathlib import Path


def find_root(start: Path | None = None) -> Path:
    """
    the project root ~ the nearest ancestor holding seeds/ and garden/. ~
    """

    here = (start or Path.cwd()).resolve()

    for parent in [here, *here.parents]:
        if (parent / "seeds").is_dir() and (parent / "garden").is_dir():
            return parent
        
    return Path.cwd()