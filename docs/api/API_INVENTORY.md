# 🌐 NEXUS CONTROL API ENDPOINT INVENTORY
**Base URL**: `http://localhost:8000`  
**API Prefix**: `/api/v1`  
**OpenAPI Specification**: `http://localhost:8000/docs`  
**WebSocket Stream**: `ws://localhost:8000/ws`  

---

## 1. System Overview & Telemetry
* `GET /api/v1/overview`: System telemetry, agent fleet counts, active projects, pending approvals.
* `GET /api/health`: Health probe returning `status: ONLINE`.
* `GET /api/telemetry`: Real-time psutil CPU load (overall & per core), RAM breakdown, disk space.
* `WS  /ws`: 1 Hz bi-directional WebSocket streaming live telemetry, agent metrics, and pending gates.

---

## 2. Project Registry & Actions
* `GET /api/v1/projects`: List registered projects with environments, health scores, and providers.
* `POST /api/v1/projects`: Register a new project.
* `GET /api/v1/projects/{id}`: Detailed metadata for a specific project.
* `POST /api/v1/projects/{id}/audit`: Trigger multi-point audit (git, security, tests).
* `POST /api/v1/projects/{id}/test`: Execute unit and integration tests.
* `POST /api/v1/projects/{id}/security`: Run AST code and secret leakage scanner.
* `POST /api/v1/projects/{id}/deploy`: Request production deployment (Gated by Approval Engine).

---

## 3. Autonomous Agent Swarm
* `GET /api/v1/agents`: List 13 specialized agent manifests, status, token usage, and autonomy tiers.
* `GET /api/v1/agents/{id}`: Detailed manifest and capabilities for an agent.
* `POST /api/v1/agents/{id}/dispatch`: Dispatch a task to a specific agent.
* `GET /api/tasks`: List all active, awaiting_approval, and completed neural tasks.
* `POST /api/tasks/dispatch`: Legacy dispatch alias.

---

## 4. Human Approval Gates
* `GET /api/v1/approvals`: List all approval requests and statuses (`PENDING`, `APPROVED`, `REJECTED`, `EXECUTED`).
* `POST /api/v1/approvals`: Request a new approval token for an action.
* `POST /api/v1/approvals/{id}/decide`: Operator decision endpoint (`APPROVED` or `REJECTED`).
* `POST /api/approvals/decide`: Legacy decision alias for HUD.

---

## 5. Central Policy Engine
* `GET /api/v1/policy`: List 10 loaded policy rules.
* `GET /api/v1/policy/rules`: Alias for listing policy rules.
* `POST /api/v1/policy/evaluate`: Risk classifier evaluating command and target project.

---

## 6. Audit & Compliance
* `GET /api/v1/audit`: Query append-only audit trail with automatic secret redaction.
* `POST /api/v1/audit`: Append manual operator or agent audit event.

---

## 7. FinOps & Cost Guardrails
* `GET /api/v1/cost/status`: Incurred monthly spend ($0.00), budget ceiling, free-tier quotas.
* `POST /api/v1/cost/evaluate`: Pre-flight check evaluating cost risk for cloud operations.

---

## 8. Scheduled Automations
* `GET /api/v1/automations/jobs`: List 6 registered operational routines with cron schedules.
* `POST /api/v1/automations/run/{id}`: Manually trigger an automated operational routine.
* `GET /api/v1/automations/brief`: Generate instant Markdown Morning Engineering Brief.

---

## 9. Observability & Distributed Tracing
* `GET /api/v1/metrics`: Request counters, status code breakdown, error rates, average latencies.
* `GET /api/v1/traces`: Query distributed trace buffer with `trace_id`, `span_id`, duration ms.

---

## 10. Secrets & Credentials (Zero-Leakage)
* `GET /api/v1/secrets`: List configured secret metadata, status (`CONFIGURED` / `PENDING`), masked preview.
* `GET /api/v1/secrets/{name}/status`: Check single secret configuration status.

---

## 11. Integration Adapters
* `GET /api/v1/integrations/isolated-projects`: Manifest of protected legacy GCP projects.
* `GET /api/v1/integrations/termux`: Mobile Android node heartbeat and battery status.
* `POST /api/v1/integrations/termux/heartbeat`: Post mobile node telemetry.
* `GET /api/v1/integrations/vercel/{project_name}`: Query Vercel deployment status.

---

## 12. Command & Emergency Operations
* `POST /api/v1/eco/execute`: Natural language prompt router for eco directives.
* `POST /api/panic`: Emergency killswitch aborting all neural tasks and setting status to `HALTED`.
* `POST /api/macros/run`: Execute predefined operations macros (`git:status`, `system:diagnostics`).
* `GET /api/v1/docs`: Knowledge matrix and Architecture Decision Records (ADRs).
