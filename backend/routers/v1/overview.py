from fastapi import APIRouter
from datetime import datetime
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

    # Telemetry
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_percent(percpu=True, interval=None) or [cpu_percent]
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    return {
        "status": "ONLINE",
        "system": config.app_name,
        "api_version": config.api_version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cloud_project": config.gcp_project_id,
        "fleet": {
            "total_agents": len(agents),
            "active": sum(1 for a in agents if a.status in ["active", "monitoring"]),
            "idle": sum(1 for a in agents if a.status == "idle")
        },
        "projects_count": len(projects),
        "pending_approvals": len(pending_apprs),
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
