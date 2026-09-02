import sys, os
sys.path.append(os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm'))
from infrastructure.graph_db import GraphConnector

connector = GraphConnector()
with connector.driver.session() as session:
    print("=== DISTINCT RUN IDs IN NEO4J ===")
    res = session.run("""
        MATCH (n) 
        WHERE n.run_id IS NOT NULL 
        RETURN n.run_id AS run_id, count(n) AS node_count, collect(distinct labels(n))[..3] AS node_types 
        ORDER BY node_count DESC
    """)
    for r in res:
        print(f"Run ID: {r['run_id']} | Nodes: {r['node_count']} | Types: {r['node_types']}")
        
    print("\n=== SAMPLE NODES WITHOUT RUN_ID ===")
    res2 = session.run("MATCH (n) WHERE n.run_id IS NULL RETURN labels(n) as lbls, keys(n) as keys LIMIT 5")
    for r in res2:
        print(f"Labels: {r['lbls']} | Keys: {r['keys']}")
