"""
Test suite for AmadeusFlightProvider.

Integration tests for Amadeus API provider with mocking for API calls.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flight_tracker.flight_data import AmadeusFlightProvider


class TestAmadeusProvider(unittest.TestCase):
    """Test cases for AmadeusFlightProvider."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_api_key = "test_key"
        self.test_api_secret = "test_secret"

    @patch('amadeus.Client')
    def test_amadeus_provider_initialization(self, mock_client_class):
        """Test that AmadeusProvider initializes Amadeus client correctly."""
        print("\nTesting AmadeusProvider initialization...")

        provider = AmadeusFlightProvider(
            api_key=self.test_api_key,
            api_secret=self.test_api_secret,
            target_currency="USD"
        )

        # Verify Client was instantiated with correct credentials
        mock_client_class.assert_called_once_with(
            client_id=self.test_api_key,
            client_secret=self.test_api_secret
        )

        # Verify target currency is stored
        self.assertEqual(provider.target_currency, "USD")

        print("✓ AmadeusProvider initializes correctly")

    @patch('amadeus.Client')
    def test_amadeus_one_way_search(self, mock_client_class):
        """Test one-way flight search through Amadeus API."""
        print("\nTesting Amadeus one-way flight search...")

        # Create mock Amadeus client and response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.data = [
            {
                'price': {'total': '250.50', 'currency': 'USD'},
                'itineraries': [{
                    'segments': [{
                        'carrierCode': 'UA',
                        'number': '123',
                        'departure': {},
                        'arrival': {}
                    }]
                }]
            }
        ]

        mock_client.shopping.flight_offers_search.get.return_value = mock_response

        # Create provider and search
        provider = AmadeusFlightProvider(
            api_key=self.test_api_key,
            api_secret=self.test_api_secret
        )

        result = provider.get_price("SFO", "JFK", "2026-06-01")

        # Verify API was called with correct parameters
        mock_client.shopping.flight_offers_search.get.assert_called_once_with(
            originLocationCode="SFO",
            destinationLocationCode="JFK",
            departureDate="2026-06-01",
            adults=1
        )

        # Verify result structure
        self.assertIsNotNone(result)
        self.assertEqual(result['price'], 250.50)
        self.assertEqual(result['currency'], 'USD')
        self.assertEqual(result['airline'], 'UA')
        self.assertEqual(result['flight_number'], 'UA123')
        self.assertEqual(result['trip_type'], 'one-way')
        self.assertEqual(result['departure_date'], '2026-06-01')
        self.assertIsNone(result['return_date'])

        print("✓ Amadeus one-way search works correctly")

    @patch('amadeus.Client')
    def test_amadeus_round_trip_search(self, mock_client_class):
        """Test round-trip flight search through Amadeus API."""
        print("\nTesting Amadeus round-trip flight search...")

        # Create mock client and response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.data = [
            {
                'price': {'total': '500.00', 'currency': 'EUR'},
                'itineraries': [{
                    'segments': [{
                        'carrierCode': 'BA',
                        'number': '456',
                        'departure': {},
                        'arrival': {}
                    }]
                }]
            }
        ]

        mock_client.shopping.flight_offers_search.get.return_value = mock_response

        # Create provider and search with return date
        provider = AmadeusFlightProvider(
            api_key=self.test_api_key,
            api_secret=self.test_api_secret
        )

        result = provider.get_price("LHR", "JFK", "2026-07-01", "2026-07-15")

        # Verify API was called with return date
        call_args = mock_client.shopping.flight_offers_search.get.call_args
        self.assertEqual(call_args.kwargs['returnDate'], '2026-07-15')

        # Verify result has return date
        self.assertEqual(result['trip_type'], 'round-trip')
        self.assertEqual(result['return_date'], '2026-07-15')

        print("✓ Amadeus round-trip search works correctly")

    @patch('forex_python.converter.CurrencyRates')
    @patch('amadeus.Client')
    def test_amadeus_currency_conversion(self, mock_client_class, mock_currency_rates):
        """Test that AmadeusProvider converts currency when target is different."""
        print("\nTesting Amadeus currency conversion...")

        # Mock Amadeus client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.data = [
            {
                'price': {'total': '500.00', 'currency': 'EUR'},
                'itineraries': [{
                    'segments': [{
                        'carrierCode': 'LH',
                        'number': '789',
                        'departure': {},
                        'arrival': {}
                    }]
                }]
            }
        ]

        mock_client.shopping.flight_offers_search.get.return_value = mock_response

        # Mock currency converter
        mock_converter = Mock()
        mock_converter.convert.return_value = 750.00  # EUR 500 = AUD 750
        mock_currency_rates.return_value = mock_converter

        # Create provider with target currency
        provider = AmadeusFlightProvider(
            api_key=self.test_api_key,
            api_secret=self.test_api_secret,
            target_currency="AUD"
        )

        result = provider.get_price("FRA", "SYD", "2026-08-01")

        # Verify currency was converted
        self.assertEqual(result['price'], 750.00)
        self.assertEqual(result['currency'], 'AUD')
        self.assertEqual(result['original_price'], 500.00)
        self.assertEqual(result['original_currency'], 'EUR')

        # Verify converter was called correctly
        mock_converter.convert.assert_called_once_with('EUR', 'AUD', 500.00)

        print("✓ Amadeus currency conversion works correctly")

    @patch('amadeus.Client')
    def test_amadeus_no_currency_conversion_when_same(self, mock_client_class):
        """Test that no conversion happens when currencies match."""
        print("\nTesting Amadeus skips conversion when currencies match...")

        # Mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.data = [
            {
                'price': {'total': '300.00', 'currency': 'USD'},
                'itineraries': [{
                    'segments': [{
                        'carrierCode': 'AA',
                        'number': '111',
                        'departure': {},
                        'arrival': {}
                    }]
                }]
            }
        ]

        mock_client.shopping.flight_offers_search.get.return_value = mock_response

        # Create provider with same target currency
        provider = AmadeusFlightProvider(
            api_key=self.test_api_key,
            api_secret=self.test_api_secret,
            target_currency="USD"
        )

        result = provider.get_price("LAX", "SFO", "2026-05-01")

        # Verify no conversion happened
        self.assertEqual(result['price'], 300.00)
        self.assertEqual(result['currency'], 'USD')
        self.assertNotIn('original_price', result)
        self.assertNotIn('original_currency', result)

        print("✓ Amadeus correctly skips conversion when currencies match")

    @patch('amadeus.Client')
    def test_amadeus_finds_cheapest_flight(self, mock_client_class):
        """Test that AmadeusProvider selects the cheapest flight."""
        print("\nTesting Amadeus selects cheapest flight...")

        # Mock client with multiple offers
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.data = [
            {
                'price': {'total': '400.00', 'currency': 'USD'},
                'itineraries': [{
                    'segments': [{
                        'carrierCode': 'DL',
                        'number': '222',
                        'departure': {},
                        'arrival': {}
                    }]
                }]
            },
            {
                'price': {'total': '250.00', 'currency': 'USD'},  # Cheapest
                'itineraries': [{
                    'segments': [{
                        'carrierCode': 'UA',
                        'number': '333',
                        'departure': {},
                        'arrival': {}
                    }]
                }]
            },
            {
                'price': {'total': '350.00', 'currency': 'USD'},
                'itineraries': [{
                    'segments': [{
                        'carrierCode': 'AA',
                        'number': '444',
                        'departure': {},
                        'arrival': {}
                    }]
                }]
            }
        ]

        mock_client.shopping.flight_offers_search.get.return_value = mock_response

        # Create provider and search
        provider = AmadeusFlightProvider(
            api_key=self.test_api_key,
            api_secret=self.test_api_secret
        )

        result = provider.get_price("ORD", "LAX", "2026-09-01")

        # Verify cheapest flight was selected
        self.assertEqual(result['price'], 250.00)
        self.assertEqual(result['flight_number'], 'UA333')

        print("✓ Amadeus correctly selects cheapest flight")

    @patch('amadeus.Client')
    def test_amadeus_handles_no_results(self, mock_client_class):
        """Test that AmadeusProvider handles empty results gracefully."""
        print("\nTesting Amadeus handles no results...")

        # Mock client with empty results
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.data = []  # No flights found

        mock_client.shopping.flight_offers_search.get.return_value = mock_response

        # Create provider and search
        provider = AmadeusFlightProvider(
            api_key=self.test_api_key,
            api_secret=self.test_api_secret
        )

        result = provider.get_price("ABC", "XYZ", "2026-12-31")

        # Should return None
        self.assertIsNone(result)

        print("✓ Amadeus handles no results gracefully")

    @patch('amadeus.Client')
    def test_amadeus_handles_api_error(self, mock_client_class):
        """Test that AmadeusProvider handles API errors gracefully."""
        print("\nTesting Amadeus handles API errors...")

        # Mock client that raises exception
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.shopping.flight_offers_search.get.side_effect = Exception("API Error")

        # Create provider and search
        provider = AmadeusFlightProvider(
            api_key=self.test_api_key,
            api_secret=self.test_api_secret
        )

        result = provider.get_price("SFO", "JFK", "2026-06-01")

        # Should return None, not raise exception
        self.assertIsNone(result)

        print("✓ Amadeus handles API errors gracefully")

    @patch('forex_python.converter.CurrencyRates')
    @patch('amadeus.Client')
    def test_amadeus_handles_currency_conversion_error(self, mock_client_class, mock_currency_rates):
        """Test that AmadeusProvider falls back to original currency on conversion error."""
        print("\nTesting Amadeus handles currency conversion errors...")

        # Mock Amadeus client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.data = [
            {
                'price': {'total': '500.00', 'currency': 'EUR'},
                'itineraries': [{
                    'segments': [{
                        'carrierCode': 'AF',
                        'number': '999',
                        'departure': {},
                        'arrival': {}
                    }]
                }]
            }
        ]

        mock_client.shopping.flight_offers_search.get.return_value = mock_response

        # Mock currency converter that raises exception
        mock_converter = Mock()
        mock_converter.convert.side_effect = Exception("Conversion failed")
        mock_currency_rates.return_value = mock_converter

        # Create provider with different target currency
        provider = AmadeusFlightProvider(
            api_key=self.test_api_key,
            api_secret=self.test_api_secret,
            target_currency="AUD"
        )

        result = provider.get_price("CDG", "SYD", "2026-10-01")

        # Should fall back to original currency
        self.assertEqual(result['price'], 500.00)
        self.assertEqual(result['currency'], 'EUR')
        self.assertNotIn('original_price', result)

        print("✓ Amadeus falls back to original currency on conversion error")


if __name__ == "__main__":
    unittest.main()
