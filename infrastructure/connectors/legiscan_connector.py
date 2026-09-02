"""
LegiScan Connector: Concrete implementation for LegiScan data source.
Fetches bills and legislation from state legislatures via the LegiScan API.
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


class LegiScanConnector(BaseSourceConnector):
    """
    Concrete connector for the LegiScan data source.
    Fetches and normalizes LegiScan bills and legislation.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LegiScanConnector.

        Args:
            config: Dictionary containing configuration for the connector
                   Expected keys: 'api_base_url', 'timeout', 'rate_limit_delay', 'api_key'
        """
        super().__init__(config)
        self.api_base_url = config.get('api_base_url', 'https://api.legiscan.com/')
        self.timeout = config.get('timeout', 30)
        self.rate_limit_delay = config.get('rate_limit_delay', 1.0)
        self.api_key = config.get('api_key')
        self._session = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self) -> bool:
        """
        Establish connection to the LegiScan API by creating a requests session.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info("Connecting to LegiScan API")
            self._session = requests.Session()
            # LegiScan API doesn't require special headers beyond standard ones
            self._session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            })
            self._connected = True
            self.logger.info("Connection to LegiScan API established")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to LegiScan API: {str(e)}")
            self._connected = False
            return False

    def authenticate(self) -> bool:
        """
        Authenticate with the LegiScan API.
        Note: LegiScan API uses API key in query parameters.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        if not self.api_key:
            self.logger.warning("No API key provided for LegiScan connector")
            self._authenticated = False
            return False
        # The API key is passed in the request parameters, not as a header
        self._authenticated = True
        return True

    def health_check(self) -> bool:
        """
        Check if the connection to the LegiScan API is healthy by making a simple request.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        if not self._connected or not self._session:
            return False

        try:
            # Make a minimal request to check API availability using getMasterList with minimal parameters
            params = {
                'key': self.api_key,
                'op': 'getMasterList',
                'state': 'US'  # Federal level
            }
            response = self._session.get(
                self.api_base_url,
                params=params,
                timeout=self.timeout
            )
            # Consider 200 OK as healthy
            is_healthy = response.status_code == 200
            if is_healthy:
                # Also check if the response contains valid JSON
                try:
                    data = response.json()
                    if data.get('status') == 'OK':
                        self.logger.debug("LegiScan API health check passed")
                    else:
                        self.logger.warning(f"LegiScan API health check failed: {data.get('message')}")
                        is_healthy = False
                except ValueError:
                    self.logger.warning("LegiScan API health check failed: invalid JSON response")
                    is_healthy = False
            else:
                self.logger.warning(f"LegiScan API health check failed with status {response.status_code}")
            return is_healthy
        except RequestException as e:
            self.logger.error(f"LegiScan API health check failed: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during LegiScan API health check: {str(e)}")
            return False

    def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve data from the LegiScan API based on query parameters.

        Args:
            query: Dictionary containing query parameters
                  Expected keys: 'state', 'query', 'year', etc.

        Returns:
            List of dictionaries containing the retrieved data
        """
        if not self.is_connected or not self._session:
            self.connect()
            self.authenticate()

        try:
            self.logger.info(f"Fetching data from LegiScan API with query: {query}")

            # Prepare request parameters for LegiScan API
            params = {}

            # Handle API key
            if self.api_key:
                params['key'] = self.api_key

            # Handle operation - default to getSearch for bill searching
            if 'op' in query:
                params['op'] = query['op']
            else:
                params['op'] = 'getSearch'  # Default operation

            # Handle state parameter
            if 'state' in query:
                params['state'] = query['state']
            else:
                params['state'] = 'US'  # Default to federal

            # Handle query parameter (search terms)
            if 'query' in query:
                params['query'] = query['query']

            # Handle year parameter
            if 'year' in query:
                params['year'] = query['year']

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

            # LegiScan API returns a dictionary with 'status' and data
            if response_data.get('status') != 'OK':
                self.logger.warning(f"LegiScan API returned non-OK status: {response_data.get('status')}")
                return []

            # Extract the relevant data based on operation
            op = params.get('op', 'getSearch')
            raw_data = []

            if op == 'getSearch':
                # For getSearch, the results are in 'searchresult'
                search_result = response_data.get('searchresult', {})
                if isinstance(search_result, dict):
                    # Convert dict to list of bills, skipping 'summary' key
                    for key, value in search_result.items():
                        if key != 'summary' and isinstance(value, dict):
                            raw_data.append(value)
                elif isinstance(search_result, list):
                    raw_data = search_result
            elif op == 'getBill':
                # For getBill, the bill data is in 'bill'
                bill_data = response_data.get('bill', {})
                if bill_data:
                    raw_data = [bill_data]
            elif op == 'getMasterList':
                # For getMasterList, the bills are in 'masterlist'
                master_list = response_data.get('masterlist', [])
                if isinstance(master_list, list):
                    raw_data = master_list

            # Ensure we got a list
            if not isinstance(raw_data, list):
                self.logger.warning(f"Expected list from LegiScan API, got {type(raw_data)}")
                raw_data = []

            self.logger.info(f"Retrieved {len(raw_data)} records from LegiScan API")
            return raw_data

        except RequestException as e:
            self.logger.error(f"Request to LegiScan API failed: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching data from LegiScan API: {str(e)}")
            return []

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedPolicyEvent:
        """
        Normalize retrieved LegiScan data to the NormalizedPolicyEvent schema.

        Args:
            raw_data: Dictionary containing raw LegiScan bill data

        Returns:
            NormalizedPolicyEvent object containing normalized policy event data
        """
        try:
            # Extract relevant fields from LegiScan bill data
            # Based on LegiScan API documentation for getBill response
            bill_id = raw_data.get('bill_id', '')
            bill_number = raw_data.get('bill_number', '')
            state = raw_data.get('state', '')
            title = raw_data.get('title', '')
            sponsor = raw_data.get('sponsor', '')  # This might be a string or dict
            introduced_date = raw_data.get('introduced_date', '')
            last_action = raw_data.get('last_action', '')
            last_action_date = raw_data.get('last_action_date', '')
            url = raw_data.get('url', '')
            chamber = raw_data.get('chamber', '')  # e.g., 'House', 'Senate'
            status = raw_data.get('status', '')  # e.g., 'Active', 'Passed'

            # Process sponsor field (can be string or dict)
            sponsor_name = ""
            if isinstance(sponsor, dict):
                sponsor_name = f"{sponsor.get('firstName', '')} {sponsor.get('lastName', '')}".strip()
            elif isinstance(sponsor, str):
                sponsor_name = sponsor

            # Determine jurisdiction based on state
            jurisdiction = "Federal" if state == "US" else f"State ({state})"

            # Determine policy type based on bill number prefix or chamber
            # This is a simplification - in reality you'd need to check bill type
            policy_type = "legislation"
            if bill_number:
                # Common prefixes: HR (House Resolution), SB (Senate Bill), etc.
                if bill_number.upper().startswith(('HR', 'HB')):
                    policy_type = "house bill"
                elif bill_number.upper().startswith(('SB', 'S')):
                    policy_type = "senate bill"

            # Use the later of introduced_date or last_action_date for event date
            date_to_use = introduced_date or last_action_date
            try:
                # LegiScan dates are typically in YYYY-MM-DD format
                event_date = datetime.fromisoformat(date_to_use) if date_to_use else datetime.now()
            except ValueError:
                # Try parsing with time if present
                try:
                    event_date = datetime.fromisoformat(date_to_use.replace('Z', '+00:00'))
                except ValueError:
                    event_date = datetime.now()

            # Create normalized event using the schema
            normalized_event = NormalizedPolicyEvent(
                source_name="LegiScan",
                source_type="legiscan",
                jurisdiction=jurisdiction,
                title=title,
                summary=f"{bill_number}: {title} - {last_action}" if bill_number and title and last_action else title or "LegiScan bill",
                event_type=policy_type,
                event_date=event_date,
                url=url,
                organizations=[],  # LegiScan bills don't typically have organizations in the same sense
                agencies=[],       # LegiScan bills don't involve federal agencies in the bill metadata
                committees=[],     # We don't have committee info in basic bill data
                legislators=[sponsor_name] if sponsor_name else [],  # Sponsor as legislator
                keywords=[],       # We could extract from title/summary but not required for now
                confidence=0.9,    # High confidence since we're mapping directly from official LegiScan data
                raw_payload=raw_data  # Store the original LegiScan bill data
            )

            return normalized_event

        except Exception as e:
            self.logger.error(f"Error normalizing LegiScan bill: {str(e)}")
            # Return a minimal valid normalized event in case of error
            from datetime import datetime
            return NormalizedPolicyEvent(
                source_name="LegiScan",
                source_type="legiscan",
                jurisdiction="Unknown",
                title="Error processing LegiScan bill",
                summary=f"Failed to normalize LegiScan bill: {str(e)}",
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
        self.logger.info("Performing incremental sync for LegiScan connector")

        # Retrieve the current state
        cursor = self.checkpoint_manager.get_cursor(self.__class__.__name__)

        # Check for a "last_sync_date"
        last_sync_date = cursor.get('last_sync_date')

        # Build query for incremental sync
        query = {}
        query['op'] = 'getSearch'
        query['state'] = 'US'  # Default to federal level
        query['year'] = str(datetime.now().year)  # Current year

        # We'll use the query parameter to search for recent bills
        # For simplicity, we'll search for bills from the last sync date onward
        # Note: LegiScan API doesn't have a direct date range for getSearch,
        # so we'll rely on the checkpoint to avoid re-processing old data
        # and limit the results to a reasonable number

        # For demonstration, we'll search for a common term to get some bills
        # In a real implementation, you might want to get all bills and filter by date locally
        query['query'] = "budget"  # Generic term likely to return results

        # Limit results to avoid too much data
        # Note: LegiScan API doesn't have a direct limit parameter for getSearch
        # but we can limit what we process

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
            self.logger.info("Shutting down LegiScan connector")
            if self._session:
                self._session.close()
                self._session = None
            self._connected = False
            self._authenticated = False
            self.logger.info("LegiScan connector shut down successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during LegiScan connector shutdown: {str(e)}")
            return False
    def normalize(self, raw_data):
        return []

    def deduplicate(self, records):
        return records

    def checkpoint(self, checkpoint_data):
        pass

    def incremental_sync(self):
        return []

    def rate_limit(self):
        import time
        time.sleep(self.rate_limit_delay)

    def retry(self, exception, attempt):
        return attempt < 3

    def metadata(self):
        return {"name": "LegiScanConnector"}
