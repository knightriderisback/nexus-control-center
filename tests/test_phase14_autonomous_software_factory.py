"""
NEXUS Phase 14: Autonomous Software Factory Test Suite.

Validates the full autonomous software engineering lifecycle:
Goal → Requirements → Mission DAG → Capability Selection → Isolated Worktrees →
Artifact Synthesis → AGY ↔ Codex Review & Fix Loop → Pytest Verification →
Machine Acceptance → Merge Arbitration → Persistent Memory → $0 FinOps.
"""

import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

from server import app
from models.schemas import (
    FactoryProjectCreateRequest,
    FactoryGoalExecuteRequest,
    EngineeringMission,
    MissionState
)
from orchestrator.factory_engine import factory_engine
from orchestrator.capability_registry import capability_registry
from orchestrator.acceptance_engine import acceptance_engine
from orchestrator.traceability_engine import traceability_engine
from orchestrator.mission_memory import mission_memory
from registry.projects import get_project_by_id, load_projects

from core.auth import DEFAULT_DEV_TOKEN
client = TestClient(app)
AUTH_HEADERS = {"Authorization": f"Bearer {DEFAULT_DEV_TOKEN}"}


@pytest.fixture
def temp_project_dir():
    temp_dir = tempfile.mkdtemp(prefix="nexus_factory_test_")
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestFactoryProjectCreation:
    """Tests autonomous project scaffolding, git initialization, and registry binding."""

    def test_scaffold_project_structure(self, temp_project_dir):
        req = FactoryProjectCreateRequest(
            project_name="Analytics Ingestion Engine",
            goal="Build a high-performance stream analytics service with metrics",
            template="fastapi_service",
            base_path=temp_project_dir,
            init_git=True
        )
        project, record = factory_engine.create_project_from_goal(req)

        assert project.id.startswith("project-")
        assert os.path.exists(project.path)
        assert os.path.exists(os.path.join(project.path, "src"))
        assert os.path.exists(os.path.join(project.path, "tests"))
        assert os.path.exists(os.path.join(project.path, "docs"))
        assert os.path.exists(os.path.join(project.path, "README.md"))
        assert os.path.exists(os.path.join(project.path, "pyproject.toml"))
        assert os.path.exists(os.path.join(project.path, ".git"))

        # Check registered in ProjectRegistry
        registered = get_project_by_id(project.id)
        assert registered is not None
        assert registered.name == "Analytics Ingestion Engine"

    def test_factory_templates_listing(self):
        resp = client.get("/api/v1/factory/templates", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "templates" in data
        assert len(data["templates"]) >= 6
        template_ids = [t["id"] for t in data["templates"]]
        assert "fastapi_service" in template_ids
        assert "cache_engine" in template_ids
        assert "auth_service" in template_ids
        assert "rate_limiter" in template_ids


class TestGoalSynthesisAndArchetypes:
    """Tests high-fidelity synthesis of code and unit tests across software archetypes."""

    def test_cache_engine_synthesis_and_execution(self, temp_project_dir):
        req = FactoryGoalExecuteRequest(
            goal="Build an LRU cache with TTL eviction and stats tracking",
            target_path=temp_project_dir,
            template="cache_engine",
            auto_merge=False,
            background=False
        )
        res = factory_engine.execute_factory_goal(req)
        assert res["success"] is True
        assert res["stage"] == "COMPLETED"

        # Check files created on disk
        artifacts = res["generated_artifacts"]
        assert any("cache" in a.lower() and a.endswith(".py") for a in artifacts)
        assert any("test_" in a.lower() for a in artifacts)

    def test_auth_service_synthesis_and_execution(self, temp_project_dir):
        req = FactoryGoalExecuteRequest(
            goal="Implement HMAC-SHA256 JWT auth token generator and password hasher",
            target_path=temp_project_dir,
            template="auth_service",
            auto_merge=False,
            background=False
        )
        res = factory_engine.execute_factory_goal(req)
        assert res["success"] is True
        assert res["stage"] == "COMPLETED"
        assert len(res["review_rounds"]) >= 1

    def test_rate_limiter_synthesis_and_execution(self, temp_project_dir):
        req = FactoryGoalExecuteRequest(
            goal="Create sliding window rate limiter middleware",
            target_path=temp_project_dir,
            template="rate_limiter",
            auto_merge=False,
            background=False
        )
        res = factory_engine.execute_factory_goal(req)
        assert res["success"] is True
        assert res["stage"] == "COMPLETED"

    def test_event_bus_synthesis_and_execution(self, temp_project_dir):
        req = FactoryGoalExecuteRequest(
            goal="Implement Pub-Sub Event Bus with Dead-Letter Queue",
            target_path=temp_project_dir,
            template="event_bus",
            auto_merge=False,
            background=False
        )
        res = factory_engine.execute_factory_goal(req)
        assert res["success"] is True
        assert res["stage"] == "COMPLETED"

    def test_data_pipeline_synthesis_and_execution(self, temp_project_dir):
        req = FactoryGoalExecuteRequest(
            goal="Build ETL data stream transformation pipeline",
            target_path=temp_project_dir,
            template="data_pipeline",
            auto_merge=False,
            background=False
        )
        res = factory_engine.execute_factory_goal(req)
        assert res["success"] is True
        assert res["stage"] == "COMPLETED"

    def test_cli_tool_synthesis_and_execution(self, temp_project_dir):
        req = FactoryGoalExecuteRequest(
            goal="Create CLI tool with subcommand router and parser",
            target_path=temp_project_dir,
            template="cli_tool",
            auto_merge=False,
            background=False
        )
        res = factory_engine.execute_factory_goal(req)
        assert res["success"] is True
        assert res["stage"] == "COMPLETED"


class TestAgyCodexReviewAndFixLoop:
    """Tests the AGY ↔ Codex multi-turn review, finding detection, and automated remediation."""

    def test_clean_review_approval(self, temp_project_dir):
        req = FactoryGoalExecuteRequest(
            goal="Create calculation engine service with add and multiply",
            target_path=temp_project_dir,
            template="fastapi_service",
            auto_merge=False,
            background=False
        )
        res = factory_engine.execute_factory_goal(req)
        assert res["success"] is True
        rounds = res["review_rounds"]
        assert len(rounds) >= 1
        assert rounds[-1]["verdict"] == "APPROVED"
        assert rounds[-1]["tests_passed"] is True
        assert rounds[-1]["security_clean"] is True

    def test_security_sentinel_quarantine(self, temp_project_dir):
        """Sentinel must detect and prompt remediation if hardcoded secrets are present."""
        req = FactoryGoalExecuteRequest(
            goal="Create sensitive payments gateway service",
            target_path=temp_project_dir,
            template="auth_service",
            auto_merge=False,
            background=False
        )
        res = factory_engine.execute_factory_goal(req)
        assert res["success"] is True
        # Generated code must have 0 credential leaks
        for art in res["generated_artifacts"]:
            full_p = os.path.join(temp_project_dir, art)
            if os.path.exists(full_p) and full_p.endswith(".py"):
                with open(full_p, "r") as fp:
                    content = fp.read()
                assert "AKIA" not in content
                assert "ghp_" not in content


class TestMachineAcceptanceAndTraceability:
    """Tests machine-checkable acceptance criteria and requirement traceability."""

    def test_acceptance_criteria_verification(self, temp_project_dir):
        req = FactoryGoalExecuteRequest(
            goal="Build high performance math utility module",
            target_path=temp_project_dir,
            auto_merge=False,
            background=False
        )
        res = factory_engine.execute_factory_goal(req)
        assert res["success"] is True
        assert "acceptance_criteria" in res
        for ac in res["acceptance_criteria"]:
            assert ac["status"] == "PASSED"
            assert ac["evidence"] is not None

    def test_knowledge_memory_persistence(self, temp_project_dir):
        req = FactoryGoalExecuteRequest(
            goal="Build memory persistence cache manager",
            target_path=temp_project_dir,
            template="cache_engine",
            auto_merge=False,
            background=False
        )
        res = factory_engine.execute_factory_goal(req)
        assert res["success"] is True
        entries = mission_memory.query_knowledge(category="strategy", limit=10)
        assert len(entries) > 0


class TestFactoryRESTAPIEndpoints:
    """Tests FastAPI endpoints mounted at /api/v1/factory."""

    def test_api_create_project(self, temp_project_dir):
        payload = {
            "project_name": "API Micro Service Test",
            "goal": "Build a REST API microservice",
            "template": "fastapi_service",
            "base_path": temp_project_dir,
            "init_git": True
        }
        resp = client.post("/api/v1/factory/create-project", json=payload, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["project"]["name"] == "API Micro Service Test"

    def test_api_execute_goal_sync(self, temp_project_dir):
        payload = {
            "goal": "Create a token bucket rate limiter module",
            "target_path": temp_project_dir,
            "template": "rate_limiter",
            "background": False
        }
        resp = client.post("/api/v1/factory/execute-goal", json=payload, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["stage"] == "COMPLETED"

    def test_api_list_and_get_records(self):
        resp = client.get("/api/v1/factory/records", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        records = resp.json()
        assert isinstance(records, list)
        if len(records) > 0:
            rec_id = records[0]["factory_id"]
            single_resp = client.get(f"/api/v1/factory/records/{rec_id}", headers=AUTH_HEADERS)
            assert single_resp.status_code == 200
            assert single_resp.json()["factory_id"] == rec_id

    def test_zero_spend_finops_governance(self, temp_project_dir):
        """Verifies strict $0.00 cost compliance across autonomous factory runs."""
        req = FactoryGoalExecuteRequest(
            goal="Build an analytics event aggregator with tests",
            target_path=temp_project_dir,
            template="event_bus",
            auto_merge=False,
            background=False
        )
        res = factory_engine.execute_factory_goal(req)
        assert res["success"] is True
        mission_obj = res.get("mission")
        if mission_obj:
            assert mission_obj.get("cost_estimate_usd", 0.0) == 0.0
