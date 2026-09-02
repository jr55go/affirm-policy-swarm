from .base_agent import BaseAgent
from typing import Dict, Any, List

class ResearchSynthesisAgent(BaseAgent):
    def __init__(self, agent_id="research-synthesis"):
        super().__init__(agent_id, role="Research Synthesis Agent")
        self.name = "Research Synthesis Agent"

    def execute_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        findings = payload.get("findings", payload.get("impact_findings", payload.get("impact", {}).get("findings", [])))
        
        self.logger.info(f"Starting Research Synthesis on {len(findings)} findings...")
        
        context_str = ""
        for f in findings:
            context_str += f"- {f.get('bill_id', 'Unknown')}: {f.get('title', '')}\n"
            
        if not context_str:
            context_str = "No specific legislative findings were provided for this run."

        prompt = (
            "You are the Research Synthesis Agent for Project Olmec.\n"
            "Synthesize the following regulatory findings into policy meaning.\n\n"
            f"Findings:\n{context_str}\n\n"
            "Return ONLY a JSON object with these exact keys:\n"
            "- 'executive_summary' (string)\n"
            "- 'policy_trends' (list of strings)\n"
            "- 'top_risks' (list of strings)\n"
            "- 'recommended_monitoring_actions' (list of strings)\n"
            "- 'jurisdictions_to_watch' (list of strings)"
        )

        try:
            synthesis = self.call_llm_json(
                prompt=prompt,
                schema_name="research_synthesis",
                temperature=0.3,
                max_tokens=1024
            )
        except Exception as e:
            self.logger.error(f"Synthesis LLM failed: {e}")
            synthesis = {
                "executive_summary": f"Deterministic fallback due to LLM error: {e}",
                "policy_trends": [], "top_risks": [], 
                "recommended_monitoring_actions": [], "jurisdictions_to_watch": []
            }

        return {
            "agent_id": self.agent_id,
            "status": "COMPLETED",
            "research_context_summary": synthesis.get("executive_summary", ""),
            "synthesis": synthesis
        }

    def get_capabilities(self) -> List[str]:
        return ["policy_synthesis", "trend_analysis"]
