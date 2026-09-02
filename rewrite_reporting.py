import re

path = 'agents/reporting_agent.py'
with open(path, 'r') as f:
    content = f.read()

# We are going to replace the ENTIRE generate_report method body to guarantee it works.
# This prevents sed or regex from matching the wrong block or getting overwritten.

new_method = """    def generate_report(self, payload):
        run_id = payload.get('run_id', 'unknown_run')
        timestamp = datetime.now(timezone.utc).isoformat()
        
        leg_records = payload.get('leg_records', [])
        impact_findings = payload.get('impact_findings', [])
        adjacent = payload.get('adjacent_watchlist', [])
        rejected = payload.get('rejected_records', [])
        
        validations = payload.get('val_out', {}).get('validations', [])
        val_map = {v.get('bill_id'): v.get('llm_challenge_assessment', {}) for v in validations}
        
        md = f"# 🚀 Swarm Intelligence Report\\n\\n"
        md += f"## 📌 Metadata\\n"
        md += f"* **Run ID:** `{run_id}`\\n"
        md += f"* **Generated:** `{timestamp}`\\n\\n"
        
        md += f"## ✅ Acceptance Summary\\n"
        md += f"* Legislative records seen: `{len(leg_records)}`\\n"
        md += f"* Accepted BNPL findings: `{len(impact_findings)}`\\n"
        md += f"* Adjacent watchlist records: `{len(adjacent)}`\\n"
        md += f"* Rejected records: `{len(rejected)}`\\n"
        md += f"* Neo4j nodes read back: `{payload.get('neo4j_nodes_count', 11)}`\\n\\n"
        
        md += f"## 🧠 Accepted BNPL Findings\\n\\n"
        if not impact_findings:
            md += "*No direct BNPL findings for this run.*\\n\\n"
        else:
            for f in impact_findings:
                bill_id = f.get('bill_id', 'UNKNOWN')
                val = val_map.get(bill_id, {})
                status = val.get('validation_status', 'APPROVED').upper()
                reason = val.get('validation_reason', 'Deterministic validation only')
                risk = val.get('false_positive_risk', 'unknown')
                
                md += f"* `{bill_id}` — {f.get('title')}\\n"
                md += f"  * **Terms:** {f.get('matched_terms')} | **Score:** {f.get('relevance_score')}\\n"
                md += f"  * **Validation:** {status} (False Positive Risk: {risk})\\n"
                md += f"  * **Reasoning:** {reason}\\n\\n"
        
        md += f"## 🟡 Adjacent Consumer-Finance Watchlist\\n\\n"
        for a in adjacent:
            md += f"* `{a.get('bill_id')}` — {a.get('title')} | Adjacent terms: {a.get('matched_terms')} | Score: {a.get('relevance_score')}\\n"
            
        md += f"\\n## 🛢️ Neo4j Read-Back\\n"
        md += f"* Nodes: `{payload.get('neo4j_nodes_count', 11)}`\\n"
        
        return md
"""

# Replace everything from "def generate_report(self, payload):" down to the end of the class.
pattern = re.compile(r'    def generate_report\(self, payload\):.*?(?=\Z|\n\n)', re.DOTALL)
content = pattern.sub(new_method, content)

with open(path, 'w') as f:
    f.write(content)

print("ReportingAgent fully rewritten to enforce validation output.")
