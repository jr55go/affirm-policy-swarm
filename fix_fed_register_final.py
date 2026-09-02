import os
import re

path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/connectors/federal_register.py")
if os.path.exists(path):
    with open(path, "r") as f:
        content = f.read()
    
    # Aggressively replace any len() check that might hit a None object
    content = re.sub(r"len\(([^)]+)\)", r"len(\1 or [])", content)
    
    with open(path, "w") as f:
        f.write(content)
    print("[+] Federal Register strictly patched against NoneType len() crashes.")
