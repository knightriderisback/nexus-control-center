"""
NEXUS Phase 13: Goal Decomposer & Dynamic Sub-Mission DAG Planner.

Transforms natural-language engineering directives into:
1. Normalized Objective & Multi-Category Requirements (REQ-001, REQ-002...)
2. Machine-Verifiable Acceptance Criteria (AC-001, AC-002...)
3. Dynamically Inferred Capability Requirements
4. Capability-Selected Agent Assignments
5. Dependency-Aware Directed Acyclic Graph (DAG) partitioned into parallel topological levels.
"""

import re
import hashlib
import logging
from typing import Dict, Any, List, Set, Tuple, Optional

from models.schemas import (
    EngineeringMission,
    MissionState,
    MissionSubtask,
    MissionRequirement,
    AcceptanceCriterion,
    EngineeringBlueprint,
    RiskLevel,
    MissionPlanRequest
)
from orchestrator.capability_registry import capability_registry

logger = logging.getLogger("nexus.goal_decomposer")


class GoalDecomposer:
    """Decomposes goals into requirements, acceptance criteria, and a capability-driven DAG."""

    def decompose(self, req: MissionPlanRequest) -> Tuple[
        str,                               # normalized_objective
        List[MissionRequirement],          # requirements
        List[AcceptanceCriterion],         # acceptance_criteria
        List[str],                         # required_capabilities
        List[MissionSubtask],              # subtasks (DAG nodes)
        List[List[str]],                   # execution_order (topological levels)
        Dict[str, Any]                     # risk_profile
    ]:
        goal = req.goal.strip()
        goal_lower = goal.lower()

        # 1. Normalize Objective
        normalized_objective = self._normalize_objective(goal)

        # 2. Derive Required Capabilities from Goal Semantics
        required_capabilities = self._infer_capabilities(goal_lower)

        # 3. Derive Multi-Category Requirements (REQ-001 to REQ-006)
        requirements = self._derive_requirements(goal, goal_lower, required_capabilities)

        # 4. Generate Target Artifact & Test File Names
        module_name, test_file_name, doc_file_name = self._derive_filenames(goal)

        # 5. Derive Machine-Verifiable Acceptance Criteria (AC-001...)
        acceptance_criteria = self._derive_acceptance_criteria(
            module_name=module_name,
            test_file_name=test_file_name,
            doc_file_name=doc_file_name,
            requirements=requirements,
            capabilities=required_capabilities
        )

        # 6. Dynamically Synthesize Sub-Missions / DAG Nodes with Capability Assignment
        subtasks = self._synthesize_dag_nodes(
            goal=goal,
            goal_lower=goal_lower,
            module_name=module_name,
            test_file_name=test_file_name,
            doc_file_name=doc_file_name,
            requirements=requirements,
            capabilities=required_capabilities
        )

        # 7. Topological Sort & Parallel Level Partitioning (Kahn's Algorithm)
        execution_order = self._topological_sort_levels(subtasks)

        # 8. Compute Risk Profile
        risk_profile = self._assess_risk(goal_lower, subtasks)

        return (
            normalized_objective,
            requirements,
            acceptance_criteria,
            required_capabilities,
            subtasks,
            execution_order,
            risk_profile
        )

    # -------------------------------------------------------------------------
    # Helper Derivations
    # -------------------------------------------------------------------------

    def _normalize_objective(self, goal: str) -> str:
        clean = re.sub(r"\s+", " ", goal).strip()
        if not clean.endswith("."):
            clean += "."
        return f"Autonomous delivery: {clean}"

    def _infer_capabilities(self, goal_lower: str) -> List[str]:
        caps: Set[str] = {"research", "architecture", "testing", "security", "documentation"}

        if any(w in goal_lower for w in ["api", "rest", "endpoint", "route", "service", "fastapi"]):
            caps.add("api")
            caps.add("backend")
        if any(w in goal_lower for w in ["database", "db", "sql", "postgres", "sqlite", "model", "schema"]):
            caps.add("database")
            caps.add("backend")
        if any(w in goal_lower for w in ["ui", "frontend", "react", "dashboard", "view", "component", "tailwind", "mobile"]):
            caps.add("frontend")
            caps.add("ux")
        if any(w in goal_lower for w in ["docker", "container", "devops", "deploy", "ci", "k8s"]):
            caps.add("devops")
            caps.add("infrastructure")
        if any(w in goal_lower for w in ["perf", "fast", "cache", "benchmark", "optimize", "lru"]):
            caps.add("performance")
        if any(w in goal_lower for w in ["deliver", "pr", "github", "merge"]):
            caps.add("delivery")
            caps.add("arbitration")

        # Default engineering baseline
        caps.add("backend")
        return sorted(list(caps))

    def _derive_filenames(self, goal: str) -> Tuple[str, str, str]:
        words = re.findall(r"[a-zA-Z0-9]+", goal.lower())
        stopwords = {"build", "create", "implement", "a", "an", "the", "with", "and", "for", "in", "to", "production", "ready"}
        meaningful = [w for w in words if w not in stopwords]
        base = "_".join(meaningful[:2]) if meaningful else "module"
        if not base:
            base = "service"

        module_file = f"{base}.py"
        test_file = f"test_{base}.py"
        doc_file = f"docs/{base.upper()}_SPEC.md"
        return module_file, test_file, doc_file

    def _derive_requirements(
        self,
        goal: str,
        goal_lower: str,
        capabilities: List[str]
    ) -> List[MissionRequirement]:
        reqs: List[MissionRequirement] = [
            MissionRequirement(
                requirement_id="REQ-001",
                category="functional",
                description=f"Synthesize core functional capability according to goal: '{goal}'",
                priority="CRITICAL",
                status="PENDING",
                assigned_subtask_ids=["subtask-02-dev"]
            ),
            MissionRequirement(
                requirement_id="REQ-002",
                category="technical",
                description="Establish modular architecture, interface contracts, and dependency-isolated components",
                priority="HIGH",
                status="PENDING",
                assigned_subtask_ids=["subtask-01-arch", "subtask-02-dev"]
            ),
            MissionRequirement(
                requirement_id="REQ-003",
                category="quality",
                description="Provide automated unit, edge-case, and regression test suite with 100% pass verification",
                priority="HIGH",
                status="PENDING",
                assigned_subtask_ids=["subtask-03-qa"]
            ),
            MissionRequirement(
                requirement_id="REQ-004",
                category="security",
                description="Enforce AST secret leak audit, prompt injection quarantine, and zero credential exposure",
                priority="CRITICAL",
                status="PENDING",
                assigned_subtask_ids=["subtask-04-sec"]
            ),
            MissionRequirement(
                requirement_id="REQ-005",
                category="operational",
                description="Generate technical specification, architecture decisions (ADR), and release changelog",
                priority="MEDIUM",
                status="PENDING",
                assigned_subtask_ids=["subtask-05-doc"]
            ),
            MissionRequirement(
                requirement_id="REQ-006",
                category="delivery",
                description="Execute pre-merge verification, branch arbitration, and governed delivery candidate generation",
                priority="HIGH",
                status="PENDING",
                assigned_subtask_ids=["subtask-06-delivery"]
            )
        ]
        return reqs

    def _derive_acceptance_criteria(
        self,
        module_name: str,
        test_file_name: str,
        doc_file_name: str,
        requirements: List[MissionRequirement],
        capabilities: List[str]
    ) -> List[AcceptanceCriterion]:
        criteria: List[AcceptanceCriterion] = [
            AcceptanceCriterion(
                criterion_id="AC-001",
                requirement_id="REQ-001",
                description=f"Core module '{module_name}' exists and has valid Python syntax",
                evaluator="schema_valid",
                params={"file": module_name}
            ),
            AcceptanceCriterion(
                criterion_id="AC-002",
                requirement_id="REQ-003",
                description=f"Automated test suite '{test_file_name}' executes and passes all assertions",
                evaluator="test_passes",
                params={"test_file": test_file_name}
            ),
            AcceptanceCriterion(
                criterion_id="AC-003",
                requirement_id="REQ-004",
                description="Security scan of workspace confirms 0 static secrets or credentials",
                evaluator="security_scan_clean",
                params={}
            ),
            AcceptanceCriterion(
                criterion_id="AC-004",
                requirement_id="REQ-005",
                description=f"Technical specification artifact '{doc_file_name}' exists",
                evaluator="file_exists",
                params={"file": doc_file_name}
            ),
            AcceptanceCriterion(
                criterion_id="AC-005",
                requirement_id="REQ-002",
                description="Clean compilation confirmed with zero syntax errors",
                evaluator="build_succeeds",
                params={"file": module_name}
            )
        ]
        return criteria

    def _synthesize_dag_nodes(
        self,
        goal: str,
        goal_lower: str,
        module_name: str,
        test_file_name: str,
        doc_file_name: str,
        requirements: List[MissionRequirement],
        capabilities: List[str]
    ) -> List[MissionSubtask]:
        # Node 1: Architecture & Research (Assigned via capability)
        agent_arch = capability_registry.select_best_agent("architecture", ["research", "architecture"])
        st1 = MissionSubtask(
            subtask_id="subtask-01-arch",
            title="System Topology & Interface Specification",
            description=f"Analyze repository topology and design modular interface contracts for: {goal}",
            assigned_agent=agent_arch.name,
            dependencies=[],
            target_files=[doc_file_name],
            risk_level=RiskLevel.LOW,
            required_capabilities=["research", "architecture"],
            linked_requirement_ids=["REQ-002"]
        )

        # Node 2: Core Engineering Implementation
        agent_dev = capability_registry.select_best_agent("backend", ["backend", "api"])
        st2 = MissionSubtask(
            subtask_id="subtask-02-dev",
            title="Modular Feature Synthesis",
            description=f"Synthesize production-grade implementation satisfying: {goal}",
            assigned_agent=agent_dev.name,
            dependencies=["subtask-01-arch"],
            target_files=[module_name],
            risk_level=RiskLevel.MEDIUM,
            required_capabilities=["backend", "api"],
            linked_requirement_ids=["REQ-001", "REQ-002"]
        )

        # Node 3: QA Test Suite Synthesis & Execution
        agent_qa = capability_registry.select_best_agent("testing", ["testing", "verification"])
        st3 = MissionSubtask(
            subtask_id="subtask-03-qa",
            title="Automated Test Suite Verification",
            description=f"Construct comprehensive unit and regression assertions for {module_name}",
            assigned_agent=agent_qa.name,
            dependencies=["subtask-02-dev"],
            target_files=[test_file_name],
            risk_level=RiskLevel.LOW,
            required_capabilities=["testing"],
            linked_requirement_ids=["REQ-003"]
        )

        # Node 4: Security Sentinel AST Audit (Can run in parallel with Node 5)
        agent_sec = capability_registry.select_best_agent("security", ["security", "review"])
        st4 = MissionSubtask(
            subtask_id="subtask-04-sec",
            title="AST Security & Secret Leak Audit",
            description="Audit synthesized artifacts for sensitive tokens, prompt injection vectors, and CVE risks",
            assigned_agent=agent_sec.name,
            dependencies=["subtask-02-dev"],
            target_files=[module_name],
            risk_level=RiskLevel.HIGH,
            required_capabilities=["security"],
            linked_requirement_ids=["REQ-004"]
        )

        # Node 5: Documentation & Changelog Synthesis (Can run in parallel with Node 4)
        agent_doc = capability_registry.select_best_agent("documentation", ["documentation", "seo"])
        st5 = MissionSubtask(
            subtask_id="subtask-05-doc",
            title="Technical Documentation & Changelog",
            description=f"Synthesize Architecture Decision Record and documentation for {module_name}",
            assigned_agent=agent_doc.name,
            dependencies=["subtask-02-dev"],
            target_files=[doc_file_name],
            risk_level=RiskLevel.LOW,
            required_capabilities=["documentation"],
            linked_requirement_ids=["REQ-005"]
        )

        # Node 6: Arbitration & Governed Delivery
        agent_arb = capability_registry.select_best_agent("arbitration", ["arbitration", "delivery"])
        st6 = MissionSubtask(
            subtask_id="subtask-06-delivery",
            title="Pre-Merge Arbitration & Governed Candidate Delivery",
            description="Reconcile changes, verify acceptance criteria, and stage candidate branch for delivery",
            assigned_agent=agent_arb.name,
            dependencies=["subtask-03-qa", "subtask-04-sec", "subtask-05-doc"],
            target_files=[module_name, test_file_name, doc_file_name],
            risk_level=RiskLevel.HIGH,
            required_capabilities=["arbitration", "delivery"],
            linked_requirement_ids=["REQ-006"]
        )

        return [st1, st2, st3, st4, st5, st6]

    def _topological_sort_levels(self, subtasks: List[MissionSubtask]) -> List[List[str]]:
        """Kahn's topological sort grouping independent nodes into parallel levels."""
        task_map = {t.subtask_id: t for t in subtasks}
        in_degree: Dict[str, int] = {t.subtask_id: 0 for t in subtasks}
        adj_list: Dict[str, List[str]] = {t.subtask_id: [] for t in subtasks}

        for t in subtasks:
            for dep in t.dependencies:
                if dep in in_degree:
                    in_degree[t.subtask_id] += 1
                    adj_list[dep].append(t.subtask_id)

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        levels: List[List[str]] = []
        visited_count = 0

        while queue:
            current_level = list(queue)
            levels.append(current_level)
            visited_count += len(current_level)
            next_queue = []

            for tid in current_level:
                for neighbor in adj_list.get(tid, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            queue = next_queue

        if visited_count != len(subtasks):
            raise ValueError("Cycle detected in mission DAG: cannot construct topological execution order.")

        return levels

    def _assess_risk(self, goal_lower: str, subtasks: List[MissionSubtask]) -> Dict[str, Any]:
        high_risk_keywords = ["auth", "token", "billing", "payment", "iam", "secret", "private_key", "prod", "delete"]
        matched_risks = [w for w in high_risk_keywords if w in goal_lower]

        overall_risk = "LOW"
        requires_approval = False

        if matched_risks:
            overall_risk = "HIGH"
            requires_approval = True
        elif any(s.risk_level == RiskLevel.HIGH for s in subtasks):
            overall_risk = "MEDIUM"

        return {
            "overall_risk": overall_risk,
            "matched_sensitive_keywords": matched_risks,
            "requires_human_approval": requires_approval,
            "approval_boundary": "SENSITIVE_GOAL_OR_IAM_CHANGE" if requires_approval else "ROUTINE_AUTONOMOUS"
        }


# Singleton export
goal_decomposer = GoalDecomposer()
