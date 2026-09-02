import os

WORKSPACE = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm")

stub_methods = """
    # --- ABSTRACT METHOD STUBS TO PREVENT INITIALIZATION CRASH ---
    def deduplicate(self, records):
        '''Default passthrough deduplication'''
        return records

    def metadata(self):
        '''Default metadata'''
        return {"source": self.source_name, "status": "active"}

    def rate_limit(self):
        '''Default rate limit handler'''
        pass
"""

files_to_patch = [
    "infrastructure/connectors/federal_register_connector.py",
    "infrastructure/connectors/regulations_gov_connector.py",
    "infrastructure/connectors/cfpb_connector.py"
]

for file in files_to_patch:
    full_path = os.path.join(WORKSPACE, file)
    if os.path.exists(full_path):
        with open(full_path, "a") as f:
            f.write(f"\n{stub_methods}\n")
        print(f"[+] Added abstract method stubs to {file}")

print("\n[+] Abstract Base Class patches complete.")
