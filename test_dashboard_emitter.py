import json
from pathlib import Path

from jsonschema import validate

from infrastructure.dashboard_emitter import DashboardRunEmitter


SCHEMA = json.loads((Path(__file__).parent / "contracts" / "swarm_run_bundle.schema.json").read_text())


def test_emitter_writes_empty_starting_bundle(tmp_path):
    emitter = DashboardRunEmitter("run_1788377000", str(tmp_path), "Policy intelligence run")
    bundle = emitter.emit("starting")
    stored = json.loads((tmp_path / "dashboard_bundle.json").read_text())
    assert stored == bundle
    assert bundle["run"]["mode"] == "production"
    assert bundle["findings"] == []
    assert bundle["report"] is None
    validate(instance=bundle, schema=SCHEMA)


def test_emitter_excludes_fallback_findings(tmp_path):
    emitter = DashboardRunEmitter("run_1788377001", str(tmp_path), "Policy intelligence run")
    record = {
        "title": "Source-backed record",
        "source": "Direct source",
        "impact_score": "high",
        "policy_risk_score": 80,
        "validation_status": "approved",
        "impact_fallback": True,
    }
    bundle = emitter.build_bundle("running", [record])
    assert bundle["findings"] == []


def test_completed_run_requires_written_report(tmp_path):
    emitter = DashboardRunEmitter("run_1788377002", str(tmp_path), "Policy intelligence run")
    try:
        emitter.build_bundle("completed", [])
    except ValueError as error:
        assert "requires an actual generated report" in str(error)
    else:
        raise AssertionError("Completed run accepted without a report")


def test_stage_updates_emit_running_bundle(tmp_path):
    emitter = DashboardRunEmitter("run_1788377003", str(tmp_path), "Stage lifecycle test")
    submitted = []
    emitter._submit = submitted.append

    emitter.emit("starting")
    emitter.stage("discovery", "running")
    emitter.stage("discovery", "completed", output_count=3)

    assert submitted[0]["run"]["status"] == "starting"
    assert submitted[1]["run"]["status"] == "running"
    assert submitted[2]["stages"][0]["status"] == "completed"
    stored = json.loads((tmp_path / "dashboard_bundle.json").read_text())
    assert stored["stages"][0]["outputCount"] == 3


def test_orchestrator_declares_all_terminal_emissions():
    source = (Path(__file__).parent / "agents" / "orchestrator.py").read_text()
    assert 'emitter.emit("starting")' in source
    assert 'emitter.emit("failed")' in source
    assert 'final_status = "completed" if report_status == "completed" else "partial"' in source
    assert "emitter.emit(final_status" in source
