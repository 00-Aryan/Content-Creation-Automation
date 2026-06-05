import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from content_creation.audit.models import AuditActorType, AuditRecord, AuditSeverity, AuditSource
from content_creation.events.models import EventSeverity, EventType, WorkflowEvent
from content_creation.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)
from content_creation.security.redaction import redact_mapping, redact_secret, redact_text


def test_redact_secret_standard():
    # Length > 8
    secret = "sk-1234567890abcdef"
    assert redact_secret(secret) == "sk-1...cdef"

    # Length <= 8
    short_secret = "12345"
    assert redact_secret(short_secret) == "[REDACTED]"


def test_redact_secret_empty_and_none():
    assert redact_secret(None) == ""
    assert redact_secret("") == ""


def test_redact_mapping_flat():
    raw = {
        "api_key": "sk-1234567890abcdef",
        "normal_field": "public_data",
        "my_token": "secret_token_value",
        "some_secret": "my_password",
    }
    redacted = redact_mapping(raw)

    assert redacted["api_key"] == "sk-1...cdef"
    assert redacted["normal_field"] == "public_data"
    assert redacted["my_token"] == "secr...alue"
    assert redacted["some_secret"] == "my_p...word"


def test_redact_mapping_nested():
    raw = {
        "info": {
            "api_key": "sk-1234567890abcdef",
            "normal_field": "public",
        },
        "list_of_dicts": [
            {"password": "secretpassword"},
            {"normal": "ok"},
        ],
        "list_of_strings_under_secret_key": ["secretpassword", "anothersecret"],
    }
    # If the key itself contains 'secret'
    raw_with_secret_list = {
        "secret_keys": ["sk-1234567890", "supersecret123"],
        "normal_field": "ok",
        "nested": raw,
    }

    redacted = redact_mapping(raw_with_secret_list)
    assert redacted["secret_keys"] == ["sk-1...7890", "supe...t123"]
    assert redacted["nested"]["info"]["api_key"] == "sk-1...cdef"
    assert redacted["nested"]["info"]["normal_field"] == "public"
    assert redacted["nested"]["list_of_dicts"][0]["password"] == "secr...word"
    assert redacted["nested"]["list_of_dicts"][1]["normal"] == "ok"


def test_redact_text():
    # Test key-value styles
    text1 = "Error occurred while using api_key='sk-1234567890abcdef' in pipeline."
    assert "sk-1...cdef" in redact_text(text1)
    assert "sk-1234567890abcdef" not in redact_text(text1)

    text2 = "Config: token: 'super_secret_token_123' and bearer: \"another_token_abc\""
    redacted_text2 = redact_text(text2)
    assert "supe..._123" in redacted_text2
    assert "anot..._abc" in redacted_text2
    assert "super_secret_token_123" not in redacted_text2

    # Test Bearer prefix style
    text3 = "Headers: Authorization: Bearer sk-1234567890abcdef, Content-Type: application/json"
    redacted_text3 = redact_text(text3)
    assert "sk-1...cdef" in redacted_text3
    assert "sk-1234567890abcdef" not in redacted_text3


def test_event_safe_payload():
    event = WorkflowEvent(
        event_id=uuid.uuid4(),
        event_type=EventType.ASSET_GENERATED,
        timestamp=datetime.now(timezone.utc),
        source="test",
        correlation_id="corr-1",
        actor_id="actor-1",
        entity_type="brief",
        entity_id="entity-1",
        severity=EventSeverity.INFO,
        payload={
            "api_key": "sk-1234567890abcdef",
            "normal_data": "some_value",
        },
    )
    assert event.payload["api_key"] == "sk-1...cdef"
    assert event.payload["normal_data"] == "some_value"


def test_audit_safe_payload():
    record = AuditRecord(
        audit_id=uuid.uuid4(),
        timestamp=datetime.now(timezone.utc),
        actor_type=AuditActorType.SYSTEM,
        actor_id="actor-1",
        action_type="generate_brief",
        entity_type="brief",
        entity_id="entity-1",
        event_type="brief_generated",
        correlation_id="corr-1",
        previous_state="api_key=sk-1234567890abcdef",
        new_state="normal",
        metadata={
            "token": "secret_token_value_abc",
            "normal": "value",
        },
        source=AuditSource.WORKFLOW,
        severity=AuditSeverity.INFO,
    )
    assert record.metadata["token"] == "secr..._abc"
    assert "sk-1...cdef" in record.previous_state
    assert "sk-1234567890abcdef" not in record.previous_state


def test_notification_safe_payload():
    notif = Notification(
        notification_id=uuid.uuid4(),
        title="Error: api_key='sk-1234567890abcdef' failed",
        message="Details of fail: token=1234567890abcdef",
        severity=NotificationSeverity.ERROR,
        category=NotificationCategory.SYSTEM,
        status=NotificationStatus.UNREAD,
        timestamp=datetime.now(timezone.utc),
        correlation_id="corr-1",
    )
    assert "sk-1...cdef" in notif.title
    assert "sk-1234567890abcdef" not in notif.title
    assert "1234...cdef" in notif.message
    assert "1234567890abcdef" not in notif.message
