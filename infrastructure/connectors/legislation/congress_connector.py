import os
import json
import requests
from datetime import datetime
from typing import Dict, Any, List
from affirm_policy_swarm.infrastructure.connectors.base_connector import BaseSourceConnector
from affirm_policy_swarm.infrastructure.connectors.normalization import NormalizedPolicyEvent

class CongressConnector(BaseSourceConnector):
    def __init__(self):
        self.api_key = None
        self.base_url = "https://api.congress.gov/v3"
        self.session = requests.Session()

    def connect(self) -> bool:
        self.api_key = os.environ.get("CONGRESS_GOV_API_KEY")
        if not self.api_key:
            return False
        self.session.headers.update({"x-api-key": self.api_key})
        return True

    def health_check(self) -> str:
        if not self.connect():
            return "AUTH_FAILED"
        try:
            response = self.session.get(f"{self.base_url}/bill")
            if response.status_code == 200:
                return "HEALTHY"
            elif response.status_code == 429:
                return "RATE_LIMITED"
            return "DEGRADED"
        except Exception:
            return "OFFLINE"

    def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        if not self.api_key:
            self.connect()

        # Example fetch logic for recent bills
        response = self.session.get(f"{self.base_url}/bill", params={"limit": 5, "format": "json"})
        response.raise_for_status()

        data = response.json()
        bills = data.get("bills", [])

        # Keyword Bouncer: filter for finance-relevant legislation
        TARGET_KEYWORDS = ["credit", "lending", "bnpl", "buy now, pay later", "industrial loan", "bank", "charter", "consumer finance", "interest rate"]
        # Convert keywords to lowercase for case-insensitive matching
        keywords = [k.lower() for k in TARGET_KEYWORDS]
        filtered_bills = []
        for bill in bills:
            title = bill.get('title', '').lower()
            summary = bill.get('summary', '').lower()
            # Check if any keyword appears in title or summary
            if any(keyword in title or keyword in summary for keyword in keywords):
                filtered_bills.append(bill)

        return filtered_bills

    def normalize(self, raw_payload: Dict[str, Any]) -> NormalizedPolicyEvent:
        """
        Maps the Congress.gov API JSON into the NormalizedPolicyEvent dataclass.
        """
        try:
            congress_num = str(raw_payload.get("congress", ""))
            bill_type = str(raw_payload.get("type", "")).upper()
            bill_number = str(raw_payload.get("number", ""))
            title = raw_payload.get("title", "Unknown Title")

            # Construct public URL
            public_url = ""
            if congress_num and bill_type and bill_number:
                public_url = f"https://www.congress.gov/bill/{congress_num}th-congress/{bill_type.lower()}-bill/{bill_number}"

            return NormalizedPolicyEvent(
                source_name="Congress.gov",
                source_type="Legislation",
                jurisdiction="Federal",
                title=title,
                summary=raw_payload.get("updateDate", "No summary provided."),
                event_type="Bill Update",
                event_date=raw_payload.get("latestAction", {}).get("actionDate", datetime.utcnow().isoformat()),
                url=public_url,
                organization=["US Congress"],
                people=[],
                committees=[],
                agencies=[],
                legislation=[f"{bill_type} {bill_number}"],
                topics=[],
                keywords=[],
                confidence="high",
                evidence=[public_url],
                raw_payload=raw_payload,
                connector_version="1.0",
                collected_at=datetime.utcnow().isoformat(),
                human_review_status=None
            )
        except Exception as e:
            # Return a fallback event if parsing fails completely
            return NormalizedPolicyEvent(
                source_name="Congress.gov",
                source_type="Legislation",
                jurisdiction="Federal",
                title="Error Normalizing Bill",
                summary=str(e),
                event_type="Error",
                event_date=datetime.utcnow().isoformat(),
                url="",
                organization=[],
                people=[],
                committees=[],
                agencies=[],
                legislation=[],
                topics=[],
                keywords=[],
                confidence="low",
                evidence=[],
                raw_payload=raw_payload,
                connector_version="1.0",
                collected_at=datetime.utcnow().isoformat(),
                human_review_status=None
            )

    def deduplicate(self): pass
    def checkpoint(self): pass
    def incremental_sync(self): pass
    def rate_limit(self): pass
    def retry(self): pass
    def metadata(self): return {"version": "1.0"}
    def shutdown(self): self.session.close()