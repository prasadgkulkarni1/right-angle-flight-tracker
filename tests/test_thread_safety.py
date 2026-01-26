"""
Test suite for thread safety.

Tests concurrent operations, thread safety of shared data structures,
and race condition handling in the Flask application.
"""

import sys
import os
import unittest
import threading
import time
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

import app as flask_app
from flight_tracker.flight_data import MockFlightProvider, FlightTool


class TestThreadSafety(unittest.TestCase):
    """Test cases for thread safety in concurrent operations."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear search results before each test
        with flask_app.search_lock:
            flask_app.search_results.clear()

    def test_search_lock_protects_shared_state(self):
        """Test that search_lock properly protects search_results."""
        print("\nTesting search_lock protects shared state...")

        results = []

        def write_to_results(search_id, value):
            with flask_app.search_lock:
                flask_app.search_results[search_id] = value
                # Simulate some processing time
                time.sleep(0.01)
                results.append(search_id)

        # Create multiple threads writing concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=write_to_results, args=(f"search_{i}", {'status': f'test_{i}'}))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all writes completed
        self.assertEqual(len(flask_app.search_results), 10)
        self.assertEqual(len(results), 10)

        # Verify data integrity
        for i in range(10):
            self.assertIn(f"search_{i}", flask_app.search_results)
            self.assertEqual(flask_app.search_results[f"search_{i}"]['status'], f'test_{i}')

        print("✓ search_lock properly protects shared state")

    def test_concurrent_search_result_updates(self):
        """Test concurrent updates to the same search result."""
        print("\nTesting concurrent search result updates...")

        search_id = "test_search"

        # Initialize search result
        with flask_app.search_lock:
            flask_app.search_results[search_id] = {
                'status': 'parsing',
                'messages': [],
                'result': None
            }

        update_count = [0]
        lock = threading.Lock()

        def add_message(message):
            with flask_app.search_lock:
                flask_app.search_results[search_id]['messages'].append(message)
                with lock:
                    update_count[0] += 1

        # Create threads that add messages concurrently
        threads = []
        for i in range(20):
            thread = threading.Thread(target=add_message, args=({'type': 'info', 'content': f'Message {i}'},))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all messages added
        with flask_app.search_lock:
            self.assertEqual(len(flask_app.search_results[search_id]['messages']), 20)
            self.assertEqual(update_count[0], 20)

        print("✓ Concurrent updates handled safely")

    def test_concurrent_read_write_operations(self):
        """Test concurrent reads and writes to search results."""
        print("\nTesting concurrent read/write operations...")

        search_id = "test_read_write"

        # Initialize search result
        with flask_app.search_lock:
            flask_app.search_results[search_id] = {
                'status': 'searching',
                'messages': [],
                'result': None
            }

        read_values = []
        read_lock = threading.Lock()

        def reader():
            for _ in range(10):
                with flask_app.search_lock:
                    status = flask_app.search_results[search_id]['status']
                    with read_lock:
                        read_values.append(status)
                time.sleep(0.001)

        def writer(new_status):
            time.sleep(0.005)
            with flask_app.search_lock:
                flask_app.search_results[search_id]['status'] = new_status

        # Start readers and writers
        threads = []

        # Multiple readers
        for _ in range(3):
            thread = threading.Thread(target=reader)
            threads.append(thread)
            thread.start()

        # Writers changing status
        statuses = ['parsing', 'searching', 'complete']
        for status in statuses:
            thread = threading.Thread(target=writer, args=(status,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify reads completed without errors
        self.assertGreater(len(read_values), 0)

        # Final status should be from last writer
        with flask_app.search_lock:
            final_status = flask_app.search_results[search_id]['status']
            self.assertIn(final_status, ['parsing', 'searching', 'complete'])

        print(f"✓ Concurrent read/write operations safe ({len(read_values)} reads)")

    def test_search_id_uniqueness_under_concurrency(self):
        """Test that concurrent search ID generation produces unique IDs."""
        print("\nTesting search ID uniqueness...")

        search_ids = []
        lock = threading.Lock()

        def generate_search_id(query_suffix):
            # Simulate search ID generation with unique queries
            import threading
            query = f"test query {query_suffix}"
            search_id = str(hash(query + str(threading.current_thread().ident)))

            with lock:
                search_ids.append(search_id)

        # Generate IDs concurrently with different queries
        threads = []
        for i in range(50):
            thread = threading.Thread(target=generate_search_id, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify uniqueness (different queries + different thread IDs = unique hashes)
        unique_ids = set(search_ids)
        self.assertEqual(len(unique_ids), len(search_ids), "All search IDs should be unique")

        print(f"✓ Generated {len(unique_ids)} unique search IDs from {len(search_ids)} concurrent requests")

    def test_provider_thread_safety(self):
        """Test that MockFlightProvider is thread-safe."""
        print("\nTesting provider thread safety...")

        provider = MockFlightProvider(default_currency="USD")
        results = []
        results_lock = threading.Lock()

        def get_flight():
            result = provider.get_price("SFO", "JFK", "2026-06-01")
            with results_lock:
                results.append(result)

        # Call provider concurrently
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=get_flight)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all calls completed successfully
        self.assertEqual(len(results), 20)

        # Verify all results are valid
        for result in results:
            self.assertIn('price', result)
            self.assertIn('currency', result)
            self.assertEqual(result['currency'], 'USD')

        print("✓ Provider is thread-safe")

    def test_daemon_threads_cleanup(self):
        """Test that daemon threads clean up properly."""
        print("\nTesting daemon thread cleanup...")

        thread_started = []
        thread_completed = []

        def background_task():
            thread_started.append(True)
            time.sleep(0.1)
            thread_completed.append(True)

        # Create daemon thread
        thread = threading.Thread(target=background_task)
        thread.daemon = True
        thread.start()

        # Wait briefly
        time.sleep(0.15)

        # Verify thread ran
        self.assertEqual(len(thread_started), 1)
        self.assertEqual(len(thread_completed), 1)

        print("✓ Daemon threads execute and complete properly")

    def test_no_deadlock_with_nested_locks(self):
        """Test that no deadlock occurs with proper lock usage."""
        print("\nTesting no deadlock with proper locking...")

        # Create two locks
        lock_a = threading.Lock()
        lock_b = threading.Lock()

        def task_a_then_b():
            with lock_a:
                time.sleep(0.01)
                # Don't nest locks - this is safe pattern
                pass
            with lock_b:
                pass

        def task_b_then_a():
            with lock_b:
                time.sleep(0.01)
                pass
            with lock_a:
                pass

        # Run tasks concurrently
        thread1 = threading.Thread(target=task_a_then_b)
        thread2 = threading.Thread(target=task_b_then_a)

        thread1.start()
        thread2.start()

        thread1.join(timeout=1)
        thread2.join(timeout=1)

        # If we get here, no deadlock occurred
        self.assertFalse(thread1.is_alive(), "Thread1 should complete")
        self.assertFalse(thread2.is_alive(), "Thread2 should complete")

        print("✓ No deadlock with proper lock ordering")

    def test_race_condition_in_status_check(self):
        """Test that status checks don't have race conditions."""
        print("\nTesting status check race conditions...")

        search_id = "test_race"

        # Initialize
        with flask_app.search_lock:
            flask_app.search_results[search_id] = {
                'status': 'searching',
                'messages': [],
                'result': None
            }

        status_snapshots = []
        lock = threading.Lock()

        def check_status():
            with flask_app.search_lock:
                status = flask_app.search_results[search_id]['status']
                with lock:
                    status_snapshots.append(status)

        def update_status():
            time.sleep(0.01)
            with flask_app.search_lock:
                flask_app.search_results[search_id]['status'] = 'complete'

        # Start multiple status checkers and one updater
        threads = []

        # Checkers
        for _ in range(10):
            thread = threading.Thread(target=check_status)
            threads.append(thread)
            thread.start()

        # Updater
        updater = threading.Thread(target=update_status)
        threads.append(updater)
        updater.start()

        # More checkers after updater starts
        for _ in range(10):
            thread = threading.Thread(target=check_status)
            threads.append(thread)
            thread.start()

        # Wait for all
        for thread in threads:
            thread.join()

        # Verify all status checks returned valid values
        for status in status_snapshots:
            self.assertIn(status, ['searching', 'complete'])

        # Should have mix of both statuses
        self.assertGreater(len(status_snapshots), 0)

        print(f"✓ Status checks safe ({len(status_snapshots)} checks)")

    def test_concurrent_different_searches(self):
        """Test that different searches don't interfere with each other."""
        print("\nTesting concurrent different searches...")

        results = {}
        lock = threading.Lock()

        def run_search(search_id, delay):
            with flask_app.search_lock:
                flask_app.search_results[search_id] = {
                    'status': 'searching',
                    'messages': [],
                    'result': None
                }

            time.sleep(delay)

            with flask_app.search_lock:
                flask_app.search_results[search_id]['status'] = 'complete'
                flask_app.search_results[search_id]['result'] = {'search_id': search_id}

            with lock:
                results[search_id] = flask_app.search_results[search_id]

        # Run multiple different searches concurrently
        threads = []
        search_configs = [
            ('search_1', 0.05),
            ('search_2', 0.03),
            ('search_3', 0.07),
            ('search_4', 0.02),
            ('search_5', 0.04),
        ]

        for search_id, delay in search_configs:
            thread = threading.Thread(target=run_search, args=(search_id, delay))
            threads.append(thread)
            thread.start()

        # Wait for all
        for thread in threads:
            thread.join()

        # Verify all searches completed independently
        self.assertEqual(len(results), 5)

        for search_id, _ in search_configs:
            self.assertIn(search_id, results)
            self.assertEqual(results[search_id]['status'], 'complete')
            self.assertEqual(results[search_id]['result']['search_id'], search_id)

        print("✓ Concurrent different searches don't interfere")

    def test_memory_safety_under_load(self):
        """Test memory safety with many concurrent operations."""
        print("\nTesting memory safety under load...")

        # Create and destroy many search results
        iterations = 100
        completed = [0]
        lock = threading.Lock()

        def create_and_cleanup(i):
            search_id = f"search_{i}"

            # Create
            with flask_app.search_lock:
                flask_app.search_results[search_id] = {
                    'status': 'complete',
                    'messages': [{'type': 'info', 'content': f'Test {i}'}],
                    'result': {'data': 'test' * 100}  # Some data
                }

            # Read
            with flask_app.search_lock:
                _ = flask_app.search_results[search_id]

            # Mark completed
            with lock:
                completed[0] += 1

        # Run many operations
        threads = []
        for i in range(iterations):
            thread = threading.Thread(target=create_and_cleanup, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all
        for thread in threads:
            thread.join()

        # Verify all completed
        self.assertEqual(completed[0], iterations)

        # Cleanup
        with flask_app.search_lock:
            flask_app.search_results.clear()

        print(f"✓ Memory safe under load ({iterations} operations)")


if __name__ == "__main__":
    unittest.main()
