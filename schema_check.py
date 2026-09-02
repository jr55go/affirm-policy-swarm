import sys
import os
sys.path.append(os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm'))
from infrastructure.graph_db import GraphConnector

connector = GraphConnector()
with connector.driver.session() as session:
    queries = {
        "PolicyRecord": "MATCH (n:PolicyRecord) RETURN keys(n) LIMIT 1",
        "NewsArticle": "MATCH (n:NewsArticle) RETURN keys(n) LIMIT 1",
        "Observation": "MATCH (n:Observation) RETURN keys(n) LIMIT 1"
    }
    for name, query in queries.items():
        print(f"\n=== {name} Properties ===")
        record = session.run(query).single()
        if record:
            print(record[0])
        else:
            print("None found.")
