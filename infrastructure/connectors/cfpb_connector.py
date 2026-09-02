import os
import requests
import warnings
from typing import List, Dict, Any
from infrastructure.connectors.connector_checkpoint import CheckpointManager

class CFPBConnector:
    def __init__(self, config=None):
        self.config = config or {}
        self.api_base_url = 'https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/'
        
    @property
    def checkpoint_manager(self):
        if not hasattr(self, '_checkpoint_manager'):
            self._checkpoint_manager = CheckpointManager()
        return self._checkpoint_manager

    def fetch_data(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            print(f"[CFPBConnector] Fetching live data from {self.api_base_url}")
            response = requests.get(self.api_base_url, params={'size': 5, 'search_term': 'Affirm'})
            if response.status_code == 200:
                hits = response.json().get('hits', {}).get('hits', [])
                results = []
                for h in hits:
                    src = h.get('_source', {})
                    results.append({
                        'title': f"CFPB Complaint: {src.get('product', 'Unknown Product')}",
                        'snippet': src.get('complaint_what_happened', 'No narrative provided.')[:1000],
                        'url': f"https://www.consumerfinance.gov/data-research/consumer-complaints/search/detail/{src.get('complaint_id', '')}",
                        'source': 'CFPB'
                    })
                print(f"[CFPBConnector] Successfully fetched {len(results)} live records.")
                return results
            return []
        except Exception as e:
            print(f"[CFPBConnector] Fetch failed: {e}")
            return []

    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return []
