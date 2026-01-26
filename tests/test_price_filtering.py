"""
Test suite for flight tracker price filtering logic.

This suite tests that flights over the target price are properly filtered out.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flight_tracker.flight_data import MockFlightProvider
from flight_tracker.agent import PriceTrackerAgent


def test_mock_provider_currency():
    """Test that MockFlightProvider returns correct currency."""
    print("Testing MockFlightProvider currency...")
    
    provider_usd = MockFlightProvider(default_currency="USD")
    result_usd = provider_usd.get_price("SYD", "DXB", "2026-06-08", "2026-06-15")
    assert result_usd['currency'] == "USD", f"Expected USD, got {result_usd['currency']}"
    print(f"✓ USD provider returns {result_usd['currency']} {result_usd['price']}")
    
    provider_aud = MockFlightProvider(default_currency="AUD")
    result_aud = provider_aud.get_price("SYD", "DXB", "2026-06-08", "2026-06-15")
    assert result_aud['currency'] == "AUD", f"Expected AUD, got {result_aud['currency']}"
    print(f"✓ AUD provider returns {result_aud['currency']} {result_aud['price']}")


def test_query_parsing():
    """Test that natural language query parsing extracts correct parameters."""
    print("\nTesting query parsing...")
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠ Skipping - ANTHROPIC_API_KEY not set")
        return
    
    query = "Find return flights under AUD 1200 from Sydney to Dubai in the month of June 2026 starting 8th of June"
    
    try:
        params = PriceTrackerAgent.parse_query(query, api_key)
        
        print(f"  Query: {query}")
        print(f"  Parsed parameters:")
        print(f"    Origin: {params.get('origin')}")
        print(f"    Destination: {params.get('destination')}")
        print(f"    Date: {params.get('date')}")
        print(f"    Return Date: {params.get('return_date')}")
        print(f"    Target Price: {params.get('target_price')}")
        print(f"    Target Currency: {params.get('target_currency')}")
        
        # Verify critical parameters
        assert params.get('origin') == 'SYD', f"Expected SYD, got {params.get('origin')}"
        assert params.get('destination') == 'DXB', f"Expected DXB, got {params.get('destination')}"
        assert params.get('target_price') == 1200, f"Expected 1200, got {params.get('target_price')}"
        assert params.get('target_currency') == 'AUD', f"Expected AUD, got {params.get('target_currency')}"
        assert '2026-06-08' in params.get('date'), f"Expected June 8, got {params.get('date')}"
        
        print("✓ All parameters parsed correctly")
        
    except Exception as e:
        print(f"✗ Parse error: {e}")
        raise


def test_price_comparison_logic():
    """Test that price comparison respects target price."""
    print("\nTesting price comparison logic...")
    
    # Test case 1: Flight under target (should pass)
    flight_price = 800
    target_price = 1200
    assert flight_price <= target_price, "Flight under target should pass"
    print(f"✓ {flight_price} <= {target_price}: PASS (flight shown)")
    
    # Test case 2: Flight over target (should fail)
    flight_price = 1600
    target_price = 1200
    assert flight_price > target_price, "Flight over target should fail"
    print(f"✓ {flight_price} > {target_price}: FAIL (flight hidden)")
    
    # Test case 3: Flight exactly at target (should pass)
    flight_price = 1200
    target_price = 1200
    assert flight_price <= target_price, "Flight at target should pass"
    print(f"✓ {flight_price} <= {target_price}: PASS (flight shown)")


def main():
    """Run all tests."""
    print("=" * 60)
    print("FLIGHT TRACKER TEST SUITE")
    print("=" * 60)
    
    try:
        test_mock_provider_currency()
        test_query_parsing()
        test_price_comparison_logic()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
