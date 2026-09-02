import os

dash_path = os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm/dashboard.py')
with open(dash_path, 'r') as f:
    dash_code = f.read()

old_driver_code = """@st.cache_resource
def get_db_driver():
    # Connects to your local Neo4j instance (Update password if necessary)
    return GraphDatabase.driver("bolt://localhost:7688", auth=("neo4j", "password"))"""

new_driver_code = """import sys
import os
sys.path.append(os.path.dirname(__file__))
from infrastructure.graph_db import GraphConnector

@st.cache_resource
def get_db_driver():
    # Dynamically loads credentials from your central swarm infrastructure
    connector = GraphConnector()
    return connector.driver"""

if old_driver_code in dash_code:
    dash_code = dash_code.replace(old_driver_code, new_driver_code)
    with open(dash_path, 'w') as f:
        f.write(dash_code)
    print("Dashboard authentication successfully patched.")
else:
    print("Error: Could not find the target code to replace.")
