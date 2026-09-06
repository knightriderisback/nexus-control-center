import json
import os
import re
from typing import Tuple, List, NamedTuple
from core.config import config
from models.schemas import RiskLevel, PolicyRule

class EvaluationResult(NamedTuple):
    risk_level: RiskLevel
    requires_approval: bool
    description: str

DEFAULT_RULES: List[PolicyRule] = [
    PolicyRule(
        id="pol-000",
        name="Absolute Legacy Project Isolation",
        action_pattern=r"(?i)(protyourfolio|whatsapp-autopost-by-termux|gen-lang-client-0352285705)",
        risk_level=RiskLevel.CRITICAL,
        requires_approval=True,
        description="Legacy projects are strictly isolated and protected from mutation."
    ),
    PolicyRule(
        id="pol-001",
        name="Destructive File System / Database Wipe",
        action_pattern=r"(?i)(rm\s+-rf|drop\s+database|wipe|format|truncate\s+table)",
        risk_level=RiskLevel.CRITICAL,
        requires_approval=True,
        description="Destructive deletion or database drop requires explicit human approval."
    ),
    PolicyRule(
        id="pol-002",
        name="Billing Changes & Account Linking",
        action_pattern=r"(?i)(billing\s+accounts\s+link|billing\s+update|modify\s+billing)",
        risk_level=RiskLevel.CRITICAL,
        requires_approval=True,
        description="Billing configuration changes have direct financial implications."
    ),
    PolicyRule(
        id="pol-003",
        name="Credential & Secret Key Creation",
        action_pattern=r"(?i)(service-accounts\s+keys\s+create|generate\s+private\s+key|export\s+secret)",
        risk_level=RiskLevel.CRITICAL,
        requires_approval=True,
        description="Static key creation violates zero-trust posture and requires explicit signoff."
    ),
    PolicyRule(
        id="pol-004",
        name="Production Cloud Run / GCP Deployment",
        action_pattern=r"(?i)(run\s+deploy|deploy\s+production|push\s+image|terraform\s+apply|deploy)",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        description="Production infrastructure deployments must be verified and cleared by the operator."
    ),
    PolicyRule(
        id="pol-005",
        name="IAM Role & Policy Modification",
        action_pattern=r"(?i)(add-iam-policy-binding|set-iam-policy|grant\s+permission|roles/owner)",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        description="Privilege escalations and policy changes require review."
    ),
    PolicyRule(
        id="pol-006",
        name="Git Force Push / Branch Deletion",
        action_pattern=r"(?i)(git\s+push\s+--force|git\s+branch\s+-D|git\s+reset\s+--hard)",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        description="Destructive git operations may overwrite history."
    ),
    PolicyRule(
        id="pol-007",
        name="Git Commit / Branch Creation / PR",
        action_pattern=r"(?i)(git\s+commit|git\s+checkout\s+-b|create\s+pr|git\s+push)",
        risk_level=RiskLevel.MEDIUM,
        requires_approval=False,
        description="Normal development workflow actions run within guardrails."
    ),
    PolicyRule(
        id="pol-008",
        name="Dependency Installation",
        action_pattern=r"(?i)(pip\s+install|npm\s+install|apt-get\s+install)",
        risk_level=RiskLevel.MEDIUM,
        requires_approval=False,
        description="Installing packages locally runs with medium risk."
    ),
    PolicyRule(
        id="pol-009",
        name="Read-Only Audits, Inspections, Tests",
        action_pattern=r"(?i)(status|test|audit|list|describe|get|view|cat|curl|scan)",
        risk_level=RiskLevel.LOW,
        requires_approval=False,
        description="Read-only operations and telemetry queries execute autonomously."
    )
]

def load_policy_rules() -> List[PolicyRule]:
    os.makedirs(os.path.dirname(config.policies_file), exist_ok=True)
    if not os.path.exists(config.policies_file):
        with open(config.policies_file, "w") as f:
            json.dump([r.model_dump() for r in DEFAULT_RULES], f, indent=2)
        return DEFAULT_RULES
    try:
        with open(config.policies_file, "r") as f:
            raw = json.load(f)
            return [PolicyRule(**item) for item in raw]
    except Exception:
        return DEFAULT_RULES

def evaluate_action(action: str, target: str = "") -> EvaluationResult:
    rules = load_policy_rules()
    combined = f"{action} {target}".strip()

    # Check from most severe to least
    for rule in rules:
        if re.search(rule.action_pattern, combined):
            return EvaluationResult(rule.risk_level, rule.requires_approval, rule.description)

    # Default fallback: safe heuristic
    if any(k in combined.lower() for k in ["delete", "drop", "purge", "destroy"]):
        return EvaluationResult(RiskLevel.HIGH, True, "Destructive keyword detected in unmapped command.")
    elif any(k in combined.lower() for k in ["deploy", "publish", "release"]):
        return EvaluationResult(RiskLevel.HIGH, True, "Deployment operation detected.")
    elif any(k in combined.lower() for k in ["write", "create", "modify", "update"]):
        return EvaluationResult(RiskLevel.MEDIUM, False, "State-modifying action within standard boundaries.")

    return EvaluationResult(RiskLevel.LOW, False, "Standard autonomous operation.")

class PolicyEngine:
    @property
    def rules(self) -> List[PolicyRule]:
        return load_policy_rules()

    def evaluate_action(self, action: str, target: str = "") -> EvaluationResult:
        return evaluate_action(action, target)

policy_engine = PolicyEngine()
