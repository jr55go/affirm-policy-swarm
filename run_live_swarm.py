#!/usr/bin/env python3
"""
Production-hardened entry point for the Affirm Policy Swarm.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fail-fast check for required API key
if not os.getenv("CONGRESS_GOV_API_KEY"):
    print("❌ CRITICAL ERROR: CONGRESS_GOV_API_KEY not found. Ensure .env is loaded.")
    sys.exit(1)

from agents.orchestrator import PolicyOrchestratorAgent

cg_key = os.getenv("CONGRESS_GOV_API_KEY")
ls_key = os.getenv("LEGISCAN_API_KEY")

orch = PolicyOrchestratorAgent()
result = orch.run_swarm(cg_key, ls_key)
print(f"✅ Swarm Complete. Report generated at: {result['report_dir']}/report.md")