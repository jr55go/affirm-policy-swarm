"""
Public Statement Connector: Concrete implementation for official social media posts and newsletters.
Fetches and normalizes official social media posts, LinkedIn updates, and official newsletters from regulators and agencies.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import requests
import feedparser
from requests.exceptions import RequestException
from datetime import datetime, timezone

from .base_connector import BaseSourceConnector
from .normalization import NormalizedPolicyEvent
from .connector_checkpoint import ConnectorCheckpointManager
from .connector_health import ConnectorHealth, ConnectorHealthState

logger = logging.getLogger(__name__)


class PublicStatementConnector(BaseSourceConnector):
    """
    Concrete connector for official social media posts and newsletters.
    Fetches and normalizes official social media posts, LinkedIn updates, and official newsletters 
    from regulators and agencies via RSS feeds (where available) or APIs.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the PublicStatementConnector.

        Args:
            config: Dictionary containing configuration for the connector
                   Expected keys: 'feeds' (list of feed configs), 'timeout', 'rate_limit_delay'
                   Each feed config should have: 'name', 'url', and optionally 'source_name_override'
                   For social media, we often use RSS feeds provided by platforms (e.g., Twitter via nitter, LinkedIn via RSS bridges)
                   or official newsletters/RSS feeds from agencies.
        """
        super().__init__(config)
        self.feeds = config.get('feeds', [])
        self.timeout = config.get('timeout', 30)
        self.rate_limit_delay = config.get('rate_limit_delay', 1.0)
        self._session = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self) -> bool:
        """
        Establish connection by creating a requests session.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info("Connecting to public statement sources (social media, newsletters)")
            self._session = requests.Session()
            # Set a user agent to avoid being blocked
            self._session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            self._connected = True
            self.logger.info("Connection to public statement sources established")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to public statement sources: {str(e)}")
            self._connected = False
            return False

    def authenticate(self) -> bool:
        """
        Authenticate with the public statement sources.
        Note: Many RSS feeds are public; some APIs might require keys, but we assume RSS where possible.

        Returns:
            True (assuming no authentication needed for RSS feeds; if API keys are needed, they'd be in config)
        """
        self.logger.info("Public statement sources (RSS) do not require authentication for public access")
        self._authenticated = True
        return True

    def health_check(self) -> bool:
        """
        Check if the connection to the public statement sources is healthy by making a simple request to the first feed.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self._connected or not self._session or not self.feeds:
            return False

        try:
            # Check the health of the first feed in the list
            first_feed = self.feeds[0]
            url = first_feed.get('url')
            if not url:
                return False

            response = self._session.get(url, timeout=self.timeout)
            # Consider 200 OK as healthy
            is_healthy = response.status_code == 200
            if is_healthy:
                self.logger.debug("Public statement source health check passed")
            else:
                self.logger.warning(f"Public statement source health check failed with status {response.status_code}")
            return is_healthy
        except RequestException as e:
            self.logger.error(f"Public statement source health check failed: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during public statement source health check: {str(e)}")
            return False

    def fetch(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve data from the public statement sources based on query parameters.

        Args:
            query: Dictionary containing query parameters
                  Expected keys: 'feeds_to_fetch' (optional list of feed names to fetch, defaults to all),
                                 'since' (optional datetime to filter entries published after this time)

        Returns:
            List of dictionaries containing the retrieved feed entries
        """
        if not self.is_connected or not self._session:
            self.connect()
            self.authenticate()

        entries = []
        feeds_to_process = self.feeds

        # If specific feeds are requested, filter by name
        if 'feeds_to_fetch' in query:
            requested_names = set(query['feeds_to_fetch'])
            feeds_to_process = [f for f in self.feeds if f.get('name') in requested_names]

        # Parse the 'since' parameter if provided
        since_time = None
        if 'since' in query:
            since_time = query['since']
            if isinstance(since_time, str):
                try:
                    since_time = datetime.fromisoformat(since_time.replace('Z', '+00:00'))
                except ValueError:
                    self.logger.warning(f"Could not parse 'since' parameter: {since_time}")
                    since_time = None

        try:
            for feed_config in feeds_to_process:
                feed_name = feed_config.get('name', 'Unknown Feed')
                feed_url = feed_config.get('url')
                if not feed_url:
                    self.logger.warning(f"Feed '{feed_name}' has no URL, skipping")
                    continue

                self.logger.info(f"Fetching public statement feed: {feed_name} from {feed_url}")

                # Apply rate limiting
                time.sleep(self.rate_limit_delay)

                # Fetch the feed
                response = self._session.get(feed_url, timeout=self.timeout)
                response.raise_for_status()

                # Parse the feed
                feed = feedparser.parse(response.content)

                if feed.bozo:
                    self.logger.warning(f"Feed {feed_name} may be malformed: {feed.bozo_exception}")

                # Process each entry
                for entry in feed.entries:
                    # Parse the publication date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6])
                    else:
                        pub_date = datetime.now()

                    # Filter by 'since' time if provided
                    if since_time and pub_date < since_time:
                        continue

                    # Prepare the entry data
                    entry_data = {
                        'title': getattr(entry, 'title', ''),
                        'summary': getattr(entry, 'summary', '') or getattr(entry, 'description', ''),
                        'link': getattr(entry, 'link', ''),
                        'published': pub_date.isoformat() if pub_date else None,
                        'author': getattr(entry, 'author', ''),
                        'tags': [tag.term for tag in getattr(entry, 'tags', [])] if hasattr(entry, 'tags') else [],
                        'feed_name': feed_name,
                        'source_name_override': feed_config.get('source_name_override')
                    }
                    entries.append(entry_data)

                self.logger.info(f"Retrieved {len(feed.entries)} entries from {feed_name}")

            self.logger.info(f"Total entries retrieved from public statement feeds: {len(entries)}")
            return entries

        except RequestException as e:
            self.logger.error(f"Request to public statement feeds failed: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching data from public statement feeds: {str(e)}")
            return []

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedPolicyEvent:
        """
        Normalize retrieved public statement feed entry to the NormalizedPolicyEvent schema.

        Args:
            raw_data: Dictionary containing raw public statement feed entry data

        Returns:
            NormalizedPolicyEvent object containing normalized policy event data
        """
        try:
            # Extract fields from the feed entry
            title = raw_data.get('title', '')
            summary = raw_data.get('summary', '')
            link = raw_data.get('link', '')
            published_str = raw_data.get('published')
            author = raw_data.get('author', '')
            feed_name = raw_data.get('feed_name', 'Public Statement Feed')
            source_name_override = raw_data.get('source_name_override')

            # Determine source_name: use override if provided, otherwise use feed name
            # For social media, we might want to show the platform and author (e.g., "LinkedIn: Rohit Chopra")
            source_name = source_name_override if source_name_override else feed_name

            # Parse publication date
            try:
                if published_str:
                    event_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                else:
                    event_date = datetime.now()
            except ValueError:
                event_date = datetime.now()

            # Determine event type based on title, summary, or feed name
            title_lower = title.lower()
            summary_lower = summary.lower()
            feed_name_lower = feed_name.lower()
            if 'newsletter' in title_lower or 'newsletter' in summary_lower or 'newsletter' in feed_name_lower:
                event_type = 'Newsletter'
            elif 'tweet' in title_lower or 'tweet' in summary_lower or 'twitter' in feed_name_lower or 'x.com' in feed_name_lower:
                event_type = 'Social Post'
            elif 'linkedin' in feed_name_lower or 'linkedin' in title_lower or 'linkedin' in summary_lower:
                event_type = 'Social Post'
            elif 'facebook' in feed_name_lower or 'facebook' in title_lower or 'facebook' in summary_lower:
                event_type = 'Social Post'
            else:
                # Default to Social Post for public statements from social media
                event_type = 'Social Post'

            # Extract people/policymaker names from author or title
            people = []
            if author:
                # Clean up author string (might contain extra info)
                author_clean = author.strip()
                if author_clean:
                    people.append(author_clean)
            # Also try to extract from title if it contains a name pattern (simple approach)
            # This is a basic extraction - could be enhanced with NLP
            if not people and title:
                # Look for patterns like "Sen. Name", "Rep. Name", etc.
                import re
                # Pattern for senator/representative titles
                patterns = [
                    r'Sen\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
                    r'Senator\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
                    r'Rep\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
                    r'Representative\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
                    r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+\([D-R]\)'  # Name (party)
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, title)
                    if matches:
                        people.extend(matches)
                        break

            # If still no people found, use the feed name as a fallback for organization
            organizations = []
            if not people and feed_name:
                # Treat feed name as organization if no specific person found
                organizations.append(feed_name)

            # Create normalized event
            normalized_event = NormalizedPolicyEvent(
                source_name=source_name,
                source_type="Public_Post",
                jurisdiction="Federal",  # Assuming federal level for now; could be enhanced
                title=title,
                summary=summary.strip() if summary else title,
                event_type=event_type,
                event_date=event_date,
                url=link,
                organizations=organizations,
                people=people,
                committees=[],  # Could be extracted from title/summary if needed
                agencies=[],    # Could be extracted if mentioned
                legislation=[], # Could be extracted if mentioned
                topics=[],      # Could be extracted from tags/categories
                keywords=raw_data.get('tags', []),  # Use tags as keywords
                confidence=0.75,  # Good confidence for official public statements
                evidence=f"Source: {feed_name}; Author: {author}; Published: {published_str}",
                raw_payload=raw_data
            )

            return normalized_event

        except Exception as e:
            self.logger.error(f"Error normalizing public statement feed entry: {str(e)}")
            # Return a minimal valid normalized event in case of error
            from datetime import datetime
            return NormalizedPolicyEvent(
                source_name="Unknown Public Statement Source",
                source_type="Public_Post",
                jurisdiction="Federal",
                title="Error processing public statement",
                summary=f"Failed to normalize public statement: {str(e)}",
                event_type="error",
                event_date=datetime.now(),
                url="",
                organizations=[],
                people=[],
                committees=[],
                agencies=[],
                legislation=[],
                topics=[],
                keywords=[],
                confidence=0.0,
                evidence=f"Error: {str(e)}",
                raw_payload=raw_data
            )

    def incremental_sync(self) -> Dict[str, Any]:
        """
        Perform incremental synchronization since last checkpoint.
        We'll store the last seen publication date per feed to avoid duplicates.

        Returns:
            Dictionary containing new data and updated checkpoint
        """
        self.logger.info("Performing incremental sync for public statement connector")

        # Retrieve the current state (checkpoint) for this connector
        cursor = self.checkpoint_manager.get_cursor(self.__class__.__name__)

        # We'll store a dictionary of last_seen dates per feed name
        last_seen_per_feed = cursor.get('last_seen_per_feed', {})

        # Determine the earliest date we need to consider (oldest last_seen)
        # If we have no history, we'll fetch recent entries (default to last 24 hours)
        since_time = None
        if last_seen_per_feed:
            # We'll pass the last_seen_per_feed to the fetch method via query
            pass  # We'll handle per-feed filtering in fetch

        # Build query for incremental sync
        query = {}
        # We'll pass the last_seen_per_feed to the feed processing logic
        query['last_seen_per_feed'] = last_seen_per_feed

        # Fetch new data (returns list of entries)
        raw_data_list = self.fetch(query)

        # Update the last_seen_per_feed with the latest publication date from this batch
        new_last_seen_per_feed = last_seen_per_feed.copy()
        for entry in raw_data_list:
            feed_name = entry.get('feed_name')
            pub_date_str = entry.get('published')
            if feed_name and pub_date_str:
                try:
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                    # Keep the latest date for each feed
                    if feed_name not in new_last_seen_per_feed or pub_date > new_last_seen_per_feed[feed_name]:
                        new_last_seen_per_feed[feed_name] = pub_date
                except ValueError:
                    pass  # Skip if date parsing fails

        # Save the updated checkpoint
        new_cursor = {"last_seen_per_feed": {k: v.isoformat() for k, v in new_last_seen_per_feed.items()}}
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
            True if shutdown successful, False otherwise
        """
        try:
            self.logger.info("Shutting down public statement connector")
            if self._session:
                self._session.close()
                self._session = None
            self._connected = False
            self._authenticated = False
            self.logger.info("Public statement connector shut down successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during public statement connector shutdown: {str(e)}")
            return False