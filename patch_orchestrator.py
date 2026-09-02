import os

filepath = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/orchestrator.py")
with open(filepath, 'r') as f:
    content = f.read()

# 1. Add the deduplication function right before the main class
func_code = """
def deduplicate_records(records: list) -> list:
    '''Removes duplicate context strings before dispatching to LLM.'''
    seen_hashes = set()
    unique_records = []
    for r in records:
        text_stub = (str(r.get("title", "")) + str(r.get("text_context", "")) + str(r.get("snippet", "")))[:150].strip().lower()
        if not text_stub:
            continue
        if text_stub not in seen_hashes:
            seen_hashes.add(text_stub)
            unique_records.append(r)
    return unique_records

class PolicyOrchestratorAgent:
"""
if "def deduplicate_records" not in content:
    content = content.replace("class PolicyOrchestratorAgent:", func_code.strip())

# 2. Inject the deduplication call right before Pipeline Execution
target_str = "# 3. PIPELINE EXECUTION"
inject_str = """all_records = deduplicate_records(all_records)
        logger.info(f"[{self.__class__.__name__}] Deduplicated down to {len(all_records)} unique records")

        # 3. PIPELINE EXECUTION"""

if "all_records = deduplicate_records" not in content:
    content = content.replace(target_str, inject_str)

with open(filepath, 'w') as f:
    f.write(content)
    
print("✅ orchestrator.py successfully patched!")
