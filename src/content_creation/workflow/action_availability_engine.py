"""Action Availability Engine: maps artifact states and dependencies to available actions.

This engine is a pure domain-level, deterministic, and side-effect free service.
It determines which operator or system actions are available, which are blocked,
and explains the reasons why, conforming to the canonical Action Registry definitions.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from content_creation.shared.enums import ReviewStatus
from content_creation.workflow.review_transition_engine import ReviewTransitionEngine
from content_creation.workflow.states import ArtifactLifecycleState


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AvailableAction:
    """Represents an action that can be executed in the current state."""
    action_id: str
    category: str
    description: str


@dataclass(frozen=True)
class BlockedAction:
    """Represents an action that is currently blocked with a reason code and message."""
    action_id: str
    category: str
    blocking_code: str
    blocking_message: str


@dataclass(frozen=True)
class ActionAvailabilityResult:
    """The complete result containing both available and blocked actions."""
    available_actions: List[AvailableAction]
    blocked_actions: List[BlockedAction]


# ---------------------------------------------------------------------------
# Action Definitions and Metadata
# ---------------------------------------------------------------------------

ACTION_METADATA = {
    "generate_briefs": {
        "category": "GENERATION",
        "description": "Generate educational brief via Gemini API",
    },
    "approve_brief": {
        "category": "APPROVAL",
        "description": "Approve the generated brief",
    },
    "reject_brief": {
        "category": "APPROVAL",
        "description": "Reject the generated brief",
    },
    "generate_ci": {
        "category": "GENERATION",
        "description": "Generate content intelligence report",
    },
    "generate_storyboards": {
        "category": "GENERATION",
        "description": "Generate detailed storyboard layout",
    },
    "approve_storyboard": {
        "category": "APPROVAL",
        "description": "Approve the storyboard layout",
    },
    "reject_storyboard": {
        "category": "APPROVAL",
        "description": "Reject the storyboard layout",
    },
    "generate_assets": {
        "category": "GENERATION",
        "description": "Generate scripts, carousels, newsletters, and thumbnails",
    },
    "approve_asset": {
        "category": "APPROVAL",
        "description": "Approve a specific asset",
    },
    "reject_asset": {
        "category": "APPROVAL",
        "description": "Reject a specific asset",
    },
    "build_manifest": {
        "category": "ORCHESTRATION",
        "description": "Compile manifest files for a single topic",
    },
    "plan_week": {
        "category": "PLANNING",
        "description": "Schedule approved assets into 7-day calendar",
    },
    "dry_run": {
        "category": "VALIDATION",
        "description": "Validate scheduled assets for publishing readiness",
    },
    "publish": {
        "category": "PUBLISHING",
        "description": "Deliver finalized post to destination channel",
    },
}

BLOCKING_MESSAGES = {
    "BLOCKED_TOPIC_REJECTED": "Topic scored below threshold or was rejected.",
    "BLOCKED_MISSING_SCORED_TOPIC": "The source topic has no scoring record.",
    "BLOCKED_BRIEF_NOT_APPROVED": "Upstream brief is not approved.",
    "BLOCKED_MISSING_BRIEF": "Brief is missing.",
    "BLOCKED_MISSING_STORYBOARD": "Storyboard file does not exist.",
    "BLOCKED_STORYBOARD_NOT_APPROVED": "Storyboard exists but is not approved.",
    "BLOCKED_ASSET_ALREADY_EXISTS": "Target asset file is already populated.",
    "BLOCKED_DEPENDENCY_REJECTED": "Upstream dependency is in a rejected state.",
    "BLOCKED_MISSING_CONTENT_INTELLIGENCE": "Content Intelligence is missing.",
    "BLOCKED_NO_READY_MANIFESTS": "No topics have fully approved asset packages.",
    "BLOCKED_MISSING_CALENDAR": "Weekly calendar has not been generated.",
    "BLOCKED_DRY_RUN_FAILED": "Scheduled post failed publishing validation checks.",
    "BLOCKED_ALREADY_TERMINAL": "The artifact is already in a terminal state.",
    "BLOCKED_UNAPPROVED_ASSET": "The asset scheduled for this post is not approved.",
}

LIFECYCLE_TO_REVIEW = {
    ArtifactLifecycleState.DRAFT: ReviewStatus.DRAFT,
    ArtifactLifecycleState.NEEDS_REVIEW: ReviewStatus.NEEDS_REVIEW,
    ArtifactLifecycleState.REVIEWED: ReviewStatus.REVIEWED,
    ArtifactLifecycleState.APPROVED: ReviewStatus.APPROVED,
    ArtifactLifecycleState.REJECTED: ReviewStatus.REJECTED,
}


# ---------------------------------------------------------------------------
# Action Availability Engine
# ---------------------------------------------------------------------------

class ActionAvailabilityEngine:
    """Deterministic, side-effect free engine to evaluate action availability."""

    def __init__(self, transition_engine: Optional[ReviewTransitionEngine] = None) -> None:
        """Initialise the engine with a transition engine."""
        self._transition_engine = transition_engine or ReviewTransitionEngine()

    def get_actions_result(
        self,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> ActionAvailabilityResult:
        """Compute all available and blocked actions for a given artifact state.

        Parameters
        ----------
        artifact_type : str
            The type of artifact (e.g., "brief", "storyboard", "assets", "manifest", "weekly_calendar").
        current_state : ArtifactLifecycleState
            The current lifecycle state of this artifact.
        dependencies : dict[str, ArtifactLifecycleState], optional
            States of upstream dependencies.

        Returns
        -------
        ActionAvailabilityResult
        """
        deps = dependencies or {}
        available: List[AvailableAction] = []
        blocked: List[BlockedAction] = []

        # Find actions related to this artifact type
        relevant_actions = self._get_relevant_actions_for_type(artifact_type)

        for action_id in relevant_actions:
            blocking_code = self._check_blocking_reason(
                action_id, artifact_type, current_state, deps
            )
            meta = ACTION_METADATA[action_id]
            if blocking_code is None:
                available.append(
                    AvailableAction(
                        action_id=action_id,
                        category=meta["category"],
                        description=meta["description"],
                    )
                )
            else:
                msg = BLOCKING_MESSAGES.get(blocking_code, "Action is blocked.")
                blocked.append(
                    BlockedAction(
                        action_id=action_id,
                        category=meta["category"],
                        blocking_code=blocking_code,
                        blocking_message=msg,
                    )
                )

        return ActionAvailabilityResult(available_actions=available, blocked_actions=blocked)

    def get_available_actions(
        self,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> List[AvailableAction]:
        """Return lists of available actions."""
        res = self.get_actions_result(artifact_type, current_state, dependencies)
        return res.available_actions

    def get_blocked_actions(
        self,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> List[BlockedAction]:
        """Return lists of blocked actions."""
        res = self.get_actions_result(artifact_type, current_state, dependencies)
        return res.blocked_actions

    def can_execute_action(
        self,
        action_id: str,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> bool:
        """Check if a specific action can be executed."""
        deps = dependencies or {}
        blocking_code = self._check_blocking_reason(action_id, artifact_type, current_state, deps)
        return blocking_code is None

    def explain_blocking_reason(
        self,
        action_id: str,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> Optional[str]:
        """Return the user-friendly blocking message if blocked, else None."""
        deps = dependencies or {}
        blocking_code = self._check_blocking_reason(action_id, artifact_type, current_state, deps)
        if blocking_code:
            return BLOCKING_MESSAGES.get(blocking_code, "Action is blocked.")
        return None

    def get_next_recommended_action(
        self,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> Optional[str]:
        """Determine the single next recommended action for the operator.

        Parameters
        ----------
        artifact_type : str
        current_state : ArtifactLifecycleState
        dependencies : dict[str, ArtifactLifecycleState], optional

        Returns
        -------
        str, optional
            The action_id of the recommended next action, or None.
        """
        deps = dependencies or {}
        
        if artifact_type == "brief":
            if current_state in {ArtifactLifecycleState.MISSING, ArtifactLifecycleState.FAILED, ArtifactLifecycleState.REJECTED}:
                if self.can_execute_action("generate_briefs", "brief", current_state, deps):
                    return "generate_briefs"
            elif current_state in {ArtifactLifecycleState.DRAFT, ArtifactLifecycleState.NEEDS_REVIEW, ArtifactLifecycleState.REVIEWED}:
                return "approve_brief"
            elif current_state == ArtifactLifecycleState.APPROVED:
                return "generate_ci"

        elif artifact_type == "content_intelligence":
            if current_state in {ArtifactLifecycleState.MISSING, ArtifactLifecycleState.FAILED}:
                if self.can_execute_action("generate_ci", "content_intelligence", current_state, deps):
                    return "generate_ci"
            elif current_state == ArtifactLifecycleState.APPROVED:
                return "generate_storyboards"

        elif artifact_type == "storyboard":
            if current_state in {ArtifactLifecycleState.MISSING, ArtifactLifecycleState.FAILED, ArtifactLifecycleState.REJECTED}:
                if self.can_execute_action("generate_storyboards", "storyboard", current_state, deps):
                    return "generate_storyboards"
            elif current_state in {ArtifactLifecycleState.DRAFT, ArtifactLifecycleState.NEEDS_REVIEW, ArtifactLifecycleState.REVIEWED}:
                return "approve_storyboard"
            elif current_state == ArtifactLifecycleState.APPROVED:
                return "generate_assets"

        elif artifact_type == "assets":
            if current_state in {ArtifactLifecycleState.MISSING, ArtifactLifecycleState.FAILED, ArtifactLifecycleState.REJECTED}:
                if self.can_execute_action("generate_assets", "assets", current_state, deps):
                    return "generate_assets"
            elif current_state in {ArtifactLifecycleState.DRAFT, ArtifactLifecycleState.NEEDS_REVIEW, ArtifactLifecycleState.REVIEWED}:
                return "approve_asset"
            elif current_state == ArtifactLifecycleState.APPROVED:
                return "build_manifest"

        elif artifact_type == "manifest":
            if current_state != ArtifactLifecycleState.APPROVED:
                if self.can_execute_action("build_manifest", "manifest", current_state, deps):
                    return "build_manifest"
            else:
                return "plan_week"

        elif artifact_type == "weekly_calendar":
            if current_state == ArtifactLifecycleState.MISSING:
                if self.can_execute_action("plan_week", "weekly_calendar", current_state, deps):
                    return "plan_week"
            elif current_state == ArtifactLifecycleState.DRAFT:
                if self.can_execute_action("dry_run", "weekly_calendar", current_state, deps):
                    return "dry_run"
            elif current_state == ArtifactLifecycleState.APPROVED:
                if self.can_execute_action("publish", "weekly_calendar", current_state, deps):
                    return "publish"

        return None

    # ------------------------------------------------------------------
    # Internal Evaluation Logic
    # ------------------------------------------------------------------

    def _get_relevant_actions_for_type(self, artifact_type: str) -> List[str]:
        """Return the actions configured for a specific artifact type."""
        if artifact_type == "brief":
            return ["generate_briefs", "approve_brief", "reject_brief"]
        if artifact_type == "content_intelligence":
            return ["generate_ci"]
        if artifact_type == "storyboard":
            return ["generate_storyboards", "approve_storyboard", "reject_storyboard"]
        if artifact_type == "assets":
            return ["generate_assets", "approve_asset", "reject_asset"]
        if artifact_type == "manifest":
            return ["build_manifest", "plan_week"]
        if artifact_type == "weekly_calendar":
            return ["plan_week", "dry_run", "publish"]
        return []

    def _check_blocking_reason(
        self,
        action_id: str,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Dict[str, ArtifactLifecycleState],
    ) -> Optional[str]:
        """Evaluate rules and return blocking reason code, or None if allowed."""
        # 1. Evaluate allowed and forbidden states
        if action_id == "generate_briefs":
            if current_state not in {
                ArtifactLifecycleState.MISSING,
                ArtifactLifecycleState.FAILED,
                ArtifactLifecycleState.REJECTED,
            }:
                return "BLOCKED_ASSET_ALREADY_EXISTS"
            
            # Check topic dependency
            topic_state = dependencies.get("topic")
            if topic_state == ArtifactLifecycleState.REJECTED:
                return "BLOCKED_TOPIC_REJECTED"
            if topic_state == ArtifactLifecycleState.MISSING:
                return "BLOCKED_MISSING_SCORED_TOPIC"

        elif action_id in {"approve_brief", "reject_brief"}:
            if current_state in {ArtifactLifecycleState.APPROVED, ArtifactLifecycleState.REJECTED}:
                return "BLOCKED_ALREADY_TERMINAL"
            if current_state not in {
                ArtifactLifecycleState.DRAFT,
                ArtifactLifecycleState.NEEDS_REVIEW,
                ArtifactLifecycleState.REVIEWED,
            }:
                return "BLOCKED_ALREADY_TERMINAL"
            
            # Use ReviewTransitionEngine to validate transitions
            from_status = LIFECYCLE_TO_REVIEW.get(current_state)
            to_status = (
                ReviewStatus.APPROVED if action_id == "approve_brief" else ReviewStatus.REJECTED
            )
            if from_status is None or not self._transition_engine.can_transition(
                from_status, to_status
            ):
                return "BLOCKED_ALREADY_TERMINAL"

        elif action_id == "generate_ci":
            if current_state not in {
                ArtifactLifecycleState.MISSING,
                ArtifactLifecycleState.FAILED,
            }:
                return "BLOCKED_ASSET_ALREADY_EXISTS"

            # Brief dependency checks
            brief_state = dependencies.get("brief")
            if brief_state is None or brief_state == ArtifactLifecycleState.MISSING:
                return "BLOCKED_MISSING_BRIEF"
            if brief_state == ArtifactLifecycleState.REJECTED:
                return "BLOCKED_DEPENDENCY_REJECTED"
            if brief_state != ArtifactLifecycleState.APPROVED:
                return "BLOCKED_BRIEF_NOT_APPROVED"

        elif action_id == "generate_storyboards":
            if current_state not in {
                ArtifactLifecycleState.MISSING,
                ArtifactLifecycleState.FAILED,
                ArtifactLifecycleState.REJECTED,
            }:
                return "BLOCKED_ASSET_ALREADY_EXISTS"

            # Brief dependency checks
            brief_state = dependencies.get("brief")
            if brief_state is None or brief_state == ArtifactLifecycleState.MISSING:
                return "BLOCKED_MISSING_BRIEF"
            if brief_state == ArtifactLifecycleState.REJECTED:
                return "BLOCKED_DEPENDENCY_REJECTED"
            if brief_state != ArtifactLifecycleState.APPROVED:
                return "BLOCKED_BRIEF_NOT_APPROVED"

            # Content Intelligence dependency checks
            ci_state = dependencies.get("content_intelligence")
            if ci_state is None or ci_state == ArtifactLifecycleState.MISSING:
                return "BLOCKED_MISSING_CONTENT_INTELLIGENCE"
            if ci_state == ArtifactLifecycleState.FAILED:
                return "BLOCKED_DEPENDENCY_REJECTED"

        elif action_id in {"approve_storyboard", "reject_storyboard"}:
            if current_state in {ArtifactLifecycleState.APPROVED, ArtifactLifecycleState.REJECTED}:
                return "BLOCKED_ALREADY_TERMINAL"
            if current_state not in {
                ArtifactLifecycleState.DRAFT,
                ArtifactLifecycleState.NEEDS_REVIEW,
                ArtifactLifecycleState.REVIEWED,
            }:
                return "BLOCKED_ALREADY_TERMINAL"

            # Transition validation
            from_status = LIFECYCLE_TO_REVIEW.get(current_state)
            to_status = (
                ReviewStatus.APPROVED
                if action_id == "approve_storyboard"
                else ReviewStatus.REJECTED
            )
            if from_status is None or not self._transition_engine.can_transition(
                from_status, to_status
            ):
                return "BLOCKED_ALREADY_TERMINAL"

        elif action_id == "generate_assets":
            if current_state not in {
                ArtifactLifecycleState.MISSING,
                ArtifactLifecycleState.FAILED,
                ArtifactLifecycleState.REJECTED,
            }:
                return "BLOCKED_ASSET_ALREADY_EXISTS"

            # Storyboard dependency checks
            storyboard_state = dependencies.get("storyboard")
            if storyboard_state is None or storyboard_state == ArtifactLifecycleState.MISSING:
                return "BLOCKED_MISSING_STORYBOARD"
            if storyboard_state != ArtifactLifecycleState.APPROVED:
                return "BLOCKED_STORYBOARD_NOT_APPROVED"

        elif action_id in {"approve_asset", "reject_asset"}:
            if current_state in {ArtifactLifecycleState.APPROVED, ArtifactLifecycleState.REJECTED}:
                return "BLOCKED_ALREADY_TERMINAL"
            if current_state not in {
                ArtifactLifecycleState.DRAFT,
                ArtifactLifecycleState.NEEDS_REVIEW,
                ArtifactLifecycleState.REVIEWED,
            }:
                return "BLOCKED_ALREADY_TERMINAL"

            # Transition validation
            from_status = LIFECYCLE_TO_REVIEW.get(current_state)
            to_status = (
                ReviewStatus.APPROVED if action_id == "approve_asset" else ReviewStatus.REJECTED
            )
            if from_status is None or not self._transition_engine.can_transition(
                from_status, to_status
            ):
                return "BLOCKED_ALREADY_TERMINAL"

        elif action_id == "build_manifest":
            # Dependencies checks
            brief_state = dependencies.get("brief")
            if brief_state is None or brief_state == ArtifactLifecycleState.MISSING:
                return "BLOCKED_MISSING_BRIEF"

        elif action_id == "plan_week":
            # manifest state in dependencies checks
            manifest_state = dependencies.get("manifest")
            if manifest_state is None or manifest_state == ArtifactLifecycleState.MISSING:
                return "BLOCKED_NO_READY_MANIFESTS"
            if manifest_state != ArtifactLifecycleState.APPROVED:
                return "BLOCKED_NO_READY_MANIFESTS"

        elif action_id == "dry_run":
            # Requires calendar to exist
            calendar_state = dependencies.get("weekly_calendar")
            if calendar_state is None or calendar_state == ArtifactLifecycleState.MISSING:
                return "BLOCKED_MISSING_CALENDAR"

        elif action_id == "publish":
            # Requires dry run checks to be completed and approved
            dry_run_state = dependencies.get("dry_run")
            if dry_run_state is None or dry_run_state != ArtifactLifecycleState.APPROVED:
                return "BLOCKED_DRY_RUN_FAILED"

            # Requires scheduled assets to be approved
            assets_state = dependencies.get("assets")
            if assets_state is None or assets_state != ArtifactLifecycleState.APPROVED:
                return "BLOCKED_UNAPPROVED_ASSET"

        return None
