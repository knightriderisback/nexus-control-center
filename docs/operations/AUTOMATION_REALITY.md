# ⏱️ AUTOMATION ENGINE REALITY REPORT

**Audit Date**: 2026-09-07  
**Operating Project**: `personal-engineering-os-2026`  
**Engine Implementation**: `backend/core/automations.py`  
**API Router**: `backend/routers/v1/automations_router.py`  

---

## 1. Classification of Automation Jobs

In cloud and systems engineering, it is vital to distinguish between a **Cloud Scheduler job**, a **local cron job**, and an **on-demand application function**. The 6 jobs registered in NEXUS were individually analyzed:

| Job ID | Name | Declared Schedule | Actual Function | Execution Mechanism | Trigger Mechanism | Scheduling Reality | Persistence | Audit Logging |
|---|---|---|---|---|---|---|---|---|
| `auto-morning-brief` | Morning Engineering Brief | `0 6 * * *` | `generate_morning_brief()` | Application Function (In-memory markdown) | Manual Trigger | **NO ACTIVE CRON** | None (Generated on request) | Yes (`AUTOMATION_EXECUTION`) |
| `auto-nightly-health` | Nightly Health Check | `0 20 * * *` | Fallback branch in `execute_job` | Simulated (Static dictionary) | Manual Trigger | **NO ACTIVE CRON** | `last_run` in memory | Yes (`AUTOMATION_EXECUTION`) |
| `auto-repo-sweep` | Git Repo Drift Sweep | `*/30 * * * *` | `_run_repo_sweep()` | Real (`git status -s` subprocess) | Manual Trigger | **NO ACTIVE CRON** | `last_run` in memory | Yes (`AUTOMATION_EXECUTION`) |
| `auto-security-audit` | Dependency & IAM Audit | `0 2 * * *` | Fallback branch in `execute_job` | Simulated (Static dictionary) | Manual Trigger | **NO ACTIVE CRON** | `last_run` in memory | Yes (`AUTOMATION_EXECUTION`) |
| `auto-secret-scan` | Secret Leakage Scanner | `0 */4 * * *` | `_run_secret_scan()` | Real (`grep -rn` subprocess) | Manual Trigger | **NO ACTIVE CRON** | `last_run` in memory | Yes (`AUTOMATION_EXECUTION`) |
| `auto-cost-check` | Zero-Cost Guardrail Audit | `0 0 * * *` | `cost_guard.get_status()` | Real (Reads `data/cost_guard.json`) | Manual Trigger | **NO ACTIVE CRON** | `last_run` in memory | Yes (`AUTOMATION_EXECUTION`) |

---

## 2. Key Ground-Truth Distinctions

1. **Zero Cloud Scheduler Jobs**: There are no jobs deployed to Google Cloud Scheduler (`gcloud scheduler jobs list` returns 0).
2. **Zero Systemd / Crontab Entries**: No Linux crontab (`crontab -l`) or systemd timer is currently configured on the host machine to invoke these jobs automatically.
3. **Application Functions with Manual Trigger**: All 6 jobs are Python methods on `AutomationsEngine` callable via HTTP `POST /api/v1/automations/run/{job_id}` or `eco automations run <id>`.
4. **Execution Fidelity**:
   - `auto-secret-scan` and `auto-repo-sweep` run real operating-system subprocesses (`grep` and `git`).
   - `auto-morning-brief` and `auto-cost-check` dynamically read state files.
   - `auto-nightly-health` and `auto-security-audit` return canned status dictionaries.
