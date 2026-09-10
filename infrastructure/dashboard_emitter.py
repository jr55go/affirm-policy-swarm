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


SCHEMA_VERSION = "1.0.0"
EMITTER_VERSION = "1.0.0"
RUN_ID_PATTERN = re.compile(r"^run_[0-9]{9,}$")
UNSAFE_TEXT_PATTERN = re.compile(r"\b(mock|dummy|simulated|synthetic|demo)\b", re.IGNORECASE)

STAGE_LABELS = {
    "discovery": "Web discovery and triage",
    "direct_sources": "Direct RSS and SEC sources",
    "regulatory_apis": "Legislative and regulatory APIs",
    "sentiment": "News and public narrative",
    "deduplication": "Topic gating and deduplication",
    "context_expansion": "Source context expansion",
    "impact_analysis": "Policy impact analysis",
    "compression": "Evidence compression",
    "entity_resolution": "Entity resolution",
    "risk_scoring": "Policy risk scoring",
    "validation": "Factual validation",
    "graph_sync": "Optional graph synchronization",
    "synthesis": "Executive synthesis",
    "reporting": "Report generation",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _code_version() -> str:
    configured = os.getenv("SWARM_CODE_VERSION", "").strip()
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unversioned-runtime"


def _list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _timestamp(value: Any, fallback: str) -> str:
    if not value:
        return fallback
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return fallback


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
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def stage(self, key: str, status: str, input_count: int = 0, output_count: int = 0, error: Optional[str] = None) -> None:
        if key not in STAGE_LABELS:
            raise ValueError(f"Unsupported dashboard stage: {key}")
        now = utc_now()
        previous = self.stages.get(key, {})
        started_at = previous.get("startedAt")
        if status == "running" and not started_at:
            started_at = now
        self.stages[key] = {
            "key": key,
            "label": STAGE_LABELS[key],
            "status": status,
            "startedAt": started_at,
            "completedAt": now if status in {"completed", "failed", "skipped"} else None,
            "updatedAt": now,
            "inputCount": max(0, int(input_count)),
            "outputCount": max(0, int(output_count)),
            "error": str(error) if error else None,
        }
        if error:
            self.add_error(key, str(error), recoverable=status != "failed")
        self.emit("running")

    def source(self, key: str, name: str, category: str, status: str, record_count: int, error: Optional[str] = None, used_fallback: bool = False) -> None:
        if used_fallback:
            status = "failed"
            record_count = 0
            error = error or "Fallback output was rejected by production policy."
            self.add_error(key, error, recoverable=True)
        self.sources[key] = {
            "key": key,
            "name": name,
            "category": category,
            "status": status,
            "recordCount": max(0, int(record_count)),
            "checkedAt": utc_now(),
            "usedFallback": False,
            "error": str(error) if error else None,
        }

    def add_error(self, stage: str, message: str, recoverable: bool) -> None:
        self.errors.append({
            "stage": stage,
            "message": str(message),
            "occurredAt": utc_now(),
            "recoverable": bool(recoverable),
        })

    def _unsafe(self, finding: Dict[str, Any]) -> bool:
        flags = (
            "impact_fallback", "entity_fallback", "risk_fallback", "validation_fallback",
            "triage_fallback", "is_fallback", "is_mock", "is_simulated", "mock", "simulated",
        )
        if any(bool(finding.get(flag)) for flag in flags):
            return True
        return bool(UNSAFE_TEXT_PATTERN.search(f"{finding.get('title', '')} {finding.get('source', '')}"))

    def _finding(self, finding: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self._unsafe(finding) or finding.get("validation_status") != "approved":
            return None
        title = str(finding.get("title", "")).strip()
        source_name = str(finding.get("source") or finding.get("source_name") or "").strip()
        if not title or not source_name:
            return None
        try:
            risk = int(finding["policy_risk_score"])
        except (KeyError, TypeError, ValueError):
            return None
        if risk < 0 or risk > 100:
            return None
        impact = str(finding.get("impact_score", "")).lower()
        if impact not in {"high", "medium", "low"}:
            return None
        confidence = finding.get("confidence", finding.get("relevance_score", 0))
        try:
            confidence = min(1.0, max(0.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.0
        raw_context = str(
            finding.get("full_text") or finding.get("text_context") or finding.get("snippet") or ""
        ).strip()
        summary = str(finding.get("compressed_summary") or finding.get("summary") or finding.get("snippet") or "").strip()
        url = str(finding.get("url") or "").strip() or None
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

    def build_bundle(self, status: str, records: Iterable[Dict[str, Any]] = (), report_path: Optional[str] = None) -> Dict[str, Any]:
        now = utc_now()
        self.updated_at = now
        self.status = status
        if status == "completed":
            self.completed_at = now
        if status == "failed":
            self.failed_at = now
        safe_findings = self._findings(records)
        report = None
        if report_path:
            path = Path(report_path)
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

    def emit(self, status: str, records: Iterable[Dict[str, Any]] = (), report_path: Optional[str] = None) -> Dict[str, Any]:
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
