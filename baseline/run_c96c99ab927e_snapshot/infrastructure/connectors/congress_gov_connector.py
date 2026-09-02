"""
Congress.gov Connector: Concrete implementation for Congress.gov data source.
Fetches bills and resolutions from the U.S. Congress via the Congress.gov API.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import RequestException
from datetime import datetime, timezone

from .base_connector import BaseSourceConnector
from .normalization import NormalizedPolicyEvent

logger = logging.getLogger(__name__)


class CongressGovConnector(BaseSourceConnector):
    """
    Concrete connector for the Congress.gov data source.
    Fetches and normalizes Congress.gov bills and resolutions.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the CongressGovConnector.

        Args:
            config: Dictionary containing configuration for the connector
                   Expected keys: 'api_base_url', 'timeout', 'rate_limit_delay', 'api_key'
        """
        super().__init__(config)
        self.api_base_url = config.get('api_base_url', 'https://api.congress.gov/v3')
        self.timeout = config.get('timeout', 30)
        self.rate_limit_delay = config.get('rate_limit_delay', 1.0)
        self.api_key = config.get('api_key')
        self._session = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self) -> bool:
        """
        Establish connection to the Congress.gov API by creating a requests session.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info("Connecting to Congress.gov API")
            self._session = requests.Session()
            # Set standard browser User-Agent header to avoid being blocked
            self._session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            })
            self._connected = True
            self.logger.info("Connection to Congress.gov API established")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Congress.gov API: {str(e)}")
            self._connected = False
            return False

    def authenticate(self) -> bool:
        """
        Authenticate with the Congress.gov API.
        Note: Congress.gov API requires an API key for authentication.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        if not self.api_key:
            self.logger.warning("No API key provided for Congress.gov connector")
            self._authenticated = False
            return False
        # The API key is passed in the request parameters, not as a header
        self._authenticated = True
        return True

    def health_check(self) -> bool:
        """
        Check if the connection to the Congress.gov API is healthy by making a simple request.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        if not self._connected or not self._session:
            return False

        try:
            # Make a minimal request to check API availability
            # Using the bills endpoint with limit=1 for fast response
            response = self._session.get(
                f"{self.api_base_url}/bill",
                params={'api_key': self.api_key, 'limit': 1},
                timeout=self.timeout
            )
            # Consider 200 OK as healthy
            is_healthy = response.status_code == 200
            if is_healthy:
                self.logger.debug("Congress.gov API health check passed")
            else:
                self.logger.warning(f"Congress.gov API health check failed with status {response.status_code}")
            return is_healthy
        except RequestException as e:
            self.logger.error(f"Congress.gov API health check failed: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during Congress.gov API health check: {str(e)}")
            return False

    def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve data from the Congress.gov API based on query parameters.

        Args:
            query: Dictionary containing query parameters
                  Expected keys: 'query', 'limit', 'offset', 'sort', etc.

        Returns:
            List of dictionaries containing the retrieved data
        """
        if not self.is_connected or not self._session:
            self.connect()
            self.authenticate()

        try:
            self.logger.info(f"Fetching data from Congress.gov API with query: {query}")

            # Prepare request parameters for Congress.gov API
            params = {}

            # Handle API key
            if self.api_key:
                params['api_key'] = self.api_key

            # Handle query parameter
            if 'query' in query:
                params['query'] = query['query']

            # Handle limit parameter
            if 'limit' in query:
                params['limit'] = query['limit']
            else:
                params['limit'] = 20  # default batch size

            # Handle offset parameter (for pagination)
            if 'offset' in query:
                params['offset'] = query['offset']

            # Handle sort parameter
            if 'sort' in query:
                params['sort'] = query['sort']

            # Make the request
            response = self._session.get(
                f"{self.api_base_url}/bill",
                params=params,
                timeout=self.timeout
            )

            # Raise exception for bad status codes
            response.raise_for_status()

            # Parse JSON response
            response_data = response.json()

            # Congress.gov API returns a dictionary with 'bills' array and pagination info
            raw_data = response_data.get('bills', [])

            # Ensure we got a list
            if not isinstance(raw_data, list):
                self.logger.warning(f"Expected list from Congress.gov API, got {type(raw_data)}")
                raw_data = []

            self.logger.info(f"Retrieved {len(raw_data)} records from Congress.gov API")
            return raw_data

        except RequestException as e:
            self.logger.error(f"Request to Congress.gov API failed: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching data from Congress.gov API: {str(e)}")
            return []

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedPolicyEvent:
        """
        Normalize retrieved Congress.gov data to the NormalizedPolicyEvent schema.

        Args:
            raw_data: Dictionary containing raw Congress.gov bill data

        Returns:
            NormalizedPolicyEvent object containing normalized policy event data
        """
        try:
            # Extract relevant fields from Congress.gov bill data
            bill_number = raw_data.get('number', '')
            bill_type = raw_data.get('type', '')
            title = raw_data.get('title', '')
            sponsor_list = raw_data.get('sponsors', [])
            introduced_date = raw_data.get('introducedDate', '')
            latest_action_text = raw_data.get('latestAction', {}).get('text', '') if raw_data.get('latestAction') else ''
            bill_url = raw_data.get('url', '')

            # Extract sponsor name from sponsors list (take first sponsor if available)
            sponsor_name = ""
            if isinstance(sponsor_list, list) and len(sponsor_list) > 0:
                first_sponsor = sponsor_list[0]
                if isinstance(first_sponsor, dict):
                    sponsor_name = f"{first_sponsor.get('firstName', '')} {first_sponsor.get('lastName', '')}".strip()
                elif isinstance(first_sponsor, str):
                    sponsor_name = first_sponsor

            # Determine policy type based on bill type
            policy_type = "legislation"
            if bill_type in ["hr", "s"]:
                policy_type = "bill"
            elif bill_type in ["hjres", "sjres"]:
                policy_type = "joint resolution"
            elif bill_type in ["hconres", "sconres"]:
                policy_type = "concurrent resolution"
            elif bill_type in ["hres", "sres"]:
                policy_type = "simple resolution"

            # Create normalized event using the schema
            try:
                # Congress.gov introducedDate is in YYYY-MM-DD format
                event_date = datetime.fromisoformat(introduced_date) if introduced_date else datetime.now()
            except ValueError:
                # Try parsing with time if present
                try:
                    event_date = datetime.fromisoformat(introduced_date.replace('Z', '+00:00'))
                except ValueError:
                    event_date = datetime.now()

            normalized_event = NormalizedPolicyEvent(
                source_name="Congress.gov",
                source_type="congress_gov",
                jurisdiction="Federal",
                title=title,
                summary=f"{bill_type.upper()} {bill_number}: {title}",
                event_type=policy_type,
                event_date=event_date,
                url=bill_url,
                organizations=[],  # Congress.gov bills don't typically have organizations in the same sense
                agencies=[],       # Congress.gov bills don't involve federal agencies in the bill metadata
                committees=[],     # We could extract from committees if available, but not in basic bill data
                legislators=[sponsor_name] if sponsor_name else [],  # Sponsor as legislator
                keywords=[],       # We could extract from title/summary but not required for now
                confidence=0.9,    # High confidence since we're mapping directly from official Congress.gov data
                raw_payload=raw_data  # Store the original Congress.gov bill data
            )

            return normalized_event

        except Exception as e:
            self.logger.error(f"Error normalizing Congress.gov bill: {str(e)}")
            # Return a minimal valid normalized event in case of error
            from datetime import datetime
            return NormalizedPolicyEvent(
                source_name="Congress.gov",
                source_type="congress_gov",
                jurisdiction="Federal",
                title="Error processing Congress.gov bill",
                summary=f"Failed to normalize Congress.gov bill: {str(e)}",
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
        self.logger.info("Performing incremental sync for Congress.gov connector")

        # Retrieve the current state
        cursor = self.checkpoint_manager.get_cursor(self.__class__.__name__)

        # Check for a "last_sync_date"
        last_sync_date = cursor.get('last_sync_date')

        # Build query for incremental sync
        query = {'limit': 5}  # Congress.gov API allows up to 250 per page, but we'll use a small batch for testing
        if last_sync_date:
            # We want bills introduced after the last successful sync
            # Congress.gov API uses 'fromDateTime' parameter for updated date, but we'll use a simple query for now
            # For simplicity, we'll use the introduced date as a proxy for recency
            query['query'] = f"introducedDate:{last_sync_date}..*"

        # Fetch new data (returns list of bills)
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
            self.logger.info("Shutting down Congress.gov connector")
            if self._session:
                self._session.close()
                self._session = None
            self._connected = False
            self._authenticated = False
            self.logger.info("Congress.gov connector shut down successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during Congress.gov connector shutdown: {str(e)}")
            return False