import os
import shutil

path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/reader_agent.py")

# Backup the original file
shutil.copy2(path, path + ".before_classifier_patch")

with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add required imports cleanly
old_imports = """import logging
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync"""

new_imports = """import logging
import requests
from io import BytesIO
from pypdf import PdfReader
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync"""

if "import requests" not in text:
    text = text.replace(old_imports, new_imports)

# 2. Inject helper functions into the ReaderAgent class
helpers = """    def classify_document(self, url):
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
                text += (page.extract_text() or "") + "\\n"
            return " ".join(text.split())[:15000]
        except Exception as e:
            logging.error(f"[{self.agent_id}] PDF extraction failed: {e}")
            return ""

    def fetch_full_text(self, url):"""

if "def classify_document" not in text:
    text = text.replace("    def fetch_full_text(self, url):", helpers)

# 3. Inject routing logic inside fetch_full_text
old_logic = """    def fetch_full_text(self, url):
        text = ""
        try:
            with sync_playwright() as p:"""

new_logic = """    def fetch_full_text(self, url):
        doc_type = self.classify_document(url)
        
        if doc_type == "pdf":
            return self.extract_pdf_text(url)
        if doc_type == "unknown":
            logging.warning(f"[{self.agent_id}] Unknown document type for {url}. Skipping Playwright.")
            return ""

        text = ""
        try:
            with sync_playwright() as p:"""

if "doc_type =" not in text:
    text = text.replace(old_logic, new_logic)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("✅ reader_agent.py patched with pre-download classifier and PDF routing.")
