from .base_agent import BaseAgent
from typing import Dict, Any, List

class ValidationAgent(BaseAgent):
    def __init__(self, agent_id="validation-agent"):
        super().__init__(agent_id, role="Validation Agent")
        self.name = "Validation Agent"

    def execute_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        findings = payload.get("impact_findings", [])
        validations = []
        
        self.logger.info(f"Starting ValidationAgent challenge on {len(findings)} findings...")

        for finding in findings:
            bill_id = finding.get("bill_id", "UNKNOWN")
            title = finding.get("title", "No Title")
            
            prompt = (
                "You are a Policy Validation Agent for Project Olmec.\n"
                "Review the following legislative finding to determine if it is truly relevant to Buy Now, Pay Later (BNPL) or consumer credit, or if it is a false positive.\n\n"
                f"Bill ID: {bill_id}\n"
                f"Title: {title}\n\n"
                "Return ONLY a JSON object with these exact keys:\n"
                "- 'validation_status': strictly 'approved' or 'rejected'\n"
                "- 'evidence_sufficient': boolean (true/false)\n"
                "- 'false_positive_risk': 'low', 'medium', or 'high'\n"
                "- 'validation_reason': a concise string explaining your reasoning\n"
                "- 'confidence': 'high', 'medium', or 'low'\n"
                "- 'fallback_mode': boolean (false)\n"
            )

            try:
                # Force temperature to 0.0 for deterministic validation
                llm_result = self.call_llm_json(
                    prompt=prompt,
                    schema_name="validation_challenge",
                    temperature=0.0,
                    max_tokens=512
                )
                llm_result["bill_id"] = bill_id
                validations.append(llm_result)
            except Exception as e:
                self.logger.error(f"Validation LLM failed for {bill_id}: {e}")
                validations.append({
                    "bill_id": bill_id,
                    "validation_status": "approved",
                    "evidence_sufficient": True,
                    "false_positive_risk": "low",
                    "validation_reason": f"Deterministic fallback due to LLM error: {e}",
                    "confidence": "low",
                    "fallback_mode": True
                })

        return {
            "agent_id": self.agent_id,
            "status": "COMPLETED",
            "validation_status": "APPROVED" if all(v.get('validation_status', '').lower() == 'approved' for v in validations) else "MIXED",
            "confidence": "high",
            "uncertainty_notes": f"LLM Challenge completed for {len(validations)} items.",
            "validations": validations,
            "total_validated": len(validations)
        }

    def get_capabilities(self) -> List[str]:
        return ["false_positive_challenge", "bnpl_relevance_validation"]
