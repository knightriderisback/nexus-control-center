import json
import os
import uuid
import subprocess
from datetime import datetime
from typing import List, Optional
from core.config import config
from core.audit import record_audit
from core.policy import evaluate_action
from models.schemas import ApprovalRequest, ApprovalStatus, RiskLevel

def load_approvals() -> List[ApprovalRequest]:
    if not os.path.exists(config.approvals_file):
        return []
    try:
        with open(config.approvals_file, "r") as f:
            raw = json.load(f)
            return [ApprovalRequest(**item) for item in raw]
    except Exception:
        return []

def save_approvals(approvals: List[ApprovalRequest]):
    os.makedirs(os.path.dirname(config.approvals_file), exist_ok=True)
    with open(config.approvals_file, "w") as f:
        json.dump([a.model_dump() for a in approvals], f, indent=2)

def request_approval(
    action: str,
    target_project: str,
    reason: str,
    command: Optional[str] = None,
    actor: str = "agent",
    task_id: Optional[str] = None,
    risk_level: Optional[RiskLevel] = None
) -> ApprovalRequest:
    eval_risk, _, policy_desc = evaluate_action(action, target_project)
    effective_risk = risk_level if risk_level is not None else eval_risk
    
    appr = ApprovalRequest(
        id=f"appr-{uuid.uuid4().hex[:6]}",
        task_id=task_id,
        action=action,
        target_project=target_project,
        risk_level=effective_risk,
        command=command,
        actor=actor,
        reason=f"{reason} (Policy: {policy_desc})",
        timestamp=datetime.utcnow().isoformat() + "Z",
        status=ApprovalStatus.PENDING
    )
    
    all_apprs = load_approvals()
    all_apprs.insert(0, appr)
    save_approvals(all_apprs)

    record_audit(
        action=f"APPROVAL_REQUESTED: {action}",
        project=target_project,
        target=command or action,
        reason=reason,
        risk_level=effective_risk,
        result="PENDING_APPROVAL",
        actor=actor,
        approval_id=appr.id
    )

    return appr

def decide_approval(approval_id: str, decision: str, user: str = "human_operator", decided_by: Optional[str] = None) -> ApprovalRequest:
    effective_user = decided_by if decided_by is not None else user
    all_apprs = load_approvals()
    appr = next((a for a in all_apprs if a.id == approval_id), None)
    if not appr:
        raise ValueError(f"Approval request {approval_id} not found")

    if appr.status != ApprovalStatus.PENDING:
        raise ValueError(f"Approval request {approval_id} is already {appr.status.value}. Replay blocked.")

    if decision.upper() == "APPROVED":
        appr.status = ApprovalStatus.APPROVED
        appr.approved_by = effective_user
        appr.decided_at = datetime.utcnow().isoformat() + "Z"
        
        # Execute action if executable non-comment command exists
        exec_output = ""
        exec_err = None
        if appr.command and not appr.command.strip().startswith("#"):
            try:
                res = subprocess.run(appr.command, shell=True, capture_output=True, text=True, timeout=60)
                exec_output = res.stdout
                if res.returncode != 0:
                    exec_err = res.stderr
                appr.status = ApprovalStatus.EXECUTED
            except Exception as e:
                exec_err = str(e)

        record_audit(
            action=f"APPROVAL_GRANTED: {appr.action}",
            project=appr.target_project,
            target=appr.command or appr.action,
            reason=f"Approved by {effective_user}",
            risk_level=appr.risk_level,
            result="EXECUTED" if not exec_err else "EXEC_ERROR",
            actor=effective_user,
            user=effective_user,
            approval_id=appr.id,
            error=exec_err
        )
    else:
        appr.status = ApprovalStatus.REJECTED
        appr.approved_by = effective_user
        appr.decided_at = datetime.utcnow().isoformat() + "Z"

        record_audit(
            action=f"APPROVAL_REJECTED: {appr.action}",
            project=appr.target_project,
            target=appr.command or appr.action,
            reason=f"Rejected by {effective_user}",
            risk_level=appr.risk_level,
            result="REJECTED",
            actor=effective_user,
            user=effective_user,
            approval_id=appr.id
        )

    save_approvals(all_apprs)
    return appr
