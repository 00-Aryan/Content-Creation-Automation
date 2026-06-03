"""Service for orchestrating storyboard review and approval workflows."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from content_creation.application.context import ApplicationContext
from content_creation.domains.storyboard import Storyboard
from content_creation.models.review_history import ReviewHistoryEntry
from content_creation.shared.enums import ReviewStatus


@dataclass(frozen=True)
class StoryboardReviewItem:
    """Represents a reviewable storyboard metadata package."""

    topic_id: str
    status: ReviewStatus
    review_notes: Optional[str]
    visual_style: str
    visual_metaphor: str
    formats_planned: List[str]


@dataclass(frozen=True)
class StoryboardDecision:
    """Input payload for making a review decision on a storyboard."""

    status: ReviewStatus
    notes: Optional[str] = None


@dataclass(frozen=True)
class StoryboardReviewResult:
    """Outcome of applying a storyboard review decision."""

    topic_id: str
    previous_status: ReviewStatus
    new_status: ReviewStatus
    notes: Optional[str]


class StoryboardReviewService:
    """Service to coordinate storyboard reviews, status updates, and history recording."""

    def get_review_item(
        self, ctx: ApplicationContext, topic_id: str
    ) -> Optional[StoryboardReviewItem]:
        """Loads a storyboard and prepares it for review."""
        storyboard = ctx.storage.get_storyboard(topic_id)
        if storyboard is None:
            return None

        return StoryboardReviewItem(
            topic_id=storyboard.topic_id,
            status=storyboard.review_status,
            review_notes=storyboard.review_notes,
            visual_style=storyboard.visual_style,
            visual_metaphor=storyboard.visual_metaphor,
            formats_planned=storyboard.formats_planned,
        )

    def apply_decision(
        self,
        ctx: ApplicationContext,
        topic_id: str,
        decision: StoryboardDecision,
    ) -> StoryboardReviewResult:
        """Updates storyboard review status, notes, and records history."""
        storyboard = ctx.storage.get_storyboard(topic_id)
        if storyboard is None:
            raise FileNotFoundError(f"No storyboard found for topic '{topic_id}'")

        previous_status = storyboard.review_status

        success = ctx.storage.update_asset_status_with_notes(
            "storyboard", topic_id, decision.status, decision.notes
        )
        if not success:
            raise RuntimeError(f"Failed to update storyboard status for topic '{topic_id}'")

        entry = ReviewHistoryEntry(
            topic_id=topic_id,
            asset_type="storyboard",
            action=decision.status.value,
            previous_status=previous_status,
            new_status=decision.status,
            notes=decision.notes,
        )
        ctx.storage.save_review_history_entry(entry)

        return StoryboardReviewResult(
            topic_id=topic_id,
            previous_status=previous_status,
            new_status=decision.status,
            notes=decision.notes,
        )

    def get_history(
        self, ctx: ApplicationContext, topic_id: str
    ) -> List[ReviewHistoryEntry]:
        """Returns the review history for a storyboard."""
        all_history = ctx.storage.get_review_history(topic_id)
        return [entry for entry in all_history if entry.asset_type == "storyboard"]
