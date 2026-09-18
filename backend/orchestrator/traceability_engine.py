"""
NEXUS Phase 13: End-to-End Requirement Traceability Subsystem.

Traces every requirement through:
Requirement -> Sub-mission -> Agent execution -> Artifact -> Test -> Review -> Delivery.
Provides deterministic answers to:
- "Why is this code/artifact part of this mission?"
- "Which requirement does this test verify?"
"""

import os
import logging
from typing import Dict, Any, List, Optional
from models.schemas import EngineeringMission, TraceabilityLink, MissionRequirement, MissionSubtask

logger = logging.getLogger("nexus.traceability")


class TraceabilityEngine:
    """Manages and queries requirement-to-outcome traceability graphs."""

    def build_traceability_matrix(self, mission: EngineeringMission) -> List[TraceabilityLink]:
        """Constructs or refreshes the full traceability matrix for a mission."""
        links: List[TraceabilityLink] = []
        req_map: Dict[str, MissionRequirement] = {r.requirement_id: r for r in mission.requirements}

        for subtask in mission.subtasks:
            # Map subtask targets and results to requirements
            linked_req_ids = subtask.linked_requirement_ids or []
            if not linked_req_ids:
                # If no explicit links, map by category/title heuristic
                for r in mission.requirements:
                    if r.category.lower() in subtask.title.lower() or any(f in subtask.description for f in r.description.split()):
                        linked_req_ids.append(r.requirement_id)
                if not linked_req_ids and mission.requirements:
                    linked_req_ids = [mission.requirements[0].requirement_id]

            for req_id in linked_req_ids:
                req = req_map.get(req_id)
                req_desc = req.description if req else "General objective"

                # Find associated tests and criteria
                linked_tests = [f for f in subtask.target_files if "test" in f.lower()]
                linked_artifacts = [f for f in subtask.target_files if "test" not in f.lower()]

                if not linked_artifacts and not linked_tests:
                    link = TraceabilityLink(
                        link_id=f"trace-{subtask.subtask_id}-{req_id}",
                        requirement_id=req_id,
                        subtask_id=subtask.subtask_id,
                        agent_id=subtask.assigned_agent,
                        artifact_path=None,
                        test_id=None,
                        acceptance_criterion_id=None,
                        status="VERIFIED" if subtask.status == "COMPLETED" else "PENDING",
                        explanation=f"Subtask '{subtask.title}' addresses requirement '{req_id}': {req_desc}"
                    )
                    links.append(link)

                # Link artifacts
                for art in linked_artifacts:
                    link = TraceabilityLink(
                        link_id=f"trace-{subtask.subtask_id}-{req_id}-{os.path.basename(art)}",
                        requirement_id=req_id,
                        subtask_id=subtask.subtask_id,
                        agent_id=subtask.assigned_agent,
                        artifact_path=art,
                        test_id=linked_tests[0] if linked_tests else None,
                        status="VERIFIED" if subtask.status == "COMPLETED" else "PENDING",
                        explanation=f"Artifact '{art}' synthesized by agent '{subtask.assigned_agent}' to satisfy {req_id}"
                    )
                    links.append(link)

                # Link tests
                for tst in linked_tests:
                    link = TraceabilityLink(
                        link_id=f"trace-{subtask.subtask_id}-{req_id}-{os.path.basename(tst)}",
                        requirement_id=req_id,
                        subtask_id=subtask.subtask_id,
                        agent_id=subtask.assigned_agent,
                        artifact_path=None,
                        test_id=tst,
                        status="VERIFIED" if subtask.status == "COMPLETED" else "PENDING",
                        explanation=f"Test '{tst}' verifies compliance of requirement {req_id}"
                    )
                    links.append(link)

        mission.traceability = links
        return links

    def why_artifact(self, mission: EngineeringMission, artifact_path: str) -> Dict[str, Any]:
        """
        Answers: 'Why is this code/artifact part of this mission?'
        Returns the originating requirement, subtask, agent, and explanation.
        """
        norm_target = os.path.basename(artifact_path).lower()

        # Check existing traceability links
        for link in mission.traceability:
            if link.artifact_path and os.path.basename(link.artifact_path).lower() == norm_target:
                req = next((r for r in mission.requirements if r.requirement_id == link.requirement_id), None)
                subtask = next((s for s in mission.subtasks if s.subtask_id == link.subtask_id), None)
                return {
                    "artifact": artifact_path,
                    "found": True,
                    "requirement_id": link.requirement_id,
                    "requirement_description": req.description if req else "Objective specification",
                    "subtask_id": link.subtask_id,
                    "subtask_title": subtask.title if subtask else "",
                    "assigned_agent": link.agent_id,
                    "status": link.status,
                    "explanation": link.explanation
                }

        # Fallback inspection of subtasks
        for subtask in mission.subtasks:
            for f in subtask.target_files:
                if os.path.basename(f).lower() == norm_target:
                    req_id = subtask.linked_requirement_ids[0] if subtask.linked_requirement_ids else (mission.requirements[0].requirement_id if mission.requirements else "REQ-GEN")
                    req = next((r for r in mission.requirements if r.requirement_id == req_id), None)
                    return {
                        "artifact": artifact_path,
                        "found": True,
                        "requirement_id": req_id,
                        "requirement_description": req.description if req else "Objective specification",
                        "subtask_id": subtask.subtask_id,
                        "subtask_title": subtask.title,
                        "assigned_agent": subtask.assigned_agent,
                        "status": subtask.status,
                        "explanation": f"Synthesized during subtask '{subtask.title}' to satisfy {req_id}"
                    }

        return {
            "artifact": artifact_path,
            "found": False,
            "explanation": f"Artifact '{artifact_path}' is not mapped to any known requirement in mission {mission.mission_id}."
        }

    def tests_for_requirement(self, mission: EngineeringMission, requirement_id: str) -> List[Dict[str, Any]]:
        """
        Answers: 'Which requirement does this test verify?'
        Returns all tests, subtasks, and acceptance criteria linked to requirement_id.
        """
        results: List[Dict[str, Any]] = []

        # Check traceability links
        for link in mission.traceability:
            if link.requirement_id == requirement_id and link.test_id:
                results.append({
                    "test_file": link.test_id,
                    "subtask_id": link.subtask_id,
                    "agent_id": link.agent_id,
                    "status": link.status,
                    "explanation": link.explanation
                })

        # Check subtasks
        if not results:
            for subtask in mission.subtasks:
                if requirement_id in subtask.linked_requirement_ids:
                    tests = [f for f in subtask.target_files if "test" in f.lower()]
                    for t in tests:
                        results.append({
                            "test_file": t,
                            "subtask_id": subtask.subtask_id,
                            "agent_id": subtask.assigned_agent,
                            "status": subtask.status,
                            "explanation": f"Test created in subtask '{subtask.title}' to verify {requirement_id}"
                        })

        # Check acceptance criteria
        for ac in mission.acceptance_criteria:
            if ac.requirement_id == requirement_id:
                results.append({
                    "acceptance_criterion_id": ac.criterion_id,
                    "evaluator": ac.evaluator,
                    "status": ac.status,
                    "evidence": ac.evidence,
                    "explanation": f"Acceptance test: {ac.description}"
                })

        return results

    def get_matrix_summary(self, mission: EngineeringMission) -> Dict[str, Any]:
        """Returns coverage metrics for requirements traceability."""
        total_reqs = len(mission.requirements)
        if total_reqs == 0:
            return {"coverage_percent": 100.0, "total_requirements": 0, "covered_requirements": 0}

        covered = set()
        for link in mission.traceability:
            if link.status in ["VERIFIED", "COMPLETED", "PASSED"]:
                covered.add(link.requirement_id)

        # Also check completed subtasks with linked requirements
        for subtask in mission.subtasks:
            if subtask.status == "COMPLETED":
                for r in subtask.linked_requirement_ids:
                    covered.add(r)

        return {
            "total_requirements": total_reqs,
            "covered_requirements": len(covered),
            "coverage_percent": round((len(covered) / total_reqs) * 100, 1),
            "fully_traced": len(covered) == total_reqs
        }


# Singleton export
traceability_engine = TraceabilityEngine()
