import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, '.')

from infrastructure.database import db_manager, get_neo4j_driver
from agents.legislative_monitor import LegislativeMonitorAgent

def test_swarm_id_filtering():
    print("=== Testing Swarm ID Filtering ===")
    
    # Initialize the database manager
    db_manager.initialize()
    
    # Create an agent
    agent = LegislativeMonitorAgent('test-agent')
    print(f"Agent SWARM_ID: {agent.SWARM_ID}")
    print(f"Agent PROJECT_SCOPE: {agent.PROJECT_SCOPE}")
    
    # Test 1: Write a node via the agent's update_graph_state
    test_key = f"test_policy_{hash('test')}"
    test_data = {
        "policy_name": "Test Policy",
        "description": "This is a test policy for swarm_id verification.",
        "source": "test"
    }
    
    success = agent.update_graph_state(test_key, test_data)
    print(f"Write success: {success}")
    
    if not success:
        print("FAIL: Could not write node via agent.")
        return False
    
    # Test 2: Verify the node has swarm_id and project_scope in the database
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
            data = json.loads(record['data']) if record['data'] else {}
            print(f"Retrieved swarm_id: {swarm_id}")
            print(f"Retrieved project_scope: {project_scope}")
            print(f"Retrieved data: {data}")
            
            if swarm_id == agent.SWARM_ID and project_scope == agent.PROJECT_SCOPE:
                print("SUCCESS: swarm_id and project_scope match in stored node.")
            else:
                print("FAILURE: swarm_id or project_scope mismatch.")
                print(f"  Expected swarm_id: {agent.SWARM_ID}, got: {swarm_id}")
                print(f"  Expected project_scope: {agent.PROJECT_SCOPE}, got: {project_scope}")
                return False
        else:
            print("FAILURE: Could not find the node with the given key.")
            return False
    
    # Test 3: Read back via agent's query_graph_state (should return the data)
    result = agent.query_graph_state(test_key)
    if result:
        print(f"query_graph_state returned: {result}")
        # The query_graph_state does not return swarm_id and project_scope, but we know they are there from the direct query.
        # We can check that the data matches.
        if result.get('data') == test_data:
            print("SUCCESS: query_graph_state returned the correct data.")
        else:
            print("FAILURE: query_graph_state returned incorrect data.")
            print(f"  Expected: {test_data}")
            print(f"  Got: {result.get('data')}")
            return False
    else:
        print("FAILURE: query_graph_state returned None.")
        return False
    
    # Test 4: Verify that a node without swarm_id is not returned by the agent's query
    # Write a node directly to Neo4j without swarm_id and project_scope
    with driver.session() as session:
        session.run("""
            MERGE (n:PolicyState {lookup_key: $key})
            SET n.data = $data
            """, key="test_no_swarm", data=json.dumps({"policy_name": "No Swarm"}))
        print("Written a node without swarm_id and project_scope.")
    
    # Now try to read it via the agent's query_graph_state (which should filter by swarm_id and project_scope)
    result_no_swarm = agent.query_graph_state("test_no_swarm")
    if result_no_swarm is None:
        print("SUCCESS: Node without swarm_id not returned by filtered query.")
    else:
        print("FAILURE: Node without swarm_id was returned by filtered query.")
        print(f"  Result: {result_no_swarm}")
        return False
    
    # Clean up: delete the test nodes
    with driver.session() as session:
        session.run("MATCH (n:PolicyState {lookup_key: $key}) DELETE n", key=test_key)
        session.run("MATCH (n:PolicyState {lookup_key: $key}) DELETE n", key="test_no_swarm")
        print("Cleaned up test nodes.")
    
    print("\nAll tests passed!")
    return True

if __name__ == "__main__":
    if test_swarm_id_filtering():
        sys.exit(0)
    else:
        sys.exit(1)
