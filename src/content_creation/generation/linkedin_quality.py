"""Deterministic LinkedIn post quality evaluator."""

import re
from typing import Any, List

from content_creation.models.linkedin_quality import (
    LinkedInQualityGateResult,
    LinkedInQualityScore,
)


class LinkedInQualityEvaluator:
    """Score LinkedIn posts against deterministic platform quality gates."""

    MAX_TOTAL_CHARS = 3000
    MAX_HOOK_CHARS = 180
    MAX_HOOK_LINES = 2
    MIN_HASHTAGS = 3
    MAX_HASHTAGS = 5

    BANNED_HYPE_WORDS = (
        "game-changing",
        "mind-blowing",
        "insane",
        "guaranteed",
        "secret hack",
        "ultimate guide",
        "you won't believe",
    )

    def evaluate(self, post: Any) -> LinkedInQualityScore:
        """Return deterministic quality score for a LinkedIn-like post object."""
        gate_results = [
            self._check_hashtags(post),
            self._check_cta(post),
            self._check_total_length(post),
            self._check_hook(post),
            self._check_source(post),
            self._check_banned_hype_language(post),
        ]

        issues = [gate.message for gate in gate_results if not gate.passed]
        warnings: List[str] = []
        overall_score = round(
            sum(gate.score for gate in gate_results) / len(gate_results)
        )

        return LinkedInQualityScore(
            overall_score=overall_score,
            passed=all(gate.passed for gate in gate_results),
            gate_results=gate_results,
            issues=issues,
            warnings=warnings,
        )

    def _check_hashtags(self, post: Any) -> LinkedInQualityGateResult:
        hashtags = getattr(post, "hashtags", [])
        passed = (
            isinstance(hashtags, list)
            and self.MIN_HASHTAGS <= len(hashtags) <= self.MAX_HASHTAGS
        )
        return self._gate(
            name="hashtags",
            passed=passed,
            pass_message="Hashtag count is within the LinkedIn contract.",
            fail_message="Hashtag count must be between 3 and 5.",
        )

    def _check_cta(self, post: Any) -> LinkedInQualityGateResult:
        cta = self._text(getattr(post, "cta", ""))
        prompt_count = cta.count("?")
        passed = bool(cta) and prompt_count == 1
        return self._gate(
            name="cta",
            passed=passed,
            pass_message="CTA contains exactly one question prompt.",
            fail_message="CTA must contain exactly one question prompt.",
        )

    def _check_total_length(self, post: Any) -> LinkedInQualityGateResult:
        combined = "\n".join(
            [
                self._text(getattr(post, "hook", "")),
                self._text(getattr(post, "post_body", "")),
                self._text(getattr(post, "takeaway", "")),
                self._text(getattr(post, "cta", "")),
            ]
        )
        passed = 0 < len(combined) <= self.MAX_TOTAL_CHARS
        return self._gate(
            name="length",
            passed=passed,
            pass_message="Post length is within the hard LinkedIn limit.",
            fail_message=f"Post length must be between 1 and {self.MAX_TOTAL_CHARS} characters.",
        )

    def _check_hook(self, post: Any) -> LinkedInQualityGateResult:
        hook = self._text(getattr(post, "hook", ""))
        hook_lines = [line for line in hook.splitlines() if line.strip()]
        passed = (
            bool(hook)
            and hook != "needs_review"
            and len(hook) <= self.MAX_HOOK_CHARS
            and len(hook_lines) <= self.MAX_HOOK_LINES
        )
        return self._gate(
            name="hook",
            passed=passed,
            pass_message="Hook is present and concise.",
            fail_message=(
                "Hook must be present, not needs_review, concise, "
                f"and no more than {self.MAX_HOOK_LINES} lines."
            ),
        )

    def _check_source(self, post: Any) -> LinkedInQualityGateResult:
        source_reference = self._text(getattr(post, "source_reference", ""))
        source_links = getattr(post, "source_links", [])
        passed = (
            bool(source_reference)
            and source_reference != "needs_review"
            and isinstance(source_links, list)
            and any(self._text(link) for link in source_links)
        )
        return self._gate(
            name="source",
            passed=passed,
            pass_message="Source reference and source link are present.",
            fail_message="Source reference and at least one source link are required.",
        )

    def _check_banned_hype_language(self, post: Any) -> LinkedInQualityGateResult:
        combined = " ".join(
            [
                self._text(getattr(post, "hook", "")),
                self._text(getattr(post, "post_body", "")),
                self._text(getattr(post, "takeaway", "")),
                self._text(getattr(post, "cta", "")),
            ]
        ).lower()

        banned_found = [
            word
            for word in self.BANNED_HYPE_WORDS
            if re.search(re.escape(word), combined)
        ]
        passed = not banned_found
        return self._gate(
            name="banned_hype_language",
            passed=passed,
            pass_message="No banned hype language detected.",
            fail_message=(
                "Post contains banned hype language: " + ", ".join(banned_found)
                if banned_found
                else "Post contains banned hype language."
            ),
        )

    def _gate(
        self,
        name: str,
        passed: bool,
        pass_message: str,
        fail_message: str,
    ) -> LinkedInQualityGateResult:
        return LinkedInQualityGateResult(
            name=name,
            passed=passed,
            score=100 if passed else 0,
            message=pass_message if passed else fail_message,
        )

    def _text(self, value: Any) -> str:
        return value.strip() if isinstance(value, str) else ""
