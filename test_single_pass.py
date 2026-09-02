#!/usr/bin/env python3
"""
Single-pass test of Affirm Policy Swarm orchestrator
Simulates one iteration of the main loop with a mock BNPL regulatory update
"""

import sys
import os
from datetime import datetime, timezone

# Add the workspace to Python path
sys.path.insert(0, '/home/jr55gomez/.openclaw/workspace/affirm-policy-swarm')

from agents.orchestrator import PolicyOrchestratorAgent
from infrastructure.config import load_config
from infrastructure.database import DatabaseManager

def test_single_pass():
    """Run a single pass of the orchestrator with mock BNPL regulatory update"""
    print("=== Affirm Policy Swarm Single-Pass Test ===")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}Z")
    
    # Load configuration
    config = load_config()
    print(f"Configuration loaded. Logging level: {config.logging_level}")
    
    # Initialize database connections (will work now that we have neo4j/redis installed)
    db_manager = DatabaseManager()
    try:
        db_manager.initialize()
        print("✓ Database connections initialized (Neo4j, Redis)")
    except Exception as e:
        print(f"⚠ Warning: Database initialization had issues: {e}")
        print("Continuing with limited functionality...")
    
    # Initialize the orchestrator agent
    orchestrator = PolicyOrchestratorAgent("policy-orchestrator-test-001")
    print(f"✓ Orchestrator agent initialized: {orchestrator.agent_id}")
    
    print("\n--- Starting Single-Pass Simulation ---")
    
    # Simulate one iteration of the main loop
    loop_count = 1
    loop_start_time = datetime.now(timezone.utc)
    
    try:
        # 1. Orchestrator decomposes high-level objectives
        #    Using a mock 'Buy Now, Pay Later' regulatory update as the objective
        print("\n1. Decomposing objective...")
        decomposition = orchestrator.execute_task({
            "type": "decompose_objective",
            "objective": "Process mock Buy Now, Pay Later regulatory update for consumer protection changes",
            "scope": {
                "products": ["Buy Now, Pay Later"],
                "jurisdictions": ["US Federal", "California", "New York"],
                "sources": ["regulatory", "legislative", "research"]
            }
        })
        
        if decomposition.get("status") == "success":
            print(f"   ✓ Decomposed into {decomposition.get('total_tasks', 0)} tasks")
            print(f"   Objective: {decomposition.get('objective')}")
        else:
            print(f"   ✗ Decomposition failed: {decomposition.get('message')}")
            
        # 2. Schedule tasks based on priority/dependencies
        print("\n2. Scheduling tasks...")
        scheduling = orchestrator.execute_task({
            "type": "schedule_tasks"
        })
        
        if scheduling.get("status") == "success":
            print(f"   ✓ Scheduled {len(scheduling.get('scheduled_tasks', []))} tasks")
            print(f"   Remaining in queue: {scheduling.get('remaining_queue_length', 0)}")
            print(f"   Currently active: {scheduling.get('active_tasks_count', 0)}")
        else:
            print(f"   ✗ Scheduling failed: {scheduling.get('message')}")
            
        # 3. Monitor progress and handle completions/failures
        print("\n3. Monitoring progress...")
        monitoring = orchestrator.execute_task({
            "type": "monitor_progress"
        })
        
        if monitoring.get("status") == "success":
            print(f"   ✓ Progress monitor completed")
            print(f"   Active tasks: {monitoring.get('active_tasks', 0)}")
            print(f"   Completed tasks: {monitoring.get('completed_tasks', 0)}")
            print(f"   Failed tasks: {monitoring.get('failed_tasks', 0)}")
            print(f"   Queue length: {monitoring.get('queue_length', 0)}")
            
            # Show some recently completed tasks if any
            recently_completed = monitoring.get('recently_completed', [])
            if recently_completed:
                print("   Recently completed tasks:")
                for task in recently_completed[:3]:  # Show first 3
                    print(f"     - {task.get('type')} ({task.get('jurisdiction')})")
        else:
            print(f"   ✗ Monitoring failed: {monitoring.get('message')}")
        
        loop_end_time = datetime.now(timezone.utc)
        loop_duration = (loop_end_time - loop_start_time).total_seconds()
        
        print(f"\n--- Single-Pass Complete ---")
        print(f"Loop duration: {loop_duration:.2f} seconds")
        print(f"Timestamp: {loop_end_time.isoformat()}Z")
        
        # Close database connections
        try:
            db_manager.close()
            print("✓ Database connections closed")
        except Exception as e:
            print(f"⚠ Warning closing databases: {e}")
            
        return True
        
    except Exception as e:
        print(f"\n✗ Error during single-pass test: {e}")
        import traceback
        traceback.print_exc()
        
        # Still try to close connections
        try:
            db_manager.close()
        except:
            pass
        return False

if __name__ == "__main__":
    success = test_single_pass()
    sys.exit(0 if success else 1)