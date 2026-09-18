# NEXUS Phase 12: Autonomous Engineering Mission Control & Closed-Loop Remediation Engine

## 1. Executive Summary & Verification Matrix

### Verification Status Distinction
| Capability / Verification Domain | Status | Evidence / Mode |
| :--- | :--- | :--- |
| **Goal Decomposition & DAG Topology** | **LOCAL VERIFIED** | Deterministic blueprint compilation into Kahn topological levels |
| **Ephemeral Worktree Sandboxing** | **LOCAL VERIFIED** | Isolated `git worktree` execution; 0 orphaned worktrees verified |
| **Closed-Loop Self-Healing Remediation** | **LOCAL VERIFIED** | QA failure triggers automated patch synthesis & verification within bounded rounds |
| **Security Sentinel AST & Leak Audit** | **LOCAL VERIFIED** | High-risk pattern scanning flags API keys/AKIA/tokens before merge |
| **Swarm Branch Merge Arbitration** | **LOCAL VERIFIED** | Three-way merge analysis and clean trunk reconciliation |
| **Phase 11 Governed Delivery Bridge** | **LOCAL VERIFIED** | Automatic candidate branch publication and PR creation via Phase 11 bridge |
| **FinOps Zero-Spend Enforcement** | **LOCAL VERIFIED** | $0.00 cloud incurrence strictly maintained; billing unlinked |
| **Live Remote GitHub Execution** | **NOT VERIFIED** | **Intentionally NOT executed**. Air-gapped zero-cost preservation ($0.00 spend). Mock/dry-run mode active. |

### Objective & Architecture Rationale
NEXUS Phase 12 closes the loop between natural language user intent and governed production delivery. Prior phases established multi-agent execution, worktree sandboxing, merge arbitration, and GitHub PR delivery. Phase 12 introduces the **Mission Engine**—a supervisor engine that:
1. Accepts a high-level natural language directive (e.g. *"Build an LRU cache module with unit tests and deliver to GitHub"*).
2. Decomposes the directive into an `EngineeringBlueprint` and a dependency DAG of `MissionSubtasks`.
3. Validates DAG acyclicity and groups tasks into concurrent topological levels.
4. Mounts ephemeral Git worktrees for parallel agent execution (`RESEARCH-01`, `DEVELOPER-02`, `QA-VERIFIER`, `SENTINEL-SEC`, `DOC-CHRONICLER`).
5. Executes closed-loop automated QA testing: failures trigger iterative self-healing remediation patches bounded by `max_remediation_rounds`.
6. Enforces policy gating on sensitive target paths (e.g., `rules.json`, `auth`, `iam`).
7. Executes pre-merge test verification and atomic branch arbitration into the target branch.
8. Automatically triggers the Phase 11 GitHub delivery engine for candidate publication and governed PR creation.
9. Synthesizes a telemetry-rich Markdown release changelog with $0.00 FinOps ledger verification.

---

## 2. System Architecture & Lifecycle DAG

```
                        ┌─────────────────────────────────────────┐
                        │       NATURAL LANGUAGE DIRECTIVE        │
                        │       "Build feature X with tests"      │
                        └────────────────────┬────────────────────┘
                                             │
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │      GOAL DECOMPOSITION ENGINE          │
                        │    • Synthesizes EngineeringBlueprint   │
                        │    • Partitions into MissionSubtasks    │
                        │    • Kahn DAG Topological Sorting       │
                        └────────────────────┬────────────────────┘
                                             │
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │       POLICY & SENSITIVE PATH GATE      │
                        │   Inspects target paths & directives    │
                        └────────────┬───────────────┬────────────┘
                                     │               │
                            [Normal Directive]  [Sensitive Path: auth/rules]
                                     │               │
                                     │               ▼
                                     │      AWAITING_APPROVAL
                                     │      (Human signoff required)
                                     │               │
                                     ▼               ▼
                        ┌─────────────────────────────────────────┐
                        │       EPHEMERAL WORKTREE SANDBOX        │
                        │       data/worktrees/mission-<id>       │
                        │       Branch: nexus/mission-<id>        │
                        └────────────────────┬────────────────────┘
                                             │
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │   CONCURRENT TOPOLOGICAL LEVEL RUNNER   │
                        │   Level 0: RESEARCH-01 (Architecture)   │
                        │   Level 1: DEVELOPER-02 (Synthesis)     │
                        │   Level 2: QA-VERIFIER & SENTINEL-SEC   │
                        │   Level 3: DOC-CHRONICLER (ADR & Notes) │
                        └────────────────────┬────────────────────┘
                                             │
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │     CLOSED-LOOP REMEDIATION ENGINE      │
                        │     QA fails? ──▶ Patch ──▶ Retest      │
                        │     Self-heals within max rounds        │
                        └────────────────────┬────────────────────┘
                                             │
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │      SWARM MERGE ARBITRATION            │
                        │      Three-way diff & pre-merge tests   │
                        └────────────────────┬────────────────────┘
                                             │
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │   PHASE 11 GITHUB DELIVERY BRIDGE       │
                        │   • Publishes candidate branch          │
                        │   • Synthesizes Governed PR             │
                        └────────────────────┬────────────────────┘
                                             │
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │    EPHEMERAL WORKTREE PRUNING           │
                        │    0 orphaned worktrees; FinOps: $0.00  │
                        └─────────────────────────────────────────┘
```

---

## 3. Core Engine Components

### 3.1 Goal Decomposition & DAG Topological Sorter
- **Blueprint Extraction**: Generates `spec_id`, architecture strategy, target files, proposed modifications, test strategies, and verification assertions.
- **Topological Sorting**: Evaluates dependencies across all subtasks using Kahn's algorithm. Detects cycles deterministically, raising `Cycle detected in Mission Subtask DAG` to block infinite agent deadlock.
- **Concurrent Level Execution**: Independent subtasks within the same level run concurrently via `ThreadPoolExecutor` while respecting the dependency boundaries of subsequent levels.

### 3.2 Ephemeral Git Worktree Sandboxing
- Prior to executing changes, the engine provisions an isolated ephemeral worktree at `data/worktrees/<mission_id>` on branch `nexus/<mission_id>` branched off `target_branch`.
- Primary working trees remain untouched during agent synthesis.
- Upon completion, failure, cancellation, or rollback, the engine systematically executes `SafeCommandExecutor.execute(["git", "worktree", "remove", "--force", worktree_path])` and removes branch references, guaranteeing pristine repository state.

### 3.3 Closed-Loop Self-Healing Remediation
- When `agent-qa` encounters test failures or assertion mismatches, it transitions the mission into `MissionState.REMEDIATING`.
- Captured failure context (`pytest` stderr, stdout, traceback) is supplied to `_apply_remediation_patch`.
- The developer agent applies targeted corrections and immediately re-evaluates the test suite.
- If resolved, the mission transitions back to `MissionState.EXECUTING` and marks the subtask as healed.
- If failures persist past `max_remediation_rounds`, the mission safely halts with `MissionState.FAILED` without corrupting downstream branches.

### 3.4 Security Sentinel & AST Policy Gate
- Modifying files containing hardcoded credentials (AWS AKIA keys, Bearer tokens, API keys) or unsafe execution patterns (`eval(user_input)`, unsanitized `os.system`) triggers immediate quarantine.
- Operations targeting security-critical configuration files (`backend/core/rules.json`, `auth`, `iam`, `service_account`) automatically demand human operator signoff (`MissionState.AWAITING_APPROVAL`).

### 3.5 Swarm Merge Arbitration & GitHub Delivery Bridge
- When `auto_merge=True`, the engine evaluates the candidate branch using `merge_arbitrator.evaluate_merge`.
- Ephemeral dry-run merges run pre-merge semantic tests in a dedicated sandbox before touching the target branch.
- When `auto_deliver_github=True`, the engine forwards candidate branches to `github_delivery_engine.initiate_delivery(...)` and `create_pull_request(...)`, registering `github_delivery_id` directly in the mission record.

---

## 4. REST API & ECO CLI Specifications

### REST API Endpoints (`/api/v1/missions`)
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/missions/plan` | Decomposes directive, returns `EngineeringMission` with blueprint and execution topology |
| `POST` | `/api/v1/missions/run` | Plans and immediately launches asynchronous mission execution |
| `GET` | `/api/v1/missions` | Lists all engineering missions with telemetry and statuses |
| `GET` | `/api/v1/missions/{id}` | Retrieves detailed mission record, subtasks, and logs |
| `POST` | `/api/v1/missions/{id}/execute` | Triggers execution of a previously planned mission |
| `POST` | `/api/v1/missions/{id}/cancel` | Aborts running mission and dismantles ephemeral worktree |
| `POST` | `/api/v1/missions/{id}/rollback` | Safely rolls back mission commits on target branch |
| `GET` | `/api/v1/missions/{id}/changelog` | Returns synthesized Markdown release notes and verification audit |

### ECO CLI Commands (`eco mission`)
```bash
# Plan a new mission directive
eco mission plan "Build a high performance math calculator"

# Execute a mission
eco mission run mission-4fcf5b9f

# Check mission status and subtask progress
eco mission status mission-4fcf5b9f

# View synthesized release changelog
eco mission changelog mission-4fcf5b9f

# Cancel an active mission
eco mission cancel mission-4fcf5b9f
```

---

## 5. Verification & Test Evidence

### Targeted Unit & Integration Tests (`tests/test_phase12_mission_control.py`)
```
tests/test_phase12_mission_control.py::test_goal_decomposition_into_dag PASSED
tests/test_phase12_mission_control.py::test_dag_cycle_detection_and_validation PASSED
tests/test_phase12_mission_control.py::test_mission_state_machine_integrity PASSED
tests/test_phase12_mission_control.py::test_sensitive_path_policy_gating PASSED
tests/test_phase12_mission_control.py::test_autonomous_mission_execution_clean_merge PASSED
tests/test_phase12_mission_control.py::test_ephemeral_worktree_zero_pollution PASSED
tests/test_phase12_mission_control.py::test_closed_loop_remediation_heals_failure PASSED
tests/test_phase12_mission_control.py::test_remediation_exhaustion_on_persistent_failure PASSED
tests/test_phase12_mission_control.py::test_security_sentinel_secret_detection PASSED
tests/test_phase12_mission_control.py::test_mission_cancellation PASSED
tests/test_phase12_mission_control.py::test_mission_rollback PASSED
tests/test_phase12_mission_control.py::test_mission_persistence_and_reload PASSED
tests/test_phase12_mission_control.py::test_mission_to_github_delivery_bridge PASSED
tests/test_phase12_mission_control.py::test_missions_rest_api_endpoints PASSED
tests/test_phase12_mission_control.py::test_eco_cli_mission_commands PASSED

================== 15 passed in 86.35s ==================
```

### Production CI Gatekeeper Audit (`scripts/ci_verify.py`)
Gate 13 (`verify_phase12_mission_control`) audits:
1. Complete import of Phase 12 models, engines, and routers.
2. Kahn topological sorting accuracy and cycle detection triggers.
3. Policy enforcement for sensitive target paths (`rules.json`, `auth`).
4. Strict state machine transition validation and illegal step rejection.
5. Zero-cost FinOps preservation ($0.00 spend, billing unlinked).
6. Ephemeral worktree lifecycle hygiene (0 orphaned worktrees).
7. Execution of all 15 Phase 12 targeted verification tests.
