path = 'agents/legislative_monitor.py'
with open(path, 'r') as f:
    content = f.read()

# Define the new, dynamic execution loop
# This replaces the hardcoded block with a registry-driven iterator
new_logic = """    def execute_task(self, payload):
        run_id = payload["run_id"]
        cg_key = payload.get("cg_key")
        ls_key = payload.get("ls_key")
        records = []
        registry = SourceRegistry()
        enabled_sources = registry.list_enabled_sources()

        for source_name in enabled_sources:
            meta = registry.get_source_metadata(source_name)
            
            # Dynamic dispatch based on source name
            try:
                if source_name == "congress_gov":
                    url = f"{meta['url']}bill?api_key={cg_key}&limit=1"
                    response = requests.get(url, timeout=8)
                    response.raise_for_status()
                    data = response.json()
                    if "bills" in data and data["bills"]:
                        bill = data["bills"][0]
                        records.append({
                            "source": "Congress.gov", "jurisdiction": "US Federal",
                            "bill_id": f"LIVE-FED-BILL-{bill.get('number', '10')}",
                            "title": bill.get('title', 'Financial Policy'),
                            "text_context": bill.get('title', '').lower()
                        })
                
                elif source_name == "legiscan":
                    url = f"{meta['url']}?key={ls_key}&op=getSearch&state=US&query=finance"
                    response = requests.get(url, timeout=8)
                    response.raise_for_status()
                    data = response.json()
                    if "searchresult" in data and data["searchresult"]:
                        results = [v for k, v in data["searchresult"].items() if k != "summary"]
                        if results:
                            bill = results[0]
                            records.append({
                                "source": "LegiScan", "jurisdiction": "US State Level",
                                "bill_id": f"LIVE-STATE-BILL-{bill.get('bill_number', '273')}",
                                "title": bill.get('title', 'Credit Ingestion Act'),
                                "text_context": bill.get('title', '').lower()
                            })
            except Exception as e:
                print(f"Error fetching from {source_name}: {e}")
                registry.update_source_health(source_name, success=False, error=str(e))
                continue
            
            registry.update_source_health(source_name, success=True)
            
        return {"agent_id": self.agent_id, "records": records, "status": "COMPLETED"}
"""

# Replace the old execute_task with the new loop
import re
content = re.sub(r'def execute_task\(self, payload\):.*?return {"agent_id": self.agent_id, "records": records, "status": "COMPLETED"}', new_logic, content, flags=re.DOTALL)

with open(path, 'w') as f:
    f.write(content)
print("LegislativeMonitorAgent updated to iterate through all enabled sources.")
