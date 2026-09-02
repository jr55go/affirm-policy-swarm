import sys
import json
from agents.validation_agent import ValidationAgent

print("=== RUNNING PHASE 1.1 SMOKE TEST ===")
try:
    agent = ValidationAgent()
    
    # We pass one obvious BNPL bill, and one obvious false positive (Agriculture)
    mock_payload = {
        "impact_findings": [
            {
                "bill_id": "LEGISCAN-2153768",
                "title": "Buy Now Pay Later Consumer Protection Act of 2026"
            },
            {
                "bill_id": "LEGISCAN-9999999",
                "title": "An Act relating to agriculture; recognizing the state insect."
            }
        ]
    }
    
    print(f"Agent initialized. Model: {agent.model_name}")
    print("Executing ValidationAgent challenge on 2 mock findings...")
    
    result = agent.execute_task(mock_payload)
    
    print("\n--- VALIDATION RESULTS (FROM QWEN) ---")
    print(json.dumps(result, indent=2))
    
    print("\n✅ SMOKE TEST PASSED.")
except Exception as e:
    print(f"\n❌ SMOKE TEST FAILED: {e}")
    sys.exit(1)
