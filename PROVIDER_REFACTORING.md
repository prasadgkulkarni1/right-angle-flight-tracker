# Provider Configuration Refactoring

## Overview

This document describes the major refactoring completed on January 26, 2026 to make the flight data provider system fully configurable and extensible.

## Motivation

The original implementation had several limitations:
1. **Hardcoded Provider Logic**: Provider selection was hardcoded with if/else statements
2. **Scattered Configuration**: API keys checked in multiple places
3. **Poor Extensibility**: Adding new providers required changes across multiple files
4. **No Centralized Registry**: No single place to see available providers
5. **Static UI**: Provider toggle was fixed to mock/amadeus only

## Solution Architecture

### New Components

#### 1. Configuration System ([flight_tracker/config.py](flight_tracker/config.py))

**`ProviderConfig` Dataclass**:
```python
@dataclass
class ProviderConfig:
    provider_id: str              # Unique identifier (e.g., "amadeus")
    name: str                     # Display name (e.g., "Amadeus (Real Flight Data)")
    enabled: bool                 # Whether provider is enabled
    config_params: Dict           # Provider-specific configuration
    required_env_vars: List[str]  # Required environment variables

    def is_configured(self) -> bool
    def get_missing_vars(self) -> List[str]
```

**`FlightProviderConfig` Class**:
- Centralized registry of all providers
- Methods:
  - `register_provider()` - Add new provider
  - `get_provider_config()` - Get specific provider config
  - `get_available_providers()` - Get only configured providers
  - `get_provider_status()` - Detailed status for UI/CLI

**Global Instance**:
```python
config = FlightProviderConfig()  # Singleton instance
```

#### 2. Provider Factory ([flight_tracker/provider_factory.py](flight_tracker/provider_factory.py))

**`ProviderFactory` Class**:
- Factory pattern for creating provider instances
- Methods:
  - `create_provider(provider_id, target_currency)` - Create specific provider
  - `get_default_provider(target_currency)` - Auto-select best available
  - `list_available_providers()` - Get all available providers
  - `validate_provider(provider_id)` - Check configuration validity

**Benefits**:
- Single place to add new provider creation logic
- Automatic validation of environment variables
- Clear error messages when misconfigured
- Supports auto-detection of best provider

### Updated Components

#### 3. Application Server ([app.py](app.py))

**New Endpoint**: `GET /api/providers`
```json
{
  "providers": [
    {
      "provider_id": "mock",
      "name": "Mock Provider (Test Data)",
      "enabled": true,
      "configured": true,
      "missing_vars": [],
      "description": "..."
    },
    ...
  ]
}
```

**Updated Search Logic**:
```python
# OLD:
if provider_type == 'amadeus':
    # Manual validation and initialization
    provider = AmadeusFlightProvider(...)
else:
    provider = MockFlightProvider()

# NEW:
provider = ProviderFactory.create_provider(provider_type, target_currency)
```

#### 4. Command-Line Interface ([flight_tracker/main.py](flight_tracker/main.py))

**New Features**:
- `--list-providers` - Show all available providers with status
- Dynamic provider choices based on configuration
- Auto-detection when no provider specified
- Better error messages with configuration hints

**Example Output**:
```bash
$ python -m flight_tracker.main --list-providers

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

#### 5. Web User Interface

**Updated HTML** ([static/index.html](static/index.html)):
```html
<!-- OLD: Fixed toggle -->
<input type="checkbox" id="providerToggle">
<span>Real Data (Amadeus)</span>

<!-- NEW: Dynamic dropdown -->
<select id="providerSelect" class="provider-select">
  <option value="">Loading providers...</option>
</select>
<span id="providerStatus" class="provider-status"></span>
```

**Updated JavaScript** ([static/app.js](static/app.js)):
```javascript
// Load providers on page load
async function loadProviders() {
    const response = await fetch('/api/providers');
    const data = await response.json();

    // Populate dropdown
    availableProviders.forEach(provider => {
        const option = document.createElement('option');
        option.value = provider.provider_id;
        option.textContent = provider.name;
        if (!provider.configured) {
            option.textContent += ' (Not configured)';
            option.disabled = true;
        }
        providerSelect.appendChild(option);
    });
}
```

**Updated CSS** ([static/style.css](static/style.css)):
- New `.provider-selector` styles
- `.provider-select` dropdown styles
- `.provider-status` indicator styles (✓ Ready / ✗ Not configured)

### Supporting Files

#### 6. Configuration Guide ([PROVIDER_CONFIGURATION.md](PROVIDER_CONFIGURATION.md))

Comprehensive 350+ line guide covering:
- Overview of provider system
- Configuration for each provider (Mock, Amadeus)
- How to add new providers (step-by-step)
- Environment variable reference
- Troubleshooting guide
- Security best practices
- Example workflows

#### 7. Environment Template ([.env.example](.env.example))

Template file showing all required and optional environment variables:
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional providers
AMADEUS_API_KEY=your-amadeus-api-key
AMADEUS_API_SECRET=your-amadeus-api-secret
```

## Migration Guide

### For Existing Code

**Before** (Direct instantiation):
```python
if provider_type == 'amadeus':
    amadeus_key = os.environ.get("AMADEUS_API_KEY")
    if not amadeus_key:
        raise ValueError("Missing AMADEUS_API_KEY")
    provider = AmadeusFlightProvider(amadeus_key, amadeus_secret)
else:
    provider = MockFlightProvider()
```

**After** (Factory pattern):
```python
try:
    provider = ProviderFactory.create_provider(provider_type, target_currency)
except (ValueError, RuntimeError) as e:
    print(f"Error: {e}")
    # Factory provides detailed error messages
```

### For New Providers

To add a new provider (e.g., Skyscanner):

1. **Implement provider class** in [flight_tracker/flight_data.py](flight_tracker/flight_data.py):
```python
class SkyscannerFlightProvider(FlightProvider):
    def __init__(self, api_key, target_currency=None):
        self.api_key = api_key
        self.target_currency = target_currency

    def get_price(self, origin, destination, date, return_date=None):
        # Implementation
        pass
```

2. **Register in config** ([flight_tracker/config.py](flight_tracker/config.py)):
```python
self.register_provider(ProviderConfig(
    provider_id="skyscanner",
    name="Skyscanner",
    enabled=True,
    config_params={
        "description": "Real-time flight data from Skyscanner"
    },
    required_env_vars=["SKYSCANNER_API_KEY"]
))
```

3. **Add factory support** ([flight_tracker/provider_factory.py](flight_tracker/provider_factory.py)):
```python
elif provider_id == "skyscanner":
    api_key = os.environ.get("SKYSCANNER_API_KEY")
    return SkyscannerFlightProvider(api_key, target_currency)
```

4. **Done!** The provider will automatically appear in:
   - CLI `--list-providers` output
   - Web UI dropdown
   - API `/api/providers` endpoint

## Benefits

### 1. Extensibility
- Adding new providers takes ~20 lines of code
- No changes needed to UI, API endpoints, or CLI argument parsing
- Configuration and factory handle all the complexity

### 2. Discoverability
- `--list-providers` shows what's available
- UI dropdown dynamically populated
- API endpoint for programmatic discovery

### 3. User Experience
- Clear status indicators (✓ Ready / ✗ Not configured)
- Helpful error messages with missing env vars
- Auto-detection of best available provider

### 4. Maintainability
- Configuration centralized in one place
- Provider creation logic isolated in factory
- Clear separation of concerns

### 5. Testing
- Easy to mock providers via factory
- Configuration can be mocked for tests
- No hardcoded dependencies

## Testing

All existing tests remain passing. New functionality tested manually:

**CLI Testing**:
```bash
# List providers
python -m flight_tracker.main --list-providers

# Use specific provider
python -m flight_tracker.main --query "Find flights..." --provider mock

# Auto-detect (selects first non-mock configured provider)
python -m flight_tracker.main --query "Find flights..."
```

**Web UI Testing**:
```bash
# Start server
python app.py

# Check providers endpoint
curl http://localhost:5000/api/providers

# Test UI dropdown populates correctly
# Test disabled providers cannot be selected
# Test status indicator updates on selection
```

## Files Changed

### New Files (4):
1. [flight_tracker/config.py](flight_tracker/config.py) - 143 lines
2. [flight_tracker/provider_factory.py](flight_tracker/provider_factory.py) - 145 lines
3. [PROVIDER_CONFIGURATION.md](PROVIDER_CONFIGURATION.md) - 350+ lines
4. [.env.example](.env.example) - 60 lines

### Modified Files (5):
1. [app.py](app.py) - Added `/api/providers` endpoint, refactored search logic
2. [flight_tracker/main.py](flight_tracker/main.py) - Added `--list-providers`, refactored provider init
3. [static/index.html](static/index.html) - Replaced toggle with dropdown
4. [static/app.js](static/app.js) - Added provider loading and selection logic
5. [static/style.css](static/style.css) - Added dropdown and status indicator styles

### Documentation Files (This file):
- [PROVIDER_REFACTORING.md](PROVIDER_REFACTORING.md) - This document

## Next Steps

### Recommended Enhancements:

1. **Add More Providers**:
   - Skyscanner API integration
   - Kayak web scraping
   - Google Flights unofficial API
   - Direct airline APIs (United, Delta, etc.)

2. **Provider-Specific Features**:
   - Support provider-specific filters (cabin class, stops, etc.)
   - Provider-specific metadata (reliability score, average response time)
   - Provider preference ordering

3. **Configuration Persistence**:
   - Save provider preferences per user
   - Remember last used provider
   - Store provider credentials securely (vault integration)

4. **Monitoring & Logging**:
   - Track provider success/failure rates
   - Log API response times
   - Alert on provider failures

5. **Testing**:
   - Unit tests for ProviderFactory
   - Integration tests for provider switching
   - E2E tests for UI provider selection

## Conclusion

This refactoring transforms the flight tracker from a two-provider system with hardcoded logic into a flexible, extensible multi-provider architecture. The factory pattern and centralized configuration make it trivial to add new providers while maintaining backwards compatibility with existing code.

**Impact**:
- ✅ Easier to maintain
- ✅ Easier to extend
- ✅ Better user experience
- ✅ Production-ready architecture
- ✅ No breaking changes

**Time Investment**: ~3 hours
**Complexity Added**: Minimal (abstraction reduces complexity)
**Value**: High (enables future growth)
