import os
import json
import logging
from infrastructure.audit_logger import compliance_log

logger = logging.getLogger(__name__)

class ValidationAgent:
    def __init__(self, agent_id="ValidationAgent"):
        self.agent_id = agent_id

    def _call_ollama(self, prompt):
        # Stub or existing model call wrapper
        try:
            from infrastructure.config import LLMClient
            return LLMClient().complete(prompt)
        except Exception:
            return None

    def _parse_llm_response(self, response_text):
        try:
            if not response_text:
                return None
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception:
            return None

    def execute_task(self, payload):
        findings = payload.get("findings", [])
        validated_findings = []
        
        logger.info(f"[{self.agent_id}] Auditing {len(findings)} findings with Phase 0 strict fail-closed gates...")
        
        for finding in findings:
            title = finding.get("title", "")
            source_content = finding.get("source_content", "") or finding.get("text_context", "")
            url = finding.get("url", "")
            
            # Phase 0 Precondition: Fail closed if missing locator or source body
            if not url or not source_content:
                finding["validation_status"] = "rejected"
                finding["validation_reason"] = "Phase 0 Rejection: Missing canonical locator (url) or source content."
                finding["validation_fallback"] = True
                self._log_rejection(title, finding["validation_reason"])
                continue

            prompt = f"""You are a strict Policy Auditor enforcing Phase 0 governance.
Verify that the Inferred Analysis is strictly grounded in the Source Body.

Rules:
1. If the analysis contains claims, dates, or facts not present in the Source Body, output "rejected".
2. You MUST provide exact matching quote spans from the source body.
3. Output ONLY valid JSON with keys: "validation_status" ("approved" or "rejected"), "validation_reason" (string), "span" (string).

Source Body: {source_content[:2500]}
Inferred Analysis: {finding.get('inferred_market_impact', '')[:1500]}

JSON Output:
{{
  "validation_status": "approved" or "rejected",
  "validation_reason": "...",
  "span": "..."
}}
""".strip()

            llm_response = self._call_ollama(prompt)
            
            if llm_response is None:
                finding["validation_status"] = "rejected"
                finding["validation_reason"] = "Phase 0 Rejection: LLM timeout or failure (fail-closed)."
                finding["validation_fallback"] = True
            else:
                parsed = self._parse_llm_response(llm_response)
                if parsed and isinstance(parsed, dict):
                    v_status = str(parsed.get("validation_status", "")).strip().lower()
                    v_reason = str(parsed.get("validation_reason", "")).strip()
                    v_span = str(parsed.get("span", "")).strip()
                    
                    # Strict schema and exact enum check
                    if v_status == "approved" and v_reason and v_span and v_span in source_content:
                        finding["validation_status"] = "approved"
                        finding["validation_reason"] = v_reason
                    else:
                        finding["validation_status"] = "rejected"
                        finding["validation_reason"] = "Phase 0 Rejection: Invalid schema, unverified span, or non-approved status."
                        finding["validation_fallback"] = True
                else:
                    finding["validation_status"] = "rejected"
                    finding["validation_reason"] = "Phase 0 Rejection: Unparseable LLM response structure."
                    finding["validation_fallback"] = True

            if finding.get("validation_status") == "rejected":
                self._log_rejection(title, finding.get("validation_reason"))
            else:
                validated_findings.append(finding)

        return validated_findings

    def _log_rejection(self, title, reason):
        logger.info(f"[{self.agent_id}] ❌ REJECTED: {title} — {reason}")
        try:
            compliance_log.log_action(
                agent_id=self.agent_id,
                action_type="Validation Failed",
                payload_title=title,
                reasoning=reason,
                disposition="Rejected & Dropped"
            )
        except Exception:
            pass
