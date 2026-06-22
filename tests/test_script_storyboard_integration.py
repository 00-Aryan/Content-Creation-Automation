"""Tests for Storyboard → Script integration."""

import json
from unittest.mock import MagicMock, patch

import pytest

from content_creation.domains.storyboard.model import Storyboard
from content_creation.generation.script import ScriptGenerator
from content_creation.models.brief import Brief
from content_creation.models.script import Script
from content_creation.prompts import PromptRegistry
from content_creation.shared.enums import ReviewStatus


@pytest.fixture
def brief():
    return Brief(
        topic_id="script_int_test",
        why_it_matters="Transformers replaced RNNs",
        plain_english_summary=[
            "Brief summary point 1",
            "Brief summary point 2",
            "Brief summary point 3",
        ],
        student_takeaway="Learn attention",
        analogy="A librarian scanning books",
        limitation="Quadratic memory",
        audience_fit="ML students",
        recommended_formats=["short_video"],
        source_url="https://example.com/script",
        review_status=ReviewStatus.DRAFT,
        generated_at="2026-06-02T00:00:00+00:00",
    )


@pytest.fixture
def storyboard():
    return Storyboard(
        topic_id="script_int_test",
        generated_at="2026-06-02T00:00:00+00:00",
        formats_planned=["short_video", "carousel", "newsletter"],
        script_hook="What if you could read all pages at once?",
        carousel_hook="carousel-h",
        newsletter_hook="news-h",
        thumbnail_hook="thumb-h",
        script_cta="Try writing attention mechanisms in PyTorch",
        carousel_cta="carousel-c",
        newsletter_cta="news-c",
        script_claims=["Script claim 1", "Script claim 2"],
        carousel_claims=["Carousel claim 1"],
        newsletter_claims=["Newsletter claim 1"],
        visual_style="diagram_overlay",
        visual_metaphor="Parallel scanner compared to a sequential reader",
    )


@pytest.fixture
def script_registry(tmp_path):
    (tmp_path / "prompts").mkdir(exist_ok=True)
    (tmp_path / "prompts" / "short_video.md").write_text(
        "Test script prompt {{ brief.topic_id }}"
    )
    return PromptRegistry(tmp_path)


@pytest.fixture
def valid_script_response():
    return json.dumps(
        {
            "hook": "LLM Generated Hook",
            "script_sections": [
                "LLM section 1",
                "LLM section 2",
            ],
            "shorts_segments": [
                {
                    "section": "hook",
                    "time_range": "0:00-0:03",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "LLM Generated Hook",
                },
                {
                    "section": "explanation",
                    "time_range": "0:03-0:10",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "LLM section 1",
                },
                {
                    "section": "explanation",
                    "time_range": "0:10-0:15",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "LLM section 2",
                },
                {
                    "section": "cta",
                    "time_range": "0:15-0:20",
                    "visual": "visual",
                    "audio": "audio",
                    "spoken": "LLM Generated CTA",
                },
            ],
            "cta": "LLM Generated CTA",
            "claims_used": ["LLM Generated Claims"],
            "review_status": "draft",
        }
    )


def _make_result(text, success=True):
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


class TestScriptLegacyMode:
    """Verify legacy behavior is unchanged when storyboard=None."""

    def test_legacy_mode_no_storyboard(
        self, brief, valid_script_response, script_registry
    ):
        with patch("content_creation.generation.script.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_script_response)

            gen = ScriptGenerator(api_key="test", prompt_dir=script_registry)
            script = gen.generate(None, brief, format="short_video")

        assert script.hook == "LLM Generated Hook"
        assert script.cta == "LLM Generated CTA"
        assert script.claims_used == ["LLM Generated Claims"]
        assert script.source_links == [brief.source_url]

    def test_legacy_fallback_no_storyboard(self, brief, script_registry):
        with patch("content_creation.generation.script.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result("", success=False)

            gen = ScriptGenerator(api_key="test", prompt_dir=script_registry)
            script = gen.generate(None, brief, format="short_video")

        assert script.hook == "needs_review"
        assert script.cta == "needs_review"
        assert script.claims_used == ["needs_review"]


class TestScriptStoryboardMode:
    """Verify Storyboard values override LLM-generated fields dynamically based on format."""

    def test_storyboard_overrides_fields_short_video(
        self, brief, storyboard, valid_script_response, script_registry
    ):
        with patch("content_creation.generation.script.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_script_response)

            gen = ScriptGenerator(api_key="test", prompt_dir=script_registry)
            script = gen.generate(storyboard, brief, format="short_video")

        # Overridden fields come from short_video planning fields in storyboard
        assert script.hook == "What if you could read all pages at once?"
        assert script.cta == "Try writing attention mechanisms in PyTorch"
        assert script.claims_used == ["Script claim 1", "Script claim 2"]

    def test_storyboard_fallback_uses_storyboard_values(
        self, brief, storyboard, script_registry
    ):
        with patch("content_creation.generation.script.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result("", success=False)

            gen = ScriptGenerator(api_key="test", prompt_dir=script_registry)
            script = gen.generate(storyboard, brief, format="short_video")

        # Fallback fields are populated from storyboard
        assert script.hook == "What if you could read all pages at once?"
        assert script.cta == "Try writing attention mechanisms in PyTorch"
        assert script.claims_used == ["Script claim 1", "Script claim 2"]
        assert script.script_sections == [
            "needs_review",
            "needs_review",
            "needs_review",
            "needs_review",
        ]
        assert script.review_status == ReviewStatus.NEEDS_REVIEW


class TestScriptMigration:
    """Verify Phase 5D prompt mapping and input behavior."""

    def test_prompt_field_mapping(
        self, brief, storyboard, valid_script_response, tmp_path
    ):
        """Verify that brief.analogy is replaced with storyboard.visual_metaphor and summary bullets are from storyboard claims."""
        prompt_dir = tmp_path / "custom_prompts"
        prompt_dir.mkdir(exist_ok=True)
        (prompt_dir / "short_video.md").write_text(
            "Metaphor: {{ brief.analogy }}\nClaims:\n{{ brief.plain_english_summary }}"
        )

        with patch("content_creation.generation.script.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(valid_script_response)

            gen = ScriptGenerator(api_key="test", prompt_dir=prompt_dir)
            gen.generate(storyboard, brief, format="short_video")

            called_prompt = mock_mgr.generate.call_args[1]["prompt"]
            assert (
                "Metaphor: Parallel scanner compared to a sequential reader"
                in called_prompt
            )
            assert "- Script claim 1\n- Script claim 2" in called_prompt


class TestScriptMarkerCleanup:
    """Verify that (F), (K), and (C) markers are cleaned up deterministically from generated script text."""

    def test_marker_cleanup(self, brief, script_registry):
        response_with_markers = json.dumps(
            {
                "hook": "LLM Hook with (F) marker.",
                "shorts_segments": [
                    {
                        "section": "hook",
                        "time_range": "0:00-0:03",
                        "visual": "visual (F)",
                        "audio": "audio (K)",
                        "spoken": "LLM Hook with (F) marker.",
                    },
                    {
                        "section": "context",
                        "time_range": "0:03-0:08",
                        "visual": "visual (C)",
                        "audio": "audio (F)",
                        "spoken": "This matters. (F) Next point. (K)",
                    },
                    {
                        "section": "explanation",
                        "time_range": "0:08-0:15",
                        "visual": "visual",
                        "audio": "audio",
                        "spoken": "Punctuation check: (C) is done. (like this parenthetical)",
                    },
                    {
                        "section": "payoff",
                        "time_range": "0:15-0:22",
                        "visual": "visual",
                        "audio": "audio",
                        "spoken": "Multiple markers: (F) one, (K) two, (C) three.",
                    },
                    {
                        "section": "explanation",
                        "time_range": "0:22-0:28",
                        "visual": "visual",
                        "audio": "audio",
                        "spoken": "Newline check: (F)\nnext line (K)\nfinal line (C)",
                    },
                    {
                        "section": "cta",
                        "time_range": "0:28-0:33",
                        "visual": "visual",
                        "audio": "audio",
                        "spoken": "LLM CTA (C).",
                    },
                ],
                "cta": "LLM CTA (C).",
                "claims_used": ["Claim (F)"],
                "review_status": "draft",
            }
        )

        with patch("content_creation.generation.script.InferenceManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.generate.return_value = _make_result(response_with_markers)

            gen = ScriptGenerator(api_key="test", prompt_dir=script_registry)
            script = gen.generate(None, brief, format="short_video")

        assert script.script_sections[0] == "This matters. Next point."
        assert (
            script.script_sections[1]
            == "Punctuation check: is done. (like this parenthetical)"
        )
        assert script.script_sections[2] == "Multiple markers: one, two, three."
        assert script.script_sections[3] == "Newline check:\nnext line\nfinal line"
        assert script.hook == "LLM Hook with marker."
        assert script.cta == "LLM CTA."
