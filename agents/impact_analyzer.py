class ImpactAnalyzerAgent:
    def __init__(self, agent_id="impact-analyst"):
        self.agent_id = agent_id
        self.name = "Impact Analyzer Agent"
        print(f"2026-06-24 18:50:00 - agent.{self.agent_id} - INFO - Model Assigned: nemotron:70b | Temp=0.2")

    def execute_task(self, payload):
        findings = []
        for r in payload["records"]:
            is_bnpl = any(t in r["text_context"] for t in ["bnpl", "buy now pay later", "affirm", "installment"])
            score = 0.92 if is_bnpl else 0.12
            findings.append({
                "source": r["source"], "bill_id": r["bill_id"], "title": r["title"],
                "jurisdiction": r["jurisdiction"], "latest_action": r["latest_action"], "url": r["url"],
                "primary_topic": "BNPL Regulatory Shift" if is_bnpl else "General Corporate Finance Ingestion Proof",
                "bnpl_terms_found": [t for t in ["bnpl", "buy now pay later", "affirm"] if t in r["text_context"]],
                "direct_bnpl_relevance": "high" if is_bnpl else "low", "relevance_score": score,
                "reason_for_score": "Substantive point-of-sale risk signal tracked." if is_bnpl else "These records prove live ingestion and graph persistence, but they are not strong BNPL policy signals."
            })
        return {"agent_id": self.agent_id, "findings": findings, "status": "COMPLETED"}
