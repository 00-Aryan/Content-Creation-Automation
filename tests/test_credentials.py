import os
import pytest
from unittest.mock import patch, MagicMock
from content_creation.inference.credentials import resolve_credential
from content_creation.inference.manager import InferenceManager


def test_resolve_credential_from_env():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "env-gemini-key"}):
        assert resolve_credential("GEMINI_API_KEY") == "env-gemini-key"


def test_resolve_credential_from_streamlit_secrets():
    # Clear environment variable to test fallback
    with patch.dict(os.environ, {}):
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
            
        mock_st = MagicMock()
        mock_st.secrets = {"GEMINI_API_KEY": "streamlit-gemini-key"}
        
        with patch.dict("sys.modules", {"streamlit": mock_st}):
            assert resolve_credential("GEMINI_API_KEY") == "streamlit-gemini-key"


def test_resolve_credential_not_found():
    with patch.dict(os.environ, {}):
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        with patch.dict("sys.modules", {"streamlit": None}):
            assert resolve_credential("GEMINI_API_KEY") is None


def test_inference_manager_resolves_credentials():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "env-gemini-key"}, clear=True):
        # Should initialize without raising an error because key is in environment
        # We mock build_provider to avoid genai.Client initialization with mock key
        with patch.object(InferenceManager, "_build_provider") as mock_build:
            manager = InferenceManager()
            assert manager.is_available() is True
            mock_build.assert_called_once_with("gemini", "env-gemini-key", None)
