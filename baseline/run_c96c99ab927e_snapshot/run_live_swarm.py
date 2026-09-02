import os
import sys
from agents.orchestrator import PolicyOrchestratorAgent

# Grab keys from the environment
cg_key = os.getenv("CONGRESS_GOV_API_KEY")
ls_key = os.getenv("LEGISCAN_API_KEY")

if not cg_key or not ls_key:
    print("❌ ERROR: API keys not found in environment.")
    sys.exit(1)

print(f"🚀 Starting Live Swarm. Keys Loaded: Congress={cg_key[:4]}..., LegiScan={ls_key[:4]}...")

orch = PolicyOrchestratorAgent()
result = orch.run_swarm(cg_key, ls_key)

print(f"✅ Swarm Complete. Report generated at: {result['report_dir']}/report.md")
