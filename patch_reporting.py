import re
path = 'agents/reporting_agent.py'
with open(path, 'r') as f:
    content = f.read()

# We need to find the loop that generates the "Accepted BNPL Findings" bullet points
# and inject the validation reasons.

old_block = """        for f in payload.get('impact_findings', []):
            line = f"* `{f.get('bill_id')}` — {f.get('title')} | Terms: {f.get('matched_terms')} | Score: {f.get('relevance_score')}"
            accepted_lines.append(line)"""

new_block = """        
        validations = payload.get('val_out', {}).get('validations', [])
        val_map = {v.get('bill_id'): v.get('llm_challenge_assessment', {}) for v in validations}

        for f in payload.get('impact_findings', []):
            bill_id = f.get('bill_id')
            val = val_map.get(bill_id, {})
            val_reason = val.get('validation_reason', val.get('reason', 'Deterministic validation only'))
            fp_risk = val.get('false_positive_risk', 'unknown')
            
            line = f"* `{bill_id}` — {f.get('title')}\\n  * **Terms:** {f.get('matched_terms')} | **Score:** {f.get('relevance_score')}\\n  * **Validation:** {val.get('validation_status', 'APPROVED')} (Risk: {fp_risk}) - {val_reason}\\n"
            accepted_lines.append(line)"""

if old_block in content:
    content = content.replace(old_block, new_block)
    
    # We also need to ensure the orchestrator is passing 'val_out' to the reporting agent
    orch_path = 'agents/orchestrator.py'
    with open(orch_path, 'r') as f2:
        orch_content = f2.read()
    
    old_rep_call = """        rep_out = rep_agent.execute_task({
            "run_id": run_id, "leg_records": leg_out.get("records", []), "impact_findings": impact_out.get("findings", []), "adjacent_watchlist": impact_out.get("adjacent_watchlist", []),
            "rejected_records": impact_out.get("rejected_records", [])
        })"""
    
    new_rep_call = """        rep_out = rep_agent.execute_task({
            "run_id": run_id, "leg_records": leg_out.get("records", []), "impact_findings": impact_out.get("findings", []), "adjacent_watchlist": impact_out.get("adjacent_watchlist", []),
            "rejected_records": impact_out.get("rejected_records", []), "val_out": val_out
        })"""
    
    orch_content = orch_content.replace(old_rep_call, new_rep_call)
    
    with open(path, 'w') as f:
        f.write(content)
    with open(orch_path, 'w') as f2:
        f2.write(orch_content)
        
    print("ReportingAgent patched successfully.")
else:
    print("Could not find the target block in reporting_agent.py.")
