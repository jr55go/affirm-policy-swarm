class ConnectorCache:
    """A simple in-memory cache for deduplication of records."""

    def __init__(self):
        self._cache = set()

    def is_cached(self, record_id: str) -> bool:
        """Check if a record ID is already in the cache.

        Args:
            record_id: The unique identifier for a record.

        Returns:
            bool: True if the record ID is in the cache, False otherwise.
        """
        return record_id in self._cache

    def add_to_cache(self, record_id: str) -> None:
        """Add a record ID to the cache.

        Args:
            record_id: The unique identifier for a record.
        """
        self._cache.add(record_id)

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)