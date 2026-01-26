"""
Configuration management for flight data providers.

This module provides a centralized configuration system for managing
multiple flight data providers and their API credentials.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ProviderConfig:
    """Configuration for a single flight data provider."""

    provider_id: str
    name: str
    enabled: bool
    config_params: Dict[str, Any] = field(default_factory=dict)
    required_env_vars: List[str] = field(default_factory=list)

    def is_configured(self) -> bool:
        """Check if all required environment variables are set."""
        if not self.required_env_vars:
            return True  # No requirements means always configured

        return all(
            os.environ.get(env_var)
            for env_var in self.required_env_vars
        )

    def get_missing_vars(self) -> List[str]:
        """Get list of missing required environment variables."""
        return [
            env_var
            for env_var in self.required_env_vars
            if not os.environ.get(env_var)
        ]


class FlightProviderConfig:
    """Centralized configuration for all flight data providers."""

    def __init__(self):
        """Initialize provider configurations."""
        self._providers: Dict[str, ProviderConfig] = {}
        self._load_default_providers()

    def _load_default_providers(self):
        """Load default provider configurations."""

        # Mock Provider - Always available, no API keys needed
        self.register_provider(ProviderConfig(
            provider_id="mock",
            name="Mock Provider (Test Data)",
            enabled=True,
            config_params={
                "default_currency": "USD",
                "description": "Generates random test data for development"
            },
            required_env_vars=[]
        ))

        # Amadeus Provider - Requires API credentials
        self.register_provider(ProviderConfig(
            provider_id="amadeus",
            name="Amadeus (Real Flight Data)",
            enabled=True,
            config_params={
                "api_base_url": "https://api.amadeus.com",
                "description": "Real-time flight data from Amadeus API"
            },
            required_env_vars=["AMADEUS_API_KEY", "AMADEUS_API_SECRET"]
        ))

        # Add more providers here in the future
        # Example:
        # self.register_provider(ProviderConfig(
        #     provider_id="skyscanner",
        #     name="Skyscanner",
        #     enabled=False,  # Not yet implemented
        #     config_params={
        #         "api_base_url": "https://api.skyscanner.net"
        #     },
        #     required_env_vars=["SKYSCANNER_API_KEY"]
        # ))

    def register_provider(self, config: ProviderConfig):
        """Register a new provider configuration."""
        self._providers[config.provider_id] = config

    def get_provider_config(self, provider_id: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider."""
        return self._providers.get(provider_id)

    def get_all_providers(self) -> Dict[str, ProviderConfig]:
        """Get all registered provider configurations."""
        return self._providers.copy()

    def get_enabled_providers(self) -> Dict[str, ProviderConfig]:
        """Get all enabled provider configurations."""
        return {
            provider_id: config
            for provider_id, config in self._providers.items()
            if config.enabled
        }

    def get_available_providers(self) -> Dict[str, ProviderConfig]:
        """Get providers that are enabled AND properly configured."""
        return {
            provider_id: config
            for provider_id, config in self._providers.items()
            if config.enabled and config.is_configured()
        }

    def get_provider_status(self, provider_id: str) -> Dict[str, Any]:
        """Get detailed status for a provider."""
        config = self.get_provider_config(provider_id)
        if not config:
            return {"error": "Provider not found"}

        return {
            "provider_id": config.provider_id,
            "name": config.name,
            "enabled": config.enabled,
            "configured": config.is_configured(),
            "missing_vars": config.get_missing_vars() if not config.is_configured() else [],
            "description": config.config_params.get("description", "")
        }

    def get_all_provider_status(self) -> List[Dict[str, Any]]:
        """Get status for all providers."""
        return [
            self.get_provider_status(provider_id)
            for provider_id in self._providers.keys()
        ]


# Global configuration instance
config = FlightProviderConfig()
