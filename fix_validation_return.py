path = 'agents/validation_agent.py'
with open(path, 'r') as f:
    content = f.read()

old_return = """        return {
            "agent_id": self.agent_id,
            "status": "COMPLETED",
            "validations": validations,
            "total_validated": len(validations)
        }"""

new_return = """        return {
            "agent_id": self.agent_id,
            "status": "COMPLETED",
            "validation_status": "APPROVED" if all(v.get('validation_status', '').lower() == 'approved' for v in validations) else "MIXED",
            "confidence": "high",
            "uncertainty_notes": f"LLM Challenge completed for {len(validations)} items.",
            "validations": validations,
            "total_validated": len(validations)
        }"""

if old_return in content:
    content = content.replace(old_return, new_return)
    with open(path, 'w') as f:
        f.write(content)
    print("Patched ValidationAgent return schema for Orchestrator compatibility.")
else:
    print("Could not find the target return block. It may have already been patched.")
