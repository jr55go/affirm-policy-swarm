"""
Regulations.gov Connector: Concrete implementation for Regulations.gov data source.
Uses the Regulations.gov v4 API for access to federal regulatory documents.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import RequestException
from datetime import datetime, timezone

from .base_connector import BaseSourceConnector
from .normalization import NormalizedPolicyEvent
from .connector_checkpoint import ConnectorCheckpointManager
from .connector_health import ConnectorHealth, ConnectorHealthState

logger = logging.getLogger(__name__)


class RegulationsGovConnector(BaseSourceConnector):
    """
    Concrete connector for the Regulations.gov data source.
    Fetches and normalizes Regulations.gov documents (rules, proposed rules, notices, etc.).
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the RegulationsGovConnector.
        
        Args:
            config: Dictionary or object containing configuration for the connector
                   Expected keys/attributes: 'api_key', 'timeout', 'rate_limit_delay'
        """
        super().__init__(config)
        try:
            # Try dict access first
            self.api_key = config.get("api_key")
        except (AttributeError, TypeError):
            try:
                self.api_key = getattr(config, "api_key", None)
            except (AttributeError, TypeError):
                self.api_key = None
        
        try:
            self.timeout = config.get("timeout", 30)
        except (AttributeError, TypeError):
            try:
                self.timeout = getattr(config, "timeout", 30)
            except (AttributeError, TypeError):
                self.timeout = 30
        
        try:
            self.rate_limit_delay = config.get("rate_limit_delay", 1.0)
        except (AttributeError, TypeError):
            try:
                self.rate_limit_delay = getattr(config, "rate_limit_delay", 1.0)
            except (AttributeError, TypeError):
                self.rate_limit_delay = 1.0
                
        self.api_base_url = 'https://api.regulations.gov/v4/documents'
        self._session = None
        self._checkpoint = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def connect(self) -> bool:
        """
        Establish connection to the Regulations.gov API by creating a requests session.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info("Connecting to Regulations.gov API")
            self._session = requests.Session()
            # Set required headers for Regulations.gov API
            self._session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'X-Api-Key': self.api_key
            })
            self._connected = True
            self.logger.info("Connection to Regulations.gov API established")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Regulations.gov API: {str(e)}")
            self._connected = False
            return False
    
    def authenticate(self) -> bool:
        """
        Authenticate with the Regulations.gov API.
        Note: Regulations.gov API uses API key in headers, set during connection.
        
        Returns:
            bool: True if authentication setup successful, False otherwise
        """
        if not self._session:
            self.logger.error("Cannot authenticate: not connected")
            return False
            
        try:
            self.logger.info("Setting up Regulations.gov API authentication")
            # The API key is already set in headers during connect()
            self._authenticated = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to authenticate with Regulations.gov API: {str(e)}")
            self._authenticated = False
            return False
    
    def health_check(self) -> bool:
        """
        Check if the connection to the Regulations.gov API is healthy by making a simple request.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        if not self._connected or not self._session:
            return False
        
        try:
            # Make a minimal request to check API availability with page[size]=5, sort, and filter for valid request
            response = self._session.get(
                self.api_base_url,
                params={'page[size]': 5, 'sort': '-lastModifiedDate', 'filter[documentType]': 'Notice'},
                timeout=self.timeout
            )
            # Consider 200 OK as healthy
            is_healthy = response.status_code == 200
            if is_healthy:
                self.logger.debug("Regulations.gov API health check passed")
            else:
                self.logger.warning(f"Regulations.gov API health check failed with status {response.status_code}")
            return is_healthy
        except RequestException as e:
            self.logger.error(f"Regulations.gov API health check failed: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during Regulations.gov API health check: {str(e)}")
            return False
    
    def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve data from the Regulations.gov API based on query parameters.
        
        Args:
            query: Dictionary containing query parameters
                  Expected keys: 'size', 'filter', 'sort', etc.
                  
        Returns:
            List of dictionaries containing the retrieved data
        """
        if not self.is_connected or not self._session:
            self.connect()
            self.authenticate()
        
        try:
            self.logger.info(f"Fetching data from Regulations.gov API with query: {query}")
            
            # Prepare request parameters for Regulations.gov API
            params = {}
            
            # Handle size parameter -> page[size]
            if 'size' in query:
                # Enforce minimum page[size] of 5 for Regulations.gov API
                requested_size = int(query['size'])
                params['page[size]'] = max(5, requested_size)
            else:
                params['page[size]'] = 100  # default batch size (already >= 5)
            
            # Handle filter parameters (Regulations.gov uses filter[field]=value format)
            if 'filter' in query and isinstance(query['filter'], dict):
                for key, value in query['filter'].items():
                    params[f'filter[{key}]'] = value
            
            # Handle search term parameters (q, term, query) -> map to filter[searchTerm]
            search_keys = ['q', 'term', 'query']
            for key in search_keys:
                if key in query and query[key]:
                    params['filter[searchTerm]'] = query[key]
                    break  # Only use the first one found
            
            # Handle sort parameter - always ensure sort is present
            if 'sort' in query:
                params['sort'] = query['sort']
            else:
                # Default sort as required by the API
                params['sort'] = '-lastModifiedDate'
            
            # Crucial: Always ensure the final parameters contain "sort": "-lastModifiedDate"
            # (already handled above by setting default if not present)
            
            # Crucial: If the final parameters contain no filter[...] keys at all, 
            # attach a default filter to satisfy API constraints
            has_filter = any(key.startswith('filter[') for key in params.keys())
            if not has_filter:
                # Add default filter for document type: Rule
                params['filter[documentType]'] = 'Rule'
            # Force financial/BNPL filtering if no search term provided
            if 'filter[searchTerm]' not in params:
                params['filter[searchTerm]'] = 'consumer credit'
            
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
            
            # Regulations.gov API returns a dictionary with 'data' array and metadata
            raw_data = response_data.get('data', [])
            
            # Ensure we got a list
            if not isinstance(raw_data, list):
                self.logger.warning(f"Expected list from Regulations.gov API, got {type(raw_data)}")
                raw_data = []
            
            self.logger.info(f"Retrieved {len(raw_data)} records from Regulations.gov API")
            return raw_data
            
        except RequestException as e:
            self.logger.error(f"Request to Regulations.gov API failed: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching data from Regulations.gov API: {str(e)}")
            return []
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedPolicyEvent:
        """
        Normalize retrieved Regulations.gov data to the NormalizedPolicyEvent schema.
        
        Args:
            raw_data: Dictionary containing raw Regulations.gov document data
            
        Returns:
            NormalizedPolicyEvent object containing normalized policy event data
        """
        try:
            # Regulations.gov API v4 document structure:
            # {
            #   "data": {
            #     "type": "documents",
            #     "id": "document-id",
            #     "attributes": {
            #       "title": "Document Title",
            #       "documentType": "Rule",
            #       "postedDate": "2023-01-01T00:00:00Z",
            #       "objectId": "object-id",
            #       "fileFormats": [
            #         {
            #           "fileUrl": "https://example.com/document.pdf",
            #           "fileFormat": "PDF",
            #           "fileSize": 12345
            #         }
            #       ],
            #       "agencyId": ["agency1", "agency2"]
            #     }
            #   }
            # }
            
            # Extract attributes from the data structure
            attributes = raw_data.get('attributes', {}) if isinstance(raw_data, dict) else {}
            
            # Extract fields according to the mapping requirements
            title = attributes.get('title', '')
            document_type = attributes.get('documentType', '')  # This maps to event_type
            posted_date = attributes.get('postedDate', '')  # This maps to event_date
            
            # Extract URL: prefer fileFormats[0].fileUrl, else construct from objectId
            url = ''
            file_formats = attributes.get('fileFormats', [])
            if isinstance(file_formats, list) and len(file_formats) > 0:
                first_format = file_formats[0]
                if isinstance(first_format, dict) and 'fileUrl' in first_format:
                    url = first_format['fileUrl']
            
            # If no file URL found, construct web URL using objectId
            if not url:
                object_id = attributes.get('objectId', '')
                if object_id:
                    url = f"https://www.regulations.gov/document/{object_id}"
            
            # Extract agency IDs
            agency_ids = attributes.get('agencyId', [])
            if isinstance(agency_ids, str):
                agency_ids = [agency_ids]
            elif not isinstance(agency_ids, list):
                agency_ids = []
            
            # Construct summary from available fields
            summary_parts = []
            if title:
                summary_parts.append(title)
            if document_type:
                summary_parts.append(f"Type: {document_type}")
            summary = " - ".join(summary_parts) if summary_parts else "Regulations.gov document"
            
            # Parse the posted date
            from datetime import datetime
            try:
                # Handle ISO format with timezone
                if posted_date:
                    # Remove timezone info for simpler parsing if needed
                    date_str = posted_date.replace('Z', '+00:00')
                    event_date = datetime.fromisoformat(date_str)
                else:
                    event_date = datetime.now()
            except ValueError:
                # Fallback to current time if parsing fails
                event_date = datetime.now()
            
            # Create normalized event using the schema
            normalized_event = NormalizedPolicyEvent(
                source_name="Regulations.gov",
                source_type="Regulator",
                jurisdiction="Federal",
                title=title,
                summary=summary,
                event_type=document_type,
                event_date=event_date,
                url=url,
                organizations=[],  # Regulations.gov documents don't typically have separate organizations field
                agencies=agency_ids,  # Map agencyId to agencies list
                committees=[],  # Regulations.gov doesn't involve congressional committees
                legislators=[],  # Regulations.gov doesn't involve specific legislators
                keywords=[],  # Could extract from title/description but not required for now
                confidence=0.9,  # High confidence since we're mapping directly from official API
                raw_payload=raw_data  # Store the original document data
            )

            return normalized_event
                
        except Exception as e:
            self.logger.error(f"Error normalizing Regulations.gov document: {str(e)}")
            # Return a minimal valid normalized event in case of error
            from datetime import datetime
            return NormalizedPolicyEvent(
                source_name="Regulations.gov",
                source_type="Regulator",
                jurisdiction="Federal",
                title="Error processing Regulations.gov document",
                summary=f"Failed to normalize Regulations.gov document: {str(e)}",
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
        self.logger.info("Performing incremental sync for Regulations.gov connector")
        
        # Retrieve the current state
        cursor = self.checkpoint_manager.get_cursor(self.__class__.__name__)
        
        # Check for a "last_posted_date"
        last_posted_date = cursor.get('last_posted_date')
        
        # Build query for incremental sync
        query = {'size': 5}  # Regulations.gov API constraint
        filter_dict = {}
        
        # Add posted date filter if we have a checkpoint date
        if last_posted_date:
            # Regulations.gov API uses format: filter[postedDate][ge]=2023-01-01T00:00:00Z
            filter_dict['postedDate[ge]'] = last_posted_date
        
        # Add filter to query if we have any filter conditions
        if filter_dict:
            query['filter'] = filter_dict
        
        # Fetch new data (returns list of documents)
        raw_data_list = self.fetch(query)
        
        # Record a new timestamp
        new_cursor = {"last_posted_date": datetime.now(timezone.utc).isoformat()}
        
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
            self.logger.info("Shutting down Regulations.gov connector")
            if self._session:
                self._session.close()
                self._session = None
            self._connected = False
            self._authenticated = False
            self.logger.info("Regulations.gov connector shut down successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during Regulations.gov connector shutdown: {str(e)}")
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
