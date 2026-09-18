from fastapi import APIRouter
from datetime import datetime, timezone
import psutil
from core.config import config
from orchestrator.agents import get_agent_list
from registry.projects import load_projects
from core.approvals import load_approvals
from core.audit import get_recent_audit_events

router = APIRouter(prefix="/overview", tags=["Overview & Telemetry"])

@router.get("")
def get_system_overview():
    agents = get_agent_list()
    projects = load_projects()
    approvals = load_approvals()
    pending_apprs = [a for a in approvals if a.status == "PENDING"]
    audit_events = get_recent_audit_events(limit=10)

    # GitHub Delivery Telemetry
    from orchestrator.github_delivery import github_delivery_engine
    from models.schemas import DeliveryState
    deliveries = github_delivery_engine.list_deliveries(limit=10)
    active_deliveries = [
        {
            "delivery_id": d.delivery_id,
            "branch": d.published_branch or d.source_branch,
            "pr_number": d.pr_number,
            "state": d.state.value if hasattr(d.state, "value") else str(d.state),
            "risk": d.risk_level.value if hasattr(d.risk_level, "value") else str(d.risk_level),
            "qa_state": "passed" if any(c.get("check") == "pytest-suite" and c.get("conclusion") == "clean" for c in d.checks_results) else "pending",
            "security_state": "clean" if any(c.get("check") == "ast-security-sentinel" and c.get("conclusion") == "clean" for c in d.checks_results) else "pending",
            "failure_reason": d.error
        }
        for d in deliveries
        if d.state not in [DeliveryState.COMPLETED, DeliveryState.CANCELLED]
    ]

    # FinOps Spend & Guardrail
    from core.cost_guard import cost_guard
    cost_summary = cost_guard.get_cost_summary()

    # AI Providers
    from orchestrator.providers import provider_router
    prov_list = provider_router.list_providers()

    # Worktrees & Merges
    from orchestrator.worktree_manager import worktree_manager
    from orchestrator.merge_arbitrator import merge_arbitrator
    wts = worktree_manager.list_worktrees()
    cand_merges = merge_arbitrator.list_candidates()

    # Missions
    from orchestrator.mission_engine import mission_engine
    missions = mission_engine.list_missions()

    # Telemetry
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_percent(percpu=True, interval=None) or [cpu_percent]
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # System Health Evaluation
    overall_health = "HEALTHY"
    if cost_summary.get("current_spend_usd", 0.0) > 0.0 or cost_summary.get("billing_linked", False):
        overall_health = "BLOCKED"
    elif any(a.risk_level.lower() in ["high", "critical"] for a in pending_apprs):
        overall_health = "WARNING"
    elif any(p.get("health", {}).get("circuit_state") == "OPEN" for p in prov_list):
        overall_health = "DEGRADED"

    return {
        "status": "ONLINE",
        "system_health": overall_health,
        "system": config.app_name,
        "api_version": config.api_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cloud_project": config.gcp_project_id,
        "fleet": {
            "total_agents": len(agents),
            "active": sum(1 for a in agents if a.status in ["active", "monitoring"]),
            "idle": sum(1 for a in agents if a.status == "idle")
        },
        "delivery_summary": {
            "total": len(deliveries),
            "active": len(active_deliveries),
            "items": active_deliveries
        },
        "projects_count": len(projects),
        "pending_approvals": len(pending_apprs),
        "finops": {
            "current_spend_usd": cost_summary.get("current_spend_usd", 0.0),
            "spend_ceiling_usd": cost_summary.get("hard_spend_limit_usd", 0.0),
            "billing_linked": cost_summary.get("billing_linked", False),
            "guardrail_active": cost_summary.get("zero_cost_guardrail_active", True)
        },
        "providers_summary": {
            "active_preference": provider_router.default_preference,
            "total": len(prov_list),
            "circuits_open": sum(1 for p in prov_list if p.get("health", {}).get("circuit_state") == "OPEN")
        },
        "worktrees_count": len(wts),
        "merges_pending": len([c for c in cand_merges if c.state.value in ["ANALYZED", "VERIFIED", "AWAITING_APPROVAL"]]),
        "missions_summary": {
            "total": len(missions),
            "active": len([m for m in missions if m.state.value in ["RUNNING", "EXECUTING", "REMEDIATING"]]),
            "failed": len([m for m in missions if m.state.value in ["FAILED", "RECOVERY"]])
        },
        "telemetry": {
            "cpu_load": cpu_percent,
            "cpu_cores": cpu_cores,
            "ram_used_gb": round(mem.used / (1024**3), 2),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_percent": mem.percent,
            "disk_percent": disk.percent
        },
        "recent_audits": [e.model_dump() for e in audit_events]
    }
