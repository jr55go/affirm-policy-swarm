import os

path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/discovery_agent.py")
with open(path, "r") as f:
    content = f.read()

old_code = "response = requests.get(url, params=params, timeout=10)"
new_code = """headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "application/json"
            }
            response = requests.get(url, headers=headers, params=params, timeout=10)"""

if old_code in content:
    with open(path, "w") as f:
        f.write(content.replace(old_code, new_code))
    print("[+] Chrome stealth headers injected into the agent!")
else:
    print("[-] Could not find the code to replace. You may need to edit it manually.")
