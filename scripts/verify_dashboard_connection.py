#!/usr/bin/env python3
"""Verify the authenticated dashboard ingestion endpoint without submitting run data."""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


endpoint = os.getenv("DASHBOARD_INGEST_URL", "").strip()
token = os.getenv("DASHBOARD_INGEST_TOKEN", "").strip()

if not endpoint:
    fail("DASHBOARD_INGEST_URL is not set")
if len(token) < 32:
    fail("DASHBOARD_INGEST_TOKEN must be at least 32 characters")

parsed = urllib.parse.urlparse(endpoint)
if parsed.scheme not in {"https", "http"} or not parsed.netloc:
    fail("DASHBOARD_INGEST_URL must be an absolute HTTP(S) URL")
if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
    fail("Use HTTPS unless the dashboard is running on the same machine")
if not parsed.path.rstrip("/").endswith("/api/ingest/v1/runs"):
    fail("DASHBOARD_INGEST_URL must end with /api/ingest/v1/runs")

health_url = endpoint.rstrip("/")[:-len("runs")] + "health"
request = urllib.request.Request(
    health_url,
    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
)

try:
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
except urllib.error.HTTPError as error:
    if error.code == 401:
        fail("Dashboard reached, but the ingestion token does not match")
    fail(f"Dashboard health check returned HTTP {error.code}")
except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
    fail(f"Could not validate the dashboard endpoint: {error}")

if payload.get("ok") is not True or payload.get("schemaVersion") != "1.0.0":
    fail(f"Unexpected health response: {payload}")

print(f"Dashboard ingestion connection verified: {parsed.scheme}://{parsed.netloc}")
print("Accepted schema version: 1.0.0")
