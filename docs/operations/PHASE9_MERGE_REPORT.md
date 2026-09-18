# NEXUS Phase 9: Swarm Branch Merge Arbitration & Cross-Session Conflict Resolution

## Executive Summary
Phase 9 delivers the autonomous **Swarm Branch Merge Arbitration & Cross-Session Conflict Resolution Engine** for NEXUS. This closes the gap between isolated concurrent swarm sessions (`swarm/<session_id>`) and safe integration into trunk branches (`main` or `integration`).

The arbitration engine executes all simulations, conflict analyses, multi-agent reviews, and pre-merge regressions strictly inside **ephemeral verification worktrees**, ensuring the user's primary working tree and uncommitted work remain **100% untouched and preserved**.

---

## Architecture & Pipeline

```
Completed Swarm Branch (`swarm/<session_id>`)
                     │
                     ▼
       Target Base Branch (`main`)
                     │
                     ▼
      [1] Native Three-Way Merge Analysis
          - git merge-base detection
          - Divergence & diff analysis
          - Overlapping file detection
          - Rename/delete & binary conflict detection
          - Sensitive/dangerous path inspection
                     │
                     ▼
      [2] Risk & Conflict Classification
          - SENSITIVE_CATEGORIES inspection (Security, Auth, IaC, DB, Core)
          - Mergeability classification (FAST_FORWARD, CLEAN_THREE_WAY, etc.)
          - High-level decision classification:
            • CLEAN_MERGE
            • AUTO_MERGEABLE
            • CONFLICTED
            • HIGH_RISK
            • VERIFICATION_FAILED
            • REQUIRES_HUMAN
            • REJECTED
                     │
                     ▼
      [3] Ephemeral Verification Worktree
          - Isolated staging worktree (`staging/<merge_id>`)
          - Pre-merge regression test execution (`pytest`)
          - Security Sentinel scan for secrets and boundary leaks
          - Candidate commit & tree identity SHA hashing
                     │
                     ▼
      [4] Multi-Agent Fleet Review (AGY ↔ Codex)
          - AGY Planner (`agent-research`): merge intent & conflict topology
          - Codex Reviewer (`agent-dev`): implementation & syntax review
          - QA Verifier (`agent-qa`): test assertions & coverage delta
          - Security Sentinel (`agent-security`): leak & boundary audit
                     │
                     ▼
      [5] Governed Trunk Integration & Staleness Protection
          - Scoped Human Approval Gate for high-risk changes
          - Anti-replay protection with scoped token execution
          - Target branch staleness detection (abort on concurrent advances)
          - Per-repository concurrency lock (`_RepoFileLock`)
          - Safe target update (preserves dirty primary working tree)
```

---

## Key Technical Protections

### 1. Deterministic Conflict Resolution Strategies
- **Fast-Forward & Clean Three-Way**: Applied deterministically when no textual conflicts exist.
- **Autonomous Agent Resolution**: Safely resolves non-colliding syntax blocks (e.g. distinct function/class additions, non-overlapping imports) without guessing.
- **Low-Confidence Collision Handling**: When conflicting logic occurs in the same function or class, arbitration halts with `confidence_sufficient=False`, marks status `REQUIRES_HUMAN`, and preserves candidate state.
- **Ours / Theirs Guardrails**: Prohibits blind resolution. `OURS` and `THEIRS` strategies require explicit policy allowance (`allow_ours_theirs=True`); otherwise, integration halts and flags `REQUIRES_HUMAN`.

### 2. Scoped Human Approval Gate & Anti-Replay
- When a candidate modifies sensitive paths (e.g., `backend/core/policy.py`, `infra/`, `.env`, migrations), it triggers the `WAITING_FOR_APPROVAL` state.
- Approvals are cryptographically and contextually scoped to the exact `candidate_commit` and `candidate_tree_sha`.
- Generic approvals cannot be replayed on arbitrary future commits.
- Upon approval integration, the approval record is atomically updated to `EXECUTED`, blocking replay attacks.

### 3. Target Branch Staleness Detection
- If the target base branch advances between initial merge analysis and final integration, the arbitrator detects commit divergence and halts with `STALE_TARGET_BRANCH`.
- Re-arbitration is required before trunk refs can be updated, preventing silent overwrite of concurrent work.

### 4. Zero-Clobber Primary Working Tree Protection
- If the target branch is currently checked out in the user's primary repository, the arbitrator checks `git status --porcelain`.
- If uncommitted user modifications are present, the merge candidate is preserved on `staging/<merge_id>` and reported as `STAGED_READY`.
- The user's uncommitted work is **never** reset, checked out, or overwritten.

---

## Verification & Audit Telemetry
- **Fast Unit & Integration Tests**: 16/16 tests passing in `tests/test_phase9_merge_arbitration.py`.
- **Full CI Gatekeeper**: 10/10 stages passing in `scripts/ci_verify.py` (including Stage 10: Swarm Branch Merge Arbitration Audit).
- **Audit Logging**: Every evaluation, execution, approval check, and rejection records structured JSON audit entries with cryptographic execution IDs.
- **FinOps Compliance**: $0.00 cloud spend maintained with GCP billing strictly unlinked.
