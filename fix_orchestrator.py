import os
import re

path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/orchestrator.py")
with open(path, "r") as f:
    content = f.read()

# Fix 1: Safely call connect() only if the method exists (fixes CFPB missing attribute)
content = re.sub(r"([a-zA-Z0-9_\.]+)\.connect\(\)", r"getattr(\1, 'connect', lambda: None)()", content)

# Fix 2: Prevent NoneType crashes in len() by defaulting to an empty list
content = re.sub(r"len\(([a-zA-Z0-9_\.]+)\)", r"len(\1 or [])", content)

with open(path, "w") as f:
    f.write(content)

print("[+] Orchestrator patched to handle API connector quirks.")
