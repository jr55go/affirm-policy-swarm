"""
Federal Register Connector: Concrete implementation for Federal Register data source.
Uses the Federal Register API for machine-readable access to federal regulations.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import RequestException
from datetime import datetime, timezone

from .base_connector import BaseSourceConnector
from .normalization import NormalizedPolicyEvent
from .connector_checkpoint import CheckpointManager
from .connector_health import ConnectorHealth, ConnectorHealthState

logger = logging.getLogger(__name__)


class FederalRegisterConnector(BaseSourceConnector):
    """
    Concrete connector for the Federal Register data source.
    Fetches and normalizes Federal Register articles (rules, proposed rules, notices, etc.).
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the FederalRegisterConnector.

        Args:
            config: Dictionary containing configuration for the connector
                   Expected keys: 'api_base_url', 'timeout', 'rate_limit_delay'
        """
        super().__init__(config)
        self.api_base_url = config.get('api_base_url', 'https://www.federalregister.gov/api/v1/articles.json')
        self.timeout = config.get('timeout', 30)
        self.rate_limit_delay = config.get('rate_limit_delay', 1.0)
        self._session = None
        self._checkpoint = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self) -> bool:
        """
        Establish connection to the Federal Register API by creating a requests session.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info("Connecting to Federal Register API")
            self._session = requests.Session()
            # Set standard browser User-Agent header to avoid being blocked
            self._session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            })
            self._connected = True
            self.logger.info("Connection to Federal Register API established")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Federal Register API: {str(e)}")
            self._connected = False
            return False

    def authenticate(self) -> bool:
        """
        Authenticate with the Federal Register API.
        Note: Federal Register public API does not require authentication for basic access.

        Returns:
            bool: True (since no authentication is required for public endpoints)
        """
        self.logger.info("Federal Register API does not require authentication for public endpoints")
        self._authenticated = True
        return True

    def health_check(self) -> bool:
        """
        Check if the connection to the Federal Register API is healthy by making a simple request.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        if not self._connected or not self._session:
            return False

        try:
            # Make a minimal request to check API availability with per_page=1 for fast response
            response = self._session.get(
                self.api_base_url,
                params={'per_page': 1},
                timeout=self.timeout
            )
            # Consider 200 OK as healthy
            is_healthy = response.status_code == 200
            if is_healthy:
                self.logger.debug("Federal Register API health check passed")
            else:
                self.logger.warning(f"Federal Register API health check failed with status {response.status_code}")
            return is_healthy
        except RequestException as e:
            self.logger.error(f"Federal Register API health check failed: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during Federal Register API health check: {str(e)}")
            return False

    def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve data from the Federal Register API based on query parameters.

        Args:
            query: Dictionary containing query parameters
                  Expected keys: 'size', 'start_date', 'end_date', 'type', 'agency_names', etc.

        Returns:
            List of dictionaries containing the retrieved data
        """
        if not self.is_connected or not self._session:
            self.connect()
            self.authenticate()

        try:
            self.logger.info(f"Fetching data from Federal Register API with query: {query}")

            # Prepare request parameters for Federal Register API
            params = {}

            # Handle size parameter -> per_page
            if 'size' in query:
                params['per_page'] = query['size']
            else:
                params['per_page'] = 100  # default batch size

            # Force financial/BNPL filtering
            params['conditions[term]'] = 'consumer credit OR finance OR BNPL'

            # Date range filtering (Federal Register uses publication_date)
            if 'start_date' in query:
                params['publication_date[gte]'] = query['start_date']
            if 'end_date' in query:
                params['publication_date[lte]'] = query['end_date']

            # Type filtering (e.g., Rule, Proposed Rule, Notice)
            if 'type' in query:
                params['type'] = query['type']

            # Agency filtering
            if 'agency_names' in query:
                # Federal Register API expects agency names as a comma-separated string for the 'agencies[]' parameter
                # However, the API uses a different format: we can use 'agencies[]' multiple times or a comma-separated string in one parameter
                # Let's use the format: agencies[]=agency1&agencies[]=agency2
                # But requests will handle a list of values for the same key if we pass a list
                # We'll pass as a list for the key 'agencies[]'
                agency_names = query['agency_names']
                if isinstance(agency_names, list):
                    params['agencies[]'] = agency_names
                else:
                    # If it's a string, split by comma if needed, but assume it's a single agency or comma-separated string
                    # We'll split by comma and make a list
                    agency_list = [name.strip() for name in str(agency_names).split(',') if name.strip()]
                    if agency_list:
                        params['agencies[]'] = agency_list

            # Make the request
            response = self._session.get(
                self.api_base_url,
                params=params,
                timeout=self.timeout
            )

            # Raise exception for bad status codes
            response.raise_for_status()

            # Parse JSON response
            response_data = response.json()

            # Federal Register API returns a dictionary with 'results' array and metadata
            raw_data = response_data.get('results', [])

            # Ensure we got a list
            if not isinstance(raw_data, list):
                self.logger.warning(f"Expected list from Federal Register API, got {type(raw_data)}")
                raw_data = []

            self.logger.info(f"Retrieved {len(raw_data)} records from Federal Register API")
            return raw_data

        except RequestException as e:
            self.logger.error(f"Request to Federal Register API failed: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching data from Federal Register API: {str(e)}")
            return []

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedPolicyEvent:
        """
        Normalize retrieved Federal Register data to the NormalizedPolicyEvent schema.

        Args:
            raw_data: Dictionary containing raw Federal Register article data

        Returns:
            NormalizedPolicyEvent object containing normalized policy event data
        """
        try:
            # Extract relevant fields from Federal Register article
            title = raw_data.get('title', '')
            abstract = raw_data.get('abstract', '') or ''
            publication_date = raw_data.get('publication_date', '')
            html_url = raw_data.get('html_url', '')
            article_type = raw_data.get('type', '')  # e.g., "Rule", "Proposed Rule", "Notice"
            agencies = raw_data.get('agencies', [])  # List of agency objects

            # Extract agency names from the agencies list - safely handle nested dictionaries
            agency_names = []
            if isinstance(agencies, list):
                for agency in agencies:
                    if isinstance(agency, dict) and 'name' in agency:
                        agency_names.append(agency['name'])
                    elif isinstance(agency, str):
                        agency_names.append(agency)

            # Construct summary from abstract (if available) or fallback
            summary = abstract.strip() if abstract and abstract.strip() else "Federal Register article"

            # Create normalized event using the schema
            from datetime import datetime
            try:
                # Federal Register publication_date is in YYYY-MM-DD format
                event_date = datetime.fromisoformat(publication_date) if publication_date else datetime.now()
            except ValueError:
                # Try parsing with time if present
                try:
                    event_date = datetime.fromisoformat(publication_date.replace('Z', '+00:00'))
                except ValueError:
                    event_date = datetime.now()

            normalized_event = NormalizedPolicyEvent(
                source_name="Federal Register",
                source_type="Regulator",
                jurisdiction="Federal",
                title=title,
                summary=summary,
                event_type=article_type,
                event_date=event_date,
                url=html_url,
                organizations=[],  # Federal Register articles don't typically have organizations in the same sense
                agencies=agency_names,
                committees=[],  # Federal Register doesn't involve congressional committees in the article metadata
                legislators=[],  # Federal Register doesn't involve specific legislators
                keywords=[],  # We could extract from title/abstract but not required for now
                confidence=0.9,  # High confidence since we're mapping directly from official Federal Register data
                raw_payload=raw_data  # Store the original Federal Register article data
            )

            return normalized_event

        except Exception as e:
            self.logger.error(f"Error normalizing Federal Register article: {str(e)}")
            # Return a minimal valid normalized event in case of error
            from datetime import datetime
            return NormalizedPolicyEvent(
                source_name="Federal Register",
                source_type="Regulator",
                jurisdiction="Federal",
                title="Error processing Federal Register article",
                summary=f"Failed to normalize Federal Register article: {str(e)}",
                event_type="error",
                event_date=datetime.now(),
                url="",
                organizations=[],
                agencies=[],
                committees=[],
                legislators=[],
                keywords=[],
                confidence=0.0,
                raw_payload=raw_data
            )

    def incremental_sync(self) -> Dict[str, Any]:
        """
        Perform incremental synchronization since last checkpoint.

        Returns:
            Dictionary containing new data and updated checkpoint
        """
        self.logger.info("Performing incremental sync for Federal Register connector")

        # Retrieve the current state
        cursor = self.checkpoint_manager.get_cursor(self.__class__.__name__)

        # Check for a "last_sync_date"
        last_sync_date = cursor.get('last_sync_date')

        # Build query for incremental sync
        query = {'size': 3}  # Federal Register basic API constraint
        if last_sync_date:
            # We want articles published after the last successful sync
            query['start_date'] = last_sync_date

        # Fetch new data (returns list of articles)
        raw_data_list = self.fetch(query)

        # Record a new timestamp
        new_cursor = {"last_sync_date": datetime.now(timezone.utc).isoformat()}

        # Save the state
        self.checkpoint(new_cursor)

        # Return the fetched raw data
        return raw_data_list

    def checkpoint(self, cursor_data: Dict[str, Any]) -> None:
        """
        Save current synchronization checkpoint.
        
        Args:
            cursor_data: Dictionary containing checkpoint data to save
        """
        self.checkpoint_manager.save_cursor(self.__class__.__name__, cursor_data)

    def retry(self, operation: callable, max_retries: int = 3, backoff_factor: float = 1.0) -> Any:
        """
        Retry a failed operation with exponential backoff.

        Args:
            operation: Callable operation to retry
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for exponential delay

        Returns:
            Result of the operation if successful

        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Attempt {attempt + 1} of {max_retries} for operation")
                result = operation()
                if attempt > 0:
                    self.logger.info(f"Operation succeeded on attempt {attempt + 1}")
                return result
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    sleep_time = backoff_factor * (2 ** attempt)
                    self.logger.debug(f"Sleeping {sleep_time} seconds before retry")
                    time.sleep(sleep_time)

        self.logger.error(f"All {max_retries} attempts failed. Last error: {str(last_exception)}")
        raise last_exception

    def shutdown(self) -> bool:
        """
        Perform clean shutdown of the connector.

        Returns:
            bool: True if shutdown successful, False otherwise
        """
        try:
            self.logger.info("Shutting down Federal Register connector")
            if self._session:
                self._session.close()
                self._session = None
            self._connected = False
            self._authenticated = False
            self.logger.info("Federal Register connector shut down successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during Federal Register connector shutdown: {str(e)}")
            return False

    # --- ABSTRACT METHOD STUBS TO PREVENT INITIALIZATION CRASH ---
    def deduplicate(self, records):
        '''Default passthrough deduplication'''
        return records

    def metadata(self):
        '''Default metadata'''
        return {"source": self.source_name, "status": "active"}

    def rate_limit(self):
        '''Default rate limit handler'''
        pass



    @property
    def checkpoint_manager(self):
        from infrastructure.connectors.connector_checkpoint import CheckpointManager
        if not hasattr(self, '_checkpoint_manager'):
            self._checkpoint_manager = CheckpointManager()
        return self._checkpoint_manager

