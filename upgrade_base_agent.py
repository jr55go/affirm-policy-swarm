import re

path = 'agents/base_agent.py'
with open(path, 'r') as f:
    content = f.read()

# Check if we already injected the LLM logic to avoid duplicates
if "def call_llm_json(" not in content:
    llm_method = """
    def call_llm_json(self, prompt: str, schema_name: str = "default", temperature: float = 0.2, max_tokens: int = 2048) -> Dict[str, Any]:
        \"\"\"Call local Ollama Qwen model and enforce JSON output.\"\"\"
        import urllib.request
        import json
        
        self.logger.info(f"Calling LLM ({self.model_name}) for schema: {schema_name}")
        
        payload = {
            "model": self.model_name,
            "prompt": prompt + "\\n\\nRespond ONLY with valid, parsable JSON.",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            # Assumes local Ollama API for Qwen 32b
            req = urllib.request.Request(
                "http://localhost:11434/api/generate", 
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                
            # Parse the JSON string returned by the model
            llm_response = result.get("response", "{}")
            return json.loads(llm_response)
            
        except Exception as e:
            self.logger.error(f"LLM Call Failed: {str(e)}")
            raise e
"""
    
    # Inject right before the query_graph_state method
    content = content.replace("    def query_graph_state", llm_method + "\n    def query_graph_state")
    
    with open(path, 'w') as f:
        f.write(content)
    print("Successfully injected real LLM capabilities into BaseAgent.")
else:
    print("BaseAgent already has LLM capabilities.")
