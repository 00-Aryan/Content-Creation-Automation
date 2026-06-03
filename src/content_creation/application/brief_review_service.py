"""Service for orchestrating brief review and approval workflows."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from content_creation.application.context import ApplicationContext
from content_creation.models.brief import Brief
from content_creation.models.review_history import ReviewHistoryEntry
from content_creation.shared.enums import ReviewStatus


@dataclass(frozen=True)
class BriefReviewItem:
    """Represents a reviewable brief metadata package."""

    topic_id: str
    status: ReviewStatus
    review_notes: Optional[str]
    why_it_matters: str
    student_takeaway: str
    summary: List[str]


@dataclass(frozen=True)
class BriefDecision:
    """Input payload for making a review decision on a brief."""

    status: ReviewStatus
    notes: Optional[str] = None


@dataclass(frozen=True)
class BriefReviewResult:
    """Outcome of applying a brief review decision."""

    topic_id: str
    previous_status: ReviewStatus
    new_status: ReviewStatus
    notes: Optional[str]


class BriefReviewService:
    """Service to coordinate brief reviews, status updates, and history recording."""

    def get_review_item(
        self, ctx: ApplicationContext, topic_id: str
    ) -> Optional[BriefReviewItem]:
        """Loads a brief and prepares it for review."""
        brief = ctx.storage.get_brief(topic_id)
        if brief is None:
            return None

        return BriefReviewItem(
            topic_id=brief.topic_id,
            status=brief.review_status,
            review_notes=brief.review_notes,
            why_it_matters=brief.why_it_matters,
            student_takeaway=brief.student_takeaway,
            summary=brief.plain_english_summary,
        )

    def apply_decision(
        self,
        ctx: ApplicationContext,
        topic_id: str,
        decision: BriefDecision,
    ) -> BriefReviewResult:
        """Updates brief review status, notes, and records history."""
        brief = ctx.storage.get_brief(topic_id)
        if brief is None:
            raise FileNotFoundError(f"No brief found for topic '{topic_id}'")

        previous_status = brief.review_status

        success = ctx.storage.update_asset_status_with_notes(
            "brief", topic_id, decision.status, decision.notes
        )
        if not success:
            raise RuntimeError(f"Failed to update brief status for topic '{topic_id}'")

        entry = ReviewHistoryEntry(
            topic_id=topic_id,
            asset_type="brief",
            action=decision.status.value,
            previous_status=previous_status,
            new_status=decision.status,
            notes=decision.notes,
        )
        ctx.storage.save_review_history_entry(entry)

        return BriefReviewResult(
            topic_id=topic_id,
            previous_status=previous_status,
            new_status=decision.status,
            notes=decision.notes,
        )

    def get_history(
        self, ctx: ApplicationContext, topic_id: str
    ) -> List[ReviewHistoryEntry]:
        """Returns the review history for a brief."""
        all_history = ctx.storage.get_review_history(topic_id)
        return [entry for entry in all_history if entry.asset_type == "brief"]

    def get_all_history(
        self, ctx: ApplicationContext, topic_id: str
    ) -> List[ReviewHistoryEntry]:
        """Returns all review history entries for a topic across all asset types."""
        return ctx.storage.get_review_history(topic_id)
