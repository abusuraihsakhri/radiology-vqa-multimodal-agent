"""Regression coverage for package behavior, safety boundaries, and CLI handling."""
import csv
import json

import pytest
from fastapi.testclient import TestClient

from agents.api import app
from agents.base import AuditTrail, PHIGuard, SecurityException
from agents.llm_factory import LLMFactory
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from cli import main


def test_attributes_are_checked_for_identifiers():
    supervisor = SystemSupervisor()
    payload = SystemTaskPayload(
        task_id="TEST-001",
        target_identifier="SYNTHETIC-01",
        primary_metric=1,
        attributes={"notes": {"contact": "private@example.com"}},
    )
    with pytest.raises(SecurityException):
        supervisor.process_task(payload)


def test_public_audit_snapshot_does_not_mutate_chain():
    trail = AuditTrail(secret_key="synthetic-test-key")
    trail.log("tester", "local", "TEST", {"safe": True})
    exported = trail.get_trail()
    exported[0]["payload_hash"] = "CORRUPTED"
    exported.clear()
    assert trail.verify_integrity()
    assert len(trail.get_trail()) == 1


def test_unsupported_providers_fail_without_mocking_success():
    assert "Deterministic" in LLMFactory.create("mock").invoke("test query")
    for name in ("openai", "ollama", "claude", "unknown"):
        with pytest.raises(ValueError, match="not implemented"):
            LLMFactory.create(name)


def test_api_handles_audit_and_rejects_nested_identifiers():
    client = TestClient(app)
    result = client.post("/api/audit", json={
        "task_id": "TEST-API-01",
        "target_identifier": "SYNTHETIC-01",
        "primary_metric": 30,
        "secondary_metric": 2,
        "status_descriptor": "NOMINAL",
    })
    assert result.status_code == 200
    data = result.json()
    assert data["overall_urgency"] == "ELEVATED_RISK"
    assert data["total_alerts"] == 1

    # SecurityException should not silently become a successful dossier.
    # A blocked payload currently raises a domain exception outside the FastAPI
    # request validator; the API must translate this to a non-200 response.
    denied = client.post("/api/audit", json={
        "task_id": "TEST-API-02",
        "target_identifier": "SYNTHETIC-01",
        "primary_metric": 2,
        "attributes": {"contact": "private@example.com"},
    })
    assert denied.status_code == 400


def test_batch_validates_columns_and_values(tmp_path, capsys):
    missing = tmp_path / "missing.csv"
    missing.write_text("task_id,primary_metric\nA,3\n", encoding="utf-8")
    assert main(["batch", "-i", str(missing), "-o", str(tmp_path / "out.csv")]) == 1

    invalid = tmp_path / "invalid.csv"
    invalid.write_text(
        "task_id,target_identifier,primary_metric,secondary_metric,is_critical_flag\n"
        "ONE,SYN-01,3,2,maybe\n"
        "TWO,SYN-02,3,2,no\n",
        encoding="utf-8",
    )
    output = tmp_path / "good.csv"
    assert main(["batch", "-i", str(invalid), "-o", str(output)]) == 0
    with output.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["task_id"] == "TWO"


def test_audit_verification_failure_returns_nonzero(monkeypatch):
    from cli import AuditLogger
    monkeypatch.setattr(AuditLogger, "verify_integrity", lambda: False)
    assert main(["verify-audit"]) == 1


def test_batch_skips_recognizable_identifiers(tmp_path):
    source = tmp_path / "phi.csv"
    source.write_text(
        "task_id,target_identifier,primary_metric,secondary_metric,is_critical_flag\n"
        "SAFE,SYNTHETIC-01,2,1,no\n"
        "UNSAFE,private@example.com,2,1,no\n", encoding="utf-8"
    )
    destination = tmp_path / "results.csv"
    assert main(["batch", "-i", str(source), "-o", str(destination)]) == 0
    with destination.open(encoding="utf-8", newline="") as handle:
        data = list(csv.DictReader(handle))
    assert len(data) == 1
    assert data[0]["task_id"] == "SAFE"


def test_simulator_rejects_nonpositive_iterations():
    from simulator import run_simulation
    with pytest.raises(ValueError, match="positive"):
        run_simulation(0)


def test_batch_prevents_overwriting_source_and_duplicate_headers(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("task_id,target_identifier,primary_metric\nT1,SYN-01,2\n", encoding="utf-8")
    assert main(["batch", "-i", str(source), "-o", str(source)]) == 1
    assert "T1,SYN-01,2" in source.read_text(encoding="utf-8")
    duplicates = tmp_path / "duplicates.csv"
    duplicates.write_text("task_id,task_id,target_identifier,primary_metric\nT1,T2,SYN-01,2\n", encoding="utf-8")
    assert main(["batch", "-i", str(duplicates), "-o", str(tmp_path / "out.csv")]) == 1
