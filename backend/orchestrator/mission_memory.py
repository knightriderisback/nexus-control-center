"""
NEXUS Phase 13: Mission Checkpointing & Structured Knowledge Subsystem.

Provides:
1. Persistent mission checkpoints allowing safe pause, resume, and daemon restart recovery.
2. Structured local mission knowledge layer capturing successful strategies, remediation patterns,
   failure diagnoses, and architectural decisions.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core.storage import load_json_safe, atomic_save_json
from models.schemas import EngineeringMission, MissionCheckpoint, MissionKnowledge

logger = logging.getLogger("nexus.mission_memory")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MissionMemoryManager:
    """Manages persistent checkpoints and mission knowledge."""

    def __init__(
        self,
        checkpoint_dir: str = "/root/control-center/data/mission_checkpoints",
        knowledge_file: str = "/root/control-center/data/mission_knowledge.json"
    ):
        self.checkpoint_dir = checkpoint_dir
        self.knowledge_file = knowledge_file
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(self.knowledge_file)), exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. Checkpoint Engine
    # -------------------------------------------------------------------------

    def save_checkpoint(
        self,
        mission: EngineeringMission,
        label: str = "auto_checkpoint"
    ) -> MissionCheckpoint:
        """Saves a point-in-time recovery checkpoint of the mission state."""
        node_states = {s.subtask_id: s.status for s in mission.subtasks}
        retry_counters = {s.subtask_id: s.remediation_rounds for s in mission.subtasks}
        artifacts = []
        for s in mission.subtasks:
            artifacts.extend(s.target_files)

        acceptance_results = {
            ac.criterion_id: {"status": ac.status, "evidence": ac.evidence}
            for ac in mission.acceptance_criteria
        }

        cp_id = f"cp-{mission.mission_id}-{uuid.uuid4().hex[:6]}"
        checkpoint = MissionCheckpoint(
            checkpoint_id=cp_id,
            mission_id=mission.mission_id,
            timestamp=_now_iso(),
            state=str(mission.state),
            graph_state={"execution_order": mission.execution_order, "label": label},
            node_states=node_states,
            artifacts=list(set(artifacts)),
            current_workspace=mission.worktree_path or mission.repo_path,
            retry_counters=retry_counters,
            acceptance_results=acceptance_results,
            risk_state=mission.risk_profile or {}
        )

        # Save to mission-specific checkpoint file
        cp_file = os.path.join(self.checkpoint_dir, f"{mission.mission_id}.json")
        history = load_json_safe(cp_file, default=[])
        if not isinstance(history, list):
            history = []
        history.append(checkpoint.model_dump())
        atomic_save_json(cp_file, history)

        # Append to mission in-memory checkpoint list
        mission.checkpoints.append(checkpoint)
        logger.info(f"Saved checkpoint '{cp_id}' for mission '{mission.mission_id}' (state={mission.state})")
        return checkpoint

    def get_checkpoints(self, mission_id: str) -> List[MissionCheckpoint]:
        """Retrieves all persisted checkpoints for a mission."""
        cp_file = os.path.join(self.checkpoint_dir, f"{mission_id}.json")
        raw = load_json_safe(cp_file, default=[])
        checkpoints: List[MissionCheckpoint] = []
        if isinstance(raw, list):
            for item in raw:
                try:
                    checkpoints.append(MissionCheckpoint(**item))
                except Exception:
                    pass
        return checkpoints

    def restore_mission_state(
        self,
        mission: EngineeringMission,
        checkpoint: Optional[MissionCheckpoint] = None
    ) -> EngineeringMission:
        """Restores a mission's subtask and execution state from a checkpoint."""
        if not checkpoint:
            cps = self.get_checkpoints(mission.mission_id)
            if not cps:
                logger.warning(f"No checkpoints found to restore mission '{mission.mission_id}'")
                return mission
            checkpoint = cps[-1]

        # Reapply node states
        for subtask in mission.subtasks:
            saved_status = checkpoint.node_states.get(subtask.subtask_id)
            if saved_status:
                subtask.status = saved_status
            saved_retries = checkpoint.retry_counters.get(subtask.subtask_id)
            if saved_retries is not None:
                subtask.remediation_rounds = saved_retries

        # Reapply acceptance states
        for ac in mission.acceptance_criteria:
            res = checkpoint.acceptance_results.get(ac.criterion_id)
            if res and isinstance(res, dict):
                ac.status = res.get("status", ac.status)
                ac.evidence = res.get("evidence", ac.evidence)

        if checkpoint.current_workspace and os.path.exists(checkpoint.current_workspace):
            mission.worktree_path = checkpoint.current_workspace

        logger.info(f"Restored mission '{mission.mission_id}' from checkpoint '{checkpoint.checkpoint_id}'")
        return mission

    # -------------------------------------------------------------------------
    # 2. Mission Knowledge Store
    # -------------------------------------------------------------------------

    def record_knowledge(
        self,
        category: str,
        pattern: str,
        details: Dict[str, Any],
        outcome: str = "SUCCESS",
        mission_id: str = "global"
    ) -> MissionKnowledge:
        """Appends a structured knowledge entry (strategy, remediation, decision, observation)."""
        k_id = f"know-{uuid.uuid4().hex[:8]}"
        entry = MissionKnowledge(
            knowledge_id=k_id,
            category=category,
            mission_id=mission_id,
            pattern=pattern,
            details=details,
            outcome=outcome,
            timestamp=_now_iso()
        )

        all_knowledge = load_json_safe(self.knowledge_file, default=[])
        if not isinstance(all_knowledge, list):
            all_knowledge = []
        all_knowledge.append(entry.model_dump())
        atomic_save_json(self.knowledge_file, all_knowledge)
        logger.info(f"Captured mission knowledge [{category}] pattern: '{pattern}' (id={k_id})")
        return entry

    def query_knowledge(
        self,
        category: Optional[str] = None,
        pattern_query: Optional[str] = None,
        limit: int = 50
    ) -> List[MissionKnowledge]:
        """Queries the structured knowledge store by category or pattern."""
        raw = load_json_safe(self.knowledge_file, default=[])
        results: List[MissionKnowledge] = []
        if isinstance(raw, list):
            for item in raw:
                try:
                    k = MissionKnowledge(**item)
                    if category and k.category.lower() != category.lower():
                        continue
                    if pattern_query and pattern_query.lower() not in k.pattern.lower():
                        continue
                    results.append(k)
                except Exception:
                    pass
        return results[:limit]

    def get_remediation_guidance(self, error_text: str, failure_category: str) -> Optional[str]:
        """Queries historical remediation knowledge to return best known fix pattern."""
        entries = self.query_knowledge(category="remediation")
        err_lower = error_text.lower()
        for e in entries:
            if e.outcome == "SUCCESS" and e.pattern.lower() in err_lower:
                return e.details.get("recommended_fix") or e.details.get("patch_strategy")
        return None


# Singleton export
mission_memory = MissionMemoryManager()
