import logging
import requests
from io import BytesIO
from pypdf import PdfReader
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

class ReaderAgent:
    def __init__(self, agent_id="reader_agent"):
        self.agent_id = agent_id

    def classify_document(self, url):
        try:
            if not url: return "empty"
            if ".pdf" in url.lower().split("?")[0]: return "pdf"
            response = requests.head(url, timeout=10, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
            content_type = response.headers.get("Content-Type", "").lower()
            if "application/pdf" in content_type: return "pdf"
            if "text/html" in content_type: return "html"
            return "unknown"
        except Exception as e:
            logging.warning(f"[{self.agent_id}] Document classification failed for {url}: {e}")
            return "unknown"

    def extract_pdf_text(self, url):
        try:
            logging.info(f"[{self.agent_id}] Downloading PDF for extraction: {url}")
            response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            reader = PdfReader(BytesIO(response.content))
            text = ""
            for page in reader.pages[:25]:
                text += (page.extract_text() or "") + "\n"
            return " ".join(text.split())[:15000]
        except Exception as e:
            logging.error(f"[{self.agent_id}] PDF extraction failed: {e}")
            return ""

    def fetch_full_text(self, url):
        doc_type = self.classify_document(url)
        
        if doc_type == "pdf":
            return self.extract_pdf_text(url)
        if doc_type == "unknown":
            logging.warning(f"[{self.agent_id}] Unknown document type for {url}. Skipping Playwright.")
            return ""

        text = ""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36").new_page()
                stealth_sync(page)
                page.goto(url, timeout=15000)
                
                # Extract all text from the body of the page
                text = page.locator("body").inner_text()
                browser.close()
        except Exception as e:
            logging.error(f"[{self.agent_id}] Failed to read {url}: {e}")
        
        # Clean up whitespace and truncate to fit the LLM context window
        return " ".join(text.split())[:15000]

    def execute_task(self, task_data):
        records = task_data.get("records", [])
        logging.info(f"[{self.agent_id}] Deep-reading {len(records)} targets...")
        
        for record in records:
            url = record.get("url")
            if url:
                logging.info(f"[{self.agent_id}] Scraping full document: {url}")
                full_text = self.fetch_full_text(url)
                
                # Replace the tiny search snippet with the massive full document text
                if full_text:
                    record["snippet"] = full_text
                    
        return {"records": records}
