"""
canopy/manifest/__init__.py

Manifest management: atomic transactions, surgical YAML editing, 
consistency checking, and changelog tracking.

The manifest is the community's declaration of what data their 
pipeline contains. Changes to it must be reliable, documented,
and reversible.
"""

from .surgeon import ManifestSurgeon
from .transaction import ManifestTransaction, TransactionResult

__all__ = [
    "ManifestSurgeon",
    "ManifestTransaction",
    "TransactionResult",
]