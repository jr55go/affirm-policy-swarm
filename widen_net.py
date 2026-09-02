import os

path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/discovery_agent.py")
with open(path, "r") as f:
    content = f.read()

# Replace the overly strict vector generator with a smarter one
old_func = """    def generate_vectors(self, core_query):
        \"\"\"Expands the query into predictive OSINT vectors.\"\"\"
        return [
            # 1. Consumer Sentiment / Pain Points
            f'site:reddit.com/r/personalfinance OR site:reddit.com/r/povertyfinance "{core_query}" (ruined credit OR predatory OR hidden fees)',
            # 2. Regulator Rhetoric (Pre-law)
            f'site:consumerfinance.gov/about-us/newsroom OR site:ftc.gov/news-events "{core_query}" OR "buy now pay later" speech',
            # 3. Think Tanks & Policy Blueprints
            f'site:brookings.edu OR site:americanactionforum.org "buy now pay later" OR "{core_query}"',
            # 4. Market Signals / Compliance panic
            f'site:wsj.com OR site:bloomberg.com "{core_query}" (compliance OR probe OR scrutiny)'
        ]"""

new_func = """    def generate_vectors(self, core_query):
        \"\"\"Expands the query into predictive OSINT vectors using just the entity name.\"\"\"
        # Strip out academic words so we catch raw internet chatter
        base_term = core_query.lower().replace(" policy", "").replace(" regulation", "").strip()
        
        return [
            # 1. Consumer Sentiment / Pain Points
            f'site:reddit.com/r/personalfinance OR site:reddit.com/r/povertyfinance "{base_term}" (ruined OR predatory OR hidden fees OR trap)',
            # 2. Regulator Rhetoric (Pre-law)
            f'site:consumerfinance.gov/about-us/newsroom OR site:ftc.gov/news-events "{base_term}" OR "buy now pay later" speech',
            # 3. Think Tanks & Policy Blueprints
            f'site:brookings.edu OR site:americanactionforum.org "buy now pay later" OR "{base_term}"',
            # 4. Market Signals / Compliance panic
            f'site:wsj.com OR site:bloomberg.com "{base_term}" (compliance OR probe OR scrutiny OR lawsuit)'
        ]"""

if old_func in content:
    with open(path, "w") as f:
        f.write(content.replace(old_func, new_func))
    print("[+] Discovery vectors broadened. It will now search for 'affirm' instead of 'affirm policy'.")
else:
    print("[-] Could not find the exact function. It may have already been modified.")
