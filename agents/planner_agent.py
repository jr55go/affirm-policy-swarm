import json
import logging
import requests
import re
from datetime import datetime

class PlannerAgent:
    def __init__(self, model="nemotron:70b"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"

    def generate_plan(self, notebook_state=None, recent_brain=None):
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        notebook_context = ""
        if notebook_state and len(notebook_state) > 0:
            notebook_context = "Active Policy Threads under investigation: " + json.dumps(notebook_state)
        else:
            notebook_context = "No active threads. Focus on: BNPL, Affirm regulatory scrutiny, CFPB rulemaking, state licensing, credit reporting guidelines."
        
        feedback_context = ""
        if recent_brain and len(recent_brain) > 0:
            failures_str = "\n".join(recent_brain)
            feedback_context = "\nRECENT REJECTIONS TO AVOID:\n" + failures_str + "\n\nCRITICAL: You MUST pivot your search hypothesis immediately. DO NOT REPEAT PREVIOUS QUERIES."

        prompt = (
            "You are the Chief Regulatory Intelligence Strategist for a major consumer fintech (Affirm). Today is " + current_date + ".\n"
            "Your directive is to act as a top-tier OSINT researcher. You must formulate exactly 15 highly precise, non-obvious search engine queries to uncover emerging regulatory risks.\n\n"
            "CURRENT CONTEXT:\n"
            + notebook_context + "\n"
            + feedback_context + "\n\n"
            "OSINT STRATEGY (DISTRIBUTE YOUR 15 QUERIES ACROSS THESE 4 VECTORS):\n"
            "1. Federal Regulatory (e.g., site:consumerfinance.gov, site:ftc.gov)\n"
            "2. State Legislative (e.g., site:dfs.ny.gov, site:dfpi.ca.gov)\n"
            "3. Academic/Think Tanks (e.g., site:brookings.edu, filetype:pdf)\n"
            "4. Legal & Enforcement Actions\n\n"
            "RULES:\n"
            "- EVERY query must be a complex, multi-word search string.\n"
            "- You MUST use the 'site:' operator in at least 10 queries.\n"
            "- NEVER use single words (e.g., \"proposed\", \"legal\").\n\n"
            "CRITICAL OUTPUT FORMAT:\n"
            "You must first write a 2-sentence summary of your strategy. THEN, output the JSON block inside triple backticks like this:\n"
            "```json\n"
            "{\n"
            "  \"search_queries\": [\n"
            "    \"site:consumerfinance.gov \\\"Buy Now Pay Later\\\" intitle:rule\",\n"
            "    \"site:dfs.ny.gov \\\"BNPL\\\" proposed rule\"\n"
            "  ]\n"
            "}\n"
            "```"
        )

        try:
            logging.info(f"[PlannerAgent] Formulating massive OSINT matrix using {self.model} (Chain-of-Thought)...")
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 1500
                    }
                },
                timeout=180
            )
            
            raw_text = response.json().get("response", "")
            
            # BRUTE-FORCE JSON EXTRACTION
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                clean_json = re.sub(r'//.*', '', raw_text[start_idx:end_idx+1])
                try:
                    result = json.loads(clean_json)
                except Exception as e:
                    logging.error(f"[PlannerAgent] JSON PARSE FAILED. RAW TEXT:\n{raw_text}")
                    raise e
            else:
                logging.error(f"[PlannerAgent] NO BRACKETS FOUND. RAW TEXT:\n{raw_text}")
                raise ValueError("No JSON brackets found in output")
            
            queries = result.get("search_queries", [])
            valid_queries = [q for q in queries if len(str(q).split()) >= 3]
            
            if valid_queries:
                logging.info(f"[PlannerAgent] Generated {len(valid_queries)} VALID top-tier search vectors:")
                for i, q in enumerate(valid_queries):
                    logging.info(f"   {i+1}. {q}")
                return valid_queries
            else:
                raise ValueError("LLM returned garbage/empty array.")

        except Exception as e:
            logging.warning(f"[PlannerAgent] Plan generation rejected due to: {e}. Falling back to defaults.")
            return [
                'site:consumerfinance.gov "Buy Now Pay Later" intitle:"rule"',
                'site:dfs.ny.gov "BNPL" proposed rule',
                'site:brookings.edu "algorithmic credit" regulation'
            ]