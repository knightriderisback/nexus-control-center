from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
from models.schemas import PolicyRule, RiskLevel
from core.policy import load_policy_rules, evaluate_action

router = APIRouter(prefix="/policy", tags=["Central Policy Engine"])

class EvaluateRequest(BaseModel):
    action: str
    target: str = ""

@router.get("", response_model=List[PolicyRule])
@router.get("/rules", response_model=List[PolicyRule])
def list_rules():
    return load_policy_rules()

@router.post("/evaluate")
def evaluate(req: EvaluateRequest):
    risk, req_appr, desc = evaluate_action(req.action, req.target)
    return {
        "action": req.action,
        "target": req.target,
        "risk_level": risk,
        "requires_human_approval": req_appr,
        "policy_reason": desc
    }
