import os
import json
import requests
import re
import pandas as pd

class LegislativeEnricher:
    def __init__(self):
        self.api_key = os.environ.get("CONGRESS_GOV_API_KEY") or os.environ.get("CONGRESS_API_KEY")
        self.data_dir = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/data/cel_les_data")
        
    def _load_cel_data(self, chamber):
        file_path = os.path.join(self.data_dir, f"{chamber}_les.json")
        if not os.path.exists(file_path):
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _extract_bill_id(self, text):
        match = re.search(r'(H\.?R\.?|S\.?)\s*(\d+)', text, re.IGNORECASE)
        if match:
            chamber_prefix = match.group(1).replace(".", "").upper()
            bill_type = "hr" if chamber_prefix == "HR" else "s"
            return bill_type, match.group(2)
        return None, None

    def enrich(self, target_text):
        if not self.api_key:
            return {"error": "Missing CONGRESS_GOV_API_KEY environment variable."}

        bill_type, bill_number = self._extract_bill_id(target_text)
        if not bill_type:
            return {"error": "No valid bill number found in text."}
        
        url = f"https://api.congress.gov/v3/bill/119/{bill_type}/{bill_number}?api_key={self.api_key}&format=json"
        
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            bill_data = resp.json().get("bill", {})
            
            sponsors = bill_data.get("sponsors", [{}])
            sponsor_name = sponsors[0].get("lastName", "") if sponsors else "Unknown"
            cosponsor_count = bill_data.get("cosponsors", {}).get("count", 0)
            
            chamber = "house" if bill_type == "hr" else "senate"
            cel_records = self._load_cel_data(chamber)
            
            sponsor_les = "Unknown (Freshman or Unlisted)"
            for record in cel_records:
                thomas_name = str(record.get("thomas_name", "")).lower()
                if sponsor_name.lower() in thomas_name and sponsor_name:
                    les_raw = record.get("les", 0)
                    sponsor_les = round(float(les_raw), 3) if pd.notnull(les_raw) else "Unknown"
                    break
                    
            return {
                "bill_type": bill_type.upper(),
                "bill_number": bill_number,
                "live_cosponsors": cosponsor_count,
                "sponsor_last_name": sponsor_name,
                "sponsor_historical_les_score": sponsor_les,
                "congress_api_status": "Success"
            }
        except Exception as e:
            return {"error": f"API request failed: {e}"}

if __name__ == "__main__":
    enricher = LegislativeEnricher()
    print(json.dumps(enricher.enrich("The committee reviewed H.R. 1 today."), indent=2))
