"""
canopy/indicators ~ what a number means, and everything that computes it

  registry  every indicator, declared once in seeds/indicators/*.yml
  weights   every weighting, declared once in seeds/weights/*.yml
  preview   indicator values in Python, labelled preview, and the hand
            check against a published file (python -m canopy.indicators.preview)
  oracle    the later stages of CII's method in Python, held to the R
            primitives that perform them

the registry is the package's public face, so `from canopy.indicators import
IndicatorRegistry` reads the same as it always has. ♡
"""

from .registry import Derivation, Indicator, IndicatorRegistry

__all__ = ["Derivation", "Indicator", "IndicatorRegistry"]