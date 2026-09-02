import os, sys, uuid, requests
sys.path.insert(0, os.getcwd())
cg_key = os.environ.get("CONGRESS_GOV_API_KEY", "")
ls_key = os.environ.get("LEGISCAN_API_KEY", "")

if not cg_key or not ls_key:
    print("❌ FAIL: Missing environment target credentials."); sys.exit(1)

from agents.orchestrator import PolicyOrchestratorAgent
from infrastructure.database import neo4j_session

try:
    orchestrator = PolicyOrchestratorAgent()
    swarm_res = orchestrator.run_swarm(cg_key, ls_key)
    run_id = swarm_res["run_id"]
    
    # Readback query isolated solely by the current thread token
    with neo4j_session() as session:
        res = session.run("""
        MATCH (b:LegislativeItem)
        WHERE b.run_id = $run_id AND b.swarm_id = 'affirm_policy_swarm' AND b.project_scope = 'affirm_bnpl_policy'
        RETURN b.bill_id AS bill_id, b.agent_id AS agent_id
        """, {"run_id": run_id})
        nodes = [row for row in res]
        
    if len(nodes) != swarm_res["records_count"]:
        print("❌ FAIL: Swarm isolation read-back mismatch."); sys.exit(5)
        
    print(f"\n🏆 [TRUE SWARM PASS] Run isolated completely via tokens: {run_id}")
    sys.exit(0)
except Exception as e:
    print(f"❌ CRITICAL INTER-AGENT SWARM ACCIDENT: {e}"); sys.exit(6)
