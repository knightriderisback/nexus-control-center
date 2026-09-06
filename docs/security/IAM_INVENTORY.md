# 🛡️ LEAST-PRIVILEGE IAM & ACCESS CONTROL INVENTORY
**Project ID**: `personal-engineering-os-2026`  
**Security Posture**: Zero-Trust, Keyless Workload Identity, Least Privilege  
**Static Service Account Keys**: 0 (Strictly Prohibited)  

---

## 1. Service Identities & Role Bindings

### `nexus-control-sa@personal-engineering-os-2026.iam.gserviceaccount.com`
* **Display Name**: NEXUS Control Service Account
* **Assigned Roles**:
  - `roles/logging.logWriter`: Allows appending structured events to Cloud Logging.
  - `roles/monitoring.metricWriter`: Allows writing telemetry and custom metrics.
  - `roles/iam.workloadIdentityUser`: Allows impersonation via approved federated identities.
* **Prohibited Roles**: `roles/owner`, `roles/editor`, `roles/iam.securityAdmin`.

### `nexus-deploy-sa@personal-engineering-os-2026.iam.gserviceaccount.com`
* **Display Name**: NEXUS Deploy Service Account
* **Assigned Roles**:
  - Bound to `principalSet://iam.googleapis.com/projects/582208055065/locations/global/workloadIdentityPools/github-pool/attribute.repository_owner/knightriderisback`
  - Staged for Cloud Run developer deployment role upon billing activation.
* **Prohibited Roles**: Permanent administrative privileges.

### `nexus-agent-sa@personal-engineering-os-2026.iam.gserviceaccount.com`
* **Display Name**: NEXUS Agent Runner Service Account
* **Assigned Roles**:
  - `roles/logging.logWriter`: Audits all agent executions into centralized append-only log.
* **Prohibited Roles**: Any cloud resource modification roles.

### `nexus-monitor-sa@personal-engineering-os-2026.iam.gserviceaccount.com`
* **Display Name**: NEXUS Monitor Service Account
* **Assigned Roles**:
  - `roles/monitoring.metricWriter`: Publishes health checks and latency statistics.

---

## 2. Workload Identity Federation Architecture
```
GitHub Actions Workflow
   │
   ├─ 1. Requests short-lived OIDC Token from GitHub Token Authority
   │     (Audience: 'https://token.actions.githubusercontent.com')
   │
   ▼
Google Cloud Security Token Service (STS)
   │
   ├─ 2. Validates assertion.repository_owner == 'knightriderisback'
   │
   ▼
Federated Identity Pool (`github-pool`)
   │
   ├─ 3. Exchanges OIDC Token for Google Cloud Federated Token
   │
   ▼
Google Cloud IAM
   │
   └─ 4. Generates temporary (1 hour max) access token for nexus-deploy-sa
```

---

## 3. Central Policy Rules & Risk Tiers
Enforced by [`backend/core/policy.py`](file:///root/control-center/backend/core/policy.py):

| Rule ID | Risk Level | Requires Approval | Target Action | Purpose |
|---|---|---|---|---|
| `pol-000` | `CRITICAL` | YES | Legacy Project Access | Absolute isolation of `protyourfolio`, `whatsapp-autopost`, etc. |
| `pol-001` | `CRITICAL` | YES | `rm -rf`, `drop database` | Prevents destructive data deletion |
| `pol-002` | `CRITICAL` | YES | `billing accounts link` | Prevents unauthorized financial liability |
| `pol-003` | `CRITICAL` | YES | `service-accounts keys create`| Enforces 0 static JSON key policy |
| `pol-004` | `HIGH` | YES | `run deploy`, `deploy production` | Operator clearance gate for production releases |
| `pol-005` | `HIGH` | YES | `add-iam-policy-binding` | Prevents privilege escalation |
| `pol-006` | `HIGH` | YES | `git push --force`, `git reset` | Prevents overwriting version control history |
| `pol-007` | `MEDIUM`| NO | `git commit`, `create pr` | Normal software development workflows |
| `pol-008` | `MEDIUM`| NO | `pip install`, `npm install` | Dependency installation within containers |
| `pol-009` | `LOW` | NO | `status`, `test`, `audit`, `get` | Read-only queries execute autonomously |
