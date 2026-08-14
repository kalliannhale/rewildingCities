#!/usr/bin/env python3
"""
Sprint 3 Verification — run from project root:
    python tests/test_sprint3.py

Tests the provider system without making real network calls.
Tests registry dispatch, provider routing, and advisory messages.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_registry_creation():
    """Test that all providers register correctly."""
    from canopy.providers import create_default_registry

    registry = create_default_registry()
    providers = registry.registered_providers

    print(f"  Registered providers: {providers}")

    expected = [
        "Local", "URL", "Manual", "Socrata", "ArcGIS REST",
        "Planetary Computer (STAC)", "AWS S3 (ESA WorldCover)",
        "Google Earth Engine",
    ]
    for name in expected:
        assert name in providers, f"FAIL: '{name}' not registered"
    print(f"  ✓ All {len(expected)} providers registered")


def test_provider_dispatch():
    """Test that the registry dispatches to the right provider."""
    from canopy.providers import create_default_registry

    registry = create_default_registry()

    test_cases = [
        ({"type": "local", "path": "/tmp/test"}, "Local"),
        ({"type": "url", "url": "https://example.com/data.tif"}, "URL"),
        ({"type": "manual", "notes": "Download from..."}, "Manual"),
        ({"type": "api", "provider": "socrata", "endpoint": "https://data.nyc.gov/..."}, "Socrata"),
        ({"type": "api", "provider": "arcgis_rest", "endpoint": "https://services.arcgis.com/..."}, "ArcGIS REST"),
        ({"type": "stac", "collection": "landsat-c2-l2"}, "Planetary Computer (STAC)"),
        ({"type": "s3", "provider": "esa_worldcover"}, "AWS S3 (ESA WorldCover)"),
        ({"type": "earthengine", "collection": "NOAA/VIIRS/..."}, "Google Earth Engine"),
    ]

    for source_config, expected_name in test_cases:
        provider = registry.find_provider(source_config)
        assert provider is not None, f"FAIL: no provider for {source_config}"
        assert provider.name == expected_name, (
            f"FAIL: expected '{expected_name}', got '{provider.name}' "
            f"for {source_config}"
        )
        print(f"  ✓ {source_config['type']}/{source_config.get('provider', '')} → {provider.name}")

    # Unknown type returns None
    unknown = registry.find_provider({"type": "ftp"})
    assert unknown is None, "FAIL: should return None for unknown type"
    print("  ✓ Unknown type → None")


def test_manual_advisory():
    """Test that ManualProvider gives advisory instead of acquiring."""
    from canopy.providers import create_default_registry

    registry = create_default_registry()
    result = registry.acquire(
        source_config={
            "type": "manual",
            "notes": "Download Landsat from USGS EarthExplorer and place at .data/lst_summer.tif"
        },
        cache_path=Path("/tmp/test_manual.tif"),
        dataset_name="land_surface_temperature",
    )

    assert not result.success, "FAIL: manual should not succeed"
    assert result.requires_manual, "FAIL: should flag requires_manual"
    assert result.manual_instructions is not None, "FAIL: should have instructions"
    assert "Landsat" in result.manual_instructions, "FAIL: instructions should contain source notes"
    print(f"  ✓ Manual provider returns advisory: {result.message[:60]}...")
    print(f"  ✓ Instructions: {result.manual_instructions[:60]}...")


def test_earthengine_advisory():
    """Test that EarthEngine provider gives auth advisory when not authenticated."""
    from canopy.providers import create_default_registry

    registry = create_default_registry()
    result = registry.acquire(
        source_config={
            "type": "earthengine",
            "collection": "NOAA/VIIRS/DNB/ANNUAL_V22",
            "band": "average_masked",
        },
        cache_path=Path("/tmp/test_ntl.tif"),
        dataset_name="nighttime_lights",
        gee_project="rewildingcities",
    )

    # This will fail because GEE isn't authenticated in the test env
    # (or succeed if it is — both are valid)
    if not result.success:
        assert result.requires_auth, "FAIL: should flag requires_auth"
        assert result.auth_instructions is not None, "FAIL: should have auth instructions"
        assert "earthengine authenticate" in result.auth_instructions, (
            "FAIL: instructions should mention authentication"
        )
        print(f"  ✓ GEE provider returns auth advisory: {result.message[:60]}...")
        print(f"  ✓ Auth instructions present")
    else:
        print(f"  ✓ GEE provider authenticated and acquired (unexpected but valid)")


def test_no_provider_message():
    """Test that unknown source types get clear error messages."""
    from canopy.providers import create_default_registry

    registry = create_default_registry()
    result = registry.acquire(
        source_config={"type": "ftp", "host": "ftp.example.com"},
        cache_path=Path("/tmp/test.dat"),
        dataset_name="test_dataset",
    )

    assert not result.success, "FAIL: unknown type should fail"
    assert "ftp" in result.message.lower(), "FAIL: message should mention the source type"
    print(f"  ✓ Unknown source type: {result.message[:70]}...")


def test_discovery():
    """Test that providers can discover datasets for a bounding box."""
    from canopy.providers import create_default_registry

    registry = create_default_registry()

    # NYC bounding box
    nyc_bbox = (-74.26, 40.49, -73.70, 40.92)

    results = registry.discover_all(nyc_bbox)
    print(f"  Discovered {len(results)} datasets for NYC bbox:")
    for r in results:
        auth = " (auth required)" if r.requires_auth else ""
        print(f"    {r.semantic_type}: {r.description[:50]}...{auth}")

    # Should find at least LST, NDVI, land_cover from STAC and S3
    types_found = {r.semantic_type for r in results}
    assert "land_surface_temperature" in types_found, "FAIL: should discover LST"
    assert "ndvi" in types_found, "FAIL: should discover NDVI"
    assert "land_cover" in types_found, "FAIL: should discover land cover"
    print(f"  ✓ Found: {', '.join(sorted(types_found))}")

    # Check that each result has a valid source_config
    for r in results:
        assert "type" in r.source_config, f"FAIL: {r.semantic_type} missing source_config.type"
    print("  ✓ All discoveries have valid source configs")


def test_manifest_integration():
    """Test that providers handle real manifest source configs."""
    from canopy.providers import create_default_registry
    from canopy.orchestrator.orchestrator import parse_manifest

    manifest_path = project_root / "plots" / "nyc" / "manifest.yml"
    if not manifest_path.exists():
        print("  SKIP — manifest not found")
        return

    registry = create_default_registry()
    manifest = parse_manifest(manifest_path)

    print(f"  Testing provider dispatch for all {len(manifest.datasets)} datasets:")
    for name, ds in manifest.datasets.items():
        if ds.source is None:
            print(f"    {name}: no source config")
            continue

        provider = registry.find_provider(ds.source)
        if provider:
            print(f"    ✓ {name} ({ds.source_type}/{ds.provider_name or ''}) → {provider.name}")
        else:
            print(f"    ✗ {name} ({ds.source_type}/{ds.provider_name or ''}) → NO PROVIDER")

    # Every dataset with a source should have a matching provider
    for name, ds in manifest.datasets.items():
        if ds.source is not None:
            provider = registry.find_provider(ds.source)
            assert provider is not None, (
                f"FAIL: no provider for {name} "
                f"(type={ds.source_type}, provider={ds.provider_name})"
            )
    print("  ✓ All datasets with source configs have matching providers")


if __name__ == "__main__":
    print("\n=== Sprint 3 Verification ===\n")

    for name, fn in [
        ("Test 1: Registry creation", test_registry_creation),
        ("Test 2: Provider dispatch", test_provider_dispatch),
        ("Test 3: Manual provider advisory", test_manual_advisory),
        ("Test 4: Earth Engine auth advisory", test_earthengine_advisory),
        ("Test 5: Unknown source type message", test_no_provider_message),
        ("Test 6: Provider discovery", test_discovery),
        ("Test 7: Real manifest integration", test_manifest_integration),
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
