"""
NEXUS Phase 13: Capability-Based Agent Registry & Selection Subsystem.

Provides dynamic, capability-based discovery, matching, and selection of specialized
agents without hardcoding mission tasks to specific agent identifiers.
Maintains 100% backward compatibility with existing Phase 6-12 specialized fleet agents.
"""

import logging
from typing import Dict, List, Optional, Set
from models.schemas import AgentCapability, RiskLevel, AgentManifest
from orchestrator.agents import SPECIALIZED_AGENTS, get_agent_by_id, get_agent_list

logger = logging.getLogger("nexus.capability_registry")

# Standard capabilities supported across the NEXUS engineering swarm
STANDARD_CAPABILITIES: Set[str] = {
    "research",
    "architecture",
    "frontend",
    "backend",
    "database",
    "api",
    "testing",
    "security",
    "performance",
    "documentation",
    "devops",
    "infrastructure",
    "data",
    "ux",
    "seo",
    "recovery",
    "review",
    "delivery",
    "arbitration"
}

# Base capability profiles for existing specialized fleet agents
AGENT_CAPABILITY_PROFILES: Dict[str, Dict[str, Any]] = {
    "agent-research": {
        "name": "RESEARCH-01",
        "supported_tasks": ["research", "architecture", "analysis", "rfc_summary"],
        "capabilities": ["research", "architecture", "documentation", "review"],
        "risk_level": RiskLevel.LOW,
        "tools": ["grep", "ast_search", "web_search", "doc_reader"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 100000}
    },
    "agent-dev": {
        "name": "DEVELOPER-02",
        "supported_tasks": ["backend", "frontend", "api", "refactoring", "synthesis"],
        "capabilities": ["backend", "frontend", "api", "database", "data"],
        "risk_level": RiskLevel.MEDIUM,
        "tools": ["file_editor", "code_patcher", "linter", "git_branch"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 200000}
    },
    "agent-security": {
        "name": "SENTINEL-SEC",
        "supported_tasks": ["security", "secret_scan", "cve_audit", "policy_check"],
        "capabilities": ["security", "review", "infrastructure"],
        "risk_level": RiskLevel.HIGH,
        "tools": ["regex_audit", "cve_lookup", "secret_detector", "iam_inspector"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 150000}
    },
    "agent-qa": {
        "name": "QA-VERIFIER",
        "supported_tasks": ["testing", "unit_tests", "e2e_tests", "verification"],
        "capabilities": ["testing", "review", "performance"],
        "risk_level": RiskLevel.LOW,
        "tools": ["pytest_runner", "npm_test_runner", "curl_probe", "coverage_inspector"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 100000}
    },
    "agent-docs": {
        "name": "DOC-CHRONICLER",
        "supported_tasks": ["documentation", "adr_synthesis", "changelog", "openapi"],
        "capabilities": ["documentation", "seo", "architecture"],
        "risk_level": RiskLevel.LOW,
        "tools": ["doc_writer", "openapi_generator", "markdown_formatter"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 80000}
    },
    "agent-db": {
        "name": "DB-ARCHITECT",
        "supported_tasks": ["database", "schema_design", "migrations", "indices"],
        "capabilities": ["database", "backend", "architecture", "data"],
        "risk_level": RiskLevel.MEDIUM,
        "tools": ["schema_migrator", "sql_linter", "index_analyzer"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 120000}
    },
    "agent-api": {
        "name": "API-INTEGRATOR",
        "supported_tasks": ["api", "rest_endpoints", "contract_validation", "routes"],
        "capabilities": ["api", "backend", "testing"],
        "risk_level": RiskLevel.LOW,
        "tools": ["curl_probe", "openapi_generator", "route_validator"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 120000}
    },
    "agent-frontend": {
        "name": "UI-ENGINEER",
        "supported_tasks": ["frontend", "components", "tailwind", "react"],
        "capabilities": ["frontend", "ux", "seo"],
        "risk_level": RiskLevel.LOW,
        "tools": ["vite_builder", "tailwind_checker", "component_tester"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 150000}
    },
    "agent-devops": {
        "name": "DEVOPS-DEPLOYER",
        "supported_tasks": ["devops", "docker", "containers", "ci_cd", "scripts"],
        "capabilities": ["devops", "infrastructure", "delivery"],
        "risk_level": RiskLevel.MEDIUM,
        "tools": ["docker_cli", "bash_runner", "ci_tester"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 100000}
    },
    "agent-perf": {
        "name": "PERF-PROFILER",
        "supported_tasks": ["performance", "latency", "benchmarking", "profiling"],
        "capabilities": ["performance", "testing", "backend"],
        "risk_level": RiskLevel.LOW,
        "tools": ["benchmark_runner", "memory_profiler", "latency_meter"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 80000}
    },
    "agent-ux": {
        "name": "UX-STRATEGIST",
        "supported_tasks": ["ux", "accessibility", "responsive_layout", "mobile_touch"],
        "capabilities": ["ux", "frontend", "seo"],
        "risk_level": RiskLevel.LOW,
        "tools": ["a11y_auditor", "viewport_simulator"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 80000}
    },
    "agent-arbitrator": {
        "name": "SWARM-ARBITRATOR",
        "supported_tasks": ["arbitration", "merge", "conflict_resolution", "delivery"],
        "capabilities": ["arbitration", "delivery", "review"],
        "risk_level": RiskLevel.HIGH,
        "tools": ["merge_evaluator", "git_arbitrator", "diff_inspector"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 150000}
    },
    "agent-recovery": {
        "name": "RECOVERY-ORCHESTRATOR",
        "supported_tasks": ["recovery", "remediation", "circuit_reset", "resumption"],
        "capabilities": ["recovery", "testing", "security"],
        "risk_level": RiskLevel.HIGH,
        "tools": ["checkpoint_loader", "circuit_breaker", "remediation_loop"],
        "cost_policy": {"cost_per_token": 0.0, "max_tokens": 120000}
    }
}


class CapabilityRegistry:
    """Registry of agent capabilities and dynamic matching engine."""

    def __init__(self):
        self._capabilities: Dict[str, AgentCapability] = {}
        self._agent_id_to_capabilities: Dict[str, Set[str]] = {}
        self._initialize_from_fleet()

    def _initialize_from_fleet(self):
        """Builds capability mappings from specialized agents."""
        for agent in SPECIALIZED_AGENTS:
            profile = AGENT_CAPABILITY_PROFILES.get(agent.id, {})
            caps = set(profile.get("capabilities", []))
            tasks = profile.get("supported_tasks", [])
            
            # Map manifest capabilities
            for c in agent.capabilities:
                caps.add(c.lower().replace(" ", "_"))
            
            self._agent_id_to_capabilities[agent.id] = caps
            
            cap_obj = AgentCapability(
                name=agent.name,
                version="1.0.0",
                provider="nexus-local",
                supported_tasks=tasks,
                risk_level=agent.risk_level,
                tools=agent.allowed_tools,
                execution_limits={"max_parallel": 3, "timeout_seconds": 300},
                availability="AVAILABLE",
                health="HEALTHY",
                cost_policy=profile.get("cost_policy", {"cost_per_token": 0.0, "max_tokens": 100000})
            )
            self._capabilities[agent.id] = cap_obj

    def register_agent_capability(self, agent_id: str, capability: AgentCapability, capabilities: List[str]):
        """Dynamically registers or updates an agent's capability profile."""
        if hasattr(capability, "agent_id") and not getattr(capability, "agent_id", None):
            setattr(capability, "agent_id", agent_id)
        self._capabilities[agent_id] = capability
        self._agent_id_to_capabilities[agent_id] = set(c.lower() for c in capabilities)

    def list_all_capabilities(self) -> Dict[str, AgentCapability]:
        """Returns all registered agent capabilities."""
        return dict(self._capabilities)

    def get_agent_capabilities(self, agent_id: str) -> Set[str]:
        """Returns the set of capabilities supported by a specific agent."""
        return set(self._agent_id_to_capabilities.get(agent_id, set()))

    def find_agents_for_capability(self, capability: str) -> List[Any]:
        """Finds all agents that possess a specific capability."""
        cap_norm = capability.lower().strip()
        matched: List[Any] = []
        # Check specialized fleet agents
        seen_ids = set()
        for agent in get_agent_list():
            agent_caps = self._agent_id_to_capabilities.get(agent.id, set())
            if cap_norm in agent_caps or any(cap_norm in c for c in agent_caps):
                matched.append(agent)
                seen_ids.add(agent.id)
        # Check custom registered capabilities
        for agent_id, cap_obj in self._capabilities.items():
            if agent_id in seen_ids:
                continue
            agent_caps = self._agent_id_to_capabilities.get(agent_id, set())
            if cap_norm in agent_caps or any(cap_norm in c for c in agent_caps):
                if hasattr(cap_obj, "agent_id") and not getattr(cap_obj, "agent_id", None):
                    setattr(cap_obj, "agent_id", agent_id)
                matched.append(cap_obj)
        return matched

    def select_best_agent(
        self,
        task_type: str,
        required_capabilities: Optional[List[str]] = None,
        risk_limit: Optional[RiskLevel] = None
    ) -> AgentManifest:
        """
        Dynamically selects the best matching agent based on required capabilities and task requirements.
        Falls back to DEVELOPER-02 if no specific match is found.
        """
        required = set(c.lower().strip() for c in (required_capabilities or []))
        if task_type:
            required.add(task_type.lower().strip())

        candidates = get_agent_list()
        best_agent: Optional[AgentManifest] = None
        best_score = -1

        for agent in candidates:
            # Check risk ceiling if provided
            if risk_limit:
                risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
                if risk_order.index(agent.risk_level) > risk_order.index(risk_limit):
                    continue

            agent_caps = self._agent_id_to_capabilities.get(agent.id, set())
            profile = AGENT_CAPABILITY_PROFILES.get(agent.id, {})
            supported_tasks = set(profile.get("supported_tasks", []))

            score = 0
            # Task type exact match
            if task_type and (task_type.lower() in supported_tasks or task_type.lower() in agent_caps):
                score += 10

            # Capabilities overlap
            overlap = len(required.intersection(agent_caps))
            score += overlap * 3

            # Prefer idle agents
            if getattr(agent, "status", "idle") == "idle":
                score += 1

            if score > best_score:
                best_score = score
                best_agent = agent

        if best_agent is not None and best_score > 0:
            return best_agent

        # Safe fallback
        dev_agent = get_agent_by_id("agent-dev")
        if dev_agent:
            return dev_agent
        return candidates[0] if candidates else SPECIALIZED_AGENTS[0]

    def match_tools_for_capabilities(self, capabilities: List[str]) -> List[Any]:
        """
        Dynamically matches and resolves universal tools needed to satisfy
        a set of required capabilities for an autonomous mission subtask.
        """
        from orchestrator.universal_tool_engine import universal_tool_engine
        all_tools = universal_tool_engine.list_tools()
        req_set = set(c.lower().strip() for c in capabilities)
        matched_tools = []
        for tool in all_tools:
            tool_caps = set(c.lower().strip() for c in tool.required_capabilities)
            if tool_caps.intersection(req_set) or tool.category.value.lower() in req_set:
                matched_tools.append(tool)
        return matched_tools


# Singleton export
capability_registry = CapabilityRegistry()

