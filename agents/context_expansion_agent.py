import logging
import requests
from io import BytesIO
from pypdf import PdfReader
from playwright.sync_api import sync_playwright

class ContextExpansionAgent:
    def __init__(self, agent_id="context_expansion_agent", model="nemotron:70b"):
        self.agent_id = agent_id
        self.model = model


    def classify_document(self, url):
        """
        Pre-download classifier.
        Determines whether URL is PDF, HTML, or unknown before extraction.
        """
        try:
            if not url:
                return "empty"

            if ".pdf" in url.lower().split("?")[0]:
                return "pdf"

            response = requests.head(
                url,
                timeout=10,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            content_type = response.headers.get("Content-Type", "").lower()

            if "application/pdf" in content_type:
                return "pdf"
            if "text/html" in content_type:
                return "html"

            return "unknown"

        except Exception as e:
            logging.warning(f"[{self.agent_id}] Document classification failed for {url}: {e}")
            return "unknown"

    def extract_pdf_text(self, url):
        try:
            logging.info(f"[{self.agent_id}] Downloading PDF for extraction: {url}")

            from infrastructure.safe_fetch import safe_get
            response = safe_get(url, timeout=15)

            response.raise_for_status()

            reader = PdfReader(BytesIO(response.content))

            text = ""

            for page in reader.pages[:25]:
                text += (page.extract_text() or "") + "\n"

            cleaned = " ".join(text.split())

            if len(cleaned) < 150:
                logging.warning(
                    f"[{self.agent_id}] PDF extraction returned insufficient text."
                )
                return ""

            return cleaned[:15000]

        except Exception as e:
            logging.error(f"[{self.agent_id}] PDF extraction failed: {e}")
            return ""

    def extract_full_text(self, url):
        if not url:
            return ""
            
        doc_type = self.classify_document(url)

        logging.info(f"[{self.agent_id}] Classified {url} as {doc_type}")

        if doc_type == "pdf":
            return self.extract_pdf_text(url)

        if doc_type == "unknown":
            logging.warning(f"[{self.agent_id}] Unknown document type for {url}. Skipping extraction.")
            return ""

        text = ""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Upgrade wait state to 'networkidle' for SPA/JavaScript rendering
                page.goto(url, timeout=25000, wait_until="networkidle")
                text = page.locator("body").inner_text()
                
                # WAF / Anti-Bot Blacklist Detection
                waf_triggers = [
                    "Checking your browser", 
                    "Access Denied", 
                    "Enable JavaScript", 
                    "Just a moment...", 
                    "Security check",
                    "Please verify you are human"
                ]
                
                if any(trigger.lower() in text.lower() for trigger in waf_triggers) or len(text) < 150:
                    logging.warning(f"[{self.agent_id}] WAF/Challenge page detected. Discarding boilerplate.")
                    text = ""

                browser.close()
        except Exception as e:
            logging.error(f"[{self.agent_id}] Playwright extraction failed: {e}")
        return text

    def execute_task(self, task_data):
        if isinstance(task_data, dict):
            records = task_data.get("records", [])
        else:
            records = task_data
            task_data = {"records": records}
            
        logging.info(f"[{self.agent_id}] Expanding context for {len(records)} records")
        expanded_records = []
        
        high_value_domains = ['gov', 'reddit.com', 'brookings.edu', 'americanactionforum.org', 'wsj.com', 'bloomberg.com', 'ft.com']
        
        for record in records:
            if not isinstance(record, dict):
                expanded_records.append(record)
                continue
            
            # Skip Playwright if native API connectors already populated the full text
            if record.get('full_text') and len(record.get('full_text')) > 500:
                logging.info(f"[{self.agent_id}] Full text already provided by API for {record.get('url', 'record')}. Skipping scrape.")
                expanded_records.append(record)
                continue

            source_vector = record.get('source_vector', '')
            url = record.get('url', '')
            
            is_high_value = any(domain in source_vector or domain in url for domain in high_value_domains)
            
            if is_high_value and url:
                logging.info(f"[{self.agent_id}] Predictive signal detected. Initiating Playwright deep extraction for: {url}")
                full_text = self.extract_full_text(url)
                if full_text:
                    record['full_text'] = full_text[:15000]
                    logging.info(f"[{self.agent_id}] Successfully extracted {len(record['full_text'])} characters.")
            
            expanded_records.append(record)
            
        task_data["records"] = expanded_records
        return task_data
