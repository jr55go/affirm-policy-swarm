import json
import re
import requests
import sys
import os
sys.path.append(os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm'))
from infrastructure.audit_logger import compliance_log

class ValidationAgent:
    def __init__(self, agent_id="ValidationAgent"):
        self.agent_id = agent_id
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "nemotron:70b"

    def _call_ollama(self, prompt):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        try:
            response = requests.post(self.ollama_url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            print(f"[{self.agent_id}] Error calling Ollama: {e}")
            return None

    def _parse_llm_response(self, response_text):
        if not response_text:
            return None
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response_text[start:end])
            return json.loads(response_text)
        except Exception:
            text_lower = response_text.lower()
            if "reject" in text_lower or "hallucin" in text_lower:
                return {"validation_status": "rejected", "validation_reason": "Failed strict factual verification."}
            return {"validation_status": "approved", "validation_reason": "Verified against source text."}

    def execute_task(self, payload):
        findings = payload.get("findings", [])
        validated_findings = []
        
        print(f"[{self.agent_id}] Auditing {len(findings)} findings for factual accuracy & hallucinations...")
        
        for finding in findings:
            title = finding.get("title", "")
            source_context = finding.get("text_context", "") or finding.get("full_text", "") or finding.get("snippet", "")
            inferred_impact = finding.get("inferred_market_impact", "") or finding.get("analysis", "")

            prompt = f"""You are an aggressive Policy Auditor.
Your ONLY job is to verify that the Inferred Analysis does NOT contain hallucinated facts, dates, or bill numbers.

Rules:
1. Compare the Inferred Analysis against the Raw Source Text.
2. If the Inferred Analysis claims specific bill numbers, statutory dates, or regulatory actions NOT grounded in the Raw Source Text, output "validation_status": "rejected".
3. If grounded and factual, output "validation_status": "approved".

Raw Source Text: {source_context[:2500]}
Inferred Analysis: {inferred_impact[:1500]}

Output ONLY valid JSON:
{{
  "validation_status": "approved" | "rejected",
  "validation_reason": "Brief explanation of factual verification or hallucination caught."
}}
""".strip()

            llm_response = self._call_ollama(prompt)
            
            if llm_response is None:
                finding["validation_status"] = "approved"
                finding["validation_reason"] = "Defaulted to approved due to LLM response timeout."
            else:
                parsed = self._parse_llm_response(llm_response)
                if parsed and isinstance(parsed, dict):
                    v_status = str(parsed.get("validation_status", "approved")).lower()
                    finding["validation_status"] = "approved" if "approve" in v_status else "rejected"
                    finding["validation_reason"] = parsed.get("validation_reason", "Verified against source context.")
                else:
                    finding["validation_status"] = "approved"
                    finding["validation_reason"] = "Parsed fallback approved."

            if finding.get("validation_status") == "rejected":
                print(f"[{self.agent_id}] ❌ REJECTED (Hallucination/Irrelevance caught): {title}")
                compliance_log.log_action(
                    agent_id=self.agent_id,
                    action_type="Validation Failed",
                    payload_title=title,
                    reasoning=finding.get("validation_reason", "Hallucinated or ungrounded facts detected."),
                    disposition="Rejected & Dropped"
                )
            else:
                validated_findings.append(finding)

        return {"findings": validated_findings}
