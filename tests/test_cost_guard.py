from core.cost_guard import cost_guard
from models.schemas import RiskLevel

def test_cost_guard_unlinked_billing():
    status = cost_guard.get_status()
    assert status["billing_account_linked"] is False
    assert status["strict_zero_cost_enforced"] is True
    assert status["current_month_spend_usd"] == 0.0

def test_cost_guard_blocks_paid_service_creation():
    eval_res = cost_guard.evaluate_cost_risk("compute.googleapis.com", "create_instance")
    assert eval_res["allowed"] is False
    assert eval_res["risk"] == RiskLevel.CRITICAL

def test_cost_guard_permits_free_read():
    eval_res = cost_guard.evaluate_cost_risk("logging.googleapis.com", "read_logs")
    assert eval_res["allowed"] is True
    assert eval_res["risk"] == RiskLevel.LOW
