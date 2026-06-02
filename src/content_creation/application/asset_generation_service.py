"""Service for orchestrating multi-format educational asset generation."""

from dataclasses import dataclass
import logging
import os
import time
from typing import Dict, Optional

from content_creation.application.context import ApplicationContext
from content_creation.generation.carousel import CarouselGenerator
from content_creation.generation.newsletter import NewsletterGenerator
from content_creation.generation.script import ScriptGenerator
from content_creation.generation.thumbnail import ThumbnailGenerator
from content_creation.manifest import FORMAT_TO_ASSET, FREETEXT_TO_FORMAT

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssetGenerationResult:
    """Result of the asset generation process."""

    counts: Dict[str, int]
    skipped_count: int
    failed_count: int


class AssetGenerationService:
    """Service to coordinate visual and text asset generation for top-N briefs."""

    def run(
        self,
        ctx: ApplicationContext,
        top_n: int = 5,
        api_key: Optional[str] = None,
        rate_limit_delay: float = 5.0,
    ) -> AssetGenerationResult:
        """Generates thumbnails, scripts, newsletters, and carousels for the top briefs."""
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_key:
            raise ValueError("GEMINI_API_KEY not set in environment or parameter")

        briefs = ctx.storage.list_briefs()
        briefs.sort(key=lambda b: b.generated_at, reverse=True)
        briefs = briefs[:top_n]

        if not briefs:
            return AssetGenerationResult(
                counts={"thumbnail": 0, "script": 0, "carousel": 0, "newsletter": 0},
                skipped_count=0,
                failed_count=0,
            )

        # Instantiate generators using registry
        thumb_gen = ThumbnailGenerator(resolved_key, ctx.prompt_registry)
        script_gen = ScriptGenerator(resolved_key, ctx.prompt_registry)
        carousel_gen = CarouselGenerator(resolved_key, ctx.prompt_registry)
        newsletter_gen = NewsletterGenerator(resolved_key, ctx.prompt_registry)

        counts = {"thumbnail": 0, "script": 0, "carousel": 0, "newsletter": 0}
        skipped = 0
        failures = 0

        for brief in briefs:
            # 1. Thumbnail Generation (always required)
            if ctx.workflow.stage_completed(brief.topic_id, "thumbnail"):
                skipped += 1
            elif not (ctx.storage.thumbnails_dir / f"{brief.topic_id}.json").exists():
                try:
                    storyboard = ctx.storage.get_storyboard(brief.topic_id)
                    thumb = thumb_gen.generate(storyboard, brief)
                    ctx.storage.save_thumbnail(thumb)
                    ctx.workflow.mark_completed(
                        brief.topic_id,
                        "thumbnail",
                        artifact_path=str(
                            ctx.storage.thumbnails_dir / f"{brief.topic_id}.json"
                        ),
                    )
                    counts["thumbnail"] += 1
                    if rate_limit_delay > 0:
                        time.sleep(rate_limit_delay)
                except Exception as e:
                    ctx.workflow.mark_failed(brief.topic_id, "thumbnail")
                    logger.error(
                        f"Thumbnail generation failed for {brief.topic_id}: {e}"
                    )
                    failures += 1

            # 2. Format-specific assets mapping
            mapped_formats = set()
            for fmt in brief.recommended_formats:
                if fmt in FORMAT_TO_ASSET:
                    mapped_formats.add(fmt)
                else:
                    mapped = FREETEXT_TO_FORMAT.get(fmt.lower())
                    if mapped:
                        mapped_formats.add(mapped)
                    else:
                        mapped_formats.add("short_video")

            # Iterate recommended formats
            for fmt in mapped_formats:
                asset_type = FORMAT_TO_ASSET.get(fmt)
                if not asset_type:
                    continue

                if ctx.workflow.stage_completed(brief.topic_id, asset_type):
                    skipped += 1
                    continue

                asset_dir = getattr(ctx.storage, f"{asset_type}s_dir")
                if (asset_dir / f"{brief.topic_id}.json").exists():
                    continue

                try:
                    if fmt == "short_video":
                        asset = script_gen.generate(brief, "short_video")
                        ctx.storage.save_script(asset)
                    elif fmt == "carousel":
                        storyboard = ctx.storage.get_storyboard(brief.topic_id)
                        asset = carousel_gen.generate(storyboard, brief)
                        ctx.storage.save_carousel(asset)
                    elif fmt == "newsletter":
                        storyboard = ctx.storage.get_storyboard(brief.topic_id)
                        asset = newsletter_gen.generate(storyboard, brief)
                        ctx.storage.save_newsletter(asset)

                    ctx.workflow.mark_completed(
                        brief.topic_id,
                        asset_type,
                        artifact_path=str(asset_dir / f"{brief.topic_id}.json"),
                    )
                    counts[asset_type] += 1
                    if rate_limit_delay > 0:
                        time.sleep(rate_limit_delay)
                except Exception as e:
                    ctx.workflow.mark_failed(brief.topic_id, asset_type)
                    logger.error(
                        f"{asset_type} generation failed for {brief.topic_id}: {e}"
                    )
                    failures += 1

        return AssetGenerationResult(
            counts=counts, skipped_count=skipped, failed_count=failures
        )
