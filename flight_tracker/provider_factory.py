"""
Provider Factory for creating flight data provider instances.

This module provides a factory pattern implementation for creating
flight data provider instances based on configuration.
"""

import os
from typing import Optional
from flight_tracker.flight_data import FlightProvider, MockFlightProvider, AmadeusFlightProvider
from flight_tracker.config import config, ProviderConfig


class ProviderFactory:
    """Factory for creating flight data provider instances."""

    @staticmethod
    def create_provider(provider_id: str, target_currency: str = None) -> Optional[FlightProvider]:
        """
        Create a flight data provider instance based on provider ID.

        Args:
            provider_id (str): The provider identifier (e.g., 'mock', 'amadeus')
            target_currency (str, optional): Target currency for price conversion

        Returns:
            Optional[FlightProvider]: Provider instance or None if creation fails

        Raises:
            ValueError: If provider_id is not recognized
            RuntimeError: If provider is not properly configured
        """
        provider_config = config.get_provider_config(provider_id)

        if not provider_config:
            raise ValueError(f"Unknown provider: {provider_id}")

        if not provider_config.enabled:
            raise RuntimeError(f"Provider '{provider_id}' is not enabled")

        if not provider_config.is_configured():
            missing_vars = provider_config.get_missing_vars()
            raise RuntimeError(
                f"Provider '{provider_id}' is not properly configured. "
                f"Missing environment variables: {', '.join(missing_vars)}"
            )

        # Create provider instance based on ID
        if provider_id == "mock":
            default_currency = target_currency or provider_config.config_params.get("default_currency", "USD")
            return MockFlightProvider(default_currency=default_currency)

        elif provider_id == "amadeus":
            api_key = os.environ.get("AMADEUS_API_KEY")
            api_secret = os.environ.get("AMADEUS_API_SECRET")
            return AmadeusFlightProvider(
                api_key=api_key,
                api_secret=api_secret,
                target_currency=target_currency
            )

        # Add more providers here as they are implemented
        # elif provider_id == "skyscanner":
        #     api_key = os.environ.get("SKYSCANNER_API_KEY")
        #     return SkyscannerFlightProvider(api_key=api_key, target_currency=target_currency)

        else:
            raise ValueError(f"Provider '{provider_id}' is recognized but not implemented")

    @staticmethod
    def get_default_provider(target_currency: str = None) -> FlightProvider:
        """
        Get the default provider (first available configured provider).

        Falls back to mock provider if no other providers are configured.

        Args:
            target_currency (str, optional): Target currency for price conversion

        Returns:
            FlightProvider: A configured provider instance
        """
        available_providers = config.get_available_providers()

        # Try to use first non-mock provider if available
        for provider_id in available_providers.keys():
            if provider_id != "mock":
                try:
                    return ProviderFactory.create_provider(provider_id, target_currency)
                except Exception as e:
                    print(f"Failed to create provider '{provider_id}': {e}")
                    continue

        # Fall back to mock provider
        return ProviderFactory.create_provider("mock", target_currency)

    @staticmethod
    def list_available_providers() -> dict:
        """
        List all available (enabled and configured) providers.

        Returns:
            dict: Dictionary of provider_id -> status information
        """
        return {
            provider_id: config.get_provider_status(provider_id)
            for provider_id, provider_config in config.get_available_providers().items()
        }

    @staticmethod
    def validate_provider(provider_id: str) -> dict:
        """
        Validate a provider's configuration without creating an instance.

        Args:
            provider_id (str): The provider identifier

        Returns:
            dict: Validation result with 'valid' boolean and 'message' string
        """
        provider_config = config.get_provider_config(provider_id)

        if not provider_config:
            return {
                "valid": False,
                "message": f"Provider '{provider_id}' not found"
            }

        if not provider_config.enabled:
            return {
                "valid": False,
                "message": f"Provider '{provider_id}' is disabled"
            }

        if not provider_config.is_configured():
            missing_vars = provider_config.get_missing_vars()
            return {
                "valid": False,
                "message": f"Missing environment variables: {', '.join(missing_vars)}"
            }

        return {
            "valid": True,
            "message": f"Provider '{provider_id}' is properly configured"
        }
