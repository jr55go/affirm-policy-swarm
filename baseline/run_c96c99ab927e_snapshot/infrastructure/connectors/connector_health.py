"""
Connector Health Model: Reusable state object for reporting connector operational status.
Defines standard health states and health reporting format for connectors.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Union, Optional
from datetime import datetime


class ConnectorHealthState(Enum):
    """
    Enumeration of possible health states for a connector.
    """
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    OFFLINE = "OFFLINE"
    AUTH_FAILED = "AUTH_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    SCHEMA_CHANGED = "SCHEMA_CHANGED"
    RETRYING = "RETRYING"
    TIMEOUT = "TIMEOUT"


@dataclass
class ConnectorHealth:
    """
    Standardized health status structure for reporting connector operational status.
    Connectors should report health using this format.
    """
    
    source_name: str
    state: ConnectorHealthState
    last_checked: Union[datetime, str]
    details: Optional[str] = None