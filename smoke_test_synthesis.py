import sys
import json
from agents.research_synthesis_agent import ResearchSynthesisAgent

print("=== RUNNING PHASE 1.2 SMOKE TEST ===")
try:
    agent = ResearchSynthesisAgent()
    
    mock_payload = {
        "impact_findings": [
            {
                "bill_id": "NY-S1234",
                "title": "Provides for the regulation of buy-now-pay-later lenders; requires licensing and establishes fee caps."
            },
            {
                "bill_id": "IL-HB5678",
                "title": "Creates the Consumer Credit Protection Act; amends interest rate limits on installment loans."
            }
        ]
    }
    
    print(f"Agent initialized. Model: {agent.model_name}")
    print("Executing Research Synthesis on 2 findings...")
    
    result = agent.execute_task(mock_payload)
    
    print("\n--- SYNTHESIS RESULTS (FROM QWEN) ---")
    print(json.dumps(result.get("synthesis", {}), indent=2))
    
    print("\n✅ SMOKE TEST PASSED.")
except Exception as e:
    print(f"\n❌ SMOKE TEST FAILED: {e}")
    sys.exit(1)
