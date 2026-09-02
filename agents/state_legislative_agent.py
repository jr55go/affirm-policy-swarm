import re
import time
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

class StateLegislativeAgent:
    def __init__(self, agent_id="StateLegislativeAgent"):
        self.agent_id = agent_id

    def execute_task(self, payload={}):
        print(f"[{self.agent_id}] Booting Stealth Playwright to scan State Feeds (WAF Bypass)...")
        records = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
                    extra_http_headers={"Accept": "text/xml, application/rss+xml, application/xml"}
                )
                page = context.new_page()
                stealth_sync(page)

                # 1. CA DFPI (WordPress RSS Feed via Raw XML Response)
                try:
                    url = "https://dfpi.ca.gov/feed/"
                    res = page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    time.sleep(2)
                    feed_text = res.text() if res else ""
                    
                    # Extract titles and links directly from raw XML tags
                    items = re.findall(r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>", feed_text, re.DOTALL)
                    for title, link in items:
                        clean_title = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", title).strip()
                        clean_link = link.strip()
                        records.append({
                            "title": f"CA DFPI: {clean_title}",
                            "snippet": f"California DFPI Regulatory Notice: {clean_title}",
                            "text_context": f"Document published by CA DFPI. Source URL: {clean_link}",
                            "source": "California DFPI",
                            "url": clean_link,
                            "date": ""
                        })
                except Exception as e:
                    print(f"[{self.agent_id}] CA DFPI feed error: {e}")

                # 2. NY DFS (Press Releases via Raw HTML Fetch)
                try:
                    url = "https://www.dfs.ny.gov/reports_and_publications/press_releases"
                    res = page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    time.sleep(2)
                    html_text = res.text() if res else ""
                    
                    # Match href and text cleanly
                    links = re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_text, re.IGNORECASE)
                    valid = 0
                    for href, text in links:
                        clean_text = re.sub(r'<[^>]+>', '', text).strip()
                        if len(clean_text) > 25 and ("/reports_and_publications/" in href or "/press_releases/" in href or href.startswith("http")):
                            full_url = href if href.startswith("http") else f"https://www.dfs.ny.gov{href}"
                            records.append({
                                "title": f"NY DFS: {clean_text}",
                                "snippet": f"New York DFS Notice: {clean_text}",
                                "text_context": f"Document published by NY DFS. Source URL: {full_url}",
                                "source": "New York DFS",
                                "url": full_url,
                                "date": ""
                            })
                            valid += 1
                            
                except Exception as e:
                    print(f"[{self.agent_id}] NY DFS fetch error: {e}")

                browser.close()
        except Exception as e:
            print(f"[{self.agent_id}] Playwright error during state scan: {e}")

        print(f"[{self.agent_id}] State scan complete. Collected {len(records)} records.")
        return {"records": records}
