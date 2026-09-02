import hashlib
import re

def generate_content_fingerprint(raw_text):
    """
    Normalizes text and generates a SHA-256 fingerprint for duplicate detection.
    """
    if not raw_text:
        return None
    text = raw_text.lower()
    text = re.sub(r'<[^>]+>', ' ', text)
    boilerplate = ["subscribe", "log in", "sign up", "terms of service", "privacy policy", "cookie policy"]
    for bp in boilerplate:
        text = text.replace(bp, "")
    text = re.sub(r'\s+', ' ', text).strip()
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
