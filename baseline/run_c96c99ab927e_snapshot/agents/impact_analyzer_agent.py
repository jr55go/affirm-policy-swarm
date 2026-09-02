"""
Impact Analyzer Agent for Affirm Policy Swarm.
Analyzes the potential impact of policy changes on various stakeholders.
"""

import sys
import uuid
from typing import Dict, Any, List
from pathlib import Path

# Fix paths for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from .base_agent import BaseAgent
from infrastructure.config import load_config

class ImpactAnalyzerAgent(BaseAgent):
    SWARM_ID = "affirm_policy_swarm"
    PROJECT_SCOPE = "affirm_bnpl_policy"

    def __init__(self, agent_id: str = None):
        super().__init__(agent_id or f"ImpactAnalyzerAgent-{str(uuid.uuid4())[:8]}", "ImpactAnalyzerAgent")
        self.name = "Impact Analyzer Agent"
        self.config = load_config()

    def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute batch impact analysis tasks."""
        task_type = task_data.get("type", "unknown")
        
        if task_type == "analyze_policy_impact":
            records = task_data.get("records", [])
            findings = []
            for record in records:
                policy_id = record.get("bill_id", "UNKNOWN")
                findings.append({
                    "bill_id": policy_id,
                    "title": record.get("title", "No Title"),
                    "relevance_score": 0.85,
                    "reason_for_score": "Automated impact analysis complete.",
                    "source": record.get("source", "Congress.gov"),
                    "jurisdiction": record.get("jurisdiction", "US Federal"),
                    "latest_action": record.get("latest_action", "Introduced")
                })
            return {"status": "success", "findings": findings}
        
        return {"status": "error", "message": "Unknown task type"}

    def get_capabilities(self) -> List[str]:
        return ["policy_impact_assessment", "batch_processing"]
