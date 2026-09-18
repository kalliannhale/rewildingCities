"""
canopy/api ~ the seam

the engine, offered over HTTP. it holds no science of its own: every read is
a projection of PlotReading and every action delegates to a capability that
already exists and is already tested. if a question can be answered here and
not in the CLI, something has been built in the wrong place. ~
"""

from .app import app

__all__ = ["app"]
