from fastapi import APIRouter
from core.cost_guard import cost_guard

router = APIRouter(prefix="/cost", tags=["Cost Guard"])

@router.get("/status")
def get_cost_status():
    """Returns current spend, free tier utilization, and billing guardrails."""
    return cost_guard.get_status()

@router.post("/evaluate")
def evaluate_service_cost(payload: dict):
    """Evaluates whether deploying/calling a service complies with cost constraints."""
    service = payload.get("service", "")
    action = payload.get("action", "")
    return cost_guard.evaluate_cost_risk(service, action)
