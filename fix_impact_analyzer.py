path = 'agents/impact_analyzer_agent.py'
with open(path, 'r') as f:
    content = f.read()

# Make the analyzer aware of 'regulator' source types so it doesn't filter them out
# This patch modifies the logic that determines what is "relevant"
old_logic = 'if "bill" in item.get("text_context", ""):'
new_logic = 'if "bnpl" in item.get("text_context", "") or "credit" in item.get("text_context", "") or "rule" in item.get("text_context", ""):'

content = content.replace(old_logic, new_logic)

with open(path, 'w') as f:
    f.write(content)
print("ImpactAnalyzerAgent updated to accept regulatory findings.")
