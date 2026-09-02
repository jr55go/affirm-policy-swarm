from pathlib import Path
import inspect
import agents.reporting_agent as ra

p = Path(ra.__file__)
print("Overwriting imported ReportingAgent file:", p)

p.write_text(r'''import os
import json
from datetime import datetime, timezone

try:
    from infrastructure.database import neo4j_session
except Exception:
    neo4j_session = None


class ReportingAgent:
    def __init__(self, agent_id="reporting-agent"):
        self.agent_id = agent_id
        self.name = "Reporting Agent"

    def execute_task(self, payload):
        rid = payload.get("run_id")
        traces = payload.get("traces", [])
        legislative = payload.get("legislative", {})
        impact = payload.get("impact", {})
        research = payload.get("research", {})
        validation = payload.get("validation", {})

        findings = impact.get("findings", []) or []
        adjacent = impact.get("adjacent_watchlist", []) or []
        rejected = impact.get("rejected_records", []) or []

        rd = f"reports/live_runs/{rid}"
        os.makedirs(rd, exist_ok=True)

        nodes = []
        neo4j_error = None

        # Only touch Neo4j when exact BNPL findings exist.
        if findings and neo4j_session:
            try:
                with neo4j_session() as s:
                    for f_i in findings:
                        s.run(
                            """
                            MERGE (b:LegislativeItem {bill_id:$bill_id, run_id:$run_id})
                            SET b.title=$title,
                                b.source=$source,
                                b.url=$url,
                                b.agent_id=$agent_id,
                                b.swarm_id='affirm_policy_swarm',
                                b.project_scope='affirm_bnpl_policy',
                                b.relevance_score=$relevance_score,
                                b.updated_at=$updated_at
                            """,
                            {
                                "bill_id": f_i.get("bill_id"),
                                "run_id": rid,
                                "title": f_i.get("title"),
                                "source": f_i.get("source"),
                                "url": f_i.get("url"),
                                "agent_id": self.agent_id,
                                "relevance_score": f_i.get("relevance_score"),
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            },
                        )

                    res = s.run(
                        """
                        MATCH (b:LegislativeItem)
                        WHERE b.run_id=$run_id
                          AND b.swarm_id='affirm_policy_swarm'
                          AND b.project_scope='affirm_bnpl_policy'
                        RETURN b.bill_id AS bill_id
                        """,
                        {"run_id": rid},
                    )
                    nodes = [dict(row) for row in res]
            except Exception as e:
                neo4j_error = str(e)

        report = {
            "run_id": rid,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "legislative_records_seen": len(legislative.get("records", []) or []),
                "accepted_bnpl_findings": len(findings),
                "adjacent_watchlist_count": len(adjacent),
                "rejected_count": len(rejected),
                "neo4j_matched": len(nodes),
                "neo4j_error": neo4j_error,
            },
            "findings": findings,
            "adjacent_watchlist": adjacent,
            "rejected_sample": rejected[:20],
            "research_context": research,
            "validation": validation,
            "neo4j_readback": {"matched": len(nodes), "nodes": nodes},
        }

        with open(f"{rd}/report.json", "w") as f:
            json.dump(report, f, indent=2)

        with open(f"{rd}/neo4j_readback.json", "w") as f:
            json.dump(
                {
                    "run_id": rid,
                    "fresh_records_read_back": len(nodes),
                    "nodes": [x.get("bill_id") for x in nodes],
                    "neo4j_error": neo4j_error,
                },
                f,
                indent=2,
            )

        with open(f"{rd}/agent_trace.json", "w") as f:
            json.dump(traces, f, indent=2)

        with open(f"{rd}/evidence_ledger.json", "w") as f:
            json.dump(
                [
                    {
                        "source": f_i.get("source"),
                        "bill_id": f_i.get("bill_id"),
                        "title": f_i.get("title"),
                        "evidence_snippets": [f_i.get("reason_for_score")],
                        "run_id": rid,
                    }
                    for f_i in findings
                ],
                f,
                indent=2,
            )

        md = "# 🚀 Swarm Intelligence Report\n\n"
        md += "## 📌 Metadata\n"
        md += f"* **Run ID:** `{rid}`\n"
        md += f"* **Generated:** `{report['generated_at']}`\n\n"

        md += "## ✅ Acceptance Summary\n"
        md += f"* Legislative records seen: `{report['summary']['legislative_records_seen']}`\n"
        md += f"* Accepted BNPL findings: `{len(findings)}`\n"
        md += f"* Adjacent watchlist records: `{len(adjacent)}`\n"
        md += f"* Rejected records: `{len(rejected)}`\n"
        md += f"* Neo4j nodes read back: `{len(nodes)}`\n\n"

        md += "## 🧠 Accepted BNPL Findings\n\n"
        if findings:
            for f_i in findings:
                md += f"* `{f_i.get('bill_id')}` — {f_i.get('title')} | Terms: {f_i.get('bnpl_terms_found')} | Score: {f_i.get('relevance_score')}\n"
        else:
            md += "* No exact BNPL findings accepted in this run.\n"

        md += "\n## 🟡 Adjacent Consumer-Finance Watchlist\n\n"
        if adjacent:
            for a_i in adjacent[:50]:
                md += f"* `{a_i.get('bill_id')}` — {a_i.get('title')} | Adjacent terms: {a_i.get('adjacent_policy_terms_found')} | Score: {a_i.get('relevance_score')}\n"
        else:
            md += "* No adjacent consumer-finance records captured.\n"

        md += "\n## 🛢️ Neo4j Read-Back\n"
        md += f"* Nodes: `{len(nodes)}`\n"

        with open(f"{rd}/report.md", "w") as f:
            f.write(md)

        return {
            "agent_id": self.agent_id,
            "report_dir": rd,
            "neo4j_matched": len(nodes),
            "neo4j_error": neo4j_error,
            "records_in": len(findings),
            "records_out": len(nodes),
            "status": "COMPLETED",
        }
''')
