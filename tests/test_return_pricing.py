"""
Test suite for return flight pricing logic.

This suite tests that return flights have appropriate pricing logic (e.g. usually higher than one-way).
"""

import sys
import os
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flight_tracker.flight_data import MockFlightProvider

class TestReturnPricing(unittest.TestCase):
    def test_mock_return_price_higher(self):
        """Test that mock provider returns higher price for round-trip than one-way."""
        print("\nTesting MockFlightProvider return pricing...")
        
        provider = MockFlightProvider()
        
        # Get one-way price
        # seed random for consistent one-way price generation if possible, 
        # but MockProvider generates random each call. 
        # We can simulate by checking if return price calculation logic exists in code.
        # Ideally, we'd check if the provider accounts for trip type.
        
        # Since MockProvider is random, we can't strictly assert one > other in a single run 
        # unless we control the randomness or if the logic explicitly doubles/adds to it.
        # Let's inspect the logic by reading the file first (which I did).
        # The current MockProvider implementation:
        # base_price = random.uniform(100, 1000)
        # return { "price": ... }
        # It DOES NOT use return_date to adjust price. This is the bug in Mock provider.
        
        # For this test to pass after fix, we expect the logic to depend on return_date.
        # We will mock random to return constant to verify the multiplier logic.
        
        import random
        # Fix random seed
        random.seed(42)
        price_one_way = provider.get_price("SYD", "BLR", "2026-06-01")['price']
        
        random.seed(42) # Reset seed to get same base price
        price_return = provider.get_price("SYD", "BLR", "2026-06-01", "2026-06-10")['price']
        
        print(f"One-way price (seeded): {price_one_way}")
        print(f"Return price (seeded): {price_return}")
        
        # This assertion will FAIL currently because they will be equal (MockProvider ignores return_date for price)
        self.assertNotEqual(price_one_way, price_return, "Return price should probably not be identical to one-way price for same base seed")
        self.assertGreater(price_return, price_one_way, "Return price should be higher than one-way")

if __name__ == "__main__":
    unittest.main()
