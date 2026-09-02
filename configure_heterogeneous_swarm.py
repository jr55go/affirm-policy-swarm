import os

WORKSPACE = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm")

print("\n========================================")
print(" HETEROGENEOUS SWARM CONFIGURATION")
print("========================================\n")

def swap_model(filename):
    path = os.path.join(WORKSPACE, "agents", filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            data = f.read()
        
        # Swap the core model variable assignments
        data = data.replace('"nemotron:70b"', '"mistral:7b-instruct"')
        data = data.replace("'nemotron:70b'", "'mistral:7b-instruct'")
        
        # Update the logging print statements so your terminal trace is accurate
        data = data.replace("Model Assigned: nemotron:70b", "Model Assigned: mistral:7b-instruct")
        data = data.replace("Model=nemotron:70b", "Model=mistral:7b-instruct")
        
        with open(path, 'w') as f:
            f.write(data)
        print(f"  [+] Swapped model to Mistral 7B Instruct in {filename}")
    else:
        print(f"  [-] Could not find {filename}")

# Target ONLY the highly rigid JSON extraction agents
swap_model("risk_scoring_agent.py")
swap_model("entity_resolution_agent.py")

print("\n========================================\n")
