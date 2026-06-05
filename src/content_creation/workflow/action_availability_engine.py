"""Action Availability Engine: maps artifact states and dependencies to available actions.

This engine is a pure domain-level, deterministic, and side-effect free service.
It determines which operator or system actions are available, which are blocked,
and explains the reasons why, conforming to the canonical Action Registry definitions.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from content_creation.shared.enums import ReviewStatus
from content_creation.workflow.review_transition_engine import ReviewTransitionEngine
from content_creation.workflow.states import ArtifactLifecycleState


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AvailableAction:
    """Represents an action that can be executed in the current state (backward compatibility)."""
    action_id: str
    category: str
    description: str


@dataclass(frozen=True)
class BlockedAction:
    """Represents an action that is currently blocked with a reason code, message, and recommendation."""
    action_id: str
    blocking_code: str
    blocking_message: str
    recommendation: str = ""
    category: str = "SYSTEM"  # backward compatibility


@dataclass(frozen=True)
class DependencyCheck:
    """Evaluation output of a single dependency check."""
    dependency_type: str
    required_state: ArtifactLifecycleState
    actual_state: ArtifactLifecycleState
    optional: bool
    passed: bool


@dataclass(frozen=True)
class DependencyEvaluation:
    """Aggregated evaluation details of all checks for an action."""
    action_id: str
    passed: bool
    checks: List[DependencyCheck]


@dataclass(frozen=True)
class ActionAvailabilityResult:
    """Canonical result mapping evaluated states to UI actions."""
    allowed: bool
    warnings: List[str]
    blocking_reasons: List[BlockedAction]
    lifecycle_state: ArtifactLifecycleState
    available_actions: List[str]
    recommended_action: Optional[str]
    dependency_status: Dict[str, ArtifactLifecycleState]

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, list):
            return self.available_actions == other
        return super().__eq__(other)


@dataclass(frozen=True)
class OldActionAvailabilityResult:
    """Result container for backward compatibility in tests."""
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
    "BLOCKED_INVALID_STATE": "The target artifact is in an invalid state for this action.",
    "BLOCKED_MANIFEST_NOT_READY": "The topic manifest is not fully approved and compiled.",
}

BLOCKING_RECOMMENDATIONS = {
    "BLOCKED_TOPIC_REJECTED": "Select a different topic from the staged pool.",
    "BLOCKED_MISSING_SCORED_TOPIC": "Run the `score-topics` command on this topic first.",
    "BLOCKED_BRIEF_MISSING": "Generate the brief first.",
    "BLOCKED_BRIEF_NOT_APPROVED": "Review the brief and set status to APPROVED.",
    "BLOCKED_STORYBOARD_MISSING": "Generate the storyboard first.",
    "BLOCKED_STORYBOARD_NOT_APPROVED": "Review the storyboard and set status to APPROVED.",
    "BLOCKED_ASSET_ALREADY_EXISTS": "Archive the asset or provide an override flag.",
    "BLOCKED_DEPENDENCY_REJECTED": "Revise the brief or generate a new one.",
    "BLOCKED_NO_READY_MANIFESTS": "Review and approve topic assets to compile manifests.",
    "BLOCKED_MISSING_CALENDAR": "Generate the calendar by planning the week first.",
    "BLOCKED_DRY_RUN_FAILED": "Fix scheduling conflicts or unapproved assets shown in report.",
    "BLOCKED_UNAPPROVED_ASSET": "Review and approve the asset for publication.",
    "BLOCKED_ALREADY_TERMINAL": "Revise/regenerate the asset to reopen it.",
    "BLOCKED_INVALID_TRANSITION": "Follow standard progression: DRAFT -> NEEDS_REVIEW -> APPROVED.",
    "BLOCKED_INVALID_STATE": "Re-stage the item or select a valid state.",
    "BLOCKED_MANIFEST_NOT_READY": "Run manifest generation or approve all child assets first.",
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

    def get_available_actions(
        self,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> ActionAvailabilityResult:
        """Determines the complete availability profile of the target artifact."""
        deps = dependencies or {}
        relevant_actions = self._get_relevant_actions_for_type(artifact_type)
        
        available_actions = []
        blocking_reasons = []
        
        for action_id in relevant_actions:
            reasons = self.get_blocking_reasons(action_id, artifact_type, current_state, deps)
            if not reasons:
                available_actions.append(action_id)
            else:
                blocking_reasons.extend(reasons)
                
        rec_actions = self.get_next_recommended_actions(artifact_type, current_state, deps)
        rec_action = rec_actions[0] if rec_actions else None
        
        allowed = len(available_actions) > 0
        
        return ActionAvailabilityResult(
            allowed=allowed,
            warnings=[],
            blocking_reasons=blocking_reasons,
            lifecycle_state=current_state,
            available_actions=available_actions,
            recommended_action=rec_action,
            dependency_status=deps,
        )

    def is_action_available(
        self,
        action_id: str,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> bool:
        """Shorthand check to see if an action is allowed."""
        deps = dependencies or {}
        blocking_code = self._check_blocking_reason(action_id, artifact_type, current_state, deps)
        return blocking_code is None

    def evaluate_dependencies(
        self,
        action_id: str,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> DependencyEvaluation:
        """Compares actual dependency states against registered action prerequisites."""
        deps = dependencies or {}
        checks = []
        passed = True

        if action_id == "generate_briefs":
            topic_state = deps.get("topic", ArtifactLifecycleState.MISSING)
            check_passed = topic_state not in {ArtifactLifecycleState.REJECTED, ArtifactLifecycleState.MISSING}
            checks.append(
                DependencyCheck(
                    dependency_type="topic",
                    required_state=ArtifactLifecycleState.DRAFT,
                    actual_state=topic_state,
                    optional=False,
                    passed=check_passed
                )
            )
            if not check_passed:
                passed = False

        elif action_id == "generate_ci":
            brief_state = deps.get("brief", ArtifactLifecycleState.MISSING)
            check_passed = brief_state == ArtifactLifecycleState.APPROVED
            checks.append(
                DependencyCheck(
                    dependency_type="brief",
                    required_state=ArtifactLifecycleState.APPROVED,
                    actual_state=brief_state,
                    optional=False,
                    passed=check_passed
                )
            )
            if not check_passed:
                passed = False

        elif action_id == "generate_storyboards":
            brief_state = deps.get("brief", ArtifactLifecycleState.MISSING)
            brief_passed = brief_state == ArtifactLifecycleState.APPROVED
            checks.append(
                DependencyCheck(
                    dependency_type="brief",
                    required_state=ArtifactLifecycleState.APPROVED,
                    actual_state=brief_state,
                    optional=False,
                    passed=brief_passed
                )
            )
            if not brief_passed:
                passed = False

            ci_state = deps.get("content_intelligence", ArtifactLifecycleState.MISSING)
            ci_passed = ci_state not in {ArtifactLifecycleState.MISSING, ArtifactLifecycleState.FAILED}
            checks.append(
                DependencyCheck(
                    dependency_type="content_intelligence",
                    required_state=ArtifactLifecycleState.APPROVED,
                    actual_state=ci_state,
                    optional=False,
                    passed=ci_passed
                )
            )
            if not ci_passed:
                passed = False

        elif action_id == "generate_assets":
            storyboard_state = deps.get("storyboard", ArtifactLifecycleState.MISSING)
            check_passed = storyboard_state == ArtifactLifecycleState.APPROVED
            checks.append(
                DependencyCheck(
                    dependency_type="storyboard",
                    required_state=ArtifactLifecycleState.APPROVED,
                    actual_state=storyboard_state,
                    optional=False,
                    passed=check_passed
                )
            )
            if not check_passed:
                passed = False

        elif action_id == "build_manifest":
            brief_state = deps.get("brief", ArtifactLifecycleState.MISSING)
            check_passed = brief_state != ArtifactLifecycleState.MISSING
            checks.append(
                DependencyCheck(
                    dependency_type="brief",
                    required_state=ArtifactLifecycleState.APPROVED,
                    actual_state=brief_state,
                    optional=False,
                    passed=check_passed
                )
            )
            if not check_passed:
                passed = False

        elif action_id == "plan_week":
            manifest_state = deps.get("manifest", ArtifactLifecycleState.MISSING)
            check_passed = manifest_state == ArtifactLifecycleState.APPROVED
            checks.append(
                DependencyCheck(
                    dependency_type="manifest",
                    required_state=ArtifactLifecycleState.APPROVED,
                    actual_state=manifest_state,
                    optional=False,
                    passed=check_passed
                )
            )
            if not check_passed:
                passed = False

        elif action_id == "dry_run":
            calendar_state = deps.get("weekly_calendar", ArtifactLifecycleState.MISSING)
            check_passed = calendar_state != ArtifactLifecycleState.MISSING
            checks.append(
                DependencyCheck(
                    dependency_type="weekly_calendar",
                    required_state=ArtifactLifecycleState.DRAFT,
                    actual_state=calendar_state,
                    optional=False,
                    passed=check_passed
                )
            )
            if not check_passed:
                passed = False

        elif action_id == "publish":
            dry_run_state = deps.get("dry_run", ArtifactLifecycleState.MISSING)
            dr_passed = dry_run_state == ArtifactLifecycleState.APPROVED
            checks.append(
                DependencyCheck(
                    dependency_type="dry_run",
                    required_state=ArtifactLifecycleState.APPROVED,
                    actual_state=dry_run_state,
                    optional=False,
                    passed=dr_passed
                )
            )
            if not dr_passed:
                passed = False

            assets_state = deps.get("assets", ArtifactLifecycleState.MISSING)
            assets_passed = assets_state == ArtifactLifecycleState.APPROVED
            checks.append(
                DependencyCheck(
                    dependency_type="assets",
                    required_state=ArtifactLifecycleState.APPROVED,
                    actual_state=assets_state,
                    optional=False,
                    passed=assets_passed
                )
            )
            if not assets_passed:
                passed = False

        return DependencyEvaluation(action_id=action_id, passed=passed, checks=checks)

    def get_blocking_reasons(
        self,
        action_id: str,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> List[BlockedAction]:
        """Queries the exact reasons why a specific action is blocked."""
        deps = dependencies or {}
        blocking_code = self._check_blocking_reason(action_id, artifact_type, current_state, deps)
        if blocking_code:
            message = BLOCKING_MESSAGES.get(blocking_code, "Action is blocked.")
            recommendation = BLOCKING_RECOMMENDATIONS.get(blocking_code, "Check dependency requirements.")
            meta = ACTION_METADATA.get(action_id, {"category": "SYSTEM"})
            return [
                BlockedAction(
                    action_id=action_id,
                    blocking_code=blocking_code,
                    blocking_message=message,
                    recommendation=recommendation,
                    category=meta["category"],
                )
            ]
        return []

    def get_next_recommended_actions(
        self,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> List[str]:
        """Determine next recommended actions for the operator."""
        deps = dependencies or {}
        rec = self.get_next_recommended_action(artifact_type, current_state, deps)
        return [rec] if rec else []

    # ------------------------------------------------------------------
    # Compatibility Methods for existing code and tests
    # ------------------------------------------------------------------

    def can_execute_action(
        self,
        action_id: str,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> bool:
        """Backward compatibility: alias for is_action_available."""
        return self.is_action_available(action_id, artifact_type, current_state, dependencies)

    def explain_blocking_reason(
        self,
        action_id: str,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> Optional[str]:
        """Backward compatibility: returns user-friendly blocking message."""
        reasons = self.get_blocking_reasons(action_id, artifact_type, current_state, dependencies)
        return reasons[0].blocking_message if reasons else None

    def get_actions_result(
        self,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> OldActionAvailabilityResult:
        """Backward compatibility: returns the old ActionsAvailabilityResult format for tests."""
        deps = dependencies or {}
        relevant_actions = self._get_relevant_actions_for_type(artifact_type)
        
        available = []
        blocked = []
        
        for action_id in relevant_actions:
            reasons = self.get_blocking_reasons(action_id, artifact_type, current_state, deps)
            meta = ACTION_METADATA.get(action_id, {"category": "SYSTEM", "description": ""})
            if not reasons:
                available.append(
                    AvailableAction(
                        action_id=action_id,
                        category=meta["category"],
                        description=meta["description"],
                    )
                )
            else:
                for r in reasons:
                    blocked.append(
                        BlockedAction(
                            action_id=action_id,
                            category=meta["category"],
                            blocking_code=r.blocking_code,
                            blocking_message=r.blocking_message,
                            recommendation=r.recommendation,
                        )
                    )
        return OldActionAvailabilityResult(available_actions=available, blocked_actions=blocked)

    def get_blocked_actions(
        self,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> List[BlockedAction]:
        """Backward compatibility: returns lists of blocked actions."""
        res = self.get_actions_result(artifact_type, current_state, dependencies)
        return res.blocked_actions

    def get_next_recommended_action(
        self,
        artifact_type: str,
        current_state: ArtifactLifecycleState,
        dependencies: Optional[Dict[str, ArtifactLifecycleState]] = None,
    ) -> Optional[str]:
        """Backward compatibility: returns recommended action."""
        deps = dependencies or {}
        
        if artifact_type == "brief":
            if current_state in {ArtifactLifecycleState.MISSING, ArtifactLifecycleState.FAILED, ArtifactLifecycleState.REJECTED}:
                if self.is_action_available("generate_briefs", "brief", current_state, deps):
                    return "generate_briefs"
            elif current_state in {ArtifactLifecycleState.DRAFT, ArtifactLifecycleState.NEEDS_REVIEW, ArtifactLifecycleState.REVIEWED}:
                return "approve_brief"
            elif current_state == ArtifactLifecycleState.APPROVED:
                return "generate_ci"

        elif artifact_type == "content_intelligence":
            if current_state in {ArtifactLifecycleState.MISSING, ArtifactLifecycleState.FAILED}:
                if self.is_action_available("generate_ci", "content_intelligence", current_state, deps):
                    return "generate_ci"
            elif current_state == ArtifactLifecycleState.APPROVED:
                return "generate_storyboards"

        elif artifact_type == "storyboard":
            if current_state in {ArtifactLifecycleState.MISSING, ArtifactLifecycleState.FAILED, ArtifactLifecycleState.REJECTED}:
                if self.is_action_available("generate_storyboards", "storyboard", current_state, deps):
                    return "generate_storyboards"
            elif current_state in {ArtifactLifecycleState.DRAFT, ArtifactLifecycleState.NEEDS_REVIEW, ArtifactLifecycleState.REVIEWED}:
                return "approve_storyboard"
            elif current_state == ArtifactLifecycleState.APPROVED:
                return "generate_assets"

        elif artifact_type == "assets":
            if current_state in {ArtifactLifecycleState.MISSING, ArtifactLifecycleState.FAILED, ArtifactLifecycleState.REJECTED}:
                if self.is_action_available("generate_assets", "assets", current_state, deps):
                    return "generate_assets"
            elif current_state in {ArtifactLifecycleState.DRAFT, ArtifactLifecycleState.NEEDS_REVIEW, ArtifactLifecycleState.REVIEWED}:
                return "approve_asset"
            elif current_state == ArtifactLifecycleState.APPROVED:
                return "build_manifest"

        elif artifact_type == "manifest":
            if current_state != ArtifactLifecycleState.APPROVED:
                if self.is_action_available("build_manifest", "manifest", current_state, deps):
                    return "build_manifest"
            else:
                return "plan_week"

        elif artifact_type == "weekly_calendar":
            if current_state == ArtifactLifecycleState.MISSING:
                if self.is_action_available("plan_week", "weekly_calendar", current_state, deps):
                    return "plan_week"
            elif current_state == ArtifactLifecycleState.DRAFT:
                if self.is_action_available("dry_run", "weekly_calendar", current_state, deps):
                    return "dry_run"
            elif current_state == ArtifactLifecycleState.APPROVED:
                if self.is_action_available("publish", "weekly_calendar", current_state, deps):
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
