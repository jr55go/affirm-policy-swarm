import feedparser
import logging
from datetime import datetime, timedelta

class RSSFeedAgent:
    def __init__(self, agent_id="RSSFeedAgent"):
        self.agent_id = agent_id
        self.feeds = {
            "regulatory_pulse": [
                "https://www.federalregister.gov/documents/current.rss",
                "https://www.consumerfinance.gov/about-us/newsroom/feed/",
                "https://www.occ.gov/news-issuances/rss/occ-news.xml",
                "https://www.ftc.gov/feeds/press-release.xml",
                "https://www.fdic.gov/news/press-releases/rss.xml",
            ],
            "bnpl_competitive": [
                "https://news.google.com/rss/search?q=Klarna+regulation+policy&hl=en-US&gl=US&ceid=US:en",
                "https://news.google.com/rss/search?q=Afterpay+BNPL+regulation&hl=en-US&gl=US&ceid=US:en",
                "https://news.google.com/rss/search?q=Sezzle+PayPal+buy+now+pay+later+policy&hl=en-US&gl=US&ceid=US:en",
            ],
            "financial_inclusion": [
                "https://www.brookings.edu/feed/",
                "https://www.urban.org/rss.xml",
                "https://www.responsiblelending.org/feed",
            ],
            "political_coalition": [
                "https://news.google.com/rss/search?q=Senate+Banking+Committee+fintech&hl=en-US&gl=US&ceid=US:en",
                "https://news.google.com/rss/search?q=House+Financial+Services+BNPL&hl=en-US&gl=US&ceid=US:en",
            ],
            "media_narrative": [
                "https://news.google.com/rss/search?q=buy+now+pay+later&hl=en-US&gl=US&ceid=US:en",
                "https://www.americanbanker.com/feed",
                "https://www.paymentsdive.com/feeds/news/",
            ],
            "ai_governance": [
                "https://news.google.com/rss/search?q=AI+financial+services+regulation+2026&hl=en-US&gl=US&ceid=US:en",
                "https://news.google.com/rss/search?q=algorithmic+credit+underwriting+rules&hl=en-US&gl=US&ceid=US:en",
            ],
            "state_tracker": [
                "https://dfpi.ca.gov/feed/",
                "https://news.google.com/rss/search?q=BNPL+state+legislation+2026&hl=en-US&gl=US&ceid=US:en",
            ],
            "internal_alignment": [
                "https://www.affirm.com/en-us/blog/feed",
            ],
        }

    def execute_task(self, payload={}):
        records = []
        for section, feed_urls in self.feeds.items():
            for url in feed_urls:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:8]:
                        title = entry.get("title", "").strip()
                        link = entry.get("link", "")
                        summary = entry.get("summary", "") or entry.get("description", "")
                        if title and link:
                            records.append({
                                "title": title,
                                "snippet": summary[:500],
                                "url": link,
                                "source": feed.feed.get("title", "Direct RSS Feed"),
                                "section_tag": section,
                                "date": entry.get("published", datetime.now().strftime('%Y-%m-%d')),
                                "text_context": f"{title} - {summary[:1000]}",
                            })
                except Exception as e:
                    logging.warning(f"[{self.agent_id}] Feed error {url}: {e}")

        logging.info(f"[{self.agent_id}] RSS sweep complete. Collected {len(records)} records across {len(self.feeds)} section streams.")
        return {"records": records}
