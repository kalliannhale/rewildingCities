"""
canopy/expose/ ~ the one gate (Contract 1)

the system may compute with anything; what leaves it is decided here, by one
function, at every exit. no other module holds tier logic.
"""

from .gate import GATE_VERSION, SHARING_LEVELS, TIERS, decide, exposure_tier

__all__ = ["GATE_VERSION", "SHARING_LEVELS", "TIERS", "decide", "exposure_tier"]
