import pytest
from core.policy import policy_engine
from models.schemas import RiskLevel

def test_policy_engine_rules_loaded():
    assert len(policy_engine.rules) >= 9
    rule_ids = [r.id for r in policy_engine.rules]
    assert "pol-001" in rule_ids # Absolute isolation
    assert "pol-002" in rule_ids # Zero static SA keys
    assert "pol-003" in rule_ids # Destructive deletion approval gate
    assert "pol-004" in rule_ids # Production deployment approval gate

def test_safe_read_actions():
    eval_result = policy_engine.evaluate_action("git:status", "portfolio")
    assert eval_result.risk_level == RiskLevel.LOW
    assert eval_result.requires_approval is False

def test_destructive_actions_require_approval():
    eval_result = policy_engine.evaluate_action("rm -rf /var/data", "portfolio")
    assert eval_result.risk_level == RiskLevel.CRITICAL
    assert eval_result.requires_approval is True

def test_production_deployment_requires_approval():
    eval_result = policy_engine.evaluate_action("deploy_production", "portfolio")
    assert eval_result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert eval_result.requires_approval is True

def test_absolute_isolation_rule_blocks_legacy():
    eval_result = policy_engine.evaluate_action("deploy", "protyourfolio")
    assert eval_result.risk_level == RiskLevel.CRITICAL
    assert eval_result.requires_approval is True
