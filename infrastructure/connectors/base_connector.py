import abc
import time
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod

# Import NormalizedPolicyEvent from the normalization module
from .normalization import NormalizedPolicyEvent


class BaseSourceConnector(ABC):
    """Abstract base class for all policy source connectors."""

    def __init__(self, source_name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize the connector with source name and configuration.

        Args:
            source_name: Identifier for the data source (e.g., 'congress_gov', 'legiscan')
            config: Configuration dictionary for the connector
        """
        self.source_name = source_name
        self.config = config or {}
        self._is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the data source.

        Returns:
            True if connection successful, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the data source connection.

        Returns:
            Dictionary containing health status information
        """
        raise NotImplementedError

    @abstractmethod
    def fetch(self) -> Any:
        """Fetch raw data from the data source.

        Returns:
            Raw data retrieved from the source (format depends on implementation)
        """
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_data: Any) -> Union[NormalizedPolicyEvent, List[NormalizedPolicyEvent]]:
        """Normalize raw data into a common format.

        Args:
            raw_data: Data returned from fetch() method

        Returns:
            Normalized data as a NormalizedPolicyEvent or list of them
        """
        raise NotImplementedError

    @abstractmethod
    def deduplicate(self, records: List[NormalizedPolicyEvent]) -> List[NormalizedPolicyEvent]:
        """Remove duplicate records based on a unique identifier.

        Args:
            records: List of normalized policy events

        Returns:
            List of deduplicated normalized policy events
        """
        raise NotImplementedError

    @abstractmethod
    def checkpoint(self, checkpoint_data: Dict[str, Any]) -> None:
        """Save checkpoint data for incremental synchronization.

        Args:
            checkpoint_data: Data to save for resuming synchronization later
        """
        raise NotImplementedError

    @abstractmethod
    def incremental_sync(self) -> Dict[str, Any]:
        """Perform incremental synchronization, returning only new/changed data.

        Returns:
            Dictionary containing new data and metadata about the sync
        """
        raise NotImplementedError

    @abstractmethod
    def rate_limit(self) -> None:
        """Apply rate limiting to prevent overwhelming the data source."""
        raise NotImplementedError

    @abstractmethod
    def retry(self, exception: Exception, attempt: int) -> bool:
        """Determine whether to retry an operation after an exception.

        Args:
            exception: The exception that occurred
            attempt: Current attempt number (starting from 1)

        Returns:
            True if the operation should be retried, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Return metadata about the connector and its capabilities.

        Returns:
            Dictionary containing connector metadata
        """
        raise NotImplementedError

    @abstractmethod
    def shutdown(self) -> None:
        """Clean up resources and close connections."""
        raise NotImplementedError

    @property
    def is_connected(self) -> bool:
        """Check if the connector is currently connected.

        Returns:
            True if connected, False otherwise
        """
        return self._is_connected

    def set_connected(self, status: bool) -> None:
        """Set the connection status.

        Args:
            status: Connection status to set
        """
        self._is_connected = status