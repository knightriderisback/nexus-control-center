"""
NEXUS Phase 18: Autonomous Security & Compliance REST API Router.
Mounted under /api/v1/secops and /api/v1/security.
Provides endpoints for SAST scans, secret detection, threat quarantine, compliance audits, policy evaluations, and posture telemetry.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body

from models.schemas import (
    SecurityScanRequest,
    SecurityScanReport,
    SecurityFinding,
    ComplianceControlResult,
    QuarantineRecord,
    SecOpsTelemetry,
    ComplianceFramework,
    FindingStatus,
)
from orchestrator.security_compliance_engine import security_compliance_engine
from core.audit import get_recent_audit_events

router = APIRouter(prefix="/secops", tags=["Security & Compliance Operations"])
security_router = APIRouter(prefix="/security", tags=["Security & Compliance Operations"])


# =========================================================================
# CORE ENDPOINTS (Mounted under both /secops and /security)
# =========================================================================

def _get_security_health():
    telemetry = security_compliance_engine.get_telemetry()
    return {
        "status": "ONLINE",
        "subsystem": "security-compliance",
        "posture_score": telemetry.overall_security_posture_score,
        "zero_trust_status": telemetry.zero_trust_status,
        "active_scanners": telemetry.active_scanners,
        "timestamp": telemetry.calculated_at
    }


def _run_scan(request: Optional[SecurityScanRequest] = None):
    try:
        return security_compliance_engine.scan_codebase(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _list_findings(
    severity: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None
):
    return security_compliance_engine.list_findings(severity=severity, category=category, status=status)


def _get_finding(finding_id: str):
    finding = security_compliance_engine.get_finding(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail=f"Security finding '{finding_id}' not found.")
    return finding


def _quarantine_threat(finding_id: str, operator: str = "cyber-secops-operator"):
    try:
        return security_compliance_engine.quarantine_threat(finding_id, operator=operator)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _remediate_finding(finding_id: str, operator: str = "cyber-secops-operator"):
    try:
        return security_compliance_engine.remediate_finding(finding_id, operator=operator)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _evaluate_compliance(framework: Optional[str] = None):
    fw_enum = ComplianceFramework(framework) if framework in [f.value for f in ComplianceFramework] else None
    return security_compliance_engine.evaluate_compliance(framework=fw_enum)


def _get_telemetry():
    return security_compliance_engine.get_telemetry()


def _list_quarantine():
    return security_compliance_engine.list_quarantine_records()


def _release_quarantine(quarantine_id: str, operator: str = "cyber-secops-operator", reason: str = "Approved for release"):
    try:
        success = security_compliance_engine.release_quarantine(quarantine_id, operator=operator, reason=reason)
        return {"status": "ok", "released": success, "quarantine_id": quarantine_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _transition_finding(finding_id: str, new_state: str, actor: str = "cyber-secops-operator", reason: str = ""):
    try:
        state_enum = FindingStatus(new_state)
        return security_compliance_engine.transition_finding_state(finding_id, state_enum, actor=actor, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_audit_trail():
    events = get_recent_audit_events(limit=100)
    return [e for e in events if "secops" in getattr(e, "action", "") or "security" in getattr(e, "action", "")]


def _get_history():
    return security_compliance_engine.list_scan_history()


# Mount routes onto both routers (/secops and /security)
for r in (router, security_router):
    r.add_api_route("/health", _get_security_health, methods=["GET"])
    r.add_api_route("/posture", _get_telemetry, response_model=SecOpsTelemetry, methods=["GET"])
    r.add_api_route("/scan", _run_scan, response_model=SecurityScanReport, methods=["POST"])
    r.add_api_route("/findings", _list_findings, response_model=List[SecurityFinding], methods=["GET"])
    r.add_api_route("/findings/{finding_id}", _get_finding, response_model=SecurityFinding, methods=["GET"])
    r.add_api_route("/findings/{finding_id}/quarantine", _quarantine_threat, response_model=QuarantineRecord, methods=["POST"])
    r.add_api_route("/findings/{finding_id}/remediate", _remediate_finding, methods=["POST"])
    r.add_api_route("/findings/{finding_id}/transition", _transition_finding, response_model=SecurityFinding, methods=["POST"])
    r.add_api_route("/compliance", _evaluate_compliance, response_model=List[ComplianceControlResult], methods=["GET"])
    r.add_api_route("/telemetry", _get_telemetry, response_model=SecOpsTelemetry, methods=["GET"])
    r.add_api_route("/quarantine", _list_quarantine, response_model=List[QuarantineRecord], methods=["GET"])
    r.add_api_route("/quarantine/{quarantine_id}/release", _release_quarantine, methods=["POST"])
    r.add_api_route("/audit", _get_audit_trail, methods=["GET"])
    r.add_api_route("/history", _get_history, methods=["GET"])
    r.add_api_route("/evidence", lambda: security_compliance_engine.list_evidence_records(), methods=["GET"])
    r.add_api_route("/policies", lambda: security_compliance_engine._policy_rules, methods=["GET"])
    r.add_api_route("/policies/evaluate", lambda target_action=Body(..., embed=True), target_entity=Body(..., embed=True), context=Body(None, embed=True), actor=Body("cyber-secops-operator", embed=True): security_compliance_engine.evaluate_security_policy(target_action=target_action, target_entity=target_entity, context=context, actor=actor), methods=["POST"])

    # Explicit lifecycle action aliases
    r.add_api_route("/findings/{finding_id}/acknowledge", lambda finding_id, actor="operator", reason="": _transition_finding(finding_id, FindingStatus.ACKNOWLEDGED.value, actor, reason), methods=["POST"])
    r.add_api_route("/findings/{finding_id}/escalate", lambda finding_id, actor="operator", reason="": _transition_finding(finding_id, FindingStatus.ESCALATED.value, actor, reason), methods=["POST"])
    r.add_api_route("/findings/{finding_id}/approve", lambda finding_id, actor="operator", reason="": _transition_finding(finding_id, FindingStatus.APPROVED.value, actor, reason), methods=["POST"])
    r.add_api_route("/findings/{finding_id}/release", lambda finding_id, operator="operator", reason="Approved release": _release_quarantine(finding_id, operator, reason), methods=["POST"])
