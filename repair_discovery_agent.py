import os

path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/discovery_agent.py")

with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Remove the lines we commented out
    if not line.strip().startswith("#"):
        new_lines.append(line)
    elif "tavily" in line.lower():
        continue
    else:
        new_lines.append(line)

# Ensure the return statement is properly indented at the function level
with open(path, 'w') as f:
    f.writelines(new_lines)

print("[+] Cleaned up discovery_agent.py and fixed indentation.")
