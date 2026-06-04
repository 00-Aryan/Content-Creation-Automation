"""Service adapter layer for resolving backend services in Streamlit UI."""

from dataclasses import dataclass
import os
from pathlib import Path
import time
from typing import Optional
import streamlit as st

from content_creation.application.context import ApplicationContext
from content_creation.application.collect_topics_service import CollectTopicsService
from content_creation.application.score_topics_service import ScoreTopicsService
from content_creation.application.brief_generation_service import BriefGenerationService
from content_creation.application.content_intelligence_service import ContentIntelligenceService
from content_creation.application.storyboard_service import StoryboardService
from content_creation.application.asset_generation_service import AssetGenerationService
from content_creation.application.pipeline_run_service import PipelineRunService
from content_creation.application.asset_review_service import AssetReviewService
from content_creation.application.brief_review_service import BriefReviewService
from content_creation.application.storyboard_review_service import StoryboardReviewService


@dataclass(frozen=True)
class TimedServiceResult:
    """UI-facing wrapper for a backend service result and elapsed time."""

    result: object
    duration_seconds: float


@st.cache_resource
def get_context() -> ApplicationContext:
    """Bootstraps and caches the ApplicationContext relative to the workspace root.

    Resolves two independent roots:
    - data_dir: Where mutable state lives (persistent disk on Render).
                 Controlled by CONTENT_FACTORY_ROOT env var.
    - source_dir: Where immutable source code lives (config/, prompts/).
                  Resolved from this script's location.
    """
    # Data directory: CONTENT_FACTORY_ROOT or auto-detect from script location
    root_env = os.environ.get("CONTENT_FACTORY_ROOT")
    if root_env:
        data_dir = Path(root_env)
    else:
        # Walk up from the current script location to locate the package directory base
        data_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        if not (data_dir / "config").exists():
            data_dir = Path.cwd()

    # Source directory: always resolved from this script's location (immutable code)
    source_dir = Path(__file__).resolve().parent.parent.parent.parent.parent

    return ApplicationContext.create(data_dir, source_dir=source_dir)


class ServiceClient:
    """Provides UI access to the concrete backend application services."""

    def __init__(self) -> None:
        self.ctx = get_context()
        from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
        self.executor = WorkflowActionExecutor()

    def is_generation_available(self) -> bool:
        """Verifies if the generation service credentials are configured on the backend."""
        from content_creation.inference.manager import InferenceManager
        return InferenceManager.is_available()

    @property
    def collect(self) -> CollectTopicsService:
        """Resolves CollectTopicsService."""
        return CollectTopicsService()

    @property
    def score(self) -> ScoreTopicsService:
        """Resolves ScoreTopicsService."""
        return ScoreTopicsService()

    @property
    def brief(self) -> BriefGenerationService:
        """Resolves BriefGenerationService."""
        return BriefGenerationService()

    @property
    def content_intelligence(self) -> ContentIntelligenceService:
        """Resolves ContentIntelligenceService."""
        return ContentIntelligenceService()

    @property
    def storyboard(self) -> StoryboardService:
        """Resolves StoryboardService."""
        return StoryboardService()

    @property
    def asset_generation(self) -> AssetGenerationService:
        """Resolves AssetGenerationService."""
        return AssetGenerationService()

    @property
    def pipeline(self) -> PipelineRunService:
        """Resolves PipelineRunService."""
        return PipelineRunService()

    @property
    def asset_review(self) -> AssetReviewService:
        """Resolves AssetReviewService."""
        return AssetReviewService()

    @property
    def brief_review(self) -> BriefReviewService:
        """Resolves BriefReviewService."""
        return BriefReviewService()

    @property
    def storyboard_review(self) -> StoryboardReviewService:
        """Resolves StoryboardReviewService."""
        return StoryboardReviewService()

    def _timed(self, fn, *args, **kwargs) -> TimedServiceResult:
        started_at = time.perf_counter()
        result = fn(*args, **kwargs)
        return TimedServiceResult(
            result=result,
            duration_seconds=time.perf_counter() - started_at,
        )

    def run_full_pipeline(
        self,
        top_n: int = 5,
        source_filter: Optional[str] = None,
    ) -> TimedServiceResult:
        """Runs the approved end-to-end pipeline service."""
        def _run():
            res = self.executor.execute(
                self.ctx,
                "run_pipeline",
                "manifest",
                "all",
                {
                    "top_n": top_n,
                    "source": source_filter,
                    "api_key": os.environ.get("GEMINI_API_KEY"),
                }
            )
            if not res.success:
                raise RuntimeError(f"Pipeline failed: {res.blocking_reasons}")
            return res.raw_result
        return self._timed(_run)

    def collect_topics(self, source_filter: Optional[str] = None) -> TimedServiceResult:
        """Runs topic collection through CollectTopicsService."""
        def _run():
            res = self.executor.execute(
                self.ctx,
                "collect",
                "topic",
                "all",
                {"source": source_filter}
            )
            if not res.success:
                raise RuntimeError(f"Collection failed: {res.blocking_reasons}")
            return res.raw_result
        return self._timed(_run)

    def score_topics(self) -> TimedServiceResult:
        """Runs topic scoring through ScoreTopicsService."""
        def _run():
            res = self.executor.execute(
                self.ctx,
                "score_topics",
                "topic",
                "all",
                {}
            )
            if not res.success:
                raise RuntimeError(f"Scoring failed: {res.blocking_reasons}")
            return res.raw_result
        return self._timed(_run)

    def generate_briefs(
        self,
        top_n: int = 5,
        rate_limit_delay: float = 5.0,
    ) -> TimedServiceResult:
        """Runs brief generation through BriefGenerationService."""
        def _run():
            res = self.executor.execute(
                self.ctx,
                "generate_briefs",
                "brief",
                "all",
                {
                    "top_n": top_n,
                    "api_key": os.environ.get("GEMINI_API_KEY"),
                }
            )
            if not res.success:
                raise RuntimeError(f"Brief generation failed: {res.blocking_reasons}")
            return res.raw_result
        return self._timed(_run)

    def generate_content_intelligence(
        self,
        top_n: int = 5,
        rate_limit_delay: float = 5.0,
    ) -> TimedServiceResult:
        """Runs content intelligence generation through ContentIntelligenceService."""
        def _run():
            res = self.executor.execute(
                self.ctx,
                "generate_ci",
                "content_intelligence",
                "all",
                {
                    "top_n": top_n,
                    "api_key": os.environ.get("GEMINI_API_KEY"),
                }
            )
            if not res.success:
                raise RuntimeError(f"Content Intelligence generation failed: {res.blocking_reasons}")
            return res.raw_result
        return self._timed(_run)

    def generate_storyboards(
        self,
        top_n: int = 5,
        rate_limit_delay: float = 5.0,
    ) -> TimedServiceResult:
        """Runs storyboard generation through StoryboardService."""
        def _run():
            res = self.executor.execute(
                self.ctx,
                "generate_storyboards",
                "storyboard",
                "all",
                {
                    "top_n": top_n,
                    "api_key": os.environ.get("GEMINI_API_KEY"),
                }
            )
            if not res.success:
                raise RuntimeError(f"Storyboard generation failed: {res.blocking_reasons}")
            return res.raw_result
        return self._timed(_run)

    def generate_asset_suite(
        self,
        top_n: int = 5,
        rate_limit_delay: float = 5.0,
    ) -> TimedServiceResult:
        """Runs storyboard-first asset generation through AssetGenerationService."""
        def _run():
            res = self.executor.execute(
                self.ctx,
                "generate_assets",
                "assets",
                "all",
                {
                    "top_n": top_n,
                    "api_key": os.environ.get("GEMINI_API_KEY"),
                }
            )
            if not res.success:
                raise RuntimeError(f"Asset generation failed: {res.blocking_reasons}")
            return res.raw_result
        return self._timed(_run)

    def apply_asset_decisions(self, topic_id: str, decisions: list) -> TimedServiceResult:
        """Applies asset review decisions through AssetReviewService."""
        def _run():
            last_res = None
            for decision in decisions:
                action_id = "approve_asset" if decision.status.value == "approved" else "reject_asset"
                res = self.executor.execute(
                    self.ctx,
                    action_id,
                    "assets",
                    topic_id,
                    {"asset_type": decision.asset_type},
                    notes=decision.rejection_reason
                )
                if not res.success:
                    raise RuntimeError(f"Asset review failed: {res.blocking_reasons}")
                last_res = res.raw_result
            return last_res
        return self._timed(_run)

    def apply_brief_decision(self, topic_id: str, decision) -> TimedServiceResult:
        """Applies a brief review decision through BriefReviewService."""
        def _run():
            action_id = "approve_brief" if decision.status.value == "approved" else "reject_brief"
            res = self.executor.execute(
                self.ctx,
                action_id,
                "brief",
                topic_id,
                {},
                notes=decision.notes
            )
            if not res.success:
                raise RuntimeError(f"Brief review failed: {res.blocking_reasons}")
            return res.raw_result
        return self._timed(_run)

    def apply_storyboard_decision(self, topic_id: str, decision) -> TimedServiceResult:
        """Applies a storyboard review decision through StoryboardReviewService."""
        def _run():
            action_id = "approve_storyboard" if decision.status.value == "approved" else "reject_storyboard"
            res = self.executor.execute(
                self.ctx,
                action_id,
                "storyboard",
                topic_id,
                {},
                notes=decision.notes
            )
            if not res.success:
                raise RuntimeError(f"Storyboard review failed: {res.blocking_reasons}")
            return res.raw_result
        return self._timed(_run)

    def get_review_history(self, topic_id: str) -> list:
        """Returns all review history entries for a topic via BriefReviewService."""
        return self.brief_review.get_all_history(self.ctx, topic_id)

    def get_brief_review_history(self, topic_id: str) -> list:
        """Returns review history entries for briefs only."""
        return self.brief_review.get_history(self.ctx, topic_id)

    def get_storyboard_review_history(self, topic_id: str) -> list:
        """Returns review history entries for storyboards only."""
        return self.storyboard_review.get_history(self.ctx, topic_id)

    def get_asset_review_history(self, topic_id: str) -> list:
        """Returns review history entries for assets only."""
        return self.asset_review.get_history(self.ctx, topic_id)

    def get_metric_counts(self) -> dict:
        """Returns current pipeline queue counts for dashboard metrics."""
        return {
            "staged": len(self.ctx.storage.list_staged()),
            "scored": len(self.ctx.storage.list_scored()),
            "briefs": len(self.ctx.storage.list_briefs()),
            "storyboards": len(self.ctx.storage.list_storyboards()),
            "manifests": len(self.ctx.storage.list_manifests()),
        }

    def list_staged_topics(self) -> list:
        return self.ctx.storage.list_staged()

    def list_scored_topics(self) -> list:
        return self.ctx.storage.list_scored()

    def get_scored_topic(self, topic_id: str):
        return self.ctx.storage.get_scored(topic_id)

    def list_briefs(self) -> list:
        return self.ctx.storage.list_briefs()

    def get_brief(self, topic_id: str):
        return self.ctx.storage.get_brief(topic_id)

    def list_content_intelligence(self) -> list:
        return self.ctx.storage.list_content_intelligence()

    def get_content_intelligence(self, topic_id: str):
        return next(
            (item for item in self.ctx.storage.list_content_intelligence() if item.topic_id == topic_id),
            None,
        )

    def get_storyboard(self, topic_id: str):
        return self.ctx.storage.get_storyboard(topic_id)

    def list_manifests(self) -> list:
        return self.ctx.storage.list_manifests()

    def get_manifest(self, topic_id: str):
        return next(
            (manifest for manifest in self.ctx.storage.list_manifests() if manifest.topic_id == topic_id),
            None,
        )

    def get_topic_assets(self, topic_id: str) -> dict:
        return {
            "script": next((s for s in self.ctx.storage.list_scripts() if s.topic_id == topic_id), None),
            "carousel": next((c for c in self.ctx.storage.list_carousels() if c.topic_id == topic_id), None),
            "newsletter": next((n for n in self.ctx.storage.list_newsletters() if n.topic_id == topic_id), None),
            "thumbnail": next((t for t in self.ctx.storage.list_thumbnails() if t.topic_id == topic_id), None),
        }

    def list_workflow_states(self) -> list:
        workflow_files = list(self.ctx.workflow._dir.glob("*.json"))
        return [self.ctx.workflow.load_state(path.stem) for path in workflow_files]
