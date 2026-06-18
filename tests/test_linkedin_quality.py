from types import SimpleNamespace

from content_creation.generation.linkedin_quality import LinkedInQualityEvaluator
from content_creation.models.linkedin import LinkedInPost
from content_creation.models.linkedin_quality import LinkedInQualityScore
from content_creation.shared.enums import ReviewStatus


def _valid_post() -> LinkedInPost:
    return LinkedInPost(
        topic_id="topic_123",
        hook="What if attention is the missing mental model?",
        post_body=(
            "Transformers are easier to understand when attention is treated "
            "as a relevance filter over tokens."
        ),
        takeaway="Start with attention before jumping into full architectures.",
        cta="What part of Transformers confused you first?",
        hashtags=["#AI", "#MachineLearning", "#Transformers"],
        source_reference="Paper: Attention Is All You Need",
        source_links=["https://arxiv.org/abs/1706.03762"],
        claims_used=["Transformers use attention to process token relationships."],
        review_status=ReviewStatus.DRAFT,
        generated_at="2026-06-18T00:00:00Z",
    )


def _post_with(**overrides):
    data = _valid_post().model_dump()
    data.update(overrides)
    return SimpleNamespace(**data)


def test_linkedin_quality_evaluator_passes_valid_post():
    evaluator = LinkedInQualityEvaluator()

    result = evaluator.evaluate(_valid_post())

    assert isinstance(result, LinkedInQualityScore)
    assert result.passed is True
    assert result.overall_score == 100
    assert result.issues == []
    assert [gate.name for gate in result.gate_results] == [
        "hashtags",
        "cta",
        "length",
        "hook",
        "source",
        "banned_hype_language",
    ]


def test_linkedin_quality_evaluator_fails_invalid_hashtag_count():
    post = _post_with(hashtags=["#AI", "#ML"])
    evaluator = LinkedInQualityEvaluator()

    result = evaluator.evaluate(post)

    assert result.passed is False
    assert result.overall_score < 100
    assert "Hashtag count must be between 3 and 5." in result.issues


def test_linkedin_quality_evaluator_fails_cta_without_exactly_one_question():
    post = _post_with(cta="Share your thoughts. What confused you first? What helped?")
    evaluator = LinkedInQualityEvaluator()

    result = evaluator.evaluate(post)

    assert result.passed is False
    assert "CTA must contain exactly one question prompt." in result.issues


def test_linkedin_quality_evaluator_fails_overlong_post():
    post = _post_with(post_body="x" * (LinkedInQualityEvaluator.MAX_TOTAL_CHARS + 1))
    evaluator = LinkedInQualityEvaluator()

    result = evaluator.evaluate(post)

    assert result.passed is False
    assert any("Post length must be" in issue for issue in result.issues)


def test_linkedin_quality_evaluator_fails_missing_hook():
    post = _post_with(hook="needs_review")
    evaluator = LinkedInQualityEvaluator()

    result = evaluator.evaluate(post)

    assert result.passed is False
    assert any("Hook must be present" in issue for issue in result.issues)


def test_linkedin_quality_evaluator_fails_missing_source():
    post = _post_with(source_reference="", source_links=[])
    evaluator = LinkedInQualityEvaluator()

    result = evaluator.evaluate(post)

    assert result.passed is False
    assert (
        "Source reference and at least one source link are required." in result.issues
    )


def test_linkedin_quality_evaluator_fails_banned_hype_language():
    post = _post_with(
        post_body="This is a game-changing secret hack for learning Transformers."
    )
    evaluator = LinkedInQualityEvaluator()

    result = evaluator.evaluate(post)

    assert result.passed is False
    assert any("banned hype language" in issue for issue in result.issues)
