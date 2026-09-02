path = 'agents/orchestrator.py'
with open(path, 'r') as f:
    content = f.read()

# Add import
if "from agents.regulatory_watch_agent import RegulatoryWatchAgent" not in content:
    content = content.replace(
        "from agents.legislative_monitor import LegislativeMonitorAgent",
        "from agents.legislative_monitor import LegislativeMonitorAgent\nfrom agents.regulatory_watch_agent import RegulatoryWatchAgent"
    )

# Add to run_swarm execution
# Insert after LegislativeMonitorAgent
if "reg_agent = RegulatoryWatchAgent()" not in content:
    content = content.replace(
        '        leg_out = leg_agent.execute_task({"run_id": run_id, "cg_key": cg_key, "ls_key": ls_key})',
        '        leg_out = leg_agent.execute_task({"run_id": run_id, "cg_key": cg_key, "ls_key": ls_key})\n\n        reg_agent = RegulatoryWatchAgent()\n        reg_out = reg_agent.execute_task({"run_id": run_id})'
    )

with open(path, 'w') as f:
    f.write(content)
