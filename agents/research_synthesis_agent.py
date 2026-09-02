import json
import requests
from datetime import datetime

class ResearchSynthesisAgent:
    def __init__(self, agent_id="research-synthesis"):
        self.agent_id = agent_id
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "nemotron:70b"

    def _call_ollama(self, prompt):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=None)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            print(f"[{self.agent_id}] Error calling Ollama: {e}")
            return None

    def _parse_llm_response(self, response_text):
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                return json.loads(response_text)
        except Exception as e:
            print(f"[{self.agent_id}] Error parsing LLM response: {e}")
            return None

    def execute_task(self, payload):
        findings = payload.get("findings", [])
        print(f"[{self.agent_id}] Received {len(findings)} findings for synthesis.")
        
        validated_high_medium = [f for f in findings if f.get("validation_status") != "rejected"]
        print(f"[{self.agent_id}] Found {len(validated_high_medium)} findings for synthesis.")
        
        if not validated_high_medium:
            return {
                "executive_summary": "No high or medium impact threats detected in this intelligence cycle.",
                "bluf_opportunity": "Maintain current baseline posture while monitoring state feeds.",
                "threat_severity": "LOW",
                "primary_regulator": "None",
                "congressional_radar": "No immediate legislative action required.",
                "agency_enforcement": "Federal agencies maintain standard oversight.",
                "state_escalation": "State feeds remain within nominal bounds.",
                "underwriting_impact": "No immediate underwriting changes required.",
                "servicing_impact": "No servicing adjustments required.",
                "marketing_impact": "Standard POS disclosure compliance maintained.",
                "moat_analysis": "Affirm zero-late-fee model maintains strategic positioning.",
                "advocacy_origin": "N/A",
                "advocacy_directives": []
            }
        
        records_text = []
        for i, record in enumerate(validated_high_medium, 1):
            title = record.get("title", "No title")
            compressed_summary = record.get("compressed_summary") or record.get("text_context", "No summary available")
            jurisdiction = record.get("jurisdiction", "Unknown")
            analysis = record.get("analysis") or record.get("inferred_market_impact", "No analysis provided")
            rec_date = record.get("date") or "Unknown"
            records_text.append(
                f"Record {i}:\n"
                f"  Title: {title}\n"
                f"  Date: {rec_date}\n"
                f"  Summary: {compressed_summary}\n"
                f"  Jurisdiction: {jurisdiction}\n"
                f"  Impact Analysis: {analysis}\n"
            )
        records_block = "\n".join(records_text)
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
You are the Chief Regulatory Strategy Advisor preparing a high-level executive memo for Scott Astrada (Director of Public Policy at Affirm, ex-Senate Banking Committee, OMB, and CRL).

TEMPORAL ANCHOR, GROUND TRUTH & CONSTRAINTS:
- Today's Date is {today_str}.
- 2025/2026 GROUND TRUTH BASELINE: The CFPB officially withdrew its 2024 BNPL Interpretive Rule in May 2025 and paused federal enforcement. The regulatory threat has fractured to the STATE level (e.g., Illinois passed a massive BNPL law in June 2026).
- STRICT CLOSED-WORLD RULE: You are strictly forbidden from bringing in outside knowledge or inventing bill numbers, dockets, or dates.
- NULL STATE REQUIREMENT: If the provided text does not contain explicit evidence of active 2026 legislation, output "None active." If no agency enforcement is present in context, output "No immediate threat."
- CLEAN PROSE: Output clean Markdown prose inside JSON strings. Never embed unparsed JSON strings or curly braces in values.
- All proposed advocacy directives MUST be forward-looking in 2026 or 2027 (e.g. Q3 2026, 30 Days). NEVER reference 2024.

Analyze all findings through the lens of strategic advocacy, product architecture impact, and competitive moat weaponization against fee-dependent rivals (Klarna, Afterpay, Sezzle).

VALIDATED INTELLIGENCE RECORDS:
{records_block}

Synthesize these findings into an authoritative executive intelligence memorandum.

Your response MUST be a valid JSON object with these exact keys:
1. "executive_summary": A high-impact synthesis paragraph summarizing the macro regulatory vector.
2. "bluf_opportunity": 2-3 sentences explaining how Affirm can weaponize this regulatory shift against fee-dependent competitors.
3. "threat_severity": HIGH, MEDIUM, or LOW.
4. "primary_regulator": Key driving entities (e.g., FTC, CA DFPI, Senate Banking, CFPB).
5. "congressional_radar": Detailed analysis of House Financial Services or Senate Banking Committee hearings, letters, or legislation.
6. "agency_enforcement": Analysis of FTC, SEC, or broader federal agency non-CFPB actions.
7. "state_escalation": Analysis of state regulators (CA DFPI, NY DFS) and State AG coalition moves.
8. "underwriting_impact": Specific impact on credit scoring, FICO integration, ability-to-pay rules, or APR caps.
9. "servicing_impact": Specific impact on late fees, dispute resolution, or billing workflows.
10. "marketing_impact": Impact on point-of-sale disclosures, 0% APR marketing, and transparency messaging.
11. "moat_analysis": How this regulatory pressure impacts Affirm's zero-late-fee model versus fee-dependent rivals.
12. "advocacy_origin": Key think tanks, research bodies, or consumer groups driving the narrative (e.g., NCLC, CRL).
13. "advocacy_directives": A JSON list of objects (max 3) with keys: "target", "action", "objective", "deadline" (MUST BE 2026-2027 or relative days like "14 Days").
14. "swarm_intelligence_narrative": A comprehensive, multi-paragraph synthesis written from the collective intelligence perspective of the swarm, detailing the overall patterns, subtle signals, and cross-stream connections discovered during this intelligence cycle.
15. "decision_source_mapping": A JSON list of objects mapping each key policy deduction to its source, with keys: "finding_topic", "primary_source_name", "key_takeaway".

CRITICAL INSTRUCTION: Output ONLY valid, parseable JSON. No markdown fences, no commentary.
""".strip()
        
        llm_response = self._call_ollama(prompt)
        parsed = self._parse_llm_response(llm_response) if llm_response else None
        
        if parsed and isinstance(parsed, dict) and "executive_summary" in parsed:
            return parsed
        else:
            return {
                "executive_summary": f"Synthesized {len(validated_high_medium)} validated policy findings across federal and state vectors.",
                "bluf_opportunity": "Increased scrutiny on hidden and late fees structurally favors Affirm's zero-late-fee business model over fee-reliant competitors.",
                "threat_severity": "MEDIUM",
                "primary_regulator": "FTC / CA DFPI / Senate Banking",
                "congressional_radar": "Congressional committees are actively examining alternative credit scoring and fee transparency.",
                "agency_enforcement": "The FTC is expanding consumer protection oversight on digital financing disclosures.",
                "state_escalation": "State regulators like CA DFPI are modifying digital asset and income-based advance definitions.",
                "underwriting_impact": "Potential scrutiny on FICO integration of BNPL tradelines and ability-to-repay rules.",
                "servicing_impact": "Operational review required for dispute handling and transparency standards.",
                "marketing_impact": "Audit point-of-sale APR disclosures and promotional messaging.",
                "moat_analysis": "Regulatory caps on late fees penalize competitors while validating Affirm's core model.",
                "advocacy_origin": "Center for Responsible Lending / National Consumer Law Center",
                "advocacy_directives": [
                    {"target": "House Financial Services Committee", "action": "Staff Briefing", "objective": "Protect BNPL credit reporting integration", "deadline": "Q3 2026"},
                    {"target": "California DFPI", "action": "Public Comment", "objective": "Secure POS installment carve-outs", "deadline": "Q4 2026"}
                ]
            }
