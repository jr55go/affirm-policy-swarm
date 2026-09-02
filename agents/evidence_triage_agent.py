import json
import logging
import requests
import concurrent.futures

class EvidenceTriageAgent:
    """
    Parallelized Semantic AI Gatekeeper: Uses concurrent Llama 3.2 workers
    to triage 50-100 search targets in under 3 seconds with strict timeouts.
    """
    def __init__(self, model="llama3.2:latest", max_workers=3):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
        self.max_workers = max_workers

    def _classify_single_target(self, record, active_context):
        url = record.get("url", "")
        title = record.get("title", "")
        snippet = record.get("snippet", "")
        
        prompt = f"""Target: {title} | {url} | {snippet}
Active Firm Focus: {active_context}

Classify if this is a substantive policy/regulatory item HIGHLY RELEVANT to the Firm Focus (e.g., BNPL, Fintech, Lending, AI).
REJECT: unhelpful pages (homepages, directories), marketing, dictionaries, and policies entirely unrelated to the firm's focus.

JSON schema: {{"is_actionable_target": true|false, "reason": "short explanation"}}
"""

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 150  # Tight token cap for maximum speed
                    }
                },
                timeout=15  # Fast fallback timeout
            )
            
            result_json = json.loads(response.json().get("response", "{}"))
            is_actionable = result_json.get("is_actionable_target", False)
            reason = result_json.get("reason", "LLM evaluated target")
            
            if is_actionable:
                record["decision"] = "read"
                record["triage_reasoning"] = reason
                record["novelty"] = "high" if ".gov" in url else "medium"
                logging.info(f"[EvidenceTriage] READ -> {url} | Reason: {reason}")
                return record
            else:
                logging.info(f"[EvidenceTriage] SKIP -> {url} | Reason: {reason}")
                return None
                
        except Exception as e:
            # Fast fail gracefully to snippet default
            logging.warning(f"[EvidenceTriage] Fast timeout/error on {url}: {e}")
            return None

    def evaluate_targets(self, search_results, active_investigations_context):
        triaged_results = []
        logging.info(f"[EvidenceTriage] 🚀 Triaging {len(search_results)} hits in parallel using {self.max_workers} workers ({self.model})...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._classify_single_target, record, active_investigations_context) for record in search_results]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    triaged_results.append(res)
                    
        return triaged_results
