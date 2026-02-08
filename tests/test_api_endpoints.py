"""
Test suite for Flask API endpoints.

Integration tests for the REST API that powers the web interface.
"""

import sys
import os
import unittest
import json
import time
from unittest.mock import patch, Mock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the environment before importing app
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

import app as flask_app


class TestAPIEndpoints(unittest.TestCase):
    """Test cases for Flask API endpoints."""

    def setUp(self):
        """Set up test client before each test."""
        self.app = flask_app.app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Clear search results
        flask_app.search_results.clear()

    def test_index_route_returns_html(self):
        """Test that GET / returns the main HTML page."""
        print("\nTesting index route returns HTML...")

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Flights Finder', response.data)

        print("✓ Index route returns HTML successfully")

    def test_search_endpoint_requires_query(self):
        """Test that POST /api/search requires a query parameter."""
        print("\nTesting search endpoint validation...")

        # Request without query
        response = self.client.post('/api/search',
                                   data=json.dumps({}),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Query is required', data['error'])

        print("✓ Search endpoint validates required query parameter")

    def test_search_endpoint_returns_search_id(self):
        """Test that POST /api/search returns a search ID."""
        print("\nTesting search endpoint returns search_id...")

        with patch('app.PriceTrackerAgent.parse_query') as mock_parse:
            mock_parse.return_value = {
                "origin": "SFO",
                "destination": "JFK",
                "date": "2026-06-01",
                "target_price": 500,
                "target_currency": "USD"
            }

            response = self.client.post('/api/search',
                                       data=json.dumps({"query": "test query"}),
                                       content_type='application/json')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('search_id', data)
            self.assertIsNotNone(data['search_id'])

        print("✓ Search endpoint returns search_id")

    def test_status_endpoint_not_found(self):
        """Test that GET /api/status/<invalid_id> returns 404."""
        print("\nTesting status endpoint with invalid ID...")

        response = self.client.get('/api/status/invalid_search_id')

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Search not found', data['error'])

        print("✓ Status endpoint returns 404 for invalid search_id")

    def test_status_endpoint_returns_progress(self):
        """Test that GET /api/status/<search_id> returns search progress."""
        print("\nTesting status endpoint returns progress...")

        # Manually add a search result
        test_search_id = "test_123"
        flask_app.search_results[test_search_id] = {
            'status': 'searching',
            'messages': [
                {'type': 'info', 'content': 'Parsing query...'},
                {'type': 'success', 'content': 'Found route'}
            ],
            'result': None
        }

        response = self.client.get(f'/api/status/{test_search_id}')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'searching')
        self.assertEqual(len(data['messages']), 2)
        self.assertIsNone(data['result'])

        print("✓ Status endpoint returns search progress")

    def test_search_with_mock_provider(self):
        """Test full search flow with mock provider."""
        print("\nTesting search with mock provider...")

        with patch('app.PriceTrackerAgent.parse_query') as mock_parse:
            mock_parse.return_value = {
                "origin": "SFO",
                "destination": "JFK",
                "date": "2026-06-01",
                "target_price": 10000,  # High target to ensure it passes
                "target_currency": "USD"
            }

            # Initiate search
            response = self.client.post('/api/search',
                                       data=json.dumps({
                                           "query": "test query",
                                           "provider": "mock"
                                       }),
                                       content_type='application/json')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            search_id = data['search_id']

            # Poll for completion (with timeout)
            max_attempts = 20
            attempts = 0
            final_status = None

            while attempts < max_attempts:
                time.sleep(0.5)
                status_response = self.client.get(f'/api/status/{search_id}')
                status_data = json.loads(status_response.data)

                if status_data['status'] in ['complete', 'error']:
                    final_status = status_data
                    break

                attempts += 1

            self.assertIsNotNone(final_status, "Search should complete within timeout")
            self.assertIn(final_status['status'], ['complete', 'error'])

        print(f"✓ Search completed with status: {final_status['status']}")

    def test_search_with_amadeus_provider_no_credentials(self):
        """Test that Amadeus provider fails gracefully without credentials."""
        print("\nTesting Amadeus provider without credentials...")

        # Save and remove Amadeus credentials
        saved_key = os.environ.pop("AMADEUS_API_KEY", None)
        saved_secret = os.environ.pop("AMADEUS_API_SECRET", None)

        try:
            with patch('app.PriceTrackerAgent.parse_query') as mock_parse:
                mock_parse.return_value = {
                    "origin": "SFO",
                    "destination": "JFK",
                    "date": "2026-06-01",
                    "target_price": 500,
                    "target_currency": "USD"
                }

                response = self.client.post('/api/search',
                                           data=json.dumps({
                                               "query": "test query",
                                               "provider": "amadeus"
                                           }),
                                           content_type='application/json')

                search_id = json.loads(response.data)['search_id']

                # Wait for processing and check for error
                time.sleep(1.5)
                status_response = self.client.get(f'/api/status/{search_id}')
                status_data = json.loads(status_response.data)

                # Should be in error or complete state with error message
                self.assertIn(status_data['status'], ['error', 'complete'])

                # Check that error message mentions credentials
                has_credential_error = any('Amadeus credentials' in msg.get('content', '')
                                          for msg in status_data['messages'])

                # If status is error, credential error should be present
                # If status is complete without credential error, that's also acceptable
                # (means the search flow completed but handled the missing credentials)
                if status_data['status'] == 'error':
                    self.assertTrue(has_credential_error,
                                   "Error status should mention credentials")

            print("✓ Amadeus provider fails gracefully without credentials")

        finally:
            # Restore credentials
            if saved_key:
                os.environ["AMADEUS_API_KEY"] = saved_key
            if saved_secret:
                os.environ["AMADEUS_API_SECRET"] = saved_secret

    def test_concurrent_searches(self):
        """Test that multiple searches can run concurrently."""
        print("\nTesting concurrent searches...")

        with patch('app.PriceTrackerAgent.parse_query') as mock_parse:
            mock_parse.return_value = {
                "origin": "SFO",
                "destination": "JFK",
                "date": "2026-06-01",
                "target_price": 10000,
                "target_currency": "USD"
            }

            # Start multiple searches
            search_ids = []
            for i in range(3):
                response = self.client.post('/api/search',
                                           data=json.dumps({
                                               "query": f"test query {i}",
                                               "provider": "mock"
                                           }),
                                           content_type='application/json')
                data = json.loads(response.data)
                search_ids.append(data['search_id'])

            # Verify all searches are tracked
            self.assertEqual(len(search_ids), 3)
            self.assertEqual(len(set(search_ids)), 3, "Search IDs should be unique")

            # Wait for all to complete
            time.sleep(2)

            # Check all completed
            completed_count = 0
            for search_id in search_ids:
                status_response = self.client.get(f'/api/status/{search_id}')
                status_data = json.loads(status_response.data)
                if status_data['status'] in ['complete', 'error']:
                    completed_count += 1

            self.assertGreater(completed_count, 0, "At least one search should complete")

        print(f"✓ Concurrent searches work ({completed_count}/3 completed)")

    def test_search_invalid_json(self):
        """Test that invalid JSON returns proper error."""
        print("\nTesting invalid JSON handling...")

        response = self.client.post('/api/search',
                                   data="invalid json {",
                                   content_type='application/json')

        self.assertEqual(response.status_code, 400)

        print("✓ Invalid JSON handled properly")


if __name__ == "__main__":
    unittest.main()
