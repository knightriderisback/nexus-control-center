# 📦 COMPLETE INVENTORY OF ACTUALLY CREATED RESOURCES
**System**: `NEXUS // Personal Engineering OS`  
**Audit Date**: 2026-09-07T01:52:00+05:30  
**Verification Standard**: Ground-Truth Inspection (Zero Speculative Claims)  

---

## 1. Google Cloud Platform Resources (`personal-engineering-os-2026`)
* **Project**: `personal-engineering-os-2026` (Number: `582208055065`, State: `ACTIVE`).
* **Workload Identity Pool**:
  - `projects/582208055065/locations/global/workloadIdentityPools/github-pool` (State: `ACTIVE`).
* **Workload Identity Provider**:
  - `projects/582208055065/locations/global/workloadIdentityPools/github-pool/providers/github-provider` (State: `ACTIVE`, OIDC bound to GitHub).
* **Dedicated Service Accounts (4 Total)**:
  1. `nexus-control-sa@personal-engineering-os-2026.iam.gserviceaccount.com` (State: `ACTIVE`, Keys: 0).
  2. `nexus-deploy-sa@personal-engineering-os-2026.iam.gserviceaccount.com` (State: `ACTIVE`, Keys: 0).
  3. `nexus-agent-sa@personal-engineering-os-2026.iam.gserviceaccount.com` (State: `ACTIVE`, Keys: 0).
  4. `nexus-monitor-sa@personal-engineering-os-2026.iam.gserviceaccount.com` (State: `ACTIVE`, Keys: 0).
* **IAM Role Bindings**:
  - `nexus-control-sa`: `roles/logging.logWriter`, `roles/monitoring.metricWriter`, `roles/iam.workloadIdentityUser`.
  - `nexus-agent-sa`: `roles/logging.logWriter`.
  - `nexus-monitor-sa`: `roles/monitoring.metricWriter`.
  - `nexus-deploy-sa`: Bound to `principalSet` of WIF `github-pool` with `assertion.repository_owner == 'knightriderisback'`.

---

## 2. Local Workstation & Runtime Resources (`/root/control-center`)
* **Control API Daemon**:
  - Running on `0.0.0.0:8000` (FastAPI with Uvicorn, background PID 19038).
  - Serving 34 versioned endpoints under `/api/v1/...` and WebSocket `/ws`.
* **Frontend Cyber-HUD Web Application**:
  - Compiled production bundle in `/root/control-center/frontend/dist` (Vite 8 + React 19 + TypeScript).
  - Assets: `dist/assets/index-CaxepmNw.js` (288 kB), `dist/assets/index-ABmivxDD.css` (48 kB).
* **Command Line Interface**:
  - Executable binary `/usr/local/bin/eco` (7.5 kB).
  - Symlink `/root/control-center/eco`.
* **State & Data Stores**:
  - Policy Rules: `/root/control-center/data/policies/rules.json` (10 rules).
  - Project Registry: `/root/control-center/data/projects/projects_registry.json` (3 tracked projects).
  - Approvals State Store: `/root/control-center/data/approvals.json`.
  - Append-Only Audit Trail: `/root/control-center/data/audit/audit_trail.jsonl` (Redacted events).
  - Cost Guard State: `/root/control-center/data/cost_guard.json` (Spend: $0.00).
  - Secrets Template: `/root/control-center/data/secrets/secrets.template.json`.
  - Memory & ADR Store: `/root/control-center/data/memory_vault.json`.
* **CI/CD & Operational Scripts**:
  - Workflow: `/root/control-center/.github/workflows/production-pipeline.yml` (12-stage pipeline).
  - Rollback Protocol: `/root/control-center/scripts/rollback.sh`.
  - System Verification Probe: `/root/control-center/scripts/verify_system.sh`.
* **Automated Test Suite**:
  - 27 test cases across 6 test modules in `/root/control-center/tests/`.

---

## 3. Cloud Resources Intentionally ZERO (Cost Safety Guaranteed)
* **Compute Engine Virtual Machines**: 0 (Zero VMs created).
* **Google Kubernetes Engine Clusters**: 0 (Zero clusters created).
* **Cloud SQL Database Instances**: 0 (Zero database instances created).
* **Static Service Account JSON Keys**: 0 (Zero keys generated).
* **Billable Incurred Cost**: **$0.00** (Billing account strictly unlinked).
