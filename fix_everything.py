import os
import re

# --- 1. Fix Context Expansion Agent ---
cea_path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/context_expansion_agent.py")
cea_code = """import logging

class ContextExpansionAgent:
    def __init__(self, agent_id="context_expansion_agent", model="nemotron:70b"):
        self.agent_id = agent_id
        self.model = model
        self.browser = None  # Framework injects the browser tool here

    def execute_task(self, task_data):
        # Handle dict wrapping from orchestrator safely
        if isinstance(task_data, dict):
            records = task_data.get("records", [])
        else:
            records = task_data
            task_data = {"records": records}
            
        logging.info(f"[{self.agent_id}] Expanding context for {len(records)} records")
        expanded_records = []
        
        for record in records:
            # Skip if the record isn't a dictionary (safeguard)
            if not isinstance(record, dict):
                expanded_records.append(record)
                continue
                
            source_vector = record.get('source_vector', '')
            url = record.get('url')
            
            if 'site:gov' in source_vector and url and self.browser:
                logging.info(f"[{self.agent_id}] High-value .gov vector detected. Initiating full-page extraction for: {url}")
                try:
                    page_data = self.browser.navigate(url, profile="openclaw")
                    if page_data and isinstance(page_data, list) and len(page_data) > 0:
                        full_text = page_data[0].get('content', '')
                        if full_text:
                            record['full_text'] = full_text
                            logging.info(f"[{self.agent_id}] Successfully extracted {len(full_text)} characters.")
                except Exception as e:
                    logging.error(f"[{self.agent_id}] Failed to extract full text: {e}")
            
            expanded_records.append(record)
            
        # Return in the exact format the orchestrator expects
        task_data["records"] = expanded_records
        return task_data
"""
with open(cea_path, "w") as f:
    f.write(cea_code)
print("[+] Context Expansion Agent updated to handle dictionary unwrapping.")

# --- 2. Fix Federal Register Connector ---
fed_path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/connectors/federal_register.py")
if os.path.exists(fed_path):
    with open(fed_path, "r") as f:
        content = f.read()
    
    # Catch any place where len() might be called on the raw API response
    content = re.sub(r"len\((self\.data|response|results)\)", r"len(\1 or [])", content)
    
    # Ensure any method returning records defaults to an empty list instead of None
    content = re.sub(r"return\s+None\s*(#.*)?$", r"return [] \1", content, flags=re.MULTILINE)
    
    with open(fed_path, "w") as f:
        f.write(content)
    print("[+] Federal Register connector patched.")
else:
    print("[-] Federal Register connector file not found.")
