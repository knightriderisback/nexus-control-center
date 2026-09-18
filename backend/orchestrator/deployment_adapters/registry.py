"""
NEXUS Phase 16: Deployment Adapter Registry.
Provides dynamic registration, discovery, and dispatching for all deployment targets.
"""

from typing import Dict, List, Optional, Any
from models.schemas import DeploymentTargetType
from orchestrator.deployment_adapters.base import BaseDeploymentAdapter
from orchestrator.deployment_adapters.local_process_adapter import LocalProcessDeploymentAdapter
from orchestrator.deployment_adapters.static_bundle_adapter import StaticBundleDeploymentAdapter
from orchestrator.deployment_adapters.vercel_edge_adapter import VercelEdgeDeploymentAdapter
from orchestrator.deployment_adapters.cloud_run_adapter import CloudRunDeploymentAdapter
from orchestrator.deployment_adapters.termux_node_adapter import TermuxNodeDeploymentAdapter


class DeploymentAdapterRegistry:
    """
    Registry for managing all deployment target adapters.
    """

    def __init__(self):
        self._adapters: Dict[DeploymentTargetType, BaseDeploymentAdapter] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(LocalProcessDeploymentAdapter())
        self.register(StaticBundleDeploymentAdapter())
        self.register(VercelEdgeDeploymentAdapter())
        self.register(CloudRunDeploymentAdapter())
        self.register(TermuxNodeDeploymentAdapter())

    def register(self, adapter: BaseDeploymentAdapter):
        """Registers a deployment adapter."""
        self._adapters[adapter.target_type] = adapter

    def get_adapter(self, target_type: DeploymentTargetType) -> Optional[BaseDeploymentAdapter]:
        """Retrieves an adapter for a given target type."""
        return self._adapters.get(target_type)

    def list_adapters(self) -> List[BaseDeploymentAdapter]:
        """Returns all registered adapters."""
        return list(self._adapters.values())

    def get_target_manifests(self) -> List[Dict[str, Any]]:
        """Returns metadata descriptors for all registered deployment targets."""
        manifests = []
        for adapter in self._adapters.values():
            manifests.append({
                "target_type": adapter.target_type.value,
                "name": adapter.name,
                "description": adapter.description,
                "status": adapter.get_target_status(),
            })
        return manifests


deployment_adapter_registry = DeploymentAdapterRegistry()
