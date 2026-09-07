# NEXUS Runtime Reliability, Resilience & Circuit Breakers

## Overview
This operational guide details the mechanisms ensuring execution stability, fault containment, concurrency safety, and recovery within the Personal Engineering OS control plane.

---

## 1. Circuit Breaker Pattern

To prevent cascading failures or runaway agent retry loops, the runtime implements a dedicated `CircuitBreakerManager` (`backend/orchestrator/circuit_breaker.py`).

### 1.1 State Machine Lifecycle
```
+-------------+      3 consecutive failures      +-------------+
|   CLOSED    | -------------------------------> |    OPEN     |
| (Normal Ops)|                                  | (Tripped)   |
+-------------+                                  +-------------+
       ^                                                |
       |  Success                                       | 30s Cooldown
       |                                                v
+-------------+             Probe Fails          +-------------+
|  HALF_OPEN  | <------------------------------- |  HALF_OPEN  |
|  (Testing)  | -------------------------------> |  (Cooldown) |
+-------------+                                  +-------------+
```

1. **CLOSED**: Normal operation. Tool calls execute unhindered.
2. **OPEN**: Upon recording 3 consecutive failures for a specific `(agent_id, tool_id)` pair, the circuit trips. Subsequent requests are blocked instantly with:
   `Circuit breaker OPEN for agent:tool. Tripped until <time>. Execution halted.`
3. **HALF_OPEN**: After a 30-second cooldown, a single probe request is permitted.
   - If the probe succeeds: State reverts to `CLOSED` and failure counter resets.
   - If the probe fails: State immediately reverts to `OPEN` for another cooldown cycle.
4. **Manual Override**: Operators can reset circuits via `circuit_breaker.reset(key)`.

---

## 2. Process Group Isolation & Resource Containment

### 2.1 Timeout Guarantees
Every external command runs under explicit timeouts (10s for git, 15s for file tools, 60s for pytest, 30s for shell). When a timeout expires:
- The runner issues `SIGKILL` to the entire process group (`os.killpg(os.getpgid(proc.pid), signal.SIGKILL)`).
- Subprocesses and child trees are cleaned up completely, preventing zombie processes.

### 2.2 Memory Bomb Mitigation
To prevent memory exhaustion attacks or infinite command streams from crashing the control plane, stdout capture is bounded to 500 KB (500,000 characters).

---

## 3. Storage Resilience & Concurrency Safety

### 3.1 Atomic File Storage
The control plane avoids partial writes and race conditions during persistence:
- `atomic_save_json()` writes payloads to a temporary file in the same filesystem directory and executes an atomic POSIX rename (`os.replace`).
- `load_json_safe()` intercepts corrupted JSON or non-existent files, returning an empty collection or default structure without raising uncaught runtime exceptions.

### 3.2 Thread-Safe Synchronization
- Approvals are guarded by `_approval_lock` across all read-modify-write operations.
- Telemetry metrics are guarded by `_collector_lock`.
- Multithreaded test suites verify that concurrent agent dispatches execute without thread collisions or state corruption.

---

## 4. Empirical Agent Execution Verification

### 4.1 Developer Agent Lifecycle & Clean Rollback
Empirically validated on dedicated fixture repository `data/fixtures/fixture-calculator`:
1. **INSPECT**: Reads git working tree status via `git.status`.
2. **PLAN**: Synthesizes formal `AgentPlan` with step rationale.
3. **READ**: Inspects target source code (`calculator.py`).
4. **MODIFY**: Implements fix in safe fixture.
5. **TEST**: Runs `test.pytest` to verify fix passes tests.
6. **DIFF**: Extracts unified diff via `git.diff`.
7. **ROLLBACK**: When configured or when tests fail, issues `git checkout .` and `git clean -fd`, restoring the working tree to a 100% clean baseline.

### 4.2 QA Agent Framework Discovery & Parsing
Empirically validated on passing and failing test fixtures:
- Automatically detects test framework (`pytest`).
- Parses test stdout into structured results: `status` (PASSED/FAILED), `passed` count, `failed` count, duration.

### 4.3 Security Agent Triaged Findings
Empirically validated on credential leak test fixture `data/fixtures/fixture-security`:
- Detects safe dummy RSA test key via regex pattern.
- Partitions findings into three distinct, non-fabricated tiers:
  - `REAL_FINDING`: Detected live exposed private key.
  - `INFORMATIONAL`: CORS restricted to explicit origins.
  - `UNAVAILABLE_CHECK`: Dependency scanner `pip-audit` missing from environment.
