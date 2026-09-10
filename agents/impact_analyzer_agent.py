import json
import re
import requests
import sys
import os
sys.path.append(os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm'))
from infrastructure.audit_logger import compliance_log

class ImpactAnalyzerAgent:
    def __init__(self, agent_id="ImpactAnalyzerAgent"):
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

    def _clean_text(self, val):
        if isinstance(val, dict):
            return " ".join([f"{k}: {v}" if isinstance(v, str) else str(v) for k, v in val.items()])
        if isinstance(val, str):
            # Strip embedded JSON strings if present
            if val.strip().startswith("{") and val.strip().endswith("}"):
                try:
                    parsed_dict = json.loads(val)
                    if isinstance(parsed_dict, dict):
                        return " ".join([f"{k}: {v}" for k, v in parsed_dict.items() if isinstance(v, str)])
                except Exception:
                    pass
            return re.sub(r"[\{\}\"']", '', val).strip()
        return str(val)

    def _parse_llm_response(self, response_text):
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                data = json.loads(json_str)
                return {
                    "impact_score": str(data.get("impact_score", "medium")).lower(),
                    "explicit_source_facts": self._clean_text(data.get("explicit_source_facts", "")),
                    "inferred_market_impact": self._clean_text(data.get("inferred_market_impact", "")),
                    "impact_fallback": False,
                }
            return json.loads(response_text)
        except Exception as e:
            print(f"[{self.agent_id}] JSON Truncation or formatting issue detected: {e}. Cleaning raw text...")
            return {
                "impact_score": "medium", 
                "explicit_source_facts": "Document analysis extracted directly from raw context.",
                "inferred_market_impact": self._clean_text(response_text),
                "impact_fallback": True,
            }

    def execute_task(self, payload):
        records = payload.get("records", [])
        analyzed_records = []
        
        print(f"[{self.agent_id}] Analyzing {len(records)} records with LLM...")
        
        for idx, item in enumerate(records):
            full_context = item.get("text_context", "") or item.get("full_text", "") or item.get("snippet", "")
            context = full_context[:3500] 
            title = item.get("title", "")
            jurisdiction = item.get("jurisdiction", "")

            print(f"[{self.agent_id}] Processing record {idx + 1}/{len(records)}: {title[:40]}...")

            prompt = f"""[CLOSED-WORLD DIRECTIVE: STRICT FACTUAL GROUNDING]
Evaluate the potential impact of the following legislative/regulatory record on the BNPL (Buy Now, Pay Later) sector.
Rely ONLY on facts in the provided text. Do NOT invent dates, bill numbers, or provisions.

Title: {title}
Context: {context}
Jurisdiction: {jurisdiction}

Output ONLY raw valid JSON:
{{
  "impact_score": "high" | "medium" | "low",
  "explicit_source_facts": "Clean string summary of explicit facts in source text.",
  "inferred_market_impact": "Clean prose analysis of BNPL market impact."
}}
""".strip()

            llm_response = self._call_ollama(prompt)
            
            if llm_response is None:
                item["impact_fallback"] = True
                text = context.lower()
                if any(term in text for term in ["bnpl", "credit", "rule", "finance", "affirm"]):
                    item["impact_score"] = "high"
                    item["explicit_source_facts"] = "Direct mention of BNPL/credit/finance regulation found in text."
                    item["inferred_market_impact"] = "Potential direct impact on BNPL sector inferred from keyword match."
                else:
                    item["impact_score"] = "low"
                    item["explicit_source_facts"] = "No specific BNPL/credit/finance terms detected in text."
                    item["inferred_market_impact"] = "No significant impact on BNPL sector inferred."
            else:
                parsed = self._parse_llm_response(llm_response)
                if parsed:
                    item["impact_score"] = parsed.get("impact_score", "medium")
                    item["explicit_source_facts"] = parsed.get("explicit_source_facts", "")
                    item["inferred_market_impact"] = parsed.get("inferred_market_impact", "")
                    item["impact_fallback"] = bool(parsed.get("impact_fallback", False))

            analyzed_records.append(item)
            
        payload["records"] = analyzed_records
        return payload
