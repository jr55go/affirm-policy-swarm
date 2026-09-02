import json
import os
from typing import Dict, Any


class ConnectorCheckpointManager:
    """Manages persistent checkpoints for connectors to enable incremental synchronization."""

    def __init__(self, checkpoint_file: str = "infrastructure/connectors/checkpoints.json"):
        """Initialize the checkpoint manager with a JSON file path.
        
        Args:
            checkpoint_file: Path to the JSON file storing checkpoints.
        """
        self.checkpoint_file = checkpoint_file
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.checkpoint_file), exist_ok=True)
        # If the file doesn't exist, create an empty JSON object
        if not os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'w') as f:
                json.dump({}, f)

    def get_cursor(self, source_name: str) -> Dict[str, Any]:
        """Retrieve the last saved state for a given source.
        
        Args:
            source_name: Name of the connector/source (e.g., 'federal_register').
            
        Returns:
            Dictionary containing cursor data (e.g., {'last_timestamp': '...', 'last_id': '...'}).
            Returns empty dict if no cursor exists.
        """
        try:
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
            return data.get(source_name, {})
        except (json.JSONDecodeError, FileNotFoundError):
            # If file is corrupted or missing, reset to empty dict and return empty
            with open(self.checkpoint_file, 'w') as f:
                json.dump({}, f)
            return {}

    def save_cursor(self, source_name: str, cursor_data: Dict[str, Any]) -> None:
        """Save cursor data for a given source, updating the JSON file safely.
        
        Args:
            source_name: Name of the connector/source.
            cursor_data: Dictionary containing cursor data to save.
        """
        try:
            # Read existing data
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {}
        
        # Update the specific source's checkpoint
        data[source_name] = cursor_data
        
        # Write back to file
        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2)