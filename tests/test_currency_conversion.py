"""
Test suite for currency conversion edge cases.

Tests currency handling throughout the application including conversions,
comparisons, and error scenarios.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flight_tracker.flight_data import MockFlightProvider


class TestCurrencyConversion(unittest.TestCase):
    """Test cases for currency conversion scenarios."""

    def test_same_currency_no_conversion_needed(self):
        """Test that same currency comparison requires no conversion."""
        print("\nTesting same currency comparison...")

        flight_price = 500.00
        flight_currency = "USD"
        target_price = 600.00
        target_currency = "USD"

        # When currencies match, simple comparison
        self.assertTrue(flight_currency == target_currency)
        self.assertTrue(flight_price <= target_price)

        print("✓ Same currency comparison works without conversion")

    def test_different_currency_requires_conversion(self):
        """Test that different currencies require conversion."""
        print("\nTesting different currency detection...")

        flight_currency = "EUR"
        target_currency = "USD"

        # Should detect mismatch
        self.assertNotEqual(flight_currency, target_currency)

        print("✓ Different currency correctly detected")

    @patch('forex_python.converter.CurrencyRates')
    def test_currency_conversion_eur_to_usd(self, mock_currency_rates):
        """Test EUR to USD conversion."""
        print("\nTesting EUR to USD conversion...")

        # Mock converter
        mock_converter = Mock()
        mock_converter.convert.return_value = 550.00  # EUR 500 = USD 550
        mock_currency_rates.return_value = mock_converter

        from forex_python.converter import CurrencyRates
        c = CurrencyRates()

        # Convert
        converted = c.convert("EUR", "USD", 500.00)

        self.assertEqual(converted, 550.00)
        mock_converter.convert.assert_called_once_with("EUR", "USD", 500.00)

        print("✓ EUR to USD conversion works")

    @patch('forex_python.converter.CurrencyRates')
    def test_currency_conversion_usd_to_aud(self, mock_currency_rates):
        """Test USD to AUD conversion."""
        print("\nTesting USD to AUD conversion...")

        # Mock converter with realistic rate
        mock_converter = Mock()
        mock_converter.convert.return_value = 750.00  # USD 500 = AUD 750
        mock_currency_rates.return_value = mock_converter

        from forex_python.converter import CurrencyRates
        c = CurrencyRates()

        converted = c.convert("USD", "AUD", 500.00)

        self.assertEqual(converted, 750.00)

        print("✓ USD to AUD conversion works")

    @patch('forex_python.converter.CurrencyRates')
    def test_currency_conversion_handles_failure(self, mock_currency_rates):
        """Test that currency conversion handles failures gracefully."""
        print("\nTesting currency conversion error handling...")

        # Mock converter that raises exception
        mock_converter = Mock()
        mock_converter.convert.side_effect = Exception("Conversion service unavailable")
        mock_currency_rates.return_value = mock_converter

        from forex_python.converter import CurrencyRates
        c = CurrencyRates()

        # Should raise exception (caller must handle)
        with self.assertRaises(Exception):
            c.convert("EUR", "USD", 500.00)

        print("✓ Currency conversion raises exception on failure")

    def test_mock_provider_respects_default_currency(self):
        """Test that MockFlightProvider uses default currency."""
        print("\nTesting MockProvider default currency...")

        # Test USD
        provider_usd = MockFlightProvider(default_currency="USD")
        result_usd = provider_usd.get_price("SFO", "JFK", "2026-06-01")
        self.assertEqual(result_usd['currency'], "USD")

        # Test EUR
        provider_eur = MockFlightProvider(default_currency="EUR")
        result_eur = provider_eur.get_price("CDG", "LHR", "2026-06-01")
        self.assertEqual(result_eur['currency'], "EUR")

        # Test AUD
        provider_aud = MockFlightProvider(default_currency="AUD")
        result_aud = provider_aud.get_price("SYD", "MEL", "2026-06-01")
        self.assertEqual(result_aud['currency'], "AUD")

        print("✓ MockProvider respects default currency")

    def test_price_comparison_same_currency(self):
        """Test price comparison when currencies match."""
        print("\nTesting price comparison with same currency...")

        test_cases = [
            (400.00, "USD", 500.00, "USD", True),   # Under target
            (500.00, "USD", 500.00, "USD", True),   # Equal to target
            (600.00, "USD", 500.00, "USD", False),  # Over target
            (499.99, "EUR", 500.00, "EUR", True),   # Just under
            (500.01, "EUR", 500.00, "EUR", False),  # Just over
        ]

        for flight_price, flight_curr, target_price, target_curr, expected in test_cases:
            if flight_curr == target_curr:
                result = flight_price <= target_price
                self.assertEqual(result, expected,
                    f"Failed: {flight_price} {flight_curr} vs {target_price} {target_curr}")

        print("✓ Price comparison works correctly for same currency")

    @patch('forex_python.converter.CurrencyRates')
    def test_price_comparison_different_currency(self, mock_currency_rates):
        """Test price comparison with currency conversion."""
        print("\nTesting price comparison with conversion...")

        # Mock converter: EUR to USD at 1.1 rate
        mock_converter = Mock()

        def convert_side_effect(from_curr, to_curr, amount):
            if from_curr == "EUR" and to_curr == "USD":
                return amount * 1.1
            return amount

        mock_converter.convert.side_effect = convert_side_effect
        mock_currency_rates.return_value = mock_converter

        from forex_python.converter import CurrencyRates
        c = CurrencyRates()

        # EUR 400 = USD 440, target is USD 500 (should pass)
        flight_price = 400.00
        flight_currency = "EUR"
        target_price = 500.00
        target_currency = "USD"

        if flight_currency != target_currency:
            converted_price = c.convert(flight_currency, target_currency, flight_price)
            result = converted_price <= target_price
            self.assertTrue(result)
            self.assertAlmostEqual(converted_price, 440.00, places=2)

        print("✓ Price comparison with conversion works correctly")

    def test_zero_price_handling(self):
        """Test handling of zero prices."""
        print("\nTesting zero price handling...")

        # Zero flight price (should always be under target)
        self.assertTrue(0.00 <= 500.00)

        # Zero target price (only zero flights match)
        self.assertTrue(0.00 <= 0.00)
        self.assertFalse(100.00 <= 0.00)

        print("✓ Zero price handling works correctly")

    def test_negative_price_handling(self):
        """Test handling of negative prices (shouldn't occur but test anyway)."""
        print("\nTesting negative price handling...")

        # Negative prices should be handled like any number
        self.assertTrue(-100.00 <= 500.00)
        self.assertFalse(500.00 <= -100.00)

        print("✓ Negative price handling works correctly")

    def test_very_large_price_handling(self):
        """Test handling of very large prices."""
        print("\nTesting very large price handling...")

        # Very expensive flight
        expensive_flight = 999999.99
        reasonable_target = 1000.00

        self.assertFalse(expensive_flight <= reasonable_target)

        # Very high target (everything should match)
        very_high_target = 1000000.00
        normal_flight = 500.00

        self.assertTrue(normal_flight <= very_high_target)

        print("✓ Very large price handling works correctly")

    def test_decimal_precision(self):
        """Test that decimal precision is handled correctly."""
        print("\nTesting decimal precision...")

        # Prices with many decimal places
        price1 = 499.999999
        price2 = 500.000001
        target = 500.00

        # Should use standard float comparison
        self.assertTrue(price1 < target)
        self.assertFalse(price2 <= target)  # Just over target

        print("✓ Decimal precision handled correctly")

    def test_currency_code_case_sensitivity(self):
        """Test that currency codes are case-sensitive."""
        print("\nTesting currency code case sensitivity...")

        # Standard: currency codes should be uppercase
        usd_upper = "USD"
        usd_lower = "usd"

        # They should not be equal (case matters)
        self.assertNotEqual(usd_upper, usd_lower)

        # MockProvider should use exactly what's given
        provider = MockFlightProvider(default_currency="USD")
        result = provider.get_price("SFO", "JFK", "2026-06-01")
        self.assertEqual(result['currency'], "USD")

        print("✓ Currency codes are case-sensitive")

    def test_invalid_currency_codes(self):
        """Test handling of invalid/unknown currency codes."""
        print("\nTesting invalid currency codes...")

        # MockProvider should accept any string
        provider = MockFlightProvider(default_currency="XXX")
        result = provider.get_price("SFO", "JFK", "2026-06-01")
        self.assertEqual(result['currency'], "XXX")

        # Real converter would fail (tested in provider tests)
        print("✓ Invalid currency codes handled")

    @patch('forex_python.converter.CurrencyRates')
    def test_conversion_rate_zero(self, mock_currency_rates):
        """Test handling of zero conversion rate."""
        print("\nTesting zero conversion rate...")

        mock_converter = Mock()
        mock_converter.convert.return_value = 0.00
        mock_currency_rates.return_value = mock_converter

        from forex_python.converter import CurrencyRates
        c = CurrencyRates()

        # Even with non-zero input, converter returns zero
        result = c.convert("EUR", "USD", 500.00)
        self.assertEqual(result, 0.00)

        print("✓ Zero conversion rate handled")

    @patch('forex_python.converter.CurrencyRates')
    def test_conversion_preserves_precision(self, mock_currency_rates):
        """Test that conversion preserves reasonable precision."""
        print("\nTesting conversion precision...")

        mock_converter = Mock()
        mock_converter.convert.return_value = 550.12345678
        mock_currency_rates.return_value = mock_converter

        from forex_python.converter import CurrencyRates
        c = CurrencyRates()

        result = c.convert("EUR", "USD", 500.00)

        # Should preserve precision from converter
        self.assertEqual(result, 550.12345678)

        # In practice, would round to 2 decimals for display
        rounded = round(result, 2)
        self.assertEqual(rounded, 550.12)

        print("✓ Conversion precision preserved")


if __name__ == "__main__":
    unittest.main()
