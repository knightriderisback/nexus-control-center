from fastapi import APIRouter
from typing import List, Optional
from models.schemas import AuditEvent
from core.audit import get_recent_audit_events

router = APIRouter(prefix="/audit", tags=["Audit Trail"])

@router.get("", response_model=List[AuditEvent])
def query_audit_trail(limit: int = 50, project: Optional[str] = None):
    return get_recent_audit_events(limit=limit, project=project)
