"""
NEXUS Observability & Tracing Engine.
OpenTelemetry-compatible telemetry, correlation tracking, structured logging,
and in-memory ring buffer for traces & system metrics.
"""

import time
import uuid
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# -----------------------------------------------------------------------------
# Structured JSON Formatter
# -----------------------------------------------------------------------------
class StructuredLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "N/A"),
            "trace_id": getattr(record, "trace_id", "N/A"),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

# -----------------------------------------------------------------------------
# Metrics & Traces Storage (In-memory ring buffers)
# -----------------------------------------------------------------------------
class ObservabilityCollector:
    def __init__(self, max_traces: int = 300):
        self.max_traces = max_traces
        self.traces: deque = deque(maxlen=max_traces)
        self.request_count = 0
        self.error_count = 0
        self.status_codes: Dict[int, int] = {}
        self.endpoint_latencies: Dict[str, List[float]] = {}
        self.agent_runs: Dict[str, Dict[str, int]] = {}
        self.start_time = time.time()

    def record_trace(
        self,
        trace_id: str,
        span_id: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        correlation_id: str
    ):
        trace_entry = {
            "trace_id": trace_id,
            "span_id": span_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "correlation_id": correlation_id
        }
        self.traces.appendleft(trace_entry)
        
        # Update metrics
        self.request_count += 1
        if status_code >= 400:
            self.error_count += 1
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        
        if path not in self.endpoint_latencies:
            self.endpoint_latencies[path] = []
        if len(self.endpoint_latencies[path]) > 50:
            self.endpoint_latencies[path].pop(0)
        self.endpoint_latencies[path].append(round(duration_ms, 2))

    def record_agent_metric(
        self,
        agent_id: str,
        status: str,
        duration_ms: float = 0.0,
        tool_calls: int = 0,
        approval_waits: int = 0,
        rejected_executions: int = 0,
        errors: int = 0,
        provider_used: str = "MockEngine"
    ):
        if agent_id not in self.agent_runs:
            self.agent_runs[agent_id] = {
                "execution_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "total_duration_ms": 0.0,
                "tool_calls": 0,
                "approval_waits": 0,
                "rejected_executions": 0,
                "errors": 0,
                "providers_used": {},
                # Backward compatibility keys
                "total": 0,
                "success": 0,
                "failed": 0
            }

        rec = self.agent_runs[agent_id]
        rec["execution_count"] += 1
        rec["total"] += 1
        rec["total_duration_ms"] += round(duration_ms, 2)
        rec["tool_calls"] += tool_calls
        rec["approval_waits"] += approval_waits
        rec["rejected_executions"] += rejected_executions
        rec["errors"] += errors

        prov_counts = rec["providers_used"]
        prov_counts[provider_used] = prov_counts.get(provider_used, 0) + 1

        if status.upper() in ["COMPLETED", "SUCCESS"]:
            rec["success_count"] += 1
            rec["success"] += 1
        else:
            rec["failure_count"] += 1
            rec["failed"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        uptime_seconds = round(time.time() - self.start_time, 1)
        avg_latencies = {}
        for path, lat_list in self.endpoint_latencies.items():
            avg_latencies[path] = round(sum(lat_list) / len(lat_list), 2) if lat_list else 0.0

        return {
            "uptime_seconds": uptime_seconds,
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate_pct": round((self.error_count / self.request_count * 100), 2) if self.request_count else 0.0,
            "status_codes": self.status_codes,
            "endpoint_avg_latencies_ms": avg_latencies,
            "agent_metrics": self.agent_runs,
            "trace_buffer_depth": len(self.traces)
        }

    def get_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self.traces)[:limit]

collector = ObservabilityCollector()

# -----------------------------------------------------------------------------
# Tracing & Correlation Middleware
# -----------------------------------------------------------------------------
class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:8]}"
        trace_id = f"trace-{uuid.uuid4().hex[:16]}"
        span_id = f"span-{uuid.uuid4().hex[:8]}"

        request.state.correlation_id = correlation_id
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request.state.span_id = span_id

        start_time = time.time()
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000.0
            collector.record_trace(
                trace_id=trace_id,
                span_id=span_id,
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
                correlation_id=correlation_id
            )
            raise exc

        duration_ms = (time.time() - start_time) * 1000.0

        # Don't clutter trace logs with websocket or static asset polling
        if not request.url.path.startswith("/assets") and request.url.path != "/ws":
            collector.record_trace(
                trace_id=trace_id,
                span_id=span_id,
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                correlation_id=correlation_id
            )

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

        return response
