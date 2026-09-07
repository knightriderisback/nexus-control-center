import json
import os
import re
import uuid
from datetime import datetime
from typing import List, Optional
from core.config import config
from models.schemas import AuditEvent, RiskLevel

def sanitize_text(text: str) -> str:
    if not text:
        return text
    clean = text
    clean = re.sub(r'(?i)(key|token|secret|password|auth|bearer)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', r'\1: [REDACTED_SECRET]', clean)
    clean = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED_GEMINI_KEY]', clean)
    clean = re.sub(r'gh[pousr]_[0-9A-Za-z]{36}', '[REDACTED_GITHUB_TOKEN]', clean)
    clean = re.sub(r'ya29\.[0-9A-Za-z-_]+', '[REDACTED_OAUTH_TOKEN]', clean)
    return clean

def record_audit(
    action: str,
    project: str,
    target: str,
    reason: str,
    risk_level: RiskLevel,
    result: str = "SUCCESS",
    actor: str = "operator",
    agent: Optional[str] = None,
    agent_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    tool_id: Optional[str] = None,
    status: Optional[str] = None,
    result_summary: Optional[str] = None,
    user: str = "operator",
    approval_id: Optional[str] = None,
    error: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> AuditEvent:
    os.makedirs(os.path.dirname(config.audit_log_file), exist_ok=True)
    
    effective_agent = agent or agent_id
    effective_status = status or result

    event = AuditEvent(
        id=f"audit-{uuid.uuid4().hex[:8]}",
        correlation_id=correlation_id or f"corr-{uuid.uuid4().hex[:6]}",
        timestamp=datetime.utcnow().isoformat() + "Z",
        actor=actor,
        agent=effective_agent,
        agent_id=agent_id or agent,
        execution_id=execution_id,
        tool_id=tool_id,
        user=user,
        action=sanitize_text(action),
        project=project,
        target=sanitize_text(target),
        reason=sanitize_text(reason),
        risk_level=risk_level,
        approval_id=approval_id,
        result=result,
        status=effective_status,
        result_summary=sanitize_text(result_summary) if result_summary else None,
        error=sanitize_text(error) if error else None
    )

    with open(config.audit_log_file, "a") as f:
        f.write(event.model_dump_json() + "\n")

    return event

def get_recent_audit_events(limit: int = 100, project: Optional[str] = None) -> List[AuditEvent]:
    if not os.path.exists(config.audit_log_file):
        return []
    
    events: List[AuditEvent] = []
    try:
        with open(config.audit_log_file, "r") as f:
            lines = f.readlines()
            for line in reversed(lines):
                if not line.strip():
                    continue
                data = json.loads(line)
                if project and data.get("project") != project:
                    continue
                events.append(AuditEvent(**data))
                if len(events) >= limit:
                    break
    except Exception as e:
        print(f"Error reading audit log: {e}")
    return events
