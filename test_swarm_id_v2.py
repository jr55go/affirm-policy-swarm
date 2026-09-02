import sys
sys.path.insert(0, '.')

from infrastructure.database import db_manager
from agents.legislative_monitor import LegislativeMonitorAgent

def test_swarm_id():
    # Initialize the database manager
    db_manager.initialize()
    
    # Create an agent
    agent = LegislativeMonitorAgent('test-agent')
    print(f"Agent SWARM_ID: {agent.SWARM_ID}")
    print(f"Agent PROJECT_SCOPE: {agent.PROJECT_SCOPE}")
    
    # Test writing a LegislativeItem node via the agent's internal method?
    # Instead, let's use the base agent's update_graph_state to create a PolicyState node with swarm_id and project_scope.
    test_key = f"test_policy_{hash('test')}"
    test_data = {
        "policy_name": "Test Policy",
        "description": "This is a test policy for swarm_id verification.",
        "source": "test"
    }
    
    # Use the update_graph_state method (which should now include swarm_id and project_scope)
    agent.update_graph_state(test_key, test_data)
    print(f"Written PolicyState node with key: {test_key}")
    
    # Now, let's check directly in the database that the node has the swarm_id and project_scope
    from infrastructure.database import get_neo4j_driver
    driver = get_neo4j_driver()
    with driver.session() as session:
        # Check the node we just wrote
        result = session.run("""
            MATCH (n:PolicyState {lookup_key: $key})
            RETURN n.swarm_id as swarm_id, n.project_scope as project_scope, n.data as data
            """, key=test_key)
        record = result.single()
        if record:
            swarm_id = record['swarm_id']
            project_scope = record['project_scope']
            data = record['data']
            print(f"Retrieved swarm_id: {swarm_id}")
            print(f"Retrieved project_scope: {project_scope}")
            print(f"Retrieved data: {data}")
            if swarm_id == agent.SWARM_ID and project_scope == agent.PROJECT_SCOPE:
                print("SUCCESS: swarm_id and project_scope match in stored node.")
            else:
                print("FAILURE: swarm_id or project_scope mismatch.")
                print(f"  Expected swarm_id: {agent.SWARM_ID}, got: {swarm_id}")
                print(f"  Expected project_scope: {agent.PROJECT_SCOPE}, got: {project_scope}")
        else:
            print("FAILURE: Could not find the node with the given key.")
            return
    
    # Now test the query_graph_state method (which should filter by swarm_id and project_scope)
    result = agent.query_graph_state(test_key)
    if result:
        print(f"query_graph_state returned: {result}")
        # Note: the current query_graph_state does not return swarm_id and project_scope, so we cannot check them here.
        # But we know from the direct query that they are stored correctly.
    else:
        print("FAILURE: query_graph_state returned None.")
    
    # Also, let's check that a node without the swarm_id is not returned when we query with swarm_id filter.
    # We'll write a node directly to Neo4j without swarm_id and project_scope, then try to read it via the agent's query.
    from infrastructure.database import get_neo4j_driver
    driver = get_neo4j_driver()
    with driver.session() as session:
        # Write a node without swarm_id and project_scope
        session.run("""
            MERGE (n:PolicyState {lookup_key: $key})
            SET n.data = $data
            """, key="test_no_swarm", data={"policy_name": "No Swarm"})
        print("Written a node without swarm_id and project_scope.")
    
    # Now try to read it via the agent's query_graph_state (which should filter by swarm_id and project_scope)
    result_no_swarm = agent.query_graph_state("test_no_swarm")
    if result_no_swarm is None:
        print("SUCCESS: Node without swarm_id not returned by filtered query.")
    else:
        print("FAILURE: Node without swarm_id was returned by filtered query.")
        print(f"  Result: {result_no_swarm}")
    
    # Clean up: delete the test nodes
    with driver.session() as session:
        session.run("MATCH (n:PolicyState {lookup_key: $key}) DELETE n", key=test_key)
        session.run("MATCH (n:PolicyState {lookup_key: $key}) DELETE n", key="test_no_swarm")
        print("Cleaned up test nodes.")

if __name__ == "__main__":
    test_swarm_id()
