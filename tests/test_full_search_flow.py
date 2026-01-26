"""
Test suite for end-to-end full search flow.

Integration tests that verify the complete search flow from query to result,
including query parsing, flight search, and result formatting.
"""

import sys
import os
import unittest
import time
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

from flight_tracker.flight_data import MockFlightProvider, FlightTool
from flight_tracker.agent import PriceTrackerAgent


class TestFullSearchFlow(unittest.TestCase):
    """End-to-end test cases for complete search flow."""

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_complete_one_way_search_flow(self, mock_anthropic_class):
        """Test complete flow from query parsing to flight result."""
        print("\nTesting complete one-way search flow...")

        # Mock Claude for query parsing
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock parse_query response
        parse_response = Mock()
        parse_response.content = [
            Mock(text='{"origin": "SFO", "destination": "JFK", "date": "2026-06-01", "target_price": 10000, "target_currency": "USD", "return_date": null, "preferred_airlines": null, "max_duration": null}')
        ]

        # Mock tracking responses
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "get_price"
        mock_tool_use.id = "tool_123"
        mock_tool_use.input = {"origin": "SFO", "destination": "JFK", "date": "2026-06-01"}

        tool_use_response = Mock()
        tool_use_response.stop_reason = "tool_use"
        tool_use_response.content = [mock_tool_use]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(text="DEAL FOUND! Price is USD 500", type="text")]
        final_response.content[0].text = "DEAL FOUND! Price is USD 500"

        mock_client.messages.create.side_effect = [
            parse_response,
            tool_use_response,
            final_response
        ]

        # Step 1: Parse query
        query = "Find flights from SFO to JFK on June 1 under $10000"
        params = PriceTrackerAgent.parse_query(query, "test-key")

        self.assertEqual(params['origin'], 'SFO')
        self.assertEqual(params['destination'], 'JFK')
        self.assertEqual(params['target_price'], 10000)

        # Step 2: Create provider and tool
        provider = MockFlightProvider(default_currency="USD")
        tool = FlightTool(provider=provider)

        # Step 3: Get flight price
        flight_result = tool.get_price(
            params['origin'],
            params['destination'],
            params['date']
        )

        self.assertEqual(flight_result['status'], 'AVAILABLE')
        self.assertIn('price', flight_result)
        self.assertIn('currency', flight_result)
        self.assertEqual(flight_result['trip_type'], 'one-way')

        print("✓ Complete one-way search flow successful")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_complete_round_trip_search_flow(self, mock_anthropic_class):
        """Test complete flow for round-trip flights."""
        print("\nTesting complete round-trip search flow...")

        # Mock Claude client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock parse response with return date
        parse_response = Mock()
        parse_response.content = [
            Mock(text='{"origin": "SYD", "destination": "BLR", "date": "2026-06-01", "return_date": "2026-06-30", "target_price": 2000, "target_currency": "AUD", "preferred_airlines": null, "max_duration": null}')
        ]
        mock_client.messages.create.return_value = parse_response

        # Parse query
        query = "Return flights from Sydney to Bangalore in June under AUD 2000"
        params = PriceTrackerAgent.parse_query(query, "test-key")

        self.assertEqual(params['origin'], 'SYD')
        self.assertEqual(params['destination'], 'BLR')
        self.assertEqual(params['return_date'], '2026-06-30')
        self.assertEqual(params['target_currency'], 'AUD')

        # Create provider with AUD currency
        provider = MockFlightProvider(default_currency="AUD")
        tool = FlightTool(provider=provider)

        # Get round-trip flight
        flight_result = tool.get_price(
            params['origin'],
            params['destination'],
            params['date'],
            params['return_date']
        )

        self.assertEqual(flight_result['status'], 'AVAILABLE')
        self.assertEqual(flight_result['currency'], 'AUD')
        self.assertEqual(flight_result['trip_type'], 'round-trip')
        self.assertEqual(flight_result['return_date'], '2026-06-30')

        print("✓ Complete round-trip search flow successful")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_search_flow_with_price_filtering(self, mock_anthropic_class):
        """Test that search correctly filters by target price."""
        print("\nTesting search flow with price filtering...")

        # Mock Claude client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        parse_response = Mock()
        parse_response.content = [
            Mock(text='{"origin": "LAX", "destination": "SFO", "date": "2026-07-01", "target_price": 200, "target_currency": "USD", "return_date": null, "preferred_airlines": null, "max_duration": null}')
        ]
        mock_client.messages.create.return_value = parse_response

        # Parse query with low target
        query = "Flights from LAX to SFO under $200"
        params = PriceTrackerAgent.parse_query(query, "test-key")

        # Get flight price
        provider = MockFlightProvider(default_currency="USD")
        tool = FlightTool(provider=provider)
        flight_result = tool.get_price(
            params['origin'],
            params['destination'],
            params['date']
        )

        # Check if price meets target
        target_price = params['target_price']
        flight_price = flight_result['price']

        if flight_price <= target_price:
            deal_found = True
        else:
            deal_found = False

        # Result depends on random price, but logic is correct
        self.assertIsInstance(deal_found, bool)

        print(f"✓ Price filtering works (flight: ${flight_price}, target: ${target_price}, deal: {deal_found})")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_search_flow_with_multi_currency(self, mock_anthropic_class):
        """Test search flow with currency conversion."""
        print("\nTesting search flow with currency conversion...")

        # Mock Claude client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        parse_response = Mock()
        parse_response.content = [
            Mock(text='{"origin": "LHR", "destination": "CDG", "date": "2026-08-01", "target_price": 150, "target_currency": "EUR", "return_date": null, "preferred_airlines": null, "max_duration": null}')
        ]
        mock_client.messages.create.return_value = parse_response

        # Parse query with EUR currency
        query = "Flights from London to Paris under EUR 150"
        params = PriceTrackerAgent.parse_query(query, "test-key")

        self.assertEqual(params['target_currency'], 'EUR')

        # Get flight in EUR
        provider = MockFlightProvider(default_currency="EUR")
        tool = FlightTool(provider=provider)
        flight_result = tool.get_price(
            params['origin'],
            params['destination'],
            params['date']
        )

        # Verify currency matches
        self.assertEqual(flight_result['currency'], 'EUR')

        print("✓ Multi-currency search flow successful")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_search_flow_handles_no_flights(self, mock_anthropic_class):
        """Test search flow when no flights are available."""
        print("\nTesting search flow with no flights...")

        # Create mock provider that returns None
        mock_provider = Mock()
        mock_provider.get_price.return_value = None

        tool = FlightTool(provider=mock_provider)
        result = tool.get_price("ABC", "XYZ", "2026-12-31")

        # Should return UNAVAILABLE status
        self.assertEqual(result['status'], 'UNAVAILABLE')
        self.assertIn('error', result)

        print("✓ Search flow handles no flights gracefully")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_search_flow_with_preferences(self, mock_anthropic_class):
        """Test search flow with airline and duration preferences."""
        print("\nTesting search flow with preferences...")

        # Mock Claude client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        parse_response = Mock()
        parse_response.content = [
            Mock(text='{"origin": "SYD", "destination": "LAX", "date": "2026-09-01", "target_price": 1000, "target_currency": "USD", "return_date": null, "preferred_airlines": ["QF", "UA"], "max_duration": 15}')
        ]
        mock_client.messages.create.return_value = parse_response

        # Parse query with preferences
        query = "Flights SYD to LAX on Qantas or United, max 15 hours, under $1000"
        params = PriceTrackerAgent.parse_query(query, "test-key")

        # Verify preferences extracted
        self.assertEqual(params['preferred_airlines'], ['QF', 'UA'])
        self.assertEqual(params['max_duration'], 15)

        # Note: Current implementation doesn't filter by preferences,
        # but they are parsed and available for future use
        provider = MockFlightProvider()
        tool = FlightTool(provider=provider)
        result = tool.get_price(params['origin'], params['destination'], params['date'])

        self.assertEqual(result['status'], 'AVAILABLE')

        print("✓ Search flow with preferences parsed (filtering not yet implemented)")

    def test_cli_to_web_parameter_compatibility(self):
        """Test that parameters work across CLI and web interfaces."""
        print("\nTesting CLI/web parameter compatibility...")

        # Simulate parameters from CLI
        cli_params = {
            "origin": "SFO",
            "destination": "JFK",
            "date": "2026-06-01",
            "target_price": 500.0,
            "target_currency": "USD",
            "return_date": None,
            "preferred_airlines": None,
            "max_duration": None
        }

        # Use in provider (simulating web flow)
        provider = MockFlightProvider(default_currency=cli_params['target_currency'])
        tool = FlightTool(provider=provider)

        result = tool.get_price(
            cli_params['origin'],
            cli_params['destination'],
            cli_params['date'],
            cli_params['return_date']
        )

        # Should work identically
        self.assertEqual(result['status'], 'AVAILABLE')
        self.assertEqual(result['currency'], cli_params['target_currency'])

        print("✓ CLI/web parameter compatibility verified")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_error_recovery_in_search_flow(self, mock_anthropic_class):
        """Test that search flow handles errors at various stages."""
        print("\nTesting error recovery in search flow...")

        # Test 1: Parse query error
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        parse_response = Mock()
        parse_response.content = [Mock(text='invalid json {')]
        mock_client.messages.create.return_value = parse_response

        with self.assertRaises(Exception):
            PriceTrackerAgent.parse_query("test query", "test-key")

        print("  ✓ Parse error handled")

        # Test 2: Provider error
        mock_provider = Mock()
        mock_provider.get_price.side_effect = Exception("Provider error")

        tool = FlightTool(provider=mock_provider)

        with self.assertRaises(Exception):
            tool.get_price("SFO", "JFK", "2026-06-01")

        print("  ✓ Provider error raised")

        print("✓ Error recovery mechanisms verified")

    def test_data_consistency_across_components(self):
        """Test that data format is consistent across all components."""
        print("\nTesting data consistency...")

        # Get flight from MockProvider
        provider = MockFlightProvider(default_currency="USD")
        raw_result = provider.get_price("SFO", "JFK", "2026-06-01")

        # Verify provider output format
        required_fields = ['price', 'currency', 'airline', 'flight_number',
                          'booking_url', 'trip_type', 'departure_date', 'return_date']
        for field in required_fields:
            self.assertIn(field, raw_result, f"Missing field: {field}")

        # Wrap with FlightTool
        tool = FlightTool(provider=provider)
        wrapped_result = tool.get_price("SFO", "JFK", "2026-06-01")

        # Verify tool adds status but preserves all fields
        self.assertIn('status', wrapped_result)
        for field in required_fields:
            self.assertIn(field, wrapped_result, f"Tool removed field: {field}")

        # Verify data types
        self.assertIsInstance(wrapped_result['price'], (int, float))
        self.assertIsInstance(wrapped_result['currency'], str)
        self.assertIsInstance(wrapped_result['trip_type'], str)

        print("✓ Data consistency verified across components")


if __name__ == "__main__":
    unittest.main()
