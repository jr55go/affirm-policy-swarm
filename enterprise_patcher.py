import os

print("\n========================================")
print(" OPENCLAW SWARM MASTER PATCHER")
print("========================================\n")

WORKSPACE = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm")

def patch_file(filepath, replacements):
    full_path = os.path.join(WORKSPACE, filepath)
    if not os.path.exists(full_path):
        print(f"[-] Skipped: {filepath} not found.")
        return
    with open(full_path, 'r') as f:
        content = f.read()
    
    patched = content
    for old, new in replacements:
        patched = patched.replace(old, new)
        
    if patched != content:
        with open(full_path, 'w') as f:
            f.write(patched)
        print(f"[+] Patched: {filepath}")
    else:
        print(f"[*] Already clean: {filepath}")

# 1. Orchestrator Fixes
orch_replacements = [
    ("cfbp_records", "cfpb_records"),  # Fix fatal typo
    ("human_decision = \"monitor\"", "human_decision = None  # REMOVED MOCK DATA"),
    ("corrected_reasoning = \"Upon manual review, this record contains significant BNPL relevance despite initial low-score assessment. Contains relevant credit finance implications.\"", "corrected_reasoning = \"\"  # REMOVED MOCK DATA")
]
patch_file("agents/orchestrator.py", orch_replacements)

# 2. Source Registry Fixes
reg_replacements = [
    ("\"fallback_enabled\": True,", "\"fallback_enabled\": False,  # DISABLED MOCK DATA"),
]
patch_file("infrastructure/source_registry.py", reg_replacements)

# 3. Connector Syntax Error Fixes
connectors_dir = os.path.join(WORKSPACE, "infrastructure/connectors")
if os.path.exists(connectors_dir):
    for root, _, files in os.walk(connectors_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.relpath(os.path.join(root, file), WORKSPACE)
                patch_file(filepath, [
                    ("'rate_limit_delay:.1f}", "'{rate_limit_delay:.1f}"),
                    ("\"rate_limit_delay:.1f}", "\"{rate_limit_delay:.1f}")
                ])

print("\n[+] Enterprise patch complete. The swarm is now in strict production mode.\n")
