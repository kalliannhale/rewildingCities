#!/usr/bin/env python3
"""
Sprint 1 Verification — run from project root:
    python tests/test_sprint1.py
"""

import sys
from pathlib import Path

# Add project root to path if needed
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_parse_manifest():
    """Test that parse_manifest loads all datasets with full config."""
    from canopy.orchestrator.orchestrator import parse_manifest
    
    manifest_path = project_root / "plots" / "nyc" / "manifest.yml"
    if not manifest_path.exists():
        print(f"  SKIP — manifest not found at {manifest_path}")
        return
    
    m = parse_manifest(manifest_path)
    
    # Should load ALL datasets, not just available ones
    total = len(m.datasets)
    available = len(m.available_datasets())
    unavailable = len(m.unavailable_datasets())
    acquirable = len(m.acquirable_datasets())
    
    print(f"  Total datasets:      {total}")
    print(f"  Available:           {available}")
    print(f"  Unavailable:         {unavailable}")
    print(f"  Auto-acquirable:     {acquirable}")
    
    assert total > available, (
        f"FAIL: total ({total}) should be > available ({available}). "
        f"parse_manifest is still filtering out unavailable datasets."
    )
    assert total == available + unavailable, (
        f"FAIL: total ({total}) != available ({available}) + unavailable ({unavailable})"
    )
    print("  ✓ All datasets loaded (available + unavailable)")
    
    # Check that unavailable datasets exist (NTL and population should be there)
    for name in ["nighttime_lights", "population_density"]:
        if name in m.datasets:
            ds = m.datasets[name]
            assert not ds.available, f"FAIL: {name} should be unavailable"
            print(f"  ✓ {name} loaded as unavailable")
        else:
            print(f"  WARN: {name} not in manifest (expected but not required)")
    
    # Check source config preserved
    parks = m.datasets.get("park_boundaries")
    if parks:
        assert parks.source is not None, "FAIL: park_boundaries source config is None"
        assert parks.source_type == "api", f"FAIL: expected source_type 'api', got '{parks.source_type}'"
        assert parks.provider_name == "socrata", f"FAIL: expected provider 'socrata', got '{parks.provider_name}'"
        assert parks.is_auto_acquirable, "FAIL: park_boundaries should be auto-acquirable"
        assert not parks.requires_auth, "FAIL: park_boundaries should not require auth"
        print(f"  ✓ park_boundaries: source={parks.source_type}/{parks.provider_name}, auto_acquirable=True")
    
    lst = m.datasets.get("land_surface_temperature")
    if lst:
        assert lst.source is not None, "FAIL: LST source config is None"
        assert lst.source_type == "manual", f"FAIL: expected LST source_type 'manual', got '{lst.source_type}'"
        assert lst.requires_manual_action, "FAIL: LST should require manual action"
        assert not lst.is_auto_acquirable, "FAIL: LST (manual) should not be auto-acquirable"
        print(f"  ✓ land_surface_temperature: source={lst.source_type}, requires_manual=True")
    
    # Check GEE datasets
    ntl = m.datasets.get("nighttime_lights")
    if ntl and ntl.source:
        assert ntl.source_type == "earthengine", f"FAIL: expected NTL source_type 'earthengine', got '{ntl.source_type}'"
        assert ntl.requires_auth, "FAIL: NTL (earthengine) should require auth"
        print(f"  ✓ nighttime_lights: source={ntl.source_type}, requires_auth=True")
    
    # Check manifest-level fields
    assert m.city_name == "New York City", f"FAIL: city_name is '{m.city_name}'"
    assert m.city_id == "nyc", f"FAIL: city_id is '{m.city_id}'"
    assert m.manifest_path is not None, "FAIL: manifest_path should be set"
    assert m.crs_working == "EPSG:2263", f"FAIL: crs_working is '{m.crs_working}'"
    print(f"  ✓ Manifest metadata: {m.city_name} ({m.city_id}), CRS={m.crs_working}")
    
    # Check consistency
    issues = m.check_consistency()
    print(f"  Consistency issues found: {len(issues)}")
    for issue in issues:
        print(f"    {issue.issue}: {issue.dataset_name} — {issue.suggestion[:80]}...")
    
    print("  ✓ check_consistency() runs without error")


def test_reference_resolver_unavailable():
    """Test that _resolve_manifest_ref gives clear errors for unavailable datasets."""
    from canopy.orchestrator.orchestrator import parse_manifest, parse_experiment, Experiment, Manifest
    from canopy.orchestrator.references import ReferenceResolver
    
    manifest_path = project_root / "plots" / "nyc" / "manifest.yml"
    if not manifest_path.exists():
        print("  SKIP — manifest not found")
        return
    
    m = parse_manifest(manifest_path)
    
    # We need a minimal experiment to construct the resolver
    # Find any experiment file
    exp_dir = project_root / "plots" / "nyc" / "experiments"
    exp_files = list(exp_dir.glob("*.yml")) if exp_dir.exists() else []
    
    if not exp_files:
        # Create a minimal fake experiment for testing
        print("  SKIP — no experiment files found, testing with manifest only")
        return
    
    exp = parse_experiment(exp_files[0])
    resolver = ReferenceResolver(manifest=m, experiment=exp)
    
    # Test 1: Available dataset should resolve (if file exists)
    try:
        path, stype, env = resolver._resolve_manifest_ref("park_boundaries", "test")
        print(f"  ✓ park_boundaries resolved to {path}")
    except FileNotFoundError as e:
        print(f"  ✓ park_boundaries available but file missing (expected on fresh clone): {str(e)[:80]}...")
    except ValueError as e:
        print(f"  ✗ park_boundaries raised ValueError (unexpected): {str(e)[:80]}...")
    
    # Test 2: Unavailable dataset should raise ValueError with advisory
    unavailable_names = [name for name, ds in m.datasets.items() if not ds.available]
    if unavailable_names:
        test_name = unavailable_names[0]
        try:
            resolver._resolve_manifest_ref(test_name, "test")
            print(f"  ✗ FAIL: {test_name} should have raised ValueError (it's unavailable)")
        except ValueError as e:
            error_msg = str(e)
            assert "not available" in error_msg.lower() or "unavailable" in error_msg.lower() or "not yet available" in error_msg.lower(), (
                f"FAIL: Error message should mention availability. Got: {error_msg[:100]}"
            )
            print(f"  ✓ {test_name} correctly raises ValueError: {error_msg[:80]}...")
    else:
        print("  SKIP — no unavailable datasets to test against")
    
    # Test 3: Nonexistent dataset should still raise ValueError
    try:
        resolver._resolve_manifest_ref("totally_fake_dataset", "test")
        print("  ✗ FAIL: totally_fake_dataset should have raised ValueError")
    except ValueError as e:
        assert "no dataset" in str(e).lower() or "has no dataset" in str(e).lower(), (
            f"FAIL: Error should say dataset not found. Got: {str(e)[:100]}"
        )
        print(f"  ✓ Nonexistent dataset raises correct error")


if __name__ == "__main__":
    print("\n=== Sprint 1 Verification ===\n")
    
    print("Test 1: parse_manifest loads all datasets with full config")
    try:
        test_parse_manifest()
        print("  PASSED\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        import traceback
        traceback.print_exc()
    
    print("Test 2: _resolve_manifest_ref handles availability correctly")
    try:
        test_reference_resolver_unavailable()
        print("  PASSED\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        import traceback
        traceback.print_exc()
    
    print("=== Done ===")
