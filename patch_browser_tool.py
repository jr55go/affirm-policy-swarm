import os
import shutil

path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/tools/browser_tool.py")

# Backup the original file
shutil.copy2(path, path + ".before_classifier_patch")

with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add required imports cleanly
old_imports = """import asyncio
from playwright.async_api import async_playwright
import logging"""

new_imports = """import asyncio
import requests
from io import BytesIO
from pypdf import PdfReader
from playwright.async_api import async_playwright
import logging"""

if "import requests" not in text:
    text = text.replace(old_imports, new_imports)

# 2. Inject helper functions right before the main async function
helpers = """
def classify_document(url: str) -> str:
    try:
        if not url: return "empty"
        if ".pdf" in url.lower().split("?")[0]: return "pdf"
        response = requests.head(url, timeout=10, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/pdf" in content_type: return "pdf"
        if "text/html" in content_type: return "html"
        return "unknown"
    except Exception as e:
        logger.warning(f"Document classification failed for {url}: {e}")
        return "unknown"

def extract_pdf_text(url: str) -> str:
    try:
        logger.info(f"Downloading PDF for extraction: {url}")
        response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        reader = PdfReader(BytesIO(response.content))
        text = ""
        for page in reader.pages[:25]:
            text += (page.extract_text() or "") + "\\n"
        return " ".join(text.split())[:15000]
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return f"Error extracting PDF: {str(e)}"

async def fetch_and_extract_text"""

if "def classify_document" not in text:
    text = text.replace("async def fetch_and_extract_text", helpers)

# 3. Inject routing logic inside the try block
old_try = """    try:
        async with async_playwright() as p:"""

new_try = """    try:
        doc_type = classify_document(url)
        logger.info(f"Classified {url} as {doc_type}")

        if doc_type == "pdf":
            return extract_pdf_text(url)
        if doc_type == "unknown":
            logger.warning(f"Unknown document type for {url}. Skipping Playwright.")
            return "Error: Unknown document type or binary file."

        async with async_playwright() as p:"""

if "doc_type = classify_document" not in text:
    text = text.replace(old_try, new_try)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("✅ browser_tool.py patched with pre-download classifier and PDF routing.")
