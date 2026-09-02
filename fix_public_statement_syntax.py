import os

path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/public_statement_monitor_agent.py")

with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# The broken snippet causing the SyntaxError
broken_block = """            try:
                search_items = self._perform_live_search_fallback(f"{source_name.replace('_', ' ')} CFPB Twitter public statement Buy Now Pay Later")
            if search_items:"""

# The corrected snippet with proper indentation inside the try block
fixed_block = """            try:
                search_items = self._perform_live_search_fallback(f"{source_name.replace('_', ' ')} CFPB Twitter public statement Buy Now Pay Later")
                if search_items:"""

if broken_block in code:
    code = code.replace(broken_block, fixed_block)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print("✅ Successfully repaired try/if indentation in public_statement_monitor_agent.py")
else:
    print("⚠️ Broken block pattern not matched exactly. Inspecting manual edits...")

