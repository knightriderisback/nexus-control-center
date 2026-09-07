# 🔍 PERSONAL ENGINEERING OS — PHASE 3
## Autonomous Engineering Core: Execution Capability Audit & Hardening Report

**Date**: 2026-09-07  
**Operating Project**: `personal-engineering-os-2026`  
**Audit Target**: Autonomous Engineering Core, AI Agent Fleet, and Local Execution Paths  
**Classification Standard**: REAL | PARTIAL | SIMULATED | NOT IMPLEMENTED  
**Auditor**: Antigravity AI (Ground-Truth Execution Capability Audit)

---

## Executive Summary

A rigorous, code-level execution audit was conducted across all **13 agents** in the Personal Engineering OS (`control-center`). The objective was to cut through declarative declarations and verify what executable code paths actually exist, what tools run real operating-system or git processes, and where operations are simulated or unhandled.

### Key Audit Findings:
1. **The Swarm Is Declarative**: The 13 agents defined in `backend/orchestrator/agents.py` are declarative Pydantic models (`AgentManifest`). Their declared `allowed_tools` (e.g. `ast_search`, `file_editor`, `cve_lookup`) are string tags without executable Python function bindings in the agent dispatch path.
2. **Dispatch Mechanics**: `POST /api/v1/agents/dispatch` creates an in-memory `TaskItem` with a static progress state (`progress: 25`) and logs. It does not invoke an autonomous LLM loop, agentic reasoning, or filesystem operations.
3. **Where Real Execution Actually Lives**:
   - **Host Observability (`agent-mon`)**: Fully **REAL**. Streams live host CPU, memory, and disk statistics via `psutil` over WebSocket `/ws` and tracks latency metrics in a memory ring buffer.
   - **Cost Safeguard (`agent-cost`)**: Fully **REAL**. Evaluates billing unlinked status and programmatically blocks paid API creation (`compute.googleapis.com`, `container.googleapis.com`) in `core/cost_guard.py`.
   - **Secret Leak Detection (`agent-security`)**: **PARTIAL**. The scheduled/manual automation routine `auto-secret-scan` in `core/automations.py` executes a **REAL** `grep` subprocess across repository trees and correctly identifies private key headers. However, `POST /projects/{id}/security` and `agent-security` dispatch return hardcoded mocks.
   - **Disaster Rollback (`agent-recovery`)**: **REAL**. `scripts/rollback.sh` is an executable, idempotent Bash script capable of git branch resets and orphan process cleanup.
   - **Repository Sweeps**: **REAL**. `core/automations.py` (`auto-repo-sweep`) and `integrations/github.py` run real `git status -s`, `git branch`, and `git log` subprocesses.
4. **Where Simulation Prevailed**:
   - `POST /projects/{id}/test` returns a hardcoded mock (`passed: 24, tests_total: 24`), despite 27 real pytest tests existing in `tests/`.
   - `POST /projects/{id}/security` returns hardcoded zeroes (`cves_found: 0, secrets_leaked: 0`).
   - `integrations/adapters/github_adapter.py` returns hardcoded CI runs (`run-101`).
   - AI provider adapters in `backend/orchestrator/base.py` fall back to `MockProviderAdapter` (returning static synthetic strings) since external API keys are intentionally prohibited under the zero-cost security policy.

---

## 1. Audit of All 13 Agents

Below is the complete ground-truth capability audit for all 13 agents. Capabilities are strictly evaluated against executable code paths.

---

### Agent 1: `agent-research` (RESEARCH-01 / SCOUT-CORE)
* **Name**: RESEARCH-01 (SCOUT-CORE)
* **Role**: Codebase Discovery & Deep Research
* **Allowed Tools in Manifest**: `["grep", "ast_search", "web_search", "doc_reader"]`
* **Autonomy Tier**: Autonomous
* **Approval Required**: NO (Risk: `LOW`)
* **Execution Path**: `POST /api/v1/agents/dispatch` -> records audit log -> appends static `TaskItem` (`progress: 25`) to `ACTIVE_TASKS`.
* **Capability Classifications**:
  - **Execute shell commands**: `NOT IMPLEMENTED`
  - **Inspect Git repositories**: `NOT IMPLEMENTED` (No git tool bound to dispatch)
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `NOT IMPLEMENTED`
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `LOW`
* **Current Limitation**: Manifest-only. No callable tool functions or background worker thread exist to perform web searches or AST searches.

---

### Agent 2: `agent-dev` (DEVELOPER-02 / ARCH-DEV)
* **Name**: DEVELOPER-02 (ARCH-DEV)
* **Role**: Autonomous Feature & Refactoring Synthesizer
* **Allowed Tools in Manifest**: `["file_editor", "code_patcher", "linter", "git_branch"]`
* **Autonomy Tier**: Guardrailed
* **Approval Required**: YES for mutations/branches (Risk: `MEDIUM`)
* **Execution Path**: `POST /api/v1/agents/dispatch` -> triggers policy check -> creates `TaskItem` (`progress: 25`).
* **Capability Classifications**:
  - **Execute shell commands**: `NOT IMPLEMENTED`
  - **Inspect Git repositories**: `NOT IMPLEMENTED`
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `NOT IMPLEMENTED`
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `MEDIUM`
* **Current Limitation**: Cannot inspect repositories, create git diffs, or edit files autonomously. No write-tools are wired to the agent dispatcher.

---

### Agent 3: `agent-security` (SENTINEL-SEC)
* **Name**: SENTINEL-SEC
* **Role**: Secret Leak Auditor & AST Vulnerability Scanner
* **Allowed Tools in Manifest**: `["regex_audit", "cve_lookup", "secret_detector", "iam_inspector"]`
* **Autonomy Tier**: Autonomous
* **Approval Required**: YES for quarantine/IAM changes; NO for read-only scans (Risk: `HIGH`)
* **Execution Path**: 
  - Automation Routine: `POST /api/v1/automations/run/auto-secret-scan` -> executes real `grep` subprocess.
  - Project Endpoint: `POST /api/v1/projects/{id}/security` -> returns static mock JSON.
  - Agent Dispatch: `POST /api/v1/agents/dispatch` -> returns static `TaskItem`.
* **Capability Classifications**:
  - **Execute shell commands**: `PARTIAL` (Subprocess grep executed via automation engine; not via agent dispatch)
  - **Inspect Git repositories**: `NOT IMPLEMENTED`
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `PARTIAL` (Real regex scan for private keys in automation; CVE scan and AST scan simulated)
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `SIMULATED` (Reads local config metadata; no live IAM calls)
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `HIGH`
* **Current Limitation**: Real execution is restricted to the scheduled/manual automation job `auto-secret-scan`. Project security endpoint and agent dispatch do not call the grep engine.

---

### Agent 4: `agent-qa` (QA-VERIFIER / VERIFY-QA)
* **Name**: QA-VERIFIER (VERIFY-QA)
* **Role**: Automated Unit, E2E & Smoke Test Runner
* **Allowed Tools in Manifest**: `["pytest_runner", "npm_test_runner", "curl_probe", "coverage_inspector"]`
* **Autonomy Tier**: Autonomous
* **Approval Required**: NO (Risk: `LOW`)
* **Execution Path**: `POST /api/v1/projects/{id}/test` -> returns hardcoded `{tests_total: 24, passed: 24}`. Agent dispatch returns static `TaskItem`.
* **Capability Classifications**:
  - **Execute shell commands**: `NOT IMPLEMENTED`
  - **Inspect Git repositories**: `NOT IMPLEMENTED`
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `SIMULATED` (Returns hardcoded mock results rather than running `pytest`)
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `NOT IMPLEMENTED`
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `LOW`
* **Current Limitation**: Even though 27 real pytest unit tests exist in `tests/`, the agent and API endpoint return hardcoded synthetic results (`24/24 in 1.42s`).

---

### Agent 5: `agent-docs` (DOC-CHRONICLER / CHRONICLER)
* **Name**: DOC-CHRONICLER (CHRONICLER)
* **Role**: Architecture Decision Record & API Documentation Writer
* **Allowed Tools in Manifest**: `["doc_writer", "openapi_generator", "markdown_formatter"]`
* **Autonomy Tier**: Autonomous
* **Approval Required**: NO (Risk: `LOW`)
* **Execution Path**: `GET /api/v1/docs` reads static ADRs. `auto-morning-brief` formats markdown in memory. Dispatch returns static `TaskItem`.
* **Capability Classifications**:
  - **Execute shell commands**: `NOT IMPLEMENTED`
  - **Inspect Git repositories**: `NOT IMPLEMENTED`
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `PARTIAL` (Formats morning brief markdown; cannot edit markdown files on disk)
  - **Interact with GCP**: `NOT IMPLEMENTED`
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `LOW`
* **Current Limitation**: No write capability to create or update ADRs or markdown files in `/docs`.

---

### Agent 6: `agent-devops` (DEVOPS-RUNNER / PIPELINE-OPS)
* **Name**: DEVOPS-RUNNER (PIPELINE-OPS)
* **Role**: Containerization & CI/CD Pipeline Orchestrator
* **Allowed Tools in Manifest**: `["dockerfile_gen", "github_actions_writer", "build_verifier"]`
* **Autonomy Tier**: Guardrailed
* **Approval Required**: YES for deployments/pipeline triggers (Risk: `HIGH`)
* **Execution Path**: `backend/integrations/adapters/github_adapter.py` returns hardcoded status dict. Dispatch returns static `TaskItem`.
* **Capability Classifications**:
  - **Execute shell commands**: `NOT IMPLEMENTED`
  - **Inspect Git repositories**: `NOT IMPLEMENTED`
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `NOT IMPLEMENTED`
  - **Interact with GitHub**: `SIMULATED` (Returns mock action run `run-101`)
* **Actual Risk Level**: `HIGH`
* **Current Limitation**: Cannot parse or validate GitHub Actions workflow YAML (`.github/workflows/production-pipeline.yml`). Mock CI runs.

---

### Agent 7: `agent-infra` (INFRA-ENGINEER / TERRA-FORM)
* **Name**: INFRA-ENGINEER (TERRA-FORM)
* **Role**: GCP Cloud Infrastructure & Workload Identity Daemon
* **Allowed Tools in Manifest**: `["gcloud_cli", "iam_manager", "service_account_tool"]`
* **Autonomy Tier**: Step-by-Step
* **Approval Required**: YES for all cloud modifications (Risk: `CRITICAL`)
* **Execution Path**: `backend/routers/v1/cloud_router.py` returns metadata constructed from `core/config.py`.
* **Capability Classifications**:
  - **Execute shell commands**: `NOT IMPLEMENTED`
  - **Inspect Git repositories**: `NOT IMPLEMENTED`
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `SIMULATED` (Returns pre-configured constants; does not invoke `gcloud` or GCP client libraries)
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `CRITICAL`
* **Current Limitation**: Read-only configuration reflection. Live infrastructure provisioning, IAM adjustments, and gcloud CLI execution are blocked/unwired.

---

### Agent 8: `agent-data` (DATA-CATALYST / SYNAPSE-DB)
* **Name**: DATA-CATALYST (SYNAPSE-DB)
* **Role**: Schema Migration & Data Store Observer
* **Allowed Tools in Manifest**: `["sqlite_inspector", "json_vault_query", "schema_validator"]`
* **Autonomy Tier**: Guardrailed
* **Approval Required**: YES for schema mutations/drops (Risk: `HIGH`)
* **Execution Path**: Backend services read/write JSON files directly. Agent dispatch returns static `TaskItem`.
* **Capability Classifications**:
  - **Execute shell commands**: `NOT IMPLEMENTED`
  - **Inspect Git repositories**: `NOT IMPLEMENTED`
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `NOT IMPLEMENTED`
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `HIGH`
* **Current Limitation**: The underlying storage is flat JSON (`data/approvals.json`, `data/cost_guard.json`, `data/audit/`). There is no SQLite or relational database, and no query tool bound to the agent.

---

### Agent 9: `agent-ux` (UX-TACTICIAN / INTERFACE-UX)
* **Name**: UX-TACTICIAN (INTERFACE-UX)
* **Role**: Mobile-First Cyber-HUD & Design System Architect
* **Allowed Tools in Manifest**: `["css_stylist", "react_component_gen", "tailwind_optimizer"]`
* **Autonomy Tier**: Autonomous
* **Approval Required**: NO (Risk: `LOW`)
* **Execution Path**: Dispatch returns static `TaskItem`.
* **Capability Classifications**:
  - **Execute shell commands**: `NOT IMPLEMENTED`
  - **Inspect Git repositories**: `NOT IMPLEMENTED`
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `NOT IMPLEMENTED`
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `LOW`
* **Current Limitation**: Cannot inspect `frontend/src` or compile CSS/React components dynamically. The UI is statically built.

---

### Agent 10: `agent-seo` (SEO-AMPLIFIER / RADAR-METRICS)
* **Name**: SEO-AMPLIFIER (RADAR-METRICS)
* **Role**: Metadata, Web Vitals & Search Index Optimizer
* **Allowed Tools in Manifest**: `["lighthouse_auditor", "meta_tag_generator", "sitemap_validator"]`
* **Autonomy Tier**: Autonomous
* **Approval Required**: NO (Risk: `LOW`)
* **Execution Path**: Dispatch returns static `TaskItem`.
* **Capability Classifications**:
  - **Execute shell commands**: `NOT IMPLEMENTED`
  - **Inspect Git repositories**: `NOT IMPLEMENTED`
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `NOT IMPLEMENTED`
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `LOW`
* **Current Limitation**: No Lighthouse engine or sitemap validator implemented.

---

### Agent 11: `agent-cost` (COST-OPTIMIZER / PRUDENCE-COST)
* **Name**: COST-OPTIMIZER (PRUDENCE-COST)
* **Role**: Cloud Billing & Hard Zero-Incurrence Guardrail Sentinel
* **Allowed Tools in Manifest**: `["billing_auditor", "tier_calculator", "budget_verifier"]`
* **Autonomy Tier**: Autonomous
* **Approval Required**: NO (Risk: `LOW`)
* **Execution Path**: Direct execution in `backend/core/cost_guard.py` via `/api/v1/cost/status` and `/api/v1/cost/evaluate`.
* **Capability Classifications**:
  - **Execute shell commands**: `NOT IMPLEMENTED`
  - **Inspect Git repositories**: `NOT IMPLEMENTED`
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `REAL` (Accurately tracks billing account status and enforces free-tier limits)
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `LOW`
* **Current Limitation**: Cost evaluation logic is real in Python, but agent dispatch routing is declarative.

---

### Agent 12: `agent-mon` (METRICS-PROBER / TELEM-BEACON)
* **Name**: METRICS-PROBER (TELEM-BEACON)
* **Role**: Host Telemetry, Ports & Socket Health Observer
* **Allowed Tools in Manifest**: `["psutil_stream", "port_scanner", "socket_probe"]`
* **Autonomy Tier**: Autonomous
* **Approval Required**: NO (Risk: `LOW`)
* **Execution Path**: Direct background execution in `backend/server.py` `/ws` streaming live `psutil` CPU/RAM and `backend/core/observability.py` recording HTTP latencies and trace spans.
* **Capability Classifications**:
  - **Execute shell commands**: `NOT IMPLEMENTED` (Uses native Python library `psutil`)
  - **Inspect Git repositories**: `NOT IMPLEMENTED`
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `NOT IMPLEMENTED`
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `LOW`
* **Current Limitation**: Observability pipeline is 100% real code, but it operates as a background daemon service rather than an autonomous decision-making agent.

---

### Agent 13: `agent-recovery` (RECOVERY-GUARDIAN / PHOENIX-REC)
* **Name**: RECOVERY-GUARDIAN (PHOENIX-REC)
* **Role**: Disaster Recovery, Health Restoration & Panic Protocol
* **Allowed Tools in Manifest**: `["state_restorer", "process_killer", "backup_manager"]`
* **Autonomy Tier**: Guardrailed
* **Approval Required**: YES except during active panic protocol (Risk: `CRITICAL`)
* **Execution Path**: `/api/panic` records an audit trace. `scripts/rollback.sh` is an executable, verified Bash script that restores git working trees and terminates orphan processes.
* **Capability Classifications**:
  - **Execute shell commands**: `REAL` (Executes `bash scripts/rollback.sh`)
  - **Inspect Git repositories**: `REAL` (Checks git status and branches during rollback)
  - **Create git diffs**: `NOT IMPLEMENTED`
  - **Run tests**: `NOT IMPLEMENTED`
  - **Perform security scans**: `NOT IMPLEMENTED`
  - **Update documentation**: `NOT IMPLEMENTED`
  - **Interact with GCP**: `NOT IMPLEMENTED`
  - **Interact with GitHub**: `NOT IMPLEMENTED`
* **Actual Risk Level**: `CRITICAL`
* **Current Limitation**: Automatic trigger of `rollback.sh` from `/api/panic` requires manual CLI execution or pipeline invocation; the API endpoint records the panic state in the audit log.

---

## Complete 13-Agent Capability Matrix

| Agent ID | Agent Name | Autonomy Tier | Risk Level | Approval Required | Shell Cmds | Inspect Git | Git Diffs | Run Tests | Security Scans | Update Docs | GCP Read/Write | GitHub Int | Execution Reality |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `agent-research` | RESEARCH-01 | Autonomous | LOW | NO | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | **SIMULATED** |
| `agent-dev` | DEVELOPER-02 | Guardrailed | MEDIUM | YES | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | **SIMULATED** |
| `agent-security` | SENTINEL-SEC | Autonomous | HIGH | YES | PARTIAL | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | PARTIAL | NOT IMPLEMENTED | SIMULATED | NOT IMPLEMENTED | **PARTIAL** |
| `agent-qa` | QA-VERIFIER | Autonomous | LOW | NO | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | SIMULATED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | **SIMULATED** |
| `agent-docs` | DOC-CHRONICLER | Autonomous | LOW | NO | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | PARTIAL | NOT IMPLEMENTED | NOT IMPLEMENTED | **PARTIAL** |
| `agent-devops` | DEVOPS-RUNNER | Guardrailed | HIGH | YES | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | SIMULATED | **SIMULATED** |
| `agent-infra` | INFRA-ENGINEER | Step-by-Step | CRITICAL | YES | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | SIMULATED | NOT IMPLEMENTED | **SIMULATED** |
| `agent-data` | DATA-CATALYST | Guardrailed | HIGH | YES | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | **PARTIAL** |
| `agent-ux` | UX-TACTICIAN | Autonomous | LOW | NO | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | **SIMULATED** |
| `agent-seo` | SEO-AMPLIFIER | Autonomous | LOW | NO | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | **SIMULATED** |
| `agent-cost` | COST-OPTIMIZER | Autonomous | LOW | NO | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | REAL | NOT IMPLEMENTED | **REAL** |
| `agent-mon` | METRICS-PROBER | Autonomous | LOW | NO | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | **REAL** |
| `agent-recovery` | RECOVERY-GUARDIAN | Guardrailed | CRITICAL | YES | REAL | REAL | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | **REAL** |

---

## 2. Empirical Testing of Real Execution Paths Locally

The 11 representative execution paths were empirically evaluated against the running backend daemon (`localhost:8000`) and the local filesystem without touching GCP or production:

### Path 1: Research Agent
* **Task**: Perform a research task using configured provider/tooling.
* **Test**: `POST /api/v1/agents/dispatch` with `instructions: "Analyze backend/routers/v1 to map all endpoints"`.
* **Observed Result**: Returns `status: "DISPATCHED"`, `progress: 25`, `tokens_spent: 350`, `result: null`. The task remains permanently in the `running` state with `progress: 25`. No AST search, file read, or provider query was executed.
* **Verdict**: **SIMULATED / UNWIRED**.

### Path 2: Developer Agent
* **Task**: Inspect a local repository and produce a real code change or git diff.
* **Test**: `POST /api/v1/agents/dispatch` with `agent_id: "agent-dev"`, `instructions: "Add a comment to README.md"`.
* **Observed Result**: Audit event logged, static `TaskItem` returned. Working tree status (`git status -s`) remains completely untouched.
* **Verdict**: **NOT IMPLEMENTED**.

### Path 3: Security Agent
* **Task**: Inspect actual files and identify a deliberately introduced safe test vulnerability.
* **Test**: 
  1. Introduced a safe test file `scratch/test_vuln.txt` containing a `-----BEGIN PRIVATE KEY-----` dummy header.
  2. Invoked `POST /api/v1/projects/control-center/security`.
  3. Invoked `POST /api/v1/automations/run/auto-secret-scan`.
* **Observed Results**:
  - `POST /projects/control-center/security` returned `{"cves_found": 0, "secrets_leaked": 0}` (**FAILED** to detect).
  - `POST /automations/run/auto-secret-scan` returned:
    ```json
    {
      "job_id": "auto-secret-scan",
      "status": "SUCCESS",
      "output": {
        "findings_count": 1,
        "findings": ["Potential private key found in /root/control-center"],
        "status": "WARNING"
      }
    }
    ```
    (**SUCCESSFULLY DETECTED** via real `grep` subprocess).
* **Cleanup**: Test file `scratch/test_vuln.txt` cleanly deleted.
* **Verdict**: **PARTIAL** (Real detection in automation engine; simulated in project security endpoint and agent dispatch).

### Path 4: QA Agent
* **Task**: Execute an existing local test suite and report real results.
* **Test**: Invoked `POST /api/v1/projects/control-center/test`.
* **Observed Result**: Returned `{"tests_total": 24, "passed": 24, "failed": 0, "duration": "1.42s"}`.
* **Ground Truth Verification**: Running `pytest tests/ --collect-only -q` revealed **27 tests** in `tests/`, not 24. Pytest took 3.07 seconds.
* **Verdict**: **SIMULATED**. The endpoint returns static mock data and does not invoke pytest.

### Path 5: Documentation Agent
* **Task**: Inspect code/ADRs and update documentation.
* **Test**: Inspected `backend/routers/v1/docs_router.py`.
* **Observed Result**: `GET /api/v1/docs` returns a static array of 3 ADRs. There is no `POST`, `PUT`, or markdown editing function. `auto-morning-brief` formats markdown in memory but writes nothing to disk.
* **Verdict**: **NOT IMPLEMENTED** (No write/update capability exists).

### Path 6: DevOps Agent
* **Task**: Inspect CI/CD configuration and validate it.
* **Test**: Inspected `backend/integrations/adapters/github_adapter.py`.
* **Observed Result**: Returns static mock dictionary: `{"workflow": "Production Pipeline", "status": "SUCCESS", "conclusion": "SUCCESS"}`. No YAML parser, linter, or action validator is present.
* **Verdict**: **SIMULATED**.

### Path 7: Infrastructure Agent
* **Task**: Inspect GCP/IaC configuration safely read-only.
* **Test**: Inspected `backend/routers/v1/cloud_router.py` and `backend/integrations/gcp.py`.
* **Observed Result**: Returns static JSON generated from `core/config.py` constants. Does not execute `gcloud` or GCP SDK calls.
* **Verdict**: **SIMULATED** (Configuration reflection only; no live inspection).

### Path 8: Data Agent
* **Task**: Inspect/query configured local/test data safely.
* **Test**: Inspected `data/` directory and backend data loaders.
* **Observed Result**: Flat JSON files exist (`data/approvals.json`, `data/cost_guard.json`, `data/projects/projects_registry.json`). FastAPI reads them via `json.load()`. However, the agent has no query interface, SQLite database, or tool handler.
* **Verdict**: **PARTIAL** (Underlying data is real; agent querying is unhandled).

### Path 9: UX/UI Agent
* **Task**: Inspect dashboard source and provide actionable changes.
* **Test**: Checked agent manifest and tool registry for frontend component tools.
* **Observed Result**: No tool handler exists to read or edit `frontend/src`.
* **Verdict**: **NOT IMPLEMENTED**.

### Path 10: SEO/Marketing Agent
* **Task**: Analyze provided project metadata/content.
* **Test**: Checked agent manifest and tool registry for SEO tools.
* **Observed Result**: No Lighthouse tool, metadata scraper, or sitemap builder exists.
* **Verdict**: **NOT IMPLEMENTED**.

### Path 11: Cost Optimizer
* **Task**: Evaluate cost/quota safeguards.
* **Test**: Invoked `POST /api/v1/cost/evaluate` with:
  1. `{"service": "compute.googleapis.com", "action": "create_instance"}`
  2. `{"service": "run.googleapis.com", "action": "read_logs"}`
* **Observed Results**:
  1. Returned: `{"allowed": false, "reason": "Billing unlinked: Paid infrastructure creation blocked by Zero-Cost Guardrail.", "risk": "CRITICAL"}` (**BLOCKED**).
  2. Returned: `{"allowed": true, "reason": "Action falls within Free Tier or local non-billable boundaries.", "risk": "LOW"}` (**PERMITTED**).
* **Verdict**: **REAL**. The Cost Guard evaluates business rules and enforces the $0.00 ceiling deterministically.

---

## 3. Ground-Truth Assessment: Why the Gap Exists

1. **Architecture Intent vs. Phase 2 Scaffolding**: Phase 2 focused on creating a unified cockpit interface, establishing security policies, least-privilege service accounts, keyless WIF, and comprehensive API routers. The agent swarm was populated with complete declarative manifests (`AgentManifest`) to define the target operating model, but tool execution handlers were stubbed.
2. **Safety Enforcement Precedence**: To prevent unintended cloud billing or accidental mutation of legacy projects, execution paths were intentionally guarded by strict policy gates (`core/policy.py`) and mock adapters.
3. **The Four Real Engines**:
   - **Observability Engine**: Real telemetry collection (`psutil`, OpenTelemetry traces, latency tracking).
   - **Cost Guard Engine**: Real quota and billing protection (`data/cost_guard.json`).
   - **Isolation & Policy Engine**: Real gating of destructive and legacy actions (`core/policy.py`, `core/approvals.py`).
   - **Secret Audit Engine**: Real file-level regex scanning (`core/automations.py`).

---

## 4. Hardening Roadmap (Zero-Cost Local Bridging)

To bridge the gap between declarative manifests and real execution without violating zero-cost or cloud-deployment safety rules:

1. **Wire QA Agent to Pytest**:
   - Update `POST /projects/{id}/test` and `agent-qa` handler to run `pytest tests/ --json-report` or capture stdout in a subprocess, returning live test results (27/27) rather than the static 24/24 mock.
2. **Wire Security Agent to the Regex Scanner**:
   - Update `POST /projects/{id}/security` and `agent-security` dispatch to call `_run_secret_scan()` from `core/automations.py`, making project-level security audits genuinely live.
3. **Wire Research Agent to AST / Ripgrep**:
   - Equip `agent-research` with a read-only tool handler that executes `ripgrep` / Python AST parsing within `/root/control-center` to return symbol tables and endpoint maps.
4. **Wire Data Agent to JSON Store Explorer**:
   - Equip `agent-data` with a read-only JSON query handler allowing inspection of `data/*.json` and `data/audit/*.jsonl`.
5. **Preserve Cloud-Safe Boundaries**:
   - Maintain `agent-infra` and `agent-devops` in guardrailed plan-only mode with keyless OIDC, keeping GCP billing strictly unlinked.
