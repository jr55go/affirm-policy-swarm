import sys
import os

# Force Python to look in the exact swarm directory
sys.path.append(os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm'))

from infrastructure.graph_db import GraphConnector

connector = GraphConnector()
with connector.driver.session() as session:
    labels = session.run("CALL db.labels() YIELD label RETURN collect(label) as labels").single()["labels"]
    print("\n=== NEO4J LABELS ===")
    print(labels)
    
    sample = session.run("MATCH (n) RETURN labels(n) as lbls, keys(n) as keys LIMIT 5")
    print("\n=== SAMPLE NODES ===")
    for r in sample:
        print(f"Labels: {r['lbls']} | Properties: {r['keys']}")
        
    rels = session.run("MATCH ()-[r]->() RETURN distinct type(r) as rel_type LIMIT 5")
    print("\n=== RELATIONSHIPS ===")
    print([r["rel_type"] for r in rels])
