import os, shutil

WORKSPACE = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm")

print("\n========================================")
print(" OPENCLAW API & CACHE POLISH")
print("========================================\n")

# 1. Nuke the bytecode cache so the CFPB patch loads
print("[*] Clearing compiled __pycache__ directories...")
for root, dirs, files in os.walk(WORKSPACE):
    if "__pycache__" in dirs:
        shutil.rmtree(os.path.join(root, "__pycache__"))
        print(f"  [+] Cleared {os.path.join(root, '__pycache__')}")

# 2. Inject Checkpoint Manager property into the broken connectors
print("\n[*] Patching Connectors with dynamic CheckpointManager...")
checkpoint_stub = """
    @property
    def checkpoint_manager(self):
        from infrastructure.connectors.connector_checkpoint import CheckpointManager
        if not hasattr(self, '_checkpoint_manager'):
            self._checkpoint_manager = CheckpointManager()
        return self._checkpoint_manager
"""

connectors = [
    "infrastructure/connectors/federal_register_connector.py",
    "infrastructure/connectors/regulations_gov_connector.py",
    "infrastructure/connectors/cfpb_connector.py"
]

for file in connectors:
    path = os.path.join(WORKSPACE, file)
    if os.path.exists(path):
        with open(path, "r") as f:
            content = f.read()
        if "_checkpoint_manager" not in content:
            with open(path, "a") as f:
                f.write(f"\n{checkpoint_stub}\n")
            print(f"  [+] Patched: {file}")

# 3. Update Orchestrator Human Feedback enum
print("\n[*] Updating Orchestrator Human Feedback enum...")
orch_path = os.path.join(WORKSPACE, "agents/orchestrator.py")
if os.path.exists(orch_path):
    with open(orch_path, "r") as f:
        data = f.read()
    if "human_decision = None" in data:
        data = data.replace("human_decision = None", "human_decision = 'monitor'")
        with open(orch_path, "w") as f:
            f.write(data)
        print("  [+] Orchestrator patched to use valid 'monitor' enum.")

print("\n========================================\n")
