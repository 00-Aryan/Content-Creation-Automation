"""Service adapter layer for resolving backend services in Streamlit UI."""

from dotenv import load_dotenv

load_dotenv()  # Ensures .env is reliably loaded into process memory across direct subpage accesses

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import logging
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Callable, Dict, List, Optional
import streamlit as st

logger = logging.getLogger(__name__)

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
from content_creation.models.topic import TopicCategory, TopicItem, TopicMetadata, TopicStatus
from content_creation.notifications.sqlite_repository import SQLiteNotificationRepository
from content_creation.notifications.service import NotificationService
from content_creation.notifications.maintenance import NotificationMaintenanceService


@dataclass(frozen=True)
class TimedServiceResult:
    """UI-facing wrapper for a backend service result and elapsed time."""

    result: Any
    duration_seconds: float


@st.cache_resource
def ensure_database_initialized() -> bool:
    """Idempotently bootstrap all 6 subsystem schemas in content_factory.db once per application run."""
    from content_creation.platform.storage.database import get_db_path, init_content_factory_db

    root_env = os.environ.get("CONTENT_FACTORY_ROOT")
    if root_env:
        data_dir = Path(root_env)
    else:
        data_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        if not (data_dir / "config").exists():
            data_dir = Path.cwd()

    target_db = get_db_path(data_dir)
    target_db.parent.mkdir(parents=True, exist_ok=True)

    required_tables = {"jobs", "locks", "events", "notifications", "metrics", "audit"}
    if target_db.exists():
        try:
            conn = sqlite3.connect(str(target_db))
            try:
                existing_tables: set[str] = {
                    str(row[0])
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                }
            finally:
                conn.close()
            if required_tables.issubset(existing_tables):
                return True
        except sqlite3.Error as exc:
            logger.warning(
                "Failed to inspect sqlite_master on %s, falling back to full init: %s",
                target_db,
                exc,
            )

    init_content_factory_db(target_db)
    return True


@st.cache_resource
def get_context() -> ApplicationContext:
    """Bootstraps and caches the ApplicationContext relative to the workspace root.

    Resolves two independent roots:
    - data_dir: Where mutable state lives (persistent disk on Render).
                 Controlled by CONTENT_FACTORY_ROOT env var.
    - source_dir: Where immutable source code lives (config/, prompts/).
                  Resolved from this script's location.
    """
    root_env = os.environ.get("CONTENT_FACTORY_ROOT")
    if root_env:
        data_dir = Path(root_env)
    else:
        # Walk up from the current script location to locate the package directory base
        data_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        if not (data_dir / "config").exists():
            data_dir = Path.cwd()

    source_dir = Path(__file__).resolve().parent.parent.parent.parent.parent

    return ApplicationContext.create(data_dir, source_dir=source_dir)


@st.cache_resource
def get_notification_db() -> sqlite3.Connection:
    """Bootstraps and caches the notification SQLite database connection."""
    from content_creation.platform.storage.database import (
        create_connection,
        get_db_path,
        init_content_factory_db,
    )

    root_env = os.environ.get("CONTENT_FACTORY_ROOT")
    if root_env:
        data_dir = Path(root_env)
    else:
        data_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        if not (data_dir / "config").exists():
            data_dir = Path.cwd()

    cf_db = get_db_path(data_dir)
    legacy_db = data_dir / "data" / "notifications.db"

    if cf_db.exists():
        target_db = cf_db
    elif legacy_db.exists():
        target_db = legacy_db
    else:
        init_content_factory_db(cf_db)
        target_db = cf_db

    return create_connection(target_db, timeout=10.0, check_same_thread=False)


def get_notification_service() -> NotificationService:
    """Returns a cached NotificationService instance."""
    conn = get_notification_db()
    repo = SQLiteNotificationRepository(conn)
    return NotificationService(repo)


def get_notification_maintenance() -> NotificationMaintenanceService:
    """Returns a cached NotificationMaintenanceService instance."""
    conn = get_notification_db()
    repo = SQLiteNotificationRepository(conn)
    return NotificationMaintenanceService(repo)


@st.cache_resource
def get_sse_infrastructure() -> Dict[str, Any]:
    """Deprecated: returns stub SSE infrastructure without starting background socket server."""
    return {
        "server": None,
        "manager": None,
        "publisher": None,
    }


class ServiceClient:
    """Provides UI access to the concrete backend application services."""

    def __init__(self) -> None:
        ensure_database_initialized()
        self.ctx = get_context()
        from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
        self.executor = WorkflowActionExecutor()
        # Initialize SSE infrastructure
        self._sse = get_sse_infrastructure()

    def is_generation_available(self) -> bool:
        """Verifies if the generation service credentials are configured on the backend."""
        from content_creation.inference.manager import InferenceManager
        return InferenceManager.is_available()

    @property
    def score(self) -> ScoreTopicsService:
        """Resolves ScoreTopicsService."""
        return ScoreTopicsService()

    @property
    def storyboard(self) -> StoryboardService:
        """Resolves StoryboardService."""
        return StoryboardService()

    @property
    def pipeline(self) -> PipelineRunService:
        """Resolves PipelineRunService."""
        return PipelineRunService()

    @property
    def storyboard_review(self) -> StoryboardReviewService:
        """Resolves StoryboardReviewService."""
        return StoryboardReviewService()

    def _timed(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> TimedServiceResult:
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
        def _run() -> Any:
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
        def _run() -> Any:
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
        def _run() -> Any:
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
        topic_id: Optional[str] = None,
    ) -> TimedServiceResult:
        """Runs brief generation through BriefGenerationService."""
        def _run() -> Any:
            res = self.executor.execute(
                self.ctx,
                "generate_briefs",
                "brief",
                topic_id or "all",
                {
                    "top_n": top_n,
                    "topic_id": topic_id,
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
        topic_id: Optional[str] = None,
    ) -> TimedServiceResult:
        """Runs content intelligence generation."""
        def _run() -> Any:
            res = self.executor.execute(
                self.ctx,
                "generate_ci",
                "content_intelligence",
                topic_id or "all",
                {
                    "top_n": top_n,
                    "topic_id": topic_id,
                    "api_key": os.environ.get("GEMINI_API_KEY"),
                }
            )
            if not res.success:
                raise RuntimeError(f"Content intelligence failed: {res.blocking_reasons}")
            return res.raw_result
        return self._timed(_run)

    def generate_storyboards(
        self,
        top_n: int = 5,
        rate_limit_delay: float = 5.0,
        topic_id: Optional[str] = None,
    ) -> TimedServiceResult:
        """Runs storyboard generation."""
        def _run() -> Any:
            res = self.executor.execute(
                self.ctx,
                "generate_storyboards",
                "storyboard",
                topic_id or "all",
                {
                    "top_n": top_n,
                    "topic_id": topic_id,
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
        topic_id: Optional[str] = None,
    ) -> TimedServiceResult:
        """Runs storyboard-first asset generation through AssetGenerationService."""
        def _run() -> Any:
            res = self.executor.execute(
                self.ctx,
                "generate_assets",
                "assets",
                topic_id or "all",
                {
                    "top_n": top_n,
                    "topic_id": topic_id,
                    "api_key": os.environ.get("GEMINI_API_KEY"),
                }
            )
            if not res.success:
                raise RuntimeError(f"Asset generation failed: {res.blocking_reasons}")

            target_id = topic_id
            if target_id:
                try:
                    self.build_manifest(target_id)
                except Exception as ex:
                    logger.warning("Auto-compiling manifest for %s failed: %s", target_id, ex)

            return res.raw_result
        return self._timed(_run)

    def build_manifest(self, topic_id: str) -> TimedServiceResult:
        """Builds or rebuilds the manifest for a specific topic."""
        def _run() -> Any:
            res = self.executor.execute(
                self.ctx,
                "build_manifest",
                "manifest",
                topic_id,
                {},
            )
            if not res.success:
                raise RuntimeError(f"Build manifest failed: {res.blocking_reasons}")
            return res.raw_result
        return self._timed(_run)

    def apply_asset_decisions(self, topic_id: str, decisions: List[Any]) -> TimedServiceResult:
        """Applies asset review decisions through AssetReviewService."""
        def _run() -> Any:
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

    def apply_brief_decision(self, topic_id: str, decision: Any) -> TimedServiceResult:
        """Applies a brief review decision through BriefReviewService."""
        def _run() -> Any:
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

    def apply_storyboard_decision(self, topic_id: str, decision: Any) -> TimedServiceResult:
        """Applies a storyboard review decision through StoryboardReviewService."""
        def _run() -> Any:
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

    def get_review_history(self, topic_id: str) -> List[Any]:
        """Returns all review history entries for a topic via BriefReviewService."""
        return list(BriefReviewService().get_all_history(self.ctx, topic_id))

    def get_brief_review_history(self, topic_id: str) -> List[Any]:
        """Returns review history entries for briefs only."""
        return list(BriefReviewService().get_history(self.ctx, topic_id))

    def get_storyboard_review_history(self, topic_id: str) -> List[Any]:
        """Returns review history entries for storyboards only."""
        return list(StoryboardReviewService().get_history(self.ctx, topic_id))

    def get_asset_review_history(self, topic_id: str) -> List[Any]:
        """Returns review history entries for assets only."""
        return list(AssetReviewService().get_history(self.ctx, topic_id))

    def get_metric_counts(self) -> Dict[str, Any]:
        """Returns current pipeline queue counts for dashboard metrics."""
        def _count_json_files(directory: Optional[Path]) -> int:
            if not directory or not directory.exists():
                return 0
            try:
                return sum(1 for _ in directory.glob("*.json"))
            except Exception:
                return 0

        storage = self.ctx.storage
        staged_count = _count_json_files(getattr(storage, "staged_dir", None))
        scored_count = _count_json_files(getattr(storage, "scored_dir", None))
        briefs_count = _count_json_files(getattr(storage, "briefs_dir", None))
        storyboards_count = _count_json_files(getattr(storage, "storyboards_dir", None))
        manifests_count = _count_json_files(getattr(storage, "manifests_dir", None))

        return {
            "staged": staged_count,
            "staged_topics": staged_count,
            "scored": scored_count,
            "scored_topics": scored_count,
            "briefs": briefs_count,
            "storyboards": storyboards_count,
            "manifests": manifests_count,
        }

    def list_staged_topics(self) -> List[Any]:
        return list(self.ctx.storage.list_staged())

    def create_manual_topic(
        self,
        title: str,
        notes: str,
        url: str = "",
        source_id: str = "manual",
    ) -> TopicItem:
        """Create and persist a manual TopicItem into data/staged/{topic_id}.json."""
        clean_title = (title or "").strip()
        if not clean_title:
            raise ValueError("Topic title cannot be empty.")

        clean_notes = (notes or "").strip()
        clean_url = (url or "").strip()
        clean_source = (source_id or "").strip() or "manual"

        seed = clean_url if clean_url else f"{clean_source}:{clean_title}"
        topic_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()

        item = TopicItem(
            id=topic_id,
            title=clean_title,
            url=clean_url or f"urn:manual:{topic_id[:12]}",
            source=clean_source,
            published_at=datetime.now(timezone.utc).isoformat(),
            author="creator",
            raw_text=clean_notes if clean_notes else clean_title,
            excerpt=(clean_notes[:200] if clean_notes else clean_title[:200]),
            category=TopicCategory.CONCEPT,
            topic_tags=["manual", "creator_input"],
            status=TopicStatus.STAGED,
            metadata=TopicMetadata(
                source_type="manual",
                feed_id="creator_ui",
                published_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                recommended_formats=["script", "carousel", "newsletter"],
            ),
        )

        staged_dir = getattr(self.ctx.storage, "staged_dir", self.ctx.base_dir / "data" / "staged")
        staged_dir.mkdir(parents=True, exist_ok=True)
        target_file = staged_dir / f"{topic_id}.json"
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(item.model_dump_json(indent=2))

        return item

    def list_scored_topics(self) -> List[Any]:
        return list(self.ctx.storage.list_scored())

    def get_scored_topic(self, topic_id: str) -> Any:
        return self.ctx.storage.get_scored(topic_id)

    def list_briefs(self) -> List[Any]:
        return list(self.ctx.storage.list_briefs())

    def get_brief(self, topic_id: str) -> Any:
        return self.ctx.storage.get_brief(topic_id)

    def list_content_intelligence(self) -> List[Any]:
        return list(self.ctx.storage.list_content_intelligence())

    def get_content_intelligence(self, topic_id: str) -> Any:
        return next(
            (item for item in self.ctx.storage.list_content_intelligence() if item.topic_id == topic_id),
            None,
        )

    def get_storyboard(self, topic_id: str) -> Any:
        return self.ctx.storage.get_storyboard(topic_id)

    def storyboard_file_exists(self, topic_id: str) -> bool:
        """Check whether a storyboard file exists on disk for the given topic ID.

        Used by UI to distinguish between an ungenerated storyboard
        and a corrupted/empty (0-byte) file on disk.
        """
        storyboards_dir = self.ctx.storyboards_dir
        return (storyboards_dir / f"{topic_id}.json").exists()

    def list_manifests(self) -> List[Any]:
        return list(self.ctx.storage.list_manifests())

    def get_manifest(self, topic_id: str) -> Any:
        return next(
            (manifest for manifest in self.ctx.storage.list_manifests() if manifest.topic_id == topic_id),
            None,
        )

    def get_topic_assets(self, topic_id: str) -> Dict[str, Any]:
        return {
            "script": next((s for s in self.ctx.storage.list_scripts() if s.topic_id == topic_id), None),
            "carousel": next((c for c in self.ctx.storage.list_carousels() if c.topic_id == topic_id), None),
            "newsletter": next((n for n in self.ctx.storage.list_newsletters() if n.topic_id == topic_id), None),
            "thumbnail": next((t for t in self.ctx.storage.list_thumbnails() if t.topic_id == topic_id), None),
        }

    def format_voiceover_script(self, topic_id: str) -> str:
        """Extracts clean sequential spoken text formatted for TTS audio generation."""
        assets = self.get_topic_assets(topic_id)
        script = assets.get("script")
        if not script:
            return f"No video script found for topic {topic_id}."

        lines: List[str] = []
        shorts_segments = getattr(script, "shorts_segments", None)
        if shorts_segments:
            for seg in shorts_segments:
                spoken = getattr(seg, "spoken", "").strip()
                if spoken:
                    lines.append(spoken)
        else:
            hook = getattr(script, "hook", "")
            if hook and hook.strip():
                lines.append(hook.strip())
            for sec in getattr(script, "script_sections", []):
                sec_clean = (sec or "").strip()
                if sec_clean:
                    lines.append(sec_clean)
            cta = getattr(script, "cta", "")
            if cta and cta.strip():
                lines.append(cta.strip())

        return "\n\n".join(lines) if lines else f"No voiceover text found for topic {topic_id}."

    def format_production_cue_sheet(self, topic_id: str) -> str:
        """Outputs a comprehensive production cue sheet merging storyboard and script directions."""
        storyboard = self.get_storyboard(topic_id)
        assets = self.get_topic_assets(topic_id)
        script = assets.get("script")

        if not script and not storyboard:
            return f"No script or storyboard assets found for topic {topic_id}."

        scored_topic = self.get_scored_topic(topic_id)
        title = scored_topic.title if scored_topic else f"Topic {topic_id[:8]}"

        clean_title = (title or "").strip().replace("\r", "")
        clean_topic_id = (topic_id or "").strip().replace("\r", "")

        output: List[str] = []
        output.append(f"# 🎬 PRODUCTION CUE SHEET: {clean_title}")
        output.append(f"Topic ID: {clean_topic_id}")
        if storyboard:
            v_style = str(getattr(storyboard, "visual_style", "N/A") or "N/A").strip().replace("\r", "")
            v_meta = str(getattr(storyboard, "visual_metaphor", "N/A") or "N/A").strip().replace("\r", "")
            output.append(f"Visual Style: {v_style}")
            output.append(f"Visual Metaphor: {v_meta}")
        output.append("=" * 60)

        shorts_segments = getattr(script, "shorts_segments", None) if script else None
        if shorts_segments:
            for idx, seg in enumerate(shorts_segments, start=1):
                section_name = str(getattr(seg, "section", "segment") or "segment").upper().strip().replace("\r", "")
                time_range = str(getattr(seg, "time_range", "") or "").strip().replace("\r", "")
                time_header = f" [{time_range}]" if time_range else ""
                visual_text = str(getattr(seg, "visual", "") or "").strip().replace("\r", "")
                spoken_text = str(getattr(seg, "spoken", "") or "").strip().replace("\r", "")
                audio_text = str(getattr(seg, "audio", "") or "").strip().replace("\r", "")
                output.append(f"SCENE {idx}:{time_header} - {section_name}")
                output.append(f"  👁️ VISUAL:  {visual_text}")
                output.append(f"  🎙️ SPOKEN:  \"{spoken_text}\"")
                output.append(f"  🎵 AUDIO:   {audio_text}")
                output.append("-" * 40)
        elif script:
            output.append("SCENE 1: HOOK")
            output.append(f"  🎙️ SPOKEN:  \"{getattr(script, 'hook', '')}\"")
            output.append("-" * 40)
            for idx, sec in enumerate(getattr(script, "script_sections", []), start=2):
                output.append(f"SCENE {idx}: BODY")
                output.append(f"  🎙️ SPOKEN:  \"{sec}\"")
                output.append("-" * 40)
            output.append(f"SCENE {len(getattr(script, 'script_sections', [])) + 2}: CTA")
            output.append(f"  🎙️ SPOKEN:  \"{getattr(script, 'cta', '')}\"")
            output.append("-" * 40)
        elif storyboard:
            output.append("SCENE 1: HOOK")
            output.append(f"  👁️ VISUAL:  {getattr(storyboard, 'visual_metaphor', '')}")
            output.append(f"  🎙️ HOOK:    \"{getattr(storyboard, 'script_hook', '')}\"")
            output.append("-" * 40)
            output.append("SCENE 2: CTA")
            output.append(f"  🎙️ CTA:     \"{getattr(storyboard, 'script_cta', '')}\"")
            output.append("-" * 40)

        return "\n".join(output)

    def list_workflow_states(self) -> List[Any]:
        workflow_files = list(self.ctx.workflow._dir.glob("*.json"))
        return [self.ctx.workflow.load_state(path.stem) for path in workflow_files]

    # --- Notification Methods ---

    @property
    def notification_service(self) -> NotificationService:
        """Returns the NotificationService for notification operations."""
        return get_notification_service()

    @property
    def notification_maintenance(self) -> NotificationMaintenanceService:
        """Returns the NotificationMaintenanceService for cleanup operations."""
        return get_notification_maintenance()

    def get_notification_unread_count(self) -> int:
        """Returns the current unread notification count."""
        return int(self.notification_service.unread_count())

    def get_notification_summary(self) -> Any:
        """Returns the notification summary for dashboard display."""
        return self.notification_service.summary()

    # --- Operations Dashboard & Event Timeline Facade Methods ---

    def get_operations_snapshot(self) -> Any:
        """Build and return a unified platform observability snapshot.

        Coordinates queue, lock, event, notification, metric, and audit
        subsystems via ObservabilityService, closing database connections cleanly.
        """
        import importlib
        from dataclasses import replace
        from content_creation.platform.storage.database import create_connection

        data_dir = self.ctx.base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        cf_db = data_dir / "content_factory.db"
        discrete_jobs = data_dir / "jobs.db"

        if cf_db.exists():
            use_consolidated = True
        elif discrete_jobs.exists():
            use_consolidated = False
        else:
            from content_creation.platform.storage.database import init_content_factory_db

            init_content_factory_db(cf_db)
            use_consolidated = True

        queue_engine = None
        lock_manager = None
        lock_repo = None
        event_repo = None
        notification_svc = None
        metrics_repo = None
        kpi_catalog = None
        telemetry_svc = None
        audit_repo = None
        compliance_svc = None

        main_conn = None
        job_conn = None
        lock_conn = None
        notif_conn = None

        try:
            ObsServiceMod = importlib.import_module("content_creation.platform.observability.service")
            HealthMod = importlib.import_module("content_creation.platform.observability.health")

            if use_consolidated:
                main_conn = create_connection(cf_db, timeout=5.0)
                job_conn = main_conn
                lock_conn = main_conn
                notif_conn = main_conn
                event_db_path = str(cf_db)
                metrics_db_path = str(cf_db)
                audit_db_path = str(cf_db)
            else:
                def _open_db(name: str) -> sqlite3.Connection:
                    db_path = data_dir / name
                    conn = sqlite3.connect(str(db_path), timeout=5)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA busy_timeout=5000")
                    return conn

                job_conn = _open_db("jobs.db")
                lock_conn = _open_db("locks.db")
                notif_conn = _open_db("notifications.db")
                event_db_path = str(data_dir / "events.db")
                metrics_db_path = str(data_dir / "metrics.db")
                audit_db_path = str(data_dir / "audit.db")

            try:
                JobSqliteMod = importlib.import_module("content_creation.jobs.sqlite_repository")
                LockSqliteMod = importlib.import_module("content_creation.jobs.sqlite_lock_repository")
                LockMgrMod = importlib.import_module("content_creation.jobs.lock_manager")
                QueueEngineMod = importlib.import_module("content_creation.jobs.queue_engine")

                job_repo = JobSqliteMod.SQLiteJobRepository(job_conn)
                lock_repo = LockSqliteMod.SQLiteLockRepository(lock_conn)
                lock_manager = LockMgrMod.LockManager(repository=lock_repo)
                queue_engine = QueueEngineMod.QueueEngine(repository=job_repo, lock_manager=lock_manager)
            except Exception as e:
                logger.warning("Failed to initialize Job Queue for operations snapshot: %s", e)

            try:
                EventSqliteMod = importlib.import_module("content_creation.events.store.sqlite_repository")
                event_repo = EventSqliteMod.SQLiteEventRepository(event_db_path)
            except Exception as e:
                logger.warning("Failed to initialize Event Store for operations snapshot: %s", e)

            try:
                NotifSqliteMod = importlib.import_module("content_creation.notifications.sqlite_repository")
                NotifSvcMod = importlib.import_module("content_creation.notifications.service")
                notif_repo = NotifSqliteMod.SQLiteNotificationRepository(notif_conn)
                notification_svc = NotifSvcMod.NotificationService(repository=notif_repo)
            except Exception as e:
                logger.warning("Failed to initialize Notification Service for operations snapshot: %s", e)

            try:
                MetricSqliteMod = importlib.import_module("content_creation.metrics.sqlite_repository")
                KpiMod = importlib.import_module("content_creation.metrics.kpi")
                TelemetryMod = importlib.import_module("content_creation.metrics.telemetry")
                metrics_repo = MetricSqliteMod.SQLiteMetricRepository(metrics_db_path)
                kpi_catalog = KpiMod.KPICatalog(repository=metrics_repo)
                telemetry_svc = TelemetryMod.TelemetryService(metrics_repository=metrics_repo, event_repository=event_repo)
            except Exception as e:
                logger.warning("Failed to initialize Metrics Repository for operations snapshot: %s", e)

            try:
                AuditSqliteMod = importlib.import_module("content_creation.audit.sqlite_repository")
                ComplianceMod = importlib.import_module("content_creation.audit.compliance")
                audit_repo = AuditSqliteMod.SQLiteAuditRepository(audit_db_path)
                compliance_svc = ComplianceMod.ComplianceReportService(repository=audit_repo)
            except Exception as e:
                logger.warning("Failed to initialize Audit Repository for operations snapshot: %s", e)

            service = ObsServiceMod.ObservabilityService(
                queue_engine=queue_engine,
                lock_manager=lock_manager,
                lock_repository=lock_repo,
                event_repository=event_repo,
                notification_service=notification_svc,
                connection_manager=None,
                metrics_repository=metrics_repo,
                kpi_catalog=kpi_catalog,
                telemetry_service=telemetry_svc,
                audit_repository=audit_repo,
                compliance_service=compliance_svc,
            )
            snapshot = service.snapshot()

            w_metrics = snapshot.worker_metrics or {}
            is_worker_running = w_metrics.get("is_running", False)

            q_metrics = snapshot.queue_metrics or {}
            queued_jobs = q_metrics.get("queued_count", 0)
            running_jobs = q_metrics.get("running_count", 0)
            has_jobs = queued_jobs > 0 or running_jobs > 0

            new_alerts = []
            for alert in snapshot.alerts:
                if alert.rule_id == "WORKER_OFFLINE" and not is_worker_running:
                    if not has_jobs:
                        new_alerts.append(
                            HealthMod.OperationalAlert(
                                rule_id=alert.rule_id,
                                severity=HealthMod.AlertSeverity.INFO,
                                component=alert.component,
                                title="Worker Daemon: Not running (manual mode)",
                                message="No active workers are running. This is normal when running manually (no jobs are queued).",
                                recommended_action="Start the worker daemon if you intend to run background tasks.",
                                metrics=alert.metrics,
                                timestamp=alert.timestamp,
                            )
                        )
                    else:
                        new_alerts.append(alert)
                else:
                    new_alerts.append(alert)

            new_components = []
            for comp in snapshot.components:
                # Exclude retired SSE component
                if comp.component == HealthMod.ComponentType.SSE:
                    continue
                if comp.component == HealthMod.ComponentType.WORKER and not is_worker_running:
                    if not has_jobs:
                        new_components.append(
                            HealthMod.SystemComponentHealth(
                                component=comp.component,
                                name=comp.name,
                                status=HealthMod.HealthStatus.HEALTHY,
                                message="Not running (expected in manual operation mode)",
                                metrics=comp.metrics,
                                last_checked=comp.last_checked,
                            )
                        )
                    else:
                        new_components.append(
                            HealthMod.SystemComponentHealth(
                                component=comp.component,
                                name=comp.name,
                                status=HealthMod.HealthStatus.UNHEALTHY,
                                message="No active workers but jobs are queued — pipeline may be stalled",
                                metrics=comp.metrics,
                                last_checked=comp.last_checked,
                            )
                        )
                else:
                    new_components.append(comp)

            overall = ObsServiceMod.ObservabilityService._derive_overall_status(new_components)

            snapshot = replace(
                snapshot,
                components=new_components,
                alerts=new_alerts,
                overall_status=overall,
            )

            return snapshot
        except Exception as e:
            logger.error("Failed to build operations snapshot: %s", e)
            try:
                HealthMod = importlib.import_module("content_creation.platform.observability.health")
                return HealthMod.DashboardSnapshot(
                    overall_status=HealthMod.HealthStatus.UNKNOWN,
                    components=[
                        HealthMod.SystemComponentHealth(
                            component=HealthMod.ComponentType.QUEUE,
                            name="System",
                            status=HealthMod.HealthStatus.UNKNOWN,
                            message=f"Failed to build snapshot: {e}",
                        )
                    ],
                )
            except Exception:
                return None
        finally:
            if main_conn is not None:
                try:
                    main_conn.close()
                except Exception as e:
                    logger.warning("Failed to close main db connection: %s", e)
            else:
                for conn in [job_conn, lock_conn, notif_conn]:
                    if conn is not None:
                        try:
                            conn.close()
                        except Exception as e:
                            logger.warning("Failed to close db connection: %s", e)
            for r in [event_repo, metrics_repo, audit_repo]:
                if r is not None:
                    try:
                        r.close()
                    except Exception as e:
                        logger.warning("Failed to close repo: %s", e)

    def get_event_timeline(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Any]:
        """Query and return event records formatted for UI consumption."""
        data_dir = self.ctx.base_dir / "data"
        cf_db = data_dir / "content_factory.db"
        legacy_db = data_dir / "events.db"
        target_db = cf_db if cf_db.exists() else (legacy_db if legacy_db.exists() else None)
        if target_db is None:
            return []
        try:
            import importlib
            EventSqliteMod = importlib.import_module("content_creation.events.store.sqlite_repository")
            TimelineMod = importlib.import_module("content_creation.events.store.timeline")
            event_repo = EventSqliteMod.SQLiteEventRepository(str(target_db))
            try:
                timeline_svc = TimelineMod.EventTimelineService(event_repo)
                if entity_type and entity_id:
                    return list(timeline_svc.entity_history(entity_type, entity_id, limit=limit))
                elif category:
                    return list(timeline_svc.recent_events(category=category, page_size=limit).events)
                else:
                    return list(timeline_svc.recent_events(page_size=limit).events)
            finally:
                event_repo.close()
        except Exception as e:
            logger.warning("Failed to query event timeline: %s", e)
            return []

    # --- SSE Streaming Methods (Deprecated Shims) ---

    @property
    def sse_port(self) -> int:
        """Returns the legacy SSE server port for backwards compatibility."""
        return 8502

    def publish_notification_event(self, notification: Any) -> None:
        """Publish a notification event (no-op shim; UI uses fragment polling)."""
        pass

    def publish_read_event(self, notification_id: Any) -> None:
        """Publish a notification read event (no-op shim; UI uses fragment polling)."""
        pass

    def publish_archive_event(self, notification_id: Any) -> None:
        """Publish a notification archive event (no-op shim; UI uses fragment polling)."""
        pass
