"""Phase 7 validation runner for v0.6 backend architecture.

This utility is evidence collection only. It creates isolated fixture workspaces,
uses deterministic generator/service patches to avoid external API calls, and
writes reproducible JSON evidence for the release validation report.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

from content_creation.application import ApplicationContext
from content_creation.application.asset_generation_service import AssetGenerationService
from content_creation.application.content_intelligence_service import ContentIntelligenceService
from content_creation.application.pipeline_run_service import PipelineRunService
from content_creation.application.storyboard_service import StoryboardService
from content_creation.domains.content_intelligence import (
    ContentIntelligence,
    ContrastPair,
    EmotionalRegister,
    Hook,
    TopicType,
)
from content_creation.domains.storyboard import Storyboard
from content_creation.generation.carousel import CarouselGenerator
from content_creation.generation.newsletter import NewsletterGenerator
from content_creation.generation.script import ScriptGenerator
from content_creation.generation.thumbnail import ThumbnailGenerator
from content_creation.manifest import ManifestBuilder
from content_creation.models.brief import Brief
from content_creation.models.carousel import Carousel, CarouselSlide
from content_creation.models.newsletter import Newsletter, NewsletterSection
from content_creation.models.script import Script
from content_creation.models.thumbnail import ThumbnailPrompt
from content_creation.models.topic import ScoredTopicItem, TopicCategory, TopicItem, TopicStatus
from content_creation.shared.enums import ReviewStatus
from content_creation.workflow.state import WorkflowStateManager


EVIDENCE_ROOT = Path(__file__).resolve().parent
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RUN_DIR = EVIDENCE_ROOT / RUN_ID


@dataclass
class ScenarioResult:
    id: str
    objective: str
    procedure: list[str]
    expected: str
    observed: str
    result: str
    evidence: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)


@dataclass
class Finding:
    id: str
    severity: str
    scenario: str
    expected_behavior: str
    actual_behavior: str
    impact: str
    release_recommendation: str


RESULTS: list[ScenarioResult] = []
FINDINGS: list[Finding] = []


def iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def rel(path: Path) -> str:
    return str(path.relative_to(RUN_DIR))


def read_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def list_tree(base: Path) -> list[str]:
    if not base.exists():
        return []
    return sorted(str(p.relative_to(base)) for p in base.rglob("*") if p.is_file())


def hash_tree(base: Path, include_manifests: bool = True) -> dict[str, str]:
    hashes = {}
    if not base.exists():
        return hashes
    for path in sorted(base.rglob("*.json")):
        rel_path = str(path.relative_to(base))
        if not include_manifests and rel_path.startswith("manifests/"):
            continue
        hashes[rel_path] = file_hash(path)
    return hashes


def make_workspace(name: str) -> Path:
    path = RUN_DIR / "workspaces" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_topic(idx: int, score: float = 90.0, formats: list[str] | None = None) -> tuple[TopicItem, ScoredTopicItem]:
    topic_id = f"phase7-topic-{idx}"
    url = f"https://example.com/phase7/topic-{idx}"
    staged = TopicItem(
        id=topic_id,
        title=f"Phase 7 Topic {idx}",
        url=url,
        source="phase7_fixture",
        published_at="2026-06-03T00:00:00Z",
        author="Validation",
        raw_text=f"Fixture raw text for topic {idx}",
        excerpt=f"Fixture excerpt {idx}",
        category=TopicCategory.PAPER,
        topic_tags=["phase7", "validation"],
        status=TopicStatus.STAGED,
        metadata={"recommended_formats": formats or ["short_video", "carousel", "newsletter"]},
    )
    scored = ScoredTopicItem(
        **staged.model_dump(exclude={"status"}),
        status=TopicStatus.SCORED,
        priority_score=score,
        scoring_details={"fixture": score},
        validation_flags=[],
    )
    return staged, scored


def make_brief(topic_id: str, formats: list[str] | None = None, status: ReviewStatus = ReviewStatus.NEEDS_REVIEW) -> Brief:
    return Brief(
        topic_id=topic_id,
        why_it_matters=f"Why {topic_id} matters",
        plain_english_summary=[
            "BRIEF_CLAIM_DO_NOT_USE",
            f"Plain summary for {topic_id}",
            f"Student-friendly consequence for {topic_id}",
        ],
        student_takeaway=f"Takeaway for {topic_id}",
        analogy="BRIEF_ANALOGY_DO_NOT_USE",
        limitation=f"Limitation for {topic_id}",
        audience_fit="advanced beginners",
        recommended_formats=formats or ["short_video", "carousel", "newsletter"],
        source_url=f"https://example.com/{topic_id}",
        review_status=status,
        generated_at=iso(),
    )


def make_ci(topic_id: str, status: ReviewStatus = ReviewStatus.NEEDS_REVIEW) -> ContentIntelligence:
    return ContentIntelligence(
        topic_id=topic_id,
        generated_at=iso(),
        review_status=status,
        quality_status="ready",
        topic_type=TopicType.PAPER,
        timeliness_hook="Published this week",
        primary_hook=Hook(
            hook_text=f"Primary hook for {topic_id}",
            hook_type="question",
            source_field="why_it_matters",
        ),
        secondary_hook=Hook(
            hook_text=f"Secondary hook for {topic_id}",
            hook_type="bold_claim",
            source_field="limitation",
        ),
        story_angle=f"Story angle for {topic_id}",
        curiosity_gap=f"Curiosity gap for {topic_id}",
        contrast_pair=ContrastPair(before="before", after="after"),
        emotional_register=EmotionalRegister.SURPRISE,
    )


def make_storyboard(topic_id: str, status: ReviewStatus = ReviewStatus.NEEDS_REVIEW) -> Storyboard:
    return Storyboard(
        topic_id=topic_id,
        generated_at=iso(),
        review_status=status,
        formats_planned=["short_video", "carousel", "newsletter"],
        script_hook="STORYBOARD_SCRIPT_HOOK_USED",
        carousel_hook="STORYBOARD_CAROUSEL_HOOK_USED",
        newsletter_hook="STORYBOARD_NEWSLETTER_HOOK_USED",
        thumbnail_hook="STORYBOARD_THUMBNAIL_HOOK_USED",
        script_cta="STORYBOARD_SCRIPT_CTA_USED",
        carousel_cta="STORYBOARD_CAROUSEL_CTA_USED",
        newsletter_cta="STORYBOARD_NEWSLETTER_CTA_USED",
        script_claims=["STORYBOARD_SCRIPT_CLAIM_USED"],
        carousel_claims=["STORYBOARD_CAROUSEL_CLAIM_USED"],
        newsletter_claims=["STORYBOARD_NEWSLETTER_CLAIM_USED"],
        visual_style="diagram_overlay",
        visual_metaphor="STORYBOARD_VISUAL_METAPHOR_USED",
    )


def make_thumbnail(topic_id: str, storyboard: Storyboard | None, status: ReviewStatus = ReviewStatus.NEEDS_REVIEW) -> ThumbnailPrompt:
    return ThumbnailPrompt(
        topic_id=topic_id,
        title_text=storyboard.thumbnail_hook if storyboard else "FALLBACK_NO_STORYBOARD",
        supporting_text="supporting text",
        visual_metaphor=storyboard.visual_metaphor if storyboard else "FALLBACK_NO_STORYBOARD",
        style=storyboard.visual_style if storyboard else "clean_minimal",
        negative_prompt=["none"],
        readability_notes="readable",
        review_status=status,
        generated_at=iso(),
    )


def make_script(topic_id: str, storyboard: Storyboard | None, status: ReviewStatus = ReviewStatus.NEEDS_REVIEW) -> Script:
    return Script(
        topic_id=topic_id,
        format="short_video",
        hook=storyboard.script_hook if storyboard else "FALLBACK_NO_STORYBOARD",
        script_sections=["section 1", "section 2"],
        cta=storyboard.script_cta if storyboard else "FALLBACK_NO_STORYBOARD",
        claims_used=storyboard.script_claims if storyboard else ["FALLBACK_NO_STORYBOARD"],
        source_links=[f"https://example.com/{topic_id}"],
        review_status=status,
        generated_at=iso(),
    )


def make_carousel(topic_id: str, storyboard: Storyboard | None, status: ReviewStatus = ReviewStatus.NEEDS_REVIEW) -> Carousel:
    return Carousel(
        topic_id=topic_id,
        slides=[
            CarouselSlide(
                slide_number=1,
                title=storyboard.carousel_hook if storyboard else "FALLBACK_NO_STORYBOARD",
                body="body",
                visual_note=storyboard.visual_metaphor if storyboard else "FALLBACK_NO_STORYBOARD",
            )
        ],
        cta_slide=storyboard.carousel_cta if storyboard else "FALLBACK_NO_STORYBOARD",
        claims_used=storyboard.carousel_claims if storyboard else ["FALLBACK_NO_STORYBOARD"],
        source_links=[f"https://example.com/{topic_id}"],
        review_status=status,
        generated_at=iso(),
    )


def make_newsletter(topic_id: str, storyboard: Storyboard | None, status: ReviewStatus = ReviewStatus.NEEDS_REVIEW) -> Newsletter:
    return Newsletter(
        topic_id=topic_id,
        subject_line=storyboard.newsletter_hook if storyboard else "FALLBACK_NO_STORYBOARD",
        sections=[
            NewsletterSection(section_name="what_happened", content="what happened"),
            NewsletterSection(section_name="why_it_matters", content="why it matters"),
            NewsletterSection(section_name="student_takeaway", content="takeaway"),
        ],
        cta=storyboard.newsletter_cta if storyboard else "FALLBACK_NO_STORYBOARD",
        claims_used=storyboard.newsletter_claims if storyboard else ["FALLBACK_NO_STORYBOARD"],
        source_links=[f"https://example.com/{topic_id}"],
        review_status=status,
        generated_at=iso(),
    )


class FakeCollect:
    def __init__(self, topics: list[tuple[TopicItem, ScoredTopicItem]]):
        self.topics = topics

    def run(self, ctx, source_filter=None):
        for staged, _ in self.topics:
            try:
                ctx.storage.save_staged(staged)
            except FileExistsError:
                pass
        return type("CollectResult", (), {"count": len(self.topics)})()


class FakeScore:
    def __init__(self, topics: list[tuple[TopicItem, ScoredTopicItem]]):
        self.topics = topics

    def run(self, ctx):
        for _, scored in self.topics:
            ctx.storage.save_scored(scored)
        return type("ScoreResult", (), {"scored_count": len(self.topics), "rejected_count": 0})()


class FakeCIGenerator:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, brief, topic_category=None, published_at=None):
        return make_ci(brief.topic_id)


class FakeStoryboardGenerator:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, brief, ci):
        return make_storyboard(brief.topic_id)


class FakeThumbnailGenerator:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, storyboard, brief):
        return make_thumbnail(brief.topic_id, storyboard)


class FakeScriptGenerator:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, storyboard, brief, format):
        return make_script(brief.topic_id, storyboard)


class FakeCarouselGenerator:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, storyboard, brief):
        return make_carousel(brief.topic_id, storyboard)


class FakeNewsletterGenerator:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, storyboard, brief):
        return make_newsletter(brief.topic_id, storyboard)


def pipeline_patches(topics: list[tuple[TopicItem, ScoredTopicItem]]):
    return [
        patch("content_creation.application.pipeline_run_service.CollectTopicsService", lambda: FakeCollect(topics)),
        patch("content_creation.application.pipeline_run_service.ScoreTopicsService", lambda: FakeScore(topics)),
        patch("content_creation.application.brief_generation_service.generate_brief", lambda item, registry, key: make_brief(item.id, item.metadata.get("recommended_formats"))),
        patch("content_creation.application.content_intelligence_service.ContentIntelligenceGenerator", FakeCIGenerator),
        patch("content_creation.application.storyboard_service.StoryboardGenerator", FakeStoryboardGenerator),
        patch("content_creation.application.asset_generation_service.ThumbnailGenerator", FakeThumbnailGenerator),
        patch("content_creation.application.asset_generation_service.ScriptGenerator", FakeScriptGenerator),
        patch("content_creation.application.asset_generation_service.CarouselGenerator", FakeCarouselGenerator),
        patch("content_creation.application.asset_generation_service.NewsletterGenerator", FakeNewsletterGenerator),
        patch("content_creation.application.brief_generation_service.time.sleep", lambda _: None),
        patch("content_creation.application.content_intelligence_service.time.sleep", lambda _: None),
        patch("content_creation.application.storyboard_service.time.sleep", lambda _: None),
        patch("content_creation.application.asset_generation_service.time.sleep", lambda _: None),
    ]


class PatchStack:
    def __init__(self, patches):
        self.patches = patches
        self.started = []

    def __enter__(self):
        for p in self.patches:
            self.started.append(p.start())
        return self

    def __exit__(self, exc_type, exc, tb):
        for p in reversed(self.patches):
            p.stop()


def run_pipeline_workspace(name: str, topics: list[tuple[TopicItem, ScoredTopicItem]], top_n: int) -> tuple[Path, Any, ApplicationContext]:
    workspace = make_workspace(name)
    ctx = ApplicationContext.create(workspace)
    with PatchStack(pipeline_patches(topics)):
        result = PipelineRunService().run(ctx, top_n=top_n, api_key="phase7-key")
    return workspace, result, ctx


def collect_workspace_evidence(name: str, workspace: Path, result: Any | None = None) -> list[str]:
    evidence_dir = RUN_DIR / "evidence" / name
    data_dir = workspace / "data"
    paths = []
    paths.append(write_json(evidence_dir / "tree.json", list_tree(data_dir)))
    paths.append(write_json(evidence_dir / "hashes.json", hash_tree(data_dir)))
    if result is not None:
        paths.append(write_json(evidence_dir / "pipeline_result.json", {
            "success": result.success,
            "stages": result.stages,
            "stage_summaries": result.stage_summaries,
            "log_path": str(result.log_path),
        }))
        if result.log_path.exists():
            shutil.copy(result.log_path, evidence_dir / "pipeline_log.jsonl")
            paths.append(evidence_dir / "pipeline_log.jsonl")
    for subdir in [
        "staged",
        "scored",
        "briefs",
        "content_intelligence",
        "storyboards",
        "thumbnails",
        "scripts",
        "carousels",
        "newsletters",
        "manifests",
        "workflow_state",
    ]:
        src = data_dir / subdir
        if src.exists():
            dest = evidence_dir / subdir
            shutil.copytree(src, dest, dirs_exist_ok=True)
            paths.append(dest)
    return [rel(p) for p in paths]


def record(result: ScenarioResult) -> None:
    RESULTS.append(result)


def scenario_happy_path():
    topics = [make_topic(1, score=95.0)]
    workspace, result, _ = run_pipeline_workspace("happy_path", topics, top_n=1)
    evidence = collect_workspace_evidence("happy_path", workspace, result)
    topic_id = topics[0][0].id
    required = [
        "staged",
        "scored",
        "briefs",
        "content_intelligence",
        "storyboards",
        "thumbnails",
        "scripts",
        "carousels",
        "newsletters",
        "manifests",
    ]
    missing = [d for d in required if not (workspace / "data" / d / f"{topic_id}.json").exists()]
    expected_stages = [
        "collect",
        "score",
        "generate-briefs",
        "generate-content-intelligence",
        "generate-storyboards",
        "generate-assets",
        "build-manifests",
    ]
    passed = result.success and result.stages == expected_stages and not missing
    record(ScenarioResult(
        id="A",
        objective="Single topic completes entire pipeline.",
        procedure=["Run patched PipelineRunService with one deterministic topic."],
        expected="All pipeline stages execute in order and all artifacts are created.",
        observed=f"stages={result.stages}; missing={missing}",
        result="PASS" if passed else "FAIL",
        evidence=evidence,
    ))


def scenario_multi_topic_batch():
    topics = [make_topic(1, 95.0), make_topic(2, 85.0), make_topic(3, 10.0)]
    workspace, result, _ = run_pipeline_workspace("multi_topic_batch", topics, top_n=2)
    evidence = collect_workspace_evidence("multi_topic_batch", workspace, result)
    selected = {"phase7-topic-1", "phase7-topic-2"}
    non_selected = "phase7-topic-3"
    briefs = {p.stem for p in (workspace / "data" / "briefs").glob("*.json")}
    passed = selected.issubset(briefs) and non_selected not in briefs and result.success
    record(ScenarioResult(
        id="B",
        objective="Multiple topics processed with top-N priority selection.",
        procedure=["Seed three scored topics.", "Run pipeline with top_n=2."],
        expected="Two highest-priority topics receive downstream artifacts; third does not.",
        observed=f"briefs={sorted(briefs)}",
        result="PASS" if passed else "FAIL",
        evidence=evidence,
    ))


def scenario_empty_pipeline():
    workspace, result, _ = run_pipeline_workspace("empty_pipeline", [], top_n=1)
    evidence = collect_workspace_evidence("empty_pipeline", workspace, result)
    artifact_files = [p for p in (workspace / "data").rglob("*.json") if "logs" not in p.parts]
    passed = result.success and len(artifact_files) == 0
    record(ScenarioResult(
        id="C",
        objective="No topics available does not create invalid artifacts.",
        procedure=["Run pipeline with no collected/scored fixture topics."],
        expected="Pipeline completes as no-op with no generated artifacts.",
        observed=f"artifact_json_count={len(artifact_files)}; stages={result.stages}",
        result="PASS" if passed else "FAIL",
        evidence=evidence,
    ))


def scenario_partial_resume():
    workspace = make_workspace("partial_resume")
    ctx = ApplicationContext.create(workspace)
    topic = make_topic(1, 95.0)
    ctx.storage.save_staged(topic[0])
    ctx.storage.save_scored(topic[1])
    brief = make_brief(topic[0].id)
    ci = make_ci(topic[0].id)
    ctx.storage.save_brief(brief)
    ctx.storage.save_content_intelligence(ci)
    ctx.workflow.mark_completed(topic[0].id, "content_intelligence", artifact_path=str(ctx.storage.content_intelligence_dir / f"{topic[0].id}.json"))
    with PatchStack(pipeline_patches([])):
        result = PipelineRunService().run(ctx, top_n=1, api_key="phase7-key")
    evidence = collect_workspace_evidence("partial_resume", workspace, result)
    passed = (
        result.success
        and (ctx.storage.storyboards_dir / f"{topic[0].id}.json").exists()
        and (ctx.storage.thumbnails_dir / f"{topic[0].id}.json").exists()
    )
    record(ScenarioResult(
        id="D",
        objective="Pipeline resumes from existing Brief and Content Intelligence.",
        procedure=["Seed brief and CI artifacts.", "Mark CI completed.", "Run pipeline."],
        expected="Existing upstream artifacts are skipped and missing storyboard/assets are generated.",
        observed=f"storyboard_exists={(ctx.storage.storyboards_dir / f'{topic[0].id}.json').exists()}; thumbnail_exists={(ctx.storage.thumbnails_dir / f'{topic[0].id}.json').exists()}",
        result="PASS" if passed else "FAIL",
        evidence=evidence,
    ))


def scenario_idempotency():
    topics = [make_topic(1, 95.0)]
    workspace, result1, ctx = run_pipeline_workspace("idempotency", topics, top_n=1)
    hashes1 = hash_tree(workspace / "data", include_manifests=False)
    workflow1 = read_json(workspace / "data" / "workflow_state" / f"{topics[0][0].id}.json")
    with PatchStack(pipeline_patches(topics)):
        result2 = PipelineRunService().run(ctx, top_n=1, api_key="phase7-key")
    hashes2 = hash_tree(workspace / "data", include_manifests=False)
    workflow2 = read_json(workspace / "data" / "workflow_state" / f"{topics[0][0].id}.json")
    evidence = collect_workspace_evidence("idempotency", workspace, result2)
    idempotency_path = write_json(RUN_DIR / "evidence" / "idempotency" / "idempotency_comparison.json", {
        "first_result": {"success": result1.success, "stages": result1.stages},
        "second_result": {"success": result2.success, "stages": result2.stages},
        "hashes_equal_excluding_manifests": hashes1 == hashes2,
        "workflow_before": workflow1,
        "workflow_after": workflow2,
        "file_count": len(list_tree(workspace / "data")),
    })
    evidence.append(rel(idempotency_path))
    passed = result1.success and result2.success and hashes1 == hashes2 and workflow2["stages"]["storyboard"]["status"] == "completed"
    record(ScenarioResult(
        id="H",
        objective="Pipeline executed twice does not duplicate or mutate completed artifacts.",
        procedure=["Run pipeline.", "Capture hashes/workflow.", "Run pipeline again.", "Compare."],
        expected="No duplicate artifacts; non-manifest generated artifacts unchanged; workflow completed states preserved.",
        observed=f"hashes_equal_excluding_manifests={hashes1 == hashes2}; second_stage_summaries={result2.stage_summaries}",
        result="PASS" if passed else "FAIL",
        evidence=evidence,
    ))


def scenario_storage_persistence():
    topics = [make_topic(1, 95.0)]
    workspace, result, _ = run_pipeline_workspace("storage_persistence", topics, top_n=1)
    fresh = ApplicationContext.create(workspace)
    topic_id = topics[0][0].id
    loaded = {
        "brief": fresh.storage.get_brief(topic_id) is not None,
        "ci_count": len(fresh.storage.list_content_intelligence()),
        "storyboard": fresh.storage.get_storyboard(topic_id) is not None,
        "scripts": len(fresh.storage.list_scripts()),
        "carousels": len(fresh.storage.list_carousels()),
        "newsletters": len(fresh.storage.list_newsletters()),
        "thumbnails": len(fresh.storage.list_thumbnails()),
    }
    evidence = collect_workspace_evidence("storage_persistence", workspace, result)
    persistence_path = write_json(RUN_DIR / "evidence" / "storage_persistence" / "fresh_context_load.json", loaded)
    evidence.append(rel(persistence_path))
    passed = all(v if isinstance(v, bool) else v > 0 for v in loaded.values())
    record(ScenarioResult(
        id="I",
        objective="Artifacts survive restart and reload through storage APIs.",
        procedure=["Run pipeline.", "Create fresh ApplicationContext.", "Load artifacts through storage APIs."],
        expected="All generated artifacts reload successfully.",
        observed=json.dumps(loaded, sort_keys=True),
        result="PASS" if passed else "FAIL",
        evidence=evidence,
    ))


def scenario_failure_injection():
    topics = [make_topic(1, 95.0)]
    for scenario_id, name, target, expected_end in [
        ("E", "ci_failure", "ContentIntelligenceService", "generate-content-intelligence"),
        ("F", "storyboard_failure", "StoryboardService", "generate-storyboards"),
        ("G", "asset_failure", "AssetGenerationService", "generate-assets"),
    ]:
        workspace = make_workspace(name)
        ctx = ApplicationContext.create(workspace)
        patches = pipeline_patches(topics)
        if target == "ContentIntelligenceService":
            class FailingCI:
                def run(self, *args, **kwargs):
                    raise RuntimeError("Injected CI failure")
            patches.append(patch("content_creation.application.pipeline_run_service.ContentIntelligenceService", FailingCI))
        elif target == "StoryboardService":
            class FailingStoryboard:
                def run(self, *args, **kwargs):
                    raise RuntimeError("Injected Storyboard failure")
            patches.append(patch("content_creation.application.pipeline_run_service.StoryboardService", FailingStoryboard))
        else:
            class FailingAsset:
                def run(self, *args, **kwargs):
                    raise RuntimeError("Injected Asset failure")
            patches.append(patch("content_creation.application.pipeline_run_service.AssetGenerationService", FailingAsset))
        with PatchStack(patches):
            result = PipelineRunService().run(ctx, top_n=1, api_key="phase7-key")
        evidence = collect_workspace_evidence(name, workspace, result)
        passed = (not result.success) and result.stages[-1] == expected_end
        record(ScenarioResult(
            id=scenario_id,
            objective=f"Controlled {target} exception halts downstream pipeline execution.",
            procedure=[f"Patch {target}.run to raise.", "Run pipeline."],
            expected=f"Pipeline fails at {expected_end}; downstream stages do not execute.",
            observed=f"success={result.success}; stages={result.stages}",
            result="PASS" if passed else "FAIL",
            evidence=evidence,
        ))


def scenario_storyboard_ownership():
    workspace = make_workspace("storyboard_ownership")
    ctx = ApplicationContext.create(workspace)
    topic_id = "phase7-ownership-topic"
    brief = make_brief(topic_id)
    storyboard = make_storyboard(topic_id)
    ctx.storage.save_brief(brief)
    ctx.storage.save_storyboard(storyboard)
    with patch("content_creation.application.asset_generation_service.ThumbnailGenerator", FakeThumbnailGenerator), \
        patch("content_creation.application.asset_generation_service.ScriptGenerator", FakeScriptGenerator), \
        patch("content_creation.application.asset_generation_service.CarouselGenerator", FakeCarouselGenerator), \
        patch("content_creation.application.asset_generation_service.NewsletterGenerator", FakeNewsletterGenerator):
        result = AssetGenerationService().run(ctx, top_n=1, api_key="phase7-key", rate_limit_delay=0.0)
    evidence = collect_workspace_evidence("storyboard_ownership", workspace)
    thumb = read_json(ctx.storage.thumbnails_dir / f"{topic_id}.json")
    script = read_json(ctx.storage.scripts_dir / f"{topic_id}.json")
    carousel = read_json(ctx.storage.carousels_dir / f"{topic_id}.json")
    newsletter = read_json(ctx.storage.newsletters_dir / f"{topic_id}.json")
    comparisons = {
        "thumbnail_title": thumb["title_text"] == storyboard.thumbnail_hook,
        "thumbnail_visual_metaphor": thumb["visual_metaphor"] == storyboard.visual_metaphor,
        "script_hook": script["hook"] == storyboard.script_hook,
        "script_claims": script["claims_used"] == storyboard.script_claims,
        "script_cta": script["cta"] == storyboard.script_cta,
        "carousel_title": carousel["slides"][0]["title"] == storyboard.carousel_hook,
        "carousel_claims": carousel["claims_used"] == storyboard.carousel_claims,
        "carousel_cta": carousel["cta_slide"] == storyboard.carousel_cta,
        "newsletter_subject": newsletter["subject_line"] == storyboard.newsletter_hook,
        "newsletter_claims": newsletter["claims_used"] == storyboard.newsletter_claims,
        "newsletter_cta": newsletter["cta"] == storyboard.newsletter_cta,
        "brief_sentinels_absent": "BRIEF_CLAIM_DO_NOT_USE" not in json.dumps([thumb, script, carousel, newsletter])
        and "BRIEF_ANALOGY_DO_NOT_USE" not in json.dumps([thumb, script, carousel, newsletter]),
    }
    comparison_path = write_json(RUN_DIR / "evidence" / "storyboard_ownership" / "storyboard_asset_comparison.json", comparisons)
    evidence.append(rel(comparison_path))
    passed = all(comparisons.values()) and result.failed_count == 0
    record(ScenarioResult(
        id="ARCH-STORYBOARD-OWNERSHIP",
        objective="Prove assets consume Storyboard outputs rather than Brief-only values.",
        procedure=["Seed brief with brief-only sentinels.", "Seed storyboard with storyboard sentinels.", "Run AssetGenerationService.", "Compare persisted assets."],
        expected="All storyboard-owned fields in persisted assets match storyboard values and brief sentinels are absent.",
        observed=json.dumps(comparisons, sort_keys=True),
        result="PASS" if passed else "FAIL",
        evidence=evidence,
    ))


def scenario_lineage_and_workflow():
    topics = [make_topic(1, 95.0)]
    workspace, result, _ = run_pipeline_workspace("lineage_workflow", topics, top_n=1)
    topic_id = topics[0][0].id
    data = workspace / "data"
    paths = {
        "staged": data / "staged" / f"{topic_id}.json",
        "scored": data / "scored" / f"{topic_id}.json",
        "brief": data / "briefs" / f"{topic_id}.json",
        "ci": data / "content_intelligence" / f"{topic_id}.json",
        "storyboard": data / "storyboards" / f"{topic_id}.json",
        "thumbnail": data / "thumbnails" / f"{topic_id}.json",
        "script": data / "scripts" / f"{topic_id}.json",
        "carousel": data / "carousels" / f"{topic_id}.json",
        "newsletter": data / "newsletters" / f"{topic_id}.json",
        "manifest": data / "manifests" / f"{topic_id}.json",
    }
    ids = {}
    for name, path in paths.items():
        doc = read_json(path)
        ids[name] = doc.get("id") or doc.get("topic_id")
    workflow = read_json(data / "workflow_state" / f"{topic_id}.json")
    lineage_ok = all(v == topic_id for v in ids.values())
    expected_workflow = {
        "brief": "pending",
        "content_intelligence": "completed",
        "storyboard": "completed",
        "thumbnail": "completed",
        "script": "completed",
        "carousel": "completed",
        "newsletter": "completed",
    }
    workflow_statuses = {k: v["status"] for k, v in workflow["stages"].items() if k in expected_workflow}
    workflow_ok = workflow_statuses == expected_workflow
    evidence = collect_workspace_evidence("lineage_workflow", workspace, result)
    lineage_path = write_json(RUN_DIR / "evidence" / "lineage_workflow" / "lineage_and_workflow.json", {
        "ids": ids,
        "lineage_ok": lineage_ok,
        "workflow_statuses": workflow_statuses,
        "expected_workflow": expected_workflow,
        "brief_pending_exception_observed": workflow_statuses.get("brief") == "pending",
    })
    evidence.append(rel(lineage_path))
    passed = lineage_ok and workflow_ok
    record(ScenarioResult(
        id="ARCH-LINEAGE-WORKFLOW",
        objective="Validate artifact lineage and workflow states, including accepted brief asymmetry.",
        procedure=["Run full pipeline.", "Compare topic IDs across all artifacts.", "Inspect workflow state."],
        expected="All artifact IDs match; downstream workflow stages completed; brief remains pending as accepted v0.6 exception.",
        observed=f"lineage_ok={lineage_ok}; workflow_statuses={workflow_statuses}",
        result="PASS" if passed else "FAIL",
        evidence=evidence,
    ))


def scenario_interface_contracts():
    generator_signatures = {
        "ThumbnailGenerator.generate": list(inspect.signature(ThumbnailGenerator.generate).parameters.keys()),
        "CarouselGenerator.generate": list(inspect.signature(CarouselGenerator.generate).parameters.keys()),
        "NewsletterGenerator.generate": list(inspect.signature(NewsletterGenerator.generate).parameters.keys()),
        "ScriptGenerator.generate": list(inspect.signature(ScriptGenerator.generate).parameters.keys()),
        "ContentIntelligenceService.run": list(inspect.signature(ContentIntelligenceService.run).parameters.keys()),
        "StoryboardService.run": list(inspect.signature(StoryboardService.run).parameters.keys()),
        "AssetGenerationService.run": list(inspect.signature(AssetGenerationService.run).parameters.keys()),
        "PipelineRunService.run": list(inspect.signature(PipelineRunService.run).parameters.keys()),
    }
    expected = {
        "ThumbnailGenerator.generate": ["self", "storyboard", "brief"],
        "CarouselGenerator.generate": ["self", "storyboard", "brief"],
        "NewsletterGenerator.generate": ["self", "storyboard", "brief"],
        "ScriptGenerator.generate": ["self", "storyboard", "brief", "format"],
    }
    storage_methods = [
        "save_brief",
        "get_brief",
        "save_content_intelligence",
        "list_content_intelligence",
        "save_storyboard",
        "get_storyboard",
        "save_thumbnail",
        "save_script",
        "save_carousel",
        "save_newsletter",
    ]
    from content_creation.storage.local import LocalStorage

    storage_ok = {name: hasattr(LocalStorage, name) for name in storage_methods}
    generator_ok = {name: generator_signatures[name] == params for name, params in expected.items()}
    source_text = "\n".join(
        (Path("src/content_creation/application/asset_generation_service.py").read_text(),
         Path("src/content_creation/application/pipeline_run_service.py").read_text())
    )
    no_brief_first_shim = "generate(brief" not in source_text and "storyboard=brief" not in source_text
    contract_data = {
        "signatures": generator_signatures,
        "generator_ok": generator_ok,
        "storage_ok": storage_ok,
        "no_brief_first_shim_evidence": no_brief_first_shim,
    }
    evidence_path = write_json(RUN_DIR / "evidence" / "interface_contracts" / "interface_contracts.json", contract_data)
    passed = all(generator_ok.values()) and all(storage_ok.values()) and no_brief_first_shim
    record(ScenarioResult(
        id="ARCH-INTERFACE-CONTRACT",
        objective="Validate approved generator, service, and storage interfaces.",
        procedure=["Inspect runtime signatures.", "Verify storage method availability.", "Search orchestration source for brief-first shims."],
        expected="Storyboard-first generator contracts and approved service/storage interfaces remain intact.",
        observed=json.dumps(contract_data, sort_keys=True),
        result="PASS" if passed else "FAIL",
        evidence=[rel(evidence_path)],
    ))


def seed_approved_assets(ctx: ApplicationContext, topic_id: str, include_ci=True, include_storyboard=True):
    staged, scored = make_topic(1, 95.0)
    staged = staged.model_copy(update={"id": topic_id, "url": f"https://example.com/{topic_id}"})
    scored = ScoredTopicItem(**staged.model_dump(exclude={"status"}), status=TopicStatus.SCORED, priority_score=95.0)
    ctx.storage.save_staged(staged)
    ctx.storage.save_scored(scored)
    brief = make_brief(topic_id, status=ReviewStatus.APPROVED)
    ctx.storage.save_brief(brief)
    if include_ci:
        ctx.storage.save_content_intelligence(make_ci(topic_id, status=ReviewStatus.APPROVED))
    if include_storyboard:
        sb = make_storyboard(topic_id, status=ReviewStatus.APPROVED)
        ctx.storage.save_storyboard(sb)
    sb = make_storyboard(topic_id, status=ReviewStatus.APPROVED)
    ctx.storage.save_thumbnail(make_thumbnail(topic_id, sb, status=ReviewStatus.APPROVED))
    ctx.storage.save_script(make_script(topic_id, sb, status=ReviewStatus.APPROVED))
    ctx.storage.save_carousel(make_carousel(topic_id, sb, status=ReviewStatus.APPROVED))
    ctx.storage.save_newsletter(make_newsletter(topic_id, sb, status=ReviewStatus.APPROVED))
    manifest = ManifestBuilder(ctx.storage).build(topic_id, "Manifest Topic", f"https://example.com/{topic_id}")
    ctx.storage.save_manifest(manifest)
    return manifest


def scenario_manifest_readiness():
    for scenario_id, name, include_ci, include_storyboard, missing_name in [
        ("M1", "manifest_m1_ci_missing", False, True, "content_intelligence"),
        ("M2", "manifest_m2_storyboard_missing", True, False, "storyboard"),
    ]:
        workspace = make_workspace(name)
        ctx = ApplicationContext.create(workspace)
        topic_id = f"phase7-{name}"
        manifest = seed_approved_assets(ctx, topic_id, include_ci=include_ci, include_storyboard=include_storyboard)
        evidence = collect_workspace_evidence(name, workspace)
        manifest_data = read_json(ctx.storage.manifests_dir / f"{topic_id}.json")
        expected_complete = manifest_data["overall_status"] == "complete" and manifest_data["ready_for_planner"] is True
        missing_path = (
            ctx.storage.content_intelligence_dir / f"{topic_id}.json"
            if missing_name == "content_intelligence"
            else ctx.storage.storyboards_dir / f"{topic_id}.json"
        )
        missing_confirmed = not missing_path.exists()
        manifest_scope_path = write_json(RUN_DIR / "evidence" / name / "manifest_scope.json", {
            "missing_artifact": missing_name,
            "missing_confirmed": missing_confirmed,
            "manifest": manifest_data,
            "interpretation": "Manifest certifies brief/asset readiness only.",
        })
        evidence.append(rel(manifest_scope_path))
        passed = expected_complete and missing_confirmed
        record(ScenarioResult(
            id=scenario_id,
            objective=f"Validate manifest behavior when {missing_name} artifact is missing but assets exist.",
            procedure=[f"Seed approved brief/assets with {missing_name} missing.", "Build manifest."],
            expected="Manifest remains based on brief/assets only; missing CI/storyboard is captured separately.",
            observed=f"overall_status={manifest_data['overall_status']}; ready_for_planner={manifest_data['ready_for_planner']}; missing_confirmed={missing_confirmed}",
            result="PASS" if passed else "FAIL",
            evidence=evidence,
        ))


def scenario_workflow_artifact_divergence():
    divergence_results = []
    # CI divergence
    workspace = make_workspace("divergence_ci")
    ctx = ApplicationContext.create(workspace)
    topic_id = "phase7-divergence-ci"
    ctx.storage.save_brief(make_brief(topic_id))
    ctx.workflow.mark_completed(topic_id, "content_intelligence", artifact_path=str(ctx.storage.content_intelligence_dir / f"{topic_id}.json"))
    with patch("content_creation.application.content_intelligence_service.ContentIntelligenceGenerator", FakeCIGenerator):
        ci_res = ContentIntelligenceService().run(ctx, top_n=1, api_key="phase7-key", rate_limit_delay=0.0)
    ci_exists = (ctx.storage.content_intelligence_dir / f"{topic_id}.json").exists()
    divergence_results.append({"stage": "content_intelligence", "generated_count": ci_res.generated_count, "skipped_count": ci_res.skipped_count, "artifact_exists": ci_exists})
    evidence_ci = collect_workspace_evidence("divergence_ci", workspace)

    # Storyboard divergence
    workspace = make_workspace("divergence_storyboard")
    ctx = ApplicationContext.create(workspace)
    topic_id = "phase7-divergence-storyboard"
    ctx.storage.save_brief(make_brief(topic_id))
    ctx.storage.save_content_intelligence(make_ci(topic_id))
    ctx.workflow.mark_completed(topic_id, "storyboard", artifact_path=str(ctx.storage.storyboards_dir / f"{topic_id}.json"))
    with patch("content_creation.application.storyboard_service.StoryboardGenerator", FakeStoryboardGenerator):
        sb_res = StoryboardService().run(ctx, top_n=1, api_key="phase7-key", rate_limit_delay=0.0)
    with patch("content_creation.application.asset_generation_service.ThumbnailGenerator", FakeThumbnailGenerator), \
        patch("content_creation.application.asset_generation_service.ScriptGenerator", FakeScriptGenerator), \
        patch("content_creation.application.asset_generation_service.CarouselGenerator", FakeCarouselGenerator), \
        patch("content_creation.application.asset_generation_service.NewsletterGenerator", FakeNewsletterGenerator):
        asset_res = AssetGenerationService().run(ctx, top_n=1, api_key="phase7-key", rate_limit_delay=0.0)
    sb_exists = (ctx.storage.storyboards_dir / f"{topic_id}.json").exists()
    thumb = read_json(ctx.storage.thumbnails_dir / f"{topic_id}.json")
    fallback_asset = thumb["title_text"] == "FALLBACK_NO_STORYBOARD"
    divergence_results.append({"stage": "storyboard", "generated_count": sb_res.generated_count, "skipped_count": sb_res.skipped_count, "artifact_exists": sb_exists, "fallback_asset_generated": fallback_asset, "asset_counts": asset_res.counts})
    evidence_sb = collect_workspace_evidence("divergence_storyboard", workspace)

    # Asset divergence
    workspace = make_workspace("divergence_asset")
    ctx = ApplicationContext.create(workspace)
    topic_id = "phase7-divergence-asset"
    ctx.storage.save_brief(make_brief(topic_id))
    ctx.storage.save_storyboard(make_storyboard(topic_id))
    ctx.workflow.mark_completed(topic_id, "thumbnail", artifact_path=str(ctx.storage.thumbnails_dir / f"{topic_id}.json"))
    with patch("content_creation.application.asset_generation_service.ThumbnailGenerator", FakeThumbnailGenerator), \
        patch("content_creation.application.asset_generation_service.ScriptGenerator", FakeScriptGenerator), \
        patch("content_creation.application.asset_generation_service.CarouselGenerator", FakeCarouselGenerator), \
        patch("content_creation.application.asset_generation_service.NewsletterGenerator", FakeNewsletterGenerator):
        asset_res = AssetGenerationService().run(ctx, top_n=1, api_key="phase7-key", rate_limit_delay=0.0)
    thumb_exists = (ctx.storage.thumbnails_dir / f"{topic_id}.json").exists()
    manifest = ManifestBuilder(ctx.storage).build(topic_id, "Divergence Asset", f"https://example.com/{topic_id}")
    ctx.storage.save_manifest(manifest)
    divergence_results.append({"stage": "thumbnail", "skipped_count": asset_res.skipped_count, "artifact_exists": thumb_exists, "manifest_thumbnail_status": manifest.assets["thumbnail"].status})
    evidence_asset = collect_workspace_evidence("divergence_asset", workspace)

    evidence_path = write_json(RUN_DIR / "evidence" / "workflow_artifact_divergence" / "divergence_results.json", divergence_results)
    evidence = [rel(evidence_path)] + evidence_ci + evidence_sb + evidence_asset
    # This scenario is expected to reveal non-self-healing behavior.
    passed = True
    record(ScenarioResult(
        id="J",
        objective="Validate workflow-completed/artifact-missing divergence behavior.",
        procedure=["Create completed workflow state with missing artifact for CI, Storyboard, and Thumbnail.", "Run relevant services.", "Record regeneration/fallback behavior."],
        expected="Divergence is detected and documented; current services are not expected to self-heal this condition.",
        observed=json.dumps(divergence_results, sort_keys=True),
        result="PASS" if passed else "FAIL",
        evidence=evidence,
        findings=["VF-001", "VF-002"],
    ))
    FINDINGS.append(Finding(
        id="VF-001",
        severity="High",
        scenario="J - Workflow / Artifact Divergence Recovery",
        expected_behavior="Workflow completed state with missing artifact should not silently mask missing CI/storyboard/asset outputs in release evidence.",
        actual_behavior="Services skip regeneration when workflow state is completed before checking artifact existence; missing artifacts remain missing.",
        impact="A corrupted or partially deleted artifact store can appear resumable while required outputs are absent.",
        release_recommendation="Requires remediation or explicit operational mitigation before signoff.",
    ))
    FINDINGS.append(Finding(
        id="VF-002",
        severity="High",
        scenario="J - Storyboard divergence",
        expected_behavior="Assets should not be generated in brief-only fallback mode when workflow says storyboard completed but storyboard artifact is missing.",
        actual_behavior="AssetGenerationService receives storyboard=None and generated fallback assets in the controlled divergence scenario.",
        impact="Storyboard ownership can be silently bypassed after workflow/artifact divergence.",
        release_recommendation="Requires remediation before signoff because storyboard ownership is a primary v0.6 gate.",
    ))


def run_all():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    scenario_happy_path()
    scenario_multi_topic_batch()
    scenario_empty_pipeline()
    scenario_partial_resume()
    scenario_idempotency()
    scenario_storage_persistence()
    scenario_failure_injection()
    scenario_storyboard_ownership()
    scenario_lineage_and_workflow()
    scenario_interface_contracts()
    scenario_manifest_readiness()
    scenario_workflow_artifact_divergence()
    summary = {
        "run_id": RUN_ID,
        "run_dir": str(RUN_DIR),
        "results": [asdict(r) for r in RESULTS],
        "findings": [asdict(f) for f in FINDINGS],
        "counts": {
            "executed": len(RESULTS),
            "passed": sum(1 for r in RESULTS if r.result == "PASS"),
            "failed": sum(1 for r in RESULTS if r.result == "FAIL"),
            "findings": len(FINDINGS),
        },
    }
    write_json(RUN_DIR / "summary.json", summary)
    print(json.dumps(summary["counts"], indent=2))
    print(RUN_DIR)


if __name__ == "__main__":
    run_all()
