"""Tests for runtime configuration integration of fallback providers."""

import os
from unittest.mock import patch
import pytest

from content_creation.inference import InferenceManager
from content_creation.inference.providers.openrouter import OpenRouterProvider


def test_fallback_unconfigured_when_openrouter_key_absent():
    """Test that fallback remains None when OPENROUTER_API_KEY is absent."""
    with patch.dict(os.environ, {}):
        # Temporarily clear key if it is present
        if "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]
            
        manager = InferenceManager(api_key="test-gemini-key")
        assert manager._fallback is None


def test_fallback_configured_when_openrouter_key_present():
    """Test that OpenRouter fallback is configured automatically when OPENROUTER_API_KEY is set."""
    mock_openrouter_key = "sk-or-mock-key-1234"
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": mock_openrouter_key}):
        manager = InferenceManager(api_key="test-gemini-key")
        
        # Verify that the fallback provider was instantiated
        assert manager._fallback is not None
        assert isinstance(manager._fallback, OpenRouterProvider)
        assert manager._fallback.provider_name == "openrouter"
        assert manager._fallback._api_key == mock_openrouter_key


def test_explicit_fallback_takes_precedence_over_env_fallback():
    """Test that passing an explicit fallback overrides the default environment-driven fallback."""
    mock_openrouter_key = "sk-or-mock-key-1234"
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": mock_openrouter_key}):
        # Explicitly configure NO fallback via argument (passing fallback=None or empty shouldn't trigger env lookup)
        # Wait, if we pass fallback="gemini", it should set gemini as fallback
        manager = InferenceManager(
            api_key="test-gemini-key",
            fallback="gemini",
            fallback_api_key="custom-gemini-fallback-key"
        )
        assert manager._fallback is not None
        assert manager._fallback.provider_name == "gemini"
        assert manager._fallback._client is not None
