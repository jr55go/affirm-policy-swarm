import os
import json
import ast
import hashlib
import logging
import subprocess
from datetime import datetime

class ReportingAgent:
    def __init__(self, agent_id="reporting-agent", model="nemotron:70b"):
        self.agent_id = agent_id
        # Use a heavy frontier model for deep executive synthesis
        self.model = model

        def execute_task(self, payload):
        report_dir = payload.get("report_dir")
        findings = payload.get("findings", [])
        synthesis = payload.get("synthesis", {})
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Phase 0: If no eligible findings exist, output a strict deterministic no-findings report
        if not findings:
            logging.warning(f"[{self.agent_id}] Phase 0 Containment: Zero eligible findings provided. Rendering deterministic NO-FINDINGS report.")
            report_path = os.path.join(report_dir, "report.md") if report_dir else "report.md"
            if report_dir:
                os.makedirs(report_dir, exist_ok=True)
            no_findings_content = f"""# 📝 REGULATORY & PUBLIC AFFAIRS MEMORANDUM

**TO:** Scott Astrada, Director of Public Policy  
**FROM:** Regulatory Risk & Policy Strategy Swarm  
**DATE:** {today_str}  
**SUBJECT:** Executive Policy Briefing: No Admissible Findings  

---

> **PHASE 0 GOVERNANCE NOTICE:** Zero current-run records met strict production eligibility criteria (canonical locators, span verification, and pass status). In accordance with fail-closed governance, no strategic advocacy claims or speculative regulatory conclusions are asserted for this cycle.

---
"""
            with open(report_path, "w", encoding='utf-8') as f:
                f.write(no_findings_content)
            return {"report_path": report_path}
        report_dir = payload.get("report_dir")
        findings = payload.get("findings", [])
        synthesis = payload.get("synthesis", {})
        
        actionable_findings, rejected_findings = [], []
        for f in findings:
            if f.get("validation_status") == "rejected" or f.get("impact_score", "low").lower() == "low":
                rejected_findings.append(f)
            else:
                actionable_findings.append(f)

        today_str = datetime.now().strftime('%B %d, %Y')

        if not findings:
            report_path = os.path.join(report_dir, "report.md") if report_dir else "report.md"
            if report_dir:
                os.makedirs(report_dir, exist_ok=True)
            memo_content = (
                "# Regulatory & Public Affairs Memorandum\n\n"
                f"**DATE:** {today_str}\n\n"
                "No validated production findings were produced in this run. "
                "No policy conclusions or actions are asserted.\n"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(memo_content)
            return {"report_path": report_path, "generation_status": "completed", "actionable_count": 0, "rejected_count": 0}

        if synthesis.get("generation_status") == "failed":
            logging.error(f"[{self.agent_id}] Upstream synthesis failed; production report will not be created.")
            return {"report_path": None, "generation_status": "failed", "error": synthesis.get("error", "Upstream synthesis failed")}

        # 1. Prepare raw context for the LLM
        context_block = f"UPSTREAM SYNTHESIS DATA:\n{json.dumps(synthesis, indent=2)}\n\nRAW ACTIONABLE FINDINGS:\n"
        for i, f in enumerate(actionable_findings):
            url_str = f.get('url', '#')
            date_str = f.get('date') or f.get('postedDate') or 'Date Unspecified'
            context_block += f"Title: {f.get('title')}\nURL: {url_str}\nDate: {date_str}\nSource: {f.get('source')}\nAnalysis: {f.get('inferred_market_impact', f.get('snippet'))}\n\n"

        if not actionable_findings:
            context_block += "\nNO VALIDATED ACTIONABLE FINDINGS. Do not assert baseline, horizon, or adjacent risks."

        # 2. Frontier AI Prompt - Enforcing the 9-Section Matrix
        system_prompt = f"""You are the Chief of Staff and Lead Policy Strategist for Affirm.
Read the raw intelligence below and generate the daily executive briefing.

CRITICAL LAWS:
1. You MUST use exactly the 10 sections defined below (1 BLUF + 9 numbered). Do NOT alter the titles.
2. INLINE SOURCE CITATIONS: Whenever you cite, analyze, or summarize a finding from RAW ACTIONABLE FINDINGS in ANY section (1-9 & BLUF), you MUST attach its exact URL as a clickable inline link formatted as: `[Source Title](URL)`.
3. ZERO HALLUCINATED URLS: You may ONLY cite URLs that are explicitly provided in RAW ACTIONABLE FINDINGS. If a section requires synthesis of adjacent topics without a direct finding, write in plain text with NO links.
4. DATES & 7-DAY DEADLINE WATCH: Review the Date field of every finding. Explicitly detail specific dates, hearing schedules, or comment deadlines in Section ⚡ BLUF and Section 4. If no hard deadlines fall within 7 days of today ({today_str}), state: "No immediate 7-day hard deadlines flagged in this run cycle."
5. LEGISLATIVE PROGNOSIS RULE: For any findings containing [LEGISLATIVE PROGNOSIS], explicitly detail the data in Section 9.

OUTPUT EXACTLY THIS STRUCTURE (Markdown format):

## ⚡ BLUF: 7-Day Urgent Action & Deadline Watch
(Scan records for events, hearings, or comment periods occurring within 7 days of today: {today_str}. Detail what is happening, exact date/time, why Affirm must monitor it, and attach inline link `[Source Title](URL)`. If none, state: "No immediate 7-day hard deadlines flagged in this run cycle.")

## 1. Regulatory and Legislative Pulse
(Analyze agency actions touching BNPL, credit, or AI. ALWAYS cite sources inline using `[Source Name](URL)`.)

## 2. BNPL Competitive Intelligence
(Where competitors stand on live policy debates. ALWAYS cite sources inline using `[Source Name](URL)`.)

## 3. Financial Inclusion Research Digest
(New academic/think tank findings. ALWAYS cite sources inline using `[Source Name](URL)`.)

## 4. Political and Coalition Intelligence
(Committee schedules, hearing dates, and caucus movements. Explicitly state hearing dates or schedules found in raw data and cite inline using `[Source Name](URL)`.)

## 5. Media and Narrative Monitor
(Coverage bucketed into "Amplify", "Monitor", and "Requires Response" with inline `[Source Name](URL)` links.)

## 6. AI Governance & Affirm Tech Policy
(Focus on AI underwriting, algorithms, and data privacy. Cite sources inline using `[Source Name](URL)`.)

## 7. State Regulatory Tracker
(Live heat map of state bills. Flag priority states and cite inline using `[Source Name](URL)`.)

## 8. Internal Alignment Note
(Affirm product/business decisions with policy implications. Cite sources inline using `[Source Name](URL)`.)

## 9. Legislative Feasibility Check
(Detail Passage Probability for active bills. Cite sources inline using `[Source Name](URL)`. If none, state no active bills.)

RAW DATA TO SYNTHESIZE:
{context_block}
"""

        logging.info(f"[{self.agent_id}] Triggering Frontier AI Synthesis for 9-Section Matrix...")
        try:
            import requests
            
            # Failsafe: if system_prompt is already bytes, decode it so JSON can serialize it
            prompt_str = system_prompt.decode('utf-8') if isinstance(system_prompt, bytes) else str(system_prompt)
                
            payload = {
                "model": self.model,
                "prompt": prompt_str,
                "stream": False,
                "options": {
                    "num_ctx": 100000,
                    "temperature": 0.3
                }
            }
            resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=600)
            resp.raise_for_status()
            ai_report_body = resp.json().get("response", "").strip()
        except Exception as e:
            logging.error(f"[{self.agent_id}] LLM synthesis failed; production report will not be created: {e}")
            return {"report_path": None, "generation_status": "failed", "error": str(e)}

        # 3. Build the Evidence & Provenance Tables manually so they are perfectly structured
        detail_lines = []
        for i, f in enumerate(sorted(actionable_findings, key=lambda x: x.get('policy_risk_score', 0), reverse=True)[:10]):
            node_id = f.get('id', f"Node_{hashlib.md5(f.get('title', '').encode()).hexdigest()[:8].upper()}")
            detail_lines.append(f"### {i+1}. {f.get('title', 'Unknown')} (Score: {f.get('policy_risk_score', 'N/A')}/100)")
            detail_lines.append(f"* **Node ID:** `{node_id}` | **Source:** {f.get('source', 'Web')} | [View Source]({f.get('url', '#')})")
            detail_lines.append(f"> **Raw Analysis:** {f.get('inferred_market_impact', f.get('snippet', 'N/A'))}\n")
        details_section = "\n".join(detail_lines) if detail_lines else "No high-risk dockets identified in this cycle."

        provenance_rows = []
        for f in findings:
            title = f.get('title', 'Document').strip().replace('|', '-')[:50]
            node_id = f.get('id', f"Node_{hashlib.md5(title.encode()).hexdigest()[:8].upper()}")
            status = "APPROVED (Actionable)" if f in actionable_findings else "FILTERED / TRIAGED"
            provenance_rows.append(f"| `{node_id}` | {f.get('source', 'API')} | [{title}...]({f.get('url', '#')}) | {status} |")
        
        prov_header = "| Node ID | Origin Source | Document Title / URL | Pipeline Status |\n|---|---|---|---|"
        provenance_table = prov_header + "\n" + "\n".join(provenance_rows) if provenance_rows else "No source records indexed."

        # 4. Assemble Final Master Document
        memo_content = f"""# 📝 REGULATORY & PUBLIC AFFAIRS MEMORANDUM

**TO:** Scott Astrada, Director of Public Policy  
**FROM:** Regulatory Risk & Policy Strategy Swarm  
**DATE:** {today_str}  
**SUBJECT:** Executive Policy Briefing: Threat Matrix & White-Space Risk Analysis  

---

{ai_report_body}

---

## 🔗 10. High-Signal Evidence & Docket Deep-Dive
{details_section}

---

## 🏛️ 11. Source Provenance & Decision Lineage Matrix
{provenance_table}
"""

        report_path = os.path.join(report_dir, "report.md") if report_dir else "report.md"
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)
            
        with open(report_path, "w", encoding='utf-8') as f:
            f.write(memo_content)
            
        logging.info(f"[{self.agent_id}] ✅ Report successfully generated at: {report_path}")
        return {
            "report_path": report_path,
            "generation_status": "completed",
            "actionable_count": len(actionable_findings),
            "rejected_count": len(rejected_findings),
        }
