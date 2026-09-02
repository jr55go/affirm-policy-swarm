"""
Human Feedback Agent: Responsible for managing analyst interactions and logging feedback.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

class HumanFeedbackAgent:
    def __init__(self, agent_id="human-feedback"):
        self.agent_id = agent_id
        self.name = "Human Feedback Agent"
        # Ensure the feedback directory exists
        self.feedback_dir = os.path.join("data", "fine_tuning")
        os.makedirs(self.feedback_dir, exist_ok=True)
        self.feedback_file = os.path.join(self.feedback_dir, "golden_dataset.jsonl")
        print(f"2026-06-24 18:50:00 - agent.{self.agent_id} - INFO - Logger Active: Pure Python File I/O")

    def execute_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and log human feedback on a policy record.

        Expected payload:
        {
            "record_id": "unique identifier of the record",
            "human_decision": one of ["accept", "reject", "monitor", "escalate", "false_positive", "needs_research"],
            "reason": "explanation for the human decision",
            "original_record": {...}  # optional, the original record being feedback on
        }

        Returns:
            Dict with status and feedback file path.
        """
        record_id = payload.get("record_id")
        human_decision = payload.get("human_decision")
        reason = payload.get("reason", "")
        original_record = payload.get("original_record", {})

        # Validate human_decision
        valid_decisions = ["accept", "reject", "monitor", "escalate", "false_positive", "needs_research"]
        if human_decision not in valid_decisions:
            return {
                "agent_id": self.agent_id,
                "status": "ERROR",
                "message": f"Invalid human_decision: {human_decision}. Must be one of {valid_decisions}"
            }

        # Prepare feedback entry
        feedback_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "record_id": record_id,
            "human_decision": human_decision,
            "reason": reason,
            "original_record": original_record,
            "agent_id": self.agent_id
        }

        # Append to JSONL file
        try:
            with open(self.feedback_file, 'a') as f:
                f.write(json.dumps(feedback_entry) + '\n')
            print(f"[{self.agent_id}] Feedback logged for record {record_id}: {human_decision}")
            return {
                "agent_id": self.agent_id,
                "status": "SUCCESS",
                "message": f"Feedback logged for record {record_id}",
                "feedback_file": self.feedback_file
            }
        except Exception as e:
            print(f"[{self.agent_id}] Error logging feedback: {e}")
            return {
                "agent_id": self.agent_id,
                "status": "ERROR",
                "message": f"Failed to log feedback: {str(e)}"
            }