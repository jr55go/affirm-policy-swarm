"""
CFPB Connector: Concrete implementation for Consumer Financial Protection Bureau data source.
Uses the Socrata Open Data API for machine-readable access.
"""

import logging
import time
import urllib3
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import RequestException

# Disable SSL warnings for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .base_connector import BaseSourceConnector
from .normalization import NormalizedPolicyEvent
from .connector_checkpoint import ConnectorCheckpointManager
from .connector_health import ConnectorHealth, ConnectorHealthState

logger = logging.getLogger(__name__)


class CFPBConnector(BaseSourceConnector):
    """
    Concrete connector for the Consumer Financial Protection Bureau (CFPB) data source.
    Fetches and normalizes CFPB enforcement actions or consumer complaints via Socrata API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the CFPBConnector.
        
        Args:
            config: Dictionary containing configuration for the connector
                   Expected keys: 'api_base_url', 'timeout', 'rate_limit_delay'
        """
        super().__init__(config)
        self.api_base_url = config.get('api_base_url', 'https://data.consumerfinance.gov/resource/s6ew-h6mp.json')
        self.timeout = config.get('timeout', 30)
        self.rate_limit_delay = config.get('rate_limit_delay', 1.0)
        self._session = None
        self._checkpoint = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def connect(self) -> bool:
        """
        Establish connection to the CFPB Socrata API by creating a requests session.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info("Connecting to CFPB Socrata API")
            self._session = requests.Session()
            # Set standard browser User-Agent header to avoid being blocked
            self._session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            })
            self._connected = True
            self.logger.info("Connection to CFPB Socrata API established")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to CFPB Socrata API: {str(e)}")
            self._connected = False
            return False
    
    def authenticate(self) -> bool:
        """
        Authenticate with the CFPB Socrata API.
        Note: Socrata public APIs do not require authentication for basic access.
        
        Returns:
            bool: True (since no authentication is required for public endpoints)
        """
        self.logger.info("CFPB Socrata API does not require authentication for public endpoints")
        self._authenticated = True
        return True
    
    def health_check(self) -> bool:
        """
        Check if the connection to the CFPB Socrata API is healthy by making a simple request.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        if not self._connected or not self._session:
            return False
        
        try:
            # Make a minimal request to check API availability with $limit=1 for fast response
            response = self._session.get(
                self.api_base_url,
                params={'$limit': 1},
                timeout=self.timeout,
                verify=False  # Bypass SSL verification
            )
            # Consider 200 OK as healthy, also 429 (rate limit) is still a healthy API, just rate limited
            is_healthy = response.status_code in [200, 429]
            if is_healthy:
                self.logger.debug("CFPB Socrata API health check passed")
            else:
                self.logger.warning(f"CFPB Socrata API health check failed with status {response.status_code}")
            return is_healthy
        except RequestException as e:
            self.logger.error(f"CFPB Socrata API health check failed: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during CFPB Socrata API health check: {str(e)}")
            return False
    
    def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve data from the CFPB Socrata API based on query parameters.
        
        Args:
            query: Dictionary containing query parameters
                  Expected keys: 'size', 'start_date', 'end_date', 'product', 'issue', etc.
                  
        Returns:
            List of dictionaries containing the retrieved data
        """
        if not self.is_connected or not self._session:
            self.connect()
            self.authenticate()
        
        try:
            self.logger.info(f"Fetching data from CFPB Socrata API with query: {query}")
            
            # Prepare request parameters using Socrata (SoQL) syntax
            params = {}
            
            # Handle size parameter -> $limit
            if 'size' in query:
                params['$limit'] = query['size']
            else:
                params['$limit'] = 100  # default batch size
            
            # Set order to date_received DESC as required
            params['$order'] = 'date_received DESC'
            
            # Build WHERE clause for filtering
            where_conditions = []
            
            # Date range filtering
            if 'start_date' in query:
                where_conditions.append(f"date_received >= '{query['start_date']}'")
            if 'end_date' in query:
                where_conditions.append(f"date_received <= '{query['end_date']}'")
            
            # Product filtering
            if 'product' in query:
                # Escape single quotes in product string by doubling them
                product_safe = query['product'].replace("'", "''")
                where_conditions.append(f"product = '{product_safe}'")
                
            # Issue filtering
            if 'issue' in query:
                # Escape single quotes in issue string
                issue_safe = query['issue'].replace("'", "''")
                where_conditions.append(f"issue = '{issue_safe}'")
            
            # If we have any WHERE conditions, combine them
            if where_conditions:
                params['$where'] = " AND ".join(where_conditions)
            
            # Make the request
            response = self._session.get(
                self.api_base_url,
                params=params,
                timeout=self.timeout,
                verify=False  # Bypass SSL verification
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                self.logger.warning("Rate limited by CFPB Socrata API, backing off")
                time.sleep(self.rate_limit_delay * 2)  # Back off longer on rate limit
                return []
            
            # Raise exception for other bad status codes
            response.raise_for_status()
            
            # Parse JSON response - Socrata returns a direct array of objects
            raw_data = response.json()
            
            # Ensure we got a list
            if not isinstance(raw_data, list):
                self.logger.warning(f"Expected list from Socrata API, got {type(raw_data)}")
                raw_data = []
            
            self.logger.info(f"Retrieved {len(raw_data)} records from CFPB Socrata API")
            return raw_data
            
        except RequestException as e:
            self.logger.error(f"Request to CFPB Socrata API failed: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching data from CFPB Socrata API: {str(e)}")
            return []
    
    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize retrieved CFPB Socrata data to the NormalizedPolicyEvent schema.
        
        Args:
            raw_data: List of dictionaries containing raw CFPB complaint data from Socrata
            
        Returns:
            List of dictionaries containing normalized policy event data
        """
        normalized_events = []
        
        for item in raw_data:
            try:
                # Extract relevant fields from Socrata CFPB complaint record
                complaint_id = str(item.get('complaint_id', ''))
                date_received = item.get('date_received', '')
                product = item.get('product', '') or ''
                sub_product = item.get('sub_product', '') or ''
                issue = item.get('issue', '') or ''
                sub_issue = item.get('sub_issue', '') or ''
                consumer_complaint_narrative = item.get('consumer_complaint_narrative', '') or ''
                company_public_response = item.get('company_public_response', '') or ''
                company = item.get('company', '') or ''
                state = item.get('state', '') or ''
                zip_code = item.get('zip_code', '') or ''
                tags = item.get('tags', [])
                consent_provided = item.get('consent_provided', '') or ''
                submitted_via = item.get('submitted_via', '') or ''
                date_sent_to_company = item.get('date_sent_to_company', '') or ''
                company_response_to_consumer = item.get('company_response_to_consumer', '') or ''
                timely_response = item.get('timely_response', '') or ''
                consumer_disputed = item.get('consumer_disputed', '') or ''
                
                # Construct title
                title_parts = ["CFPB Complaint"]
                if product:
                    title_parts.append(product)
                if issue:
                    title_parts.append("-")
                    title_parts.append(issue)
                if sub_product:
                    title_parts.append(f"({sub_product})")
                if sub_issue:
                    title_parts.append("-")
                    title_parts.append(sub_issue)
                
                title = " ".join(title_parts).strip()
                # Clean up extra spaces and dashes
                title = " ".join(title.split())
                
                # Construct summary
                summary_parts = []
                if product:
                    summary_parts.append(f"Product: {product}")
                if issue:
                    summary_parts.append(f"Issue: {issue}")
                if company:
                    summary_parts.append(f"Company: {company}")
                if state:
                    summary_parts.append(f"State: {state}")
                if consumer_complaint_narrative:
                    # Truncate narrative for summary
                    narrative = consumer_complaint_narrative.strip()
                    if len(narrative) > 200:
                        narrative = narrative[:200] + "..."
                    summary_parts.append(f"Narrative: {narrative}")
                
                if not summary_parts:
                    summary = "CFPB complaint received"
                else:
                    summary = ". ".join(summary_parts) + "."
                
                # Determine event type based on complaint characteristics
                event_type = "consumer_complaint"
                if company_response_to_consumer:
                    event_type += "_with_company_response"
                if timely_response == "Yes":
                    event_type += "_timely_response"
                
                # Create normalized event using the schema
                from datetime import datetime
                try:
                    event_date = datetime.fromisoformat(date_received.replace('Z', '+00:00')) if date_received else datetime.now()
                except ValueError:
                    event_date = datetime.now()
                
                normalized_event = NormalizedPolicyEvent(
                    source_name="Consumer Financial Protection Bureau",
                    source_type="Regulator",
                    jurisdiction="Federal",
                    title=title,
                    summary=summary,
                    event_type=event_type,
                    event_date=event_date,
                    url=f"https://www.consumerfinance.gov/complaint/{complaint_id}/" if complaint_id else "",
                    organizations=[company] if company else [],
                    agencies=["Consumer Financial Protection Bureau"],
                    committees=[],  # CFPB complaints don't typically involve congressional committees
                    legislators=[],  # CFPB complaints don't typically involve specific legislators
                    keywords=[product, issue, sub_product, sub_issue, state] + [tag for tag in tags if isinstance(tag, str)],
                    confidence=0.9,  # High confidence since we're mapping directly from official CFPB data
                    raw_payload=item  # Store the original CFPB complaint data
                )
                
                normalized_events.append(normalized_event.to_dict())
                
            except Exception as e:
                self.logger.error(f"Error normalizing CFPB complaint item: {str(e)}")
                # Continue processing other items even if one fails
                continue
        
        self.logger.info(f"Normalized {len(normalized_events)} CFPB complaints to policy events")
        return normalized_events
    
    def incremental_sync(self, checkpoint: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform incremental synchronization since last checkpoint.
        
        Args:
            checkpoint: Optional dictionary containing the last checkpoint
            
        Returns:
            Dictionary containing new data and updated checkpoint
        """
        self.logger.info("Performing incremental sync for CFPB connector")
        
        # Determine the start date for incremental sync
        start_date = None
        if checkpoint and 'last_successful_sync' in checkpoint:
            last_sync = checkpoint['last_successful_sync']
            if isinstance(last_sync, str):
                start_date = last_sync
            elif hasattr(last_sync, 'isoformat'):
                start_date = last_sync.isoformat()
        
        # Build query for incremental sync
        query = {'size': 1000}  # Get a reasonable batch size
        if start_date:
            query['start_date'] = start_date
        
        # Fetch new data
        raw_data = self.fetch(query)
        
        # Normalize the data
        normalized_data = self.normalize(raw_data)
        
        # Create/update checkpoint
        from datetime import datetime
        new_checkpoint = {
            'source_name': 'Consumer Financial Protection Bureau',
            'last_successful_sync': datetime.now().isoformat(),
            'last_cursor': None,  # CFPB API doesn't use cursors in the same way
            'last_timestamp': datetime.now().isoformat(),
            'retry_count': 0,
            'last_error': None
        }
        
        result = {
            'new_data': normalized_data,
            'checkpoint': new_checkpoint
        }
        
        self.logger.info(f"Incremental sync complete: {len(new_data)} new items")
        return result
    
    def checkpoint(self) -> Dict[str, Any]:
        """
        Save current synchronization checkpoint.
        
        Returns:
            Dictionary containing checkpoint data
        """
        from datetime import datetime
        
        checkpoint_data = {
            'source_name': 'Consumer Financial Protection Bureau',
            'last_successful_sync': datetime.now().isoformat(),
            'last_cursor': None,
            'last_timestamp': datetime.now().isoformat(),
            'retry_count': 0,
            'last_error': None
        }
        
        self.logger.debug("Checkpoint created for CFPB connector")
        return checkpoint_data
    
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
            self.logger.info("Shutting down CFPB connector")
            if self._session:
                self._session.close()
                self._session = None
            self._connected = False
            self._authenticated = False
            self.logger.info("CFPB connector shut down successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during CFPB connector shutdown: {str(e)}")
            return False