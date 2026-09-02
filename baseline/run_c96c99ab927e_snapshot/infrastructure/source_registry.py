"""Source Registry for Affirm Policy Swarm.

This module provides a registry for source connectors, acting as a factory
to instantiate the appropriate connector based on source name.
"""

from infrastructure.connectors.federal_register_connector import FederalRegisterConnector
from infrastructure.connectors.regulations_gov_connector import RegulationsGovConnector
from infrastructure.connectors.congress_gov_connector import CongressGovConnector
from infrastructure.connectors.legiscan_connector import LegiScanConnector


class SourceRegistry:
    """Registry for source connectors with support for structured and unstructured sources."""

    # Define allowed source types for validation
    _ALLOWED_SOURCE_TYPES = {
        "legislation", "regulator",
        "research", "news", "policymaker_article", "press_release",
        "social_post", "hearing", "court_or_docket", "trade_association", "consumer_advocacy"
    }

    def __init__(self):
        """Initialize the registry with the four active connectors and their metadata."""
        self._catalog = {
            "federal_register": {
                "connector_class": FederalRegisterConnector,
                "source_type": "regulator",
                "access_method": "api"
            },
            "regulations_gov": {
                "connector_class": RegulationsGovConnector,
                "source_type": "regulator",
                "access_method": "api"
            },
            "congress_gov": {
                "connector_class": CongressGovConnector,
                "source_type": "legislation",
                "access_method": "api"
            },
            "legiscan": {
                "connector_class": LegiScanConnector,
                "source_type": "legislation",
                "access_method": "api"
            },
            "brookings_policy_research": {
                "connector_class": FederalRegisterConnector,
                "source_type": "research",
                "access_method": "scraper"
            },
            "cfpb_research_reports": {
                "connector_class": FederalRegisterConnector,
                "source_type": "research",
                "access_method": "scraper"
            },
            "senate_banking_cmte_press": {
                "connector_class": FederalRegisterConnector,
                "source_type": "policymaker_article",
                "access_method": "scraper"
            },
            "cfpb_press_releases": {
                "connector_class": FederalRegisterConnector,
                "source_type": "press_release",
                "access_method": "scraper"
            },
            "house_financial_services_hearings": {
                "connector_class": FederalRegisterConnector,
                "source_type": "hearing",
                "access_method": "scraper"
            },
            "fintech_policy_news": {
                "connector_class": FederalRegisterConnector,
                "source_type": "news",
                "access_method": "scraper"
            },
            "x_official_policy_accounts": {
                "connector_class": FederalRegisterConnector,
                "source_type": "social_post",
                "access_method": "scraper"
            }
        }

    def get_connector(self, source_name: str, config: dict):
        """Get a connector instance by name.

        Args:
            source_name: The key for the connector (e.g., "federal_register").
            config: Configuration dictionary to pass to the connector's constructor.

        Returns:
            An instance of the requested connector.

        Raises:
            ValueError: If the source_name is not in the registry.
        """
        if source_name not in self._catalog:
            raise ValueError(f"Source '{source_name}' is not registered. Available sources: {list(self._catalog.keys())}")
        connector_class = self._catalog[source_name]["connector_class"]
        return connector_class(config)

    def get_source_type(self, source_name: str) -> str:
        """Get the source type for a registered source.

        Args:
            source_name: The key for the connector (e.g., "federal_register").

        Returns:
            String representing the source type.

        Raises:
            ValueError: If the source_name is not in the registry.
        """
        if source_name not in self._catalog:
            raise ValueError(f"Source '{source_name}' is not registered. Available sources: {list(self._catalog.keys())}")
        return self._catalog[source_name]["source_type"]

    def get_access_method(self, source_name: str) -> str:
        """Get the access method for a registered source.

        Args:
            source_name: The key for the connector (e.g., "federal_register").

        Returns:
            String representing the access method (e.g., "api", "rss", "scraper").

        Raises:
            ValueError: If the source_name is not in the registry.
        """
        if source_name not in self._catalog:
            raise ValueError(f"Source '{source_name}' is not registered. Available sources: {list(self._catalog.keys())}")
        return self._catalog[source_name]["access_method"]

    def is_valid_source_type(self, source_type: str) -> bool:
        """Check if a source type is valid (in the allowed source types).

        Args:
            source_type: The source type to validate.

        Returns:
            True if the source type is valid, False otherwise.
        """
        return source_type in self._ALLOWED_SOURCE_TYPES

    def get_all_active_sources(self) -> list:
        """Get a list of all registered source names.

        Returns:
            List of strings representing the registered source keys.
        """
        return list(self._catalog.keys())