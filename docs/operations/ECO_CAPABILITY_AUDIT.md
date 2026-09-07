# ⚡ ECO CLI: CAPABILITY & EXECUTION AUDIT

**Audit Date**: 2026-09-07  
**Operating Project**: `personal-engineering-os-2026`  
**Binary Location**: `/usr/local/bin/eco` (and `/root/control-center/eco`)  
**API Connection**: `http://127.0.0.1:8000/api/v1`  

---

## 1. Subcommand Implementation Matrix

| Command | Category | Classification | Actual Execution Path | Reaches Control API |
|---|---|---|---|---|
| `eco status` | System | **`REAL`** | Calls `GET /api/v1/overview`. Displays system status, agent counts, host CPU/RAM. | YES |
| `eco projects` | Registry | **`REAL`** | Calls `GET /api/v1/projects`. Formats registered project IDs, environments, and health scores. | YES |
| `eco agents` | Fleet | **`REAL`** | Calls `GET /api/v1/agents`. Lists all 13 specialized agent manifests with risk tiers. | YES |
| `eco audit [id]` | Auditing | **`REAL`** | Calls `POST /api/v1/projects/{id}/audit`. Verifies repo existence and dirty file status via `git`. | YES |
| `eco test [id]` | Testing | **`REAL (Hardened)`** | Calls `POST /api/v1/projects/{id}/test`. Spawns live `pytest` subprocess, returns actual pass/fail counts. | YES |
| `eco security [id]` | Security | **`REAL (Hardened)`** | Calls `POST /api/v1/projects/{id}/security`. Runs real PEM secret scans across workspaces. | YES |
| `eco deploy [id]` | Deployment | **`REAL` (Gate)** | Calls `POST /api/v1/projects/{id}/deploy`. Triggers policy gate, creates approval request, blocks deploy. | YES |
| `eco logs` | Observability | **`REAL (Hardened)`** | Calls `GET /api/v1/audit`. Displays recent structured audit events with risk levels and actors. | YES |
| `eco docs` | Knowledge | **`REAL (Hardened)`** | Calls `GET /api/v1/docs`. Lists system ADRs and architectural documents. | YES |
| `eco jobs` | Operations | **`REAL (Hardened)`** | Calls `GET /api/v1/automations/jobs`. Formats registered automation jobs, schedules, and statuses. | YES |
| `eco approvals` | Governance | **`REAL`** | Calls `GET /api/v1/approvals` (list) and `POST /api/v1/approvals/{id}/decide` (decision). | YES |
| `eco cost` | Governance | **`REAL`** | Calls `GET /api/v1/cost/status`. Displays unlinked billing status and free-tier quotas. | YES |
| `eco traces` | Observability | **`REAL`** | Calls `GET /api/v1/traces`. Displays recent HTTP request traces, latencies, and status codes. | YES |

---

## 2. Hardening Enhancements Applied to Eco CLI

1. **Native Support for `eco jobs`**: Added alias routing so `eco jobs` directly calls the automations engine rather than falling into the natural language prompt fallback.
2. **Added `eco docs`**: Directly formats architecture decision records from `/api/v1/docs`.
3. **Added `eco logs`**: Formats the latest audit log trail from `/api/v1/audit`.
4. **Default Project ID Fallback**: Subcommands `eco test`, `eco security`, `eco audit`, and `eco deploy` now default cleanly to `control-center` if no explicit project ID argument is provided.
