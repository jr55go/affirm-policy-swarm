import requests
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from infrastructure.source_registry import SourceRegistry

class LegislativeMonitorAgent:
    def __init__(self, agent_id="leg-monitor"):
        self.agent_id = agent_id
        self.name = "Legislative Monitor Agent"
        print(f"2026-06-24 18:50:00 - agent.{self.agent_id} - INFO - Model Assigned: nemotron:70b | Temp=0.1")

    def execute_task(self, payload):
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
                    url = f"{meta['url']}bill?api_key={cg_key}&limit=250"
                    response = requests.get(url, timeout=8)
                    response.raise_for_status()
                    data = response.json()
                    if "bills" in data and data["bills"]:
                        for bill in data["bills"]:
                            title = bill.get('title', '')
                            records.append({
                                "source": "Congress.gov", "jurisdiction": "US Federal",
                                "bill_id": f"LIVE-FED-BILL-{bill.get('number', '')}",
                                "title": title,
                                "text_context": title,
                                "url": bill.get('url', '')
                            })
                
                elif source_name == "legiscan":
                    url = f"{meta['url']}?key={ls_key}&op=getSearch&state=US&query=finance"
                    response = requests.get(url, timeout=8)
                    response.raise_for_status()
                    data = response.json()
                    if "searchresult" in data and data["searchresult"]:
                        results = [v for k, v in data["searchresult"].items() if k != "summary"]
                        for bill in results:
                            title = bill.get('title', '')
                            records.append({
                                "source": "LegiScan", "jurisdiction": "US State Level",
                                "bill_id": f"LIVE-STATE-BILL-{bill.get('bill_number', '')}",
                                "title": title,
                                "text_context": title,
                                "url": bill.get('url', '')
                            })
                            
            except Exception as e:
                print(f"Error fetching from {source_name}: {e}")
                registry.update_source_health(source_name, success=False, error=str(e))
                continue
            
            registry.update_source_health(source_name, success=True)
            
        return {"agent_id": self.agent_id, "records": records, "status": "COMPLETED"}
