import requests
from bs4 import BeautifulSoup
import logging
import feedparser
from urllib.parse import quote, unquote, urlparse, parse_qs


class DDGWorker:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def search(self, query, max_results=12):
        results = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote(query )}"
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for r in soup.select(".result__body")[:max_results]:
                title_el = r.select_one(".result__title a")
                snippet_el = r.select_one(".result__snippet")
                if not title_el:
                    continue
                href = title_el.get("href", "")
                if "uddg=" in href:
                    parsed = parse_qs(urlparse(href).query)
                    href = unquote(parsed.get("uddg", [href])[0])
                if href and "duckduckgo.com" not in href:
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        "url": href,
                        "source_engine": "duckduckgo",
                        "query_vector": query,
                    })
        except Exception as e:
            logging.warning(f"[DDGWorker] Error for query: {e}")
        return results


class GoogleNewsWorker:
    def search(self, query, max_results=10):
        results = []
        try:
            url = f"https://news.google.com/rss/search?q={quote(query )}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_results]:
                link = entry.get("link", "")
                if link:
                    results.append({
                        "title": entry.get("title", ""),
                        "snippet": entry.get("summary", "")[:500],
                        "url": link,
                        "source_engine": "google_news",
                        "query_vector": query,
                        "date": entry.get("published", ""),
                    })
        except Exception as e:
            logging.warning(f"[GoogleNewsWorker] Error for query: {e}")
        return results
