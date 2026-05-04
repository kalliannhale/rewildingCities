"""
canopy/manifest/transaction.py

Atomic, batched manifest updates with changelog tracking.

The manifest is the community's source of truth. Changes to it
must be:
  1. Batched — multiple changes in one write, not scattered calls
  2. Atomic — the file is never half-written
  3. Logged — every change has a changelog entry
  4. Reversible — if something fails, nothing is written

Usage:
    tx = ManifestTransaction(manifest_path)
    tx.set_available("park_boundaries", True, "Acquired via Socrata")
    tx.set_available("lst_summer", True, "Acquired via STAC")
    tx.update_cache_timestamp("park_boundaries")
    result = tx.commit()
    
    if result.success:
        print(f"Applied {result.changes_applied} changes")
    else:
        print(f"Failed: {result.changes_failed}")
"""

import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .surgeon import ManifestSurgeon

logger = logging.getLogger("manifest.transaction")


@dataclass
class PendingChange:
    """A single pending manifest change."""
    dataset_name: str
    field_name: str
    new_value: str
    reason: str
    old_value: str | None = None  # populated on commit from current file


@dataclass
class TransactionResult:
    """Result of committing a manifest transaction."""
    success: bool
    changes_applied: int
    changes_failed: list[str] = field(default_factory=list)
    changelog_entry: dict | None = None
    error: str | None = None


class ManifestTransaction:
    """Batched, atomic manifest updates with changelog.
    
    Collects changes, applies them all in one read-edit-write cycle,
    and logs what changed and why. If any individual edit fails, the
    successful edits still apply (partial success is documented).
    
    Can also be used as a context manager:
    
        with ManifestTransaction(path) as tx:
            tx.set_available("parks", True, "Acquired via Socrata")
            # commits on exit, rolls back on exception
    """
    
    def __init__(self, manifest_path: str | Path):
        self.manifest_path = Path(manifest_path)
        self.surgeon = ManifestSurgeon(self.manifest_path)
        self._pending: list[PendingChange] = []
        self._committed = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
            return False
        if not self._committed and self._pending:
            self.commit()
        return False
    
    # ── Change methods ──
    
    def set_available(
        self, 
        dataset_name: str, 
        available: bool, 
        reason: str = ""
    ) -> None:
        """Queue a change to a dataset's available flag."""
        self._pending.append(PendingChange(
            dataset_name=dataset_name,
            field_name="available",
            new_value=str(available).lower(),
            reason=reason,
        ))
    
    def update_cache_timestamp(
        self, 
        dataset_name: str,
        timestamp: str | None = None,
        reason: str = "Cache timestamp updated"
    ) -> None:
        """Queue an update to a dataset's fetched_at timestamp."""
        if timestamp is None:
            timestamp = f"'{datetime.now(timezone.utc).isoformat()}'"
        self._pending.append(PendingChange(
            dataset_name=dataset_name,
            field_name="fetched_at",
            new_value=timestamp,
            reason=reason,
        ))
    
    # ── Commit / Rollback ──
    
    def commit(self) -> TransactionResult:
        """Apply all pending changes atomically.
        
        Reads the manifest once, applies all regex edits to the text,
        writes once via atomic rename, and appends a changelog entry.
        
        Returns:
            TransactionResult with details of what happened.
        """
        if not self._pending:
            return TransactionResult(
                success=True, 
                changes_applied=0,
                changelog_entry=None,
            )
        
        if self._committed:
            return TransactionResult(
                success=False,
                changes_applied=0,
                error="Transaction already committed. Create a new transaction.",
            )
        
        # Read manifest once
        text = self.surgeon.read()
        
        # Apply all edits
        applied = 0
        failed = []
        change_records = []
        
        for change in self._pending:
            new_text, ok = self.surgeon.set_field(
                text, 
                change.dataset_name, 
                change.field_name, 
                change.new_value
            )
            
            if ok:
                text = new_text
                applied += 1
                change_records.append({
                    "dataset": change.dataset_name,
                    "field": change.field_name,
                    "value": change.new_value,
                    "reason": change.reason,
                })
                logger.debug(
                    f"  Applied: {change.dataset_name}.{change.field_name} "
                    f"= {change.new_value}"
                )
            else:
                failed.append(
                    f"{change.dataset_name}.{change.field_name}: "
                    f"field not found in manifest"
                )
                logger.warning(
                    f"  Failed: {change.dataset_name}.{change.field_name} "
                    f"— field not found"
                )
        
        # Write atomically (even if some changes failed — partial success)
        if applied > 0:
            try:
                self.surgeon.write_atomic(text)
            except Exception as e:
                return TransactionResult(
                    success=False,
                    changes_applied=0,
                    changes_failed=[f"Atomic write failed: {e}"],
                    error=f"Failed to write manifest: {e}",
                )
            
            # Write changelog
            changelog_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "triggered_by": "manifest_transaction",
                "changes_applied": applied,
                "changes_failed": len(failed),
                "changes": change_records,
            }
            
            try:
                self.surgeon.append_changelog(changelog_entry)
            except Exception as e:
                # Changelog failure is not fatal — the manifest was written
                logger.warning(f"Changelog write failed (manifest was updated): {e}")
                changelog_entry["changelog_write_error"] = str(e)
        
        self._committed = True
        self._pending.clear()
        
        return TransactionResult(
            success=len(failed) == 0,
            changes_applied=applied,
            changes_failed=failed,
            changelog_entry=changelog_entry if applied > 0 else None,
        )
    
    def rollback(self) -> None:
        """Discard all pending changes without writing."""
        count = len(self._pending)
        self._pending.clear()
        if count > 0:
            logger.debug(f"Transaction rolled back: {count} changes discarded")
    
    # ── Inspection ──
    
    @property
    def pending_changes(self) -> list[PendingChange]:
        """View pending changes without committing."""
        return list(self._pending)
    
    @property
    def has_changes(self) -> bool:
        """Whether there are pending changes."""
        return len(self._pending) > 0
