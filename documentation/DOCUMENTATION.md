# Flights Finder Application - Technical Documentation

## Overview

This Flights Finder application is built using Google's Antigravity framework and leverages **Anthropic's Claude AI** to create an intelligent flight price tracking system. The application uses natural language processing to understand user queries and can search for flights using either mock data or real flight information from the Amadeus API.

### Key Technologies
- **Backend**: Flask (Python web framework)
- **AI/LLM**: Anthropic Claude (Opus 4.5 model) via Antigravity
- **Flight Data**: Amadeus API for real flights, Mock provider for testing
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Currency Conversion**: forex-python library

---

## Architecture

The application follows a modular architecture with clear separation of concerns:

```
binary-aldrin/
├── app.py                      # Flask web server (entry point for web UI)
├── flight_tracker/             # Core business logic module
│   ├── agent.py               # AI agent orchestration (Claude integration)
│   ├── flight_data.py         # Data providers and flight tools
│   └── main.py                # CLI entry point
├── static/                     # Frontend assets
│   ├── index.html             # Web UI structure
│   ├── app.js                 # Client-side logic
│   └── style.css              # Styling
├── test_return_pricing.py     # Unit tests for return flight pricing
├── test_price_filtering.py    # Unit tests for price filtering
└── debug_auth.py              # API key validation utility
```

---

## Core Components

### 1. Flask Web Server ([app.py](app.py))

**Purpose**: Provides a REST API and serves the web UI.

#### Key Endpoints:

**`GET /`**
- Serves the main HTML page (index.html)
- Entry point for the web application

**`POST /api/search`**
- Accepts flight search queries in natural language
- Request body:
  ```json
  {
    "query": "Find return flights from Sydney to Bangalore in June under AUD 1200",
    "provider": "mock" | "amadeus"
  }
  ```
- Returns a search ID for polling status
- Spawns a background thread to process the search asynchronously

**`GET /api/status/<search_id>`**
- Polls the status of a search operation
- Returns current status: `parsing`, `searching`, `complete`, or `error`
- Includes progress messages and final results

#### How It Works:

1. **Query Reception**: Receives natural language query from frontend
2. **Background Processing**: Creates daemon thread to avoid blocking
3. **Query Parsing**: Uses Claude AI to extract structured parameters from natural language
4. **Provider Selection**: Initializes MockFlightProvider or AmadeusFlightProvider
5. **Flight Search**: Retrieves flight data through the FlightTool
6. **Price Comparison**: Checks if found flights meet target price criteria
7. **Response**: Updates search results accessible via status endpoint

#### Threading Model:
```python
def run_search():
    # 1. Parse query using Claude
    params = PriceTrackerAgent.parse_query(query, api_key)

    # 2. Initialize provider
    provider = AmadeusFlightProvider(...) or MockFlightProvider(...)

    # 3. Search for flights
    flight_details = tool.get_price(origin, destination, date, return_date)

    # 4. Compare price with target
    if flight_price <= target_price:
        # DEAL FOUND
    else:
        # Price too high
```

---

### 2. AI Agent Orchestration ([flight_tracker/agent.py](flight_tracker/agent.py))

**Purpose**: Manages the AI agent that interacts with Claude to track flight prices.

#### Class: `PriceTrackerAgent`

This is the brain of the application. It orchestrates communication between the user, Claude AI, and flight data providers.

#### Key Methods:

**`parse_query(query: str, api_key: str) -> dict`** (Static Method)
- Uses Claude Opus 4.5 to parse natural language into structured parameters
- Input: `"Find return flights from Sydney to Bangalore in June under AUD 1200"`
- Output:
  ```python
  {
      "origin": "SYD",
      "destination": "BLR",
      "date": "2026-06-01",
      "return_date": "2026-06-30",
      "target_price": 1200,
      "target_currency": "AUD",
      "preferred_airlines": None,
      "max_duration": None
  }
  ```

**How Query Parsing Works**:
```python
# 1. Construct prompt for Claude
prompt = f"""Extract flight search parameters from: "{query}"
Return JSON with: origin, destination, date, return_date, target_price, target_currency...
"""

# 2. Send to Claude API
response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}]
)

# 3. Parse JSON response
params = json.loads(response.content[0].text)
```

**`track_price(...)`** (Instance Method)
- Continuously monitors flight prices (used in CLI mode)
- Creates a conversation loop with Claude
- Uses Claude's **tool use** capability to call `get_price`
- Stops when a deal matching criteria is found

#### Claude Tool Use Pattern:

The agent defines a tool schema that Claude can invoke:
```python
tools = [{
    "name": "get_price",
    "description": "Get flight price for a route and date",
    "input_schema": {
        "type": "object",
        "properties": {
            "origin": {"type": "string"},
            "destination": {"type": "string"},
            "date": {"type": "string"}
        }
    }
}]
```

**Agent Conversation Flow**:
```
User → "Check SYD to BLR on June 1, target: AUD 1200"
  ↓
Claude → [Decides to use get_price tool]
  ↓
Agent → Executes tool.get_price("SYD", "BLR", "2026-06-01")
  ↓
Agent → Returns result to Claude as tool_result
  ↓
Claude → Analyzes price vs target
  ↓
Claude → "DEAL FOUND" or "Price too high"
```

#### Message History Management:
The agent maintains conversation context:
```python
self.messages = [
    {"role": "user", "content": "Check flight price..."},
    {"role": "assistant", "content": [tool_use_block]},
    {"role": "user", "content": [tool_result_block]},
    {"role": "assistant", "content": "DEAL FOUND..."}
]
```

---

### 3. Flight Data Providers ([flight_tracker/flight_data.py](flight_tracker/flight_data.py))

**Purpose**: Abstract interface for flight data sources with multiple implementations.

#### Class Hierarchy:

```
FlightProvider (ABC)
    ├── MockFlightProvider
    └── AmadeusFlightProvider
```

#### `FlightProvider` (Abstract Base Class)
Defines the contract all providers must implement:
```python
@abstractmethod
def get_price(origin: str, destination: str, date: str, return_date: str = None) -> Optional[Dict]:
    pass
```

#### `MockFlightProvider`
**Purpose**: Testing and demonstration without API costs

**How It Works**:
```python
def get_price(...):
    # 1. Simulate network delay
    time.sleep(0.5)

    # 2. Generate random base price
    base_price = random.uniform(100, 1000)

    # 3. Adjust for round-trip (1.8x multiplier)
    if return_date:
        base_price *= 1.8

    # 4. Return mock flight data
    return {
        "price": round(base_price, 2),
        "currency": self.default_currency,
        "airline": "MOCK",
        "flight_number": "MOCK123",
        "trip_type": "round-trip" if return_date else "one-way",
        ...
    }
```

**Key Feature**: Round-trip flights cost 1.8x the one-way base price

#### `AmadeusFlightProvider`
**Purpose**: Real flight data from Amadeus Flight Offers Search API

**Authentication**:
```python
from amadeus import Client
self.client = Client(
    client_id=api_key,
    client_secret=api_secret
)
```

**Search Process**:
```python
def get_price(...):
    # 1. Build search parameters
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": date,
        "adults": 1
    }
    if return_date:
        params["returnDate"] = return_date

    # 2. Call Amadeus API
    response = self.client.shopping.flight_offers_search.get(**params)

    # 3. Find cheapest offer
    best_offer = min(response.data, key=lambda x: float(x['price']['total']))

    # 4. Extract details
    original_price = float(best_offer['price']['total'])
    original_currency = best_offer['price']['currency']

    # 5. Convert currency if needed
    if self.target_currency != original_currency:
        converted_price = CurrencyRates().convert(...)

    # 6. Return structured data
    return {
        "price": converted_price,
        "currency": target_currency,
        "airline": airline_code,
        "flight_number": flight_number,
        ...
    }
```

**Currency Conversion**:
Uses `forex-python` library to convert prices to user's target currency:
```python
from forex_python.converter import CurrencyRates
c = CurrencyRates()
converted = c.convert("EUR", "AUD", 500)  # EUR 500 → AUD
```

#### `FlightTool`
**Purpose**: Wrapper that adapts provider output for LLM consumption

```python
class FlightTool:
    def get_price(self, origin, destination, date, return_date=None):
        flight_details = self.provider.get_price(...)
        if flight_details:
            return {"status": "AVAILABLE", **flight_details}
        else:
            return {"status": "UNAVAILABLE", "error": "..."}
```

---

### 4. Command-Line Interface ([flight_tracker/main.py](flight_tracker/main.py))

**Purpose**: CLI for direct command-line usage without web UI

#### Usage Modes:

**Natural Language Query**:
```bash
python -m flight_tracker.main --query "Find flights from SYD to BLR on June 1 under $500"
```

**Structured Arguments**:
```bash
python -m flight_tracker.main --origin SYD --destination BLR --date 2026-06-01 --target 500
```

**Provider Selection**:
```bash
python -m flight_tracker.main --query "..." --provider amadeus
```

#### Workflow:
```python
def main():
    # 1. Parse arguments
    args = parser.parse_args()

    # 2. If natural language, parse with Claude
    if args.query:
        params = PriceTrackerAgent.parse_query(args.query, api_key)

    # 3. Initialize provider
    provider = AmadeusFlightProvider(...) or MockFlightProvider()

    # 4. Create agent
    agent = PriceTrackerAgent(tool=FlightTool(provider))

    # 5. Start continuous tracking
    agent.track_price(
        origin, destination, date, target_price,
        notification_callback=notify
    )
```

---

### 5. Frontend ([static/](static/))

#### HTML Structure ([index.html](static/index.html))

**Key Elements**:
- **Header**: Logo and provider toggle (Mock vs Amadeus)
- **Search Box**: Auto-resizing textarea for natural language input
- **Example Queries**: Pre-filled search buttons for common routes
- **Results Container**: Dynamically populated with flight cards

#### JavaScript Logic ([app.js](static/app.js))

**Search Flow**:
```javascript
async function sendQuery() {
    // 1. Get query and provider selection
    const query = queryInput.value.trim();
    const provider = providerToggle.checked ? 'amadeus' : 'mock';

    // 2. Send POST to /api/search
    const response = await fetch('/api/search', {
        method: 'POST',
        body: JSON.stringify({ query, provider })
    });

    // 3. Get search ID
    const data = await response.json();
    currentSearchId = data.search_id;

    // 4. Start polling
    pollStatus();
}
```

**Polling Mechanism**:
```javascript
async function pollStatus() {
    // Fetch status every 500ms
    const response = await fetch(`/api/status/${currentSearchId}`);
    const data = await response.json();

    if (data.status === 'complete') {
        displayFlightCard(data.result);
    } else if (data.status === 'error') {
        showError(data.messages);
    } else {
        // Continue polling
        setTimeout(pollStatus, 500);
    }
}
```

**Flight Card Display**:
```javascript
function displayFlightCard(flight) {
    // Display: Price, currency conversion info, airline, dates
    // Show "Converted from EUR 500" if currency was converted
    // Add "Book Flight" button linking to booking_url
}
```

---

## Complete Data Flow

### Web UI Search Flow:

```
1. User enters query: "Find return flights from Sydney to Bangalore in June under AUD 1200"
   ↓
2. Frontend sends POST /api/search
   ↓
3. Flask spawns background thread
   ↓
4. PriceTrackerAgent.parse_query() → Claude extracts parameters
   ↓
5. Initialize AmadeusFlightProvider with target_currency="AUD"
   ↓
6. FlightTool.get_price("SYD", "BLR", "2026-06-01", "2026-06-30")
   ↓
7. AmadeusFlightProvider calls Amadeus API
   ↓
8. Find cheapest offer: EUR 500 (original price)
   ↓
9. Convert EUR 500 → AUD 800 using forex_python
   ↓
10. Compare: AUD 800 <= AUD 1200 ✓ DEAL FOUND
    ↓
11. Update search_results[search_id] with flight details
    ↓
12. Frontend polls GET /api/status/{search_id}
    ↓
13. Receives result and displays flight card
```

### CLI Tracking Flow:

```
1. User runs: python -m flight_tracker.main --query "..."
   ↓
2. Parse query → structured parameters
   ↓
3. Create PriceTrackerAgent with FlightTool
   ↓
4. agent.track_price() enters loop
   ↓
5. Each iteration:
   - Send prompt to Claude: "Check flight price, target is $X"
   - Claude uses get_price tool
   - Agent executes tool, returns result to Claude
   - Claude analyzes: "DEAL FOUND" or "Price too high"
   ↓
6. If "DEAL FOUND": trigger notification_callback() and stop
   ↓
7. Otherwise: sleep for check_interval_seconds, repeat
```

---

## Key Features

### 1. Natural Language Understanding
Uses Claude AI to parse complex queries:
- Date ranges: "first week of June" → "2026-06-01"
- Airport codes: "Sydney" → "SYD"
- Currency extraction: "under AUD 1200" → target_currency="AUD", target_price=1200
- Optional parameters: airline preferences, max duration

### 2. Multi-Currency Support
- Accepts target prices in any currency (USD, AUD, EUR, etc.)
- Converts flight prices from original currency to target currency
- Displays both original and converted prices in UI

### 3. Round-Trip vs One-Way
- Detects trip type from query or parameters
- MockProvider applies 1.8x multiplier for round-trips
- Amadeus API natively supports round-trip searches

### 4. Provider Abstraction
- Abstract `FlightProvider` interface
- Easy to add new providers (e.g., Skyscanner, Kayak)
- Switch between providers via UI toggle or CLI flag

### 5. Asynchronous Processing
- Web requests don't block on slow API calls
- Background threads handle search operations
- Polling-based status updates for smooth UX

---

## Testing Strategy

### Test Files:

#### [test_return_pricing.py](test_return_pricing.py)
**Purpose**: Verify round-trip pricing logic

```python
def test_mock_return_price_higher():
    # Fix random seed for reproducibility
    random.seed(42)
    price_one_way = provider.get_price("SYD", "BLR", "2026-06-01")['price']

    random.seed(42)
    price_return = provider.get_price("SYD", "BLR", "2026-06-01", "2026-06-10")['price']

    # Assert: return price should be higher (1.8x)
    assert price_return > price_one_way
```

**What It Tests**:
- MockProvider correctly applies round-trip multiplier
- Return flights cost more than one-way flights

#### [test_price_filtering.py](test_price_filtering.py)
**Purpose**: Verify price comparison and currency handling

**Test Cases**:
1. **Currency Handling**: MockProvider returns correct default currency
2. **Query Parsing**: Claude correctly extracts all parameters including currency
3. **Price Comparison**: Flights under target pass, over target fail

```python
def test_price_comparison_logic():
    # Under target: 800 <= 1200 → PASS
    # Over target: 1600 > 1200 → FAIL
    # Exactly at target: 1200 <= 1200 → PASS
```

#### [debug_auth.py](debug_auth.py)
**Purpose**: Validate Anthropic API key setup

```python
def test_key():
    # 1. Check environment variable
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    # 2. Validate format (should start with "sk-ant-")
    if not api_key.startswith("sk-"):
        print("WARNING: Invalid key format")

    # 3. Test API call
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(...)

    # 4. Report success/failure
```

---

## Environment Variables

Required for full functionality:

```bash
# Required for AI features (query parsing, price analysis)
export ANTHROPIC_API_KEY="sk-ant-..."

# Required only for real flight data
export AMADEUS_API_KEY="your_amadeus_key"
export AMADEUS_API_SECRET="your_amadeus_secret"
```

---

## API Integration Details

### Anthropic Claude API

**Model Used**: `claude-opus-4-5` (latest Opus model)

**API Calls**:
1. **Query Parsing**: Single message with structured prompt
2. **Price Tracking**: Conversation with tool use enabled

**Tool Use Schema**:
```json
{
  "name": "get_price",
  "description": "Get flight price for a route and date",
  "input_schema": {
    "type": "object",
    "properties": {
      "origin": {"type": "string", "description": "IATA code"},
      "destination": {"type": "string", "description": "IATA code"},
      "date": {"type": "string", "description": "YYYY-MM-DD"}
    },
    "required": ["origin", "destination", "date"]
  }
}
```

**Response Processing**:
```python
# Check stop_reason
if response.stop_reason == "tool_use":
    # Extract tool_use block
    tool_use = next(b for b in response.content if b.type == "tool_use")

    # Execute tool
    result = self.tool.get_price(**tool_use.input)

    # Send result back to Claude
    messages.append({
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": str(result)
        }]
    })
```

### Amadeus Flight Offers Search API

**Endpoint**: `GET /v2/shopping/flight-offers`

**Authentication**: OAuth2 with client credentials
```python
from amadeus import Client
client = Client(client_id=..., client_secret=...)
```

**Search Parameters**:
- `originLocationCode`: IATA code (e.g., "SYD")
- `destinationLocationCode`: IATA code (e.g., "BLR")
- `departureDate`: YYYY-MM-DD
- `returnDate`: YYYY-MM-DD (optional)
- `adults`: Number of passengers (default: 1)

**Response Structure**:
```json
{
  "data": [
    {
      "price": {
        "total": "500.00",
        "currency": "EUR"
      },
      "itineraries": [{
        "segments": [{
          "carrierCode": "EK",
          "number": "412",
          "departure": {...},
          "arrival": {...}
        }]
      }]
    }
  ]
}
```

---

## Design Patterns Used

### 1. **Strategy Pattern**
`FlightProvider` abstraction allows swapping data sources:
```python
provider = MockFlightProvider() if testing else AmadeusFlightProvider()
tool = FlightTool(provider=provider)
```

### 2. **Adapter Pattern**
`FlightTool` adapts provider output for LLM consumption:
```python
# Provider returns: {price, currency, airline, ...}
# Tool returns: {status: "AVAILABLE", price, currency, ...}
```

### 3. **Observer Pattern** (Implicit)
Notification callback pattern for deal alerts:
```python
def notify(message):
    print(f"DEAL FOUND: {message}")

agent.track_price(..., notification_callback=notify)
```

### 4. **Polling Pattern**
Frontend polls backend for async operation status:
```javascript
async function pollStatus() {
    const data = await fetch(`/api/status/${searchId}`);
    if (data.status !== 'complete') {
        setTimeout(pollStatus, 500); // Poll every 500ms
    }
}
```

---

## Error Handling

### Backend:
```python
try:
    flight_details = tool.get_price(...)
    if flight_details and flight_details['status'] == 'AVAILABLE':
        # Success path
    else:
        # No flights available
except Exception as e:
    search_results[search_id]['status'] = 'error'
    search_results[search_id]['messages'].append({
        'type': 'error',
        'content': str(e)
    })
```

### Frontend:
```javascript
try {
    const response = await fetch('/api/search', ...);
    if (!response.ok) throw new Error('Search failed');
    // Success path
} catch (error) {
    showError(`Error: ${error.message}`);
    resetSearchButton();
}
```

---

## Performance Considerations

### 1. **Background Threading**
- Web searches run in daemon threads to avoid blocking Flask
- Multiple searches can run concurrently

### 2. **Caching Potential** (Not Implemented)
Could cache:
- Currency conversion rates (valid for hours)
- Flight search results (valid for minutes)
- Claude query parsing (exact query matches)

### 3. **Polling Interval**
- Frontend polls every 500ms (balance between responsiveness and server load)
- Agent checks flights every 1-2 seconds in CLI mode

### 4. **Mock Provider Latency**
Artificial 0.5s delay simulates real API calls for realistic testing

---

## Security Considerations

### 1. **API Key Management**
- Keys stored in environment variables (never committed to code)
- Debug utility validates key format before use

### 2. **CORS Configuration**
```python
from flask_cors import CORS
CORS(app)  # Enable cross-origin requests for development
```

### 3. **Input Validation**
```python
if not query:
    return jsonify({'error': 'Query is required'}), 400

required = ["origin", "destination", "date", "target_price"]
missing = [k for k in required if not params.get(k)]
if missing:
    raise ValueError(f"Missing: {', '.join(missing)}")
```

---

## Future Enhancement Opportunities

### 1. **Database Integration**
- Store search history
- Track price changes over time
- User accounts and saved searches

### 2. **Email/SMS Notifications**
Instead of console output, send real notifications when deals are found

### 3. **Additional Providers**
- Skyscanner API
- Google Flights scraping
- Kayak integration

### 4. **Advanced Filtering**
- Stops/layovers preferences
- Departure time windows
- Seat class (economy, business, first)

### 5. **Price Prediction**
Use Claude to analyze historical trends and predict best booking times

### 6. **Multi-City Routes**
Support complex itineraries beyond simple round-trips

---

## Running the Application

### Web UI:
```bash
# Set up environment
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional: For real flight data
export AMADEUS_API_KEY="..."
export AMADEUS_API_SECRET="..."

# Run server
python app.py

# Open browser to http://localhost:5000
```

### CLI:
```bash
# Natural language query
python -m flight_tracker.main --query "Find flights from SYD to BLR on June 1 under 500"

# Structured arguments
python -m flight_tracker.main --origin SYD --destination BLR --date 2026-06-01 --target 500

# Use real data
python -m flight_tracker.main --query "..." --provider amadeus
```

### Testing:
```bash
# Run test suites
python test_return_pricing.py
python test_price_filtering.py

# Debug API key
python debug_auth.py
```

---

## Conclusion

This Flights Finder application demonstrates effective integration of:
- **AI-powered natural language understanding** via Anthropic Claude
- **Modular architecture** with provider abstraction
- **Real-world API integration** (Amadeus)
- **Asynchronous web patterns** for responsive UX
- **Multi-currency support** with automatic conversion
- **Comprehensive testing** strategy

The codebase is well-structured for future enhancements while maintaining simplicity and clarity in its current implementation.
