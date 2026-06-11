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
        thumb_gen = ThumbnailGenerator(api_key, ctx.prompt_registry)
        script_gen = ScriptGenerator(api_key, ctx.prompt_registry)
        carousel_gen = CarouselGenerator(api_key, ctx.prompt_registry)
        newsletter_gen = NewsletterGenerator(api_key, ctx.prompt_registry)

        counts = {"thumbnail": 0, "script": 0, "carousel": 0, "newsletter": 0}
        skipped = 0
        failures = 0
        asset_generators = {
            "short_video": (script_gen, ctx.storage.save_script, ("short_video",)),
            "carousel": (carousel_gen, ctx.storage.save_carousel, ()),
            "newsletter": (newsletter_gen, ctx.storage.save_newsletter, ()),
        }

        for brief in briefs:
            storyboard = ctx.storage.get_storyboard(brief.topic_id)
            if storyboard is None:
                logger.warning(
                    f"Skipping asset generation for {brief.topic_id} because storyboard artifact is missing."
                )
                skipped += 1
                continue

            # 1. Thumbnail Generation (always required)
            thumbnail_file = ctx.storage.thumbnails_dir / f"{brief.topic_id}.json"
            thumbnail_completed = ctx.workflow.stage_completed(brief.topic_id, "thumbnail")

            if thumbnail_completed and thumbnail_file.exists():
                skipped += 1
            else:
                if thumbnail_completed and not thumbnail_file.exists():
                    logger.warning(
                        f"Divergence detected: stage thumbnail completed but artifact {thumbnail_file} is missing. Regenerating."
                    )
                try:
                    thumb = thumb_gen.generate(storyboard, brief)
                    ctx.storage.save_thumbnail(thumb)
                    ctx.workflow.mark_completed(
                        brief.topic_id,
                        "thumbnail",
                        artifact_path=str(thumbnail_file),
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

                asset_dir = getattr(ctx.storage, f"{asset_type}s_dir")
                asset_file = asset_dir / f"{brief.topic_id}.json"
                asset_completed = ctx.workflow.stage_completed(brief.topic_id, asset_type)

                if asset_completed and asset_file.exists():
                    skipped += 1
                    continue

                if asset_completed and not asset_file.exists():
                    logger.warning(
                        f"Divergence detected: stage {asset_type} completed but artifact {asset_file} is missing. Regenerating."
                    )

                if not asset_completed and asset_file.exists():
                    continue

                try:
                    generator, save_asset, extra_args = asset_generators[fmt]
                    asset = generator.generate(storyboard, brief, *extra_args)
                    save_asset(asset)

                    ctx.workflow.mark_completed(
                        brief.topic_id,
                        asset_type,
                        artifact_path=str(asset_file),
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
