# Flight Data Provider Configuration Guide

This guide explains how to configure different flight data providers for the Flights Finder application.

## Overview

The Flights Finder supports multiple flight data providers through a flexible configuration system. Each provider can be enabled/disabled and requires specific API credentials.

## Architecture

- **Configuration System**: [flight_tracker/config.py](flight_tracker/config.py)
- **Provider Factory**: [flight_tracker/provider_factory.py](flight_tracker/provider_factory.py)
- **Provider Implementations**: [flight_tracker/flight_data.py](flight_tracker/flight_data.py)

## Available Providers

### 1. Mock Provider (Test Data)

**Provider ID**: `mock`
**Status**: Always available (no configuration required)
**Best for**: Development, testing, demos

The Mock Provider generates random flight prices for testing purposes. No API keys or credentials are needed.

**Configuration**:
```bash
# No environment variables needed
```

**Usage**:
```bash
# CLI
python -m flight_tracker.main --query "Find flights from SYD to BLR" --provider mock

# Web UI
# Select "Mock Provider (Test Data)" from the dropdown
```

**Features**:
- Generates prices between $100-$1000
- Supports round-trip pricing (1.8x multiplier)
- Simulates 0.5s network latency
- Configurable currency support

---

### 2. Amadeus Provider (Real Flight Data)

**Provider ID**: `amadeus`
**Status**: Requires API credentials
**Best for**: Production, real flight searches

The Amadeus Provider fetches real-time flight data from the Amadeus Flight Offers Search API.

**Configuration**:

1. **Sign up for Amadeus API**:
   - Visit: https://developers.amadeus.com/
   - Create a free account
   - Create a new app in the dashboard
   - Copy your API Key and API Secret

2. **Set environment variables**:
```bash
export AMADEUS_API_KEY="your_api_key_here"
export AMADEUS_API_SECRET="your_api_secret_here"
```

Or add to your `.env` file:
```bash
AMADEUS_API_KEY=your_api_key_here
AMADEUS_API_SECRET=your_api_secret_here
```

**Usage**:
```bash
# CLI
python -m flight_tracker.main --query "Find flights from SYD to BLR" --provider amadeus

# Web UI
# Select "Amadeus (Real Flight Data)" from the dropdown
```

**Features**:
- Real-time flight data from 400+ airlines
- Actual pricing in original currency
- Automatic currency conversion
- Flight numbers and airline codes
- Booking URLs (Google Flights)

**Limitations**:
- Rate limits apply (varies by API plan)
- Free tier: ~2000 requests/month
- Requires internet connection
- API response time: 1-3 seconds

---

## Configuration Management

### Listing Available Providers

**CLI**:
```bash
python -m flight_tracker.main --list-providers
```

Output example:
```
=============================================================
AVAILABLE FLIGHT DATA PROVIDERS
=============================================================

✓ Mock Provider (Test Data) (ID: mock)
   Status: Ready
   Description: Generates random test data for development

✗ Amadeus (Real Flight Data) (ID: amadeus)
   Status: Not configured
   Description: Real-time flight data from Amadeus API
   Missing: AMADEUS_API_KEY, AMADEUS_API_SECRET

=============================================================
```

**Web UI**:
- The provider selector dropdown shows all providers
- Unavailable providers are marked "(Not configured)" and disabled
- Status indicator shows ✓ Ready or ✗ Missing credentials

**API Endpoint**:
```bash
curl http://localhost:5000/api/providers
```

Response:
```json
{
  "providers": [
    {
      "provider_id": "mock",
      "name": "Mock Provider (Test Data)",
      "enabled": true,
      "configured": true,
      "missing_vars": [],
      "description": "Generates random test data for development"
    },
    {
      "provider_id": "amadeus",
      "name": "Amadeus (Real Flight Data)",
      "enabled": true,
      "configured": false,
      "missing_vars": ["AMADEUS_API_KEY", "AMADEUS_API_SECRET"],
      "description": "Real-time flight data from Amadeus API"
    }
  ]
}
```

---

## Adding New Providers

To add a new flight data provider:

### Step 1: Implement Provider Class

Add to [flight_tracker/flight_data.py](flight_tracker/flight_data.py):

```python
class NewFlightProvider(FlightProvider):
    """Description of your provider."""

    def __init__(self, api_key: str, target_currency: str = None):
        self.api_key = api_key
        self.target_currency = target_currency

    def get_price(self, origin: str, destination: str, date: str, return_date: str = None) -> Optional[Dict]:
        """Fetch flight data from your API."""
        # Implementation here
        return {
            "price": 500.00,
            "currency": "USD",
            "airline": "XX",
            "flight_number": "XX123",
            "booking_url": "https://...",
            "trip_type": "one-way",
            "departure_date": date,
            "return_date": return_date
        }
```

### Step 2: Register Provider

Add to [flight_tracker/config.py](flight_tracker/config.py) in `_load_default_providers()`:

```python
self.register_provider(ProviderConfig(
    provider_id="newprovider",
    name="New Provider Name",
    enabled=True,
    config_params={
        "api_base_url": "https://api.newprovider.com",
        "description": "Description of what this provider does"
    },
    required_env_vars=["NEW_PROVIDER_API_KEY"]
))
```

### Step 3: Add Factory Support

Update [flight_tracker/provider_factory.py](flight_tracker/provider_factory.py) in `create_provider()`:

```python
elif provider_id == "newprovider":
    api_key = os.environ.get("NEW_PROVIDER_API_KEY")
    return NewFlightProvider(
        api_key=api_key,
        target_currency=target_currency
    )
```

### Step 4: Test

```bash
# Set API key
export NEW_PROVIDER_API_KEY="your_key"

# List providers
python -m flight_tracker.main --list-providers

# Use provider
python -m flight_tracker.main --query "Find flights..." --provider newprovider
```

---

## Environment Variables Reference

### Required for All Modes

```bash
# Claude AI for natural language parsing
ANTHROPIC_API_KEY="sk-ant-..."
```

### Provider-Specific

```bash
# Amadeus Provider
AMADEUS_API_KEY="your_amadeus_key"
AMADEUS_API_SECRET="your_amadeus_secret"

# Add your new providers here
# SKYSCANNER_API_KEY="your_skyscanner_key"
# KAYAK_API_KEY="your_kayak_key"
```

### Setting Environment Variables

**Linux/macOS**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export AMADEUS_API_KEY="your_key"
```

**Windows (Command Prompt)**:
```cmd
set ANTHROPIC_API_KEY=sk-ant-...
set AMADEUS_API_KEY=your_key
```

**Windows (PowerShell)**:
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-..."
$env:AMADEUS_API_KEY="your_key"
```

**Using .env file** (recommended):

Create a `.env` file in the project root:
```bash
ANTHROPIC_API_KEY=sk-ant-...
AMADEUS_API_KEY=your_key
AMADEUS_API_SECRET=your_secret
```

Then load with python-dotenv:
```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Provider Selection Priority

### CLI Mode
1. **Explicit**: Uses `--provider <id>` if specified
2. **Auto-detect**: Uses first available non-mock provider
3. **Fallback**: Uses mock provider if no others configured

### Web UI
- User selects from dropdown
- Only configured providers are selectable
- Unconfigured providers shown but disabled

### API Mode
- Client specifies provider in request body
- Returns error if provider not configured

---

## Troubleshooting

### Provider Shows as "Not configured"

**Problem**: Provider appears in list but marked as not configured

**Solution**:
1. Check environment variables are set:
   ```bash
   echo $AMADEUS_API_KEY
   echo $AMADEUS_API_SECRET
   ```
2. Restart the application after setting variables
3. Verify variable names match exactly (case-sensitive)

### "Provider not found" Error

**Problem**: CLI returns "Unknown provider: xyz"

**Solution**:
1. List available providers: `python -m flight_tracker.main --list-providers`
2. Check provider ID spelling matches exactly
3. Verify provider is registered in config.py

### API Credentials Not Working

**Problem**: Provider configured but API calls fail

**Solution**:
1. Verify credentials are valid on provider's website
2. Check API key hasn't expired
3. Ensure you're within rate limits
4. Test credentials with provider's test endpoint

### Currency Conversion Errors

**Problem**: Prices show in wrong currency or conversion fails

**Solution**:
1. Check internet connection (forex rates fetched online)
2. Verify target currency code is valid (USD, EUR, GBP, etc.)
3. Provider will fall back to original currency if conversion fails

---

## Best Practices

1. **Use Mock for Development**: Fast, no rate limits, no costs
2. **Use Real Providers for Production**: Amadeus for actual flight data
3. **Set Environment Variables Securely**: Don't commit API keys to git
4. **Add .env to .gitignore**: Prevent accidental credential exposure
5. **Monitor API Usage**: Check provider dashboards for quota usage
6. **Handle Provider Failures Gracefully**: App continues with fallback
7. **Cache Responses**: Consider caching to reduce API calls

---

## Security Considerations

- **Never commit API keys**: Use .env files and add to .gitignore
- **Rotate keys regularly**: Change credentials periodically
- **Use environment-specific keys**: Different keys for dev/staging/prod
- **Monitor for unauthorized usage**: Check provider dashboards
- **Limit key permissions**: Use read-only keys when possible
- **Validate all inputs**: Prevent injection attacks
- **Use HTTPS only**: Never send credentials over HTTP

---

## Example Workflows

### Local Development
```bash
# Use mock provider (no setup needed)
export ANTHROPIC_API_KEY="sk-ant-..."
python -m flight_tracker.main --query "Find flights..." --provider mock
```

### Testing with Real Data
```bash
# Configure Amadeus
export ANTHROPIC_API_KEY="sk-ant-..."
export AMADEUS_API_KEY="your_key"
export AMADEUS_API_SECRET="your_secret"

# Use Amadeus provider
python -m flight_tracker.main --query "Find flights..." --provider amadeus
```

### Production Deployment
```bash
# Set all required variables
export ANTHROPIC_API_KEY="sk-ant-..."
export AMADEUS_API_KEY="prod_key"
export AMADEUS_API_SECRET="prod_secret"

# Start web server (auto-selects best provider)
python app.py
```

---

## Support

For issues related to:
- **Mock Provider**: Check [flight_tracker/flight_data.py](flight_tracker/flight_data.py:29-76)
- **Amadeus Provider**: Visit https://developers.amadeus.com/support
- **Configuration System**: See [flight_tracker/config.py](flight_tracker/config.py)
- **Provider Factory**: See [flight_tracker/provider_factory.py](flight_tracker/provider_factory.py)

---

## What's Next?

Once you have providers configured, see:
- [QUICK_START.md](QUICK_START.md) - Getting started guide
- [DOCUMENTATION.md](DOCUMENTATION.md) - Technical architecture
- [CLAUDE.md](CLAUDE.md) - Development history and context
