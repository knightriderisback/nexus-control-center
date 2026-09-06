import pytest
from core.approvals import request_approval, decide_approval, load_approvals
from models.schemas import RiskLevel, ApprovalStatus

def test_create_and_decide_approval():
    appr = request_approval(
        action="TEST_DEPLOY",
        target_project="portfolio",
        risk_level=RiskLevel.HIGH,
        reason="Automated test approval gate validation",
        actor="test_runner"
    )
    assert appr.id.startswith("appr-")
    assert appr.status == ApprovalStatus.PENDING

    # Approve
    decided = decide_approval(appr.id, "APPROVED", decided_by="test_admin")
    assert decided.status == ApprovalStatus.APPROVED
    assert decided.approved_by == "test_admin"

def test_reject_approval():
    appr = request_approval(
        action="TEST_DELETE",
        target_project="control-center",
        risk_level=RiskLevel.CRITICAL,
        reason="Testing rejection path",
        actor="test_runner"
    )
    decided = decide_approval(appr.id, "REJECTED", decided_by="test_admin")
    assert decided.status == ApprovalStatus.REJECTED
