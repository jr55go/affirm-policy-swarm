#!/usr/bin/env python3
"""
Test script to verify the human feedback system works correctly.
"""

import os
import sys
import json
import tempfile
import shutil
from datetime import datetime

# Add the workspace to the path so we can import modules
sys.path.insert(0, '/home/jr55gomez/.openclaw/workspace/affirm_policy_swarm')

def test_human_feedback_agent():
    """Test the HumanFeedbackAgent functionality."""
    print("Testing HumanFeedbackAgent...")
    
    # Import the agent
    from agents.human_feedback_agent import HumanFeedbackAgent
    
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    original_cwd = os.getcwd()
    
    try:
        # Change to test directory
        os.chdir(test_dir)
        
        # Create the agent
        agent = HumanFeedbackAgent()
        
        # Test data
        test_record = {
            "record_id": "test_record_001",
            "title": "Test Financial Regulation",
            "text_context": "This is a test record for feedback logging",
            "source": "Test Source",
            "impact_score": "medium"
        }
        
        # Test logging feedback
        result = agent.execute_task({
            "record_id": test_record["record_id"],
            "human_decision": "accept",
            "reason": "Test feedback for validation",
            "original_record": test_record
        })
        
        print(f"Feedback result: {result}")
        
        # Verify the feedback file was created
        feedback_file = os.path.join("data", "fine_tuning", "golden_dataset.jsonl")
        assert os.path.exists(feedback_file), f"Feedback file not found: {feedback_file}"
        
        # Read and verify the content
        with open(feedback_file, 'r') as f:
            line = f.readline().strip()
            feedback_entry = json.loads(line)
            
        assert feedback_entry["record_id"] == test_record["record_id"]
        assert feedback_entry["human_decision"] == "accept"
        assert feedback_entry["reason"] == "Test feedback for validation"
        assert feedback_entry["original_record"] == test_record
        assert "timestamp" in feedback_entry
        assert feedback_entry["agent_id"] == "human-feedback"
        
        print("✓ HumanFeedbackAgent test passed")
        return True
        
    except Exception as e:
        print(f"✗ HumanFeedbackAgent test failed: {e}")
        return False
    finally:
        # Restore original directory and clean up
        os.chdir(original_cwd)
        shutil.rmtree(test_dir)

def test_normalization_schema():
    """Test that the NormalizedPolicyEvent includes human_review_status."""
    print("\nTesting NormalizedPolicyEvent schema...")
    
    try:
        from infrastructure.connectors.normalization import NormalizedPolicyEvent
        from datetime import datetime
        
        # Create a test event
        event = NormalizedPolicyEvent(
            source_name="Test Source",
            source_type="Test",
            jurisdiction="Test",
            title="Test Event",
            summary="Test Summary",
            event_type="Test",
            event_date=datetime.now(),
            url="http://test.com",
            organization=[],
            people=[],
            committees=[],
            agencies=[],
            legislation=[],
            topics=[],
            keywords=[],
            confidence=0.8,
            evidence="Test evidence",
            raw_payload={"test": "data"},
            connector_version="1.0",
            collected_at=datetime.now(),
            human_review_status="accept"  # Test the new field
        )
        
        # Verify the field exists and is correct
        assert event.human_review_status == "accept"
        
        # Test with None (default)
        event_none = NormalizedPolicyEvent(
            source_name="Test Source",
            source_type="Test",
            jurisdiction="Test",
            title="Test Event",
            summary="Test Summary",
            event_type="Test",
            event_date=datetime.now(),
            url="http://test.com",
            organization=[],
            people=[],
            committees=[],
            agencies=[],
            legislation=[],
            topics=[],
            keywords=[],
            confidence=0.8,
            evidence="Test evidence",
            raw_payload={"test": "data"},
            connector_version="1.0",
            collected_at=datetime.now()
            # human_review_status not provided, should default to None
        )
        
        assert event_none.human_review_status is None
        
        print("✓ NormalizedPolicyEvent schema test passed")
        return True
        
    except Exception as e:
        print(f"✗ NormalizedPolicyEvent schema test failed: {e}")
        return False

def test_orchestrator_imports():
    """Test that the orchestrator can import the new agent."""
    print("\nTesting orchestrator imports...")
    
    try:
        # This will test that our changes to orchestrator.py don't break imports
        from agents.orchestrator import PolicyOrchestratorAgent
        from agents.human_feedback_agent import HumanFeedbackAgent
        
        print("✓ Orchestrator imports test passed")
        return True
        
    except Exception as e:
        print(f"✗ Orchestrator imports test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running Phase 11 Human Feedback System Tests\n")
    
    tests = [
        test_human_feedback_agent,
        test_normalization_schema,
        test_orchestrator_imports
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! The human feedback system is working correctly.")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Please check the implementation.")
        sys.exit(1)