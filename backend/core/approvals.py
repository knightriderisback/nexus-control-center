import json
import os
import uuid
import secrets
import hashlib
import hmac
import threading
import subprocess
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from core.config import config
from core.audit import record_audit
from core.policy import evaluate_action
from models.schemas import ApprovalRequest, ApprovalStatus, RiskLevel
from core.storage import atomic_save_json, load_json_safe

_approval_lock = threading.Lock()

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _now_iso() -> str:
    return _now_utc().isoformat()

def load_approvals() -> List[ApprovalRequest]:
    raw = load_json_safe(config.approvals_file, default=[])
    try:
        return [ApprovalRequest(**item) for item in raw]
    except Exception:
        return []

def save_approvals(approvals: List[ApprovalRequest]):
    # Strip raw token before persisting to disk so secret tokens never leak in storage
    sanitized = []
    for a in approvals:
        dump = a.model_dump()
        dump["token"] = None
        sanitized.append(dump)
    atomic_save_json(config.approvals_file, sanitized)

def request_approval(
    action: str,
    target_project: str,
    reason: str,
    command: Optional[str] = None,
    actor: str = "agent",
    task_id: Optional[str] = None,
    risk_level: Optional[RiskLevel] = None,
    ttl_seconds: Optional[int] = None
) -> ApprovalRequest:
    with _approval_lock:
        eval_risk, _, policy_desc = evaluate_action(action, target_project)
        effective_risk = risk_level if risk_level is not None else eval_risk

        # Cryptographically secure random token (32 bytes entropy)
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        ttl = ttl_seconds or config.token_ttl_seconds
        created_at_dt = _now_utc()
        expires_at_dt = created_at_dt + timedelta(seconds=ttl)

        appr = ApprovalRequest(
            id=f"appr-{uuid.uuid4().hex[:6]}",
            task_id=task_id,
            action=action,
            target_project=target_project,
            risk_level=effective_risk,
            command=command,
            actor=actor,
            reason=f"{reason} (Policy: {policy_desc})",
            timestamp=_now_iso(),
            created_at=_now_iso(),
            expires_at=expires_at_dt.isoformat(),
            ttl_seconds=ttl,
            token_hash=token_hash,
            token=raw_token, # Available in-memory for the immediate requester
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

def decide_approval(
    approval_id: str,
    decision: str,
    user: str = "human_operator",
    decided_by: Optional[str] = None,
    token: Optional[str] = None,
    expected_action: Optional[str] = None,
    expected_actor: Optional[str] = None,
    require_token: bool = False
) -> ApprovalRequest:
    effective_user = decided_by if decided_by is not None else user

    with _approval_lock:
        all_apprs = load_approvals()
        appr = next((a for a in all_apprs if a.id == approval_id), None)
        if not appr:
            raise ValueError(f"Approval request {approval_id} not found")

        # 1. State check & Replay prevention
        if appr.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval request {approval_id} is already {appr.status.value}. Replay blocked.")

        # 2. Expiry / TTL validation
        if appr.expires_at:
            try:
                exp_dt = datetime.fromisoformat(appr.expires_at.replace("Z", "+00:00"))
                if _now_utc() > exp_dt:
                    appr.status = ApprovalStatus.EXPIRED
                    appr.decided_at = _now_iso()
                    save_approvals(all_apprs)
                    record_audit(
                        action=f"APPROVAL_EXPIRED: {appr.action}",
                        project=appr.target_project,
                        target=appr.command or appr.action,
                        reason="Approval token expired before decision was submitted",
                        risk_level=appr.risk_level,
                        result="EXPIRED",
                        actor=effective_user,
                        approval_id=appr.id
                    )
                    raise ValueError(f"Approval request {approval_id} has expired (TTL {appr.ttl_seconds}s). Decision blocked.")
            except (ValueError, TypeError) as parse_err:
                if "has expired" in str(parse_err):
                    raise parse_err

        # Check failed attempts threshold (lock after 5 attempts)
        if getattr(appr, "failed_attempts", 0) >= 5:
            record_audit(
                action=f"APPROVAL_LOCKED: {appr.action}",
                project=appr.target_project,
                target=appr.id,
                reason="Approval request locked due to excessive failed token attempts (rate limit exceeded)",
                risk_level=RiskLevel.CRITICAL,
                result="RATE_LIMITED",
                actor=effective_user,
                approval_id=appr.id
            )
            raise ValueError(f"Approval request {approval_id} is locked due to excessive failed token attempts (rate limit exceeded).")

        # 3. Token verification & Guessing defense
        if require_token or token is not None:
            if not token or not token.strip():
                raise ValueError(f"Approval token required for request {approval_id}")
            if appr.token_hash:
                calc_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
                if not hmac.compare_digest(calc_hash, appr.token_hash):
                    appr.failed_attempts = getattr(appr, "failed_attempts", 0) + 1
                    save_approvals(all_apprs)
                    record_audit(
                        action=f"APPROVAL_TOKEN_MISMATCH: {appr.action}",
                        project=appr.target_project,
                        target=appr.id,
                        reason=f"Invalid approval token submitted - attempt {appr.failed_attempts}/5",
                        risk_level=RiskLevel.HIGH,
                        result="SECURITY_VIOLATION",
                        actor=effective_user,
                        approval_id=appr.id
                    )
                    raise ValueError("Invalid approval token. Verification failed.")

        # 4. Action & Actor constraint checks
        if expected_action and expected_action != appr.action:
            raise ValueError(f"Action mismatch: expected '{expected_action}', approval is for '{appr.action}'")

        if expected_actor and expected_actor != appr.actor:
            raise ValueError(f"Actor mismatch: expected '{expected_actor}', request was made by '{appr.actor}'")

        # 5. Prevent double execution
        if appr.executed_at is not None:
            raise ValueError(f"Action for {approval_id} has already been executed at {appr.executed_at}.")

        # 6. Apply Decision
        now_str = _now_iso()
        if decision.upper() == "APPROVED":
            appr.status = ApprovalStatus.APPROVED
            appr.approved_by = effective_user
            appr.decided_at = now_str

            # Execute action if non-comment command exists via SafeCommandExecutor
            exec_output = ""
            exec_err = None
            if appr.command and not appr.command.strip().startswith("#"):
                import shlex
                from orchestrator.safe_runner import SafeCommandExecutor
                try:
                    cmd_tokens = shlex.split(appr.command.strip())
                    cmd_res = SafeCommandExecutor.execute(
                        cmd_tokens,
                        cwd=config.base_dir,
                        timeout=60,
                        actor=effective_user
                    )
                    exec_output = cmd_res.stdout
                    if cmd_res.exit_code != 0:
                        exec_err = cmd_res.stderr or f"Exit code {cmd_res.exit_code}"
                    appr.status = ApprovalStatus.EXECUTED
                    appr.executed_at = now_str
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
            appr.decided_at = now_str

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
