path = 'agents/validation_agent.py'
with open(path, 'r') as f:
    content = f.read()

# 1. Update the prompt to include the actual text of the finding and enforce the schema
old_prompt_call = """                    llm_result = self.call_llm_json(
                        prompt="Assess if this finding's BNPL terms detection is accurate and sufficient for validation. Return JSON only.",
                        schema_name="validation_challenge","""

new_prompt_call = """                    
                    prompt_text = (
                        "You are the Validation Agent. Review this legislative finding: \\n"
                        f"{f} \\n\\n"
                        "Determine if it is a true 'Buy Now, Pay Later' (BNPL) policy issue or a false positive. "
                        "Return ONLY a JSON object with these exact keys: "
                        "'validation_status' (string: 'approved' or 'rejected'), "
                        "'evidence_sufficient' (boolean), "
                        "'false_positive_risk' (string: 'low', 'medium', or 'high'), "
                        "'validation_reason' (string explaining your conclusion), "
                        "'confidence' (string: 'low', 'medium', or 'high')."
                    )
                    llm_result = self.call_llm_json(
                        prompt=prompt_text,
                        schema_name="validation_challenge","""

if old_prompt_call in content:
    content = content.replace(old_prompt_call, new_prompt_call)
    with open(path, 'w') as f:
        f.write(content)
    print("ValidationAgent patched: Added LLM challenge context and schema enforcement.")
else:
    print("Failed to find the target block in ValidationAgent. Manual inspection needed.")
