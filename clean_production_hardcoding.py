import os
import shutil

base = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents")

def load(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def save(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

patched = 0

# 1. Patch policymaker_monitor_agent.py
policy_path = os.path.join(base, "policymaker_monitor_agent.py")
if os.path.exists(policy_path):
    code = load(policy_path)

    bad_mock_block = """                        else:
                            # Fallback to mock data if regex fails
                            text_context = "The Senate Banking Committee today released a statement expressing concerns about the growth of Buy Now, Pay Later services and the need for consumer protection."
                            item = {
                                "title": "Statement on BNPL Regulation",
                                "description": text_context,
                                "link": meta["url"]
                            }"""

    good_fallback = """                        else:
                            raise ValueError("Both XML parsing and Regex extraction failed.")"""

    count = code.count(bad_mock_block)
    if count == 1:
        # Create backup only when changes are confirmed needed
        shutil.copy2(policy_path, policy_path + ".bak")
        code = code.replace(bad_mock_block, good_fallback)
        
        assert bad_mock_block not in code, "Assertion Error: Mock block was not removed!"
        assert good_fallback in code, "Assertion Error: Fallback exception was not injected!"
        
        save(policy_path, code)
        patched += 1
        print("✅ Successfully cleaned and verified policymaker_monitor_agent.py (Backup: policymaker_monitor_agent.py.bak)")
    elif count > 1:
        raise RuntimeError(f"Expected 1 mock block in policymaker_monitor_agent.py, found {count}")
    else:
        print("⚠️ Mock block not found in policymaker_monitor_agent.py (already cleaned?)")

# 2. Patch orchestrator.py
orch_path = os.path.join(base, "orchestrator.py")
if os.path.exists(orch_path):
    code = load(orch_path)

    bad_sim_block = """        # SIMULATED HUMAN FEEDBACK LOOP
        low_impact_findings = [f for f in findings if f.get("impact_score") == "low"]
        if low_impact_findings:
            feedback_target = low_impact_findings[0]
            logger.info(f"[{self.__class__.__name__}] Submitting low-impact finding to Human Review Queue...")
            human_feedback.execute_task({
                "record_id": feedback_target.get("url", "unknown_id"),
                "human_decision": "monitor",
                "reason": "Simulated golden dataset override for edge-case regulation.",
                "original_record": feedback_target
            })"""

    good_sim_block = """        # AUTHENTIC HUMAN FEEDBACK LOOP (Awaiting UI)
        low_impact_findings = [f for f in findings if f.get("impact_score") == "low"]
        if low_impact_findings:
            logger.info(f"[{self.__class__.__name__}] Skipping simulated human feedback. Run is 100% authentic.")"""

    count = code.count(bad_sim_block)
    if count == 1:
        # Create backup only when changes are confirmed needed
        shutil.copy2(orch_path, orch_path + ".bak")
        code = code.replace(bad_sim_block, good_sim_block)
        
        assert bad_sim_block not in code, "Assertion Error: Simulated feedback block was not removed!"
        assert good_sim_block in code, "Assertion Error: Authentic status message was not injected!"
        
        save(orch_path, code)
        patched += 1
        print("✅ Successfully cleaned and verified orchestrator.py (Backup: orchestrator.py.bak)")
    elif count > 1:
        raise RuntimeError(f"Expected 1 simulated feedback block in orchestrator.py, found {count}")
    else:
        print("⚠️ Simulated feedback block not found in orchestrator.py (already cleaned?)")

print(f"\n🚀 Cleanup complete. Patched {patched} file(s).")
