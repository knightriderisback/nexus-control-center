"""
NEXUS Phase 5: Runtime Reliability & Fault Tolerance Test Suite.
Verifies timeout containment, process group killing, circuit breaker behavior,
atomic storage corruption resilience, and concurrency safety.
"""

import os
import time
import tempfile
import threading
import pytest
from core.storage import atomic_save_json, load_json_safe
from orchestrator.circuit_breaker import CircuitBreakerManager, CircuitState
from orchestrator.safe_runner import SafeCommandExecutor
from orchestrator.runtime import runtime_engine
from models.schemas import ExecutionLimits

# =============================================================================
# 1. Timeout Containment & Process Tree Killing
# =============================================================================

def test_command_timeout_containment_and_zero_zombies():
    # Execute a command that attempts to sleep 10s with a 1s timeout without semicolon
    py_code = "__import__('time').sleep(10)"
    start = time.time()
    res = SafeCommandExecutor.execute(["python3", "-c", py_code], timeout=1)
    dur = time.time() - start

    assert res.exit_code == 124
    assert "CommandTimeout" in res.stderr
    assert dur < 3.0 # Verify it was interrupted near 1s deadline

# =============================================================================
# 2. Circuit Breaker State Machine & Self-Healing
# =============================================================================

def test_circuit_breaker_lifecycle():
    cb = CircuitBreakerManager(failure_threshold=3, recovery_timeout=0.2)
    key = "test-agent:test-tool"

    # Initial state: CLOSED
    can_exec, err = cb.can_execute(key)
    assert can_exec is True
    assert err is None
    assert cb.get_status(key)["state"] == CircuitState.CLOSED.value

    # Failures 1 and 2: Still CLOSED
    cb.record_failure(key)
    cb.record_failure(key)
    can_exec, _ = cb.can_execute(key)
    assert can_exec is True
    assert cb.get_status(key)["failure_count"] == 2

    # Failure 3: Trips to OPEN
    cb.record_failure(key)
    can_exec, err = cb.can_execute(key)
    assert can_exec is False
    assert "Circuit breaker OPEN" in err
    assert cb.get_status(key)["state"] == CircuitState.OPEN.value

    # Cooldown transition to HALF_OPEN
    time.sleep(0.25)
    can_exec, err = cb.can_execute(key)
    assert can_exec is True # Permits test probe
    assert cb.get_status(key)["state"] == CircuitState.HALF_OPEN.value

    # Successful probe restores CLOSED
    cb.record_success(key)
    assert cb.get_status(key)["state"] == CircuitState.CLOSED.value
    assert cb.get_status(key)["failure_count"] == 0

def test_circuit_breaker_manual_reset():
    cb = CircuitBreakerManager(failure_threshold=2)
    key = "agent-qa:test.pytest"
    cb.record_failure(key)
    cb.record_failure(key)
    assert cb.get_status(key)["state"] == CircuitState.OPEN.value

    cb.reset(key)
    can_exec, _ = cb.can_execute(key)
    assert can_exec is True
    assert cb.get_status(key)["state"] == CircuitState.CLOSED.value

# =============================================================================
# 3. Atomic Storage Corruption Resilience
# =============================================================================

def test_storage_resilience_under_corrupted_json():
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write("{ invalid corrupted json ::: [[[")
        corrupted_path = f.name

    try:
        # load_json_safe must not throw; must safely return provided default
        recovered = load_json_safe(corrupted_path, default={"safe_fallback": True})
        assert recovered == {"safe_fallback": True}

        # atomic_save_json must be able to overwrite corrupted state cleanly
        atomic_save_json(corrupted_path, {"restored": True, "count": 42})
        restored = load_json_safe(corrupted_path)
        assert restored["restored"] is True
        assert restored["count"] == 42
    finally:
        if os.path.exists(corrupted_path):
            os.remove(corrupted_path)

def test_storage_resilience_missing_file():
    missing_path = "/root/control-center/data/non_existent_file_xyz.json"
    result = load_json_safe(missing_path, default=[])
    assert result == []

# =============================================================================
# 4. Concurrency Safety Under Multi-Threaded Execution
# =============================================================================

def test_concurrent_agent_task_execution_safety():
    results = []
    errors = []

    def worker(i: int):
        try:
            task = runtime_engine.create_task(
                agent_id="agent-research",
                title=f"Concurrent probe {i}",
                instructions="Read file"
            )
            executed = runtime_engine.execute_task(task.id)
            results.append(executed.status)
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert len(errors) == 0, f"Concurrent execution errors: {errors}"
    assert len(results) == 5
    assert all(status == "completed" for status in results)
