import requests, sys

try:
    with open("swarm_agents_codebase.txt", "r", encoding="utf-8") as f:
        codebase = f.read()
except FileNotFoundError:
    print("[-] Error: swarm_agents_codebase.txt not found.")
    sys.exit(1)

# Bottom-Weighting: The massive code goes first, the instructions go last.
prompt = codebase + """

========================================================================
CRITICAL INSTRUCTION FOR LEAD ARCHITECT
========================================================================
You are a brutal, strict Lead Software Architect.
YOUR ONLY JOB IS TO FIND BUGS in the codebase above.

DO NOT summarize the codebase.
DO NOT explain what the agents do.
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
2. syntax typos in variable names (like cfbp vs cfpb)
3. fake or hardcoded "Simulated Human Feedback" blocks
4. swallowed exceptions
5. hardcoded URLs or endpoints

If no evidence exists, write exactly: NO CONFIRMED FINDINGS.
"""

print("[*] Dispatching bottom-weighted strict audit to local Qwen 32B...")

endpoints = [
    ("http://localhost:11434/api/generate", "ollama"),
    ("http://localhost:8000/v1/chat/completions", "openai"),
    ("http://localhost:4000/v1/chat/completions", "openai")
]

success = False
for url, api_type in endpoints:
    try:
        if api_type == "ollama":
            payload = {"model": "nemotron:70b", "prompt": prompt, "stream": False, "options": {"temperature": 0.0}}
            r = requests.post(url, json=payload, timeout=600)
            if r.status_code == 200:
                result = r.json().get('response', '')
                success = True
        elif api_type == "openai":
            payload = {"model": "nemotron:70b", "messages": [{"role": "user", "content": prompt}], "temperature": 0.0}
            r = requests.post(url, json=payload, timeout=600)
            if r.status_code == 200:
                result = r.json()['choices'][0]['message']['content']
                success = True
                
        if success:
            with open("qwen_agents_audit.md", "w") as out:
                out.write(result)
            print(result)
            break
    except Exception:
        continue

if not success:
    print("[-] Could not reach local inference endpoint.")
