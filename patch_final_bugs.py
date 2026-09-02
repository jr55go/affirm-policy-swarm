import os

# 1. Patch the Orchestrator NoneType bug
orch_path = os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm/agents/orchestrator.py')
with open(orch_path, 'r') as f:
    orch_code = f.read()

orch_code = orch_code.replace(
    "\"snippet\": item.get('abstract', '')[:1000],", 
    "\"snippet\": (item.get('abstract') or '')[:1000],"
)

with open(orch_path, 'w') as f:
    f.write(orch_code)

# 2. Patch the Market Sentiment Agent isolation
sent_path = os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm/agents/market_sentiment_agent.py')
with open(sent_path, 'r') as f:
    sent_code = f.read()

sent_code = sent_code.replace(
    "self._store_regulatory_results(\"market\", \"sentiment\", analyzed_content)", 
    "# self._store_regulatory_results(\"market\", \"sentiment\", analyzed_content)  # Delegated to Orchestrator"
)

with open(sent_path, 'w') as f:
    f.write(sent_code)

print("Bugs successfully patched.")
