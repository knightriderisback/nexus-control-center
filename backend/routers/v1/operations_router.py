"""
NEXUS Phase 17: Autonomous Operations & Self-Healing REST API Router.
Mounted under /api/v1/operations.
Provides provider-neutral operations endpoints for incident lifecycle, diagnosis,
recovery policies, metrics, and recovery history.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body

from models.schemas import (
    IncidentRecord,
    TriggerIncidentRequest,
    RemediateIncidentRequest,
    OperationsMetrics,
    RecoveryPolicy,
    RecoveryHistoryRecord,
    WatchdogCheckResult,
    IncidentStatus,
)
from orchestrator.self_healing_engine import self_healing_engine
from core.approvals import approvals_manager

router = APIRouter(prefix="/operations", tags=["Autonomous Operations & Self-Healing"])


@router.get("", response_model=List[IncidentRecord])
def list_incidents(
    category: Optional[str] = Query(None, description="Filter by failure category"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW, INFO)"),
    status: Optional[str] = Query(None, description="Filter by lifecycle status")
):
    """Lists all operational incident records with optional category/severity/status filtering."""
    return self_healing_engine.list_incidents(category=category, severity=severity, status=status)


@router.get("/health", response_model=List[WatchdogCheckResult])
def get_operations_health():
    """Executes a live health inspection sweep across all 6 watchdogs."""
    return self_healing_engine.run_all_watchdogs()


@router.get("/metrics", response_model=OperationsMetrics)
def get_operations_metrics():
    """Returns operational metrics including uptime, MTTR, success rate, and failure distributions."""
    return self_healing_engine.get_operations_metrics()


@router.get("/policies", response_model=RecoveryPolicy)
def get_recovery_policies():
    """Returns currently enforced recovery and loop-protection policies."""
    return self_healing_engine.get_recovery_policy()


@router.put("/policies", response_model=RecoveryPolicy)
def update_recovery_policies(policy: RecoveryPolicy):
    """Updates operational recovery policies under zero-cost governance."""
    return self_healing_engine.update_recovery_policy(policy)


@router.get("/recovery-history", response_model=List[RecoveryHistoryRecord])
def get_recovery_history():
    """Returns chronological audit log of all automated and manual recovery attempts."""
    return self_healing_engine.get_recovery_history()


@router.get("/global", response_model=Dict[str, Any])
def get_global_operations_state_alias():
    """Returns unified real-time operations state across all 13 subsystems."""
    from orchestrator.command_control_kernel import command_control_kernel
    return command_control_kernel.get_global_operations_state().model_dump()


@router.get("/timeline", response_model=List[Dict[str, Any]])
def get_operations_timeline_alias(
    limit: int = Query(100, ge=1, le=500),
    command_id: Optional[str] = Query(None)
):
    """Returns immutable chronological audit timeline (COMMAND -> DECISION -> ACTION -> RESULT -> EVIDENCE)."""
    from orchestrator.command_control_kernel import command_control_kernel
    return [e.model_dump() for e in command_control_kernel.get_operations_timeline(limit=limit, command_id=command_id)]


@router.get("/events", response_model=List[Dict[str, Any]])
def get_global_event_bus_stream_alias(
    limit: int = Query(100, ge=1, le=500),
    project_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None)
):
    """Returns cryptographic Global Event Bus stream."""
    from orchestrator.command_control_kernel import command_control_kernel
    return [e.model_dump() for e in command_control_kernel.get_event_stream(limit=limit, project_id=project_id, event_type=event_type)]


@router.get("/{incident_id}", response_model=IncidentRecord)
def get_incident(incident_id: str):
    """Retrieves detailed incident record with diagnosis evidence and healing trace."""
    inc = self_healing_engine.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    return inc


@router.post("/{incident_id}/acknowledge", response_model=IncidentRecord)
def acknowledge_incident(incident_id: str, operator: str = Query("operator")):
    """Acknowledges an active incident by operator identity."""
    try:
        return self_healing_engine.acknowledge_incident(incident_id, operator=operator)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{incident_id}/recover", response_model=IncidentRecord)
def recover_incident(incident_id: str, request: Optional[RemediateIncidentRequest] = None):
    """Executes or resumes automated remediation playbook for an incident."""
    force = request.force if request else False
    try:
        return self_healing_engine.execute_remediation(incident_id, force=force)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{incident_id}/retry", response_model=IncidentRecord)
def retry_incident(incident_id: str):
    """Retries remediation execution for an incident with loop protection."""
    try:
        return self_healing_engine.retry_incident(incident_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{incident_id}/escalate", response_model=IncidentRecord)
def escalate_incident(incident_id: str, reason: str = Query("Manual operator escalation")):
    """Escalates an incident for human intervention or manual recovery."""
    try:
        return self_healing_engine.escalate_incident(incident_id, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{incident_id}/stop", response_model=IncidentRecord)
def stop_incident_recovery(incident_id: str, reason: str = Query("Manual operator aborted")):
    """Stops remediation and marks incident recovery as STOPPED."""
    try:
        return self_healing_engine.stop_recovery(incident_id, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
