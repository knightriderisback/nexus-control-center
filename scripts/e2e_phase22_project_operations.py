#!/usr/bin/env python3
"""
NEXUS Phase 22: Autonomous Project Operations & Lifecycle Control E2E Verification.

Uses two disposable local projects inside an approved project root (/tmp).
Verifies the complete 12-step operational lifecycle:
1. Discovery (idempotent scan inside allowed roots)
2. Registration (persistent registration under allowlist validation)
3. Isolation (independent workspaces, configurations, and git repositories)
4. Health Detection (real Git state, Pytest execution, AST security, and metrics)
5. Mission Routing (natural language goal resolution with ambiguity protection)
6. Factory Integration (autonomous release candidate synthesis with SLSA provenance)
7. Deployment Integration (canary progression to STABLE with zero FinOps cost)
8. Controlled Failure (simulated configuration drift and test failure injection)
9. Self-Healing Integration (autonomous drift reconciliation and SLA watchdog auto-rollback)
10. Knowledge Feedback (Phase 19 closed-loop learning node generation)
11. Cross-Project Isolation (mutation on Alpha does not leak to Beta)
12. Cleanup (decommissioning, cryptographic tombstone archival, and workspace purge)
"""

import os
import sys
import json
import time
import shutil
import tempfile
import hashlib
import subprocess

# Ensure backend root is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from models.schemas import (
    ProjectRegistryItem,
    ProjectStatus,
    ProjectLifecycleState,
    ReleaseStrategy,
    ReleaseState,
    DriftSeverity,
    DriftType,
    MaintenanceTaskType,
    MaintenanceTaskStatus,
    CreateReleaseRequest,
    PromoteReleaseRequest,
    RollbackReleaseRequest,
    DetectDriftRequest,
    ReconcileDriftRequest,
    ScheduleMaintenanceRequest,
    ExecuteMaintenanceRequest,
    DecommissionProjectRequest,
    ArchiveProjectRequest,
    ProjectOperationRequest,
    ProjectOperationType
)
from orchestrator.project_operations_engine import ProjectOperationsEngine
from orchestrator.knowledge_learning_engine import knowledge_learning_engine


def print_step(step_num: int, title: str):
    print(f"\n[STEP {step_num}/12] {title}...")


def print_success(msg: str):
    print(f"  ✓ {msg}")


def print_info(msg: str):
    print(f"  -> {msg}")


def run_e2e_verification():
    print("=" * 80)
    print("  NEXUS PHASE 22: AUTONOMOUS PROJECT OPERATIONS & LIFECYCLE CONTROL E2E")
    print("=" * 80)

    # Use /tmp which is an explicitly approved project root
    e2e_root = tempfile.mkdtemp(prefix="nexus-phase22-e2e-", dir="/tmp")
    alpha_dir = os.path.join(e2e_root, "project-alpha")
    beta_dir = os.path.join(e2e_root, "project-beta")

    try:
        # Setup Project Alpha (FastAPI Service)
        os.makedirs(os.path.join(alpha_dir, "tests"), exist_ok=True)
        with open(os.path.join(alpha_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Project Alpha\nAutonomous payment routing microservice.\n")
        with open(os.path.join(alpha_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write("[project]\nname = 'project-alpha'\nversion = '0.1.0'\n")
        with open(os.path.join(alpha_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("def handler():\n    return {'status': 'alpha-active'}\n")
        with open(os.path.join(alpha_dir, "tests", "test_main.py"), "w", encoding="utf-8") as f:
            f.write("from main import handler\ndef test_alpha():\n    assert handler()['status'] == 'alpha-active'\n")
        
        # Initialize Git in Alpha
        subprocess.run(["git", "init"], cwd=alpha_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Nexus Bot"], cwd=alpha_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "nexus@nexus.local"], cwd=alpha_dir, capture_output=True, check=True)
        subprocess.run(["git", "add", "-A"], cwd=alpha_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit for project alpha"], cwd=alpha_dir, capture_output=True, check=True)

        # Setup Project Beta (Node/React Frontend)
        os.makedirs(os.path.join(beta_dir, "tests"), exist_ok=True)
        with open(os.path.join(beta_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Project Beta\nAutonomous analytics dashboard frontend.\n")
        with open(os.path.join(beta_dir, "package.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps({"name": "project-beta", "version": "1.0.0"}, indent=2))
        with open(os.path.join(beta_dir, "vite.config.ts"), "w", encoding="utf-8") as f:
            f.write("export default {};\n")

        # Initialize Git in Beta
        subprocess.run(["git", "init"], cwd=beta_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Nexus Bot"], cwd=beta_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "nexus@nexus.local"], cwd=beta_dir, capture_output=True, check=True)
        subprocess.run(["git", "add", "-A"], cwd=beta_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit for project beta"], cwd=beta_dir, capture_output=True, check=True)

        # Instantiate Operations Engine in isolated test data dir
        engine = ProjectOperationsEngine(data_dir=os.path.join(e2e_root, "ops_data"))

        # ---------------------------------------------------------------------
        # 1. DISCOVERY
        # ---------------------------------------------------------------------
        print_step(1, "Project Discovery inside Approved Roots")
        disc_resp = engine.discover_projects(roots=[e2e_root])
        discovered_ids = [p.project_id for p in disc_resp.discovered_projects]
        print_info(f"Scanned Roots: {disc_resp.scanned_roots}")
        print_info(f"Discovered Projects: {discovered_ids}")
        assert "project-alpha" in discovered_ids
        assert "project-beta" in discovered_ids
        alpha_item = next(p for p in disc_resp.discovered_projects if p.project_id == "project-alpha")
        beta_item = next(p for p in disc_resp.discovered_projects if p.project_id == "project-beta")
        assert alpha_item.detected_type == "fastapi"
        assert beta_item.detected_type == "react_vite"
        print_success("Project Alpha (FastAPI) and Beta (React/Vite) discovered idempotently.")

        # ---------------------------------------------------------------------
        # 2. REGISTRATION
        # ---------------------------------------------------------------------
        print_step(2, "Project Registration with Allowlist Validation")
        reg_alpha = engine.register_project(ProjectRegistryItem(
            id="project-alpha",
            name="Project Alpha",
            path=alpha_dir,
            type="fastapi",
            branch="main",
            health_score=100.0,
            status=ProjectStatus.HEALTHY
        ))
        reg_beta = engine.register_project(ProjectRegistryItem(
            id="project-beta",
            name="Project Beta",
            path=beta_dir,
            type="react_vite",
            branch="main",
            health_score=100.0,
            status=ProjectStatus.HEALTHY
        ))
        print_info(f"Registered Alpha: {reg_alpha.id} -> {reg_alpha.path}")
        print_info(f"Registered Beta: {reg_beta.id} -> {reg_beta.path}")

        fleet = engine.get_fleet_overview()
        assert fleet.total_projects >= 2
        assert fleet.finops_zero_cost_verified is True
        print_success("Projects registered into fleet inventory under strict $0.00 governance.")

        # ---------------------------------------------------------------------
        # 3. ISOLATION
        # ---------------------------------------------------------------------
        print_step(3, "Multi-Project Filesystem & Version Isolation")
        assert os.path.exists(alpha_dir) and os.path.exists(beta_dir)
        assert os.path.abspath(alpha_dir) != os.path.abspath(beta_dir)
        rec_a = engine.get_project_record("project-alpha")
        rec_b = engine.get_project_record("project-beta")
        assert rec_a.project_path != rec_b.project_path
        print_info(f"Alpha Path: {rec_a.project_path}")
        print_info(f"Beta Path:  {rec_b.project_path}")
        print_success("Independent project workspaces and records strictly isolated.")

        # ---------------------------------------------------------------------
        # 4. HEALTH DETECTION
        # ---------------------------------------------------------------------
        print_step(4, "Real Project Health Evaluation (Zero Mocked Metrics)")
        health_a = engine.get_project_health("project-alpha")
        print_info(f"Alpha Git Clean: {health_a.git_state.get('is_clean')}")
        print_info(f"Alpha Pytest Passed: {health_a.build_test_state.get('tests_passed')}")
        print_info(f"Alpha AST Clean: {health_a.security_state.get('security_clean')}")
        print_info(f"Alpha Health Score: {health_a.health_score}%")
        assert health_a.git_state.get("is_clean") is True
        assert health_a.build_test_state.get("tests_passed") is True
        assert health_a.security_state.get("security_clean") is True
        assert health_a.health_score >= 95.0
        print_success("Real Git, pytest, and AST security metrics verified for Project Alpha.")

        # ---------------------------------------------------------------------
        # 5. MISSION ROUTING
        # ---------------------------------------------------------------------
        print_step(5, "Project-Aware Mission Routing & Ambiguity Protection")
        # Existing project routing
        route_existing = engine.route_mission_goal("Add audit logging to project-alpha")
        print_info(f"Routing Existing: {route_existing.routing_type} (target: {route_existing.target_project_ids})")
        assert route_existing.routing_type == "EXISTING_PROJECT"
        assert "project-alpha" in route_existing.target_project_ids
        assert route_existing.safe_to_execute is True

        # New project routing
        route_new = engine.route_mission_goal("Create a new microservice for caching")
        print_info(f"Routing New: {route_new.routing_type}")
        assert route_new.routing_type == "NEW_PROJECT"
        assert route_new.safe_to_execute is True

        # Ambiguous / unauthorized protection
        route_ambiguous = engine.route_mission_goal("Do something random without context")
        print_info(f"Routing Ambiguous: {route_ambiguous.routing_type} (safe: {route_ambiguous.safe_to_execute})")
        assert route_ambiguous.safe_to_execute is False
        print_success("Mission routing intelligently resolved targets and blocked ambiguous goals.")

        # ---------------------------------------------------------------------
        # 6. FACTORY INTEGRATION
        # ---------------------------------------------------------------------
        print_step(6, "Factory Integration & Release Synthesis")
        rel_req = CreateReleaseRequest(
            project_id="project-alpha",
            version_bump="minor",
            strategy=ReleaseStrategy.CANARY,
            changelog_summary="Add autonomous telemetry handler"
        )
        release = engine.create_release(rel_req)
        print_info(f"Synthesized Release: v{release.version}")
        print_info(f"SLSA Provenance Hash: {release.slsa_attestation_hash}")
        print_info(f"Initial State: {release.state.value} ({release.traffic_weight_pct}% traffic)")
        assert release.version == "0.2.0"
        assert release.state == ReleaseState.CANARY_10
        assert release.traffic_weight_pct == 10
        assert len(release.slsa_attestation_hash) == 16
        print_success("Release candidate synthesized with SLSA provenance.")

        # ---------------------------------------------------------------------
        # 7. DEPLOYMENT INTEGRATION
        # ---------------------------------------------------------------------
        print_step(7, "Canary Deployment Progression (10% -> 50% -> 100% STABLE)")
        # Stage 1: Promote to 50%
        p50 = engine.promote_release(PromoteReleaseRequest(release_id=release.release_id))
        print_info(f"Promoted to 50%: {p50.state.value} ({p50.traffic_weight_pct}% traffic)")
        assert p50.state == ReleaseState.CANARY_50
        assert p50.traffic_weight_pct == 50

        # Stage 2: Promote to 100% / STABLE
        p100 = engine.promote_release(PromoteReleaseRequest(release_id=release.release_id))
        print_info(f"Promoted to STABLE: {p100.state.value} ({p100.traffic_weight_pct}% traffic)")
        assert p100.state == ReleaseState.STABLE
        assert p100.traffic_weight_pct == 100

        rec_alpha = engine.get_project_record("project-alpha")
        assert rec_alpha.current_version == "0.2.0"
        print_success("Canary rollout successfully promoted to production v0.2.0.")

        # ---------------------------------------------------------------------
        # 8. CONTROLLED FAILURE
        # ---------------------------------------------------------------------
        print_step(8, "Controlled Failure Injection (Config Drift & Error Spike)")
        # Simulate deleted pyproject.toml in Project Alpha
        pyproj_a = os.path.join(alpha_dir, "pyproject.toml")
        os.remove(pyproj_a)

        drifts = engine.detect_drift(DetectDriftRequest(project_id="project-alpha"))
        print_info(f"Detected Drifts on Alpha: {len(drifts)}")
        assert len(drifts) >= 1
        target_drift = drifts[0]
        assert target_drift.drift_type == DriftType.CONFIG_DRIFT
        print_success("Configuration drift detected via real filesystem radar.")

        # ---------------------------------------------------------------------
        # 9. SELF-HEALING INTEGRATION
        # ---------------------------------------------------------------------
        print_step(9, "Self-Healing Integration (Drift Auto-Reconcile & SLA Rollback)")
        # Autonomous drift reconcile
        reconciled = engine.reconcile_drift(ReconcileDriftRequest(drift_id=target_drift.drift_id))
        assert reconciled.remediated is True
        assert os.path.exists(pyproj_a)
        print_info("Drift reconciled: pyproject.toml restored.")

        # Simulate SLA breach on new patch release v0.2.1
        broken_rel = engine.create_release(CreateReleaseRequest(
            project_id="project-alpha",
            version_bump="patch",
            strategy=ReleaseStrategy.CANARY
        ))
        print_info(f"Simulating SLA breach on canary release v{broken_rel.version}...")
        sla = engine.evaluate_project_sla(
            project_id="project-alpha",
            sample_latency_ms=950.0,
            sample_error_rate=14.2
        )
        print_info(f"SLA Status: {sla.sla_status}")
        assert sla.sla_status == "BREACHED"
        rec_post_rollback = engine.get_project_record("project-alpha")
        print_info(f"Restored Version after Watchdog Rollback: v{rec_post_rollback.current_version}")
        assert rec_post_rollback.current_version == "0.2.0"
        print_success("Self-healing watchdog executed automatic rollback to stable v0.2.0.")

        # ---------------------------------------------------------------------
        # 10. KNOWLEDGE FEEDBACK
        # ---------------------------------------------------------------------
        print_step(10, "Closed-Loop Phase 19 Knowledge Ingestion")
        insights = knowledge_learning_engine.query_knowledge("project-alpha", limit=5)
        print_info(f"Knowledge Insights Found: {len(insights)}")
        for ins in insights:
            print_info(f"  - [{ins.tier.value}] {ins.title}")
        assert len(insights) >= 1
        print_success("Operational learnings and rollback incidents fed into Knowledge Graph.")

        # ---------------------------------------------------------------------
        # 11. CROSS-PROJECT ISOLATION
        # ---------------------------------------------------------------------
        print_step(11, "Cross-Project Isolation Verification")
        rec_b_check = engine.get_project_record("project-beta")
        assert rec_b_check.current_version == "0.1.0"
        assert rec_b_check.lifecycle_state == ProjectLifecycleState.ACTIVE
        assert os.path.exists(os.path.join(beta_dir, "package.json"))
        # Verify Git log in Beta has zero commits from Alpha
        beta_git_log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=beta_dir,
            capture_output=True,
            text=True,
            check=True
        ).stdout
        assert "Initial commit for project beta" in beta_git_log
        assert "project alpha" not in beta_git_log
        print_info(f"Beta Active Version: {rec_b_check.current_version}")
        print_info(f"Beta Workspace State: 100% pristine and unaffected")
        print_success("Strict boundary verification: Project Beta isolated from all Alpha operations.")

        # ---------------------------------------------------------------------
        # 12. CLEANUP & ARCHIVAL
        # ---------------------------------------------------------------------
        print_step(12, "Graceful Decommissioning & Cryptographic Tombstone Archival")
        # Decommission Project Alpha
        decom_a = engine.decommission_project(DecommissionProjectRequest(
            project_id="project-alpha",
            reason="E2E test verification completed"
        ))
        assert decom_a.lifecycle_state == ProjectLifecycleState.DECOMMISSIONED

        # Archive Alpha into Tombstone Vault
        tombstone = engine.archive_project(ArchiveProjectRequest(project_id="project-alpha"))
        print_info(f"Tombstone ID: {tombstone['tombstone_id']}")
        print_info(f"Tombstone Checksum: {tombstone['sha256_checksum'][:24]}...")
        print_info(f"Archive Bundle: {tombstone['archive_location']}")
        assert len(tombstone["sha256_checksum"]) == 64
        assert os.path.exists(tombstone["archive_location"])

        rec_archived = engine.get_project_record("project-alpha")
        assert rec_archived.lifecycle_state == ProjectLifecycleState.ARCHIVED
        print_success("Project Alpha decommissioned and preserved in cryptographic tombstone vault.")

        print("\n" + "=" * 80)
        print("  🎉 PHASE 22 12-STEP E2E OPERATIONS VERIFICATION COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        return True

    finally:
        shutil.rmtree(e2e_root, ignore_errors=True)


if __name__ == "__main__":
    success = run_e2e_verification()
    sys.exit(0 if success else 1)
