# Test Suite

Comprehensive test coverage for the Flights Finder application.

## Test Files

### Unit Tests

#### `test_flight_tool.py`
Tests the FlightTool wrapper class that adapts provider output for LLM consumption.

**Coverage:**
- Wrapping available flight results with status
- Handling unavailable flights
- Provider exception handling
- Field preservation from provider
- Return date parameter passing

**Run:**
```bash
python -m pytest tests/test_flight_tool.py -v
# or
python tests/test_flight_tool.py
```

#### `test_return_pricing.py`
Tests round-trip pricing logic in MockFlightProvider.

**Coverage:**
- Round-trip price multiplier (1.8x)
- One-way vs round-trip pricing comparison
- Random seed reproducibility

**Run:**
```bash
python tests/test_return_pricing.py
```

#### `test_price_filtering.py`
Tests price filtering and currency handling.

**Coverage:**
- MockProvider currency handling
- Natural language query parsing
- Price comparison logic (under/over/equal target)

**Run:**
```bash
python tests/test_price_filtering.py
```

### Integration Tests

#### `test_api_endpoints.py`
Tests Flask REST API endpoints.

**Coverage:**
- Index route serving HTML
- Search endpoint validation
- Search ID generation
- Status endpoint (valid/invalid IDs)
- Full search flow with mock provider
- Amadeus provider credential validation
- Concurrent search handling
- Invalid JSON handling

**Run:**
```bash
python tests/test_api_endpoints.py
```

#### `test_amadeus_provider.py`
Tests AmadeusFlightProvider with mocked API calls.

**Coverage:**
- Amadeus client initialization
- One-way flight search
- Round-trip flight search
- Currency conversion
- Cheapest flight selection
- No results handling
- API error handling
- Currency conversion error fallback

**Run:**
```bash
python tests/test_amadeus_provider.py
```

#### `test_agent_tracking.py`
Tests PriceTrackerAgent AI orchestration.

**Coverage:**
- Agent initialization
- API key requirement
- Query parsing (simple, complex dates, preferences)
- Tracking loop deal detection
- Continuous tracking without deal
- Stop method functionality
- Tool error handling

**Run:**
```bash
python tests/test_agent_tracking.py
```

#### `test_currency_conversion.py`
Tests currency conversion edge cases.

**Coverage:**
- Same currency comparison
- Different currency detection
- EUR/USD conversion
- USD/AUD conversion
- Conversion failure handling
- MockProvider default currency
- Price comparison with conversion
- Zero/negative/large prices
- Decimal precision
- Currency code case sensitivity
- Invalid currency codes

**Run:**
```bash
python tests/test_currency_conversion.py
```

### End-to-End Tests

#### `test_full_search_flow.py`
Tests complete search flows from query to result.

**Coverage:**
- Complete one-way search flow
- Complete round-trip search flow
- Price filtering logic
- Multi-currency search
- No flights handling
- Search with preferences
- CLI/web parameter compatibility
- Error recovery at various stages
- Data consistency across components

**Run:**
```bash
python tests/test_full_search_flow.py
```

#### `test_thread_safety.py`
Tests thread safety and concurrency.

**Coverage:**
- Search lock protection
- Concurrent result updates
- Concurrent read/write operations
- Search ID uniqueness under concurrency
- Provider thread safety
- Daemon thread cleanup
- Deadlock prevention
- Status check race conditions
- Concurrent different searches
- Memory safety under load

**Run:**
```bash
python tests/test_thread_safety.py
```

## Running All Tests

### Run all tests:
```bash
# Using pytest (recommended)
pytest tests/ -v

# Using unittest
python -m unittest discover tests/ -v
```

### Run specific test categories:
```bash
# Unit tests only
pytest tests/test_flight_tool.py tests/test_return_pricing.py tests/test_price_filtering.py -v

# Integration tests only
pytest tests/test_api_endpoints.py tests/test_amadeus_provider.py tests/test_agent_tracking.py tests/test_currency_conversion.py -v

# E2E tests only
pytest tests/test_full_search_flow.py tests/test_thread_safety.py -v
```

### Run with coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

## Test Statistics

- **Total Test Files:** 9
- **Total Test Cases:** 80+
- **Coverage Areas:**
  - FlightTool wrapper
  - Flight data providers (Mock, Amadeus)
  - AI agent orchestration
  - REST API endpoints
  - Currency conversion
  - Thread safety
  - Full search flows

## Test Environment Setup

### Required Environment Variables:
```bash
# For agent and API tests (mocked in tests)
export ANTHROPIC_API_KEY="sk-ant-test-key"

# For Amadeus tests (mocked)
export AMADEUS_API_KEY="test_key"
export AMADEUS_API_SECRET="test_secret"
```

### Install Test Dependencies:
```bash
pip install pytest pytest-cov
```

## Test Coverage Gaps

Tests now cover all major scenarios identified in CLAUDE.md. Previously missing:
- ✅ FlightTool wrapper tests
- ✅ API endpoint tests
- ✅ AmadeusProvider tests
- ✅ Agent tracking loop tests
- ✅ Currency conversion edge cases
- ✅ E2E full search flow tests
- ✅ Thread safety tests

## Adding New Tests

When adding new features, add corresponding tests:

1. **Unit tests:** For individual functions/classes
2. **Integration tests:** For component interactions
3. **E2E tests:** For complete user flows

Follow the existing pattern:
```python
"""
Test suite for [Component Name].

Brief description of what this test file covers.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module import Component


class TestComponent(unittest.TestCase):
    """Test cases for Component."""

    def test_feature(self):
        """Test that feature works correctly."""
        print("\nTesting feature...")

        # Test implementation

        print("✓ Feature works correctly")


if __name__ == "__main__":
    unittest.main()
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    python -m pytest tests/ -v --cov=. --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```
