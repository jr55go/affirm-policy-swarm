import os

WORKSPACE = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm")

def append_to_file(filepath, text):
    full_path = os.path.join(WORKSPACE, filepath)
    if os.path.exists(full_path):
        with open(full_path, "r") as f:
            content = f.read()
        if text not in content:
            with open(full_path, "a") as f:
                f.write(f"\n{text}\n")
            print(f"[+] Added backward-compatibility alias to {filepath}")
        else:
            print(f"[*] Alias already exists in {filepath}")

# 1. Alias the Checkpoint Manager
append_to_file(
    "infrastructure/connectors/connector_checkpoint.py",
    "ConnectorCheckpointManager = CheckpointManager"
)

# 2. Alias the Health Tracker
append_to_file(
    "infrastructure/connectors/connector_health.py",
    "ConnectorHealth = HealthTracker\nConnectorHealthState = ConnectorStatus"
)

print("\n[+] Import aliasing complete.")
