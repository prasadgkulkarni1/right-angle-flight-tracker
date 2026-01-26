import os
import time
import anthropic
from typing import Callable

from .flight_data import FlightTool

class PriceTrackerAgent:
    """Agent that tracks flight prices using an LLM and tools.
    
    This agent orchestrates the interaction between the user's request (implied by args)
    and the Anthropic Claude model. It sets up the model with a custom `FlightTool` and 
    prompts it to check for flight prices against a target.
    """
    
    @staticmethod
    def parse_query(query: str, api_key: str) -> dict:
        """Parse a natural language flight query into structured parameters.
        
        Args:
            query (str): Natural language query (e.g., "Find flights from SFO to JFK on 2023-12-25 under $500")
            api_key (str): Anthropic API key
            
        Returns:
            dict: Extracted parameters with keys: origin, destination, date, target_price, return_date (optional)
            
        Raises:
            ValueError: If required parameters cannot be extracted
        """
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""Extract flight search parameters from this query: "{query}"

Return a JSON object with these exact keys:
- origin: 3-letter IATA airport code (e.g., SYD, SFO)
- destination: 3-letter IATA airport code (e.g., BLR, JFK)
- date: Departure date in YYYY-MM-DD format
- return_date: Return date in YYYY-MM-DD format (null for one-way)
- target_price: Maximum price as a number (no currency symbol)
- target_currency: 3-letter currency code (e.g., USD, AUD, EUR). Use "USD" as default if not specified.
- preferred_airlines: Array of airline codes or null (e.g., ["QF", "SQ"] for Qantas and Singapore Airlines)
- max_duration: Maximum flight duration in hours or null (extract from phrases like "under 15 hours", "max 10 hours")

For date ranges like "first week of June", use the START of the range for 'date'.
For return flights mentioned as ranges, use the END of the range for 'return_date'.

Examples:
- "Find flights from Sydney to Bangalore on June 1st 2026 under 500" → {{"origin": "SYD", "destination": "BLR", "date": "2026-06-01", "return_date": null, "target_price": 500, "target_currency": "USD", "preferred_airlines": null, "max_duration": null}}
- "Return flights SYD to BLR from 01/06/2026 to 10/06/2026 under AUD 900 on Qantas or Emirates" → {{"origin": "SYD", "destination": "BLR", "date": "2026-06-01", "return_date": "2026-06-10", "target_price": 900, "target_currency": "AUD", "preferred_airlines": ["QF", "EK"], "max_duration": null}}
- "Find return flights from Sydney to Bangalore in June under EUR 800, max 15 hours flight time" → {{"origin": "SYD", "destination": "BLR", "date": "2026-06-01", "return_date": "2026-06-30", "target_price": 800, "target_currency": "EUR", "preferred_airlines": null, "max_duration": 15}}

Return ONLY the JSON object, no other text."""

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text.strip()
        
        # Parse JSON from response
        import json
        try:
            params = json.loads(result_text)
        except json.JSONDecodeError:
            raise ValueError(f"Could not parse query. Claude returned: {result_text}")
        
        # Validate required fields
        required = ["origin", "destination", "date", "target_price"]
        missing = [k for k in required if not params.get(k)]
        if missing:
            raise ValueError(f"Could not extract these parameters from query: {', '.join(missing)}")
        
        return params
    
    def __init__(self, tool: FlightTool, model_name: str = "claude-opus-4-5", check_interval_seconds: int = 5):
        """Initialize the PriceTrackerAgent.

        Args:
            tool (FlightTool): The flight data tool wrapper that the LLM will use.
            model_name (str): The name of the Claude model to use (default: "claude-opus-4-5").
            check_interval_seconds (int): The interval in seconds to wait between price checks (default: 5).
        
        Raises:
            ValueError: If the ANTHROPIC_API_KEY environment variable is not set.
        """
        self.tool = tool
        self.check_interval_seconds = check_interval_seconds
        self.is_running = False
        self.model_name = model_name
        
        # Configure Claude
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Define the tool for Claude
        self.tools = [
            {
                "name": "get_price",
                "description": "Get the current flight price for a specific route and date.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "origin": {
                            "type": "string",
                            "description": "3-letter IATA origin airport code (e.g., SFO)"
                        },
                        "destination": {
                            "type": "string",
                            "description": "3-letter IATA destination airport code (e.g., JFK)"
                        },
                        "date": {
                            "type": "string",
                            "description": "Flight date in YYYY-MM-DD format"
                        }
                    },
                    "required": ["origin", "destination", "date"]
                }
            }
        ]
        
        # Initialize conversation history
        self.messages = []

    def track_price(self, origin: str, destination: str, date: str, target_price: float, 
                   notification_callback: Callable[[str], None], return_date: str = None, 
                   target_currency: str = "USD", preferred_airlines: list = None, max_duration: float = None):
        """Starts the price tracking loop.

        This method continuously interacts with the LLM to check flight prices.
        If a deal is found (price <= target), it triggers the callback and stops.

        Args:
            origin (str): Origin airport code (e.g. 'SFO').
            destination (str): Destination airport code (e.g. 'JFK').
            date (str): Departure date (YYYY-MM-DD).
            target_price (float): The target price to beat.
            notification_callback (Callable[[str], None]): A function to call when a deal is found. 
                                                          It receives the notification message string.
            return_date (str, optional): Return date for round-trip flights (YYYY-MM-DD).
            target_currency (str, optional): Currency code for target price (default: USD).
            preferred_airlines (list, optional): List of preferred airline codes.
            max_duration (float, optional): Maximum acceptable flight duration in hours.
        """
        self.is_running = True
        trip_type = "round-trip" if return_date else "one-way"
        print(f"Starting tracking {trip_type} flight from {origin} to {destination} on {date}" + 
              (f" (returning {return_date})" if return_date else "") + f". Target: {target_currency} {target_price}")
        
        if preferred_airlines:
            print(f"Preferred airlines: {', '.join(preferred_airlines)}")
        if max_duration:
            print(f"Max duration: {max_duration} hours")
        
        while self.is_running:
            # Create prompt for Claude with currency awareness and preferences
            prompt = f"Check the flight price for {origin} to {destination} on {date}. "
            prompt += f"The target price to beat is {target_currency} {target_price}. "
            
            if preferred_airlines:
                prompt += f"Preferred airlines: {', '.join(preferred_airlines)}. "
            if max_duration:
                prompt += f"Maximum acceptable flight duration: {max_duration} hours. "
            
            prompt += "Compare the flight price to the target, considering currency conversion if needed. "
            
            if preferred_airlines or max_duration:
                prompt += "Consider the user's preferences when evaluating the deal. "
                
            prompt += f"If the price (when converted to {target_currency}) is lower than or equal to the target"
            if preferred_airlines or max_duration:
                prompt += " AND meets the preferences"
            prompt += ", tell me 'DEAL FOUND' with the price and its currency. "
            prompt += "If it's higher or doesn't meet preferences, just say 'Price too high' or 'Does not meet preferences'."
            
            try:
                # Add user message to history
                self.messages.append({
                    "role": "user",
                    "content": prompt
                })
                
                # Send message to Claude
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=1024,
                    tools=self.tools,
                    messages=self.messages
                )
                
                # Process response
                while response.stop_reason == "tool_use":
                    # Extract tool use
                    tool_use = None
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_use = block
                            break
                    
                    if tool_use and tool_use.name == "get_price":
                        print("LLM requested flight price check...")
                        
                        # Execute the tool
                        tool_input = tool_use.input
                        result = self.tool.get_price(
                            tool_input["origin"],
                            tool_input["destination"],
                            tool_input["date"],
                            return_date
                        )
                        
                        # Add assistant response to history
                        self.messages.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        
                        # Add tool result to history
                        self.messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use.id,
                                    "content": str(result)
                                }
                            ]
                        })
                        
                        # Continue conversation
                        response = self.client.messages.create(
                            model=self.model_name,
                            max_tokens=1024,
                            tools=self.tools,
                            messages=self.messages
                        )
                
                # Extract final text response
                text_response = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text_response += block.text
                
                print(f"LLM Analysis: {text_response}")
                
                # Add final assistant response to history
                self.messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Check for deal and display enhanced details
                if "DEAL FOUND" in text_response:
                    # Format enhanced notification with flight details
                    if isinstance(result, dict) and result.get("status") == "AVAILABLE":
                        enhanced_message = f"""{text_response}

✈️  Flight Details:
   • Price: {result['currency']} {result['price']}
   • Airline: {result['airline']} ({result['flight_number']})
   • Type: {result['trip_type']}
   • Departure: {result['departure_date']}"""
                        if result.get('return_date'):
                            enhanced_message += f"\n   • Return: {result['return_date']}"
                        enhanced_message += f"\n   • Book now: {result['booking_url']}"
                        
                        notification_callback(enhanced_message)
                    else:
                        notification_callback(text_response)
                    
                    self.stop()
                    
            except Exception as e:
                print(f"Error interacting with LLM: {e}")

            if self.is_running:
                time.sleep(self.check_interval_seconds)

    def stop(self):
        """Stops the tracking loop.
        
        Sets `is_running` to False, which will terminate the loop in `track_price`
        at the next iteration.
        """
        self.is_running = False
