import os
import re

path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/connectors/federal_register.py")

if os.path.exists(path):
    with open(path, "r") as f:
        content = f.read()
    
    # Ensure any method returning records defaults to an empty list instead of None
    content = re.sub(
        r"return\s+None\s*(#.*)?$", 
        r"return [] \1", 
        content, 
        flags=re.MULTILINE
    )
    
    # Catch any place where len() might be called on the raw API response
    content = re.sub(r"len\((self\.data|response|results)\)", r"len(\1 or [])", content)
    
    with open(path, "w") as f:
        f.write(content)
    print("[+] Federal Register connector patched.")
else:
    print("[-] Connector file not found at expected path.")
