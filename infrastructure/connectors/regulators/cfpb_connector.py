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
from datetime import datetime, timezone

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
        super().__init__("CFPB", config)  # source_name must be exactly "CFPB"
        self.api_base_url = config.get('api_base_url', 'https://data.consumerfinance.gov/resource/s6ew-h6mp.json')
        self.timeout = config.get('timeout', 30)
        self.rate_limit_delay = config.get('rate_limit_delay', 1.0)
        self._session = None
        self._checkpoint_manager = ConnectorCheckpointManager()
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
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the connection to the CFPB Socrata API is healthy by making a simple request.
        
        Returns:
            Dictionary containing health status information
        """
        if not self._connected or not self._session:
            return {
                "status": ConnectorHealthState.DOWN.value,
                "error": "Not connected",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
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
                return {
                    "status": ConnectorHealthState.HEALTHY.value,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                self.logger.warning(f"CFPB Socrata API health check failed with status {response.status_code}")
                return {
                    "status": ConnectorHealthState.DEGRADED.value,
                    "error": f"HTTP {response.status_code}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except RequestException as e:
            self.logger.error(f"CFPB Socrata API health check failed: {str(e)}")
            return {
                "status": ConnectorHealthState.DOWN.value,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Unexpected error during CFPB Socrata API health check: {str(e)}")
            return {
                "status": ConnectorHealthState.DOWN.value,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
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
            if not self.connect():
                self.logger.error("Failed to establish connection for fetch operation")
                return []
        
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
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedPolicyEvent:
        """
        Normalize retrieved CFPB Socrata data to the NormalizedPolicyEvent schema.
        
        Args:
            raw_data: Dictionary containing raw CFPB Socrata record
            
        Returns:
            NormalizedPolicyEvent object containing normalized policy event data
        """
        try:
            # Extract relevant fields from CFPB Socrata record
            date_received = raw_data.get('date_received', '')
            product = raw_data.get('product', '') or ''
            issue = raw_data.get('issue', '') or ''
            sub_product = raw_data.get('sub_product', '') or ''
            sub_issue = raw_data.get('sub_issue', '') or ''
            consumer_complaint_narrative = raw_data.get('consumer_complaint_narrative', '') or ''
            company = raw_data.get('company', '') or ''
            state = raw_data.get('state', '') or ''
            zip_code = raw_data.get('zip_code', '') or ''
            tags = raw_data.get('tags', '') or ''
            consumer_consent_provided = raw_data.get('consumer_consent_provided', '') or ''
            submitted_via = raw_data.get('submitted_via', '') or ''
            date_sent_to_company = raw_data.get('date_sent_to_company', '') or ''
            company_response_to_consumer = raw_data.get('company_response_to_consumer', '') or ''
            timely_response = raw_data.get('timely_response', '') or ''
            consumer_disputed = raw_data.get('consumer_disputed', '') or ''
            complaint_id = raw_data.get('complaint_id', '') or ''
            
            # Construct title from product and issue
            title_parts = []
            if product:
                title_parts.append(product)
            if issue:
                title_parts.append(issue)
            title = " - ".join(title_parts) if title_parts else "CFPB Consumer Complaint"
            
            # Construct summary from available fields
            summary_parts = []
            if consumer_complaint_narrative:
                # Truncate narrative for summary if too long
                narrative = consumer_complaint_narrative.strip()
                if len(narrative) > 200:
                    narrative = narrative[:200] + "..."
                summary_parts.append(narrative)
            if product and issue:
                summary_parts.append(f"Product: {product}, Issue: {issue}")
            elif product:
                summary_parts.append(f"Product: {product}")
            elif issue:
                summary_parts.append(f"Issue: {issue}")
            if company:
                summary_parts.append(f"Company: {company}")
            if state:
                summary_parts.append(f"State: {state}")
            
            summary = ". ".join(summary_parts) if summary_parts else "CFPB consumer complaint record"
            
            # Determine event date from date_received or current date
            try:
                if date_received:
                    # CFPB dates are typically in ISO format
                    event_date = datetime.fromisoformat(date_received.replace('Z', '+00:00'))
                else:
                    event_date = datetime.now(timezone.utc)
            except ValueError:
                # Fallback to current date if parsing fails
                event_date = datetime.now(timezone.utc)
            
            # Determine event type based on available data
            event_type = "Consumer Complaint"
            if product:
                event_type = f"{product} Complaint"
            if issue:
                event_type = f"{event_type} - {issue}"
            
            # Build URL - CFPB complaint database URL pattern
            url = f"https://www.consumerfinance.gov/data-research/consumer-complaints/search/?complaint_id={complaint_id}" if complaint_id else "https://www.consumerfinance.gov/data-research/consumer-complaints/"
            
            # Create normalized event using the schema
            normalized_event = NormalizedPolicyEvent(
                source_name="CFPB",
                source_type="Regulator",  # As specified in requirements
                jurisdiction="Federal",   # CFPB is a federal agency
                title=title,
                summary=summary,
                event_type=event_type,
                event_date=event_date,
                url=url,
                organization=[company] if company else [],  # Company mentioned in complaint
                people=[],  # Individual consumers not typically named in public data
                committees=[],  # Not applicable for CFPB
                agencies=["Consumer Financial Protection Bureau"],  # The agency itself
                legislation=[],  # Not directly applicable to individual complaints
                topics=[product, issue, sub_product, sub_issue],  # Product/Issue hierarchy as topics
                keywords=[product, issue, sub_product, sub_issue, state, company],  # Keywords for searchability
                confidence=0.8,  # High confidence for official CFPB data
                evidence=f"CFPB Complaint ID: {complaint_id}" if complaint_id else "CFPB Consumer Complaint Database",
                raw_payload=raw_data  # Store the original CFPB Socrata record
            )
            
            return normalized_event
            
        except Exception as e:
            self.logger.error(f"Error normalizing CFPB Socrata record: {str(e)}")
            # Return a minimal valid normalized event in case of error
            from datetime import datetime
            return NormalizedPolicyEvent(
                source_name="CFPB",
                source_type="Regulator",
                jurisdiction="Federal",
                title="Error processing CFPB record",
                summary=f"Failed to normalize CFPB record: {str(e)}",
                event_type="error",
                event_date=datetime.now(timezone.utc),
                url="",
                organization=[],
                people=[],
                committees=[],
                agencies=["Consumer Financial Protection Bureau"],
                legislation=[],
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
        self.logger.info("Performing incremental sync for CFPB connector")
        
        # Retrieve the current state/checkpoint
        cursor = self._checkpoint_manager.get_cursor(self.source_name)
        
        # Check for last sync timestamp
        last_sync_time = cursor.get('last_sync_time')
        
        # Build query parameters for incremental fetch
        params = {
            '$limit': 100,  # Reasonable batch size for incremental updates
            '$order': 'date_received DESC'  # Most recent first
        }
        
        # If we have a last sync time, we can filter for newer records
        if last_sync_time:
            # Convert to date format for SOQL query
            try:
                # Assuming last_sync_time is in ISO format
                from datetime import datetime
                last_sync_dt = datetime.fromisoformat(last_sync_time.replace('Z', '+00:00'))
                # Format as YYYY-MM-DD for date comparison
                date_str = last_sync_dt.strftime('%Y-%m-%d')
                params['$where'] = f"date_received >= '{date_str}'"
            except Exception as e:
                self.logger.warning(f"Could not parse last_sync_time for filtering: {e}")
                # Continue without date filter if parsing fails
        
        # Fetch new data
        raw_data_list = self.fetch(params)
        
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
        self._checkpoint_manager.save_cursor(self.source_name, cursor_data)
    
    def deduplicate(self, records: List[NormalizedPolicyEvent]) -> List[NormalizedPolicyEvent]:
        """
        Remove duplicate records based on complaint ID.
        
        Args:
            records: List of normalized policy events
            
        Returns:
            List of deduplicated normalized policy events
        """
        seen = set()
        deduplicated = []
        
        for record in records:
            # Create a unique key based on complaint ID from raw payload
            raw_payload = record.raw_payload
            complaint_id = raw_payload.get('complaint_id', '')
            
            # If no complaint ID, use a hash of the entire record as fallback
            if not complaint_id:
                import hashlib
                complaint_id = hashlib.md5(str(raw_payload).encode()).hexdigest()
            
            if complaint_id not in seen:
                seen.add(complaint_id)
                deduplicated.append(record)
        
        self.logger.info(f"Deduplicated {len(records)} records to {len(deduplicated)} unique CFPB complaints")
        return deduplicated
    
    def rate_limit(self) -> None:
        """Apply rate limiting to prevent overwhelming the CFPB Socrata API."""
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
            "type": "Regulator",
            "jurisdiction": "Federal",
            "description": "CFPB Socrata API connector for consumer complaint data",
            "version": "1.0.0",
            "endpoint": self.api_base_url,
            "rate_limit": f"{1/self.rate_limit_delay:.1f} requests/second",
            "requires_api_key": False,  # CFPB Socrata API is public
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
            self.logger.info("Shutting down CFPB connector")
            if self._session:
                self._session.close()
                self._session = None
            self._connected = False
            self.logger.info("CFPB connector shut down successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during CFPB connector shutdown: {str(e)}")
            return False