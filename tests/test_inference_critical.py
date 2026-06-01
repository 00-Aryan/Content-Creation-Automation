import pytest
from unittest.mock import MagicMock, patch, call
import time
from pathlib import Path
from content_creation.inference.retry import RetryManager, RetryPolicy
from content_creation.inference.manager import InferenceManager
from content_creation.inference.providers.base import InferenceResult
from content_creation.inference.models import ProviderError, ErrorCategory
from content_creation.inference.providers.gemini import GeminiProvider
from content_creation.inference.providers.openrouter import OpenRouterProvider

@pytest.fixture(autouse=True)
def clear_env_fallback():
    import os
    with patch.dict(os.environ):
        if "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]
        yield

# --- T-01 RetryManager.execute ---

@pytest.fixture
def mock_sleep():
    with patch("time.sleep") as mocked:
        yield mocked

def test_retry_manager_success_first_attempt(mock_sleep):
    """S1: First attempt succeeds."""
    policy = RetryPolicy(max_retries=3, base_delay=15.0)
    manager = RetryManager(policy)
    
    success_result = InferenceResult(
        text="success", provider="test", model="test", 
        retries=0, duration_seconds=0.0, success=True
    )
    fn = MagicMock(return_value=success_result)
    
    result = manager.execute(fn)
    
    assert result.success is True
    assert result.retries == 0
    assert result.duration_seconds >= 0.0
    assert fn.call_count == 1
    mock_sleep.assert_not_called()

def test_retry_manager_success_after_one_retry(mock_sleep):
    """S2: Fails once (retryable), succeeds on second attempt."""
    policy = RetryPolicy(max_retries=3, base_delay=15.0, backoff_factor=2.0)
    manager = RetryManager(policy)
    
    retryable_error = ProviderError(message="retry", retryable=True, category=ErrorCategory.RATE_LIMIT, status_code=429)
    fail_result = InferenceResult(
        text="", provider="test", model="test", 
        retries=0, duration_seconds=0.0, success=False, 
        provider_error=retryable_error
    )
    success_result = InferenceResult(
        text="success", provider="test", model="test", 
        retries=0, duration_seconds=0.0, success=True
    )
    
    fn = MagicMock(side_effect=[fail_result, success_result])
    
    result = manager.execute(fn)
    
    assert result.success is True
    assert result.retries == 1
    assert fn.call_count == 2
    mock_sleep.assert_called_once_with(15.0)

def test_retry_manager_success_after_two_retries(mock_sleep):
    """S3: Fails twice (retryable), succeeds on third attempt."""
    policy = RetryPolicy(max_retries=3, base_delay=15.0, backoff_factor=2.0)
    manager = RetryManager(policy)
    
    retryable_error = ProviderError(message="retry", retryable=True, category=ErrorCategory.RATE_LIMIT, status_code=429)
    fail_result_1 = InferenceResult(
        text="", provider="test", model="test", 
        retries=0, duration_seconds=0.0, success=False, 
        provider_error=retryable_error
    )
    fail_result_2 = InferenceResult(
        text="", provider="test", model="test", 
        retries=0, duration_seconds=0.0, success=False, 
        provider_error=retryable_error
    )
    success_result = InferenceResult(
        text="success", provider="test", model="test", 
        retries=0, duration_seconds=0.0, success=True
    )
    
    fn = MagicMock(side_effect=[fail_result_1, fail_result_2, success_result])
    
    result = manager.execute(fn)
    
    assert result.success is True
    assert result.retries == 2
    assert fn.call_count == 3
    assert mock_sleep.call_args_list == [call(15.0), call(30.0)]

def test_retry_manager_non_retryable_failure(mock_sleep):
    """F1: Non-retryable failure on first attempt."""
    policy = RetryPolicy(max_retries=3)
    manager = RetryManager(policy)
    
    non_retryable_error = ProviderError(message="fail", retryable=False, category=ErrorCategory.AUTH)
    fail_result = InferenceResult(
        text="", provider="test", model="test", 
        retries=0, duration_seconds=0.0, success=False, 
        provider_error=non_retryable_error
    )
    fn = MagicMock(return_value=fail_result)
    
    result = manager.execute(fn)
    
    assert result.success is False
    assert fn.call_count == 1
    mock_sleep.assert_not_called()

def test_retry_manager_exhaustion(mock_sleep):
    """F2: All retries exhausted (all retryable)."""
    policy = RetryPolicy(max_retries=3, base_delay=15.0, backoff_factor=2.0)
    manager = RetryManager(policy)
    
    retryable_error = ProviderError(message="retry", retryable=True, category=ErrorCategory.RATE_LIMIT, status_code=429)
    fail_result = InferenceResult(
        text="", provider="test", model="test", 
        retries=0, duration_seconds=0.0, success=False, 
        provider_error=retryable_error
    )
    
    fn = MagicMock(return_value=fail_result)
    
    result = manager.execute(fn)
    
    assert result.success is False
    assert result.retries == 2 # 2 sleeps happened
    assert result.error.startswith("Max retries exhausted")
    assert fn.call_count == 3
    assert mock_sleep.call_count == 2 # E1: last attempt does not sleep
    assert mock_sleep.call_args_list == [call(15.0), call(30.0)]

def test_retry_manager_non_retryable_after_retry(mock_sleep):
    """F3: Non-retryable failure after one retry."""
    policy = RetryPolicy(max_retries=3, base_delay=15.0)
    manager = RetryManager(policy)
    
    retryable_error = ProviderError(message="retry", retryable=True, category=ErrorCategory.RATE_LIMIT)
    non_retryable_error = ProviderError(message="fail", retryable=False, category=ErrorCategory.AUTH)
    
    res1 = InferenceResult(text="", provider="test", model="test", retries=0, duration_seconds=0.0, success=False, provider_error=retryable_error)
    res2 = InferenceResult(text="", provider="test", model="test", retries=0, duration_seconds=0.0, success=False, provider_error=non_retryable_error)
    
    fn = MagicMock(side_effect=[res1, res2])
    
    result = manager.execute(fn)
    
    assert result.success is False
    assert fn.call_count == 2
    mock_sleep.assert_called_once_with(15.0)

def test_retry_manager_no_provider_error(mock_sleep):
    """F4: provider_error=None on failure."""
    policy = RetryPolicy(max_retries=3)
    manager = RetryManager(policy)
    
    fail_result = InferenceResult(
        text="", provider="test", model="test", 
        retries=0, duration_seconds=0.0, success=False, 
        provider_error=None, error="Generic error"
    )
    fn = MagicMock(return_value=fail_result)
    
    result = manager.execute(fn)
    
    assert result.success is False
    assert fn.call_count == 1
    mock_sleep.assert_not_called()


# --- T-02 InferenceManager.generate ---

def test_inference_manager_primary_success(tmp_path):
    """S1: Primary succeeds on first attempt."""
    manager = InferenceManager(api_key="test-key", cache_dir=tmp_path)
    
    # E1: Use zero delay to avoid sleeps
    manager._retry_manager = RetryManager(RetryPolicy(max_retries=1, base_delay=0.0))
    
    success_result = InferenceResult(
        text="primary success", provider="gemini", model="gemini-2.5-flash", 
        retries=0, duration_seconds=0.1, success=True
    )
    
    with patch.object(GeminiProvider, "generate_once", return_value=success_result) as mock_gen:
        result = manager.generate("test prompt")
        
        assert result.success is True
        assert result.provider == "gemini"
        assert result.text == "primary success"
        assert manager.health.get("gemini").consecutive_failures == 0
        mock_gen.assert_called_once()
        
        # Verify cache write
        cache_files = list(tmp_path.glob("*"))
        assert len(cache_files) > 0

def test_inference_manager_cache_hit(tmp_path):
    """S2: Cache hit — provider never called."""
    manager = InferenceManager(api_key="test-key", cache_dir=tmp_path)
    manager._retry_manager = RetryManager(RetryPolicy(max_retries=1, base_delay=0.0))
    
    success_result = InferenceResult(
        text="cached result", provider="gemini", model="gemini-2.5-flash", 
        retries=0, duration_seconds=0.1, success=True
    )
    
    prompt = "cache me"
    
    # First call: populate cache
    with patch.object(GeminiProvider, "generate_once", return_value=success_result) as mock_gen:
        res1 = manager.generate(prompt)
        assert res1.text == "cached result"
        assert mock_gen.call_count == 1
        
        # Second call: hit cache
        res2 = manager.generate(prompt)
        assert res2.text == "cached result"
        assert mock_gen.call_count == 1 # Still 1

def test_inference_manager_failover(tmp_path):
    """S3: Primary fails, fallback succeeds."""
    manager = InferenceManager(
        api_key="test-key", 
        fallback="openrouter", 
        fallback_api_key="fallback-key",
        cache_dir=tmp_path
    )
    manager._retry_manager = RetryManager(RetryPolicy(max_retries=1, base_delay=0.0))
    
    fail_result = InferenceResult(
        text="", provider="gemini", model="gemini-2.5-flash", 
        retries=0, duration_seconds=0.1, success=False,
        provider_error=ProviderError(message="fail", retryable=False)
    )
    success_result = InferenceResult(
        text="fallback success", provider="openrouter", model="openrouter/auto", 
        retries=0, duration_seconds=0.1, success=True
    )
    
    with patch.object(GeminiProvider, "generate_once", return_value=fail_result) as mock_gemini:
        with patch.object(OpenRouterProvider, "generate_once", return_value=success_result) as mock_or:
            result = manager.generate("test prompt")
            
            assert result.success is True
            assert result.provider == "openrouter"
            assert result.text == "fallback success"
            assert manager.health.get("gemini").consecutive_failures == 1
            assert manager.health.get("openrouter").consecutive_failures == 0
            mock_gemini.assert_called_once()
            mock_or.assert_called_once()

def test_inference_manager_cooldown_skips_primary(tmp_path):
    """S4: Primary in cooldown, fallback called directly."""
    manager = InferenceManager(
        api_key="test-key", 
        fallback="openrouter", 
        cache_dir=tmp_path
    )
    manager._retry_manager = RetryManager(RetryPolicy(max_retries=1, base_delay=0.0))
    
    # Trigger cooldown for primary
    for _ in range(3):
        manager.health.record_failure("gemini")
    
    assert manager.health.get("gemini").in_cooldown is True
    
    success_result = InferenceResult(
        text="fallback success", provider="openrouter", model="openrouter/auto", 
        retries=0, duration_seconds=0.1, success=True
    )
    
    with patch.object(GeminiProvider, "generate_once") as mock_gemini:
        with patch.object(OpenRouterProvider, "generate_once", return_value=success_result) as mock_or:
            result = manager.generate("test prompt")
            
            assert result.success is True
            assert result.provider == "openrouter"
            mock_gemini.assert_not_called()
            mock_or.assert_called_once()

def test_inference_manager_no_fallback_failure(tmp_path):
    """F1: Primary fails, no fallback configured."""
    manager = InferenceManager(api_key="test-key", fallback=None)
    manager._retry_manager = RetryManager(RetryPolicy(max_retries=1, base_delay=0.0))
    
    fail_result = InferenceResult(
        text="", provider="gemini", model="gemini-2.5-flash", 
        retries=0, duration_seconds=0.1, success=False,
        provider_error=ProviderError(message="fail", retryable=False)
    )
    
    with patch.object(GeminiProvider, "generate_once", return_value=fail_result) as mock_gemini:
        result = manager.generate("test prompt")
        
        assert result.success is False
        assert manager.health.get("gemini").consecutive_failures == 1
        mock_gemini.assert_called_once()

def test_inference_manager_both_fail(tmp_path):
    """F2: Primary fails, fallback also fails."""
    manager = InferenceManager(api_key="test-key", fallback="openrouter")
    manager._retry_manager = RetryManager(RetryPolicy(max_retries=1, base_delay=0.0))
    
    fail_gemini = InferenceResult(
        text="", provider="gemini", model="gemini-2.5-flash", 
        retries=0, duration_seconds=0.1, success=False,
        provider_error=ProviderError(message="fail", retryable=False)
    )
    fail_or = InferenceResult(
        text="", provider="openrouter", model="openrouter/auto", 
        retries=0, duration_seconds=0.1, success=False,
        provider_error=ProviderError(message="fail", retryable=False)
    )
    
    with patch.object(GeminiProvider, "generate_once", return_value=fail_gemini):
        with patch.object(OpenRouterProvider, "generate_once", return_value=fail_or):
            result = manager.generate("test prompt")
            
            assert result.success is False
            assert result.provider == "openrouter"
            assert manager.health.get("gemini").consecutive_failures >= 1
            assert manager.health.get("openrouter").consecutive_failures >= 1

def test_inference_manager_cooldown_no_fallback(tmp_path):
    """F3: Primary in cooldown, no fallback."""
    manager = InferenceManager(api_key="test-key", fallback=None)
    manager._retry_manager = RetryManager(RetryPolicy(max_retries=1, base_delay=0.0))
    
    # Trigger cooldown
    for _ in range(3):
        manager.health.record_failure("gemini")
    
    fail_result = InferenceResult(
        text="", provider="gemini", model="gemini-2.5-flash", 
        retries=0, duration_seconds=0.1, success=False,
        provider_error=ProviderError(message="fail", retryable=False)
    )
    
    with patch.object(GeminiProvider, "generate_once", return_value=fail_result) as mock_gemini:
        result = manager.generate("test prompt")
        
        # cooldown check only skips when fallback exists
        assert result.success is False
        mock_gemini.assert_called_once()
