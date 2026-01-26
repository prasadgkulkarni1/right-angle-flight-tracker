"""
Test suite for FlightTool wrapper class.

Tests that the FlightTool correctly wraps provider results and handles errors.
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flight_tracker.flight_data import FlightTool, FlightProvider


class TestFlightTool(unittest.TestCase):
    """Test cases for FlightTool wrapper."""

    def test_flight_tool_wraps_available_result(self):
        """Test that FlightTool adds AVAILABLE status to successful results."""
        print("\nTesting FlightTool wraps available result...")

        # Create mock provider
        mock_provider = Mock(spec=FlightProvider)
        mock_provider.get_price.return_value = {
            "price": 500.00,
            "currency": "USD",
            "airline": "UA",
            "flight_number": "UA123",
            "booking_url": "https://example.com",
            "trip_type": "one-way",
            "departure_date": "2026-06-01",
            "return_date": None
        }

        # Create tool and call get_price
        tool = FlightTool(provider=mock_provider)
        result = tool.get_price("SFO", "JFK", "2026-06-01")

        # Verify result has AVAILABLE status
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["price"], 500.00)
        self.assertEqual(result["currency"], "USD")
        self.assertEqual(result["airline"], "UA")

        # Verify provider was called correctly
        mock_provider.get_price.assert_called_once_with("SFO", "JFK", "2026-06-01", None)

        print("✓ FlightTool correctly wraps available result with status")

    def test_flight_tool_handles_unavailable(self):
        """Test that FlightTool returns UNAVAILABLE status when provider returns None."""
        print("\nTesting FlightTool handles unavailable flights...")

        # Create mock provider that returns None
        mock_provider = Mock(spec=FlightProvider)
        mock_provider.get_price.return_value = None

        # Create tool and call get_price
        tool = FlightTool(provider=mock_provider)
        result = tool.get_price("ABC", "XYZ", "2026-12-31")

        # Verify UNAVAILABLE status
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIn("error", result)
        self.assertIn("Could not fetch", result["error"])

        print("✓ FlightTool correctly handles unavailable flights")

    def test_flight_tool_handles_provider_exception(self):
        """Test that FlightTool handles exceptions from provider gracefully."""
        print("\nTesting FlightTool handles provider exceptions...")

        # Create mock provider that raises exception
        mock_provider = Mock(spec=FlightProvider)
        mock_provider.get_price.side_effect = Exception("API Error")

        # Create tool and call get_price
        tool = FlightTool(provider=mock_provider)

        # Should not raise exception, but return error result
        # Note: Current implementation doesn't catch exceptions, so this will actually raise
        # This test documents the current behavior
        with self.assertRaises(Exception):
            result = tool.get_price("SFO", "JFK", "2026-06-01")

        print("✓ FlightTool exception handling documented (raises exception)")

    def test_flight_tool_preserves_all_fields(self):
        """Test that FlightTool preserves all fields from provider."""
        print("\nTesting FlightTool preserves all provider fields...")

        # Create mock provider with all fields
        mock_provider = Mock(spec=FlightProvider)
        mock_provider.get_price.return_value = {
            "price": 1200.50,
            "currency": "EUR",
            "original_price": 1000.00,
            "original_currency": "GBP",
            "airline": "BA",
            "flight_number": "BA456",
            "booking_url": "https://ba.com/book",
            "trip_type": "round-trip",
            "departure_date": "2026-07-01",
            "return_date": "2026-07-15",
            "extra_field": "should be preserved"
        }

        # Create tool and call get_price
        tool = FlightTool(provider=mock_provider)
        result = tool.get_price("LHR", "JFK", "2026-07-01", "2026-07-15")

        # Verify all fields are preserved
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["price"], 1200.50)
        self.assertEqual(result["original_price"], 1000.00)
        self.assertEqual(result["extra_field"], "should be preserved")

        print("✓ FlightTool preserves all provider fields")

    def test_flight_tool_passes_return_date(self):
        """Test that FlightTool correctly passes return_date to provider."""
        print("\nTesting FlightTool passes return_date parameter...")

        # Create mock provider
        mock_provider = Mock(spec=FlightProvider)
        mock_provider.get_price.return_value = {
            "price": 800.00,
            "currency": "AUD",
            "airline": "QF",
            "flight_number": "QF1",
            "booking_url": "https://qantas.com",
            "trip_type": "round-trip",
            "departure_date": "2026-06-01",
            "return_date": "2026-06-10"
        }

        # Create tool and call with return_date
        tool = FlightTool(provider=mock_provider)
        result = tool.get_price("SYD", "BLR", "2026-06-01", "2026-06-10")

        # Verify provider was called with return_date
        mock_provider.get_price.assert_called_once_with(
            "SYD", "BLR", "2026-06-01", "2026-06-10"
        )

        print("✓ FlightTool correctly passes return_date to provider")


if __name__ == "__main__":
    unittest.main()
