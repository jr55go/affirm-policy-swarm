import sys, os
sys.path.append(os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm'))
from infrastructure.graph_db import GraphConnector

connector = GraphConnector()
with connector.driver.session() as session:
    print("=== SIDEBAR TITLES (OBSERVATION NODES) ===")
    res1 = session.run("""
        MATCH (n:Observation)
        WHERE n.run_id = 'run_1784269240'
        RETURN n.title AS title, keys(n) AS keys LIMIT 3
    """)
    for r in res1:
        print(f"Title: {r['title']} | Keys: {r['keys']}")
        
    print("\n=== CONNECTED PARENT NODES ===")
    res2 = session.run("""
        MATCH (n:Observation)-[r]-(parent)
        WHERE n.run_id = 'run_1784269240'
        RETURN labels(parent) AS parent_labels, parent.title AS parent_title LIMIT 3
    """)
    for r in res2:
        print(f"Parent Labels: {r['parent_labels']} | Parent Title: {r['parent_title']}")
        
    print("\n=== TIMELINE DATE FORMAT ===")
    res3 = session.run("""
        MATCH (n)
        WHERE n.run_id = 'run_1784269240' AND (n.event_date IS NOT NULL OR n.timestamp IS NOT NULL)
        RETURN labels(n) as labels, type(n.event_date) as event_date_type, n.event_date AS event_date, type(n.timestamp) as timestamp_type, n.timestamp AS timestamp LIMIT 3
    """)
    for r in res3:
        print(f"Labels: {r['labels']} | Date Type: {r['event_date_type']} ({r['event_date']}) | Timestamp Type: {r['timestamp_type']} ({r['timestamp']})")
