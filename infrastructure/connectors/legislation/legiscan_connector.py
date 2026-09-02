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

from ..base_connector import BaseSourceConnector
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
        super().__init__("LegiScan", config)  # source_name must be exactly "LegiScan"
        self.api_base_url = config.get('api_base_url', 'https://api.legiscan.com/')
        self.timeout = config.get('timeout', 30)
        self.rate_limit_delay = config.get('rate_limit_delay', 1.0)
        self.api_key = config.get('api_key')
        self._session = None
        self._checkpoint_manager = None  # Will be initialized in BaseConnector or set externally
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
            if not self.connect():
                self.logger.error("Failed to establish connection for fetch operation")
                return []
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
                            # Add the state to each bill record for jurisdiction mapping
                            value['state'] = params.get('state', 'US')
                            raw_data.append(value)
                elif isinstance(search_result, list):
                    # Add state to each bill record
                    state_val = params.get('state', 'US')
                    for item in search_result:
                        if isinstance(item, dict):
                            item['state'] = state_val
                    raw_data = search_result
            elif op == 'getBill':
                # For getBill, the bill data is in 'bill'
                bill_data = response_data.get('bill', {})
                if bill_data:
                    bill_data['state'] = params.get('state', 'US')
                    raw_data = [bill_data]
            elif op == 'getMasterList':
                # For getMasterList, the bills are in 'masterlist'
                master_list = response_data.get('masterlist', [])
                if isinstance(master_list, list):
                    # Add state to each bill record
                    state_val = params.get('state', 'US')
                    for item in master_list:
                        if isinstance(item, dict):
                            item['state'] = state_val
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
            # For LegiScan, state codes like "CA", "TX", "NY" etc. represent state jurisdictions
            # "US" represents federal jurisdiction
            if state == "US":
                jurisdiction = "Federal"
            elif state and len(state) == 2:  # State codes are typically 2 letters
                jurisdiction = f"State ({state})"
            else:
                jurisdiction = "Unknown"

            # Determine policy type based on bill number prefix or chamber
            # This is a simplification - in reality you'd need to check bill type
            policy_type = "legislation"
            if bill_number:
                # Common prefixes: HR (House Resolution), HB (House Bill), SB (Senate Bill), etc.
                bill_upper = bill_number.upper()
                if bill_upper.startswith(('HR', 'HB')):
                    policy_type = "house bill"
                elif bill_upper.startswith(('SB', 'S')):
                    policy_type = "senate bill"
                elif bill_upper.startswith('HJRES'):
                    policy_type = "house joint resolution"
                elif bill_upper.startswith('SJRES'):
                    policy_type = "senate joint resolution"
                elif bill_upper.startswith('HCONRES'):
                    policy_type = "house concurrent resolution"
                elif bill_upper.startswith('SCONRES'):
                    policy_type = "senate concurrent resolution"
                elif bill_upper.startswith('HR') and 'RES' in bill_upper:
                    policy_type = "house resolution"

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

            # Construct summary from available fields
            summary_parts = []
            if bill_number:
                summary_parts.append(f"Bill {bill_number}")
            if title:
                summary_parts.append(title)
            if last_action:
                summary_parts.append(f"Status: {last_action}")
            if state and state != "US":
                summary_parts.append(f"State: {state}")

            summary = ": ".join(summary_parts) if summary_parts else "LegiScan bill record"

            # Build URL - if not provided, construct a basic LegiScan search URL
            if not url:
                url = f"https://legiscan.com/{state}/" if state and state != "US" else "https://legiscan.com/"

            # Create normalized event using the schema
            normalized_event = NormalizedPolicyEvent(
                source_name="LegiScan",
                source_type="legiscan",
                jurisdiction=jurisdiction,
                title=title or f"Bill {bill_number}" if bill_number else "LegiScan Bill",
                summary=summary,
                event_type=policy_type,
                event_date=event_date,
                url=url,
                organizations=[],  # LegiScan bills don't typically have organizations in the same sense
                agencies=[],       # LegiScan bills don't involve government agencies in the bill metadata
                committees=[],     # We don't have committee info in basic bill data from getSearch
                legislators=[sponsor_name] if sponsor_name else [],  # Sponsor as legislator
                topics=[],         # We don't have topic/subject data in basic bill data
                keywords=[bill_number, state, sponsor_name] if bill_number or state or sponsor_name else [],  # Keywords for searchability
                confidence=0.9,    # High confidence since we're mapping directly from official LegiScan data
                evidence=f"LegiScan Bill {bill_number} from {state}" if bill_number and state else "LegiScan bill data",
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
                topics=[],
                keywords=[],
                confidence=0.0,
                evidence=f"Normalization error: {str(e)}",
                raw_payload=raw_data
            )

    def incremental_sync(self) -> Dict[str, Any]:
        """
        Perform incremental synchronization since last checkpoint.

        Returns:
            Dictionary containing new data and metadata about the sync
        """
        self.logger.info("Performing incremental sync for LegiScan connector")

        # Initialize checkpoint manager if not already done
        if self._checkpoint_manager is None:
            # Try to get it from the base class or create a new one
            try:
                from .connector_checkpoint import ConnectorCheckpointManager
                self._checkpoint_manager = ConnectorCheckpointManager()
            except ImportError:
                self.logger.warning("Could not import ConnectorCheckpointManager")
                # Create a simple dict-based checkpoint as fallback
                self._checkpoint_manager = type('DummyCheckpointManager', (), {
                    'get_cursor': lambda self, name: {},
                    'save_cursor': lambda self, name, data: None
                })()

        # Retrieve the current state/checkpoint
        cursor = self._checkpoint_manager.get_cursor(self.source_name)

        # Check for last sync timestamp
        last_sync_time = cursor.get('last_sync_time')

        # Build query parameters for incremental fetch
        # We'll fetch bills from the current session/year
        current_year = datetime.now().year
        query = {
            'op': 'getMasterList',
            'state': 'US',  # Start with federal, could be made configurable
            'year': str(current_year)
        }

        # If we have a last sync time, we could potentially filter
        # Note: LegiScan API doesn't have sophisticated date filtering in getMasterList
        # For a real implementation, we might need to fetch and filter locally
        # or use different API endpoints that support date filtering

        # Fetch new data
        raw_data_list = self.fetch(query)

        # Update checkpoint with current timestamp
        new_cursor = {
            'last_sync_time': datetime.now(timezone.utc).isoformat(),
            'last_count': len(raw_data_list)
        }

        # Save the updated checkpoint
        self._checkpoint_manager.save_cursor(self.source_name, new_cursor)

        # Return the fetched data with metadata
        return {
            'new_data': raw_data_list,
            'count': len(raw_data_list),
            'sync_time': datetime.now(timezone.utc).isoformat(),
            'source': self.source_name
        }

    def checkpoint(self, cursor_data: Dict[str, Any]) -> None:
        """
        Save current synchronization checkpoint.
        
        Args:
            cursor_data: Dictionary containing checkpoint data to save
        """
        if self._checkpoint_manager is None:
            try:
                from .connector_checkpoint import ConnectorCheckpointManager
                self._checkpoint_manager = ConnectorCheckpointManager()
            except ImportError:
                self.logger.warning("Could not import ConnectorCheckpointManager for checkpoint")
                return
                
        self._checkpoint_manager.save_cursor(self.source_name, cursor_data)

    def deduplicate(self, records: List[NormalizedPolicyEvent]) -> List[NormalizedPolicyEvent]:
        """
        Remove duplicate records based on bill ID or number+state combination.
        
        Args:
            records: List of normalized policy events
            
        Returns:
            List of deduplicated normalized policy events
        """
        seen = set()
        deduplicated = []
        
        for record in records:
            # Create a unique key based on bill identifier from raw payload
            raw_payload = record.raw_payload
            bill_id = raw_payload.get('bill_id', '')
            bill_number = raw_payload.get('bill_number', '')
            state = raw_payload.get('state', '')
            
            # Prefer bill_id if available, otherwise use bill_number+state combination
            if bill_id:
                key = f"bill_id-{bill_id}"
            elif bill_number and state:
                key = f"bill-{bill_number}-{state}"
            else:
                # Fallback to hash of entire record
                import hashlib
                key = f"hash-{hashlib.md5(str(raw_payload).encode()).hexdigest()}"
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(record)
        
        self.logger.info(f"Deduplicated {len(records)} records to {len(deduplicated)} unique LegiScan bills")
        return deduplicated

    def rate_limit(self) -> None:
        """Apply rate limiting to prevent overwhelming the LegiScan API."""
        time.sleep(self.rate_limit_delay)

    def retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine whether to retry an operation after an exception.
        
        Args:
            exception: The exception that occurred
            attempt: Current attempt number (starting from 1)
            
        Returns:
            True if the operation should be retried, False otherwise
        """
        # Don't retry client errors (4xx) except 429 (rate limit)
        if isinstance(exception, RequestException):
            if hasattr(exception, 'response') and exception.response is not None:
                status_code = exception.response.status_code
                if 400 <= status_code < 500:
                    # Don't retry client errors except rate limiting
                    return status_code == 429 and attempt < 3
                elif 500 <= status_code < 600:
                    # Retry server errors
                    return attempt < 3
                else:
                    # Retry on connection errors, timeouts, etc.
                    return attempt < 3
            else:
                # Retry on connection errors
                return attempt < 3
        else:
            # Retry on other exceptions up to 3 times
            return attempt < 3

    def metadata(self) -> Dict[str, Any]:
        """
        Return metadata about the connector and its capabilities.
        
        Returns:
            Dictionary containing connector metadata
        """
        return {
            "name": self.source_name,
            "type": "legiscan",
            "jurisdiction": "Multi-State (50 states + federal)",
            "description": "LegiScan API connector for state and federal legislation",
            "version": "1.0.0",
            "endpoint": self.api_base_url,
            "rate_limit": f"{1/self.rate_limit_delay:.1f} requests/second",
            "requires_api_key": bool(self.api_key),
            "supported_operations": [
                "fetch", "normalize", "incremental_sync", "health_check"
            ]
        }

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