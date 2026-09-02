import json
import requests
import sys
import os
sys.path.append(os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm'))
from agents.legislative_enricher import LegislativeEnricher

class BillScoringAgent:
    def __init__(self, agent_id="BillScoringAgent"):
        self.agent_id = agent_id
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "nemotron:70b"
        self.enricher = LegislativeEnricher()

    def _call_ollama(self, prompt):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=120)
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
            return {"is_legislation": False, "passage_probability_percentage": 0}

    def execute_task(self, payload):
        findings = payload.get("findings", [])
        scored_findings = []
        
        print(f"[{self.agent_id}] Running Data-Backed Prognosis Model on {len(findings)} records...")
        
        for finding in findings:
            title = finding.get("title", "")
            source_context = finding.get("text_context", "") or finding.get("full_text", "") or finding.get("snippet", "")
            
            # Pull live data via our new Enricher
            hard_data = self.enricher.enrich(source_context)
            data_injection = f"Live Bill Data: {json.dumps(hard_data)}" if "error" not in hard_data else "No live metadata retrieved."
            
            prompt = f"""You are an elite Legislative Prognosis Algorithm.
Calculate the exact probability of this item passing into law using the provided text and LIVE enriched API data.

[System State]
Target: {title}
Context: {source_context[:2500]}
{data_injection}

If the target is NOT a legislative bill or resolution, set "is_legislation" to false and return 0s. 

If it IS legislation, score these dimensions (0-10) using the context and live API data:
1. Sponsor & Leadership (Use the 'sponsor_historical_les_score' provided)
2. Bipartisanship & Coalition Support (Use the 'live_cosponsors' count provided)
3. Committee & Procedural Path
4. Bill Content & Type
5. Institutional & Political Context
6. External Momentum & Environment

Base passage rate is ~3%. Adjust the final passage_probability_percentage (1-100) based on these weighted dimensions.

Output ONLY valid JSON matching this schema:
{{
  "is_legislation": <bool>,
  "dimension_scores": {{
    "sponsor_leadership": <int 0-10>,
    "bipartisanship": <int 0-10>,
    "procedural_path": <int 0-10>,
    "content_type": <int 0-10>,
    "institutional_context": <int 0-10>,
    "external_momentum": <int 0-10>
  }},
  "passage_probability_percentage": <int 0-100>,
  "key_drivers": ["<String factor 1>", "<String factor 2>"],
  "prognosis_summary": "<One sentence justification>"
}}
""".strip()

            llm_response = self._call_ollama(prompt)
            parsed = self._parse_llm_response(llm_response)
            
            if parsed and isinstance(parsed, dict):
                is_leg = parsed.get("is_legislation", False)
                finding["is_legislation"] = is_leg
                finding["passage_probability"] = parsed.get("passage_probability_percentage", 0)
                finding["prognosis_data"] = parsed
                
                if is_leg:
                    prob = finding["passage_probability"]
                    print(f"[{self.agent_id}] 🏛️ BILL DETECTED | Odds: {prob}% | Sponsors: {hard_data.get('live_cosponsors', 'Unknown')} | LES: {hard_data.get('sponsor_historical_les_score', 'Unknown')}")
                
            scored_findings.append(finding)

        return {"findings": scored_findings}
