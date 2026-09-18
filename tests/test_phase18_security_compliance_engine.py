import os
import stat
import json
import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from server import app
from models.schemas import (
    ThreatSeverity,
    VulnerabilityCategory,
    ComplianceFramework,
    FindingStatus,
    FindingConfidence,
    PolicyDecision,
    ComplianceStatus,
    SecurityScanRequest,
    SecurityScanReport,
    UniversalToolInvocationRequest
)
from orchestrator.security_compliance_engine import (
    security_compliance_engine,
    get_security_compliance_engine
)
from orchestrator.universal_tool_engine import universal_tool_engine
from core.cost_guard import cost_guard


@pytest.fixture
def secops_engine():
    return security_compliance_engine


@pytest.fixture
def client():
    return TestClient(app)


def test_secops_engine_initialization(secops_engine):
    assert secops_engine is not None
    assert secops_engine.quarantine_dir.exists()
    assert secops_engine.data_dir.exists()


def test_secret_scanner_detection_and_fingerprinting(secops_engine, tmp_path):
    test_file = tmp_path / "leaky_config.py"
    test_file.write_text(
        'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
        'GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyzAB"\n'
        'DB_URL = "postgres://admin:supersecretpassword@localhost:5432/nexus"\n'
    )

    req = SecurityScanRequest(
        target_path=str(tmp_path),
        include_secrets=True,
        include_sast=False,
        include_dependencies=False
    )
    report = secops_engine.scan_codebase(req)

    assert report.total_files_scanned >= 1
    assert len(report.findings) >= 2
    
    categories = [f.category for f in report.findings]
    assert VulnerabilityCategory.SECRET_LEAK in categories
    
    severities = [f.severity for f in report.findings]
    assert ThreatSeverity.CRITICAL in severities

    for f in report.findings:
        assert f.fingerprint is not None
        assert len(f.fingerprint) == 16


def test_python_ast_vulnerability_detection(secops_engine, tmp_path):
    test_file = tmp_path / "insecure_app.py"
    test_file.write_text(
        'import os, pickle\n'
        'def execute_cmd(user_input):\n'
        '    os.system(user_input)\n'
        'def run_code(code):\n'
        '    eval(code)\n'
        'def unpack(data):\n'
        '    return pickle.loads(data)\n'
    )

    req = SecurityScanRequest(
        target_path=str(tmp_path),
        include_secrets=False,
        include_sast=True,
        include_dependencies=False
    )
    report = secops_engine.scan_codebase(req)

    assert len(report.findings) >= 3
    for f in report.findings:
        assert f.category == VulnerabilityCategory.SAST_INJECTION
        assert f.severity in (ThreatSeverity.CRITICAL, ThreatSeverity.HIGH)
        assert f.confidence in (FindingConfidence.CONFIRMED_FINDING, FindingConfidence.HEURISTIC_FINDING)


def test_javascript_typescript_security_analysis(secops_engine, tmp_path):
    ts_file = tmp_path / "unsafe_component.tsx"
    ts_file.write_text(
        'import React from "react";\n'
        'export const Unsafe = ({ data }) => {\n'
        '  eval(data);\n'
        '  return <div dangerouslySetInnerHTML={{ __html: data }} />;\n'
        '};\n'
    )

    req = SecurityScanRequest(
        target_path=str(tmp_path),
        include_secrets=False,
        include_sast=True,
        include_dependencies=False
    )
    report = secops_engine.scan_codebase(req)
    assert len(report.findings) >= 1
    assert report.findings[0].category == VulnerabilityCategory.SAST_INJECTION


def test_dependency_cve_and_license_audit(secops_engine, tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text(
        "requests==2.25.0\n"
        "urllib3==1.26.4\n"
        "agpl-licensed-package==1.0.0\n"
        "fastapi>=0.100.0\n"
    )

    findings = secops_engine._audit_dependencies(target_path=str(tmp_path))
    assert len(findings) >= 2

    cve_findings = [f for f in findings if f.cve_id]
    assert len(cve_findings) >= 1
    assert any("CVE-2021-33503" in f.cve_id for f in cve_findings)

    license_findings = [f for f in findings if f.category == VulnerabilityCategory.LICENSE_NONCOMPLIANCE]
    assert len(license_findings) >= 1


def test_compliance_framework_evaluation(secops_engine):
    cis_results = secops_engine.evaluate_compliance(ComplianceFramework.CIS_BENCHMARK)
    assert len(cis_results) >= 2
    assert all(r.framework == ComplianceFramework.CIS_BENCHMARK for r in cis_results)
    assert all(r.status == ComplianceStatus.COMPLIANT for r in cis_results)

    finops_results = secops_engine.evaluate_compliance(ComplianceFramework.FINOPS_ZERO_COST)
    assert len(finops_results) >= 1
    assert any("FINOPS-001" in r.control_id for r in finops_results)
    assert finops_results[0].passed is True


def test_threat_quarantine_isolation_and_release(secops_engine, tmp_path):
    threat_file = tmp_path / "threat_script.py"
    threat_file.write_text(
        'AWS_ACCESS_KEY_ID = "AKIAEXAMPLE1234567890"\n'
        'print("compromised secret")\n'
    )

    req = SecurityScanRequest(target_path=str(tmp_path), include_secrets=True)
    report = secops_engine.scan_codebase(req)
    assert len(report.findings) >= 1

    finding = report.findings[0]
    quarantine_record = secops_engine.quarantine_threat(finding.finding_id, operator="TEST_SUITE")

    assert quarantine_record is not None
    assert quarantine_record.finding_id == finding.finding_id
    assert os.path.exists(quarantine_record.quarantined_path)

    st_mode = stat.S_IMODE(os.stat(quarantine_record.quarantined_path).st_mode)
    assert st_mode == (stat.S_IRUSR | stat.S_IWUSR)

    content = threat_file.read_text()
    assert "[REDACTED_BY_SECOPS" in content

    stored = secops_engine.get_finding(finding.finding_id)
    assert stored is not None
    assert stored.status == FindingStatus.QUARANTINED

    # Test quarantine release
    released = secops_engine.release_quarantine(quarantine_record.quarantine_id, operator="TEST_SUITE", reason="Unit test release")
    assert released is True


def test_finding_lifecycle_state_machine(secops_engine, tmp_path):
    test_file = tmp_path / "state_test.py"
    test_file.write_text('SECRET_KEY = "AKIA1234567890123456"\n')

    req = SecurityScanRequest(target_path=str(tmp_path), include_secrets=True)
    report = secops_engine.scan_codebase(req)
    assert len(report.findings) >= 1

    finding = report.findings[0]
    
    # Transition to INVESTIGATING
    f1 = secops_engine.transition_finding_state(finding.finding_id, FindingStatus.INVESTIGATING, actor="TEST", reason="Triage")
    assert f1.status == FindingStatus.INVESTIGATING

    # Transition to ACCEPTED_RISK
    f2 = secops_engine.transition_finding_state(finding.finding_id, FindingStatus.ACCEPTED_RISK, actor="TEST", reason="Risk approved")
    assert f2.status == FindingStatus.ACCEPTED_RISK

    # Transition to RESOLVED
    f3 = secops_engine.transition_finding_state(finding.finding_id, FindingStatus.RESOLVED, actor="TEST", reason="Mitigated")
    assert f3.status == FindingStatus.RESOLVED
    assert f3.resolved_at is not None


def test_security_policy_engine_evaluations(secops_engine, tmp_path):
    # Test secret block policy
    finding = secops_engine.scan_codebase(SecurityScanRequest(target_path=str(tmp_path))).findings
    test_file = tmp_path / "secret.py"
    test_file.write_text('AWS_KEY = "AKIA9999888877776666"\n')
    report = secops_engine.scan_codebase(SecurityScanRequest(target_path=str(tmp_path), include_secrets=True))

    eval_record = secops_engine.evaluate_security_policy(
        target_action="git.merge",
        target_entity="main",
        context={"findings": report.findings}
    )
    assert eval_record.decision == PolicyDecision.BLOCK
    assert eval_record.rule_id == "SEC-POL-001"


def test_pre_merge_security_gate(secops_engine, tmp_path):
    evidence = secops_engine.evaluate_pre_merge_gate(
        branch="feature/nexus-secops",
        changed_files=["backend/orchestrator/security_compliance_engine.py"],
        session_id="sess-merge-001"
    )
    assert evidence is not None
    assert evidence.evidence_id.startswith("sec-ev-")
    assert evidence.passed is True


def test_pre_deployment_security_gate(secops_engine, tmp_path):
    evidence = secops_engine.evaluate_pre_deployment_gate(
        artifact_path=str(tmp_path),
        target_env="local",
        session_id="dep-sess-001"
    )
    assert evidence is not None
    assert evidence.evidence_id.startswith("dep-ev-")


def test_secops_telemetry_posture_score(secops_engine):
    telemetry = secops_engine.get_telemetry()
    assert telemetry.overall_security_posture_score >= 0
    assert telemetry.overall_security_posture_score <= 100
    assert "FINOPS_ZERO_COST" in telemetry.compliance_scores
    assert telemetry.zero_trust_status == "ENFORCED"


def test_secops_rest_api_endpoints(client, tmp_path):
    test_file = tmp_path / "api_test.py"
    test_file.write_text('ADMIN_API_KEY = "AKIA1111222233334444"\n')

    scan_res = client.post(
        "/api/v1/secops/scan",
        json={
            "target_path": str(tmp_path),
            "include_secrets": True,
            "include_sast": True,
            "include_dependencies": False,
            "auto_quarantine_critical": False
        }
    )
    assert scan_res.status_code == 200
    data = scan_res.json()
    assert "findings" in data
    assert len(data["findings"]) >= 1

    finding_id = data["findings"][0]["finding_id"]

    # Test GET /api/v1/secops/findings
    findings_res = client.get("/api/v1/secops/findings")
    assert findings_res.status_code == 200
    assert isinstance(findings_res.json(), list)

    # Test GET /api/v1/secops/findings/{id}
    finding_detail_res = client.get(f"/api/v1/secops/findings/{finding_id}")
    assert finding_detail_res.status_code == 200
    assert finding_detail_res.json()["finding_id"] == finding_id

    # Test POST /api/v1/secops/findings/{id}/transition
    trans_res = client.post(f"/api/v1/secops/findings/{finding_id}/transition?new_state=INVESTIGATING")
    assert trans_res.status_code == 200
    assert trans_res.json()["status"] == "INVESTIGATING"

    # Test POST /api/v1/secops/findings/{id}/quarantine
    quar_res = client.post(
        f"/api/v1/secops/findings/{finding_id}/quarantine?operator=API_TEST"
    )
    assert quar_res.status_code == 200
    assert "quarantine_id" in quar_res.json()

    # Test GET /api/v1/secops/quarantine
    quar_list = client.get("/api/v1/secops/quarantine")
    assert quar_list.status_code == 200
    assert len(quar_list.json()) >= 1

    # Test GET /api/v1/secops/policies
    pol_res = client.get("/api/v1/secops/policies")
    assert pol_res.status_code == 200
    assert len(pol_res.json()) >= 1

    # Test GET /api/v1/secops/evidence
    ev_res = client.get("/api/v1/secops/evidence")
    assert ev_res.status_code == 200

    # Test GET /api/v1/secops/compliance
    comp_res = client.get("/api/v1/secops/compliance")
    assert comp_res.status_code == 200
    assert isinstance(comp_res.json(), list)

    # Test GET /api/v1/secops/telemetry
    tel_res = client.get("/api/v1/secops/telemetry")
    assert tel_res.status_code == 200
    assert "overall_security_posture_score" in tel_res.json()


def test_universal_tool_engine_secops_tools():
    tool_ids = [t.tool_id for t in universal_tool_engine.list_tools()]

    assert "secops.scan_codebase" in tool_ids
    assert "secops.audit_dependencies" in tool_ids
    assert "secops.evaluate_compliance" in tool_ids
    assert "secops.quarantine_threat" in tool_ids

    req = UniversalToolInvocationRequest(
        tool_id="secops.evaluate_compliance",
        input_payload={"framework": "FINOPS_ZERO_COST"},
        caller_agent_id="test-agent",
        mission_id="test-mission"
    )
    res = universal_tool_engine.invoke_tool(req)

    assert res.status == "SUCCESS"
    assert "controls" in res.output
    assert res.output["total_controls"] >= 1


def test_finops_zero_cost_preservation():
    status = cost_guard.get_cost_summary()
    assert status["current_spend_usd"] == 0.0
    assert status["billing_linked"] is False
    assert status["zero_cost_guardrail_active"] is True
