import os, re

def patch_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
        
    if "safe_json_loads" in content: 
        print(f"[*] Already patched: {filepath}")
        return

    # Replace native json.loads with our robust wrapper
    patched = content.replace("json.loads(", "safe_json_loads(")
    
    extractor = """
import re
import json

def safe_json_loads(text):
    if not isinstance(text, str): return text
    text = text.strip()
    
    # 1. Try raw parsing first
    try: 
        return json.loads(text)
    except Exception: 
        pass
        
    # 2. Strip markdown fences
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if match: 
        clean = match.group(1)
    else:
        # 3. Fallback: bracket extraction
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        clean = match.group(1) if match else text
        
    try:
        return json.loads(clean)
    except Exception as e:
        print(f"[!] JSON parsing fatally failed: {e}")
        return {} # Return empty dict to prevent pipeline crash
"""
    with open(filepath, 'w') as f:
        f.write(extractor + "\n" + patched)
    print(f"[+] Patched {filepath}")

patch_file("agents/entity_resolution_agent.py")
patch_file("agents/risk_scoring_agent.py")
