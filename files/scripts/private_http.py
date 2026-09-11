import ipaddress
from urllib.parse import urlparse

def validate_ingest_url(url):
    parsed = urlparse(url)
    
    # 1. Reject invalid schemes
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Scheme must be http or https")
        
    # 2. Reject credentials in URL
    if parsed.username or parsed.password:
        raise ValueError("Credentials not allowed in URL")
        
    # 3. Require exact ingestion path
    if parsed.path != "/api/ingest/v1/runs":
        raise ValueError("Invalid endpoint path")
        
    # 4. Reject query parameters
    if parsed.query:
        raise ValueError("Query parameters not allowed")
        
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Hostname required")
        
    # 5. Evaluate if the host is private/internal
    is_private = False
    try:
        # Check if it's a valid IP address
        ip = ipaddress.ip_address(hostname.strip("[]"))
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            is_private = True
    except ValueError:
        # It's a hostname. Treat as internal if localhost, no TLD, or .internal
        if hostname == "localhost" or "." not in hostname or hostname.endswith(".internal"):
            is_private = True
            
    # 6. Enforce scheme constraints
    if parsed.scheme == "http" and not is_private:
        raise ValueError("HTTP is only permitted for local/private network endpoints")
        
    return parsed
