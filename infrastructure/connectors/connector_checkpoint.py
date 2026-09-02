import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class CheckpointManager:
    """Manages checkpoint state for incremental synchronization."""

    def __init__(self, storage_path: str = "infrastructure/connectors/checkpoints.json"):
        self.storage_path = Path(storage_path)
        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        """Ensure the storage file and directory exist."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._write_checkpoints({})

    def _read_checkpoints(self) -> Dict[str, Any]:
        """Read all checkpoints from storage.
        
        Returns:
            Dict[str, Any]: Dictionary containing all checkpoint data
        """
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # If file is corrupted or missing, start fresh
            return {}

    def _write_checkpoints(self, data: Dict[str, Any]) -> None:
        """Write all checkpoints to storage.
        
        Args:
            data: Dictionary containing all checkpoint data to write
        """
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_cursor(self, source_name: str) -> Dict[str, Any]:
        """Get checkpoint data for a specific source.
        
        Args:
            source_name: Name of the data source
            
        Returns:
            Dict[str, Any]: Checkpoint data for the source, or empty dict if none exists
        """
        all_checkpoints = self._read_checkpoints()
        return all_checkpoints.get(source_name, {})

    def save_cursor(self, source_name: str, checkpoint_data: Dict[str, Any]) -> None:
        """Save checkpoint data for a specific source.
        
        Args:
            source_name: Name of the data source
            checkpoint_data: Data to save for the source
        """
        all_checkpoints = self._read_checkpoints()
        all_checkpoints[source_name] = checkpoint_data
        self._write_checkpoints(all_checkpoints)

    def get_last_cursor(self, source_name: str) -> Optional[str]:
        """Get the last cursor value for a source.
        
        Args:
            source_name: Name of the data source
            
        Returns:
            Optional[str]: The last cursor value, or None if not set
        """
        checkpoint = self.get_cursor(source_name)
        return checkpoint.get("last_cursor")

    def get_last_timestamp(self, source_name: str) -> Optional[str]:
        """Get the last timestamp for a source.
        
        Args:
            source_name: Name of the data source
            
        Returns:
            Optional[str]: The last timestamp, or None if not set
        """
        checkpoint = self.get_cursor(source_name)
        return checkpoint.get("last_timestamp")

    def get_last_record_id(self, source_name: str) -> Optional[str]:
        """Get the last record ID for a source.
        
        Args:
            source_name: Name of the data source
            
        Returns:
            Optional[str]: The last record ID, or None if not set
        """
        checkpoint = self.get_cursor(source_name)
        return checkpoint.get("last_record_id")

    def get_last_successful_sync(self, source_name: str) -> Optional[str]:
        """Get the last successful sync time for a source.
        
        Args:
            source_name: Name of the data source
            
        Returns:
            Optional[str]: The last successful sync time, or None if not set
        """
        checkpoint = self.get_cursor(source_name)
        return checkpoint.get("last_successful_sync")

    def get_retry_count(self, source_name: str) -> int:
        """Get the retry count for a source.
        
        Args:
            source_name: Name of the data source
            
        Returns:
            int: The retry count, or 0 if not set
        """
        checkpoint = self.get_cursor(source_name)
        return checkpoint.get("retry_count", 0)
ConnectorCheckpointManager = CheckpointManager
