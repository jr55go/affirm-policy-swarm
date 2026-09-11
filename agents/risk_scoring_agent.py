import re
import json
import requests
import json as json_module

class RiskScoringAgent:
    def __init__(self, agent_id="RiskScoringAgent"):
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
            # INCREASED TIMEOUT TO 300 SECONDS
            response = requests.post(self.ollama_url, json=payload, timeout=None)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            print(f"[{self.agent_id}] Error calling Ollama: {e}")
            return None

    def _score_risk_with_llm(self, finding, text, entities):
        if not text or not text.strip():
            finding["policy_risk_score"] = 0
            finding["risk_score"] = 0
            finding["alert_required"] = False
            finding["risk_reasoning"] = "No text to analyze"
            finding["risk_fallback"] = True
            return finding

        if isinstance(entities, list):
            ent_dict = {"organizations": entities, "policymakers": [], "themes": []}
        elif isinstance(entities, dict):
            ent_dict = entities
        else:
            ent_dict = {"organizations": [], "policymakers": [], "themes": []}

        orgs = ", ".join(ent_dict.get("organizations", [])) if ent_dict.get("organizations") else "none"
        policymakers = ", ".join(ent_dict.get("policymakers", [])) if ent_dict.get("policymakers") else "none"
        themes = ", ".join(ent_dict.get("themes", [])) if ent_dict.get("themes") else "none"

        prompt = f"""
You are a regulatory risk analyst. Evaluate the following policy finding for risk.

Finding Summary:
{text}

Entities Mentioned:
- Organizations: {orgs}
- Policymakers: {policymakers}
- Themes: {themes}

Rate the risk from 0 to 100. If this involves CFPB, interest rate caps, or BNPL enforcement, assign a 70+ score.

Return a strict JSON object with:
- "policy_risk_score": (integer 0-100)
- "alert_required": (boolean)
- "risk_reasoning": (string)

JSON Output:
"""
        llm_response = self._call_ollama(prompt)
        if llm_response is None:
            return self._fallback_scoring(finding, text, ent_dict)

        try:
            match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            json_str = match.group(0) if match else llm_response
            result = json_module.loads(json_str)
            score = int(result.get("policy_risk_score", result.get("risk_score", 50)))
            if not (0 <= score <= 100):
                raise ValueError("Risk score out of bounds (must be 0-100)")
            alert_raw = result.get('alert_required', score >= 80)
            if not isinstance(alert_raw, bool):
                raise TypeError("alert_required must be a strict boolean")
            alert_required = alert_raw
            reasoning = str(result.get("risk_reasoning", "Risk evaluated by LLM."))

            finding["policy_risk_score"] = score
            finding["risk_score"] = score
            finding["alert_required"] = alert_required
            finding["risk_reasoning"] = reasoning
            finding["risk_fallback"] = False
            return finding
        except Exception as e:
            print(f"[{self.agent_id}] Validation Failed: {e}. Rejecting stage.")
            finding["risk_fallback"] = True
            finding["pipelineStatus"] = "rejected"
            return finding

    def _fallback_scoring(self, finding, text, entities):
        text_lower = text.lower()
        high_risk_keywords = ["ban", "prohibit", "restrict", "investigation", "lawsuit", "fine", "cfpb", "usury", "rate cap"]
        keyword_count = sum(1 for k in high_risk_keywords if k in text_lower)
        score = min(100, 50 + (keyword_count * 10))
        finding["policy_risk_score"] = score
        finding["risk_score"] = score
        finding["alert_required"] = score >= 80
        finding["risk_reasoning"] = f"Fallback scoring: keyword_count={keyword_count}"
        finding["risk_fallback"] = True
        return finding

    def execute_task(self, payload):
        findings = payload.get("findings", [])
        scored_findings = []
        print(f"[{self.agent_id}] Scoring risk for {len(findings)} findings...")
        for finding in findings:
            text = finding.get("text_context") or finding.get("snippet") or finding.get("summary") or finding.get("title") or ""
            entities = finding.get('entities', {})
            scored = self._score_risk_with_llm(finding, text, entities)
            scored_findings.append(scored)
        return {"findings": scored_findings}
