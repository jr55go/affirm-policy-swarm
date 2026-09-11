"""Canonical production run-bundle emitter for the independent dashboard."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

def _timestamp(value: Any, fallback: str) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def partition_production_records(records: Iterable[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Separate explicit non-production records before they enter analysis stages."""
    safe: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for record in records:
        flags = (
            "is_fallback", "is_mock", "is_simulated", "mock", "simulated",
            "fallback_mode", "used_fallback", "triage_fallback",
        )
        text = f"{record.get('title', '')} {record.get('source', '')} {record.get('url', '')}"
        if any(bool(record.get(flag)) for flag in flags) or UNSAFE_TEXT_PATTERN.search(text) or "search_fallback_" in text.lower():
            rejected.append(record)
        else:
            safe.append(record)
    return safe, rejected


class DashboardRunEmitter:
    """Writes and optionally submits a strict production dashboard bundle."""

    def __init__(self, run_id: str, report_dir: str, objective: str):
        if not RUN_ID_PATTERN.match(run_id):
            raise ValueError(f"Invalid production run id: {run_id}")
        self.run_id = run_id
        self.report_dir = Path(report_dir)
        self.objective = objective.strip() or "Policy intelligence run"
        self.started_at = utc_now()
        self.updated_at = self.started_at
        self.status = "starting"
        self.completed_at: Optional[str] = None
        self.failed_at: Optional[str] = None
        self.stages: Dict[str, Dict[str, Any]] = {}
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.errors: List[Dict[str, Any]] = []
        url = str(finding.get("url") or "").strip()
        if not url or not url.startswith("https://"):
            return None
        content_basis = raw_context or summary or title
        content_hash = str(finding.get("document_hash") or "").strip()
        if not re.fullmatch(r"[a-fA-F0-9]{32,128}", content_hash):
            content_hash = hashlib.sha256(content_basis.encode("utf-8")).hexdigest()
        identity = hashlib.sha256(f"{self.run_id}|{url or ''}|{title}|{content_hash}".encode("utf-8")).hexdigest()
        entities = finding.get("entities") if isinstance(finding.get("entities"), dict) else {}
        explicit_facts = _list(finding.get("explicit_source_facts"))
        return {
            "id": f"finding_{identity}",
            "runId": self.run_id,
            "title": title,
            "url": url,
            "sourceName": source_name,
            "sourceType": str(finding.get("source_type") or source_name).strip(),
            "sourceRecordId": str(finding.get("id") or finding.get("bill_id") or finding.get("document_id") or "").strip() or None,
            "publishedAt": _timestamp(finding.get("date") or finding.get("published") or finding.get("postedDate"), self.started_at) if finding.get("date") or finding.get("published") or finding.get("postedDate") else None,
            "observedAt": _timestamp(finding.get("analysis_timestamp") or finding.get("timestamp"), self.started_at),
            "jurisdiction": str(finding.get("jurisdiction") or "Unspecified").strip(),
            "summary": summary,
            "context": raw_context,
            "impactScore": impact,
            "policyRiskScore": risk,
            "validationStatus": "approved",
            "validationReason": str(finding.get("validation_reason") or "").strip() or None,
            "confidence": confidence,
            "sentimentScore": finding.get("sentiment_score") if isinstance(finding.get("sentiment_score"), (int, float)) else None,
            "explicitSourceFacts": explicit_facts,
            "inferredImpact": str(finding.get("inferred_market_impact") or finding.get("analysis") or "").strip(),
            "entities": {
                "organizations": _list(entities.get("organizations")),
                "policymakers": _list(entities.get("policymakers")),
                "themes": _list(entities.get("themes")),
            },
            "deadlineAt": _timestamp(finding.get("deadline") or finding.get("deadline_at"), self.started_at) if finding.get("deadline") or finding.get("deadline_at") else None,
            "pipelineStatus": "validated",
            "provenance": {
                "kind": "derived",
                "collector": str(finding.get("collector") or finding.get("agent_id") or source_name).strip(),
                "contentHash": content_hash,
                "isFallback": False,
                "isMock": False,
                "isSimulated": False,
            },
        }

    def _findings(self, records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        safe = []
        for record in records:
            converted = self._finding(record)
            if converted:
                safe.append(converted)
        return safe

    def _investigations(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for finding in findings:
            themes = finding["entities"]["themes"]
            key = themes[0] if themes else finding["jurisdiction"]
            grouped.setdefault(key, []).append(finding)
        investigations = []
        for key, items in grouped.items():
            identity = hashlib.sha256(f"{self.run_id}|{key}".encode("utf-8")).hexdigest()
            investigations.append({
                "id": f"investigation_{identity}",
                "title": key,
                "status": "active",
                "jurisdictions": sorted({item["jurisdiction"] for item in items}),
                "themes": sorted({theme for item in items for theme in item["entities"]["themes"]}),
                "entities": sorted({entity for item in items for entity in item["entities"]["organizations"] + item["entities"]["policymakers"]}),
                "findingIds": [item["id"] for item in items],
                "knowns": [item["title"] for item in items],
                "unknowns": [],
                "scheduledFollowUps": [],
                "updatedAt": self.updated_at,
            })
        return investigations

    def build_bundle(self, status: str, records: Optional[Iterable[Dict[str, Any]]] = None, report_path: Optional[str] = None) -> Dict[str, Any]:
        now = utc_now()
        self.updated_at = now
        self.status = status
        if status == "completed":
            self.completed_at = now
        if status == "failed":
            self.failed_at = now
        if records is not None:
            self._latest_records = list(records)
        if report_path is not None:
            self._latest_report_path = report_path
        safe_findings = self._findings(self._latest_records)
        report = None
        if self._latest_report_path:
            path = Path(self._latest_report_path)
            if path.exists():
                content = path.read_text(encoding="utf-8").strip()
                if content:
                    report = {
                        "runId": self.run_id,
                        "format": "markdown",
                        "content": content,
                        "generatedAt": now,
                        "actionableFindingIds": [finding["id"] for finding in safe_findings if finding["impactScore"] != "low"],
                        "rejectedFindingIds": [],
                    }
        bundle = {
            "schemaVersion": SCHEMA_VERSION,
            "run": {
                "id": self.run_id,
                "mode": "production",
                "status": status,
                "objective": self.objective,
                "startedAt": self.started_at,
                "updatedAt": now,
                "completedAt": self.completed_at,
                "failedAt": self.failed_at,
                "codeVersion": _code_version(),
                "emitterVersion": EMITTER_VERSION,
            },
            "stages": list(self.stages.values()),
            "sources": list(self.sources.values()),
            "findings": safe_findings,
            "investigations": self._investigations(safe_findings),
            "report": report,
            "errors": self.errors,
        }
        if status == "completed" and report is None:
            raise ValueError("A completed production run requires an actual generated report")
        return bundle

    def emit(self, status: str, records: Optional[Iterable[Dict[str, Any]]] = None, report_path: Optional[str] = None) -> Dict[str, Any]:
        bundle = self.build_bundle(status, records, report_path)
        target = self.report_dir / "dashboard_bundle.json"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.report_dir, delete=False) as temp:
            json.dump(bundle, temp, indent=2, ensure_ascii=False)
            temp.flush()
            os.fsync(temp.fileno())
            temp_path = Path(temp.name)
        temp_path.replace(target)
        self._submit(bundle)
        return bundle

    def _submit(self, bundle: Dict[str, Any]) -> None:
        endpoint = os.getenv("DASHBOARD_INGEST_URL", "").strip()
        token = os.getenv("DASHBOARD_INGEST_TOKEN", "").strip()
        if not endpoint or not token:
            return
<<<<<<< HEAD
=======
        if validate_ingest_url is None:
            raise RuntimeError("scripts/private_http.py is required beside the integration package")
        validate_ingest_url(endpoint)
>>>>>>> e5095c2 (feat(phase-0): enforce fail-closed evidence lifecycle and strict schema contracts)
        timeout = float(os.getenv("DASHBOARD_INGEST_TIMEOUT_SECONDS", "30"))
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(bundle).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        last_error: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    if response.status not in {200, 202}:
                        raise RuntimeError(f"Dashboard ingestion returned HTTP {response.status}")
                error_path = self.report_dir / "dashboard_delivery_error.json"
                if error_path.exists():
                    error_path.unlink()
                return
            except (urllib.error.URLError, TimeoutError, RuntimeError) as error:
                last_error = error
                if attempt < 3:
                    time.sleep(attempt)
        self.add_error("dashboard_ingestion", f"Delivery failed after 3 attempts: {last_error}", recoverable=True)
        error_path = self.report_dir / "dashboard_delivery_error.json"
        error_path.write_text(json.dumps(self.errors[-1], indent=2), encoding="utf-8")
