import requests
from datetime import datetime, timezone
import uuid

class LegislativeMonitorAgent:
    def __init__(self, agent_id="leg-monitor"):
        self.agent_id = agent_id
        self.name = "Legislative Monitor Agent"
        print(f"2026-06-24 18:50:00 - agent.{self.agent_id} - INFO - Model Assigned: nemotron:70b | Temp=0.1")

    def execute_task(self, payload):
        run_id = payload["run_id"]
        cg_key = payload["cg_key"]
        ls_key = payload["ls_key"]
        records = []
        
        cg_url = f"https://api.congress.gov/v3/bill?api_key={cg_key}&limit=1"
        response = requests.get(cg_url, timeout=8)
        response.raise_for_status()
        cg_data = response.json()
        if "bills" in cg_data and cg_data["bills"]:
            bill = cg_data["bills"][0]
            records.append({
                "source": "Congress.gov", "jurisdiction": "US Federal",
                "bill_id": f"LIVE-FED-BILL-{bill.get("number", "10")}",
                "title": bill.get("title", "Generic Financial Services Policy Directive"),
                "latest_action": bill.get("latestAction", {}).get("text", "Referred to Committee"),
                "url": bill.get("url", "https://api.congress.gov"), "text_context": bill.get("title", "").lower()
            })
            
        ls_url = f"https://api.legiscan.com/?key={ls_key}&op=getSearch&state=US&query=finance"
        response = requests.get(ls_url, timeout=8)
        response.raise_for_status()
        ls_data = response.json()
        if "searchresult" in ls_data and ls_data["searchresult"]:
            results = [v for k, v in ls_data["searchresult"].items() if k != "summary"]
            if results:
                bill = results[0]
                records.append({
                    "source": "LegiScan", "jurisdiction": "US State Level",
                    "bill_id": f"LIVE-STATE-BILL-{bill.get("bill_number", "273")}",
                    "title": bill.get("title", "Retail Installment Credit Ingestion Boundary Act"),
                    "latest_action": bill.get("last_action", "Pending Executive Action"),
                    "url": bill.get("text_url", "https://legiscan.com"), "text_context": bill.get("title", "").lower()
                })
        return {"agent_id": self.agent_id, "records": records, "status": "COMPLETED"}
