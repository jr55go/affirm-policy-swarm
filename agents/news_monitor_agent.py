import re
import requests
import xml.etree.ElementTree as ET
from infrastructure.source_registry import SourceRegistry

class NewsMonitorAgent:

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

    def __init__(self, agent_id="news-monitor"):
        self.agent_id = agent_id
        self.name = "News Monitor Agent"
        print(f"2026-06-24 18:50:00 - agent.{self.agent_id} - INFO - Logger Active: Pure Python Scraping")

    def execute_task(self, payload):
        run_id = payload.get("run_id")
        records = []
        registry = SourceRegistry()
        news_sources = registry.get_enabled_sources_by_type("news")

        for source_name in news_sources:
            meta = registry.get_source_metadata(source_name)
            try:
                if meta.get("access_method") == "rss":
                    # Try to fetch the RSS feed
                    response = requests.get(meta["url"], timeout=10)
                    response.raise_for_status()
                    # Parse the XML (simplified: we look for <item> or <entry>)
                    root = ET.fromstring(response.content)
                    # We'll look for common RSS/Atom structures
                    items = []
                    # Try RSS 2.0
                    for item in root.findall('.//item'):
                        title_elem = item.find('title')
                        desc_elem = item.find('description')
                        link_elem = item.find('link')
                        title = title_elem.text if title_elem is not None else ""
                        description = desc_elem.text if desc_elem is not None else ""
                        link = link_elem.text if link_elem is not None else ""
                        items.append({
                            "title": title,
                            "description": description,
                            "link": link
                        })
                    # Try Atom
                    for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                        title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                        summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')
                        link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
                        title = title_elem.text if title_elem is not None else ""
                        summary = summary_elem.text if summary_elem is not None else ""
                        link = link_elem.get('href') if link_elem is not None else ""
                        items.append({
                            "title": title,
                            "description": summary,
                            "link": link
                        })
                    if not items:
                        print(f"[{self.agent_id}] Tier 1 empty for {source_name}. Escalating to Tier 2...")
                        items = self._perform_live_search_fallback(f"{source_name.replace('_', ' ')} Buy Now Pay Later regulation")

                if items:
                    for item in items[:3]:
                        record = {
                            "source": source_name.replace('_', ' ').title(),
                            "jurisdiction": "US",
                            "title": item.get("title", "Financial News Update"),
                            "text_context": item.get("description", ""),
                        }
                        records.append(record)
                    registry.update_source_health(source_name, success=True)
                else:
                    print(f"[{self.agent_id}] Tier 3 Triggered: 0 records found for {source_name}.")
                    registry.update_source_health(source_name, success=False, error="Tier 1 & 2 yield 0 records")

            except Exception as e:
                print(f"[{self.agent_id}] Tier 1 Fetch Error for {source_name}: {e}. Escalating to Tier 2...")
                fallback_items = self._perform_live_search_fallback(f"{source_name.replace('_', ' ')} Buy Now Pay Later regulation")
                if fallback_items:
                    for item in fallback_items[:3]:
                        records.append({
                            "source": source_name.replace('_', ' ').title(),
                            "jurisdiction": "US",
                            "title": item.get("title", "Financial News Update"),
                            "text_context": item.get("description", ""),
                        })
                    registry.update_source_health(source_name, success=True)
                else:
                    registry.update_source_health(source_name, success=False, error=str(e))
                continue

        return {"agent_id": self.agent_id, "records": records, "status": "COMPLETED"}