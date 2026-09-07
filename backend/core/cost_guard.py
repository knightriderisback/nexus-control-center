"""
NEXUS Cost Guard Engine.
Strict zero-cost guardrail enforcement, free-tier budget tracking,
and billable action pre-flight validation.
"""

import json
import os
from typing import Dict, Any, List
from core.config import config
from models.schemas import RiskLevel
from core.audit import record_audit

from core.storage import atomic_save_json, load_json_safe

class CostGuard:
    def __init__(self):
        self.state_file = config.cost_guard_file
        self.billing_linked = False # Verified unlinked in project personal-engineering-os-2026
        self.monthly_budget_cap = 0.00 # Zero spend ceiling
        self.current_month_spend = 0.00
        self._ensure_state_initialized()

    def _ensure_state_initialized(self):
        if not os.path.exists(self.state_file):
            state = {
                "billing_account_linked": self.billing_linked,
                "current_month_spend_usd": self.current_month_spend,
                "monthly_budget_cap_usd": self.monthly_budget_cap,
                "strict_zero_cost_enforced": True,
                "free_tier_status": {
                    "cloud_run": {"used_requests": 0, "limit": 2000000, "unit": "requests"},
                    "cloud_storage": {"used_gb": 0.0, "limit": 5.0, "unit": "GB"},
                    "bigquery": {"used_queries_tb": 0.0, "limit": 1.0, "unit": "TB"},
                    "cloud_build": {"used_minutes": 0, "limit": 120, "unit": "minutes/day"},
                    "artifact_registry": {"used_gb": 0.0, "limit": 0.5, "unit": "GB"}
                },
                "anomalies": []
            }
            atomic_save_json(self.state_file, state)

    def get_status(self) -> Dict[str, Any]:
        data = load_json_safe(self.state_file, default=None)
        if data:
            return data
        return {
            "billing_account_linked": self.billing_linked,
            "current_month_spend_usd": 0.00,
            "monthly_budget_cap_usd": 0.00,
            "strict_zero_cost_enforced": True,
            "anomalies": []
        }

    def evaluate_cost_risk(self, target_service: str, action: str) -> Dict[str, Any]:
        """
        Validates if an action risks incurring unexpected cloud charges.
        Returns risk evaluation and whether action is permitted.
        """
        paid_services = ["compute.googleapis.com", "container.googleapis.com", "sqladmin.googleapis.com"]
        
        if not self.billing_linked:
            if target_service in paid_services or "create_instance" in action.lower():
                return {
                    "allowed": False,
                    "reason": "Billing unlinked: Paid infrastructure creation blocked by Zero-Cost Guardrail.",
                    "risk": RiskLevel.CRITICAL
                }
        
        return {
            "allowed": True,
            "reason": "Action falls within Free Tier or local non-billable boundaries.",
            "risk": RiskLevel.LOW
        }

cost_guard = CostGuard()
