#!/usr/bin/env python3
"""
Quick test script to verify the provider refactoring works correctly.
"""

import sys

def test_config_system():
    """Test the configuration system."""
    print("Testing configuration system...")
    from flight_tracker.config import config

    providers = config.get_all_providers()
    print(f"  ✓ Found {len(providers)} registered providers")

    for provider_id in providers.keys():
        print(f"    - {provider_id}")

    return True

def test_provider_factory():
    """Test the provider factory."""
    print("\nTesting provider factory...")
    from flight_tracker.provider_factory import ProviderFactory

    # Test creating mock provider
    mock_provider = ProviderFactory.create_provider('mock', 'USD')
    print(f"  ✓ Created mock provider: {mock_provider.__class__.__name__}")

    # Test list available providers
    available = ProviderFactory.list_available_providers()
    print(f"  ✓ Available providers: {list(available.keys())}")

    # Test validation
    validation = ProviderFactory.validate_provider('mock')
    print(f"  ✓ Mock provider validation: {validation['valid']}")

    return True

def test_app_endpoints():
    """Test Flask app endpoints."""
    print("\nTesting Flask app...")
    from app import app

    routes = [str(rule) for rule in app.url_map.iter_rules()]
    print(f"  ✓ App created with {len(routes)} routes")

    # Check if /api/providers exists
    has_providers_endpoint = any('/api/providers' in route for route in routes)
    if has_providers_endpoint:
        print("  ✓ /api/providers endpoint exists")
    else:
        print("  ✗ /api/providers endpoint NOT FOUND")
        return False

    return True

def test_cli():
    """Test CLI functionality."""
    print("\nTesting CLI...")
    import subprocess

    result = subprocess.run(
        ['python', '-m', 'flight_tracker.main', '--list-providers'],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("  ✓ CLI --list-providers works")
        if 'mock' in result.stdout and 'amadeus' in result.stdout:
            print("  ✓ CLI shows both providers")
        else:
            print("  ✗ CLI output incomplete")
            return False
    else:
        print(f"  ✗ CLI failed: {result.stderr}")
        return False

    return True

def main():
    """Run all tests."""
    print("="*60)
    print("PROVIDER REFACTORING VERIFICATION")
    print("="*60 + "\n")

    tests = [
        test_config_system,
        test_provider_factory,
        test_app_endpoints,
        test_cli
    ]

    results = []
    for test in tests:
        try:
            success = test()
            results.append(success)
        except Exception as e:
            print(f"  ✗ Test failed with error: {e}")
            results.append(False)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(results)
    total = len(results)

    if all(results):
        print(f"✅ All {total} tests passed!")
        return 0
    else:
        print(f"❌ {passed}/{total} tests passed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
