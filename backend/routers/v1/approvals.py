from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from models.schemas import ApprovalRequest, ApprovalStatus
from core.approvals import load_approvals, decide_approval

router = APIRouter(prefix="/approvals", tags=["Human Approval Gate"])

class DecisionPayload(BaseModel):
    decision: str # APPROVED or REJECTED
    user: Optional[str] = "human_operator"

@router.get("", response_model=List[ApprovalRequest])
def list_approvals(status: Optional[str] = None):
    apprs = load_approvals()
    if status:
        return [a for a in apprs if a.status.value == status.upper()]
    return apprs

@router.post("/{approval_id}/decide", response_model=ApprovalRequest)
def decide(approval_id: str, payload: DecisionPayload):
    try:
        updated = decide_approval(approval_id, payload.decision, payload.user or "human_operator")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
