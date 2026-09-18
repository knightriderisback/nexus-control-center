"""
NEXUS Phase 17: Autonomous Self-Healing Operations Engine REST API Router.
Mounted under /api/v1/self-healing.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from models.schemas import (
    IncidentRecord,
    TriggerIncidentRequest,
    RemediateIncidentRequest,
    RemediationPlaybook,
    SelfHealingTelemetry,
    WatchdogCheckResult,
    IncidentStatus,
)
from orchestrator.self_healing_engine import self_healing_engine
from core.approvals import approvals_manager

router = APIRouter(prefix="/self-healing", tags=["Self-Healing Operations"])


@router.get("/incidents", response_model=List[IncidentRecord])
def list_incidents(
    category: Optional[str] = Query(None, description="Filter by category (PROCESS_CRASH, PORT_CONFLICT, etc.)"),
    severity: Optional[str] = Query(None, description="Filter by severity (SEV_1_CRITICAL, SEV_2_HIGH, etc.)"),
    status: Optional[str] = Query(None, description="Filter by status (DETECTED, DIAGNOSING, RESOLVED, etc.)")
):
    """Lists all operational incidents with optional filtering."""
    return self_healing_engine.list_incidents(
        category=category,
        severity=severity,
        status=status
    )


@router.post("/incidents/trigger", response_model=IncidentRecord)
def trigger_incident(request: TriggerIncidentRequest):
    """Registers an incident and initiates automated diagnosis & self-healing."""
    try:
        return self_healing_engine.trigger_incident(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents/{incident_id}", response_model=IncidentRecord)
def get_incident(incident_id: str):
    """Retrieves full incident record, actions history, and RCA post-mortem."""
    inc = self_healing_engine.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    return inc


@router.post("/incidents/{incident_id}/remediate", response_model=IncidentRecord)
def remediate_incident(incident_id: str, request: Optional[RemediateIncidentRequest] = None):
    """Executes or resumes remediation playbook for an incident."""
    force = request.force if request else False
    try:
        return self_healing_engine.execute_remediation(incident_id, force=force)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/incidents/{incident_id}/approve", response_model=IncidentRecord)
def approve_and_heal_incident(incident_id: str):
    """Approves a high-risk remediation gate and resumes healing execution."""
    inc = self_healing_engine.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    if inc.status != IncidentStatus.APPROVAL_PENDING:
        raise HTTPException(status_code=400, detail=f"Incident is not in APPROVAL_PENDING state (current: {inc.status.value}).")

    if inc.approval_id:
        approvals_manager.approve(inc.approval_id, approved_by="operator")

    inc.requires_approval = False
    return self_healing_engine.execute_remediation(incident_id, force=True)


@router.get("/playbooks", response_model=List[RemediationPlaybook])
def list_playbooks():
    """Lists all registered automated remediation playbooks."""
    return self_healing_engine.list_playbooks()


@router.get("/telemetry", response_model=SelfHealingTelemetry)
def get_telemetry():
    """Returns aggregated self-healing metrics, uptime SLA, and active watchdogs."""
    return self_healing_engine.get_telemetry()


@router.post("/watchdogs/tick", response_model=List[WatchdogCheckResult])
def run_watchdogs_tick():
    """Executes a live health inspection sweep across all 6 watchdogs."""
    return self_healing_engine.run_all_watchdogs()
