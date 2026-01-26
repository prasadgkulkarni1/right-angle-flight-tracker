import sys
import os
import argparse
from flight_tracker.flight_data import FlightTool
from flight_tracker.agent import PriceTrackerAgent
from flight_tracker.provider_factory import ProviderFactory
from flight_tracker.config import config

def main():
    """Main entry point for the Flight Tracker application.
    
    Parses command-line arguments, sets up the FlightTool and PriceTrackerAgent,
    and starts the tracking process.
    """
    parser = argparse.ArgumentParser(description="Track flight prices.")

    # Add list-providers option
    parser.add_argument("--list-providers", action="store_true", help="List all available providers and exit")

    # Create mutually exclusive group for structured vs natural language input
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("--query", type=str, help="Natural language query (e.g., 'Find flights from SYD to BLR on June 1 under $500')")
    input_group.add_argument("--origin", type=str, help="Origin airport code (e.g., SFO)")

    parser.add_argument("--destination", type=str, help="Destination airport code (e.g., JFK)")
    parser.add_argument("--date", type=str, help="Flight date (YYYY-MM-DD)")
    parser.add_argument("--target", type=float, help="Target price to alert on")

    # Get available providers dynamically
    available_providers = list(config.get_available_providers().keys())
    parser.add_argument("--provider", type=str, default=None,
                        choices=available_providers if available_providers else ["mock"],
                        help=f"Data provider (default: auto-detect). Available: {', '.join(available_providers) if available_providers else 'mock'}")

    args = parser.parse_args()

    # Handle list-providers command
    if args.list_providers:
        print("\n" + "="*60)
        print("AVAILABLE FLIGHT DATA PROVIDERS")
        print("="*60 + "\n")

        all_providers = config.get_all_provider_status()
        for provider in all_providers:
            status_symbol = "✓" if provider['configured'] else "✗"
            status_text = "Ready" if provider['configured'] else "Not configured"

            print(f"{status_symbol} {provider['name']} (ID: {provider['provider_id']})")
            print(f"   Status: {status_text}")
            if provider['description']:
                print(f"   Description: {provider['description']}")
            if not provider['configured'] and provider['missing_vars']:
                print(f"   Missing: {', '.join(provider['missing_vars'])}")
            print()

        print("="*60)
        print(f"\nUse --provider <id> to select a provider")
        print(f"Example: --provider amadeus\n")
        sys.exit(0)

    # Validate that input is required for actual search
    if not args.query and not args.origin:
        parser.error("one of the arguments --query --origin is required")

    # Parse natural language query if provided
    if args.query:
        print(f"Parsing query: '{args.query}'")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY environment variable must be set for query parsing.")
            sys.exit(1)
        
        try:
            params = PriceTrackerAgent.parse_query(args.query, api_key)
            args.origin = params["origin"]
            args.destination = params["destination"]
            args.date = params["date"]
            args.return_date = params.get("return_date")  # Optional
            args.target = float(params["target_price"])
            args.target_currency = params.get("target_currency", "USD")  # Optional, default USD
            args.preferred_airlines = params.get("preferred_airlines")  # Optional
            args.max_duration = params.get("max_duration")  # Optional
            
            if args.return_date:
                print(f"Extracted: {args.origin} → {args.destination}, {args.date} to {args.return_date}, target: {args.target_currency} {args.target}")
            else:
                print(f"Extracted: {args.origin} → {args.destination} on {args.date}, target: {args.target_currency} {args.target}")
                
            if args.preferred_airlines:
                print(f"Preferred airlines: {', '.join(args.preferred_airlines)}")
            if args.max_duration:
                print(f"Max duration: {args.max_duration} hours")
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    else:
        # Validate structured arguments
        if not all([args.origin, args.destination, args.date, args.target]):
            print("ERROR: When not using --query, you must provide --origin, --destination, --date, and --target")
            sys.exit(1)
    
    # Initialize provider using factory
    target_currency = getattr(args, 'target_currency', 'USD')

    try:
        if args.provider:
            # Use specified provider
            print(f"Using provider: {args.provider}")
            data_provider = ProviderFactory.create_provider(args.provider, target_currency)
        else:
            # Auto-select best available provider
            print("Auto-selecting provider...")
            data_provider = ProviderFactory.get_default_provider(target_currency)

        # Show which provider was selected
        provider_name = data_provider.__class__.__name__
        print(f"✓ Provider initialized: {provider_name}")

    except (ValueError, RuntimeError) as e:
        print(f"ERROR: {e}")
        print("\nRun with --list-providers to see available providers")
        sys.exit(1)
    
    # Create the tool wrapper
    tool = FlightTool(provider=data_provider)
    
    # Initialize the LLM Agent
    try:
        agent = PriceTrackerAgent(tool=tool, check_interval_seconds=2)
    except ValueError as e:
        print(f"Error initializing agent: {e}")
        print("Please set the ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)
    
    # Define notification callback
    def notify(message):
        print(f"\n{'='*50}")
        print(f"NOTIFICATION SENT: {message}")
        print(f"{'='*50}\n")
        
    try:
        agent.track_price(
            origin=args.origin,
            destination=args.destination,
            date=args.date,
            target_price=args.target,
            notification_callback=notify,
            return_date=getattr(args, 'return_date', None),
            target_currency=getattr(args, 'target_currency', 'USD'),
            preferred_airlines=getattr(args, 'preferred_airlines', None),
            max_duration=getattr(args, 'max_duration', None)
        )
    except KeyboardInterrupt:
        print("\nStopping agent...")
        agent.stop()

if __name__ == "__main__":
    main()
