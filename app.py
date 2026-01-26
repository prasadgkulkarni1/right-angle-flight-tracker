from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import threading
from flight_tracker.flight_data import FlightTool
from flight_tracker.agent import PriceTrackerAgent
from flight_tracker.provider_factory import ProviderFactory
from flight_tracker.config import config

app = Flask(__name__, static_folder='static')
CORS(app)

# Store search results
search_results = {}
search_lock = threading.Lock()

@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Explicitly serve static files."""
    return send_from_directory('static', filename)

@app.route('/api/providers', methods=['GET'])
def get_providers():
    """Get list of available flight data providers."""
    try:
        all_providers = config.get_all_provider_status()
        return jsonify({
            'providers': all_providers
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search_flights():
    """Handle flight search requests."""
    data = request.json
    query = data.get('query', '')
    provider_type = data.get('provider', 'mock')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    # Generate search ID
    search_id = str(hash(query + str(threading.current_thread().ident)))
    
    # Initialize results
    with search_lock:
        search_results[search_id] = {
            'status': 'parsing',
            'messages': [],
            'result': None
        }
    
    def run_search():
        """Run the search in a background thread."""
        try:
            # Parse query
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                with search_lock:
                    search_results[search_id]['status'] = 'error'
                    search_results[search_id]['messages'].append({
                        'type': 'error',
                        'content': 'ANTHROPIC_API_KEY not set'
                    })
                return
            
            with search_lock:
                search_results[search_id]['messages'].append({
                    'type': 'info',
                    'content': f'Parsing query: "{query}"'
                })
            
            params = PriceTrackerAgent.parse_query(query, api_key)
            
            with search_lock:
                search_results[search_id]['messages'].append({
                    'type': 'success',
                    'content': f"Found: {params['origin']} → {params['destination']} on {params['date']}"
                })
            
            # Initialize provider using factory
            target_currency = params.get('target_currency', 'USD')

            try:
                provider = ProviderFactory.create_provider(provider_type, target_currency)
            except (ValueError, RuntimeError) as e:
                with search_lock:
                    search_results[search_id]['status'] = 'error'
                    search_results[search_id]['messages'].append({
                        'type': 'error',
                        'content': str(e)
                    })
                return
            
            tool = FlightTool(provider=provider)
            agent = PriceTrackerAgent(tool=tool, check_interval_seconds=1)
            
            with search_lock:
                search_results[search_id]['status'] = 'searching'
                search_results[search_id]['messages'].append({
                    'type': 'info',
                    'content': 'Searching for flights...'
                })
            
            # Track price (one iteration only for web)
            deal_found = [False]
            deal_message = ['']
            
            def notification_callback(message):
                deal_found[0] = True
                deal_message[0] = message
            
            # We'll do a single check instead of continuous tracking
            try:
                
                # Get flight details directly
                return_date = params.get('return_date')
                target_price = params.get('target_price')
                target_currency = params.get('target_currency', 'USD')
                
                flight_details = tool.get_price(
                    params['origin'],
                    params['destination'],
                    params['date'],
                    return_date
                )
                
                if flight_details and flight_details.get('status') == 'AVAILABLE':
                    # Check if price is within target
                    flight_price = flight_details.get('price', 0)
                    flight_currency = flight_details.get('currency', 'USD')
                    
                    # Price should already be in target currency if conversion was done
                    # But double-check the currency matches
                    if flight_currency == target_currency:
                        price_under_target = flight_price <= target_price
                    else:
                        # If currencies don't match, convert for comparison
                        try:
                            from forex_python.converter import CurrencyRates
                            c = CurrencyRates()
                            converted_price = c.convert(flight_currency, target_currency, flight_price)
                            price_under_target = converted_price <= target_price
                        except:
                            # If conversion fails, just compare raw numbers
                            price_under_target = flight_price <= target_price
                    
                    if price_under_target:
                        with search_lock:
                            search_results[search_id]['status'] = 'complete'
                            search_results[search_id]['result'] = flight_details
                            search_results[search_id]['messages'].append({
                                'type': 'success',
                                'content': f'Flight found for {flight_currency} {flight_price}!'
                            })
                    else:
                        with search_lock:
                            search_results[search_id]['status'] = 'complete'
                            search_results[search_id]['messages'].append({
                                'type': 'warning',
                                'content': f'No flights found under {target_currency} {target_price}. Lowest price found: {flight_currency} {flight_price}'
                            })
                else:
                    with search_lock:
                        search_results[search_id]['status'] = 'complete'
                        search_results[search_id]['messages'].append({
                            'type': 'warning',
                            'content': 'No flights available'
                        })
            except Exception as e:
                with search_lock:
                    search_results[search_id]['status'] = 'error'
                    search_results[search_id]['messages'].append({
                        'type': 'error',
                        'content': str(e)
                    })
        except Exception as e:
            with search_lock:
                search_results[search_id]['status'] = 'error'
                search_results[search_id]['messages'].append({
                    'type': 'error',
                    'content': str(e)
                })
    
    # Start search in background
    thread = threading.Thread(target=run_search)
    thread.daemon = True
    thread.start()
    
    return jsonify({'search_id': search_id})

@app.route('/api/status/<search_id>', methods=['GET'])
def get_status(search_id):
    """Get the status of a search."""
    with search_lock:
        if search_id not in search_results:
            return jsonify({'error': 'Search not found'}), 404
        return jsonify(search_results[search_id])

if __name__ == '__main__':
    # Support configurable port via environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))

    print("🚀 Flight Tracker Web UI starting...")
    print(f"📍 Open http://localhost:{port} in your browser")
    print(f"📍 Or access via http://127.0.0.1:{port}")

    if port != 5000:
        print(f"ℹ️  Using port {port} (default is 5000)")

    # Listen on all interfaces to allow IP address access
    try:
        app.run(debug=True, host='0.0.0.0', port=port, threaded=True)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ ERROR: Port {port} is already in use!")
            print("\n💡 Solutions:")
            print(f"   1. Use a different port: PORT=5001 python app.py")
            print(f"   2. Kill process using port {port}: ./kill_port_5000.sh")
            print(f"   3. Disable AirPlay in System Settings (macOS)")
            print(f"\nSee PORT_CONFLICT_FIX.md for detailed instructions.")
        else:
            raise
