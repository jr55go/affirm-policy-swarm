"""
Judicial Monitor Agent for the Affirm Policy Swarm.
Responsible for tracking court cases and judicial decisions.
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from .base_agent import BaseAgent
from infrastructure.config import load_config
from infrastructure.database import neo4j_session


class JudicialMonitorAgent(BaseAgent):
    SWARM_ID = "affirm_policy_swarm"
    PROJECT_SCOPE = "affirm_bnpl_policy"
    """Judicial Monitor Agent for tracking judicial decisions."""
    
    def __init__(self, agent_id: str = None):
        super().__init__(agent_id or f"judicial-monitor-{str(uuid.uuid4())[:8]}", "Judicial Monitor Agent")
        self.config = load_config()
        
    def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute judicial monitoring tasks."""
        task_type = task_data.get("type", "unknown")
        
        self.log_thought(f"Judicial Monitor agent received task: {task_type}")
        
        if task_type == "judicial_monitoring":
            return self._judicial_monitoring(task_data)
        else:
            return {
                "status": "error",
                "message": f"Unknown task type: {task_type}",
                "agent_id": self.agent_id
            }
            
    def _judicial_monitoring(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Return an honest skipped state until a production court-data connector is configured."""
        jurisdiction = task_data.get("jurisdiction", "US Federal")
        product = task_data.get("product", "Buy Now, Pay Later")
        lookback_hours = task_data.get("lookback_hours", 24)
        self.log_thought(f"Skipping judicial monitoring for {product} in {jurisdiction}: no production connector")
        return {
            "status": "skipped",
            "agent_id": self.agent_id,
            "jurisdiction": jurisdiction,
            "product": product,
            "lookback_hours": lookback_hours,
            "records": [],
            "reason": "No production court-data connector is configured.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    def _store_judicial_result(self, item: Dict[str, Any], jurisdiction: str, product: str) -> bool:
        """Store judicial monitoring results in Neo4j graph."""
        if not self.neo4j_driver:
            self.logger.warning("Neo4j driver not available for storing results")
            return False
            
        try:
            with neo4j_session() as session:
                # Create or update judicial record
                query = """
                MERGE (j:JudicialCase {
                    case_id: $case_id
                    swarm_id: $swarm_id,
                    project_scope: $project_scope,
                })
                SET j.title = $title,
                    j.court = $court,
                    j.filed_date = $filed_date,
                    j.judge = $judge,
                    j.claims = $claims,
                    j.status = $status,
                    j.url = $url,
                    j.relevance_score = $relevance_score,
                    j.updated_at = $timestamp
                RETURN j.node_id as node_id
                """
                result = session.run(query, 
                                   case_id=item['case_id'],
                                   title=item['title'],
                                   court=item['court'],
                                   filed_date=item['filed_date'],
                                   judge=item['judge'],
                                   claims=item['claims'],
                                   status=item['status'],
                                   url=item['url'],
                                   relevance_score=item['relevance_score'],
                                   swarm_id=self.SWARM_ID,
                                   project_scope=self.PROJECT_SCOPE,
                                   timestamp=datetime.now(timezone.utc).isoformat())
                record = result.single()
                
                if record:
                    # Connect to Affirm target node if it exists
                    connect_query = """
                    MATCH (j {node_id: $node_id, swarm_id: $swarm_id, project_scope: $project_scope})
                    MATCH (affirm:Target {name: 'Affirm'})
                    WHERE affirm.node_id IS NOT NULL
                    MERGE (j)-[r:RELATED_TO]->(affirm)
                    SET r.relationship_type = 'judicial_case',
                        r.created_at = $timestamp
                    """
                    session.run(connect_query, node_id=record['node_id'], 
                              timestamp=datetime.now(timezone.utc).isoformat())
                    self.logger.debug(f"Stored judicial case {item['case_id']} in Neo4j")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Error storing judicial result: {e}")
            return False
            
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this agent provides."""
        return [
            "judicial_monitoring",
            "case_tracking",
            "legal_research",
            "court_database_querying",
            "deduplication_enforcement",
            "graph_database_storage"
        ]


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    agent = JudicialMonitorAgent()
    
    # Test judicial monitoring
    result = agent.execute_task({
        "type": "judicial_monitoring",
        "jurisdiction": "US Federal",
        "product": "Buy Now, Pay Later",
        "lookback_hours": 24
    })
    
    print("Judicial monitoring result:")
    print(f"Status: {result['status']}")
    print(f"Jurisdiction: {result.get('jurisdiction')}")
    print(f"Product: {result.get('product')}")
    print(f"Judicial item: {result.get('judicial_item', {}).get('title')}")
