"""
NEXUS Phase 16: Production Deployment Engine Test Suite.
Tests multi-target deployment pipelines, canary rollouts, health probes,
instant rollbacks, human approval gates, DORA metrics, universal tool integration,
and strict FinOps zero-cost governance.
"""

import os
import pytest
from fastapi.testclient import TestClient

from server import app
from orchestrator.deployment_engine import deployment_engine, ProductionDeploymentEngine
from orchestrator.universal_tool_engine import universal_tool_engine
from models.schemas import (
    DeploymentTargetType,
    DeploymentEnvironment,
    DeploymentStrategy,
    DeploymentOverallStatus,
    DeploymentRequest,
    RollbackRequest,
    CanaryPromoteRequest,
    UniversalToolInvocationRequest,
)
from core.approvals import approvals_manager
from core.cost_guard import cost_guard


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. Target & Environment Registry Tests
# ==============================================================================

class TestDeploymentRegistryAndTargets:
    """Verifies target discovery and environment matrix topology."""

    def test_list_supported_targets(self):
        targets = deployment_engine.list_targets()
        assert len(targets) >= 5
        target_types = [t["target_type"] for t in targets]
        assert "LOCAL_PROCESS" in target_types
        assert "STATIC_BUNDLE" in target_types
        assert "VERCEL_EDGE" in target_types
        assert "GCP_CLOUD_RUN" in target_types
        assert "TERMUX_NODE" in target_types

    def test_list_environments(self):
        envs = deployment_engine.list_environments()
        assert len(envs) >= 4
        env_names = [e.environment_name for e in envs]
        assert "LOCAL" in env_names
        assert "PREVIEW" in env_names
        assert "STAGING" in env_names
        assert "PRODUCTION" in env_names


# ==============================================================================
# 2. Multi-Target Pipeline Execution Tests
# ==============================================================================

class TestMultiTargetPipelineExecution:
    """Tests full lifecycle deployment pipelines across multiple targets."""

    def test_local_process_deployment_lifecycle(self):
        req = DeploymentRequest(
            project_id="control-center",
            service_name="nexus-core",
            version="v1.16.0",
            environment=DeploymentEnvironment.LOCAL,
            target_type=DeploymentTargetType.LOCAL_PROCESS,
            strategy=DeploymentStrategy.DIRECT_REPLACE,
            created_by="test-suite"
        )
        record = deployment_engine.deploy(req)
        assert record.status == DeploymentOverallStatus.LIVE
        assert record.deployed_url == "http://localhost:8000"
        assert record.health_status == "HEALTHY"
        assert len(record.stages) == 7
        assert all(s.status.value in ["SUCCESS", "SKIPPED"] for s in record.stages)

    def test_static_bundle_deployment(self):
        req = DeploymentRequest(
            project_id="control-center",
            service_name="nexus-hud",
            version="v1.16.1",
            environment=DeploymentEnvironment.LOCAL,
            target_type=DeploymentTargetType.STATIC_BUNDLE,
            strategy=DeploymentStrategy.DIRECT_REPLACE,
            created_by="test-suite"
        )
        record = deployment_engine.deploy(req)
        assert record.status == DeploymentOverallStatus.LIVE
        assert "dist" in record.deployed_url
        assert record.health_status == "HEALTHY"

    def test_vercel_edge_preview_deployment(self):
        req = DeploymentRequest(
            project_id="portfolio",
            service_name="portfolio-app",
            version="v2.1.0",
            environment=DeploymentEnvironment.PREVIEW,
            target_type=DeploymentTargetType.VERCEL_EDGE,
            strategy=DeploymentStrategy.BLUE_GREEN,
            created_by="test-suite"
        )
        record = deployment_engine.deploy(req)
        assert record.status == DeploymentOverallStatus.LIVE
        assert "vercel.app" in record.deployed_url
        assert record.duration_seconds >= 0.0

    def test_termux_mobile_node_deployment(self):
        req = DeploymentRequest(
            project_id="termux-node",
            service_name="mobile-receiver",
            version="v1.0.5",
            environment=DeploymentEnvironment.LOCAL,
            target_type=DeploymentTargetType.TERMUX_NODE,
            strategy=DeploymentStrategy.DIRECT_REPLACE,
            created_by="test-suite"
        )
        record = deployment_engine.deploy(req)
        assert record.status == DeploymentOverallStatus.LIVE
        assert "termux" in record.deployed_url


# ==============================================================================
# 3. Canary Rollout & Traffic Promotion Tests
# ==============================================================================

class TestCanaryRolloutAndPromotion:
    """Tests canary traffic splitting and incremental traffic promotion."""

    def test_canary_deployment_and_traffic_promotion(self):
        req = DeploymentRequest(
            project_id="control-center",
            service_name="nexus-api",
            version="v1.17.0",
            environment=DeploymentEnvironment.STAGING,
            target_type=DeploymentTargetType.LOCAL_PROCESS,
            strategy=DeploymentStrategy.CANARY,
            canary_percentage=25,
            created_by="test-suite"
        )
        record = deployment_engine.deploy(req)
        assert record.status == DeploymentOverallStatus.LIVE
        assert record.canary_percentage == 25

        # Promote Canary to 75%
        promote_req = CanaryPromoteRequest(
            deployment_id=record.deployment_id,
            target_percentage=75
        )
        updated = deployment_engine.promote_canary(promote_req)
        assert updated.canary_percentage == 75

        # Promote Canary to 100%
        promote_req_final = CanaryPromoteRequest(
            deployment_id=record.deployment_id,
            target_percentage=100
        )
        final_rec = deployment_engine.promote_canary(promote_req_final)
        assert final_rec.canary_percentage == 100


# ==============================================================================
# 4. Health Probing & Instant Rollback Tests
# ==============================================================================

class TestHealthProbingAndRollback:
    """Tests automated and manual atomic rollbacks."""

    def test_manual_instant_rollback(self):
        # Deploy initial stable release
        req1 = DeploymentRequest(
            project_id="sample-app",
            service_name="sample-svc",
            version="v1.0.0",
            environment=DeploymentEnvironment.LOCAL,
            target_type=DeploymentTargetType.LOCAL_PROCESS,
            created_by="test-suite"
        )
        dep1 = deployment_engine.deploy(req1)
        assert dep1.status == DeploymentOverallStatus.LIVE

        # Deploy second release
        req2 = DeploymentRequest(
            project_id="sample-app",
            service_name="sample-svc",
            version="v1.1.0",
            environment=DeploymentEnvironment.LOCAL,
            target_type=DeploymentTargetType.LOCAL_PROCESS,
            created_by="test-suite"
        )
        dep2 = deployment_engine.deploy(req2)
        assert dep2.status == DeploymentOverallStatus.LIVE

        # Rollback deployment 2
        rb_req = RollbackRequest(
            deployment_id=dep2.deployment_id,
            reason="Canary metrics degradation"
        )
        rb_res = deployment_engine.rollback(rb_req)
        assert rb_res.status == DeploymentOverallStatus.ROLLED_BACK
        assert rb_res.rollback_target_id is not None


# ==============================================================================
# 5. Human Approval Governance Tests
# ==============================================================================

class TestHumanApprovalGovernance:
    """Tests human-in-the-loop approval gate interception for high-risk production deploys."""

    def test_production_deployment_approval_interception_and_resume(self):
        req = DeploymentRequest(
            project_id="control-center",
            service_name="nexus-core-prod",
            version="v2.0.0-prod",
            environment=DeploymentEnvironment.PRODUCTION,
            target_type=DeploymentTargetType.GCP_CLOUD_RUN,
            strategy=DeploymentStrategy.BLUE_GREEN,
            created_by="test-suite"
        )
        record = deployment_engine.deploy(req)
        
        # Must pause at APPROVAL_PENDING
        assert record.status == DeploymentOverallStatus.APPROVAL_PENDING
        assert record.requires_approval is True
        assert record.approval_id is not None

        # Verify in approvals manager
        appr = approvals_manager.get_approval(record.approval_id)
        assert appr is not None
        assert appr.status == "PENDING"

        # Approve and resume
        approvals_manager.approve(record.approval_id, approved_by="operator-admin")
        record.requires_approval = False
        resumed = deployment_engine._execute_pipeline(record)
        assert resumed.status == DeploymentOverallStatus.LIVE


# ==============================================================================
# 6. DORA Metrics Tests
# ==============================================================================

class TestDORAMetrics:
    """Tests calculation of DORA DevOps operational metrics."""

    def test_dora_telemetry_calculation(self):
        dora = deployment_engine.get_dora_metrics()
        assert dora.total_deployments >= 1
        assert dora.deployment_frequency_per_week >= 0.0
        assert dora.lead_time_for_changes_minutes >= 0.0
        assert 0.0 <= dora.change_failure_rate_percent <= 100.0
        assert dora.mean_time_to_recovery_minutes > 0.0


# ==============================================================================
# 7. Universal Tool Engine Deployment Integration Tests
# ==============================================================================

class TestUniversalToolDeploymentIntegration:
    """Tests tool dispatch of deployment capabilities via Phase 15 Universal Tool Engine."""

    def test_universal_tool_deploy_trigger(self):
        req = UniversalToolInvocationRequest(
            tool_id="deploy.trigger",
            parameters={
                "project_id": "control-center",
                "service_name": "nexus-tool-svc",
                "environment": "LOCAL",
                "target_type": "LOCAL_PROCESS"
            },
            caller_agent_id="test-agent"
        )
        result = universal_tool_engine.invoke_tool(req)
        assert result.status == "SUCCESS"
        assert result.output.get("deployment_id") is not None
        assert result.output.get("status") == "LIVE"

    def test_universal_tool_deploy_promote(self):
        # Create canary deployment first
        d_req = DeploymentRequest(
            project_id="control-center",
            service_name="nexus-tool-canary",
            environment=DeploymentEnvironment.LOCAL,
            strategy=DeploymentStrategy.CANARY,
            canary_percentage=30
        )
        dep = deployment_engine.deploy(d_req)

        req = UniversalToolInvocationRequest(
            tool_id="deploy.promote",
            parameters={
                "deployment_id": dep.deployment_id,
                "target_percentage": 100
            },
            caller_agent_id="test-agent"
        )
        result = universal_tool_engine.invoke_tool(req)
        assert result.status == "SUCCESS"
        assert result.output.get("canary_percentage") == 100


# ==============================================================================
# 8. REST API Endpoints Tests
# ==============================================================================

class TestDeploymentRESTAPI:
    """Tests all Phase 16 REST endpoints mounted on FastAPI."""

    def test_api_list_deployments(self, client):
        resp = client.get("/api/v1/deployments")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_api_list_environments(self, client):
        resp = client.get("/api/v1/deployments/environments")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 4

    def test_api_list_targets(self, client):
        resp = client.get("/api/v1/deployments/targets")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 5

    def test_api_get_dora_metrics(self, client):
        resp = client.get("/api/v1/deployments/dora")
        assert resp.status_code == 200
        data = resp.json()
        assert "deployment_frequency_per_week" in data
        assert "lead_time_for_changes_minutes" in data

    def test_api_trigger_and_get_deployment(self, client):
        payload = {
            "project_id": "control-center",
            "service_name": "nexus-api-test",
            "version": "v1.16.99",
            "environment": "LOCAL",
            "target_type": "LOCAL_PROCESS",
            "strategy": "DIRECT_REPLACE"
        }
        resp = client.post("/api/v1/deployments/deploy", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        dep_id = data["deployment_id"]
        assert data["status"] == "LIVE"

        # Fetch single deployment
        get_resp = client.get(f"/api/v1/deployments/{dep_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["deployment_id"] == dep_id

    def test_api_rollback(self, client):
        # Deploy a service
        payload = {
            "project_id": "api-rollback-test",
            "service_name": "rb-svc",
            "version": "v1.0.0",
            "environment": "LOCAL",
            "target_type": "LOCAL_PROCESS"
        }
        dep_resp = client.post("/api/v1/deployments/deploy", json=payload)
        dep_id = dep_resp.json()["deployment_id"]

        # Trigger rollback
        rb_resp = client.post(f"/api/v1/deployments/{dep_id}/rollback", json={"deployment_id": dep_id, "reason": "API test rollback"})
        assert rb_resp.status_code == 200
        assert rb_resp.json()["status"] == "ROLLED_BACK"

    def test_zero_spend_finops_governance(self, client):
        """Verifies $0.00 zero-cost profile across all deployment operations."""
        summary = cost_guard.get_cost_summary()
        assert summary.get("total_spent", 0.0) == 0.0
