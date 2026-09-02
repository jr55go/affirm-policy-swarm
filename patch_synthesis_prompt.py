import os

file_path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/research_synthesis_agent.py")

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update the JSON keys requested in the prompt
old_prompt_keys = """Your response MUST be a valid JSON object with these exact keys:
8. "executive_summary": A concise paragraph synthesizing the overall policy vector.
9. "threat_velocity": A velocity rating and rationale (e.g. "High (300% surge in filings over 72 hours)").
10. "sector_exposure": Estimated sector financial/compliance risk (e.g. "$100M - $150M sector impact").
11. "strategic_directives": A JSON list of 3 concise actionable policy/public affairs directives for Affirm.
12. "competitor_impact": A JSON list of 3 distinct bullet points analyzing specific risk exposure for Affirm vs. competitors (Klarna, Afterpay, Sezzle)."""

new_prompt_keys = """Your response MUST be a valid JSON object with these exact keys:
1. "executive_summary": A concise paragraph synthesizing the overall policy vector.
2. "threat_severity": A single word rating: [HIGH / MEDIUM / LOW].
3. "primary_regulator": The primary regulatory body driving this (e.g., CFPB, NY DFS).
4. "underwriting_impact": 1 sentence on how this impacts ability-to-pay or credit checks.
5. "servicing_impact": 1 sentence on how this impacts late fees, disputes, or billing.
6. "marketing_impact": 1 sentence on how this impacts POS disclosures or 0% APR marketing.
7. "moat_analysis": 1 sentence analyzing how this uniquely impacts Affirm vs. competitors (Klarna, Afterpay).
8. "advocacy_origin": The think tank or origin of the policy pressure (e.g., NCLC).
9. "regulatory_deadlines": A JSON list of objects with keys: "event", "date", "days_remaining", "action"."""

# If the regex doesn't match perfectly, we will just brute force replace the whole block
old_prompt_block = """        prompt = f\"\"\"
You are a senior regulatory and public affairs policy analyst synthesizing legislative and regulatory records for the Buy Now, Pay Later (BNPL) sector.

Here are the validated records:

{records_block}

Synthesize these findings into executive-level intelligence for Affirm's policy leadership. Analyze how these developments impact Affirm compared to competitors like Klarna, Afterpay, and Sezzle.

Your response MUST be a valid JSON object with these exact keys:
1. "executive_summary": A concise paragraph synthesizing the overall policy vector.
2. "threat_velocity": A velocity rating and rationale (e.g. "High (300% surge in filings over 72 hours)").
3. "sector_exposure": Estimated sector financial/compliance risk (e.g. "$100M - $150M sector impact").
4. "strategic_directives": A JSON list of 3 concise actionable policy/public affairs directives for Affirm.
5. "competitor_impact": A JSON list of 3 distinct bullet points analyzing specific risk exposure for Affirm vs. competitors (Klarna, Afterpay, Sezzle).

CRITICAL INSTRUCTION: You are a machine-to-machine API. Output ONLY valid, parseable JSON. Do not include markdown formatting or prose.
\"\"\".strip()"""

new_prompt_block = """        prompt = f\"\"\"
You are a senior regulatory and public affairs policy analyst synthesizing legislative and regulatory records for the Buy Now, Pay Later (BNPL) sector.

Here are the validated records:

{records_block}

Synthesize these findings into executive-level intelligence for Affirm's policy leadership. Focus on product-level impact and competitive moats.

Your response MUST be a valid JSON object with these exact keys:
1. "executive_summary": A concise paragraph synthesizing the overall policy vector.
2. "threat_severity": A single word rating: HIGH, MEDIUM, or LOW.
3. "primary_regulator": The primary regulatory body driving this (e.g., CFPB, NY DFS).
4. "underwriting_impact": 1 sentence on how this impacts ability-to-pay or credit checks.
5. "servicing_impact": 1 sentence on how this impacts late fees, disputes, or billing.
6. "marketing_impact": 1 sentence on how this impacts POS disclosures or 0% APR marketing.
7. "moat_analysis": 1 sentence analyzing how this uniquely impacts Affirm vs competitors.
8. "advocacy_origin": The think tank or origin of the policy pressure (e.g., NCLC).
9. "regulatory_deadlines": A JSON list of objects (max 2) with keys: "event", "date", "days_remaining", "action".

CRITICAL INSTRUCTION: Output ONLY valid, parseable JSON. No markdown, no prose.
\"\"\".strip()"""

code = code.replace(old_prompt_block, new_prompt_block)

# 2. Update the fallback parsing (lines 110-117)
old_parse = """                if parsed and isinstance(parsed, dict) and "executive_summary" in parsed:
                    return {
                        "executive_summary": str(parsed.get("executive_summary", "")),
                        "threat_velocity": str(parsed.get("threat_velocity", "Standard")),
                        "sector_exposure": str(parsed.get("sector_exposure", "N/A")),
                        "strategic_directives": parsed.get("strategic_directives", []) if isinstance(parsed.get("strategic_directives"), list) else [str(parsed.get("strategic_directives"))],
                        "competitor_impact": parsed.get("competitor_impact", []) if isinstance(parsed.get("competitor_impact"), list) else [str(parsed.get("competitor_impact"))]
                    }"""

new_parse = """                if parsed and isinstance(parsed, dict) and "executive_summary" in parsed:
                    return {
                        "executive_summary": str(parsed.get("executive_summary", "")),
                        "threat_severity": str(parsed.get("threat_severity", "MEDIUM")),
                        "primary_regulator": str(parsed.get("primary_regulator", "Multiple")),
                        "underwriting_impact": str(parsed.get("underwriting_impact", "Standard monitoring required.")),
                        "servicing_impact": str(parsed.get("servicing_impact", "Standard monitoring required.")),
                        "marketing_impact": str(parsed.get("marketing_impact", "Standard monitoring required.")),
                        "moat_analysis": str(parsed.get("moat_analysis", "No immediate moat impact detected.")),
                        "advocacy_origin": str(parsed.get("advocacy_origin", "Unknown")),
                        "regulatory_deadlines": parsed.get("regulatory_deadlines", []) if isinstance(parsed.get("regulatory_deadlines"), list) else []
                    }"""

code = code.replace(old_parse, new_parse)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("✅ Successfully patched research_synthesis_agent.py with the Astrada-Tier data schema!")
