"""
NEXUS Phase 21: Autonomous Software Factory REST API Router.

Mounted at /api/v1/factory.
Exposes endpoints for:
- /api/v1/factory/projects (GET & POST)
- /api/v1/factory/spec (POST)
- /api/v1/factory/build (POST)
- /api/v1/factory/test (POST)
- /api/v1/factory/review (POST)
- /api/v1/factory/deliver (POST)
- /api/v1/factory/status/{factory_id} (GET)
- /api/v1/factory/artifacts/{factory_id} (GET)
- /api/v1/factory/create-project (POST, backward-compat)
- /api/v1/factory/execute-goal (POST, backward-compat)
- /api/v1/factory/records (GET, backward-compat)
- /api/v1/factory/records/{factory_id} (GET, backward-compat)
- /api/v1/factory/templates (GET)
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, status

from models.schemas import (
    FactoryProjectCreateRequest,
    FactoryGoalExecuteRequest,
    FactoryMissionRecord,
    ProjectRegistryItem,
    FactorySpecRequest,
    FactorySpecResponse,
    FactoryBuildRequest,
    FactoryTestRequest,
    FactoryReviewRequest,
    FactoryDeliverRequest,
    FactoryStatusResponse,
    FactoryArtifactsResponse
)
from orchestrator.factory_engine import factory_engine
from orchestrator.mission_engine import mission_engine

router = APIRouter(prefix="/factory", tags=["Autonomous Software Factory"])


# =============================================================================
# 1. PHASE 21 GRANULAR FACTORY STAGE ENDPOINTS
# =============================================================================

@router.get("/projects", response_model=List[ProjectRegistryItem])
def list_factory_projects():
    """Lists all registered software projects managed by the autonomous factory."""
    return factory_engine.list_projects()


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(req: FactoryProjectCreateRequest) -> Dict[str, Any]:
    """Scaffolds a new software project directory and initializes Git."""
    try:
        p_item, record = factory_engine.create_project_from_goal(req)
        return {
            "success": True,
            "project": p_item.model_dump(),
            "factory_record": record.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/spec", response_model=FactorySpecResponse, status_code=status.HTTP_201_CREATED)
def synthesize_factory_spec(req: FactorySpecRequest):
    """Decomposes goal into requirements, architecture spec, and acceptance criteria."""
    try:
        return factory_engine.generate_spec(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/build", status_code=status.HTTP_202_ACCEPTED)
def build_factory_project(req: FactoryBuildRequest):
    """Synthesizes code and test harness in an isolated worktree sandbox."""
    try:
        return factory_engine.build_project(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/test")
def test_factory_project(req: FactoryTestRequest):
    """Executes dynamic pytest harness with bounded autonomous repair loop."""
    try:
        return factory_engine.run_tests_with_repair(req)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review")
def review_factory_project(req: FactoryReviewRequest):
    """Executes AGY <-> Codex peer review loop and AST Security Sentinel audit."""
    try:
        return factory_engine.run_security_and_review(req)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deliver")
def deliver_factory_project(req: FactoryDeliverRequest):
    """Executes governed merge, local deployment, health check, and closed-loop learning."""
    try:
        return factory_engine.deliver_and_deploy(req)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{factory_id}", response_model=FactoryStatusResponse)
def get_factory_status(factory_id: str):
    """Retrieves current stage, telemetry, and health score for a factory mission."""
    try:
        return factory_engine.get_factory_status(factory_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/{factory_id}", response_model=FactoryArtifactsResponse)
def get_factory_artifacts(factory_id: str):
    """Retrieves generated artifacts, SLSA Level 3 attestation, and provenance hash."""
    try:
        return factory_engine.get_factory_artifacts(factory_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 2. BACKWARD-COMPATIBLE FULL LIFECYCLE ENDPOINTS
# =============================================================================

@router.post("/create-project")
def create_factory_project_legacy(req: FactoryProjectCreateRequest) -> Dict[str, Any]:
    try:
        project, record = factory_engine.create_project_from_goal(req)
        return {
            "success": True,
            "project": project.model_dump(),
            "factory_record": record.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/execute-goal")
def execute_factory_goal(req: FactoryGoalExecuteRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    try:
        if req.background:
            background_tasks.add_task(factory_engine.execute_factory_goal, req)
            return {
                "success": True,
                "status": "ACCEPTED",
                "message": f"Autonomous Software Factory mission started in background for goal: '{req.goal}'"
            }
        else:
            return factory_engine.execute_factory_goal(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/records", response_model=List[FactoryMissionRecord])
def list_factory_records(limit: int = 50):
    return factory_engine.list_records(limit=limit)


@router.get("/records/{factory_id}", response_model=FactoryMissionRecord)
def get_factory_record(factory_id: str):
    rec = factory_engine.get_record(factory_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Factory record '{factory_id}' not found.")
    return rec


@router.get("/templates")
def list_factory_templates() -> Dict[str, Any]:
    return {
        "templates": [
            {
                "id": "fastapi_service",
                "name": "FastAPI Microservice",
                "description": "High-performance asynchronous REST API with Pydantic schemas, routing, and pytest suite.",
                "capabilities": ["backend", "api", "testing"]
            },
            {
                "id": "cache_engine",
                "name": "Thread-Safe Cache Engine",
                "description": "LRU/TTL in-memory cache engine with eviction policies, concurrency locks, and telemetry.",
                "capabilities": ["backend", "performance", "testing"]
            },
            {
                "id": "auth_service",
                "name": "Cryptographic Auth & JWT Manager",
                "description": "HMAC-SHA256 token manager, role-based access control, and password hashing security engine.",
                "capabilities": ["security", "api", "backend"]
            },
            {
                "id": "rate_limiter",
                "name": "Sliding-Window Rate Limiter",
                "description": "Distributed leaky bucket / sliding-window token limiter with atomic thread-safe counters.",
                "capabilities": ["backend", "networking", "testing"]
            },
            {
                "id": "data_pipeline",
                "name": "Local ETL & Transform Pipeline",
                "description": "Deterministic local data processing pipeline with stream batching and sanitization.",
                "capabilities": ["data", "etl", "backend"]
            },
            {
                "id": "cli_tool",
                "name": "Command-Line Tool Processor",
                "description": "Subcommand router, help system, and argument parser for terminal developer tools.",
                "capabilities": ["cli", "developer_tools"]
            }
        ]
    }
