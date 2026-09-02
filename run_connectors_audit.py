import os, requests, sys

# 1. Pure Python File Packer
output_file = "swarm_connectors_codebase.txt"
with open(output_file, "w", encoding="utf-8") as out:
    for root, _, files in os.walk("infrastructure/connectors/"):
        if "__pycache__" in root: continue
        for file in files:
            if file.endswith(".py") and not file.endswith(".bak"):
                filepath = os.path.join(root, file)
                out.write(f"===== {filepath} =====\n")
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f, 1):
                            out.write(f"{i}\t{line}")
                    out.write("\n")
                except: pass

with open(output_file, "r", encoding="utf-8") as f:
    codebase = f.read()

prompt = codebase + """

========================================================================
CRITICAL INSTRUCTION FOR LEAD ARCHITECT
========================================================================
You are a brutal, strict Lead Software Architect.
YOUR ONLY JOB IS TO FIND BUGS in the connectors codebase above.

DO NOT summarize the codebase.
DO NOT explain what the connectors do.
DO NOT output introductory or concluding text.

Return ONLY a markdown list of confirmed defects.
For every finding include:
- Severity (Critical/High/Medium/Low)
- File path
- Line number(s)
- Code snippet
- Why it is a defect
- Recommended fix

Audit strictly for:
1. mock/demo/fallback data (fake JSON injections)
2. syntax typos
3. swallowed exceptions
4. hardcoded URLs or endpoints
5. rate limits that are hardcoded instead of configurable

If no evidence exists, write exactly: NO CONFIRMED FINDINGS.
"""

print("[*] Dispatching strict audit of infrastructure/connectors/ to Qwen 32B...")

try:
    payload = {"model": "nemotron:70b", "prompt": prompt, "stream": False, "options": {"temperature": 0.0}}
    r = requests.post("http://localhost:11434/api/generate", json=payload, timeout=600)
    if r.status_code == 200:
        result = r.json().get('response', '')
        print(result)
    else:
        payload = {"model": "nemotron:70b", "messages": [{"role": "user", "content": prompt}], "temperature": 0.0}
        r = requests.post("http://localhost:8000/v1/chat/completions", json=payload, timeout=600)
        result = r.json()['choices'][0]['message']['content']
        print(result)
except Exception as e:
    print(f"[-] Inference failed: {e}")
