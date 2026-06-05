import re
from typing import Any, Dict, Optional

# Secret key terms to redact (case-insensitive match)
SECRET_KEYS = ["api_key", "token", "secret", "password", "authorization", "bearer"]

# Regex for key-value secrets in text (e.g. api_key="value", token: value)
# Captures: 1=key, 2=separator, 3=optional quote, 4=optional bearer prefix, 5=secret value
TEXT_SECRET_REGEX = re.compile(
    r'(?i)\b(' + '|'.join(SECRET_KEYS) + r')\b\s*([:=])\s*(["\']?)(bearer\s+)?([a-zA-Z0-9_\-\.\+]{4,})\3'
)

# Regex for Bearer tokens in text (e.g. Bearer sk-1234...)
# Captures: 1=bearer prefix, 2=secret value
BEARER_REGEX = re.compile(
    r'(?i)\b(bearer\s+)(["\']?)([a-zA-Z0-9_\-\.\+]{4,})\2'
)


def redact_secret(value: Optional[str]) -> str:
    """
    Redacts a single secret string, preserving enough prefix/suffix for
    debugging while never revealing the full secret.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    if not value:
        return ""

    # If the secret is very short, redact it completely
    if len(value) <= 8:
        return "[REDACTED]"

    # Preserve first 4 and last 4 characters, mask the middle
    return f"{value[:4]}...{value[-4:]}"


def redact_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively clones a mapping and redacts any values associated with secret keys.
    """
    if not isinstance(mapping, dict):
        return mapping

    redacted: dict[str, Any] = {}
    for k, v in mapping.items():
        k_lower = k.lower()
        is_secret_key = any(sk in k_lower for sk in SECRET_KEYS)

        if isinstance(v, dict):
            redacted[k] = redact_mapping(v)
        elif isinstance(v, list):
            redacted[k] = [
                redact_mapping(item) if isinstance(item, dict)
                else (redact_secret(str(item)) if is_secret_key else item)
                for item in v
            ]
        elif is_secret_key:
            if v is None:
                redacted[k] = ""
            else:
                redacted[k] = redact_secret(str(v))
        else:
            redacted[k] = v

    return redacted


def redact_text(text: str) -> str:
    """
    Scans a block of text (e.g. log output, exception detail) and redacts
    any patterns resembling API keys, Bearer tokens, or secret key-value pairs.
    """
    if not text:
        return ""

    def redact_text_match(match: re.Match) -> str:
        key = match.group(1)
        sep = match.group(2)
        quote = match.group(3)
        bearer_prefix = match.group(4) or ""
        val = match.group(5)
        redacted = redact_secret(val)
        return f"{key}{sep}{quote}{bearer_prefix}{redacted}{quote}"

    def redact_bearer_match(match: re.Match) -> str:
        prefix = match.group(1)
        quote = match.group(2)
        val = match.group(3)
        redacted = redact_secret(val)
        return f"{prefix}{quote}{redacted}{quote}"

    # Replace key-value patterns first
    text = TEXT_SECRET_REGEX.sub(redact_text_match, text)
    # Replace Bearer tokens
    text = BEARER_REGEX.sub(redact_bearer_match, text)

    return text
