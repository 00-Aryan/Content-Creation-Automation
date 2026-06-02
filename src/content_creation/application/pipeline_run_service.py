"""Service for executing the end-to-end content factory pipeline."""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import List, Optional

from content_creation.application.context import ApplicationContext
from content_creation.application.collect_topics_service import CollectTopicsService
from content_creation.application.score_topics_service import ScoreTopicsService
from content_creation.application.brief_generation_service import BriefGenerationService
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
        log_filename = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
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
                service = CollectTopicsService()
                res = service.run(ctx, source_filter=source_filter)
                stage_ctx["items"] = res.count
                summaries["collect"] = {"count": res.count, "success": True}
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
                    service = ScoreTopicsService()
                    res = service.run(ctx)
                    stage_ctx["items"] = res.scored_count
                    summaries["score"] = {
                        "scored_count": res.scored_count,
                        "rejected_count": res.rejected_count,
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
                    service = BriefGenerationService()
                    res = service.run(
                        ctx,
                        top_n=top_n,
                        api_key=api_key,
                        rate_limit_delay=5.0,
                    )
                    stage_ctx["items"] = res.generated_count
                    summaries["generate-briefs"] = {
                        "generated_count": res.generated_count,
                        "skipped_count": res.skipped_count,
                        "failed_count": len(res.failures),
                        "success": True,
                    }
                except Exception as e:
                    stage_ctx["status"] = "error"
                    stage_ctx["error"] = str(e)
                    summaries["generate-briefs"] = {"error": str(e), "success": False}
                    pipeline_success = False

        # Stage 4: Generate Assets
        if pipeline_success:
            with pl.stage("generate-assets") as stage_ctx:
                stages_executed.append("generate-assets")
                try:
                    service = AssetGenerationService()
                    res = service.run(
                        ctx,
                        top_n=top_n,
                        api_key=api_key,
                        rate_limit_delay=5.0,
                    )
                    asset_count = sum(res.counts.values())
                    stage_ctx["items"] = asset_count
                    summaries["generate-assets"] = {
                        "counts": res.counts,
                        "skipped_count": res.skipped_count,
                        "failed_count": res.failed_count,
                        "success": True,
                    }
                except Exception as e:
                    stage_ctx["status"] = "error"
                    stage_ctx["error"] = str(e)
                    summaries["generate-assets"] = {"error": str(e), "success": False}
                    pipeline_success = False

        # Stage 5: Build Manifests
        if pipeline_success:
            with pl.stage("build-manifests") as stage_ctx:
                stages_executed.append("build-manifests")
                try:
                    builder = ManifestBuilder(ctx.storage)
                    manifests = builder.build_all()
                    for m in manifests:
                        ctx.storage.save_manifest(m)
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

        # Stage 6: Batch Approve (Auto-Approve)
        if pipeline_success and auto_approve:
            with pl.stage("batch-approve") as stage_ctx:
                stages_executed.append("batch-approve")
                try:
                    asset_dirs = {
                        "brief": ctx.storage.briefs_dir,
                        "script": ctx.storage.scripts_dir,
                        "carousel": ctx.storage.carousels_dir,
                        "newsletter": ctx.storage.newsletters_dir,
                        "thumbnail": ctx.storage.thumbnails_dir,
                    }

                    approve_count = 0
                    for atype, adir in asset_dirs.items():
                        for fp in adir.glob("*.json"):
                            try:
                                with open(fp, "r") as f:
                                    data = json.load(f)
                                if data.get("review_status") in (
                                    "approved",
                                    "rejected",
                                ):
                                    continue
                                ctx.storage.update_asset_status(
                                    atype, fp.stem, ReviewStatus.APPROVED
                                )
                                approve_count += 1
                            except Exception:
                                pass

                    # Rebuild manifests to reflect approved status
                    builder = ManifestBuilder(ctx.storage)
                    manifests = builder.build_all()
                    for m in manifests:
                        ctx.storage.save_manifest(m)

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
