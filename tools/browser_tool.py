import asyncio
import requests
from io import BytesIO
from pypdf import PdfReader
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)


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
            text += (page.extract_text() or "") + "\n"
        return " ".join(text.split())[:15000]
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return f"Error extracting PDF: {str(e)}"

async def fetch_and_extract_text(url: str) -> str:
    """
    Fetch and extract text from a URL using Playwright (headless Chromium).
    
    Args:
        url (str): The URL to fetch
        
    Returns:
        str: Extracted text content from the page
        
    Raises:
        Exception: If there's an error fetching or extracting the content
    """
    try:
        doc_type = classify_document(url)
        logger.info(f"Classified {url} as {doc_type}")

        if doc_type == "pdf":
            return extract_pdf_text(url)
        if doc_type == "unknown":
            logger.warning(f"Unknown document type for {url}. Skipping Playwright.")
            return "Error: Unknown document type or binary file."

        async with async_playwright() as p:
            # Launch headless browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Navigate to URL
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Extract text content
            text = await page.inner_text("body")
            
            # Close browser
            await browser.close()
            
            return text.strip()
            
    except Exception as e:
        logger.error(f"Error fetching and extracting text from {url}: {str(e)}")
        # Return empty string or raise? Let's return empty string for now
        return f"Error: {str(e)}"

# For synchronous usage, we provide a wrapper
def fetch_and_extract_text_sync(url: str) -> str:
    """
    Synchronous wrapper for fetch_and_extract_text.
    """
    return asyncio.run(fetch_and_extract_text(url))