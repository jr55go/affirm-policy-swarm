import json
import os
from datetime import datetime

class AuditLogger:
    def __init__(self, log_dir="reports"):
        self.log_dir = os.path.expanduser(f"~/.openclaw/workspace/affirm_policy_swarm/{log_dir}")
        self.log_file = os.path.join(self.log_dir, "compliance_audit_log.json")
        os.makedirs(self.log_dir, exist_ok=True)
        
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump([], f)

    def log_action(self, agent_id, action_type, payload_title, reasoning, disposition="auto-routed"):
        """
        Logs every autonomous decision per the v2.12 Compliance Audit spec.
        Enforces Stream A (KB) vs Stream B (Web) tagging.
        """
        stream_tag = "[WEB_STREAM_B]" if "monitor" in agent_id.lower() or "discovery" in agent_id.lower() else "[KB_STREAM_A]"
        
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent": agent_id,
            "stream": stream_tag,
            "action": action_type,
            "record_title": payload_title,
            "reasoning": reasoning,
            "disposition": disposition
        }
        
        try:
            with open(self.log_file, 'r+') as f:
                logs = json.load(f)
                logs.append(entry)
                f.seek(0)
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"[AuditLogger] Error writing to audit log: {e}")

# Global instance for agents to import
compliance_log = AuditLogger()
