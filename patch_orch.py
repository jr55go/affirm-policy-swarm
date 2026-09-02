path = 'agents/orchestrator.py'
with open(path, 'r') as f:
    content = f.read()

old_rep_call = """        rep_out = rep_agent.execute_task({
            "run_id": run_id, "leg_records": leg_out.get("records", []), "impact_findings": impact_out.get("findings", []), "adjacent_watchlist": impact_out.get("adjacent_watchlist", []),
            "rejected_records": impact_out.get("rejected_records", []), "val_out": val_out
        })"""

new_rep_call = """        rep_out = rep_agent.execute_task({
            "run_id": run_id, "leg_records": leg_out.get("records", []), "impact_findings": impact_out.get("findings", []), "adjacent_watchlist": impact_out.get("adjacent_watchlist", []),
            "rejected_records": impact_out.get("rejected_records", []), "val_out": val_out, "research_synthesis": research_out
        })"""

if old_rep_call in content:
    content = content.replace(old_rep_call, new_rep_call)
    with open(path, 'w') as f:
        f.write(content)
    print("Orchestrator patched!")
else:
    print("Could not find the target string in orchestrator.py.")
