"""Workflow Action Executor adoption and boundary enforcement layer.

This module acts as the canonical execution layer of the workflow pipeline.
It intercepts all mutating operations, validates them using the ActionAvailabilityEngine
and ReviewTransitionEngine, invokes the underlying services, records audit logs,
and returns structured ActionExecutionResult payloads.
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from content_creation.shared.enums import ReviewStatus
from content_creation.workflow.action_availability_engine import ActionAvailabilityEngine
from content_creation.workflow.review_transition_engine import ReviewTransitionEngine
from content_creation.workflow.states import ArtifactLifecycleState, get_lifecycle_state
from content_creation.workflow.state_mappers import ReviewStatusMapper
from content_creation.models.review_history import ReviewHistoryEntry

logger = logging.getLogger(__name__)


class ActionExecutionStatus(str, Enum):
    """Execution outcome status for a workflow action."""
    SUCCESS = "success"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"


class ActionExecutionResult:
    """Canonical result object returned by the WorkflowActionExecutor."""

    def __init__(
        self,
        action_id: str,
        success: bool,
        execution_status: ActionExecutionStatus,
        affected_artifacts: Dict[str, str],
        warnings: List[str],
        blocking_reasons: List[str],
        execution_time: float,
        emitted_events: Optional[List[str]] = None,
        raw_result: Optional[Any] = None,
    ) -> None:
        self.action_id = action_id
        self.success = success
        self.execution_status = execution_status
        self.affected_artifacts = affected_artifacts
        self.warnings = warnings
        self.blocking_reasons = blocking_reasons
        self.execution_time = execution_time
        self.emitted_events = emitted_events or []
        self.raw_result = raw_result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "success": self.success,
            "execution_status": self.execution_status.value,
            "affected_artifacts": self.affected_artifacts,
            "warnings": self.warnings,
            "blocking_reasons": self.blocking_reasons,
            "execution_time": self.execution_time,
            "emitted_events": self.emitted_events,
        }

    @classmethod
    def fail_blocked(cls, action_id: str, blocking_code: str, message: str) -> "ActionExecutionResult":
        return cls(
            action_id=action_id,
            success=False,
            execution_status=ActionExecutionStatus.BLOCKED,
            affected_artifacts={},
            warnings=[],
            blocking_reasons=[f"{blocking_code}: {message}"],
            execution_time=0.0,
            emitted_events=[],
            raw_result=None,
        )


class WorkflowActionExecutor:
    """Canonical, stateless workflow action execution manager."""

    def __init__(
        self,
        availability_engine: Optional[ActionAvailabilityEngine] = None,
        transition_engine: Optional[ReviewTransitionEngine] = None,
    ) -> None:
        self._availability_engine = availability_engine or ActionAvailabilityEngine()
        self._transition_engine = transition_engine or ReviewTransitionEngine()

    def execute(
        self,
        ctx: Any,
        action_id: str,
        target_artifact_type: str,
        target_artifact_id: str,
        payload: Dict[str, Any],
        operator_id: str = "system",
        notes: Optional[str] = None,
    ) -> ActionExecutionResult:
        """Execute the workflow action after running gating and dependency checks.

        Parameters
        ----------
        ctx : ApplicationContext
            Dependency context container.
        action_id : str
            ID of the action to execute (e.g., 'approve_brief').
        target_artifact_type : str
            Target artifact type (e.g., 'brief', 'storyboard').
        target_artifact_id : str
            Unique ID of the artifact (usually topic_id).
        payload : Dict[str, Any]
            Parameters/API keys required by the underlying service.
        operator_id : str
            Operator classification ('streamlit', 'cli', 'system').
        notes : str, optional
            Operator audit notes/rejection reasons.
        """
        start_time = time.perf_counter()

        # 1. Resolve current state and dependencies
        current_state = self._resolve_lifecycle_state(ctx, target_artifact_type, target_artifact_id, payload)
        dependencies = self._resolve_dependencies(ctx, target_artifact_type, target_artifact_id, action_id, payload)

        # 2. Check Action Availability Engine
        is_batch_idempotent_action = (
            target_artifact_id == "all"
            and action_id in {
                "generate_briefs",
                "generate_ci",
                "generate_storyboards",
                "generate_assets",
                "build_all_manifests",
            }
        )

        if not is_batch_idempotent_action and not self._availability_engine.is_action_available(
            action_id, target_artifact_type, current_state, dependencies
        ):
            reasons = self._availability_engine.get_blocking_reasons(
                action_id, target_artifact_type, current_state, dependencies
            )
            blocking_reason = reasons[0].blocking_message if reasons else "Action blocked by availability engine."
            execution_time = time.perf_counter() - start_time
            return ActionExecutionResult(
                action_id=action_id,
                success=False,
                execution_status=ActionExecutionStatus.BLOCKED,
                affected_artifacts={},
                warnings=[],
                blocking_reasons=[blocking_reason or "Action blocked by availability engine."],
                execution_time=execution_time,
                emitted_events=[],
                raw_result=None,
            )

        # 3. If action is an approval/rejection transition, validate transition graph
        if action_id in {
            "approve_brief",
            "reject_brief",
            "approve_storyboard",
            "reject_storyboard",
            "approve_asset",
            "reject_asset",
        }:
            from_status = self._map_to_review_status(current_state)
            to_status = self._map_target_review_status(action_id)
            val_result = self._transition_engine.validate_transition(from_status, to_status)
            if not val_result.valid:
                execution_time = time.perf_counter() - start_time
                return ActionExecutionResult(
                    action_id=action_id,
                    success=False,
                    execution_status=ActionExecutionStatus.BLOCKED,
                    affected_artifacts={},
                    warnings=[],
                    blocking_reasons=[val_result.reason],
                    execution_time=execution_time,
                    emitted_events=[],
                    raw_result=None,
                )

        # 4. Invoke the target service method
        correlation_id = payload.get("correlation_id", "default_corr")
        if action_id == "run_pipeline":
            try:
                from content_creation.events.bus import get_event_bus
                from content_creation.events.factory import create_pipeline_event
                from content_creation.events.models import EventType
                bus = get_event_bus()
                evt = create_pipeline_event(
                    event_type=EventType.PIPELINE_STARTED,
                    week_start=target_artifact_id,
                    operator_id=operator_id,
                    correlation_id=correlation_id,
                )
                bus.publish(evt)
            except Exception as ex:
                logger.warning(f"Failed to publish pipeline_started event: {ex}")

        try:
            affected_artifacts, raw_result = self._dispatch_to_service(
                ctx, action_id, target_artifact_type, target_artifact_id, payload, notes
            )
        except Exception as e:
            logger.error(f"Failed to execute action {action_id}: {e}", exc_info=True)
            if action_id == "run_pipeline":
                try:
                    from content_creation.events.bus import get_event_bus
                    from content_creation.events.factory import create_pipeline_event
                    from content_creation.events.models import EventType
                    bus = get_event_bus()
                    evt = create_pipeline_event(
                        event_type=EventType.PIPELINE_FAILED,
                        week_start=target_artifact_id,
                        operator_id=operator_id,
                        correlation_id=correlation_id,
                        error_message=str(e),
                    )
                    bus.publish(evt)
                except Exception as ex:
                    logger.warning(f"Failed to publish pipeline_failed event: {ex}")
            execution_time = time.perf_counter() - start_time
            return ActionExecutionResult(
                action_id=action_id,
                success=False,
                execution_status=ActionExecutionStatus.FAILED,
                affected_artifacts={},
                warnings=[],
                blocking_reasons=[f"Execution failed: {str(e)}"],
                execution_time=execution_time,
                emitted_events=[],
                raw_result=None,
            )

        execution_time = time.perf_counter() - start_time

        try:
            from content_creation.events.bus import get_event_bus
            from content_creation.events.factory import create_workflow_event, create_pipeline_event
            from content_creation.events.models import EventType
            bus = get_event_bus()
            event_type = None

            if action_id == "generate_briefs":
                event_type = EventType.BRIEF_GENERATED
            elif action_id == "generate_ci":
                event_type = EventType.CI_GENERATED
            elif action_id == "generate_storyboards":
                event_type = EventType.STORYBOARD_GENERATED
            elif action_id == "generate_assets":
                event_type = EventType.ASSET_GENERATED
            elif action_id == "build_manifest":
                event_type = EventType.MANIFEST_BUILT

            elif action_id == "approve_brief":
                event_type = EventType.BRIEF_APPROVED
            elif action_id == "reject_brief":
                event_type = EventType.BRIEF_REJECTED
            elif action_id == "approve_storyboard":
                event_type = EventType.STORYBOARD_APPROVED
            elif action_id == "reject_storyboard":
                event_type = EventType.STORYBOARD_REJECTED
            elif action_id == "approve_asset":
                event_type = EventType.ASSET_APPROVED
            elif action_id == "reject_asset":
                event_type = EventType.ASSET_REJECTED

            elif action_id == "run_pipeline":
                event_type = EventType.PIPELINE_COMPLETED

            if event_type:
                if event_type in (EventType.PIPELINE_COMPLETED, EventType.PIPELINE_STARTED):
                    evt = create_pipeline_event(
                        event_type=event_type,
                        week_start=target_artifact_id,
                        operator_id=operator_id,
                        correlation_id=correlation_id,
                    )
                else:
                    evt = create_workflow_event(
                        event_type=event_type,
                        topic_id=target_artifact_id,
                        operator_id=operator_id,
                        correlation_id=correlation_id,
                        extra_payload=affected_artifacts,
                    )
                bus.publish(evt)
        except Exception as e:
            logger.warning(f"Failed to publish action success event: {e}")

        return ActionExecutionResult(
            action_id=action_id,
            success=True,
            execution_status=ActionExecutionStatus.SUCCESS,
            affected_artifacts=affected_artifacts,
            warnings=[],
            blocking_reasons=[],
            execution_time=execution_time,
            emitted_events=[f"event_{action_id}_{int(start_time)}"],
            raw_result=raw_result,
        )

    # ------------------------------------------------------------------
    # Resolvers and Mappers
    # ------------------------------------------------------------------

    def _resolve_lifecycle_state(
        self, ctx: Any, artifact_type: str, topic_id: str, payload: Dict[str, Any]
    ) -> ArtifactLifecycleState:
        if artifact_type == "topic":
            if topic_id == "all":
                if ctx.storage.list_scored():
                    return ArtifactLifecycleState.APPROVED
                return ArtifactLifecycleState.MISSING
            topic = ctx.storage.get_scored(topic_id)
            if topic is None:
                topic = ctx.storage.get_staged(topic_id)
            if topic is None:
                return ArtifactLifecycleState.MISSING
            return get_lifecycle_state(topic_status=topic.status.value)

        elif artifact_type == "brief":
            if topic_id == "all":
                return ArtifactLifecycleState.APPROVED if ctx.storage.list_briefs() else ArtifactLifecycleState.MISSING
            brief = ctx.storage.get_brief(topic_id)
            if brief is None:
                return ArtifactLifecycleState.MISSING
            return get_lifecycle_state(review_status=brief.review_status.value)

        elif artifact_type == "content_intelligence":
            if topic_id == "all":
                return ArtifactLifecycleState.APPROVED if ctx.storage.list_content_intelligence() else ArtifactLifecycleState.MISSING
            ci = next((item for item in ctx.storage.list_content_intelligence() if item.topic_id == topic_id), None)
            if ci is None:
                return ArtifactLifecycleState.MISSING
            return get_lifecycle_state(review_status=ci.review_status.value)

        elif artifact_type == "storyboard":
            if topic_id == "all":
                return ArtifactLifecycleState.APPROVED if ctx.storage.list_storyboards() else ArtifactLifecycleState.MISSING
            sb = ctx.storage.get_storyboard(topic_id)
            if sb is None:
                return ArtifactLifecycleState.MISSING
            return get_lifecycle_state(review_status=sb.review_status.value)

        elif artifact_type == "assets":
            if topic_id == "all":
                return ArtifactLifecycleState.APPROVED if ctx.storage.list_manifests() else ArtifactLifecycleState.MISSING
            asset_type = payload.get("asset_type")
            if asset_type:
                asset_obj = self._get_specific_asset(ctx, topic_id, asset_type)
                if asset_obj is None:
                    return ArtifactLifecycleState.MISSING
                return get_lifecycle_state(review_status=asset_obj.review_status.value)
            else:
                # Overall assets status: check if manifest exists
                manifest = next((m for m in ctx.storage.list_manifests() if m.topic_id == topic_id), None)
                if manifest is None:
                    return ArtifactLifecycleState.MISSING
                return get_lifecycle_state(manifest_overall_status=manifest.overall_status)

        elif artifact_type == "manifest":
            if topic_id == "all":
                return ArtifactLifecycleState.APPROVED if ctx.storage.list_manifests() else ArtifactLifecycleState.MISSING
            manifest = next((m for m in ctx.storage.list_manifests() if m.topic_id == topic_id), None)
            if manifest is None:
                return ArtifactLifecycleState.MISSING
            return get_lifecycle_state(manifest_overall_status=manifest.overall_status)

        elif artifact_type == "weekly_calendar":
            calendars = ctx.storage.list_calendars()
            cal = next((c for c in calendars if c.week_start == topic_id), None)
            if cal is None:
                return ArtifactLifecycleState.MISSING
            return ArtifactLifecycleState.DRAFT

        return ArtifactLifecycleState.MISSING

    def _resolve_dependencies(
        self, ctx: Any, artifact_type: str, topic_id: str, action_id: str, payload: Dict[str, Any]
    ) -> Dict[str, ArtifactLifecycleState]:
        deps = {}

        if action_id == "generate_briefs":
            deps["topic"] = self._resolve_lifecycle_state(ctx, "topic", topic_id, payload)

        elif action_id == "generate_ci":
            deps["brief"] = self._resolve_lifecycle_state(ctx, "brief", topic_id, payload)

        elif action_id == "generate_storyboards":
            deps["brief"] = self._resolve_lifecycle_state(ctx, "brief", topic_id, payload)
            deps["content_intelligence"] = self._resolve_lifecycle_state(ctx, "content_intelligence", topic_id, payload)

        elif action_id == "generate_assets":
            deps["storyboard"] = self._resolve_lifecycle_state(ctx, "storyboard", topic_id, payload)

        elif action_id == "build_manifest":
            deps["brief"] = self._resolve_lifecycle_state(ctx, "brief", topic_id, payload)

        elif action_id == "plan_week":
            manifests = ctx.storage.list_manifests()
            has_approved_manifest = any(
                m.overall_status == "complete" or m.ready_for_planner for m in manifests
            )
            deps["manifest"] = (
                ArtifactLifecycleState.APPROVED if has_approved_manifest else ArtifactLifecycleState.MISSING
            )

        elif action_id == "dry_run":
            deps["weekly_calendar"] = self._resolve_lifecycle_state(ctx, "weekly_calendar", topic_id, payload)

        elif action_id == "publish":
            dryruns = ctx.storage.list_dryruns()
            report = next((r for r in dryruns if r.week_start == topic_id), None)
            if report and report.blocked_count == 0:
                deps["dry_run"] = ArtifactLifecycleState.APPROVED
            else:
                deps["dry_run"] = ArtifactLifecycleState.FAILED

            calendars = ctx.storage.list_calendars()
            cal = next((c for c in calendars if c.week_start == topic_id), None)
            if cal:
                all_approved = True
                for post in cal.posts:
                    asset_obj = self._get_specific_asset(ctx, post.topic_id, post.format)
                    if asset_obj is None or asset_obj.review_status.value != "approved":
                        all_approved = False
                        break
                deps["assets"] = ArtifactLifecycleState.APPROVED if all_approved else ArtifactLifecycleState.FAILED
            else:
                deps["assets"] = ArtifactLifecycleState.MISSING

        return deps

    def _get_specific_asset(self, ctx: Any, topic_id: str, asset_type: str) -> Optional[Any]:
        if asset_type == "brief":
            return ctx.storage.get_brief(topic_id)
        elif asset_type == "storyboard":
            return ctx.storage.get_storyboard(topic_id)
        elif asset_type == "script":
            return next((s for s in ctx.storage.list_scripts() if s.topic_id == topic_id), None)
        elif asset_type == "carousel":
            return next((c for c in ctx.storage.list_carousels() if c.topic_id == topic_id), None)
        elif asset_type == "newsletter":
            return next((n for n in ctx.storage.list_newsletters() if n.topic_id == topic_id), None)
        elif asset_type == "thumbnail":
            return next((t for t in ctx.storage.list_thumbnails() if t.topic_id == topic_id), None)
        return None

    def _map_to_review_status(self, lifecycle_state: ArtifactLifecycleState) -> ReviewStatus:
        from_review = ReviewStatusMapper.get_mapped_values()
        # Find review status matching lifecycle state value
        for rev_val, life_val in from_review.items():
            if life_val == lifecycle_state.value:
                return ReviewStatus(rev_val)
        return ReviewStatus.DRAFT

    def _map_target_review_status(self, action_id: str) -> ReviewStatus:
        if "approve" in action_id:
            return ReviewStatus.APPROVED
        return ReviewStatus.REJECTED

    # ------------------------------------------------------------------
    # Dispatch Service Layer Mutators
    # ------------------------------------------------------------------

    def _dispatch_to_service(
        self,
        ctx: Any,
        action_id: str,
        target_artifact_type: str,
        target_artifact_id: str,
        payload: Dict[str, Any],
        notes: Optional[str] = None,
    ) -> tuple[Dict[str, str], Any]:
        """Dynamically imports and calls the appropriate service method."""
        if action_id == "collect":
            from content_creation.application.collect_topics_service import CollectTopicsService
            service = CollectTopicsService()
            result = service.run(ctx, source_filter=payload.get("source"))
            return {"collected_count": str(result.count)}, result

        elif action_id == "score_topics":
            from content_creation.application.score_topics_service import ScoreTopicsService
            service = ScoreTopicsService()
            result = service.run(ctx, limit=payload.get("limit"))
            return {
                "scored_count": str(result.scored_count),
                "rejected_count": str(result.rejected_count),
            }, result

        elif action_id == "generate_briefs":
            from content_creation.application.brief_generation_service import BriefGenerationService
            service = BriefGenerationService()
            result = service.run(
                ctx,
                top_n=payload.get("top_n", 5),
                api_key=payload.get("api_key"),
            )
            return {"generated_count": str(result.generated_count), "failures": str(len(result.failures))}, result

        elif action_id == "generate_ci":
            from content_creation.application.content_intelligence_service import ContentIntelligenceService
            service = ContentIntelligenceService()
            result = service.run(
                ctx,
                top_n=payload.get("top_n", 5),
                api_key=payload.get("api_key"),
            )
            return {"generated_count": str(result.generated_count), "failures": str(len(result.failures))}, result

        elif action_id == "generate_storyboards":
            from content_creation.application.storyboard_service import StoryboardService
            service = StoryboardService()
            result = service.run(
                ctx,
                top_n=payload.get("top_n", 5),
                api_key=payload.get("api_key"),
            )
            return {"generated_count": str(result.generated_count), "failures": str(len(result.failures))}, result

        elif action_id == "generate_assets":
            from content_creation.application.asset_generation_service import AssetGenerationService
            service = AssetGenerationService()
            result = service.run(
                ctx,
                top_n=payload.get("top_n", 5),
                api_key=payload.get("api_key"),
            )
            return {"counts": str(result.counts), "failed_count": str(result.failed_count)}, result

        elif action_id in {"approve_brief", "reject_brief"}:
            from content_creation.application.brief_review_service import BriefReviewService, BriefDecision
            service = BriefReviewService()
            status = ReviewStatus.APPROVED if action_id == "approve_brief" else ReviewStatus.REJECTED
            decision = BriefDecision(status=status, notes=notes)
            result = service.apply_decision(ctx, topic_id=target_artifact_id, decision=decision)
            return {
                "brief": f"data/briefs/{target_artifact_id}.json",
                "new_status": result.new_status.value,
            }, result

        elif action_id in {"approve_storyboard", "reject_storyboard"}:
            from content_creation.application.storyboard_review_service import StoryboardReviewService, StoryboardDecision
            service = StoryboardReviewService()
            status = ReviewStatus.APPROVED if action_id == "approve_storyboard" else ReviewStatus.REJECTED
            decision = StoryboardDecision(status=status, notes=notes)
            result = service.apply_decision(ctx, topic_id=target_artifact_id, decision=decision)
            return {
                "storyboard": f"data/storyboards/{target_artifact_id}.json",
                "new_status": result.new_status.value,
            }, result

        elif action_id in {"approve_asset", "reject_asset"}:
            from content_creation.application.asset_review_service import AssetReviewService, AssetDecision
            service = AssetReviewService()
            status = ReviewStatus.APPROVED if action_id == "approve_asset" else ReviewStatus.REJECTED
            decision = AssetDecision(
                asset_type=payload["asset_type"], status=status, rejection_reason=notes
            )
            result = service.apply_decisions(ctx, topic_id=target_artifact_id, decisions=[decision])
            return {
                "asset_type": payload["asset_type"],
                "approved_count": str(result.approved_count),
                "rejected_count": str(result.rejected_count),
            }, result

        elif action_id == "batch_approve":
            asset_type = payload.get("asset_type", "all")
            exclude_incomplete = payload.get("exclude_incomplete", False)

            asset_types = ["brief", "script", "carousel", "newsletter", "thumbnail"]
            if asset_type != "all":
                asset_types = [asset_type]

            list_funcs = {
                "brief": ctx.storage.list_briefs,
                "script": ctx.storage.list_scripts,
                "carousel": ctx.storage.list_carousels,
                "newsletter": ctx.storage.list_newsletters,
                "thumbnail": ctx.storage.list_thumbnails,
            }

            approved_count = 0

            for atype in asset_types:
                list_func = list_funcs.get(atype)
                if not list_func:
                    continue
                try:
                    assets = list_func()
                except Exception:
                    continue

                for asset in assets:
                    status = asset.review_status.value if hasattr(asset, "review_status") and asset.review_status else None
                    if status in ("approved", "rejected"):
                        continue

                    if exclude_incomplete:
                        asset_dict = asset.model_dump() if hasattr(asset, "model_dump") else asset.dict()
                        has_incomplete = any(
                            v == "needs_review"
                            for k, v in asset_dict.items()
                            if k != "review_status" and isinstance(v, str)
                        )
                        if has_incomplete:
                            continue

                    topic_id = asset.topic_id
                    ctx.storage.update_asset_status(atype, topic_id, ReviewStatus.APPROVED)
                    approved_count += 1

                    # Log ReviewHistoryEntry to close INC-05
                    entry = ReviewHistoryEntry(
                        topic_id=topic_id,
                        asset_type=atype,
                        action="approved",
                        previous_status=ReviewStatus(status) if status else None,
                        new_status=ReviewStatus.APPROVED,
                        notes="Batch approved via WorkflowActionExecutor",
                    )
                    ctx.storage.save_review_history_entry(entry)

            # Rebuild manifests
            from content_creation.manifest import ManifestBuilder
            builder = ManifestBuilder(ctx.storage)
            manifests = builder.build_all()
            for m in manifests:
                ctx.storage.save_manifest(m)

            return {"approved_count": str(approved_count), "manifests_rebuilt": str(len(manifests))}, approved_count

        elif action_id == "build_manifest":
            from content_creation.manifest import ManifestBuilder
            # Load the brief or topic to get topic_title and source_url
            brief = ctx.storage.get_scored(target_artifact_id)
            if not brief:
                briefs = ctx.storage.list_briefs()
                matching = [b for b in briefs if b.topic_id == target_artifact_id]
                if matching:
                    brief = matching[0]

            topic_title = getattr(brief, "title", getattr(brief, "why_it_matters", "unknown"))
            source_url = getattr(brief, "url", getattr(brief, "source_url", "unknown"))

            builder = ManifestBuilder(ctx.storage)
            manifest = builder.build(
                topic_id=target_artifact_id,
                topic_title=topic_title,
                source_url=source_url,
            )
            ctx.storage.save_manifest(manifest)
            return {"manifest_path": f"data/manifests/{target_artifact_id}.json"}, manifest

        elif action_id == "build_all_manifests":
            from content_creation.manifest import ManifestBuilder
            builder = ManifestBuilder(ctx.storage)
            manifests = builder.build_all()
            for manifest in manifests:
                ctx.storage.save_manifest(manifest)
            return {"manifest_count": str(len(manifests))}, manifests

        elif action_id == "plan_week":
            from content_creation.planning.planner import PostingPlanner
            publishing_config_path = ctx.base_dir / "config" / "publishing.yaml"
            planner = PostingPlanner(ctx.storage, publishing_config_path)
            calendar = planner.plan_week(payload["week_start_date"])
            ctx.storage.save_calendar(calendar)
            return {"calendar_path": f"data/calendars/{calendar.week_start}.json"}, calendar

        elif action_id == "dry_run":
            from content_creation.planning.dryrun import DryRunValidator
            publishing_config_path = ctx.base_dir / "config" / "publishing.yaml"
            calendars = ctx.storage.list_calendars()
            week_start = payload.get("week_start")
            cal = next((c for c in calendars if c.week_start == week_start), None)
            if cal is None:
                raise ValueError(f"No calendar found for week_start: {week_start}")
            validator = DryRunValidator(ctx.storage, publishing_config_path)
            report = validator.run(cal)
            ctx.storage.save_dryrun(report)
            return {"dry_run_path": f"data/dryruns/{report.week_start}.json"}, report

        elif action_id == "init_analytics":
            from content_creation.models.analytics import PostAnalytics
            from datetime import datetime, timezone
            calendars = ctx.storage.list_calendars()
            week_start = payload.get("week_start")
            cal = next((c for c in calendars if c.week_start == week_start), None)
            if cal is None:
                raise ValueError(f"No calendar found for week_start: {week_start}")
            count = 0
            for post in cal.posts:
                post_id = f"{post.topic_id}_{post.format}_{cal.week_start}"
                if ctx.storage.get_analytics(post_id) is not None:
                    continue
                analytics = PostAnalytics(
                    post_id=post_id,
                    topic_id=post.topic_id,
                    topic_title=post.topic_title,
                    format=post.format,
                    asset_path=post.asset_path,
                    source_url=post.source_url,
                    week_start=cal.week_start,
                    last_updated=datetime.now(timezone.utc).isoformat(),
                )
                ctx.storage.save_analytics(analytics)
                count += 1
            return {"initialized_count": str(count)}, count

        elif action_id == "update_analytics":
            from content_creation.models.analytics import PostAnalytics
            from datetime import datetime, timezone
            post_id = payload["post_id"]
            analytics = ctx.storage.get_analytics(post_id)
            if analytics is None:
                raise ValueError(f"No analytics record found for post_id: {post_id}")
            
            # Root properties
            for k in ["posted_at", "notes"]:
                if k in payload:
                    setattr(analytics, k, payload[k])
                    
            # Performance metrics
            metrics = payload.get("metrics", {})
            for k, v in metrics.items():
                if hasattr(analytics.performance, k):
                    setattr(analytics.performance, k, v)
                    
            analytics.last_updated = datetime.now(timezone.utc).isoformat()
            ctx.storage.save_analytics(analytics)
            return {"post_id": post_id, "updated": "true"}, analytics

        elif action_id == "publish":
            return {"published_status": "mock_published"}, None

        elif action_id == "run_pipeline":
            from content_creation.application.pipeline_run_service import PipelineRunService
            service = PipelineRunService()
            result = service.run(
                ctx,
                top_n=payload.get("top_n", 5),
                source_filter=payload.get("source"),
                auto_approve=payload.get("auto_approve", False),
                api_key=payload.get("api_key"),
            )
            return {"log_path": str(result.log_path)}, result

        raise ValueError(f"Unknown action_id: {action_id}")
