"""Lightweight workflow stage-state persistence for resumability."""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_STATE_DIR = Path("data/workflow_state")


@dataclass
class ArtifactState:
    """State of a single generation stage for a topic."""

    topic_id: str
    stage: str
    status: str = "pending"  # pending | completed | failed | needs_review
    provider: Optional[str] = None
    retries: int = 0
    completed_at: Optional[str] = None
    artifact_path: Optional[str] = None


@dataclass
class WorkflowState:
    """Aggregated workflow state for a single topic."""

    topic_id: str
    stages: dict[str, ArtifactState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Pre-initialize target workflow stages to pending status
        target_stages = [
            "brief",
            "content_intelligence",
            "storyboard",
            "thumbnail",
            "script",
            "carousel",
            "newsletter",
        ]
        for stage in target_stages:
            if stage not in self.stages:
                self.stages[stage] = ArtifactState(
                    topic_id=self.topic_id,
                    stage=stage,
                    status="pending",
                )


class WorkflowStateManager:
    """File-based workflow state persistence."""

    def __init__(self, state_dir: Optional[Path] = None):
        self._dir = state_dir or _DEFAULT_STATE_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, topic_id: str) -> Path:
        return self._dir / f"{topic_id}.json"

    def load_state(self, topic_id: str) -> WorkflowState:
        path = self._path_for(topic_id)
        if not path.exists():
            return WorkflowState(topic_id=topic_id)
        try:
            data = json.loads(path.read_text())
            stages = {
                k: ArtifactState(**v) for k, v in data.get("stages", {}).items()
            }
            return WorkflowState(topic_id=topic_id, stages=stages)
        except (json.JSONDecodeError, TypeError):
            return WorkflowState(topic_id=topic_id)

    def save_state(self, state: WorkflowState) -> None:
        path = self._path_for(state.topic_id)
        data = {
            "topic_id": state.topic_id,
            "stages": {k: asdict(v) for k, v in state.stages.items()},
        }
        path.write_text(json.dumps(data, indent=2))

    def mark_completed(
        self,
        topic_id: str,
        stage: str,
        provider: Optional[str] = None,
        retries: int = 0,
        artifact_path: Optional[str] = None,
    ) -> None:
        state = self.load_state(topic_id)
        state.stages[stage] = ArtifactState(
            topic_id=topic_id,
            stage=stage,
            status="completed",
            provider=provider,
            retries=retries,
            completed_at=datetime.now(timezone.utc).isoformat(),
            artifact_path=artifact_path,
        )
        self.save_state(state)
        logger.info(f"[workflow] topic={topic_id} stage={stage} status=completed")

    def mark_failed(self, topic_id: str, stage: str, retries: int = 0) -> None:
        state = self.load_state(topic_id)
        state.stages[stage] = ArtifactState(
            topic_id=topic_id,
            stage=stage,
            status="failed",
            retries=retries,
        )
        self.save_state(state)
        logger.info(f"[workflow] topic={topic_id} stage={stage} status=failed")

    def stage_completed(self, topic_id: str, stage: str) -> bool:
        state = self.load_state(topic_id)
        artifact = state.stages.get(stage)
        if artifact and artifact.status == "completed":
            logger.debug(f"[workflow] topic={topic_id} stage={stage} skipped=already_completed")
            return True
        return False

    def get_pending_stages(self, topic_id: str, all_stages: list[str]) -> list[str]:
        state = self.load_state(topic_id)
        return [
            s for s in all_stages
            if state.stages.get(s) is None or state.stages[s].status != "completed"
        ]
