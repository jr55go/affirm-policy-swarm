"""
Research Connector: Concrete implementation for policy research data source.
Fetches white papers, policy briefs, and advocacy reports from think tanks and research organizations.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import RequestException
from datetime import datetime, timezone
import feedparser  # For parsing RSS feeds

from ..base_connector import BaseSourceConnector
from ..normalization import NormalizedPolicyEvent

logger = logging.getLogger(__name__)


class ResearchConnector(BaseSourceConnector):
    """
    Concrete connector for policy research sources.
    Fetches and normalizes policy research from think tanks and advocacy organizations.
    """

    # Common research organization RSS feeds
    DEFAULT_FEEDS = {
        'Brookings Institution': 'https://www.brookings.edu/feed/',
        'National Consumer Law Center': 'https://www.nclc.org/feed',
        'Consumer Federation of America': 'https://consumerfed.org/feed/',
        'Consumer Federation of America': 'https://consumerfed.org/feed/',  # Duplicate to ensure it's there
        'New America': 'https://www.newamerica.org/feed/',
        'Urban Institute': 'https://www.urban.org/feeds/research.xml',
        'Brookings Institution': 'https://www.brookings.edu/feed/'  # Duplicate to ensure it's there
    }

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the ResearchConnector.

        Args:
            config: Dictionary containing configuration for the connector
                   Expected keys: 'feeds' (dict of name->url), 'timeout', 'rate_limit_delay'
        """
        super().__init__("Research", config)  # Generic source name, will be overridden per source
        self.feeds = config.get('feeds', self.DEFAULT_FEEDS)
        self.timeout = config.get('timeout', 30)
        self.rate_limit_delay = config.get('rate_limit_delay', 2.0)  # Be respectful to research sites
        self._session = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self) -> bool:
        """
        Establish connection by creating a requests session.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info("Connecting to research feeds")
            self._session = requests.Session()
            # Set a user agent that identifies us as a research bot
            self._session.headers.update({
                'User-Agent': 'Affirm Policy Research Monitor/1.0 (+https://affirm.com)',
                'Accept': 'application/rss+xml, application/xml, text/xml, text/html'
            })
            self._connected = True
            self.logger.info("Connection to research feeds established")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to research feeds: {str(e)}")
            self._connected = False
            return False

    def authenticate(self) -> bool:
        """
        Authenticate with research sources.
        Most research RSS feeds are publicly accessible and don't require authentication.

        Returns:
            bool: True (authentication not required for public RSS feeds)
        """
        self._authenticated = True
        return True

    def health_check(self) -> Dict[str, Any]:
        """
        Check if the connection to research feeds is healthy by sampling a few feeds.

        Returns:
            Dictionary containing health status information
        """
        if not self._connected or not self._session:
            return {"status": "unhealthy", "reason": "Not connected"}

        # Test a few key feeds
        test_feeds = dict(list(self.feeds.items())[:3])  # Test first 3 feeds
        results = {}
        overall_healthy = True

        for name, url in test_feeds.items():
            try:
                response = self._session.get(url, timeout=self.timeout)
                is_healthy = response.status_code == 200
                results[name] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "status_code": response.status_code,
                    "url": url
                }
                if not is_healthy:
                    overall_healthy = False
                    self.logger.warning(f"Health check failed for {name}: {response.status_code}")
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "url": url
                }
                overall_healthy = False
                self.logger.warning(f"Health check failed for {name}: {str(e)}")

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "feeds_checked": len(test_feeds),
            "details": results
        }

    def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve research papers from RSS feeds based on query parameters.

        Args:
            query: Dictionary containing query parameters
                  Expected keys: 'keywords' (list of strings), 'sources' (list of source names), 
                  'since' (datetime for recent items), 'limit' (int)

        Returns:
            List of dictionaries containing the retrieved research items
        """
        if not self.is_connected or not self._session:
            if not self.connect():
                self.logger.error("Failed to establish connection for fetch operation")
                return []
            self.authenticate()

        try:
            self.logger.info(f"Fetching research with query: {query}")

            # Extract query parameters
            keywords = query.get('keywords', ['buy now pay later', 'BNPL', 'consumer credit', 'fintech', 'small dollar loans'])
            sources = query.get('sources', list(self.feeds.keys()))
            since = query.get('since')  # datetime object
            limit = query.get('limit', 50)  # Default to 50 items

            # Normalize keywords to lowercase for case-insensitive matching
            keywords = [k.lower() for k in keywords]

            results = []

            # Fetch from each specified source
            for source_name in sources:
                if source_name not in self.feeds:
                    self.logger.warning(f"Unknown source: {source_name}")
                    continue

                feed_url = self.feeds[source_name]
                try:
                    self.logger.debug(f"Fetching feed from {source_name}: {feed_url}")
                    
                    # Rate limiting
                    time.sleep(self.rate_limit_delay)
                    
                    response = self._session.get(feed_url, timeout=self.timeout)
                    response.raise_for_status()
                    
                    # Parse the RSS feed
                    feed = feedparser.parse(response.content)
                    
                    if feed.bozo:
                        self.logger.warning(f"Feed parsing issues for {source_name}: {feed.bozo_exception}")
                    
                    # Process each entry
                    for entry in feed.entries:
                        # Check if we've reached our limit
                        if len(results) >= limit:
                            break
                            
                        # Extract basic information
                        title = entry.get('title', '').strip()
                        summary = entry.get('summary', entry.get('description', '')).strip()
                        url = entry.get('link', '').strip()
                        
                        # Parse date
                        published = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published = datetime(*entry.published_parsed[:6])
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            published = datetime(*entry.updated_parsed[:6])
                        else:
                            published = datetime.now(timezone.utc)
                        
                        # Make published timezone-aware if it isn't already
                        if published.tzinfo is None:
                            published = published.replace(tzinfo=timezone.utc)
                        
                        # Filter by date if 'since' is provided
                        if since and published < since:
                            continue
                        
                        # Filter by keywords (case-insensitive)
                        text_to_search = f"{title} {summary}".lower()
                        if not any(keyword in text_to_search for keyword in keywords):
                            continue
                        
                        # Add to results
                        results.append({
                            'title': title,
                            'summary': summary,
                            'url': url,
                            'published': published,
                            'source_name': source_name,
                            'source_url': feed_url,
                            'raw_entry': entry  # Keep raw entry for normalization
                        })
                    
                    # Break if we've reached our limit
                    if len(results) >= limit:
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error fetching from {source_name}: {str(e)}")
                    continue

            self.logger.info(f"Retrieved {len(results)} research items matching criteria")
            return results

        except RequestException as e:
            self.logger.error(f"Request to research feeds failed: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching research data: {str(e)}")
            return []

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedPolicyEvent:
        """
        Normalize retrieved research data to the NormalizedPolicyEvent schema.

        Args:
            raw_data: Dictionary containing raw research item data

        Returns:
            NormalizedPolicyEvent object containing normalized policy event data
        """
        try:
            # Extract fields from raw data
            title = raw_data.get('title', 'Untitled Research')
            summary = raw_data.get('summary', '')
            url = raw_data.get('url', '')
            published = raw_data.get('published', datetime.now(timezone.utc))
            source_name = raw_data.get('source_name', 'Unknown Research Source')
            source_url = raw_data.get('source_url', '')
            raw_entry = raw_data.get('raw_entry', {})
            
            # Extract authors/people from the entry if available
            people = []
            if hasattr(raw_entry, 'authors'):
                if isinstance(raw_entry.authors, list):
                    people = [author.get('name', str(author)) for author in raw_entry.authors if hasattr(author, 'get')]
                    people = [p for p in people if p]  # Remove empty strings
                elif hasattr(raw_entry.authors, 'name'):
                    people = [raw_entry.authors.name]
            
            # Extract organizations from the source name
            organizations = [source_name] if source_name else []
            
            # Extract topics/keywords from tags/categories if available
            topics = []
            keywords_list = []
            if hasattr(raw_entry, 'tags'):
                if isinstance(raw_entry.tags, list):
                    for tag in raw_entry.tags:
                        term = getattr(tag, 'term', str(tag))
                        if term:
                            topics.append(term)
                            keywords_list.append(term)
            
            # If no topics from tags, extract from title/summary
            if not topics:
                # Simple keyword extraction - in a real implementation, you might use NLP
                text = f"{title} {summary}".lower()
                research_terms = ['policy', 'research', 'report', 'brief', 'analysis', 'study', 
                                'consumer credit', 'fintech', 'bnpl', 'buy now pay later',
                                'small dollar', 'payday lending', 'financial regulation']
                for term in research_terms:
                    if term in text:
                        topics.append(term)
                        keywords_list.append(term)
            
            # Determine jurisdiction - most US-based research organizations are federal level
            jurisdiction = "Federal"  # Default assumption for US-based think tanks
            
            # Determine event type - research publications are typically reports or briefs
            # As per requirement, event_type is always "Publication" for research
            event_type = "Publication"
            
            # Create normalized event
            normalized_event = NormalizedPolicyEvent(
                source_name=source_name,
                source_type="research",
                jurisdiction=jurisdiction,
                title=title,
                summary=summary[:500] if summary else "",  # Limit summary length
                event_type=event_type,
                event_date=published,
                url=url,
                organization=organizations,
                people=people,
                committees=[],  # Research typically doesn't have committees
                agencies=[],    # Research typically doesn't involve government agencies directly
                legislation=[], # Research typically doesn't reference specific legislation
                topics=list(set(topics))[:10],  # Deduplicate and limit
                keywords=list(set(keywords_list))[:10],  # Deduplicate and limit
                confidence=0.8,  # Good confidence for research from reputable sources
                evidence=f"Retrieved from {source_name} RSS feed: {source_url}",
                raw_payload=raw_entry.__dict__ if hasattr(raw_entry, '__dict__') else str(raw_entry),
                connector_version="1.0.0",
                collected_at=datetime.now(timezone.utc)
            )

            return normalized_event

        except Exception as e:
            self.logger.error(f"Error normalizing research item: {str(e)}")
            # Return a minimal valid normalized event in case of error
            return NormalizedPolicyEvent(
                source_name=raw_data.get('source_name', 'Unknown Research Source'),
                source_type="research",
                jurisdiction="Federal",
                title="Error processing research item",
                summary=f"Failed to normalize research item: {str(e)}",
                event_type="Publication",
                event_date=datetime.now(timezone.utc),
                url="",
                organization=[],
                people=[],
                committees=[],
                agencies=[],
                legislation=[],
                topics=[],
                keywords=[],
                confidence=0.0,
                evidence=f"Error during normalization: {str(e)}",
                raw_payload=raw_data,
                connector_version="1.0.0",
                collected_at=datetime.now(timezone.utc)
            )

    def incremental_sync(self) -> Dict[str, Any]:
        """
        Perform incremental synchronization since last checkpoint.

        Returns:
            Dictionary containing new data and metadata about the sync
        """
        self.logger.info("Performing incremental sync for research connector")

        # Retrieve the current state
        cursor = self.checkpoint_manager.get_cursor(self.__class__.__name__)

        # Check for a "last_sync_date"
        last_sync_date = cursor.get('last_sync_date')

        # Build query for incremental sync
        query = {'limit': 50}  # Reasonable batch size
        if last_sync_date:
            # Convert string back to datetime if needed
            if isinstance(last_sync_date, str):
                try:
                    last_sync_date = datetime.fromisoformat(last_sync_date.replace('Z', '+00:00'))
                except ValueError:
                    # If parsing fails, ignore the date filter
                    last_sync_date = None
            query['since'] = last_sync_date

        # Fetch new data
        raw_data_list = self.fetch(query)

        # Record a new timestamp
        new_cursor = {"last_sync_date": datetime.now(timezone.utc).isoformat()}

        # Save the state
        self.checkpoint(new_cursor)

        # Return the fetched data
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
            self.logger.info("Shutting down research connector")
            if self._session:
                self._session.close()
                self._session = None
            self._connected = False
            self._authenticated = False
            self.logger.info("Research connector shut down successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during research connector shutdown: {str(e)}")
            return False

    def metadata(self) -> Dict[str, Any]:
        """
        Return metadata about the connector and its capabilities.
        
        Returns:
            Dictionary containing connector metadata
        """
        return {
            "name": self.source_name,
            "type": "research",
            "jurisdiction": "Primarily US Federal (with some state/local)",
            "description": "Policy research connector for think tanks and advocacy organizations",
            "version": "1.0.0",
            "feeds_count": len(self.feeds),
            "sample_feeds": list(self.feeds.keys())[:5],  # First 5 feeds as examples
            "rate_limit": f"{1/self.rate_limit_delay:.1f} requests/second",
            "requires_api_key": False,
            "supported_operations": [
                "fetch", "normalize", "incremental_sync", "health_check"
            ]
        }

    def deduplicate(self, records: List[NormalizedPolicyEvent]) -> List[NormalizedPolicyEvent]:
        """
        Remove duplicate records based on URL or title similarity.

        Args:
            records: List of normalized policy events

        Returns:
            List of deduplicated normalized policy events
        """
        if not records:
            return records
        
        # Simple deduplication based on URL (most reliable)
        seen_urls = set()
        deduplicated = []
        
        for record in records:
            url = record.url
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduplicated.append(record)
            elif not url:
                # For records without URL, fall back to title+source
                key = f"{record.title}:{record.source_name}"
                if key not in seen_urls:  # Reusing the set for simplicity
                    seen_urls.add(key)
                    deduplicated.append(record)
        
        self.logger.info(f"Deduplicated {len(records)} records to {len(deduplicated)} unique records")
        return deduplicated

    def rate_limit(self) -> None:
        """
        Apply rate limiting to prevent overwhelming the data source.
        """
        time.sleep(self.rate_limit_delay)