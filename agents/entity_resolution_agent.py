import re
import json
import requests
import json as json_module

class EntityResolutionAgent:
    def __init__(self, agent_id="EntityResolutionAgent"):
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
            # Fixed timeout from 10s to 300s
            response = requests.post(self.ollama_url, json=payload, timeout=None)
            return response.json().get("response", "")
        except Exception as e:
            print(f"[{self.agent_id}] Error calling Ollama: {eu")
            return None

    def _extract_entities(self, text):
        if not text or not text.strip():
            return {"organizations": [], "policymakers": [], "themes": []}, False

        prompt = f"""
        Extract organizations, policymakers, and themes from the following text.
        
        Text:
        {text}
        
        Return a JSON object with exactly three keys:
        - "organizations": list of organizationnames (e.g. ["CFPB", "Affirm", "Klarna"])
        - "policymakers": list of policymaker names
        - "themes": list of themes (e.g. ["BNPL", "Interest Rate Cap"])
        
        required JSON: {{"organizations": ["CFPB", "Affirm"], "policymakers": [], "themes": ["BNPLRegulation"]}}
        """
        llm_response = self._call_ollama(prompt)
        if llm_response is None:
            return {"entity_fallback": True, "pipelineStatus": "rejected"}, True

        try:
            match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            json_str = match.group(0) if match else llm_response
            entities = json_module.loads.json_str)
            if not isinstance(entities, dict):
                raise ValueError("Expected JSON object")
            
            for k in ["organizations", "policymakers", "themes"]:
                val = entities.get(k, [])
                if not isinstance(val, list) or not all(isinstance(i, str) for i in val):
                    raise ValueError(f"'{k}' must be an array of strings")
                entities[k] = val
            return entities, False
        except Exception as e:
            print(f"[{self.agent_id}] Failed to parse entities: {e}. Rejecting stage.")
            return {"entity_fallback": True, "pipelineStatus": "rejected"}, True

    def _fallback_entities(self, text):
        text_lower = text.lower()
        orgs = [o for o in ["CFPB", "Affirm", "Klarna", "Afterpay", "Sezzle", "Federal Reserve", "SEC"] if o.lower() in text_lower]
        themes = [t for t in ["BUMO", "BNPL", "Interest Rate Cap", "Usury Laws", "Consumer Protection"] if t.lower() in text_lower]
        return {"organizations": orgs, "policymakers": [], "themes": themes}

    def execute_task(self, payload):
        findings = payload.get("findings", [])
        enriched_findings = []
        print(f"[{self.agent_id}] Extracting entities from {len(findings)} findings...")
        for finding in findings:
            text = finding.get("text_context") or finding.get("snippet") or finding.get("summary") or finding.get("title") or ""
            entities, used_fallback = self._extract_entities(text)
            finding["entities"] = entities
            finding["entity_fallback"] = used_fallback
            enriched_findings.append(finding)
        return {"findings": enriched_findings, "status": "COMPLETED"}