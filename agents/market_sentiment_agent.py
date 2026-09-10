import json
import logging
import urllib.parse
import requests
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

logger = logging.getLogger(__name__)


class MarketSentimentAgent:
    def __init__(self, agent_id="market-sentiment-agent", ollama_url="http://localhost:11434/api/generate", model="nemotron:70b"):
        self.agent_id = agent_id
        self.ollama_url = ollama_url
        self.model = model

    def analyze_sentiment(self, source: str, text: str) -> Optional[Dict[str, Any]]:
        prompt = (
            f"Analyze the consumer sentiment and key themes from the following {source} discussions regarding BNPL, Affirm, and fintech:\n"
            f"Text: {text[:2000]}\n\n"
            "Return JSON with:\n"
            ' "sentiment": "Positive" | "Neutral" | "Negative"\n'
            ' "key_themes": ["theme1", "theme2", "theme3"]\n'
        )
        try:
            response = requests.post(
                self.ollama_url,
                json={"model": self.model, "prompt": prompt, "stream": False, "format": "json"},
                timeout=30,
            )
            response.raise_for_status()
            parsed = json.loads(response.json().get("response", "{}"))
            return parsed if isinstance(parsed, dict) else None
        except Exception as error:
            logger.error(f"[{self.agent_id}] Sentiment LLM parsing failed: {error}")
            return None

    def _scrape_with_playwright(self, query: str) -> str:
        """Extract live public search snippets; return no data when retrieval fails."""
        logger.info(f"[{self.agent_id}] Booting Stealth Playwright for query: {query}")
        snippets = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                stealth_sync(page)
                encoded_query = urllib.parse.quote(query)
                page.goto(f"https://html.duckduckgo.com/html/?q={encoded_query}", wait_until="domcontentloaded", timeout=15000)
                for node in page.query_selector_all(".result__snippet")[:8]:
                    text = node.inner_text().strip()
                    if text:
                        snippets.append(text)
                browser.close()
        except Exception as error:
            logger.error(f"[{self.agent_id}] Playwright sentiment extraction failed for '{query}': {error}")
        return " ".join(snippets)

    def execute_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[{self.agent_id}] Pulling live social sentiment via Stealth Playwright...")
        findings = []

        reddit_text = self._scrape_with_playwright("site:reddit.com BNPL Affirm Klarna phantom debt late fees")
        reddit_analysis = self.analyze_sentiment("Reddit", reddit_text) if reddit_text else None
        if reddit_analysis:
            findings.append({
                "title": "Reddit Consumer Sentiment Pulse",
                "text_context": f"Aggregated Themes: {', '.join(reddit_analysis.get('key_themes', []))} | Content: {reddit_text[:500]}",
                "sentiment_score": -1 if reddit_analysis.get("sentiment") == "Negative" else 0,
                "key_phrases": reddit_analysis.get("key_themes", []),
                "source": "Reddit Consumers (Playwright Scrape)",
                "url": "https://reddit.com/r/personalfinance",
            })

        tiktok_text = self._scrape_with_playwright("site:tiktok.com BNPL Affirm debt checkout age verification")
        tiktok_analysis = self.analyze_sentiment("TikTok", tiktok_text) if tiktok_text else None
        if tiktok_analysis:
            findings.append({
                "title": "TikTok & Gen Z Consumer Trends",
                "text_context": f"Aggregated Themes: {', '.join(tiktok_analysis.get('key_themes', []))} | Content: {tiktok_text[:500]}",
                "sentiment_score": -1 if tiktok_analysis.get("sentiment") == "Negative" else 0,
                "key_phrases": tiktok_analysis.get("key_themes", []),
                "source": "TikTok/Social Influencers (Playwright Scrape)",
                "url": "https://tiktok.com/tag/bnpl",
            })

        return {"records": findings, "status": "completed"}
