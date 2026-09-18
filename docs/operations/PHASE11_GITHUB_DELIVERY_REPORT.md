# NEXUS Phase 11: GitHub-Native Autonomous Software Delivery & PR Governance

## 1. Executive Summary & Verification Matrix

### Verification Status Distinction
| Capability / Verification Domain | Status | Evidence / Mode |
| :--- | :--- | :--- |
| **Local Mock GitHub Lifecycle** | **LOCAL VERIFIED** | In-memory `MockGitHubClient` passing 28/28 tests & 12 CI stages |
| **Local Dry-Run Simulation** | **LOCAL VERIFIED** | Read-through with non-mutating simulated writes verified |
| **Real GitHub Client Codebase** | **LOCAL VERIFIED** | Native `httpx` REST client compiled, sanitized, and unit-tested |
| **Live Remote GitHub Execution** | **NOT VERIFIED** | **Intentionally NOT executed**. Air-gapped zero-cost preservation ($0.00 spend). No external tokens or live mutations performed. |

### Objective Selection Rationale
Following completion of NEXUS Phases 6–10 (Persistent Swarm Orchestration, Production Hardening, Isolated Git Worktrees, Swarm Merge Arbitration, and Real AI Provider Execution), software development within NEXUS was autonomous locally but lacked a governed remote delivery bridge.
Phase 11 establishes the enterprise delivery bridge extending local merge candidates to GitHub remote branches, governed Pull Requests, multi-agent reviews, risk-bound approvals, and verified merges.

---

## 2. System Architecture & Governed Pipeline

```
             ┌─────────────────────────────────────────────────────────┐
             │       LOCAL CANDIDATE RESOLUTION & VALIDATION           │
             │   (SafeCommandExecutor: git rev-parse, git merge-base)  │
             └────────────────────────────┬────────────────────────────┘
                                          │
                                          ▼
             ┌─────────────────────────────────────────────────────────┐
             │         DETERMINISTIC RISK CLASSIFICATION               │
             │    LOW / MEDIUM / HIGH / CRITICAL based on AST path     │
             └────────────────────────────┬────────────────────────────┘
                                          │
                                          ▼
             ┌─────────────────────────────────────────────────────────┐
             │         GOVERNED REMOTE BRANCH PUBLICATION              │
             │         nexus/<session_id>/<sanitized_source>           │
             └────────────────────────────┬────────────────────────────┘
                                          │
                                          ▼
             ┌─────────────────────────────────────────────────────────┐
             │       PULL REQUEST SYNTHESIS & PROVENANCE               │
             │   Deterministic labels: nexus, automated, risk:*, etc. │
             └────────────────────────────┬────────────────────────────┘
                                          │
                                          ▼
             ┌─────────────────────────────────────────────────────────┐
             │         MULTI-AGENT PR REVIEW PIPELINE                  │
             │   AGY/Research ──▶ Codex/Dev ──▶ QA ──▶ Security        │
             │   StructuredReviewFinding schema (blocking/non-blocking)│
             └────────────────────────────┬────────────────────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼                                         ▼
            [Low / Medium Risk]                       [High / Critical Risk]
                     │                                         │
                     ▼                                         ▼
             Autonomous Signoff                       Human Operator Approval
             (PR Review: APPROVE)                     (ApprovalBinding with consumed flag)
                     │                                         │
                     └────────────────────┬────────────────────┘
                                          │
                                          ▼
             ┌─────────────────────────────────────────────────────────┐
             │       10-STEP GOVERNED MERGE SEQUENCE                   │
             │  1. Confirm PR identity                                 │
             │  2. Confirm candidate commit SHA                        │
             │  3. Confirm target branch state                         │
             │  4. Confirm required checks                             │
             │  5. Confirm security gate                               │
             │  6. Confirm approval if required (Anti-Stale/Anti-Replay│
             │  7. Confirm no stale remote state                       │
             │  8. Confirm candidate still matches reviewed artifact   │
             │  9. Confirm merge policy (squash/rebase/merge)          │
             │ 10. Execute merge through GitHub abstraction            │
             └────────────────────────────┬────────────────────────────┘
                                          │
                                          ▼
             ┌─────────────────────────────────────────────────────────┐
             │      POST-MERGE VERIFICATION & AUDIT                    │
             │  - Verify target branch matches merge commit SHA        │
             │  - Recovery state entry if remote commit diverged       │
             │  - Immutable audit trail in data/audit/audit_trail.jsonl│
             └─────────────────────────────────────────────────────────┘
```

---

## 3. GitHub Security Model & Authentication

### 1. Token Protection & Secret Sanitization
- Zero GitHub personal access tokens (`ghp_`, `github_pat_`, OAuth bearer tokens) are ever logged to stdout, stderr, persistent files, or audit logs.
- All outbound requests, responses, exception stack traces, and audit logs pass through `sanitize_secrets()` multi-pattern regex redaction.

### 2. Authentication Flow
- **Environment Variable**: `GITHUB_TOKEN` (or backend `config.github_token`).
- **Headers**:
  ```http
  Authorization: Bearer <GITHUB_TOKEN>
  Accept: application/vnd.github+json
  X-GitHub-Api-Version: 2022-11-28
  User-Agent: NEXUS-Autonomous-Delivery-OS
  ```
- **Air-Gapped Fallback**: When `GITHUB_TOKEN` is unset or empty, `RealGitHubClient.health_check()` reports `configured=False`, `authenticated=False`, and `status="NOT_CONFIGURED"`. No network egress is attempted.

### 3. Prompt & Untrusted Content Quarantine
- All third-party PR diffs, commits, and comments are treated as untrusted input.
- Untrusted content is wrapped in `<UNTRUSTED_CONTENT>` tags via `wrap_safe_prompt()`, preventing prompt injection attacks from manipulating agent review verdicts.

---

## 4. Branch Strategy & Governance

### Governed Branch Naming
- Governed remote branch names follow the deterministic format:
  ```
  nexus/<session_id>/<sanitized_source_branch>
  ```
- Example: `nexus/sess-a1b2c3/feat-auth-middleware`

### Branch Sanitization & Injection Defense
- `sanitize_branch_name()` strips directory traversal sequences (`..`), shell metacharacters, whitespace, control characters, and non-ASCII glyphs.
- Slashes are preserved only for structural separators.

### Protected Branch Invariant
- **Invariant**: Direct pushes to or candidate publishing of `main`, `master`, or `production` are strictly rejected with a `ValueError("Branch Governance Violation")`.
- Default branches can only ever be updated via the 10-step governed merge sequence on GitHub.

---

## 5. Pull Request Lifecycle & Provenance

### PR Body Provenance Synthesis
Every synthesized Pull Request contains an automated provenance block including:
- Originating Swarm Session ID (`session_id`)
- Local Candidate Commit SHA (`candidate_commit`)
- Local Candidate Git Tree SHA (`candidate_tree_sha`)
- Target Branch (`target_branch`)
- Computed Risk Tier (`risk_level`)
- Agent Execution Chain (`AGY -> Codex -> QA -> Security`)
- Automated Test Results & AST Security Sentinel summary

### Deterministic Labeling
Labels are applied idempotently to prevent unbounded duplicates:
- `nexus`
- `automated`
- `risk:low` | `risk:medium` | `risk:high` | `risk:critical`
- `security-reviewed`
- `qa-passed`
- `approval-required` (added automatically for High/Critical risk deliveries)

---

## 6. Risk Model & Approval Governance

### Risk Tier Classification
The delivery engine inspects the commit diff against the target branch using AST rules:
- **`CRITICAL`**: Modifications to `data/secrets`, credential vaults, `.env`, security policies (`rules.json`, `approvals.json`), or IAM manifests.
- **`HIGH`**: Modifications to authentication modules, tokens, session management, or core orchestrator files (`backend/core/*`, `backend/orchestrator/*`).
- **`MEDIUM`**: Production code modifications outside core security paths (`backend/routers/*`, `backend/integrations/*`).
- **`LOW`**: Documentation, tests, markdown, fixtures, or non-production artifacts.

### Immutable Candidate Approval Binding
For `HIGH` and `CRITICAL` risk deliveries, a human operator approval is requested via `request_approval()`.
An immutable `ApprovalBinding` record is created:
```json
{
  "session_id": "sess-a1b2c3",
  "execution_id": "deliv-7f8e9d",
  "candidate_commit_sha": "f172b9f2...",
  "candidate_tree_sha": "4b825dc6...",
  "target_branch": "main",
  "risk_level": "HIGH",
  "approval_id": "appr-882104",
  "consumed": false,
  "bound_at": "2026-09-14T18:30:00Z"
}
```
- **Anti-Replay Protection**: Once consumed during merge, `binding.consumed = True`. Subsequent merge attempts with the same approval fail.
- **Anti-Stale Protection**: If the candidate branch is updated or re-committed after approval was granted (`candidate_commit_sha != delivery.candidate_commit`), merge is rejected with `Anti-Stale Violation`.

---

## 7. 10-Step Governed Merge & Failure Recovery

### The 10-Step Checklist
1. **Confirm PR identity**: Verify PR exists and is in `open` state.
2. **Confirm candidate commit SHA**: Match remote PR head against delivery candidate SHA.
3. **Confirm target branch state**: Verify target branch exists on remote.
4. **Confirm required checks**: Verify all CI/QA checks in `checks_results` passed.
5. **Confirm security gate**: Verify zero blocking security findings in `structured_findings`.
6. **Confirm approval if required**: Validate `ApprovalBinding`, anti-replay, and anti-stale bounds.
7. **Confirm remote freshness**: Verify remote PR has no merge conflicts (`mergeable: true`).
8. **Confirm artifact match**: Verify candidate commit matches reviewed artifact.
9. **Confirm merge policy**: Select `squash` (default), `rebase`, or `merge`.
10. **Execute merge**: Dispatch merge through GitHub abstraction.

### Post-Merge Verification & Safe Recovery
- Queries GitHub for the latest commit SHA of the target branch.
- If target branch SHA matches `merge_commit_sha`: transitions to terminal `COMPLETED`.
- If mismatch occurs: transitions to `POST_MERGE_FAILED` (recovery state).
- **Non-Destructive Guarantee**: NEXUS does NOT perform blind forced pushes or destructive git rollbacks on remote default branches. The pipeline halts in recovery state for operator intervention.

---

## 8. GitHub Client Modes & Setup

### Mode Matrix
1. **`mock` (Default)**:
   - In-memory simulator (`MockGitHubClient`).
   - Maintains simulated branches, PRs, comments, reviews, checks, and merges.
   - Cost: `$0.00`. Zero network egress. Perfect for air-gapped CI/CD and unit testing.
2. **`dry-run`**:
   - Wrap around active client (`DryRunGitHubClient`).
   - Permits read queries; logs write mutations safely with `[DRY-RUN]` prefixes without remote mutations.
3. **`real`**:
   - Live REST API client (`RealGitHubClient`).
   - Configured via `GITHUB_TOKEN`.

### Real GitHub Setup Guide
To configure live GitHub delivery:
```bash
# 1. Export personal access token with 'repo' scope
export GITHUB_TOKEN="ghp_yourPersonalAccessTokenHere"

# 2. Switch NEXUS GitHub mode to 'real'
eco github mode real

# 3. Verify health
eco github health
```

---

## 9. Audit Trail & Correlated Telemetry

### Lifecycle Audit Events
Recorded immutably to `data/audit/audit_trail.jsonl`:
- `GITHUB_HEALTH_CHECK`
- `GITHUB_CLIENT_MODE_SWITCH`
- `GITHUB_BRANCH_PUBLISHED`
- `GITHUB_PR_CREATED`
- `GITHUB_PR_REUSED`
- `GITHUB_PR_REVIEW_STARTED`
- `GITHUB_PR_REVIEW_COMPLETED`
- `GITHUB_APPROVAL_REQUESTED`
- `GITHUB_APPROVAL_CONSUMED`
- `GITHUB_MERGE_STARTED`
- `GITHUB_MERGE_COMPLETED`
- `GITHUB_POST_MERGE_VERIFIED`
- `GITHUB_DELIVERY_CANCELLED`

### Telemetry Correlation
- Every delivery is tracked in `data/deliveries.json`.
- Exposed in real-time on `GET /api/v1/overview` under `delivery_summary`.

---

## 10. CLI & REST API Reference

### ECO CLI Commands
```bash
eco github health                      # Inspect client status, rate limits, and mode
eco github mode [real|mock|dry-run]    # Switch client operational mode
eco delivery list                      # List recent software deliveries
eco delivery publish <source_branch>   # Publish candidate branch to GitHub
eco delivery pr <delivery_id>          # Create Pull Request
eco delivery review <delivery_id>      # Run multi-agent PR review
eco delivery merge <delivery_id>       # Execute 10-step governed merge
eco delivery status <delivery_id>      # Detailed pipeline status inspection
eco delivery cancel <delivery_id>      # Cancel in-flight delivery
```

### REST API Endpoints
- `GET /api/v1/github/health`: Health probe and rate-limit remaining.
- `POST /api/v1/github/mode`: Change mode (`real`, `mock`, `dry-run`).
- `POST /api/v1/github/delivery/publish`: Publish merge candidate branch.
- `POST /api/v1/github/delivery/pr`: Create Pull Request with auto-review.
- `POST /api/v1/github/delivery/review/{id}`: Run multi-agent PR review.
- `POST /api/v1/github/delivery/merge`: Execute governed merge.
- `GET /api/v1/github/delivery/deliveries`: List deliveries.
- `GET /api/v1/github/delivery/deliveries/{id}`: Fetch single delivery.
- `POST /api/v1/github/delivery/deliveries/{id}/cancel`: Cancel delivery.
- `GET /api/v1/overview`: System telemetry with `delivery_summary`.

---

## 11. Known Limitations & Boundaries

1. **Air-Gapped Default**: Without an operator-supplied `GITHUB_TOKEN`, Real GitHub mode reports `NOT_CONFIGURED`. Live network mutations are never attempted blindly.
2. **Token Scopes**: When configured, the token must possess `repo` scope to create branches and merge pull requests on private repositories.
3. **Recovery Halts**: Post-merge verification failures halt in `POST_MERGE_FAILED` rather than executing automated force-pushes or reverts, preserving default branch safety.
4. **Rate Limits**: Unauthenticated GitHub REST queries are limited to 60 req/hr by GitHub. Authenticated tokens provide 5,000 req/hr.

---

## 12. Verification & Gatekeeper Summary

- **Phase 11 Targeted Tests**: `28/28 PASSED` in [`tests/test_phase11_github_delivery.py`](file:///root/control-center/tests/test_phase11_github_delivery.py).
- **Fast Regression Suite**: `5/5 PASSED` in [`tests/test_secrets.py`](file:///root/control-center/tests/test_secrets.py) and [`tests/test_cost_guard.py`](file:///root/control-center/tests/test_cost_guard.py).
- **Production Gatekeeper**: `12/12 GATES PASSED` in [`scripts/ci_verify.py`](file:///root/control-center/scripts/ci_verify.py).
- **Primary Working Tree**: Pristine and clean.
- **Active Git Worktrees**: `0` orphaned worktrees (`git worktree list` shows only `/root/control-center [main]`).
- **Cloud Spend**: `$0.00 USD`. GCP billing unlinked. Zero secrets exposed.
