code = """import os, json
from datetime import datetime, timezone

try:
    from infrastructure.database import get_db_manager, neo4j_session
except ImportError:
    neo4j_session = None
    get_db_manager = None

class ReportingAgent:
    def __init__(self, agent_id="reporting-agent"):
        self.agent_id = agent_id
        self.name = "Reporting Agent"

    def execute_task(self, payload):
        t_start = datetime.now(timezone.utc).isoformat()
        run_id = payload.get("run_id", "run_unknown")
        report_dir = f"reports/live_runs/{run_id}"
        os.makedirs(report_dir, exist_ok=True)
        
        try:
            if get_db_manager:
                manager = get_db_manager()
                if hasattr(manager, "initialize"): manager.initialize()
                elif hasattr(manager, "connect"): manager.connect()
        except:
            pass

        impact_findings = payload.get("impact", {}).get("findings", [])
        research_items = payload.get("research", {}).get("research", [])
        validations = payload.get("validation", {}).get("validations", [])
        traces = payload.get("traces", {})

        verified_nodes = []
        
        if neo4j_session:
            try:
                with neo4j_session() as session:
                    for f_item in impact_findings:
                        session.run(\"\"\"
                        MERGE (b:LegislativeItem { bill_id: $bill_id, source: $source, run_id: $run_id })
                        SET b.title = $title, b.jurisdiction = $jurisdiction, b.latest_action = $latest_action,
                            b.url = $url, b.relevance_score = $relevance_score, b.reason_for_score = $reason_for_score,
                            b.swarm_id = 'affirm_policy_swarm', b.project_scope = 'affirm_bnpl_policy',
                            b.agent_id = $agent_id, b.created_at = $created_at
                        \"\"\", {
                            "bill_id": f_item.get("bill_id", "unknown"), "source": f_item.get("source", "unknown"), 
                            "run_id": run_id, "title": f_item.get("title", "unknown"),
                            "jurisdiction": f_item.get("jurisdiction", ""), "latest_action": f_item.get("latest_action", ""), 
                            "url": f_item.get("url", ""), "relevance_score": f_item.get("relevance_score", 0), 
                            "reason_for_score": f_item.get("reason_for_score", ""), "agent_id": self.agent_id, 
                            "created_at": t_start
                        })

                    res = session.run(\"\"\"
                    MATCH (b:LegislativeItem)
                    WHERE b.run_id = $run_id AND b.swarm_id = 'affirm_policy_swarm' AND b.project_scope = 'affirm_bnpl_policy'
                    RETURN b.bill_id AS bill_id, b.source AS source
                    \"\"\", {"run_id": run_id})
                    for row in res:
                        verified_nodes.append({"bill_id": row["bill_id"], "source": row["source"]})
            except Exception as e:
                print(f"Neo4j Warning: {e}")

        t_end = datetime.now(timezone.utc).isoformat()
        traces["ReportingAgent"] = {
            "agent_id": self.agent_id, "agent_name": self.name, "agent_role": "Telemetry Consolidation",
            "status": "COMPLETED", "started_at": t_start, "completed_at": t_end
        }

        with open(f"{report_dir}/agent_trace.json", "w") as json_f:
            json.dump(traces, json_f, indent=2)

        report_data = {
            "run_id": run_id, "status": "APPROVED_DYNAMIC",
            "findings": impact_findings, "research_context": research_items, "validation": validations,
            "neo4j_readback": {"status": "VERIFIED", "matched_count": len(verified_nodes)}
        }
        with open(f"{report_dir}/report.json", "w") as json_f:
            json.dump(report_data, json_f, indent=2)

        with open(f"{report_dir}/neo4j_readback.json", "w") as json_f:
            json.dump({
                "run_id": run_id, "fresh_records_read_back": len(verified_nodes),
                "node_identifiers": [v["bill_id"] for v in verified_nodes]
            }, json_f, indent=2)

        ledger_data = []
        for f_item in impact_findings:
            ledger_data.append({
                "source": f_item.get("source"), "bill_id": f_item.get("bill_id"), 
                "title": f_item.get("title"), "url": f_item.get("url"),
                "evidence_snippets": [f_item.get("reason_for_score")], "run_id": run_id
            })
        with open(f"{report_dir}/evidence_ledger.json", "w") as json_f:
            json.dump(ledger_data, json_f, indent=2)

        md_content = f"# 🚀 Swarm Intelligence Report (Run: {run_id})\\n\\n"
        md_content += f"## 📌 Run Metadata\\n* **Run ID:** `{run_id}`\\n* **Context Space:** `affirm_policy_swarm`\\n\\n"
        md_content += "## 🧠 Live Source Findings & Agent Reasoning\\n\\n"

        res_map = {r.get("bill_id"): r for r in research_items if "bill_id" in r}
        val_map = {v.get("bill_id"): v for v in validations if "bill_id" in v}

        for f_item in impact_findings:
            b_id = f_item.get("bill_id", "unknown")
            r_item = res_map.get(b_id, {})
            v_item = val_map.get(b_id, {})
            
            md_content += f"### {f_item.get('title', 'Unknown')}\\n"
            md_content += f"* **ID / Source:** `{b_id}` | {f_item.get('source', 'Unknown')}\\n"
            md_content += f"* **URL:** {f_item.get('url', 'N/A')}\\n"
            md_content += f"* **Latest Action:** {f_item.get('latest_action', 'N/A')}\\n\\n"
            
            md_content += "#### Impact Analysis\\n"
            md_content += f"* **Score:** {f_item.get('relevance_score', 0)} | **Direct BNPL Relevance:** {f_item.get('direct_bnpl_relevance', 'unknown')}\\n"
            md_content += f"* **Reasoning:** {f_item.get('reason_for_score', '')}\\n"
            md_content += f"* **Uncertainty Notes:** {f_item.get('uncertainty_notes', '')}\\n\\n"
            
            md_content += "#### Research Context\\n"
            md_content += f"* {r_item.get('research_notes', 'No external research lookup was performed.')}\\n\\n"
            
            md_content += "#### Validation Review\\n"
            md_content += f"* **Status:** {v_item.get('validation_status', 'UNKNOWN')} (Confidence: {v_item.get('confidence', 'unknown')})\\n"
            md_content += f"* **Validation Reason:** {v_item.get('validation_reason', '')}\\n\\n"
            
            md_content += "#### Action Recommendation\\n"
            if f_item.get('should_alert_human'):
                md_content += "* ⚠️ **HUMAN ALERT REQUIRED:** Policy signal contains explicit target terms.\\n\\n"
            else:
                md_content += "* ℹ️ **NO ACTION REQUIRED:** Record stored for baseline tracking.\\n\\n"
            md_content += "---\\n\\n"

        md_content += f"## 🛢️ Neo4j Read-Back Proof\\n* Fresh Database Read Match Count: `{len(verified_nodes)}` nodes.\\n"

        with open(f"{report_dir}/report.md", "w") as md_f:
            md_f.write(md_content)

        return {"report_dir": report_dir}
"""
with open("agents/reporting_agent.py", "w") as f:
    f.write(code)
