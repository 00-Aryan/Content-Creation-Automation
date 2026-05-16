import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from google import genai
from google.genai import errors
from content_creation.models.brief import Brief, ReviewStatus
from content_creation.models.topic import ScoredTopicItem

logger = logging.getLogger(__name__)

def generate_brief(item: ScoredTopicItem, prompt_path: Path, api_key: str) -> Brief:
    """Generate a brief for a scored topic using Gemini API with retry logic and truncation."""
    
    if not item.raw_text or len(item.raw_text) < 100:
        raise ValueError(f"Raw text is too short ({len(item.raw_text) if item.raw_text else 0} chars). Minimum 100 required.")

    # Truncate input to respect token limits (approx 15k chars is well within safe bounds)
    truncated_text = item.raw_text[:15000]

    # Read prompt template
    with open(prompt_path, "r") as f:
        template = f.read()

    # Replace placeholders
    prompt = template.replace("{{ topic.title }}", item.title)
    prompt = prompt.replace("{{ topic.source }}", item.source)
    prompt = prompt.replace("{{ topic.url }}", item.url)
    prompt = prompt.replace("{{ topic.raw_text }}", truncated_text)

    # Configure and call Gemini API
    client = genai.Client(api_key=api_key)
    
    generated_at = datetime.now(timezone.utc).isoformat()
    
    max_retries = 3
    base_delay = 15  # seconds
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            raw = response.text
            
            # Strip markdown fences
            raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
            
            data = json.loads(raw)
            
            # Ensure review_status is correctly mapped to Enum
            if "review_status" in data:
                data["review_status"] = ReviewStatus(data["review_status"])
                
            return Brief(
                topic_id=item.id,
                source_url=item.url,
                generated_at=generated_at,
                **data
            )
            
        except errors.ClientError as e:
            if e.code == 429:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited (429) for topic {item.id}. Retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
                continue
            else:
                logger.warning(f"ClientError generating brief for topic {item.id}: {e}")
                break
        except Exception as e:
            logger.warning(f"Failed to generate or parse brief for topic {item.id}: {e}")
            break
            
    # Fallback for exhausted retries or non-recoverable errors
    return Brief(
        topic_id=item.id,
        why_it_matters="needs_review",
        plain_english_summary=["needs_review", "needs_review", "needs_review"],
        student_takeaway="needs_review",
        analogy="needs_review",
        limitation="needs_review",
        audience_fit="needs_review",
        recommended_formats=["needs_review"],
        source_url=item.url,
        review_status=ReviewStatus.NEEDS_REVIEW,
        generated_at=generated_at
    )
