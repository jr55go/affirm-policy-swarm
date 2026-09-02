import requests
from bs4 import BeautifulSoup
from infrastructure.source_registry import SourceRegistry

class ResearchMonitorAgent:
    def __init__(self, agent_id="research-monitor-001"):
        self.agent_id = agent_id
        self.registry = SourceRegistry()

    def execute_task(self, payload):
        records = []
        enabled_sources = self.registry.get_enabled_sources_by_type("research")
        
        for source_name in enabled_sources:
            source_meta = self.registry.get_source_metadata(source_name)
            if not source_meta or not source_meta.get("enabled", False):
                continue
                
            print(f"[{self.agent_id}] Scraping research from {source_name}...")
            
            try:
                url = source_meta["url"]
                # For Brookings, we'll scrape the research page
                if "brookings.edu" in url:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find recent research items - this is a simplified selector
                    # In reality, we'd need to inspect the actual Brookings page structure
                    articles = soup.find_all('article', class_='teaser')[:5]  # Get first 5 articles
                    
                    for article in articles:
                        title_elem = article.find('h4', class_='title') or article.find('h3')
                        title = title_elem.get_text(strip=True) if title_elem else "Untitled Research"
                        
                        summary_elem = article.find('div', class_='synopsis') or article.find('p')
                        summary = summary_elem.get_text(strip=True) if summary_elem else "No summary available"
                        
                        records.append({
                            "source": "Brookings Institution",
                            "jurisdiction": "US Federal/Research",
                            "bill_id": f"BROOKINGS-{hash(title) % 10000:04d}",
                            "title": title,
                            "text_context": f"{title}: {summary}"
                        })
                    
                    self.registry.update_source_health(source_name, success=True)
                else:
                    # Generic handling for other research sources
                    print(f"[{self.agent_id}] No specific scraper for {source_name}, skipping")
                    self.registry.update_source_health(source_name, success=False, error="No scraper implemented")
                    
            except Exception as e:
                print(f"[{self.agent_id}] Error scraping {source_name}: {e}")
                self.registry.update_source_health(source_name, success=False, error=str(e))
        
        return {"agent_id": self.agent_id, "records": records, "status": "COMPLETED"}