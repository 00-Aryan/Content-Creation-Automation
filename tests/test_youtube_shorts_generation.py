import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from content_creation.domains.storyboard.model import Storyboard
from content_creation.generation.script import ScriptGenerator
from content_creation.models.brief import Brief
from content_creation.models.script import Script, YouTubeShortsSegment
from content_creation.shared.enums import ReviewStatus


@pytest.fixture
def sample_brief():
    return Brief(
        topic_id="test_topic_123",
        why_it_matters="Transformers revolutionized NLP",
        plain_english_summary=[
            "Transformers use attention to process text",
            "They can handle long-range dependencies",
            "Pre-training + fine-tuning is the key paradigm",
        ],
        student_takeaway="Learn Transformers fundamentals",
        analogy="Think of attention as a spotlight",
        limitation="Requires lots of compute",
        audience_fit="Intermediate ML students",
        recommended_formats=["short_video"],
        source_url="https://arxiv.org/abs/1706.03762",
        review_status=ReviewStatus.DRAFT,
        generated_at="2026-05-14T10:00:00Z",
    )


@pytest.fixture
def prompt_dir(tmp_path):
    for name in ("short_video", "carousel", "newsletter"):
        (tmp_path / f"{name}.md").write_text("Test prompt {{ brief.topic_id }}")
    return tmp_path


def _make_inference_result(text, success=True):
    from content_creation.inference.providers.base import InferenceResult

    return InferenceResult(
        text=text,
        provider="gemini",
        model="gemini-2.5-flash",
        retries=0,
        duration_seconds=1.0,
        success=success,
        error=None if success else "error",
    )


def test_valid_structured_shorts_response(sample_brief, prompt_dir):
    valid_response = json.dumps(
        {
            "hook": "What if machines could read entire documents instantly?",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "Zoom in on attention equation.",
                    "audio": "[SFX: Loud record scratch]",
                    "spoken": "What if machines could read entire documents instantly?",
                },
                {
                    "section": "explanation",
                    "time_range": "0:03-0:15",
                    "visual": "Diagram.",
                    "audio": "Music drone.",
                    "spoken": "Attention lets each word look at every other word.",
                },
                {
                    "section": "cta",
                    "time_range": "0:15-0:20",
                    "visual": "Text overlay.",
                    "audio": "Music fades.",
                    "spoken": "Try the notebook in description.",
                },
            ],
            "cta": "Try the notebook in description.",
            "claims_used": ["why_it_matters: Transformers revolutionized NLP"],
            "review_status": "draft",
        }
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_response)

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")

    assert isinstance(script, Script)
    assert script.review_status == ReviewStatus.DRAFT


def test_segments_parsed_into_models(sample_brief, prompt_dir):
    valid_response = json.dumps(
        {
            "hook": "What if machines could read entire documents instantly?",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "Zoom in.",
                    "audio": "Loud record scratch",
                    "spoken": "What if machines could read entire documents instantly?",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "Text overlay.",
                    "audio": "Music fades.",
                    "spoken": "Try the notebook.",
                },
            ],
            "cta": "Try the notebook.",
            "claims_used": [],
            "review_status": "draft",
        }
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_response)

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")

    assert len(script.shorts_segments) == 2
    assert isinstance(script.shorts_segments[0], YouTubeShortsSegment)
    assert script.shorts_segments[0].section == "hook"
    assert script.shorts_segments[0].time_range == "0:00-0:03"
    assert script.shorts_segments[0].visual == "Zoom in."
    assert script.shorts_segments[0].audio == "Loud record scratch"
    assert (
        script.shorts_segments[0].spoken
        == "What if machines could read entire documents instantly?"
    )


def test_script_sections_derived_from_middle(sample_brief, prompt_dir):
    valid_response = json.dumps(
        {
            "hook": "Hook narration",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "Zoom in.",
                    "audio": "Audio.",
                    "spoken": "Hook narration",
                },
                {
                    "section": "context",
                    "time_range": "0:03-0:08",
                    "visual": "Visual context.",
                    "audio": "Audio context.",
                    "spoken": "Middle section 1",
                },
                {
                    "section": "explanation",
                    "time_range": "0:08-0:15",
                    "visual": "Visual expl.",
                    "audio": "Audio expl.",
                    "spoken": "Middle section 2",
                },
                {
                    "section": "cta",
                    "time_range": "0:15-0:20",
                    "visual": "Visual cta.",
                    "audio": "Audio cta.",
                    "spoken": "CTA narration",
                },
            ],
            "cta": "CTA narration",
            "claims_used": [],
            "review_status": "draft",
        }
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_response)

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")

    assert script.script_sections == ["Middle section 1", "Middle section 2"]


def test_source_url_preservation(sample_brief, prompt_dir):
    valid_response = json.dumps(
        {
            "hook": "Hook narration",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "Hook narration",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "CTA narration",
                },
            ],
            "cta": "CTA narration",
            "claims_used": [],
            "review_status": "draft",
        }
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_response)

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")

    assert script.source_links == [sample_brief.source_url]


def test_storyboard_hook_cta_synchronization(sample_brief, prompt_dir):
    valid_response = json.dumps(
        {
            "hook": "LLM Hook",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "LLM Hook",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "LLM CTA",
                },
            ],
            "cta": "LLM CTA",
            "claims_used": [],
            "review_status": "draft",
        }
    )

    sb = Storyboard(
        topic_id="test_topic_123",
        generated_at="2026-06-02T00:00:00+00:00",
        formats_planned=["short_video"],
        script_hook="Storyboard Hook Override",
        carousel_hook="",
        newsletter_hook="",
        thumbnail_hook="",
        script_cta="Storyboard CTA Override",
        carousel_cta="",
        newsletter_cta="",
        script_claims=["Storyboard claim 1"],
        carousel_claims=[],
        newsletter_claims=[],
        visual_style="diagram_overlay",
        visual_metaphor="metaphor",
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_response)

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(sb, sample_brief, format="short_video")

    assert script.hook == "Storyboard Hook Override"
    assert script.cta == "Storyboard CTA Override"
    assert script.claims_used == ["Storyboard claim 1"]
    assert script.shorts_segments[0].spoken == "Storyboard Hook Override"
    assert script.shorts_segments[-1].spoken == "Storyboard CTA Override"


def test_marker_cleanup_all_segment_fields(sample_brief, prompt_dir):
    valid_response = json.dumps(
        {
            "hook": "Hook with (F)",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "visual (K)",
                    "audio": "audio (C)",
                    "spoken": "Hook with (F)",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "CTA with (F)",
                },
            ],
            "cta": "CTA with (F)",
            "claims_used": [],
            "review_status": "draft",
        }
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_response)

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")

    assert script.shorts_segments[0].visual == "visual"
    assert script.shorts_segments[0].audio == "audio"
    assert script.shorts_segments[0].spoken == "Hook with"
    assert script.shorts_segments[-1].spoken == "CTA with"


def test_missing_segments_forces_needs_review(sample_brief, prompt_dir):
    response_without_segments = json.dumps(
        {"hook": "Hook", "cta": "CTA", "claims_used": [], "review_status": "draft"}
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(
            response_without_segments
        )

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")

    assert script.review_status == ReviewStatus.NEEDS_REVIEW


def test_malformed_segments_forces_fallback(sample_brief, prompt_dir):
    malformed_response = json.dumps(
        {
            "hook": "Hook",
            "shorts_segments": [
                {
                    "section": "hook",
                }
            ],
            "cta": "CTA",
            "claims_used": [],
            "review_status": "draft",
        }
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(malformed_response)

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")

    assert script.review_status == ReviewStatus.NEEDS_REVIEW
    assert script.hook == "needs_review"


def test_first_segment_must_be_hook(sample_brief, prompt_dir):
    response = json.dumps(
        {
            "hook": "Hook",
            "shorts_segments": [
                {
                    "section": "explanation",
                    "time_range": "0:00-0:03",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "Hook spoken",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "CTA spoken",
                },
            ],
            "cta": "CTA",
            "claims_used": [],
            "review_status": "draft",
        }
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(response)

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")

    assert script.review_status == ReviewStatus.NEEDS_REVIEW


def test_last_segment_must_be_cta(sample_brief, prompt_dir):
    response = json.dumps(
        {
            "hook": "Hook",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "Hook spoken",
                },
                {
                    "section": "explanation",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "CTA spoken",
                },
            ],
            "cta": "CTA",
            "claims_used": [],
            "review_status": "draft",
        }
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(response)

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")

    assert script.review_status == ReviewStatus.NEEDS_REVIEW


def test_non_short_video_remains_unchanged(sample_brief, prompt_dir):
    valid_carousel_response = json.dumps(
        {
            "hook": "What if machines could read?",
            "script_sections": ["sec1", "sec2"],
            "cta": "Try notebook",
            "claims_used": ["claim"],
            "review_status": "draft",
        }
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_carousel_response)

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="carousel")

    assert script.format == "carousel"
    assert script.shorts_segments == []
    assert script.script_sections == ["sec1", "sec2"]


def test_previously_persisted_script_without_segments_valid():
    payload = {
        "topic_id": "test_topic_123",
        "format": "short_video",
        "hook": "Some hook",
        "script_sections": ["sec1", "sec2"],
        "cta": "Some cta",
        "claims_used": ["claim"],
        "source_links": ["https://example.com"],
        "review_status": "draft",
        "generated_at": "2026-05-14T10:00:00Z",
    }

    script = Script(**payload)
    assert script.shorts_segments == []


@pytest.mark.parametrize(
    "field_to_blank", ["section", "time_range", "visual", "audio", "spoken"]
)
def test_direct_segment_construction_rejects_empty_whitespace(field_to_blank):
    init_args = {
        "section": "hook",
        "time_range": "0:00-0:03",
        "visual": "visual",
        "audio": "audio",
        "spoken": "spoken",
    }
    init_args[field_to_blank] = "   "
    with pytest.raises(ValidationError):
        YouTubeShortsSegment(**init_args)


def test_whitespace_only_time_range_in_response(sample_brief, prompt_dir):
    response = json.dumps(
        {
            "hook": "Hook",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "   ",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
            ],
            "cta": "CTA",
            "claims_used": [],
            "review_status": "draft",
        }
    )
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(response)
        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")
    assert script.review_status == ReviewStatus.NEEDS_REVIEW


def test_whitespace_only_visual_in_response(sample_brief, prompt_dir):
    response = json.dumps(
        {
            "hook": "Hook",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": " \t ",
                    "audio": "audio",
                    "spoken": "spoken",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
            ],
            "cta": "CTA",
            "claims_used": [],
            "review_status": "draft",
        }
    )
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(response)
        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")
    assert script.review_status == ReviewStatus.NEEDS_REVIEW


def test_whitespace_only_audio_in_response(sample_brief, prompt_dir):
    response = json.dumps(
        {
            "hook": "Hook",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "visual",
                    "audio": "  ",
                    "spoken": "spoken",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
            ],
            "cta": "CTA",
            "claims_used": [],
            "review_status": "draft",
        }
    )
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(response)
        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")
    assert script.review_status == ReviewStatus.NEEDS_REVIEW


def test_whitespace_only_spoken_in_response(sample_brief, prompt_dir):
    response = json.dumps(
        {
            "hook": "Hook",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "   ",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
            ],
            "cta": "CTA",
            "claims_used": [],
            "review_status": "draft",
        }
    )
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(response)
        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")
    assert script.review_status == ReviewStatus.NEEDS_REVIEW


def test_non_short_response_containing_stray_segments(sample_brief, prompt_dir):
    valid_carousel_response = json.dumps(
        {
            "hook": "What if machines could read?",
            "script_sections": ["sec1", "sec2"],
            "cta": "Try notebook",
            "claims_used": ["claim"],
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                }
            ],
            "review_status": "draft",
        }
    )

    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(valid_carousel_response)

        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="carousel")

    assert script.format == "carousel"
    assert script.shorts_segments == []


def test_model_provided_source_links_ignored(sample_brief, prompt_dir):
    response = json.dumps(
        {
            "hook": "Hook",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
            ],
            "cta": "CTA",
            "claims_used": [],
            "source_links": ["https://malicious.com/unrelated"],
            "review_status": "draft",
        }
    )
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(response)
        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")
    assert script.source_links == [sample_brief.source_url]


def test_prompt_content_requirements(sample_brief, prompt_dir):
    real_prompt_path = (
        Path(__file__).resolve().parents[1] / "prompts" / "short_video.md"
    )
    assert real_prompt_path.exists()
    prompt_content = real_prompt_path.read_text()

    assert "valid JSON" in prompt_content or "JSON" in prompt_content
    assert (
        "No invented claims" in prompt_content
        or "no invented claims" in prompt_content
        or "ONLY facts" in prompt_content
    )
    assert "50–58 seconds" in prompt_content or "50-58 seconds" in prompt_content
    assert "130–150" in prompt_content or "130-150" in prompt_content


def test_whitespace_only_section_in_response(sample_brief, prompt_dir):
    response = json.dumps(
        {
            "hook": "Hook",
            "shorts_segments": [
                {
                    "section": "   ",
                    "time_range": "0:00-0:03",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
            ],
            "cta": "CTA",
            "claims_used": [],
            "review_status": "draft",
        }
    )
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(response)
        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")
    assert script.review_status == ReviewStatus.NEEDS_REVIEW


@pytest.mark.parametrize(
    "field_name, non_string_val",
    [
        ("time_range", 123),
        ("spoken", None),
        ("section", 456),
        ("visual", {}),
        ("audio", []),
    ],
)
def test_non_string_fields_in_response(
    sample_brief, prompt_dir, field_name, non_string_val
):
    segment = {
        "section": "hook",
        "time_range": "0:00-0:03",
        "visual": "visual",
        "audio": "audio",
        "spoken": "spoken",
    }
    segment[field_name] = non_string_val
    response = json.dumps(
        {
            "hook": "Hook",
            "shorts_segments": [
                segment,
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
            ],
            "cta": "CTA",
            "claims_used": [],
            "review_status": "draft",
        }
    )
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(response)
        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")
    assert script.review_status == ReviewStatus.NEEDS_REVIEW


def test_provider_needs_review_preserved(sample_brief, prompt_dir):
    response = json.dumps(
        {
            "hook": "Hook",
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
                {
                    "section": "cta",
                    "time_range": "0:03-0:08",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "spoken",
                },
            ],
            "cta": "CTA",
            "claims_used": [],
            "review_status": "needs_review",
        }
    )
    with patch("content_creation.generation.script.InferenceManager") as mock_mgr_class:
        mock_mgr = MagicMock()
        mock_mgr_class.return_value = mock_mgr
        mock_mgr.generate.return_value = _make_inference_result(response)
        generator = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
        script = generator.generate(None, sample_brief, format="short_video")
    assert script.review_status == ReviewStatus.NEEDS_REVIEW
