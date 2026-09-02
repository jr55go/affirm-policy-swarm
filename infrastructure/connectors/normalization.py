from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class NormalizedPolicyEvent:
    """Standardized representation of a policy event across all sources."""
    
    source_name: str
    source_type: str
    jurisdiction: str
    title: str
    summary: str
    event_type: str
    event_date: datetime
    url: str
    organization: List[str]
    people: List[str]
    committees: List[str]
    agencies: List[str]
    legislation: List[str]
    topics: List[str]
    keywords: List[str]
    confidence: float
    evidence: str
    raw_payload: Dict[str, Any]
    connector_version: str
    collected_at: datetime
    human_review_status: Optional[str] = None  # accept, reject, monitor, escalate, false_positive, needs_research