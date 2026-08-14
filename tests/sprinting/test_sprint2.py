#!/usr/bin/env python3
"""
Sprint 2 Verification — run from project root:
    python tests/test_sprint2.py
"""

import sys
import shutil
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_surgeon_read_and_set():
    """Test that ManifestSurgeon can read and surgically edit fields."""
    from canopy.manifest.surgeon import ManifestSurgeon
    
    manifest_path = project_root / "plots" / "nyc" / "manifest.yml"
    if not manifest_path.exists():
        print("  SKIP — manifest not found")
        return
    
    # Work on a copy so we don't mutate the real manifest
    with tempfile.TemporaryDirectory() as tmp:
        tmp_manifest = Path(tmp) / "manifest.yml"
        shutil.copy2(manifest_path, tmp_manifest)
        
        surgeon = ManifestSurgeon(tmp_manifest)
        
        # Read
        text = surgeon.read()
        assert len(text) > 100, "FAIL: manifest text too short"
        print(f"  ✓ Read manifest: {len(text)} chars")
        
        # Set available flag
        new_text, ok = surgeon.set_available(text, "nighttime_lights", True)
        assert ok, "FAIL: set_available returned False"
        assert "available: true" in new_text.split("nighttime_lights:")[1].split("\n")[1], \
            "FAIL: available flag not changed in text"
        print("  ✓ set_available('nighttime_lights', True) succeeded")
        
        # Set it back
        new_text2, ok2 = surgeon.set_available(new_text, "nighttime_lights", False)
        assert ok2, "FAIL: set_available back to False failed"
        print("  ✓ set_available('nighttime_lights', False) succeeded")
        
        # Try a nonexistent dataset
        _, ok3 = surgeon.set_available(text, "totally_fake_dataset", True)
        assert not ok3, "FAIL: should return False for nonexistent dataset"
        print("  ✓ Nonexistent dataset returns False (no crash)")
        
        # Atomic write
        surgeon.write_atomic(new_text)
        reread = surgeon.read()
        assert reread == new_text, "FAIL: atomic write didn't persist"
        print("  ✓ write_atomic persists changes")


def test_transaction_commit():
    """Test that ManifestTransaction batches and commits atomically."""
    from canopy.manifest.transaction import ManifestTransaction
    
    manifest_path = project_root / "plots" / "nyc" / "manifest.yml"
    if not manifest_path.exists():
        print("  SKIP — manifest not found")
        return
    
    # Work on a copy
    with tempfile.TemporaryDirectory() as tmp:
        tmp_manifest = Path(tmp) / "manifest.yml"
        shutil.copy2(manifest_path, tmp_manifest)
        
        # Create transaction
        tx = ManifestTransaction(tmp_manifest)
        
        assert not tx.has_changes, "FAIL: fresh transaction should have no changes"
        print("  ✓ Fresh transaction has no changes")
        
        # Queue changes
        tx.set_available("nighttime_lights", True, "Test acquisition")
        tx.set_available("population_density", True, "Test acquisition")
        tx.update_cache_timestamp("nighttime_lights")
        
        assert tx.has_changes, "FAIL: should have pending changes"
        assert len(tx.pending_changes) == 3, f"FAIL: expected 3 pending, got {len(tx.pending_changes)}"
        print(f"  ✓ Queued {len(tx.pending_changes)} changes")
        
        # Commit
        result = tx.commit()
        print(f"  Transaction result: applied={result.changes_applied}, failed={result.changes_failed}")
        
        assert result.changes_applied >= 2, f"FAIL: expected at least 2 applied, got {result.changes_applied}"
        print(f"  ✓ Committed: {result.changes_applied} changes applied")
        
        # Verify the file was actually changed
        with open(tmp_manifest) as f:
            text = f.read()
        
        # Find nighttime_lights block and check available
        ntl_block = text.split("nighttime_lights:")[1].split("\n")
        found_available_true = any("available: true" in line for line in ntl_block[:5])
        assert found_available_true, "FAIL: nighttime_lights not set to available: true in file"
        print("  ✓ File on disk reflects changes")
        
        # Check changelog was written
        changelog_path = Path(tmp) / ".manifest_changelog.yml"
        assert changelog_path.exists(), "FAIL: changelog not created"
        print(f"  ✓ Changelog created at {changelog_path.name}")
        
        import yaml
        with open(changelog_path) as f:
            changelog = yaml.safe_load(f)
        assert isinstance(changelog, list), "FAIL: changelog should be a list"
        assert len(changelog) == 1, f"FAIL: expected 1 entry, got {len(changelog)}"
        entry = changelog[0]
        assert "timestamp" in entry, "FAIL: changelog entry missing timestamp"
        assert "changes" in entry, "FAIL: changelog entry missing changes"
        print(f"  ✓ Changelog entry has {len(entry['changes'])} change records")
        
        # Verify double-commit is rejected
        result2 = tx.commit()
        assert result2.changes_applied == 0, "FAIL: double commit should apply 0"
        print("  ✓ Double commit correctly rejected")


def test_transaction_rollback():
    """Test that rollback discards pending changes."""
    from canopy.manifest.transaction import ManifestTransaction
    
    manifest_path = project_root / "plots" / "nyc" / "manifest.yml"
    if not manifest_path.exists():
        print("  SKIP — manifest not found")
        return
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp_manifest = Path(tmp) / "manifest.yml"
        shutil.copy2(manifest_path, tmp_manifest)
        
        tx = ManifestTransaction(tmp_manifest)
        tx.set_available("nighttime_lights", True, "Should be rolled back")
        
        assert tx.has_changes
        tx.rollback()
        assert not tx.has_changes, "FAIL: rollback didn't clear changes"
        print("  ✓ Rollback clears pending changes")
        
        # Verify file unchanged
        with open(tmp_manifest) as f:
            text = f.read()
        with open(manifest_path) as f:
            original = f.read()
        assert text == original, "FAIL: file was modified despite rollback"
        print("  ✓ File unchanged after rollback")


def test_transaction_context_manager():
    """Test context manager usage."""
    from canopy.manifest.transaction import ManifestTransaction
    
    manifest_path = project_root / "plots" / "nyc" / "manifest.yml"
    if not manifest_path.exists():
        print("  SKIP — manifest not found")
        return
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp_manifest = Path(tmp) / "manifest.yml"
        shutil.copy2(manifest_path, tmp_manifest)
        
        # Normal exit — should commit
        with ManifestTransaction(tmp_manifest) as tx:
            tx.set_available("nighttime_lights", True, "Context manager test")
        
        with open(tmp_manifest) as f:
            text = f.read()
        ntl_section = text.split("nighttime_lights:")[1][:200]
        assert "available: true" in ntl_section, "FAIL: context manager didn't commit"
        print("  ✓ Context manager commits on clean exit")


if __name__ == "__main__":
    print("\n=== Sprint 2 Verification ===\n")
    
    for name, fn in [
        ("Test 1: ManifestSurgeon read and set", test_surgeon_read_and_set),
        ("Test 2: ManifestTransaction commit", test_transaction_commit),
        ("Test 3: ManifestTransaction rollback", test_transaction_rollback),
        ("Test 4: ManifestTransaction context manager", test_transaction_context_manager),
    ]:
        print(name)
        try:
            fn()
            print("  PASSED\n")
        except Exception as e:
            print(f"  FAILED: {e}\n")
            import traceback
            traceback.print_exc()
            print()
    
    print("=== Done ===")
