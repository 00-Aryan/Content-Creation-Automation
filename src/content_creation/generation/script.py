import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TypeGuard, Union

from pydantic import ValidationError

from content_creation.domains.storyboard.model import Storyboard
from content_creation.inference import InferenceManager
from content_creation.models.brief import Brief
from content_creation.models.script import Script, ScriptFormat
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus

logger = logging.getLogger(__name__)


def _clean_markers(text: str) -> str:
    """Remove structural marker tokens (F), (K), and (C) while preserving normal parenthesis and readable spacing."""
    if not isinstance(text, str):
        return text
    cleaned = re.sub(r"\s*\((?:F|K|C)\)", "", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"^[ \t]+|[ \t]+$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"[ \t]*\n[ \t]*", "\n", cleaned)
    return cleaned.strip()


_VALID_FORMATS = frozenset({"short_video", "carousel", "newsletter"})


def _is_valid_format(value: str) -> TypeGuard[ScriptFormat]:
    return value in _VALID_FORMATS


class ScriptGenerator:
    """Generate scripts from a brief using per-format prompt templates."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        prompt_dir: Optional[Union[Path, PromptRegistry]] = None,
    ):
        self._manager = InferenceManager(api_key=api_key)
        self._registry = prompt_dir if isinstance(prompt_dir, PromptRegistry) else None
        self.prompt_dir = prompt_dir if isinstance(prompt_dir, Path) else None

    def generate(
        self,
        storyboard: Optional[Storyboard],
        brief: Brief,
        format: str,
    ) -> Script:
        """Generate a script for ``brief`` using the prompt for ``format``."""
        if not _is_valid_format(format):
            raise ValueError(
                f"Invalid format {format!r}. Must be one of: "
                f"{', '.join(sorted(_VALID_FORMATS))}"
            )

        if self._registry is not None:
            template = self._registry.get("script", format)
        elif self.prompt_dir is not None:
            prompt_path = self.prompt_dir / f"{format}.md"
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            with open(prompt_path, "r") as f:
                template = f.read()
        else:
            raise ValueError(
                "ScriptGenerator requires a PromptRegistry or prompt directory"
            )

        prompt = template.replace("{{ brief.topic_id }}", brief.topic_id)
        prompt = prompt.replace("{{ brief.why_it_matters }}", brief.why_it_matters)

        if storyboard is not None:
            prompt = prompt.replace("{{ brief.analogy }}", storyboard.visual_metaphor)
            if format == "short_video":
                claims = storyboard.script_claims
            elif format == "carousel":
                claims = storyboard.carousel_claims
            else:  # newsletter
                claims = storyboard.newsletter_claims
            summary_bullets = "\n".join([f"- {s}" for s in claims])
        else:
            prompt = prompt.replace("{{ brief.analogy }}", brief.analogy)
            summary_bullets = "\n".join([f"- {s}" for s in brief.plain_english_summary])

        prompt = prompt.replace("{{ brief.plain_english_summary }}", summary_bullets)
        prompt = prompt.replace("{{ brief.student_takeaway }}", brief.student_takeaway)
        prompt = prompt.replace("{{ brief.limitation }}", brief.limitation)
        prompt = prompt.replace("{{ brief.audience_fit }}", brief.audience_fit)
        prompt = prompt.replace("{{ brief.source_url }}", brief.source_url)

        generated_at = datetime.now(timezone.utc).isoformat()

        result = self._manager.generate(prompt=prompt, task_type="script_generation")

        if result.success:
            try:
                data = json.loads(result.text)
                if not isinstance(data, dict):
                    raise ValueError("JSON root is not a dictionary")

                if format == "short_video":
                    if (
                        "shorts_segments" not in data
                        or not isinstance(data["shorts_segments"], list)
                        or not data["shorts_segments"]
                    ):
                        raise ValueError("shorts_segments is missing or empty")

                    from content_creation.models.script import YouTubeShortsSegment

                    parsed_segments = []
                    for i, seg in enumerate(data["shorts_segments"]):
                        if not isinstance(seg, dict):
                            raise ValueError(f"Segment {i} is not a dictionary")

                        required_keys = {
                            "section",
                            "time_range",
                            "visual",
                            "audio",
                            "spoken",
                        }
                        if not required_keys.issubset(seg.keys()):
                            raise ValueError(f"Segment {i} is missing required fields")

                        for key in required_keys:
                            if not isinstance(seg[key], str):
                                raise TypeError(f"Segment field {key} must be a string")

                        section_val = seg["section"].strip()
                        time_range_val = seg["time_range"].strip()
                        visual_clean = _clean_markers(seg["visual"]).strip()
                        audio_clean = _clean_markers(seg["audio"]).strip()
                        spoken_clean = _clean_markers(seg["spoken"]).strip()

                        if not section_val:
                            raise ValueError(
                                f"Segment {i} section field is empty after stripping"
                            )
                        if not time_range_val:
                            raise ValueError(
                                f"Segment {i} time_range field is empty after stripping"
                            )
                        if not visual_clean:
                            raise ValueError(
                                f"Segment {i} visual field is empty after stripping"
                            )
                        if not audio_clean:
                            raise ValueError(
                                f"Segment {i} audio field is empty after stripping"
                            )
                        if not spoken_clean:
                            raise ValueError(
                                f"Segment {i} spoken field is empty after stripping"
                            )

                        if section_val not in {
                            "hook",
                            "context",
                            "explanation",
                            "payoff",
                            "cta",
                        }:
                            raise ValueError(
                                f"Segment {i} has invalid section: {section_val}"
                            )

                        segment_obj = YouTubeShortsSegment(
                            section=section_val,
                            time_range=time_range_val,
                            visual=visual_clean,
                            audio=audio_clean,
                            spoken=spoken_clean,
                        )
                        parsed_segments.append(segment_obj)

                    if parsed_segments[0].section != "hook":
                        raise ValueError("First segment section is not hook")
                    if parsed_segments[-1].section != "cta":
                        raise ValueError("Last segment section is not cta")

                    if storyboard is not None:
                        hook_val = storyboard.script_hook
                        cta_val = storyboard.script_cta
                        claims_val = storyboard.script_claims
                    else:
                        hook_val = parsed_segments[0].spoken
                        cta_val = parsed_segments[-1].spoken
                        claims_val = data.get("claims_used", [])

                    # Synchronize the first segment narration with the final hook
                    parsed_segments[0].spoken = hook_val
                    # Synchronize the last segment narration with the final CTA
                    parsed_segments[-1].spoken = cta_val

                    # Derive script_sections from middle segment narration
                    script_sections = [seg.spoken for seg in parsed_segments[1:-1]]

                    review_status = ReviewStatus.DRAFT
                    if "review_status" in data:
                        try:
                            review_status = ReviewStatus(data["review_status"])
                        except ValueError:
                            review_status = ReviewStatus.NEEDS_REVIEW

                    source_links = [brief.source_url]
                    script = Script(
                        topic_id=brief.topic_id,
                        format=format,
                        hook=hook_val,
                        script_sections=script_sections,
                        cta=cta_val,
                        claims_used=claims_val,
                        source_links=source_links,
                        review_status=review_status,
                        generated_at=generated_at,
                        shorts_segments=parsed_segments,
                    )
                    return script

                else:
                    if "review_status" in data:
                        data["review_status"] = ReviewStatus(data["review_status"])
                    if "hook" in data and isinstance(data["hook"], str):
                        data["hook"] = _clean_markers(data["hook"])
                    if "cta" in data and isinstance(data["cta"], str):
                        data["cta"] = _clean_markers(data["cta"])
                    if "script_sections" in data and isinstance(
                        data["script_sections"], list
                    ):
                        data["script_sections"] = [
                            (
                                _clean_markers(section)
                                if isinstance(section, str)
                                else section
                            )
                            for section in data["script_sections"]
                        ]
                    # Explicitly remove or ignore shorts_segments and source_links from provider data for non-shorts
                    data.pop("source_links", None)
                    data.pop("shorts_segments", None)
                    source_links = [brief.source_url]
                    script = Script(
                        topic_id=brief.topic_id,
                        format=format,
                        source_links=source_links,
                        generated_at=generated_at,
                        shorts_segments=[],
                        **data,
                    )

                    if storyboard is not None:
                        if format == "carousel":
                            hook_val = storyboard.carousel_hook
                            cta_val = storyboard.carousel_cta
                            claims_val = storyboard.carousel_claims
                        else:  # newsletter
                            hook_val = storyboard.newsletter_hook
                            cta_val = storyboard.newsletter_cta
                            claims_val = storyboard.newsletter_claims

                        script = script.model_copy(
                            update={
                                "hook": hook_val,
                                "cta": cta_val,
                                "claims_used": claims_val,
                            }
                        )

                    return script
            except (json.JSONDecodeError, ValueError, TypeError, ValidationError) as e:
                logger.warning(
                    "Failed to parse script for topic %s: %s",
                    brief.topic_id,
                    e,
                )
        else:
            logger.warning(
                "Inference failed for topic %s: %s",
                brief.topic_id,
                result.error,
            )

        if storyboard is not None:
            if format == "short_video":
                hook_val = storyboard.script_hook
                cta_val = storyboard.script_cta
                claims_val = storyboard.script_claims
            elif format == "carousel":
                hook_val = storyboard.carousel_hook
                cta_val = storyboard.carousel_cta
                claims_val = storyboard.carousel_claims
            else:  # newsletter
                hook_val = storyboard.newsletter_hook
                cta_val = storyboard.newsletter_cta
                claims_val = storyboard.newsletter_claims

            return Script(
                topic_id=brief.topic_id,
                format=format,
                hook=hook_val,
                script_sections=[
                    "needs_review",
                    "needs_review",
                    "needs_review",
                    "needs_review",
                ],
                cta=cta_val,
                claims_used=claims_val,
                source_links=[brief.source_url],
                review_status=ReviewStatus.NEEDS_REVIEW,
                generated_at=generated_at,
            )

        return Script(
            topic_id=brief.topic_id,
            format=format,
            hook="needs_review",
            script_sections=[
                "needs_review",
                "needs_review",
                "needs_review",
                "needs_review",
            ],
            cta="needs_review",
            claims_used=["needs_review"],
            source_links=[brief.source_url],
            review_status=ReviewStatus.NEEDS_REVIEW,
            generated_at=generated_at,
        )
