import os

workspace = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm")

# List files that are confirmed to be calling the Tavily API
files_to_patch = [
    "agents/discovery_agent.py",
    "agents/context_expansion_agent.py"
]

for filename in files_to_patch:
    filepath = os.path.join(workspace, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        with open(filepath, 'w') as f:
            for line in lines:
                # Comment out any lines containing 'tavily'
                if 'tavily' in line.lower():
                    f.write(f"# {line}")
                else:
                    f.write(line)
        print(f"[+] Commented out Tavily calls in {filename}")
