"""
NEXUS Phase 16: Base Deployment Adapter Interface.
Defines provider-neutral lifecycle contracts for all deployment targets.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from models.schemas import (
    DeploymentRecord,
    DeploymentStage,
    DeploymentTargetType,
    DeploymentEnvironment,
)


class BaseDeploymentAdapter(ABC):
    """
    Abstract contract for deployment target adapters.
    Guarantees consistent preflight, packaging, dispatch, health check, and rollback lifecycle.
    """

    @property
    @abstractmethod
    def target_type(self) -> DeploymentTargetType:
        """Returns the unique DeploymentTargetType enum for this adapter."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable target name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of the deployment target."""
        pass

    @abstractmethod
    def validate_preflight(self, record: DeploymentRecord, stage: DeploymentStage) -> bool:
        """Verifies environment, workspace bounds, secrets, syntax, and prerequisites."""
        pass

    @abstractmethod
    def build_and_package(self, record: DeploymentRecord, stage: DeploymentStage) -> bool:
        """Builds or verifies the release package / container / bundle."""
        pass

    @abstractmethod
    def dispatch_deployment(self, record: DeploymentRecord, stage: DeploymentStage) -> bool:
        """Executes target runtime payload delivery and establishes endpoint binding."""
        pass

    @abstractmethod
    def probe_health(self, record: DeploymentRecord, stage: DeploymentStage) -> bool:
        """Executes synthetic SLA health checks against the live deployed service."""
        pass

    @abstractmethod
    def rollback_release(self, record: DeploymentRecord, snapshot: Optional[Dict[str, Any]]) -> bool:
        """Atomically restores previous healthy release state and process allocation."""
        pass

    @abstractmethod
    def get_target_status(self) -> Dict[str, Any]:
        """Returns live adapter telemetry, runtime status, and active instances."""
        pass
