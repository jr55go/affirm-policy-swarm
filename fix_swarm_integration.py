# 1. Fix ImpactAnalyzerAgent
ia_path = 'agents/impact_analyzer_agent.py'
with open(ia_path, 'r') as f:
    content = f.read()

if "self.name =" not in content:
    content = content.replace(
        'super().__init__(agent_id or f"ImpactAnalyzerAgent-{str(uuid.uuid4())[:8]}", "ImpactAnalyzerAgent")',
        'super().__init__(agent_id or f"ImpactAnalyzerAgent-{str(uuid.uuid4())[:8]}", "ImpactAnalyzerAgent")\n        self.name = "Impact Analyzer Agent"'
    )
    with open(ia_path, 'w') as f:
        f.write(content)
    print("Patched ImpactAnalyzerAgent with self.name attribute.")

# 2. Fix Orchestrator Handoff
orch_path = 'agents/orchestrator.py'
with open(orch_path, 'r') as f:
    content = f.read()

# Update the ImpactAnalyzer call to include the task type
content = content.replace(
    'impact_out = impact_agent.execute_task({"run_id": run_id, "records": leg_out["records"]})',
    'impact_out = impact_agent.execute_task({"type": "analyze_policy_impact", "run_id": run_id, "records": leg_out["records"]})'
)

with open(orch_path, 'w') as f:
    f.write(content)
print("Patched Orchestrator to pass correct task type to ImpactAnalyzer.")
