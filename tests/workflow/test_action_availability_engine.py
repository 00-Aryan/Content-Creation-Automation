"""Tests for ActionAvailabilityEngine — domain-level action availability rules."""

import pytest

from content_creation.workflow.states import ArtifactLifecycleState
from content_creation.workflow.action_availability_engine import (
    ActionAvailabilityEngine,
    AvailableAction,
    BlockedAction,
)


@pytest.fixture
def engine() -> ActionAvailabilityEngine:
    """Fixture to initialise the ActionAvailabilityEngine."""
    return ActionAvailabilityEngine()


class TestActionAvailabilityEngineBasic:
    """Basic availability and state evaluation tests."""

    def test_unknown_artifact_type(self, engine: ActionAvailabilityEngine):
        """Querying an unknown artifact type should return no actions."""
        res = engine.get_actions_result("unknown_type", ArtifactLifecycleState.DRAFT)
        assert len(res.available_actions) == 0
        assert len(res.blocked_actions) == 0

        assert engine.get_available_actions("unknown_type", ArtifactLifecycleState.DRAFT) == []
        assert engine.get_blocked_actions("unknown_type", ArtifactLifecycleState.DRAFT) == []
        assert engine.get_next_recommended_action("unknown_type", ArtifactLifecycleState.DRAFT) is None


class TestBriefActions:
    """Verify rules for Brief artifact actions."""

    def test_brief_missing_generate_available(self, engine: ActionAvailabilityEngine):
        """Brief is MISSING and topic is approved, so generation is available."""
        res = engine.get_actions_result(
            "brief", ArtifactLifecycleState.MISSING, dependencies={"topic": ArtifactLifecycleState.APPROVED}
        )
        assert any(a.action_id == "generate_briefs" for a in res.available_actions)
        assert not any(a.action_id == "generate_briefs" for a in res.blocked_actions)

    def test_brief_missing_topic_rejected(self, engine: ActionAvailabilityEngine):
        """Brief is MISSING but topic is rejected, so generation is blocked."""
        res = engine.get_actions_result(
            "brief", ArtifactLifecycleState.MISSING, dependencies={"topic": ArtifactLifecycleState.REJECTED}
        )
        assert not any(a.action_id == "generate_briefs" for a in res.available_actions)
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_briefs"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_TOPIC_REJECTED"

    def test_brief_missing_topic_missing(self, engine: ActionAvailabilityEngine):
        """Brief is MISSING and topic is missing, so generation is blocked."""
        res = engine.get_actions_result(
            "brief", ArtifactLifecycleState.MISSING, dependencies={"topic": ArtifactLifecycleState.MISSING}
        )
        assert not any(a.action_id == "generate_briefs" for a in res.available_actions)
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_briefs"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_MISSING_SCORED_TOPIC"

    def test_brief_already_exists_draft(self, engine: ActionAvailabilityEngine):
        """Brief is already DRAFT, so generate_briefs is blocked."""
        res = engine.get_actions_result("brief", ArtifactLifecycleState.DRAFT)
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_briefs"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_ASSET_ALREADY_EXISTS"

    def test_brief_approve_reject_flow(self, engine: ActionAvailabilityEngine):
        """Check review transitions for Brief."""
        # Under DRAFT
        res_draft = engine.get_actions_result("brief", ArtifactLifecycleState.DRAFT)
        assert any(a.action_id == "approve_brief" for a in res_draft.available_actions)
        assert not any(a.action_id == "reject_brief" for a in res_draft.available_actions)
        assert any(b.action_id == "reject_brief" for b in res_draft.blocked_actions)

        # Under NEEDS_REVIEW
        res_needs = engine.get_actions_result("brief", ArtifactLifecycleState.NEEDS_REVIEW)
        assert any(a.action_id == "approve_brief" for a in res_needs.available_actions)
        assert any(a.action_id == "reject_brief" for a in res_needs.available_actions)

        # Under APPROVED (terminal)
        res_app = engine.get_actions_result("brief", ArtifactLifecycleState.APPROVED)
        assert not any(a.action_id == "approve_brief" for a in res_app.available_actions)
        assert any(b.action_id == "approve_brief" for b in res_app.blocked_actions)
        assert any(b.action_id == "reject_brief" for b in res_app.blocked_actions)


class TestContentIntelligenceActions:
    """Verify rules for Content Intelligence."""

    def test_ci_missing_brief_missing(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result("content_intelligence", ArtifactLifecycleState.MISSING)
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_ci"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_MISSING_BRIEF"

    def test_ci_missing_brief_rejected(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "content_intelligence",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.REJECTED},
        )
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_ci"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_DEPENDENCY_REJECTED"

    def test_ci_missing_brief_not_approved(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "content_intelligence",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.DRAFT},
        )
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_ci"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_BRIEF_NOT_APPROVED"

    def test_ci_missing_brief_approved(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "content_intelligence",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.APPROVED},
        )
        assert any(a.action_id == "generate_ci" for a in res.available_actions)

    def test_ci_already_exists(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result("content_intelligence", ArtifactLifecycleState.APPROVED)
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_ci"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_ASSET_ALREADY_EXISTS"


class TestStoryboardActions:
    """Verify rules for Storyboard."""

    def test_storyboard_missing_brief_missing(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result("storyboard", ArtifactLifecycleState.MISSING)
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_storyboards"]
        assert any(b.blocking_code == "BLOCKED_MISSING_BRIEF" for b in blocked)

    def test_storyboard_missing_brief_rejected(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "storyboard",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.REJECTED},
        )
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_storyboards"]
        assert any(b.blocking_code == "BLOCKED_DEPENDENCY_REJECTED" for b in blocked)

    def test_storyboard_missing_brief_not_approved(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "storyboard",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.DRAFT},
        )
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_storyboards"]
        assert any(b.blocking_code == "BLOCKED_BRIEF_NOT_APPROVED" for b in blocked)

    def test_storyboard_missing_ci_missing(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "storyboard",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.APPROVED},
        )
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_storyboards"]
        assert any(b.blocking_code == "BLOCKED_MISSING_CONTENT_INTELLIGENCE" for b in blocked)

    def test_storyboard_missing_ci_failed(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "storyboard",
            ArtifactLifecycleState.MISSING,
            dependencies={
                "brief": ArtifactLifecycleState.APPROVED,
                "content_intelligence": ArtifactLifecycleState.FAILED,
            },
        )
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_storyboards"]
        assert any(b.blocking_code == "BLOCKED_DEPENDENCY_REJECTED" for b in blocked)

    def test_storyboard_missing_all_ok(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "storyboard",
            ArtifactLifecycleState.MISSING,
            dependencies={
                "brief": ArtifactLifecycleState.APPROVED,
                "content_intelligence": ArtifactLifecycleState.APPROVED,
            },
        )
        assert any(a.action_id == "generate_storyboards" for a in res.available_actions)

    def test_storyboard_already_exists(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result("storyboard", ArtifactLifecycleState.DRAFT)
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_storyboards"]
        assert any(b.blocking_code == "BLOCKED_ASSET_ALREADY_EXISTS" for b in blocked)

    def test_storyboard_approvals(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result("storyboard", ArtifactLifecycleState.DRAFT)
        assert any(a.action_id == "approve_storyboard" for a in res.available_actions)
        assert not any(a.action_id == "reject_storyboard" for a in res.available_actions)
        assert any(b.action_id == "reject_storyboard" for b in res.blocked_actions)

        # Under NEEDS_REVIEW
        res_needs = engine.get_actions_result("storyboard", ArtifactLifecycleState.NEEDS_REVIEW)
        assert any(a.action_id == "approve_storyboard" for a in res_needs.available_actions)
        assert any(a.action_id == "reject_storyboard" for a in res_needs.available_actions)

        res_app = engine.get_actions_result("storyboard", ArtifactLifecycleState.APPROVED)
        assert not any(a.action_id == "approve_storyboard" for a in res_app.available_actions)
        assert any(b.action_id == "approve_storyboard" for b in res_app.blocked_actions)


class TestAssetActions:
    """Verify rules for Assets."""

    def test_assets_missing_storyboard_missing(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result("assets", ArtifactLifecycleState.MISSING)
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_assets"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_MISSING_STORYBOARD"

    def test_assets_missing_storyboard_not_approved(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "assets",
            ArtifactLifecycleState.MISSING,
            dependencies={"storyboard": ArtifactLifecycleState.DRAFT},
        )
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_assets"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_STORYBOARD_NOT_APPROVED"

    def test_assets_missing_storyboard_approved(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "assets",
            ArtifactLifecycleState.MISSING,
            dependencies={"storyboard": ArtifactLifecycleState.APPROVED},
        )
        assert any(a.action_id == "generate_assets" for a in res.available_actions)

    def test_assets_already_exists(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result("assets", ArtifactLifecycleState.APPROVED)
        blocked = [b for b in res.blocked_actions if b.action_id == "generate_assets"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_ASSET_ALREADY_EXISTS"

    def test_assets_approvals(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result("assets", ArtifactLifecycleState.DRAFT)
        assert any(a.action_id == "approve_asset" for a in res.available_actions)
        assert not any(a.action_id == "reject_asset" for a in res.available_actions)
        assert any(b.action_id == "reject_asset" for b in res.blocked_actions)

        # Under NEEDS_REVIEW
        res_needs = engine.get_actions_result("assets", ArtifactLifecycleState.NEEDS_REVIEW)
        assert any(a.action_id == "approve_asset" for a in res_needs.available_actions)
        assert any(a.action_id == "reject_asset" for a in res_needs.available_actions)

        res_app = engine.get_actions_result("assets", ArtifactLifecycleState.APPROVED)
        assert not any(a.action_id == "approve_asset" for a in res_app.available_actions)


class TestManifestActions:
    """Verify rules for Manifest and WeeklyCalendar."""

    def test_build_manifest_brief_missing(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result("manifest", ArtifactLifecycleState.MISSING)
        blocked = [b for b in res.blocked_actions if b.action_id == "build_manifest"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_MISSING_BRIEF"

    def test_build_manifest_brief_exists(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "manifest",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.APPROVED},
        )
        assert any(a.action_id == "build_manifest" for a in res.available_actions)

    def test_plan_week_manifest_missing(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result("manifest", ArtifactLifecycleState.MISSING)
        blocked = [b for b in res.blocked_actions if b.action_id == "plan_week"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_NO_READY_MANIFESTS"

    def test_plan_week_manifest_not_approved(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "manifest",
            ArtifactLifecycleState.MISSING,
            dependencies={"manifest": ArtifactLifecycleState.PENDING},
        )
        blocked = [b for b in res.blocked_actions if b.action_id == "plan_week"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_NO_READY_MANIFESTS"

    def test_plan_week_manifest_approved(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "manifest",
            ArtifactLifecycleState.MISSING,
            dependencies={"manifest": ArtifactLifecycleState.APPROVED},
        )
        assert any(a.action_id == "plan_week" for a in res.available_actions)


class TestWeeklyCalendarActions:
    """Verify rules for WeeklyCalendar validation and publishing."""

    def test_dry_run_no_calendar(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result("weekly_calendar", ArtifactLifecycleState.MISSING)
        blocked = [b for b in res.blocked_actions if b.action_id == "dry_run"]
        assert len(blocked) == 1
        assert blocked[0].blocking_code == "BLOCKED_MISSING_CALENDAR"

    def test_dry_run_has_calendar(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "weekly_calendar",
            ArtifactLifecycleState.MISSING,
            dependencies={"weekly_calendar": ArtifactLifecycleState.APPROVED},
        )
        assert any(a.action_id == "dry_run" for a in res.available_actions)

    def test_publish_blocked_by_dry_run(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "weekly_calendar",
            ArtifactLifecycleState.MISSING,
            dependencies={"weekly_calendar": ArtifactLifecycleState.APPROVED},
        )
        blocked = [b for b in res.blocked_actions if b.action_id == "publish"]
        assert any(b.blocking_code == "BLOCKED_DRY_RUN_FAILED" for b in blocked)

    def test_publish_blocked_by_assets(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "weekly_calendar",
            ArtifactLifecycleState.MISSING,
            dependencies={
                "weekly_calendar": ArtifactLifecycleState.APPROVED,
                "dry_run": ArtifactLifecycleState.APPROVED,
            },
        )
        blocked = [b for b in res.blocked_actions if b.action_id == "publish"]
        assert any(b.blocking_code == "BLOCKED_UNAPPROVED_ASSET" for b in blocked)

    def test_publish_allowed(self, engine: ActionAvailabilityEngine):
        res = engine.get_actions_result(
            "weekly_calendar",
            ArtifactLifecycleState.MISSING,
            dependencies={
                "weekly_calendar": ArtifactLifecycleState.APPROVED,
                "dry_run": ArtifactLifecycleState.APPROVED,
                "assets": ArtifactLifecycleState.APPROVED,
            },
        )
        assert any(a.action_id == "publish" for a in res.available_actions)


class TestRecommendationLogic:
    """Verify that get_next_recommended_action responds appropriately to current state."""

    def test_brief_recommendations(self, engine: ActionAvailabilityEngine):
        # 1. Missing brief but topic is approved
        rec = engine.get_next_recommended_action(
            "brief", ArtifactLifecycleState.MISSING, dependencies={"topic": ArtifactLifecycleState.APPROVED}
        )
        assert rec == "generate_briefs"

        # 2. Missing brief but topic is rejected
        rec = engine.get_next_recommended_action(
            "brief", ArtifactLifecycleState.MISSING, dependencies={"topic": ArtifactLifecycleState.REJECTED}
        )
        assert rec is None

        # 3. Draft brief
        rec = engine.get_next_recommended_action("brief", ArtifactLifecycleState.DRAFT)
        assert rec == "approve_brief"

        # 4. Approved brief
        rec = engine.get_next_recommended_action("brief", ArtifactLifecycleState.APPROVED)
        assert rec == "generate_ci"

    def test_ci_recommendations(self, engine: ActionAvailabilityEngine):
        # 1. Missing CI, Brief approved
        rec = engine.get_next_recommended_action(
            "content_intelligence",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.APPROVED},
        )
        assert rec == "generate_ci"

        # 2. Missing CI, Brief not approved
        rec = engine.get_next_recommended_action(
            "content_intelligence",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.DRAFT},
        )
        assert rec is None

        # 3. Approved CI
        rec = engine.get_next_recommended_action(
            "content_intelligence", ArtifactLifecycleState.APPROVED
        )
        assert rec == "generate_storyboards"

    def test_storyboard_recommendations(self, engine: ActionAvailabilityEngine):
        # 1. Missing Storyboard, dependencies met
        rec = engine.get_next_recommended_action(
            "storyboard",
            ArtifactLifecycleState.MISSING,
            dependencies={
                "brief": ArtifactLifecycleState.APPROVED,
                "content_intelligence": ArtifactLifecycleState.APPROVED,
            },
        )
        assert rec == "generate_storyboards"

        # 2. Draft Storyboard
        rec = engine.get_next_recommended_action("storyboard", ArtifactLifecycleState.DRAFT)
        assert rec == "approve_storyboard"

        # 3. Approved Storyboard
        rec = engine.get_next_recommended_action("storyboard", ArtifactLifecycleState.APPROVED)
        assert rec == "generate_assets"

    def test_asset_recommendations(self, engine: ActionAvailabilityEngine):
        # 1. Missing assets, Storyboard approved
        rec = engine.get_next_recommended_action(
            "assets",
            ArtifactLifecycleState.MISSING,
            dependencies={"storyboard": ArtifactLifecycleState.APPROVED},
        )
        assert rec == "generate_assets"

        # 2. Draft assets
        rec = engine.get_next_recommended_action("assets", ArtifactLifecycleState.DRAFT)
        assert rec == "approve_asset"

        # 3. Approved assets
        rec = engine.get_next_recommended_action("assets", ArtifactLifecycleState.APPROVED)
        assert rec == "build_manifest"

    def test_manifest_recommendations(self, engine: ActionAvailabilityEngine):
        # 1. Manifest not approved, brief exists
        rec = engine.get_next_recommended_action(
            "manifest",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.APPROVED},
        )
        assert rec == "build_manifest"

        # 2. Manifest approved
        rec = engine.get_next_recommended_action("manifest", ArtifactLifecycleState.APPROVED)
        assert rec == "plan_week"

    def test_calendar_recommendations(self, engine: ActionAvailabilityEngine):
        # 1. Calendar missing, manifest approved
        rec = engine.get_next_recommended_action(
            "weekly_calendar",
            ArtifactLifecycleState.MISSING,
            dependencies={"manifest": ArtifactLifecycleState.APPROVED},
        )
        assert rec == "plan_week"

        # 2. Calendar in draft, calendar approved/exists
        rec = engine.get_next_recommended_action(
            "weekly_calendar",
            ArtifactLifecycleState.DRAFT,
            dependencies={"weekly_calendar": ArtifactLifecycleState.APPROVED},
        )
        assert rec == "dry_run"

        # 3. Calendar approved, dry run and assets approved
        rec = engine.get_next_recommended_action(
            "weekly_calendar",
            ArtifactLifecycleState.APPROVED,
            dependencies={
                "dry_run": ArtifactLifecycleState.APPROVED,
                "assets": ArtifactLifecycleState.APPROVED,
            },
        )
        assert rec == "publish"


class TestQueryAPIs:
    """Verify execution query wrappers."""

    def test_can_execute_action(self, engine: ActionAvailabilityEngine):
        # Allow execute generate_ci if brief is approved
        assert engine.can_execute_action(
            "generate_ci",
            "content_intelligence",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.APPROVED},
        )
        # Block if brief not approved
        assert not engine.can_execute_action(
            "generate_ci",
            "content_intelligence",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.DRAFT},
        )

    def test_explain_blocking_reason(self, engine: ActionAvailabilityEngine):
        reason = engine.explain_blocking_reason(
            "generate_ci",
            "content_intelligence",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.DRAFT},
        )
        assert reason == "Upstream brief is not approved."

        # Should be None if not blocked
        reason_none = engine.explain_blocking_reason(
            "generate_ci",
            "content_intelligence",
            ArtifactLifecycleState.MISSING,
            dependencies={"brief": ArtifactLifecycleState.APPROVED},
        )
        assert reason_none is None


class TestActionAvailabilityEngineExtended:
    """Verify new engine APIs and 100% coverage."""

    def test_get_available_actions_detailed(self, engine: ActionAvailabilityEngine):
        # Trigger the relevant actions loop and check available_actions and blocking_reasons
        res = engine.get_available_actions(
            "brief",
            ArtifactLifecycleState.MISSING,
            dependencies={"topic": ArtifactLifecycleState.APPROVED},
        )
        assert res.allowed is True
        assert "generate_briefs" in res.available_actions
        assert any(b.action_id == "approve_brief" for b in res.blocking_reasons)
        assert res.recommended_action == "generate_briefs"

        # Compare result against list of strings (using __eq__ overload)
        assert res == ["generate_briefs"]
        
        # Test __eq__ default comparison (super().__eq__)
        assert res != "not a list or ActionAvailabilityResult"
        assert res == res

    def test_evaluate_dependencies(self, engine: ActionAvailabilityEngine):
        # generate_briefs
        eval_gb_pass = engine.evaluate_dependencies("generate_briefs", {"topic": ArtifactLifecycleState.APPROVED})
        assert eval_gb_pass.passed is True
        eval_gb_fail = engine.evaluate_dependencies("generate_briefs", {"topic": ArtifactLifecycleState.REJECTED})
        assert eval_gb_fail.passed is False

        # generate_ci
        eval_ci_pass = engine.evaluate_dependencies("generate_ci", {"brief": ArtifactLifecycleState.APPROVED})
        assert eval_ci_pass.passed is True
        eval_ci_fail = engine.evaluate_dependencies("generate_ci", {"brief": ArtifactLifecycleState.DRAFT})
        assert eval_ci_fail.passed is False

        # generate_storyboards
        eval_sb_pass = engine.evaluate_dependencies(
            "generate_storyboards",
            {"brief": ArtifactLifecycleState.APPROVED, "content_intelligence": ArtifactLifecycleState.APPROVED},
        )
        assert eval_sb_pass.passed is True
        eval_sb_fail1 = engine.evaluate_dependencies(
            "generate_storyboards",
            {"brief": ArtifactLifecycleState.DRAFT, "content_intelligence": ArtifactLifecycleState.APPROVED},
        )
        assert eval_sb_fail1.passed is False
        eval_sb_fail2 = engine.evaluate_dependencies(
            "generate_storyboards",
            {"brief": ArtifactLifecycleState.APPROVED, "content_intelligence": ArtifactLifecycleState.FAILED},
        )
        assert eval_sb_fail2.passed is False

        # generate_assets
        eval_ga_pass = engine.evaluate_dependencies("generate_assets", {"storyboard": ArtifactLifecycleState.APPROVED})
        assert eval_ga_pass.passed is True
        eval_ga_fail = engine.evaluate_dependencies("generate_assets", {"storyboard": ArtifactLifecycleState.DRAFT})
        assert eval_ga_fail.passed is False

        # build_manifest
        eval_bm_pass = engine.evaluate_dependencies("build_manifest", {"brief": ArtifactLifecycleState.APPROVED})
        assert eval_bm_pass.passed is True
        eval_bm_fail = engine.evaluate_dependencies("build_manifest", {"brief": ArtifactLifecycleState.MISSING})
        assert eval_bm_fail.passed is False

        # plan_week
        eval_pw_pass = engine.evaluate_dependencies("plan_week", {"manifest": ArtifactLifecycleState.APPROVED})
        assert eval_pw_pass.passed is True
        eval_pw_fail = engine.evaluate_dependencies("plan_week", {"manifest": ArtifactLifecycleState.DRAFT})
        assert eval_pw_fail.passed is False

        # dry_run
        eval_dr_pass = engine.evaluate_dependencies("dry_run", {"weekly_calendar": ArtifactLifecycleState.DRAFT})
        assert eval_dr_pass.passed is True
        eval_dr_fail = engine.evaluate_dependencies("dry_run", {"weekly_calendar": ArtifactLifecycleState.MISSING})
        assert eval_dr_fail.passed is False

        # publish
        eval_pub_pass = engine.evaluate_dependencies(
            "publish",
            {"dry_run": ArtifactLifecycleState.APPROVED, "assets": ArtifactLifecycleState.APPROVED},
        )
        assert eval_pub_pass.passed is True
        eval_pub_fail1 = engine.evaluate_dependencies(
            "publish",
            {"dry_run": ArtifactLifecycleState.FAILED, "assets": ArtifactLifecycleState.APPROVED},
        )
        assert eval_pub_fail1.passed is False
        eval_pub_fail2 = engine.evaluate_dependencies(
            "publish",
            {"dry_run": ArtifactLifecycleState.APPROVED, "assets": ArtifactLifecycleState.FAILED},
        )
        assert eval_pub_fail2.passed is False

        # unhandled action
        eval_unhandled = engine.evaluate_dependencies("approve_brief", {})
        assert eval_unhandled.passed is True
        assert len(eval_unhandled.checks) == 0

    def test_get_next_recommended_actions(self, engine: ActionAvailabilityEngine):
        recs = engine.get_next_recommended_actions(
            "brief",
            ArtifactLifecycleState.MISSING,
            dependencies={"topic": ArtifactLifecycleState.APPROVED},
        )
        assert recs == ["generate_briefs"]

    def test_is_action_available(self, engine: ActionAvailabilityEngine):
        assert engine.is_action_available(
            "generate_briefs",
            "brief",
            ArtifactLifecycleState.MISSING,
            dependencies={"topic": ArtifactLifecycleState.APPROVED},
        )

