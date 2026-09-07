"""
NEXUS Autonomous Circuit Breaker Subsystem.
Provides failure containment and self-healing for agent tool executions.

States:
- CLOSED: Normal operation. Failures are counted.
- OPEN: Tripped after consecutive failure threshold. Invocations fail immediately.
- HALF_OPEN: Cooldown period elapsed. Permits test invocation to verify recovery.
"""

import time
import threading
from enum import Enum
from typing import Dict, Any, Optional, Tuple

class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitEntry:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.success_count = 0

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
        self.success_count += 1

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def can_execute(self) -> Tuple[bool, Optional[str]]:
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True, None
            remaining = round(self.recovery_timeout - (now - self.last_failure_time), 1)
            return False, f"Circuit breaker OPEN. Consecutive failures: {self.failure_count}. Cooldown remaining: {remaining}s."
        return True, None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "success_count": self.success_count
        }

class CircuitBreakerManager:
    """Central registry and policy coordinator for tool and agent circuit breakers."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self._lock = threading.Lock()
        self.default_threshold = failure_threshold
        self.default_timeout = recovery_timeout
        self._circuits: Dict[str, CircuitEntry] = {}

    def _get_or_create(self, key: str) -> CircuitEntry:
        if key not in self._circuits:
            self._circuits[key] = CircuitEntry(self.default_threshold, self.default_timeout)
        return self._circuits[key]

    def can_execute(self, key: str) -> Tuple[bool, Optional[str]]:
        with self._lock:
            circuit = self._get_or_create(key)
            return circuit.can_execute()

    def record_success(self, key: str):
        with self._lock:
            circuit = self._get_or_create(key)
            circuit.record_success()

    def record_failure(self, key: str):
        with self._lock:
            circuit = self._get_or_create(key)
            circuit.record_failure()

    def reset(self, key: Optional[str] = None):
        with self._lock:
            if key:
                if key in self._circuits:
                    self._circuits[key] = CircuitEntry(self.default_threshold, self.default_timeout)
            else:
                self._circuits.clear()

    def get_status(self, key: str) -> Dict[str, Any]:
        with self._lock:
            circuit = self._get_or_create(key)
            return circuit.to_dict()

circuit_breaker = CircuitBreakerManager()
