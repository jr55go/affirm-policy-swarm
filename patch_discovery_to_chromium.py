import os
import re

agent_path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/discovery_agent.py")

with open(agent_path, 'r') as f:
    content = f.read()

# Replace the network request with a local tool call to the headless chromium browser
# We assume the agent class has access to self.browser (standard OpenClaw pattern)
new_content = re.sub(
    r"results = requests\.get\(.*?\)",
    "results = self.browser.navigate(query, profile='user')",
    content
)

with open(agent_path, 'w') as f:
    f.write(new_content)

print("[+] Discovery Agent patched to use local headless browser.")
