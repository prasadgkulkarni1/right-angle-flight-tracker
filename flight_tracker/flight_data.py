from abc import ABC, abstractmethod
import random
import time
from typing import Dict, Optional

class FlightProvider(ABC):
    """Abstract base class for flight data providers.

    This class defines the interface that all flight data providers must implement.
    It ensures consistency across different types of providers (e.g., Mock, API-based).
    """
    
    @abstractmethod
    def get_price(self, origin: str, destination: str, date: str, return_date: str = None) -> Optional[Dict]:
        """Fetches flight information for a given route and date(s).

        Args:
            origin (str): The IATA airport code for the origin (e.g., 'SFO').
            destination (str): The IATA airport code for the destination (e.g., 'JFK').
            date (str): The departure date in 'YYYY-MM-DD' format.
            return_date (str, optional): The return date for round-trip flights.

        Returns:
            Optional[Dict]: Flight details including price, currency, etc., or None if unavailable.
        """
        pass

    @abstractmethod
    def get_prices(self, origin: str, destination: str, date: str, return_date: str = None, max_results: int = 5) -> list:
        """Fetches multiple flight options for a given route and date(s).

        Args:
            origin (str): The IATA airport code for the origin (e.g., 'SFO').
            destination (str): The IATA airport code for the destination (e.g., 'JFK').
            date (str): The departure date in 'YYYY-MM-DD' format.
            return_date (str, optional): The return date for round-trip flights.
            max_results (int): Maximum number of flight options to return (default: 5).

        Returns:
            list: List of flight details dictionaries, sorted by price (lowest first).
        """
        pass


class MockFlightProvider(FlightProvider):
    """Mock implementation of a flight provider for demonstration.

    This provider generates random flight prices to simulate a real data source.
    It includes artificial latency to mimic network requests.
    """
    
    def __init__(self, default_currency: str = "USD"):
        """Initialize the mock provider with a default currency.
        
        Args:
            default_currency (str): Currency code to use for mock prices (default: USD).
        """
        self.default_currency = default_currency
    
    def get_price(self, origin: str, destination: str, date: str, return_date: str = None) -> Optional[Dict]:
        """Returns simulated flight data.
        
        Args:
            origin (str): The IATA airport code for the origin.
            destination (str): The IATA airport code for the destination.
            date (str): The flight date.
            return_date (str, optional): The return date for round-trip.
        
        Returns:
            Optional[Dict]: Simulated flight details including price and currency.
        """
        # Simulate network latency
        time.sleep(0.5)
        
        # Generate a random price between $100 and $1000
        base_price = random.uniform(100, 1000)
        
        # Adjust for round-trip
        if return_date:
            base_price *= 1.8
        
        return {
            "price": round(base_price, 2),
            "currency": self.default_currency,
            "airline": "MOCK",
            "flight_number": "MOCK123",
            "booking_url": "https://example.com/book",
            "trip_type": "round-trip" if return_date else "one-way",
            "departure_date": date,
            "return_date": return_date
        }

    def get_prices(self, origin: str, destination: str, date: str, return_date: str = None, max_results: int = 5) -> list:
        """Returns multiple simulated flight options with varying prices.

        Args:
            origin (str): The IATA airport code for the origin.
            destination (str): The IATA airport code for the destination.
            date (str): The flight date.
            return_date (str, optional): The return date for round-trip.
            max_results (int): Maximum number of flight options to generate (default: 5).

        Returns:
            list: List of simulated flight details, sorted by price (lowest first).
        """
        # Simulate network latency
        time.sleep(0.5)

        # Generate a base price
        base_price = random.uniform(100, 1000)

        # Adjust for round-trip
        if return_date:
            base_price *= 1.8

        # List of mock airlines for variety
        airlines = ['AA', 'DL', 'UA', 'EK', 'QF', 'BA', 'LH', 'AF', 'KL', 'NH']

        results = []

        for i in range(max_results):
            # Generate price variation (±30% from base price)
            variation = random.uniform(-0.30, 0.30)
            price = base_price * (1 + variation)

            # Select a random airline
            airline = random.choice(airlines)

            # Generate random flight number
            flight_num = random.randint(100, 999)

            # Generate random duration (hours and minutes)
            duration_hours = random.randint(2, 20)
            duration_mins = random.choice([0, 15, 30, 45])
            duration = f"{duration_hours}h {duration_mins}m" if duration_mins > 0 else f"{duration_hours}h"

            # Random number of stops
            stops = random.choice([0, 0, 0, 1, 1, 2])  # Bias towards direct flights

            results.append({
                "price": round(price, 2),
                "currency": self.default_currency,
                "airline": airline,
                "flight_number": f"{airline}{flight_num}",
                "booking_url": f"https://example.com/book/{airline}{flight_num}",
                "trip_type": "round-trip" if return_date else "one-way",
                "departure_date": date,
                "return_date": return_date,
                "duration": duration,
                "stops": stops
            })

        # Sort by price (lowest first)
        results.sort(key=lambda x: x['price'])

        return results

class AmadeusFlightProvider(FlightProvider):
    """Real flight data provider using Amadeus API.
    
    This provider fetches actual flight prices from the Amadeus Flight Offers Search API.
    Requires AMADEUS_API_KEY and AMADEUS_API_SECRET environment variables.
    """
    
    def __init__(self, api_key: str, api_secret: str, target_currency: str = None):
        """Initialize the Amadeus provider.
        
        Args:
            api_key (str): Amadeus API key.
            api_secret (str): Amadeus API secret.
            target_currency (str, optional): Target currency for price conversion.
        """
        from amadeus import Client
        self.client = Client(
            client_id=api_key,
            client_secret=api_secret
        )
        self.target_currency = target_currency
    
    def get_price(self, origin: str, destination: str, date: str, return_date: str = None) -> Optional[Dict]:
        """Fetches real flight information from Amadeus API.
        
        Args:
            origin (str): The IATA airport code for the origin.
            destination (str): The IATA airport code for the destination.
            date (str): The departure date in YYYY-MM-DD format.
            return_date (str, optional): The return date in YYYY-MM-DD format for round-trip.
        
        Returns:
            Optional[Dict]: Flight details including price, currency, airline, booking link, or None if unavailable.
        """
        try:
            # Search for flight offers
            search_params = {
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": date,
                "adults": 1
            }
            
            if return_date:
                search_params["returnDate"] = return_date
            
            response = self.client.shopping.flight_offers_search.get(**search_params)
            
            # Extract detailed information from the best offer
            if response.data:
                best_offer = min(response.data, key=lambda x: float(x['price']['total']))
                
                # Extract flight details
                original_price = float(best_offer['price']['total'])
                original_currency = best_offer['price']['currency']
                
                # Convert currency if target is different
                display_price = original_price
                display_currency = original_currency
                
                if self.target_currency and self.target_currency != original_currency:
                    try:
                        from forex_python.converter import CurrencyRates
                        c = CurrencyRates()
                        converted_price = c.convert(original_currency, self.target_currency, original_price)
                        display_price = converted_price
                        display_currency = self.target_currency
                    except Exception as conv_error:
                        print(f"Currency conversion error: {conv_error}, using original currency")
                
                # Get airline and flight numbers
                itineraries = best_offer['itineraries']
                outbound = itineraries[0]['segments']
                airline_code = outbound[0]['carrierCode']
                flight_number = f"{airline_code}{outbound[0]['number']}"
                
                # Generate booking URL (Google Flights as fallback)
                booking_url = f"https://www.google.com/flights?hl=en#flt={origin}.{destination}.{date}"
                if return_date:
                    booking_url += f"*{destination}.{origin}.{return_date}"
                
                result = {
                    "price": round(display_price, 2),
                    "currency": display_currency,
                    "airline": airline_code,
                    "flight_number": flight_number,
                    "booking_url": booking_url,
                    "trip_type": "round-trip" if return_date else "one-way",
                    "departure_date": date,
                    "return_date": return_date
                }
                
                # Add original price info if converted
                if display_currency != original_currency:
                    result["original_price"] = round(original_price, 2)
                    result["original_currency"] = original_currency
                
                return result
            
            return None
            
        except Exception as e:
            print(f"Amadeus API Error: {e}")
            return None

    def get_prices(self, origin: str, destination: str, date: str, return_date: str = None, max_results: int = 5) -> list:
        """Fetches multiple real flight options from Amadeus API.

        Args:
            origin (str): The IATA airport code for the origin.
            destination (str): The IATA airport code for the destination.
            date (str): The departure date in YYYY-MM-DD format.
            return_date (str, optional): The return date in YYYY-MM-DD format for round-trip.
            max_results (int): Maximum number of flight options to return (default: 5).

        Returns:
            list: List of flight details dictionaries, sorted by price (lowest first).
        """
        try:
            # Search for flight offers
            search_params = {
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": date,
                "adults": 1,
                "max": max_results  # Request up to max_results from API
            }

            if return_date:
                search_params["returnDate"] = return_date

            response = self.client.shopping.flight_offers_search.get(**search_params)

            results = []

            if response.data:
                # Sort offers by price
                sorted_offers = sorted(response.data, key=lambda x: float(x['price']['total']))

                # Process up to max_results offers
                for offer in sorted_offers[:max_results]:
                    # Extract price information
                    original_price = float(offer['price']['total'])
                    original_currency = offer['price']['currency']

                    # Convert currency if target is different
                    display_price = original_price
                    display_currency = original_currency

                    if self.target_currency and self.target_currency != original_currency:
                        try:
                            from forex_python.converter import CurrencyRates
                            c = CurrencyRates()
                            converted_price = c.convert(original_currency, self.target_currency, original_price)
                            display_price = converted_price
                            display_currency = self.target_currency
                        except Exception as conv_error:
                            print(f"Currency conversion error: {conv_error}, using original currency")

                    # Get airline and flight details
                    itineraries = offer['itineraries']
                    outbound = itineraries[0]['segments']
                    airline_code = outbound[0]['carrierCode']
                    flight_number = f"{airline_code}{outbound[0]['number']}"

                    # Calculate total duration
                    duration = itineraries[0]['duration']

                    # Count stops (segments - 1)
                    stops = len(outbound) - 1

                    # Generate booking URL (Google Flights as fallback)
                    booking_url = f"https://www.google.com/flights?hl=en#flt={origin}.{destination}.{date}"
                    if return_date:
                        booking_url += f"*{destination}.{origin}.{return_date}"

                    result = {
                        "price": round(display_price, 2),
                        "currency": display_currency,
                        "airline": airline_code,
                        "flight_number": flight_number,
                        "booking_url": booking_url,
                        "trip_type": "round-trip" if return_date else "one-way",
                        "departure_date": date,
                        "return_date": return_date,
                        "duration": duration,  # ISO 8601 format (e.g., "PT13H30M")
                        "stops": stops,
                        "raw_data": offer  # Store full offer for later use (booking)
                    }

                    # Add original price info if converted
                    if display_currency != original_currency:
                        result["original_price"] = round(original_price, 2)
                        result["original_currency"] = original_currency

                    results.append(result)

            return results

        except Exception as e:
            print(f"Amadeus API Error: {e}")
            return []


class FlightTool:
    """Tool that exposes flight data to the LLM.

    This class wraps a FlightProvider and adapts its output for consumption
    by the Gemini model, specifically formatting it as a JSON-like dictionary.
    """
    
    def __init__(self, provider: FlightProvider):
        """Initialize the FlightTool.

        Args:
            provider (FlightProvider): The underlying provider to fetch data from.
        """
        self.provider = provider

    def get_price(self, origin: str, destination: str, date: str, return_date: str = None):
        """Get the current flight information for a specific route and date(s).
        
        This method is designed to be called by the LLM via tool use.
        
        Args:
            origin (str): The three-letter IATA airport code for the origin (e.g., SFO, LHR).
            destination (str): The three-letter IATA airport code for the destination (e.g., JFK, NRT).
            date (str): The departure date in YYYY-MM-DD format.
            return_date (str, optional): The return date for round-trip flights.
        
        Returns:
            dict: Flight details including price, currency, airline, booking link, or error message.
        """
        flight_details = self.provider.get_price(origin, destination, date, return_date)
        if flight_details:
            return {
                **flight_details,
                "status": "AVAILABLE"
            }
        else:
            return {"status": "UNAVAILABLE", "error": "Could not fetch flight information"}

    def get_prices(self, origin: str, destination: str, date: str, return_date: str = None, max_results: int = 5):
        """Get multiple flight options for a specific route and date(s).

        This method is designed to be called by the web API to get multiple flight results.

        Args:
            origin (str): The three-letter IATA airport code for the origin (e.g., SFO, LHR).
            destination (str): The three-letter IATA airport code for the destination (e.g., JFK, NRT).
            date (str): The departure date in YYYY-MM-DD format.
            return_date (str, optional): The return date for round-trip flights.
            max_results (int): Maximum number of results to return (default: 5).

        Returns:
            list: List of flight details dictionaries, or empty list if unavailable.
        """
        flights = self.provider.get_prices(origin, destination, date, return_date, max_results)
        return flights if flights else []
