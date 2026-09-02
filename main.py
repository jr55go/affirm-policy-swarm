"""
Affirm Policy Swarm - Main Orchestration Loop
Continuous policy monitoring and analysis system for Affirm products.
"""

import time
import threading
import signal
import sys
from datetime import datetime, timezone
from affirm_policy_swarm.agents.orchestrator import PolicyOrchestratorAgent
from affirm_policy_swarm.infrastructure.config import load_config
from affirm_policy_swarm.infrastructure.database import neo4j_session, DatabaseManager

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    print(f"\nReceived signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True

def check_for_real_data_stored(start_time):
    """Check if any real data nodes have been stored in Neo4j since start_time."""
    try:
        with neo4j_session() as session:
            # Query for News or Social nodes created after start_time
            query = """
            MATCH (n)
            WHERE (n:News OR n:Social) 
              AND n.analysis_timestamp >= $start_time
            RETURN count(n) as count
            """
            result = session.run(query, start_time=start_time.isoformat())
            record = result.single()
            return record["count"] > 0 if record else False
    except Exception as e:
        print(f"Error checking for real data in Neo4j: {e}")
        return False

def main():
    """Main continuous orchestration loop."""
    global shutdown_requested
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Starting Affirm Policy Swarm...")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    
    # Load configuration
    config = load_config()
    print(f"Configuration loaded. Logging level: {config.logging_level}")
    
    # Initialize database connections
    db_manager = DatabaseManager()
    try:
        db_manager.initialize()
        print("Database connections initialized (Neo4j, Redis, Vault)")
    except Exception as e:
        print(f"Warning: Database initialization partially failed: {e}")
        print("Continuing with limited functionality...")
    
    # Initialize the orchestrator agent
    orchestrator = PolicyOrchestratorAgent("policy-orchestrator-001")
    print(f"Orchestrator agent initialized: {orchestrator.agent_id}")
    
    # Record start time for real data check
    start_time = datetime.now(timezone.utc)
    print(f"Run start time: {start_time.isoformat()}")
    
    # Start heartbeat monitoring in background
    def heartbeat_monitor():
        """Update heartbeats for all agents periodically."""
        while not shutdown_requested:
            try:
                orchestrator.heartbeat()
                # In a full implementation, we'd heartbeat all agents here
                time.sleep(config.agent_heartbeat_interval)
            except Exception as e:
                orchestrator.log_thought(f"Heartbeat monitor error: {e}")
                time.sleep(5)  # Shorter sleep on error
    
    heartbeat_thread = threading.Thread(target=heartbeat_monitor, daemon=True)
    heartbeat_thread.start()
    print(f"Heartbeat monitor started (interval: {config.agent_heartbeat_interval}s)")
    
    # MAIN CONTINUOUS LOOP
    print("Entering main orchestration loop...")
    loop_count = 0
    objective_decomposed = False
    
    try:
        while not shutdown_requested:
            loop_start_time = time.time()
            loop_count += 1
            
            # Log loop start (every 10 loops to avoid excessive logging)
            if loop_count % 10 == 1:
                orchestrator.log_thought(f"Main loop iteration {loop_count} started")
                print(f"Loop {loop_count} started at {datetime.utcnow().strftime('%H:%M:%S')}")
            
            try:
                # 1. Orchestrator decomposes high-level objectives
                #    (e.g., "Monitor all Affirm product policy landscape")
                #    Run only once per session
                if not objective_decomposed:
                    decomposition = orchestrator.execute_task({
                        "type": "decompose_objective",
                        "objective": "Continuously monitor and analyze policy changes and market sentiment affecting Affirm products",
                        "scope": {
                            "products": ["Buy Now, Pay Later", "Savings", "Loans"],
                            "jurisdictions": ["US Federal", "All 50 States", "Canada", "EU"],
                            "sources": ["legislative", "regulatory", "judicial", "research", "stakeholder", "market_sentiment"]
                        }
                    })
                    objective_decomposed = True
                else:
                    # Objective already decomposed, skip to avoid queue bloat
                    pass
                
                # 2. Schedule tasks based on priority/dependencies
                scheduling = orchestrator.execute_task({
                    "type": "schedule_tasks"
                })
                
                # 3. Monitor progress and handle completions/failures
                monitoring = orchestrator.execute_task({
                    "type": "monitor_progress"
                })
                
                # 4. Handle any escalations or special conditions
                #    (e.g., DEFCON-1 policy changes trigger immediate human alert)
                # This would be handled within the orchestrator's monitor_progress
                
                # 5. Adaptive sleeping - shorter intervals during high activity
                activity_level = min(monitoring.get("active_tasks", 0) / max(config.max_concurrent_agents, 1), 1.0)
                base_sleep = 30  # Base 30 seconds
                sleep_time = max(10, min(300, base_sleep - (activity_level * 20)))  # 10s-5min adaptive
                
                # Check for shutdown request before sleeping
                if shutdown_requested:
                    break
                    
                time.sleep(sleep_time)
                
                # Log loop completion (every 10 loops)
                if loop_count % 10 == 0:
                    loop_duration = time.time() - loop_start_time
                    orchestrator.log_thought(
                        f"Main loop iteration {loop_count} completed in {loop_duration:.2f}s. "
                        f"Active tasks: {monitoring.get('active_tasks', 0)}, "
                        f"Queue length: {monitoring.get('queue_length', 0)}"
                    )
                
                # Check if we have decomposed the objective, the queue is empty, no active tasks, and real data has been stored
                if objective_decomposed and len(orchestrator.task_queue) == 0 and len(orchestrator.active_tasks) == 0:
                    # Check for real data stored in Neo4j since start_time
                    if check_for_real_data_stored(start_time):
                        print("Objective decomposed, task queue empty, and real data stored in Neo4j. Breaking loop.")
                        break
                    else:
                        print("Objective decomposed and queue empty, but no real data stored yet. Continuing to wait for data...")
                        # Wait a bit more for data to be stored
                        time.sleep(10)
                        
            except Exception as e:
                orchestrator.log_thought(f"Error in main loop iteration {loop_count}: {str(e)} - continuing operation")
                print(f"Error in loop {loop_count}: {e}")
                time.sleep(60)  # Back off on errors
                
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received")
    finally:
        print("Shutting down Affirm Policy Swarm...")
        shutdown_requested = True
        
        # Close database connections
        try:
            db_manager.close()
            print("Database connections closed")
        except Exception as e:
            print(f"Error closing database connections: {e}")
        
        print(f"Affirm Policy Swarm stopped. Completed {loop_count} loop iterations.")
        print(f"Timestamp: {datetime.utcnow().isoformat()}Z")

if __name__ == "__main__":
    main()