"""Service for executing the end-to-end content factory pipeline."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import List, Optional

from content_creation.application.context import ApplicationContext
from content_creation.application.collect_topics_service import CollectTopicsService
from content_creation.application.score_topics_service import ScoreTopicsService
from content_creation.application.brief_generation_service import BriefGenerationService
from content_creation.application.content_intelligence_service import (
    ContentIntelligenceService,
)
from content_creation.application.storyboard_service import StoryboardService
from content_creation.application.asset_generation_service import AssetGenerationService
from content_creation.manifest import ManifestBuilder
from content_creation.shared.enums import ReviewStatus
from content_creation.utils.logging import PipelineLogger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineRunResult:
    """Result summary of a pipeline execution."""

    log_path: Path
    success: bool
    stages: List[str]
    stage_summaries: dict


class PipelineRunService:
    """Service to orchestrate and execute the full content factory pipeline end-to-end."""

    def run(
        self,
        ctx: ApplicationContext,
        top_n: int = 5,
        source_filter: Optional[str] = None,
        auto_approve: bool = False,
        api_key: Optional[str] = None,
    ) -> PipelineRunResult:
        """Executes all stages of the pipeline and records progress to a PipelineLogger."""
        log_filename = f"pipeline_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        log_path = ctx.storage.logs_dir / log_filename

        # Ensure directories exist
        ctx.storage.logs_dir.mkdir(parents=True, exist_ok=True)

        pl = PipelineLogger(log_path)
        stages_executed = []
        summaries = {}
        pipeline_success = True

        # Stage 1: Collect
        with pl.stage("collect") as stage_ctx:
            stages_executed.append("collect")
            try:
                from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
                executor = WorkflowActionExecutor()
                res = executor.execute(
                    ctx,
                    "collect",
                    "topic",
                    "all",
                    {"source": source_filter}
                )
                if not res.success:
                    raise RuntimeError(f"Collect failed: {res.blocking_reasons}")
                collect_res = res.raw_result
                stage_ctx["items"] = collect_res.count
                summaries["collect"] = {"count": collect_res.count, "success": True}
            except Exception as e:
                stage_ctx["status"] = "error"
                stage_ctx["error"] = str(e)
                summaries["collect"] = {"error": str(e), "success": False}
                pipeline_success = False

        # Stage 2: Score
        if pipeline_success:
            with pl.stage("score") as stage_ctx:
                stages_executed.append("score")
                try:
                    from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
                    executor = WorkflowActionExecutor()
                    res = executor.execute(
                        ctx,
                        "score_topics",
                        "topic",
                        "all",
                        {"limit": None}
                    )
                    if not res.success:
                        raise RuntimeError(f"Score failed: {res.blocking_reasons}")
                    score_res = res.raw_result
                    stage_ctx["items"] = score_res.scored_count
                    summaries["score"] = {
                        "scored_count": score_res.scored_count,
                        "rejected_count": score_res.rejected_count,
                        "success": True,
                    }
                except Exception as e:
                    stage_ctx["status"] = "error"
                    stage_ctx["error"] = str(e)
                    summaries["score"] = {"error": str(e), "success": False}
                    pipeline_success = False

        # Stage 3: Generate Briefs
        if pipeline_success:
            with pl.stage("generate-briefs") as stage_ctx:
                stages_executed.append("generate-briefs")
                try:
                    from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
                    executor = WorkflowActionExecutor()
                    res = executor.execute(
                        ctx,
                        "generate_briefs",
                        "brief",
                        "all",
                        {
                            "top_n": top_n,
                            "api_key": api_key,
                        }
                    )
                    if not res.success:
                        raise RuntimeError(f"Brief generation failed: {res.blocking_reasons}")
                    brief_res = res.raw_result
                    stage_ctx["items"] = brief_res.generated_count
                    summaries["generate-briefs"] = {
                        "generated_count": brief_res.generated_count,
                        "skipped_count": brief_res.skipped_count,
                        "failed_count": len(brief_res.failures),
                        "success": True,
                    }
                except Exception as e:
                    stage_ctx["status"] = "error"
                    stage_ctx["error"] = str(e)
                    summaries["generate-briefs"] = {"error": str(e), "success": False}
                    pipeline_success = False

        # Stage 4: Generate Content Intelligence
        if pipeline_success:
            with pl.stage("generate-content-intelligence") as stage_ctx:
                stages_executed.append("generate-content-intelligence")
                try:
                    from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
                    executor = WorkflowActionExecutor()
                    res = executor.execute(
                        ctx,
                        "generate_ci",
                        "content_intelligence",
                        "all",
                        {
                            "top_n": top_n,
                            "api_key": api_key,
                        }
                    )
                    if not res.success:
                        raise RuntimeError(f"Content Intelligence generation failed: {res.blocking_reasons}")
                    ci_res = res.raw_result
                    stage_ctx["items"] = ci_res.generated_count
                    summaries["generate-content-intelligence"] = {
                        "generated_count": ci_res.generated_count,
                        "skipped_count": ci_res.skipped_count,
                        "failed_count": len(ci_res.failures),
                        "success": True,
                    }
                except Exception as e:
                    stage_ctx["status"] = "error"
                    stage_ctx["error"] = str(e)
                    summaries["generate-content-intelligence"] = {
                        "error": str(e),
                        "success": False,
                    }
                    pipeline_success = False

        # Stage 5: Generate Storyboards
        if pipeline_success:
            with pl.stage("generate-storyboards") as stage_ctx:
                stages_executed.append("generate-storyboards")
                try:
                    from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
                    executor = WorkflowActionExecutor()
                    res = executor.execute(
                        ctx,
                        "generate_storyboards",
                        "storyboard",
                        "all",
                        {
                            "top_n": top_n,
                            "api_key": api_key,
                        }
                    )
                    if not res.success:
                        raise RuntimeError(f"Storyboard generation failed: {res.blocking_reasons}")
                    sb_res = res.raw_result
                    stage_ctx["items"] = sb_res.generated_count
                    summaries["generate-storyboards"] = {
                        "generated_count": sb_res.generated_count,
                        "skipped_count": sb_res.skipped_count,
                        "failed_count": len(sb_res.failures),
                        "success": True,
                    }
                except Exception as e:
                    stage_ctx["status"] = "error"
                    stage_ctx["error"] = str(e)
                    summaries["generate-storyboards"] = {
                        "error": str(e),
                        "success": False,
                    }
                    pipeline_success = False

        # Stage 6: Generate Assets
        if pipeline_success:
            with pl.stage("generate-assets") as stage_ctx:
                stages_executed.append("generate-assets")
                try:
                    from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
                    executor = WorkflowActionExecutor()
                    res = executor.execute(
                        ctx,
                        "generate_assets",
                        "assets",
                        "all",
                        {
                            "top_n": top_n,
                            "api_key": api_key,
                        }
                    )
                    if not res.success:
                        raise RuntimeError(f"Asset generation failed: {res.blocking_reasons}")
                    asset_res = res.raw_result
                    asset_count = sum(asset_res.counts.values())
                    stage_ctx["items"] = asset_count
                    summaries["generate-assets"] = {
                        "counts": asset_res.counts,
                        "skipped_count": asset_res.skipped_count,
                        "failed_count": asset_res.failed_count,
                        "success": True,
                    }
                except Exception as e:
                    stage_ctx["status"] = "error"
                    stage_ctx["error"] = str(e)
                    summaries["generate-assets"] = {"error": str(e), "success": False}
                    pipeline_success = False

        # Stage 7: Build Manifests
        if pipeline_success:
            with pl.stage("build-manifests") as stage_ctx:
                stages_executed.append("build-manifests")
                try:
                    from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
                    executor = WorkflowActionExecutor()
                    res = executor.execute(
                        ctx,
                        "build_all_manifests",
                        "manifest",
                        "all",
                        {}
                    )
                    if not res.success:
                        raise RuntimeError(f"Manifest build failed: {res.blocking_reasons}")
                    manifests = res.raw_result
                    stage_ctx["items"] = len(manifests)
                    summaries["build-manifests"] = {
                        "count": len(manifests),
                        "success": True,
                    }
                except Exception as e:
                    stage_ctx["status"] = "error"
                    stage_ctx["error"] = str(e)
                    summaries["build-manifests"] = {"error": str(e), "success": False}
                    pipeline_success = False

        # Stage 8: Batch Approve (Auto-Approve)
        if pipeline_success and auto_approve:
            with pl.stage("batch-approve") as stage_ctx:
                stages_executed.append("batch-approve")
                try:
                    from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor
                    executor = WorkflowActionExecutor()
                    res = executor.execute(
                        ctx,
                        "batch_approve",
                        "assets",
                        "all",
                        {
                            "asset_type": "all",
                            "exclude_incomplete": False,
                        }
                    )
                    if not res.success:
                        raise RuntimeError(f"Auto-approve batch approval failed: {res.blocking_reasons}")
                    approve_count = res.raw_result
                    stage_ctx["items"] = approve_count
                    summaries["batch-approve"] = {
                        "approved_count": approve_count,
                        "success": True,
                    }
                except Exception as e:
                    stage_ctx["status"] = "error"
                    stage_ctx["error"] = str(e)
                    summaries["batch-approve"] = {"error": str(e), "success": False}
                    pipeline_success = False

        return PipelineRunResult(
            log_path=log_path,
            success=pipeline_success,
            stages=stages_executed,
            stage_summaries=summaries,
        )
