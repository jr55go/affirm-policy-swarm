from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7688', auth=('neo4j', 'secret123'))

content_labels = [
    'PolicyRecord', 'NewsArticle', 'RegulatoryItem', 
    'LegislativeItem', 'ResearchItem', 'PolicymakerStatement', 
    'SocialPost', 'Observation'
]

with driver.session() as session:
    for label in content_labels:
        res = session.run(f"MATCH (n:`{label}`) RETURN properties(n) AS props LIMIT 1")
        for rec in res:
            props = rec['props']
            print(f"\n🏷️  Label [:{label}] Properties:")
            print("   Keys:", list(props.keys()))
            # Print a snippet of string properties
            for k, v in props.items():
                if isinstance(v, str) and len(v) > 10:
                    print(f"   Sample '{k}': {v[:120]}...")

driver.close()
