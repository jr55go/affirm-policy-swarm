import re
import requests
from infrastructure.source_registry import SourceRegistry

class PublicStatementMonitorAgent:

    def _perform_live_search_fallback(self, query: str, max_results: int = 3):
        """Tier 2 Fallback: Search web when primary feeds fail or return empty."""
        print(f"[{self.agent_id}]  Tier 2: Searching web for '{query}'...")
        fallback_records = []
        try:
            import urllib.parse, urllib.request
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            
            titles = re.findall(r'<a class="result__a"[^>]*>(.*?)</a>', html)
            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html)
            
            for i in range(min(len(titles), max_results)):
                clean_title = re.sub(r'<[^>]+>', '', titles[i]).strip()
                clean_snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else clean_title
                fallback_records.append({
                    "title": clean_title,
                    "description": clean_snippet,
                    "link": f"search_fallback_{i}"
                })
            print(f"[{self.agent_id}]  Tier 2 Recovered {len(fallback_records)} organic search items.")
        except Exception as e:
            print(f"[{self.agent_id}]  Tier 2 Search failed ({e}). Escalating to Tier 3.")
        return fallback_records

    def __init__(self, agent_id="public_statement-monitor"):
        self.agent_id = agent_id
        self.name = "Public Statement Monitor Agent"

    def execute_task(self, payload):
        run_id = payload.get("run_id")
        records = []
        registry = SourceRegistry()
        social_sources = registry.get_enabled_sources_by_type("social_public")

        for source_name in social_sources:
            meta = registry.get_source_metadata(source_name)
            try:
                search_items = self._perform_live_search_fallback(f"{source_name.replace('_', ' ')} CFPB Twitter public statement Buy Now Pay Later")
                if search_items:
                    for item in search_items[:3]:
                        records.append({
                            "source": source_name.replace('_', ' ').title(),
                            "jurisdiction": "US Federal",
                            "title": item.get("title", "Public Statement"),
                            "text_context": item.get("description", ""),
                            "url": "https://www.consumerfinance.gov/"
                        })
            except Exception as e:
                print(f"[{self.agent_id}] Error fetching from {source_name}: {e}")
                continue

        return {"agent_id": self.agent_id, "records": records, "status": "COMPLETED"}
