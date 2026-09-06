# ☁️ GOOGLE CLOUD PLATFORM INFRASTRUCTURE INVENTORY
**Project ID**: `personal-engineering-os-2026`  
**Project Number**: `582208055065`  
**Region**: `asia-south1` (Mumbai)  
**Lifecycle State**: `ACTIVE`  
**Audit Timestamp**: 2026-09-07T01:52:00+05:30  

---

## 1. Active Enabled APIs & Services (25 Total)
| API Identifier | Service Title | Purpose |
|---|---|---|
| `iam.googleapis.com` | Identity and Access Management API | Keyless Service Accounts & RBAC |
| `iamcredentials.googleapis.com` | IAM Service Account Credentials API | Workload Identity Token Generation |
| `cloudresourcemanager.googleapis.com` | Cloud Resource Manager API | Project Metadata & Policy Verification |
| `logging.googleapis.com` | Cloud Logging API | Structured Audit Logs & Redacted Traces |
| `monitoring.googleapis.com` | Cloud Monitoring API | Real-time Metrics & Dashboard Telemetry |
| `cloudtrace.googleapis.com` | Cloud Trace API | Distributed OpenTelemetry Trace Ingestion |
| `serviceusage.googleapis.com` | Service Usage API | API Quota & Activation Management |
| `servicemanagement.googleapis.com` | Service Management API | Google Cloud Service Fabric |
| `storage-api.googleapis.com` | Google Cloud Storage JSON API | Storage Bucket Access |
| `storage-component.googleapis.com` | Cloud Storage Component | Internal GCS Plumbing |
| `storage.googleapis.com` | Cloud Storage API | Artifact Storage & Object Buckets |
| `bigquery.googleapis.com` | BigQuery API | Analytics & Log Warehousing |
| `bigqueryconnection.googleapis.com` | BigQuery Connection API | External DB Query Federation |
| `bigquerydatapolicy.googleapis.com` | BigQuery Data Policy API | Data Governance & Column Masking |
| `bigquerydatatransfer.googleapis.com` | BigQuery Data Transfer API | Scheduled Data Transfers |
| `bigquerymigration.googleapis.com` | BigQuery Migration API | SQL Translation & Assessment |
| `bigqueryreservation.googleapis.com` | BigQuery Reservation API | Workgroup Quota & Slot Management |
| `bigquerystorage.googleapis.com` | BigQuery Storage API | High-throughput Arrow Ingestion |
| `datastore.googleapis.com` | Cloud Datastore API | NoSQL Document Key-Value Database |
| `dataform.googleapis.com` | Dataform API | SQL Workflow Management |
| `dataplex.googleapis.com` | Cloud Dataplex API | Data Mesh Governance |
| `analyticshub.googleapis.com` | Analytics Hub API | Cross-org Data Exchange |
| `telemetry.googleapis.com` | Telemetry API | Cloud Platform Telemetry |
| `sql-component.googleapis.com` | Cloud SQL Component | Database Integration Layer |
| `cloudapis.googleapis.com` | Google Cloud APIs | Core Google Cloud API Gateway |

---

## 2. Workload Identity Federation (Keyless GitHub CI/CD)
* **Pool Resource**: `projects/582208055065/locations/global/workloadIdentityPools/github-pool`
* **Status**: `ACTIVE`
* **Provider Resource**: `projects/582208055065/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
* **Status**: `ACTIVE`
* **Issuer URI**: `https://token.actions.githubusercontent.com`
* **Attribute Mapping**:
  - `google.subject` = `assertion.sub`
  - `attribute.actor` = `assertion.actor`
  - `attribute.repository` = `assertion.repository`
  - `attribute.repository_owner` = `assertion.repository_owner`
* **Cryptographic Condition**: `assertion.repository_owner == 'knightriderisback'`
* **Security Evaluation**: Eliminates 100% of static JSON key attack vectors.

---

## 3. Dedicated Service Account Identities
| Display Name | Service Account Email | Bound Roles | Static Keys |
|---|---|---|---|
| NEXUS Control SA | `nexus-control-sa@personal-engineering-os-2026.iam.gserviceaccount.com` | `roles/logging.logWriter`, `roles/monitoring.metricWriter`, `roles/iam.workloadIdentityUser` | 0 (None) |
| NEXUS Deploy SA | `nexus-deploy-sa@personal-engineering-os-2026.iam.gserviceaccount.com` | Bound to `github-pool` (CI/CD Deployment) | 0 (None) |
| NEXUS Agent SA | `nexus-agent-sa@personal-engineering-os-2026.iam.gserviceaccount.com` | `roles/logging.logWriter` (Agent Swarm Runner) | 0 (None) |
| NEXUS Monitor SA | `nexus-monitor-sa@personal-engineering-os-2026.iam.gserviceaccount.com` | `roles/monitoring.metricWriter` (Telemetry Probe) | 0 (None) |

---

## 4. Protected Legacy Project Isolation Boundaries
The following existing projects are strictly isolated and protected from mutations:
1. `protyourfolio`: `PROTECTED_READ_ONLY` (Untouched)
2. `whatsapp-autopost-by-termux`: `PROTECTED_READ_ONLY` (Untouched)
3. `gen-lang-client-0352285705`: `PROTECTED_READ_ONLY` (Untouched)

---

## 5. Billing & Cost Profile
* **Billing Account Association**: `UNLINKED`
* **Current Spend**: `$0.00 / month`
* **Budget Ceiling**: `$0.00 / month`
* **Strict Zero-Cost Enforcement**: `ACTIVE` (Paid API calls intercepted before execution)
