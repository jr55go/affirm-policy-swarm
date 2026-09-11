import requests
import socket
from urllib.parse import urlparse

def safe_get(url, timeout=15):
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"URL scheme {parsed.scheme} not permitted. HTTPS required.")
    
    # Block private/loopback resolution
    try:
        ip = socket.gethostbyname(parsed.hostname)
        if ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("169.254."):
            raise ValueError("Resolved IP is in a forbidden private/link-local range.")
    except socket.gaierror:
        pass # Fails naturally on DNS
        
    return requests.get(
        url, 
        timeout=timeout, 
        headers={"User-Agent": "AffirmPolicySwarm/1.0 (Research)"}, 
        allow_redirects=False
    )
