import os

filepath = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/infrastructure/connectors/cfpb_connector.py")
if os.path.exists(filepath):
    with open(filepath, 'r') as f:
        data = f.read()
    
    # Replace the relative import with the absolute one
    data = data.replace("from .base_source_connector import BaseSourceConnector", "from infrastructure.connectors.base_source_connector import BaseSourceConnector")
    
    with open(filepath, 'w') as f:
        f.write(data)
    print("[+] Fixed module import path in cfpb_connector.py")
