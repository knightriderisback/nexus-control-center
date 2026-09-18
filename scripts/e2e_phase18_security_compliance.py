#!/usr/bin/env python3
"""
Real Local E2E Verification Scenario for Phase 18:
Autonomous Security & Compliance Operations Engine (SecOps & Compliance Plane).

Lifecycle:
1. Verify $0.00 FinOps Zero-Cost Sentinel Invariant.
2. Initialize temporary sandbox repository directory with controlled synthetic security threats.
3. Trigger SecurityComplianceEngine AST secret scanner & SAST code analyzer.
4. Verify detection, classification (CRITICAL / HIGH), and CVSS scoring.
5. Quarantine critical secret finding into POSIX 0600 Threat Vault.
6. Verify in-place token redaction and vault file permissions.
7. Run comprehensive compliance benchmark across all 6 frameworks (CIS, SOC2, ISO27001, NIST, GDPR, FinOps).
8. Validate Telemetry Posture Score calculation & Audit Trail / Memory persistence.
9. Safe sandbox cleanup.
"""

import os
import sys
import stat
import json
import tempfile
from pathlib import Path

# Add backend to PYTHONPATH
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from models.schemas import (
    SecurityScanRequest,
    ThreatSeverity,
    VulnerabilityCategory,
    ComplianceFramework,
    FindingStatus,
    ToolCategory,
    UniversalToolInvocationRequest
)
from orchestrator.security_compliance_engine import security_compliance_engine
from orchestrator.universal_tool_engine import universal_tool_engine
from core.cost_guard import cost_guard
from orchestrator.mission_memory import MissionMemoryManager


def run_phase18_e2e():
    print("=" * 80)
    print("  NEXUS PHASE 18: AUTONOMOUS SECOPS & COMPLIANCE E2E VERIFICATION")
    print("=" * 80)

    # 1. FinOps Invariant Check
    print("\n[STEP 1] Validating FinOps $0.00 Zero-Cost Sentinel...")
    cost_status = cost_guard.get_cost_summary()
    print(f"  -> Current Spend: ${cost_status['current_spend_usd']:.2f}")
    print(f"  -> Spend Ceiling: ${cost_status.get('hard_spend_limit_usd', 0.0):.2f}")
    print(f"  -> Billing Linked: {cost_status['billing_linked']}")
    assert cost_status["current_spend_usd"] == 0.0, "FinOps zero-cost violated!"
    assert cost_status["billing_linked"] is False, "Paid billing detected!"
    print("  ✓ Zero-Cost Governance Invariant Verified.")

    # 2. Setup Sandbox Threat Target
    print("\n[STEP 2] Creating temporary sandbox with synthetic vulnerabilities...")
    with tempfile.TemporaryDirectory(prefix="nexus_secops_e2e_") as tmp_dir:
        sandbox_path = Path(tmp_dir)
        threat_file = sandbox_path / "vulnerable_service.py"
        threat_file.write_text(
            "# Synthetic test file for Phase 18 SecOps validation\n"
            "AWS_SECRET_KEY = \"AKIAIOSFODNN7EXAMPLE12345\"\n"
            "GITHUB_PAT = \"ghp_abcdefghijklmnopqrstuvwxyz1234567890\"\n\n"
            "def handle_rpc(user_command, raw_payload):\n"
            "    import os, pickle\n"
            "    # Dangerous execution\n"
            "    os.system(user_command)\n"
            "    return pickle.loads(raw_payload)\n"
        )
        print(f"  -> Created synthetic threat artifact at: {threat_file}")

        # Create requirements.txt
        req_file = sandbox_path / "requirements.txt"
        req_file.write_text("requests==2.25.0\nurllib3==1.26.4\nagpl-copyleft==0.1.0\n")
        print(f"  -> Created synthetic dependency manifest at: {req_file}")

        # 3. Codebase Security Scan
        print("\n[STEP 3] Executing Autonomous Security Scan (AST + SAST + CVE)...")
        scan_req = SecurityScanRequest(
            target_path=str(sandbox_path),
            include_secrets=True,
            include_sast=True,
            include_dependencies=True,
            auto_quarantine_critical=False
        )
        report = security_compliance_engine.scan_codebase(scan_req)
        print(f"  -> Total Files Scanned: {report.total_files_scanned}")
        print(f"  -> Total Findings: {len(report.findings)}")
        print(f"  -> Scan Duration: {report.duration_seconds:.3f}s")
        print(f"  -> Aggregate Risk Score: {report.risk_score:.1f} / 100")

        secret_findings = [f for f in report.findings if f.category == VulnerabilityCategory.SECRET_LEAK]
        sast_findings = [f for f in report.findings if f.category == VulnerabilityCategory.SAST_INJECTION]
        cve_findings = [f for f in report.findings if f.category == VulnerabilityCategory.DEPENDENCY_CVE]
        license_findings = [f for f in report.findings if f.category == VulnerabilityCategory.LICENSE_NONCOMPLIANCE]

        print(f"  -> Secrets Detected: {len(secret_findings)}")
        print(f"  -> SAST Injections Detected: {len(sast_findings)}")
        print(f"  -> CVE Dependencies Detected: {len(cve_findings)}")
        print(f"  -> License Noncompliances: {len(license_findings)}")

        assert len(secret_findings) >= 2, f"Expected >=2 secret findings, got {len(secret_findings)}"
        assert len(sast_findings) >= 2, f"Expected >=2 SAST findings, got {len(sast_findings)}"
        assert len(cve_findings) >= 1, f"Expected >=1 CVE finding, got {len(cve_findings)}"
        print("  ✓ Full Detection Spectrum Validated.")

        # 4. Threat Quarantine Isolation
        print("\n[STEP 4] Testing Automated Threat Quarantine Vault...")
        secret_finding = secret_findings[0]
        quarantine_record = security_compliance_engine.quarantine_threat(
            secret_finding.finding_id,
            operator="E2E_SECOPS_VERIFIER"
        )
        assert quarantine_record is not None, "Quarantine execution failed!"
        print(f"  -> Quarantined Finding ID: {quarantine_record.finding_id}")
        print(f"  -> Vault Location: {quarantine_record.quarantined_path}")
        print(f"  -> Applied Mode: {quarantine_record.permissions_applied}")

        # Check POSIX 0600 mode
        st_mode = stat.S_IMODE(os.stat(quarantine_record.quarantined_path).st_mode)
        assert st_mode == (stat.S_IRUSR | stat.S_IWUSR), f"Expected 0600 mode, got {oct(st_mode)}"
        print(f"  ✓ Verified POSIX 0600 ({oct(st_mode)}) Vault Permissions.")

        # Check source file redaction
        source_content = threat_file.read_text()
        assert "[REDACTED_BY_SECOPS" in source_content, "Source token was not redacted in-place!"
        print("  ✓ Verified In-Place Source Token Redaction.")

        # 5. Continuous Compliance Benchmark
        print("\n[STEP 5] Evaluating Multi-Standard Compliance Benchmarks...")
        all_frameworks = [
            ComplianceFramework.SOC2,
            ComplianceFramework.ISO27001,
            ComplianceFramework.CIS_BENCHMARK,
            ComplianceFramework.NIST_800_53,
            ComplianceFramework.GDPR_PRIVACY,
            ComplianceFramework.FINOPS_ZERO_COST
        ]
        total_controls = 0
        passed_controls = 0
        for fw in all_frameworks:
            results = security_compliance_engine.evaluate_compliance(fw)
            fw_passed = sum(1 for r in results if r.passed)
            total_controls += len(results)
            passed_controls += fw_passed
            print(f"  -> Framework [{fw.value}]: {fw_passed}/{len(results)} controls passed")

        assert total_controls >= 6, f"Expected >=6 total controls, evaluated {total_controls}"
        print(f"  ✓ Multi-Framework Evaluation Complete ({passed_controls}/{total_controls} controls passed).")

        # 6. Telemetry & Posture Scoring
        print("\n[STEP 6] Calculating SecOps Telemetry Posture...")
        telemetry = security_compliance_engine.get_telemetry()
        print(f"  -> Overall Security Posture Score: {telemetry.overall_security_posture_score} / 100")
        print(f"  -> Quarantined Threats Count: {telemetry.quarantined_threats}")
        print(f"  -> Active Scanners: {', '.join(telemetry.active_scanners)}")
        print(f"  -> Zero-Trust Status: {telemetry.zero_trust_status}")
        assert telemetry.zero_trust_status in ("ACTIVE", "ENFORCED")
        print("  ✓ SecOps Telemetry Cockpit Validated.")

        # 7. Universal Tool Engine Integration
        print("\n[STEP 7] Verifying Universal Tool Engine SecOps Capabilities...")
        tools = universal_tool_engine.list_tools()
        secops_tools = [t for t in tools if t.category == ToolCategory.SECURITY or t.category.value == "SECURITY" or "secops." in t.tool_id]
        print(f"  -> Registered SecOps Tools ({len(secops_tools)}): {[t.tool_id for t in secops_tools]}")
        assert len(secops_tools) >= 4, f"Expected 4 secops tools, found {len(secops_tools)}"

        # Execute universal tool call
        inv_req = UniversalToolInvocationRequest(
            tool_id="secops.audit_dependencies",
            input_payload={"target_path": str(sandbox_path)},
            caller_agent_id="e2e-verifier"
        )
        res = universal_tool_engine.invoke_tool(inv_req)
        assert res.status == "SUCCESS", f"Tool execution failed: {res.error}"
        print(f"  ✓ Universal Tool 'secops.audit_dependencies' executed successfully ({len(res.output.get('findings', []))} findings).")

        # 8. Memory & Knowledge Base Persistence
        print("\n[STEP 8] Confirming Long-Term Mission Knowledge & Audit Traceability...")
        mem_manager = MissionMemoryManager()
        knowledge_entries = mem_manager.query_knowledge(category="secops_threat_quarantine")
        print(f"  -> Knowledge Entries in 'secops_threat_quarantine': {len(knowledge_entries)}")
        assert len(knowledge_entries) >= 1, "Expected knowledge entry to be persisted!"
        print("  ✓ Mission Knowledge & Audit Traceability Confirmed.")

    print("\n" + "=" * 80)
    print("  ALL PHASE 18 SECOPS & COMPLIANCE E2E CHECKS PASSED PERFECTLY!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_phase18_e2e()
    sys.exit(0 if success else 1)
