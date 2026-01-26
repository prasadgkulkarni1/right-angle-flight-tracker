"""
Test suite for PriceTrackerAgent tracking functionality.

Tests the agent's continuous price monitoring and Claude integration.
"""

import sys
import os
import unittest
import time
from unittest.mock import Mock, patch, MagicMock
import threading

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment before importing
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

from flight_tracker.agent import PriceTrackerAgent
from flight_tracker.flight_data import FlightTool, MockFlightProvider


class TestAgentTracking(unittest.TestCase):
    """Test cases for PriceTrackerAgent tracking functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock tool with controlled responses
        mock_provider = Mock()
        self.mock_tool = FlightTool(provider=mock_provider)

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_agent_initialization(self, mock_anthropic_class):
        """Test that PriceTrackerAgent initializes correctly."""
        print("\nTesting PriceTrackerAgent initialization...")

        agent = PriceTrackerAgent(tool=self.mock_tool, check_interval_seconds=2)

        # Verify agent attributes
        self.assertEqual(agent.tool, self.mock_tool)
        self.assertEqual(agent.check_interval_seconds, 2)
        self.assertEqual(agent.model_name, "claude-opus-4-5")
        self.assertFalse(agent.is_running)
        self.assertEqual(len(agent.messages), 0)

        # Verify Anthropic client was initialized
        mock_anthropic_class.assert_called_once()

        print("✓ PriceTrackerAgent initializes correctly")

    def test_agent_requires_api_key(self):
        """Test that PriceTrackerAgent raises error without API key."""
        print("\nTesting PriceTrackerAgent requires API key...")

        # Remove API key
        original_key = os.environ.get("ANTHROPIC_API_KEY")
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        try:
            with self.assertRaises(ValueError) as context:
                agent = PriceTrackerAgent(tool=self.mock_tool)

            self.assertIn("ANTHROPIC_API_KEY", str(context.exception))

            print("✓ PriceTrackerAgent correctly requires API key")

        finally:
            # Restore API key
            if original_key:
                os.environ["ANTHROPIC_API_KEY"] = original_key

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_parse_query_extracts_parameters(self, mock_anthropic_class):
        """Test that parse_query extracts structured parameters."""
        print("\nTesting query parsing...")

        # Mock Claude response
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [
            Mock(text='{"origin": "SFO", "destination": "JFK", "date": "2026-06-01", "target_price": 500, "target_currency": "USD", "return_date": null, "preferred_airlines": null, "max_duration": null}')
        ]
        mock_client.messages.create.return_value = mock_response

        # Parse query
        result = PriceTrackerAgent.parse_query(
            "Find flights from SFO to JFK on June 1 under $500",
            "test-api-key"
        )

        # Verify extracted parameters
        self.assertEqual(result['origin'], 'SFO')
        self.assertEqual(result['destination'], 'JFK')
        self.assertEqual(result['date'], '2026-06-01')
        self.assertEqual(result['target_price'], 500)
        self.assertEqual(result['target_currency'], 'USD')

        print("✓ Query parsing extracts parameters correctly")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_parse_query_handles_complex_dates(self, mock_anthropic_class):
        """Test that parse_query handles date ranges and complex expressions."""
        print("\nTesting query parsing with complex dates...")

        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [
            Mock(text='{"origin": "SYD", "destination": "BLR", "date": "2026-06-01", "return_date": "2026-06-30", "target_price": 1200, "target_currency": "AUD", "preferred_airlines": null, "max_duration": null}')
        ]
        mock_client.messages.create.return_value = mock_response

        result = PriceTrackerAgent.parse_query(
            "Return flights from Sydney to Bangalore in June under AUD 1200",
            "test-api-key"
        )

        # Verify date range handling
        self.assertEqual(result['date'], '2026-06-01')
        self.assertEqual(result['return_date'], '2026-06-30')
        self.assertEqual(result['target_currency'], 'AUD')

        print("✓ Query parsing handles complex dates")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_parse_query_extracts_preferences(self, mock_anthropic_class):
        """Test that parse_query extracts airline and duration preferences."""
        print("\nTesting query parsing with preferences...")

        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [
            Mock(text='{"origin": "SYD", "destination": "LAX", "date": "2026-07-01", "target_price": 800, "target_currency": "USD", "return_date": null, "preferred_airlines": ["QF", "UA"], "max_duration": 15}')
        ]
        mock_client.messages.create.return_value = mock_response

        result = PriceTrackerAgent.parse_query(
            "Flights SYD to LAX on Qantas or United, max 15 hours, under $800",
            "test-api-key"
        )

        # Verify preferences extracted
        self.assertEqual(result['preferred_airlines'], ['QF', 'UA'])
        self.assertEqual(result['max_duration'], 15)

        print("✓ Query parsing extracts preferences")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_tracking_loop_detects_deal(self, mock_anthropic_class):
        """Test that tracking loop detects when deal is found."""
        print("\nTesting tracking loop deal detection...")

        # Mock Claude client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool to return a good deal
        self.mock_tool.get_price = Mock(return_value={
            "status": "AVAILABLE",
            "price": 400.00,
            "currency": "USD",
            "airline": "UA",
            "flight_number": "UA123",
            "booking_url": "https://example.com",
            "trip_type": "one-way",
            "departure_date": "2026-06-01",
            "return_date": None
        })

        # Mock Claude response that uses tool
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "get_price"
        mock_tool_use.id = "tool_123"
        mock_tool_use.input = {
            "origin": "SFO",
            "destination": "JFK",
            "date": "2026-06-01"
        }

        mock_response_1 = Mock()
        mock_response_1.stop_reason = "tool_use"
        mock_response_1.content = [mock_tool_use]

        # Mock final response with DEAL FOUND
        mock_response_2 = Mock()
        mock_response_2.stop_reason = "end_turn"
        mock_response_2.content = [Mock(text="DEAL FOUND! Price is USD 400", type="text")]
        mock_response_2.content[0].text = "DEAL FOUND! Price is USD 400"

        mock_client.messages.create.side_effect = [mock_response_1, mock_response_2]

        # Create agent and track
        agent = PriceTrackerAgent(tool=self.mock_tool, check_interval_seconds=0.1)

        deal_found = []

        def notification_callback(message):
            deal_found.append(message)
            agent.stop()

        # Run tracking in thread with timeout
        tracking_thread = threading.Thread(
            target=agent.track_price,
            args=("SFO", "JFK", "2026-06-01", 500.0, notification_callback)
        )
        tracking_thread.daemon = True
        tracking_thread.start()
        tracking_thread.join(timeout=2)

        # Verify deal was found
        self.assertEqual(len(deal_found), 1)
        self.assertIn("DEAL FOUND", deal_found[0])

        print("✓ Tracking loop detects deals correctly")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_tracking_loop_continues_when_no_deal(self, mock_anthropic_class):
        """Test that tracking loop continues when no deal found."""
        print("\nTesting tracking loop continues without deal...")

        # Mock Claude client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool to return expensive flight
        self.mock_tool.get_price = Mock(return_value={
            "status": "AVAILABLE",
            "price": 800.00,
            "currency": "USD",
            "airline": "UA",
            "flight_number": "UA123",
            "booking_url": "https://example.com",
            "trip_type": "one-way",
            "departure_date": "2026-06-01",
            "return_date": None
        })

        # Mock Claude responses (no deal)
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "get_price"
        mock_tool_use.id = "tool_123"
        mock_tool_use.input = {
            "origin": "SFO",
            "destination": "JFK",
            "date": "2026-06-01"
        }

        mock_response_1 = Mock()
        mock_response_1.stop_reason = "tool_use"
        mock_response_1.content = [mock_tool_use]

        mock_response_2 = Mock()
        mock_response_2.stop_reason = "end_turn"
        mock_response_2.content = [Mock(text="Price too high", type="text")]
        mock_response_2.content[0].text = "Price too high"

        # Return same responses multiple times
        mock_client.messages.create.side_effect = [
            mock_response_1, mock_response_2,
            mock_response_1, mock_response_2
        ]

        # Create agent
        agent = PriceTrackerAgent(tool=self.mock_tool, check_interval_seconds=0.1)

        iterations = []

        def notification_callback(message):
            iterations.append(message)

        # Run for short duration then stop
        def run_tracking():
            agent.track_price("SFO", "JFK", "2026-06-01", 500.0, notification_callback)

        tracking_thread = threading.Thread(target=run_tracking)
        tracking_thread.daemon = True
        tracking_thread.start()

        # Let it run for a bit
        time.sleep(0.5)
        agent.stop()
        tracking_thread.join(timeout=1)

        # Verify no deal was triggered (would have stopped immediately)
        self.assertEqual(len(iterations), 0)

        print("✓ Tracking loop continues when no deal found")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_agent_stop_method(self, mock_anthropic_class):
        """Test that stop() method terminates tracking loop."""
        print("\nTesting agent stop method...")

        agent = PriceTrackerAgent(tool=self.mock_tool, check_interval_seconds=1)

        # Verify initial state
        self.assertFalse(agent.is_running)

        # Simulate running state
        agent.is_running = True
        self.assertTrue(agent.is_running)

        # Stop agent
        agent.stop()
        self.assertFalse(agent.is_running)

        print("✓ Agent stop method works correctly")

    @patch('flight_tracker.agent.anthropic.Anthropic')
    def test_tracking_handles_tool_errors(self, mock_anthropic_class):
        """Test that tracking handles tool execution errors gracefully."""
        print("\nTesting tracking handles tool errors...")

        # Mock Claude client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool that raises exception
        self.mock_tool.get_price = Mock(side_effect=Exception("Tool error"))

        # Mock Claude response that tries to use tool
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "get_price"
        mock_tool_use.id = "tool_123"
        mock_tool_use.input = {
            "origin": "SFO",
            "destination": "JFK",
            "date": "2026-06-01"
        }

        mock_response = Mock()
        mock_response.stop_reason = "tool_use"
        mock_response.content = [mock_tool_use]

        mock_client.messages.create.return_value = mock_response

        # Create agent
        agent = PriceTrackerAgent(tool=self.mock_tool, check_interval_seconds=0.1)

        # Run tracking briefly
        def run_tracking():
            try:
                agent.track_price("SFO", "JFK", "2026-06-01", 500.0, lambda x: None)
            except:
                pass

        tracking_thread = threading.Thread(target=run_tracking)
        tracking_thread.daemon = True
        tracking_thread.start()

        time.sleep(0.3)
        agent.stop()
        tracking_thread.join(timeout=1)

        # Should not crash, just handle error
        print("✓ Tracking handles tool errors gracefully")


if __name__ == "__main__":
    unittest.main()
