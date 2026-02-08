#!/usr/bin/env python3
"""
Master test runner for Flights Finder application.

Runs all tests and provides a summary of results.
"""

import sys
import os
import unittest
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set test environment variables
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"
os.environ["AMADEUS_API_KEY"] = "test_key"
os.environ["AMADEUS_API_SECRET"] = "test_secret"


def run_all_tests():
    """Run all tests and display summary."""
    print("=" * 80)
    print("FLIGHT TRACKER - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print()

    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')

    # Run tests
    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed_time = time.time() - start_time

    # Print summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests Run:     {result.testsRun}")
    print(f"Successes:     {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures:      {len(result.failures)}")
    print(f"Errors:        {len(result.errors)}")
    print(f"Skipped:       {len(result.skipped)}")
    print(f"Time Elapsed:  {elapsed_time:.2f}s")
    print("=" * 80)

    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


def run_test_file(filename):
    """Run a specific test file."""
    print(f"\nRunning tests from: {filename}")
    print("=" * 80)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(f'tests.{filename[:-3]}')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


def print_usage():
    """Print usage information."""
    print("Usage:")
    print("  python run_tests.py              # Run all tests")
    print("  python run_tests.py test_name.py # Run specific test file")
    print()
    print("Available test files:")
    print("  test_flight_tool.py         - FlightTool wrapper tests")
    print("  test_api_endpoints.py       - Flask API endpoint tests")
    print("  test_amadeus_provider.py    - Amadeus provider tests")
    print("  test_agent_tracking.py      - Agent tracking loop tests")
    print("  test_currency_conversion.py - Currency conversion tests")
    print("  test_full_search_flow.py    - End-to-end search flow tests")
    print("  test_thread_safety.py       - Thread safety tests")
    print("  test_return_pricing.py      - Return flight pricing tests")
    print("  test_price_filtering.py     - Price filtering tests")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help', 'help']:
            print_usage()
            sys.exit(0)
        else:
            # Run specific test file
            test_file = sys.argv[1]
            if not test_file.startswith('test_'):
                test_file = 'test_' + test_file
            if not test_file.endswith('.py'):
                test_file = test_file + '.py'

            sys.exit(run_test_file(test_file))
    else:
        # Run all tests
        sys.exit(run_all_tests())
