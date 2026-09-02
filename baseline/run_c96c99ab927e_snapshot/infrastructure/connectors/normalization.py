"""
Normalization Schema: Reusable data model for normalized policy events.
Defines the standard format that all source connectors will output.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class NormalizedPolicyEvent:
    """
    Standardized data structure for policy events from any source.
    All connectors should output events in this format.
    """
    
    # Source identification
    source_name: str
    source_type: str  # e.g., 'congress_gov', 'legiscan', 'state_legislature'
    
    # Event classification
    jurisdiction: str  # e.g., 'federal', 'california', 'new_york'
    title: str
    summary: str
    event_type: str  # e.g., 'bill_introduced', 'bill_passed', 'hearing_scheduled'
    event_date: datetime
    url: str  # Link to the original source
    
    # Related entities
    organizations: list = field(default_factory=list)
    agencies: list = field(default_factory=list)
    committees: list = field(default_factory=list)
    legislators: list = field(default_factory=list)
    
    # Metadata
    keywords: list = field(default_factory=list)
    confidence: float = 1.0  # Confidence score of the normalization (0.0 to 1.0)
    raw_payload: dict = field(default_factory=dict)  # Original source data