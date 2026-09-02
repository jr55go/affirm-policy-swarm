import abc
from typing import Any, Dict, Optional


class BaseSourceConnector(abc.ABC):
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

    @abc.abstractmethod
    def connect(self) -> bool:
        """Establish connection to the data source.

        Returns:
            True if connection successful, False otherwise
        """
        raise NotImplementedError

    @abc.abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the data source if required.

        Returns:
            True if authentication successful, False otherwise
        """
        raise NotImplementedError

    @abc.abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the data source connection.

        Returns:
            Dictionary containing health status information
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch(self) -> Any:
        """Fetch raw data from the data source.

        Returns:
            Raw data retrieved from the source (format depends on implementation)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def normalize(self, raw_data: Any) -> Any:
        """Normalize raw data into a common format.

        Args:
            raw_data: Data returned from fetch() method

        Returns:
            Normalized data in a standard format
        """
        raise NotImplementedError

    @abc.abstractmethod
    def incremental_sync(self) -> Dict[str, Any]:
        """Perform incremental synchronization, returning only new/changed data.

        Returns:
            Dictionary containing new data and metadata about the sync
        """
        raise NotImplementedError

    @abc.abstractmethod
    def checkpoint(self, checkpoint_data: Dict[str, Any]) -> None:
        """Save checkpoint data for incremental synchronization.

        Args:
            checkpoint_data: Data to save for resuming synchronization later
        """
        raise NotImplementedError

    @abc.abstractmethod
    def retry(self, exception: Exception, attempt: int) -> bool:
        """Determine whether to retry an operation after an exception.

        Args:
            exception: The exception that occurred
            attempt: Current attempt number (starting from 1)

        Returns:
            True if the operation should be retried, False otherwise
        """
        raise NotImplementedError

    @abc.abstractmethod
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