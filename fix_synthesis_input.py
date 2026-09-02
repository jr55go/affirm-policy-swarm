ia_path = 'agents/research_synthesis_agent.py'
with open(ia_path, 'r') as f:
    content = f.read()

# Update the findings retrieval to be more robust
new_line = '        findings = payload.get("findings", payload.get("impact_findings", payload.get("impact", {}).get("findings", [])))'

# We target the specific line inside execute_task
content = content.replace(
    '        findings = payload.get("impact_findings", payload.get("impact", {}).get("findings", []))',
    new_line
)

with open(ia_path, 'w') as f:
    f.write(content)
print("Patched ResearchSynthesisAgent to accept 'findings' key from Orchestrator.")
