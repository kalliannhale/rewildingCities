"""

canopy/wonder ~ the accessible front door of the garden

wonder meets a person at their question about their community ~ a child,
an elder, an organizer, a shop owner ~ shows them what data we gathered for
their place (possibility), binds their chosen question into a real,
runnable experiment (wondering), and says it plainly for anyone (voice).
the door does not lock: everyone may enter, try, and learn ~ even from a
documented wrong answer. discovery in plain words; the orchestrator you
already built does the running. ♡

"""

from .possibility import explore, MethodPossibility, present_types
from .wondering import compose, Composed, Guidance
from .voice import speak

__all__ = [
    "explore", "MethodPossibility", "present_types",
    "compose", "Composed", "Guidance", "speak",
]
