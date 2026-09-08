# Approval Engine Adversarial Attack Audit

## 1. Overview
The approval subsystem (`backend/core/approvals.py`) serves as the core policy enforcement gateway for MEDIUM, HIGH, and CRITICAL risk operations. This document details empirical attacks executed against the approval state machine.

Protected baseline: Approval `appr-339c07` remained preserved and untouched in `PENDING` state throughout all test passes.

---

## 2. Attack Vectors Evaluated

### 2.1 State Machine Integrity & Anti-Replay
- **Approve after Approve**: Throws `ValueError: already APPROVED`. Replay blocked.
- **Reject after Reject**: Throws `ValueError: already REJECTED`. Replay blocked.
- **Approve after Reject**: Blocked.
- **Reject after Approve**: Blocked.
- **Expiry Invalidation**: Approvals with past TTL timestamps (`expires_at < now`) transition to `EXPIRED` and reject decisions.

### 2.2 Brute-Force & Rate Limiting
- Evaluated token guessing with 5 successive invalid HMAC tokens.
- Result: Approval status locks out on attempt 5; subsequent attempts rejected with rate-limit failure and logged as `RATE_LIMIT_EXCEEDED`.

### 2.3 Timing Attack Mitigation
- Token verification utilizes `hmac.compare_digest` to ensure constant-time secret evaluation.

### 2.4 Concurrent Decision Locking
- All read-modify-write operations on the approval database are guarded by a process-wide `threading.Lock` (`_approval_lock`), preventing race conditions.

---

## 3. Capability Status

| Capability | Status | Empirical Proof |
| :--- | :--- | :--- |
| Approval State Machine | REAL | `tests/test_approvals.py`, `tests/test_phase5_adversarial.py` |
| Anti-Replay Defense | REAL | Verified with duplicate decision calls |
| Token Expiry / TTL | REAL | Verified with expired timestamp fixtures |
| Rate-Limiting Lockout | REAL | 5-attempt limit tested and verified |
| Constant-Time HMAC Verification | REAL | `hmac.compare_digest` verified |
