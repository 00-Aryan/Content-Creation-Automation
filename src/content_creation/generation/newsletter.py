import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from google.genai import errors

from content_creation.models.brief import Brief
from content_creation.models.newsletter import Newsletter, NewsletterSection
from content_creation.models.brief import ReviewStatus

logger = logging.getLogger(__name__)


class NewsletterGenerator:
    """Generate newsletter content from a brief using Gemini."""

    def __init__(self, api_key: str, prompt_dir: Path):
        self._client = genai.Client(api_key=api_key)
        self.prompt_dir = prompt_dir
        self.prompt_path = prompt_dir / "newsletter.md"
        if not self.prompt_path.exists():
            logger.warning(
                "Prompt template not found: %s",
                self.prompt_path,
            )

    def generate(self, brief: Brief) -> Newsletter:
        """Generate a newsletter for ``brief``."""
        if not self.prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {self.prompt_path}")

        combined_fields = " ".join(
            [
                brief.why_it_matters,
                brief.student_takeaway,
                brief.analogy,
                brief.limitation,
                brief.audience_fit,
            ]
        )
        truncated_combined = combined_fields[:8000]

        with open(self.prompt_path, "r") as f:
            template = f.read()

        prompt = template.replace("{{ brief.topic_id }}", brief.topic_id)
        prompt = prompt.replace("{{ brief.why_it_matters }}", brief.why_it_matters)
        
        # Preserve list structure with bullets
        summary_bullets = "\n".join([f"- {s}" for s in brief.plain_english_summary])
        prompt = prompt.replace("{{ brief.plain_english_summary }}", summary_bullets)
        
        prompt = prompt.replace("{{ brief.student_takeaway }}", brief.student_takeaway)
        prompt = prompt.replace("{{ brief.analogy }}", brief.analogy)
        prompt = prompt.replace("{{ brief.limitation }}", brief.limitation)
        prompt = prompt.replace("{{ brief.audience_fit }}", brief.audience_fit)
        prompt = prompt.replace("{{ brief.source_url }}", brief.source_url)
        
        formats_list = "\n".join([f"- {fmt}" for fmt in brief.recommended_formats])
        prompt = prompt.replace("{{ brief.recommended_formats }}", formats_list)

        generated_at = datetime.now(timezone.utc).isoformat()

        max_retries = 3
        base_delay = 15

        for attempt in range(max_retries):
            try:
                response = self._client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                raw = response.text

                raw = raw.strip().removeprefix("```json").removesuffix("```").strip()

                data = json.loads(raw)

                if "review_status" in data:
                    data["review_status"] = ReviewStatus(data["review_status"])

                data.pop("source_links", None)

                sections_data = data.pop("sections", [])
                sections = [NewsletterSection(**section) for section in sections_data]

                source_links = [brief.source_url]

                return Newsletter(
                    topic_id=brief.topic_id,
                    sections=sections,
                    source_links=source_links,
                    generated_at=generated_at,
                    **data,
                )

            except errors.ClientError as e:
                if e.code == 429:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        "Rate limited (429) for topic %s. Retrying in %s seconds "
                        "(attempt %s/%s)...",
                        brief.topic_id,
                        delay,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(delay)
                    continue
                logger.warning(
                    "ClientError generating newsletter for topic %s: %s",
                    brief.topic_id,
                    e,
                )
                break
            except Exception as e:
                logger.warning(
                    "Failed to generate or parse newsletter for topic %s: %s",
                    brief.topic_id,
                    e,
                )
                break

        return Newsletter(
            topic_id=brief.topic_id,
            subject_line="needs_review",
            sections=[
                NewsletterSection(section_name="what_happened", content="needs_review"),
                NewsletterSection(section_name="why_it_matters", content="needs_review"),
                NewsletterSection(
                    section_name="student_takeaway", content="needs_review"
                ),
            ],
            cta="needs_review",
            claims_used=["needs_review"],
            source_links=[brief.source_url],
            review_status=ReviewStatus.NEEDS_REVIEW,
            generated_at=generated_at,
        )