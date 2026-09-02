import os
import re

filepath = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/orchestrator.py")
if os.path.exists(filepath):
    with open(filepath, 'r') as f:
        data = f.read()

    # Targets the specific task IDs for extraction and scoring
    # We replace nemotron:70b with mistral:7b-instruct in the master config
    data = re.sub(r'("task_id":\s+"task_(entity_resolution|risk_scoring)",\s+"model_name":\s+)"qwen2\.5-coder:32b"', 
                  r'\1"mistral:7b-instruct"', data)
    
    with open(filepath, 'w') as f:
        f.write(data)
    print("[+] Patched Orchestrator to route Extraction/Scoring tasks to Mistral 7B.")
