path = 'agents/legislative_monitor.py'
with open(path, 'r') as f:
    content = f.read()

# Add the registry import
if "from infrastructure.source_registry import SourceRegistry" not in content:
    content = "from infrastructure.source_registry import SourceRegistry\n" + content

# Refactor the URL retrieval to use the registry
# We replace the hardcoded URLs with lookups
old_cg = 'cg_url = f"https://api.congress.gov/v3/bill?api_key={cg_key}&limit=1"'
old_ls = 'ls_url = f"https://api.legiscan.com/?key={ls_key}&op=getSearch&state=US&query=finance"'

new_cg = 'registry = SourceRegistry()\n        cg_meta = registry.get_source_metadata("congress_gov")\n        cg_url = f"{cg_meta[\'url\']}bill?api_key={cg_key}&limit=1"'
new_ls = 'ls_meta = registry.get_source_metadata("legiscan")\n        ls_url = f"{ls_meta[\'url\']}?key={ls_key}&op=getSearch&state=US&query=finance"'

content = content.replace(old_cg, new_cg)
content = content.replace(old_ls, new_ls)

with open(path, 'w') as f:
    f.write(content)
print("LegislativeMonitorAgent integrated with SourceRegistry.")
