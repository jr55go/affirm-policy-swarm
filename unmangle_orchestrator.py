import re

path_orch = 'agents/orchestrator.py'
with open(path_orch, 'r') as f:
    data = f.read()

# 1. Fix the leg_agent variables that got stripped by sed
data = data.replace('getattr(agent, "agent_id", "unknown_agent")', 'leg_agent.agent_id')
data = data.replace('getattr(agent, "name", agent.__class__.__name__)', 'leg_agent.name')

# 2. Fix all the other prefixed variables (ps_getattr, research_getattr, etc.)
data = re.sub(r'([a-zA-Z0-9_]+)_getattr\(agent, "agent_id", "unknown_agent"\)', r'\1_agent.agent_id', data)
data = re.sub(r'([a-zA-Z0-9_]+)_getattr\(agent, "name", agent\.__class__\.__name__\)', r'\1_agent.name', data)

with open(path_orch, 'w') as f:
    f.write(data)

print("Orchestrator un-mangled.")
