import requests
import logging
from datetime import datetime, timedelta

class SECEdgarAgent:
    BASE = "https://efts.sec.gov/LATEST/search-index"

    def __init__(self, agent_id="SECEdgarAgent"):
        self.agent_id = agent_id
        # SEC requires explicit User-Agent format: Sample Company Name AdminContact@<sample company domain>.com
        self.headers = {
            "User-Agent": "AffirmPolicySwarm research@affirm.com",
            "Accept-Encoding": "gzip, deflate",
            "Host": "efts.sec.gov"
        }

    def execute_task(self, payload={}):
        records = []
        yesterday = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        
        queries = [
            "buy now pay later", "BNPL", "Affirm Holdings",
            "Klarna", "Afterpay", "point of sale financing"
        ]
        
        for q in queries:
            try:
                params = {
                    "q": f'"{q}"',
                    "dateRange": "custom",
                    "startdt": yesterday,
                    "enddt": today,
                }
                resp = requests.get(self.BASE, params=params, headers=self.headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    for hit in data.get("hits", {}).get("hits", [])[:3]:
                        src = hit.get("_source", {})
                        entity_name = src.get("entity_name", "Unknown Entity")
                        form_type = src.get("form_type", "Filing")
                        file_date = src.get("file_date", today)
                        file_num = src.get("file_num", "")
                        
                        records.append({
                            "title": f"SEC EDGAR Filing ({form_type}): {entity_name}",
                            "snippet": f"Entity: {entity_name} | Form: {form_type} | Filed: {file_date} | Query: {q}",
                            "url": f"https://www.sec.gov/edgar/browse/?CIK={file_num}",
                            "source": "SEC EDGAR Official Feed",
                            "section_tag": "internal_alignment" if "Affirm" in entity_name else "bnpl_competitive",
                            "date": file_date,
                            "text_context": f"Official SEC Regulatory Filing for {entity_name} regarding {q}. Form type: {form_type} on {file_date}."
                        })
            except Exception as e:
                logging.warning(f"[{self.agent_id}] SEC search warning for '{q}': {e}")
                
        logging.info(f"[{self.agent_id}] SEC EDGAR sweep complete. Harvested {len(records)} filings.")
        return {"records": records}
