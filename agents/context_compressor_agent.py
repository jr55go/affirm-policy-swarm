import json
import requests

class ContextCompressorAgent:
    def __init__(self, agent_id="ContextCompressorAgent"):
        self.agent_id = agent_id
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "qwen2.5-coder:32b"

    def _call_ollama(self, prompt):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=None)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            print(f"[{self.agent_id}] Error calling Ollama: {e}")
            return None

    def _parse_llm_response(self, response_text):
        # We expect a bulleted list, but we'll just return the text as is.
        # However, we can try to extract bullets if needed.
        return response_text.strip()

    def execute_task(self, payload):
        findings = payload.get("findings", [])
        compressed_findings = []
        
        print(f"[{self.agent_id}] Compressing {len(findings)} findings...")
        
        for finding in findings:
            # We are going to compress the text_context
            text_context = finding.get("text_context", "")
            if not text_context:
                # If there's no context, we skip compression and set empty summary
                finding["compressed_summary"] = ""
                compressed_findings.append(finding)
                continue

            # Construct prompt for LLM to compress the text into 3 bullets
            prompt = f"""
You are an expert policy analyst tasked with condensing regulatory/legislative text into a concise summary.
Focus only on policy changes and risks to the BNPL (Buy Now, Pay Later) sector.

Original Text:
{text_context}

Please provide a summary in the form of exactly 3 bullet points. Each bullet point should be a concise sentence.
Do not include any extra text or explanation—only the 3 bullet points.

Example format:
- First bullet point about policy change.
- Second bullet point about associated risk.
- Third bullet point about implication or action.

Only output the 3 bullet points.
""".strip()

            # Call the LLM
            llm_response = self._call_ollama(prompt)
            
            if llm_response is None:
                print(f"[{self.agent_id}] LLM call failed for finding: {finding.get('title', 'Unknown')}. Using fallback.")
                truncated = text_context[:200] + "..." if len(text_context) > 200 else text_context
                finding["compressed_summary"] = f"- {truncated}"
                finding["compression_fallback"] = True
                finding["pipelineStatus"] = "rejected"
            else:
                # Use the LLM response as the compressed summary
                finding["compressed_summary"] = llm_response.strip()
            
            compressed_findings.append(finding)
            
        return {"findings": compressed_findings, "status": "COMPLETED"}