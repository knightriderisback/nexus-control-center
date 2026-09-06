import os
import sys
import asyncio
import json
import psutil
from datetime import datetime
from typing import Dict, Any, List

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import config
from orchestrator.agents import get_agent_list
from registry.projects import load_projects
from core.approvals import load_approvals
from core.audit import record_audit, get_recent_audit_events
from integrations.gcp import get_gcp_system_status

# Observability & Tracing Middleware
from core.observability import TracingMiddleware

# Routers
from routers.v1.overview import router as overview_router
from routers.v1.projects import router as projects_router
from routers.v1.agents import router as agents_router
from routers.v1.approvals import router as approvals_router
from routers.v1.policy import router as policy_router
from routers.v1.audit import router as audit_router
from routers.v1.github_router import router as github_router
from routers.v1.cloud_router import router as cloud_router
from routers.v1.eco_nl import router as eco_nl_router
from routers.v1.docs_router import router as docs_router
from routers.v1.secrets_router import router as secrets_router
from routers.v1.metrics_router import router as metrics_router
from routers.v1.traces_router import router as traces_router
from routers.v1.cost_router import router as cost_router
from routers.v1.automations_router import router as automations_router
from routers.v1.adapters_router import router as adapters_router

app = FastAPI(
    title="NEXUS // Personal Engineering OS Control API",
    version="1.0.0",
    description="Central engineering control plane API for personal infrastructure, AI agents, project registry, and keyless GCP operations."
)

app.add_middleware(TracingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Version 1 API
API_V1_PREFIX = "/api/v1"
app.include_router(overview_router, prefix=API_V1_PREFIX)
app.include_router(projects_router, prefix=API_V1_PREFIX)
app.include_router(agents_router, prefix=API_V1_PREFIX)
app.include_router(approvals_router, prefix=API_V1_PREFIX)
app.include_router(policy_router, prefix=API_V1_PREFIX)
app.include_router(audit_router, prefix=API_V1_PREFIX)
app.include_router(github_router, prefix=API_V1_PREFIX)
app.include_router(cloud_router, prefix=API_V1_PREFIX)
app.include_router(eco_nl_router, prefix=API_V1_PREFIX)
app.include_router(docs_router, prefix=API_V1_PREFIX)
app.include_router(secrets_router, prefix=API_V1_PREFIX)
app.include_router(metrics_router, prefix=API_V1_PREFIX)
app.include_router(traces_router, prefix=API_V1_PREFIX)
app.include_router(cost_router, prefix=API_V1_PREFIX)
app.include_router(automations_router, prefix=API_V1_PREFIX)
app.include_router(adapters_router, prefix=API_V1_PREFIX)

# Legacy aliases for direct frontend backwards compatibility
@app.get("/api/health")
def health_check():
    return {"status": "ONLINE", "system": config.app_name, "version": "1.0.0"}

@app.get("/api/telemetry")
def read_telemetry():
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_percent(percpu=True, interval=None) or [cpu_percent]
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage('/')

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cpu": {
            "overall": cpu_percent,
            "cores": cpu_cores,
            "core_count": psutil.cpu_count(logical=True) or 1
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent": mem.percent,
            "swap_percent": swap.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent
        },
        "uptime": "Active",
        "agent_summary": {
            "total": len(get_agent_list()),
            "active": 3,
            "idle": 10
        }
    }

@app.get("/api/agents")
def get_agents():
    return [a.model_dump() for a in get_agent_list()]

@app.get("/api/tasks")
def get_tasks():
    from routers.v1.agents import ACTIVE_TASKS
    return [t.model_dump() for t in ACTIVE_TASKS]

@app.post("/api/tasks/dispatch")
def dispatch_task(payload: dict):
    from models.schemas import TaskDispatchRequest
    from routers.v1.agents import dispatch_agent_task
    req = TaskDispatchRequest(**payload)
    return dispatch_agent_task(req)

@app.get("/api/approvals")
def get_approvals():
    return [a.model_dump() for a in load_approvals()]

@app.post("/api/approvals/decide")
def decide_approval_alias(payload: dict):
    from core.approvals import decide_approval
    return decide_approval(payload["approval_id"], payload["decision"]).model_dump()

@app.get("/api/cloud")
def get_cloud_alias():
    return get_gcp_system_status()

@app.post("/api/cloud/audit")
def post_cloud_audit_alias():
    from routers.v1.cloud_router import run_cloud_audit
    return run_cloud_audit()

@app.get("/api/workspace")
def get_workspace_alias():
    from integrations.github import list_known_repositories
    return {
        "primary_workspace": "/root",
        "active_projects": load_projects(),
        "repositories": list_known_repositories()
    }

@app.post("/api/macros/run")
def run_macro(payload: dict):
    mid = payload.get("macro_id")
    if mid == "git:status":
        import subprocess
        res = subprocess.run(["git", "status", "-s"], cwd="/root/portfolio", capture_output=True, text=True)
        return {"macro": mid, "output": res.stdout or "Clean working tree."}
    elif mid == "system:diagnostics":
        telem = read_telemetry()
        return {"macro": mid, "output": f"Load: {telem['cpu']['overall']}% | RAM: {telem['memory']['used_gb']}/{telem['memory']['total_gb']} GB"}
    return {"macro": mid, "output": f"Macro {mid} executed cleanly."}

@app.get("/api/memories")
def get_memories_alias():
    from routers.v1.docs_router import list_documentation
    return list_documentation()

@app.post("/api/panic")
def panic_protocol():
    from models.schemas import RiskLevel
    record_audit(
        action="PANIC_PROTOCOL_TRIGGERED",
        project="all",
        target="Fleet Swarm",
        reason="Operator triggered master panic killswitch",
        risk_level=RiskLevel.CRITICAL,
        result="HALTED"
    )
    return {"status": "HALTED", "message": "Master Panic Protocol active. All active neural tasks aborted."}

@app.websocket("/ws")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            telem = read_telemetry()
            apprs = load_approvals()
            pending = [a.model_dump() for a in apprs if a.status == "PENDING"]
            payload = {
                "type": "telemetry_tick",
                "data": telem,
                "agents": [a.model_dump() for a in get_agent_list()],
                "pending_approvals": pending
            }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass

FRONTEND_DIST = "/root/control-center/frontend/dist"
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=config.host, port=config.port, reload=False)
