import asyncio
import pytest
import uuid

import app.integrations
from app.integrations.contracts.types import CredentialData, NexoraEvent
from app.integrations.core.event_normalizer import EventNormalizer
from app.integrations.core.rate_limiter import RateLimitManager, RetryManager
from app.integrations.core.registry import integration_registry
from app.integrations.core.webhook_manager import WebhookManager
from app.integrations.security.encryption import CredentialEncryptionManager


def test_credential_encryption():
    enc = CredentialEncryptionManager(key_secret="test_secret_key_1234567890_test_key")
    data = {"api_key": "sk-test-12345", "token": "oauth-token-xyz"}
    encrypted = enc.encrypt_data(data)
    assert encrypted != str(data)

    decrypted = enc.decrypt_data(encrypted)
    assert isinstance(decrypted, dict)
    assert decrypted["api_key"] == "sk-test-12345"


def test_integration_registry():
    catalog = integration_registry.list_all()
    assert len(catalog) >= 5
    types = [meta.integration_type for meta in catalog]
    assert "google_workspace" in types
    assert "microsoft365" in types
    assert "telegram" in types
    assert "slack" in types
    assert "github" in types
    assert "jira" in types
    assert "crm_erp" in types
    assert "database" in types
    assert "rest_api" in types


def test_event_normalizer_telegram():
    company_id = uuid.uuid4()
    integration_id = uuid.uuid4()
    raw = {
        "message": {
            "message_id": 101,
            "from": {"id": 555, "username": "ismoil"},
            "chat": {"id": 999, "type": "private"},
            "text": "Hello Nexora AI Agent!",
        }
    }
    event = EventNormalizer.normalize_event("telegram", company_id, integration_id, raw)
    assert event.event_type == "message.received"
    assert event.source_vendor == "telegram"
    assert event.actor_email == "ismoil"
    assert "Hello Nexora" in event.content_summary


def test_event_normalizer_github():
    company_id = uuid.uuid4()
    integration_id = uuid.uuid4()
    raw = {
        "action": "opened",
        "issue": {"title": "Fix memory leak in Celery worker"},
        "repository": {"id": 1234, "full_name": "Ismoil-e/nexora-ai"},
        "sender": {"login": "Ismoil-e"},
    }
    headers = {"x-github-event": "issues", "x-github-delivery": "delivery-123"}
    event = EventNormalizer.normalize_event("github", company_id, integration_id, raw, headers)
    assert event.event_type == "github.issues.opened"
    assert event.source_vendor == "github"
    assert event.actor_id == "Ismoil-e"
    assert "Fix memory leak" in event.content_summary


def test_webhook_manager_signature_verification():
    wm = WebhookManager()

    # Github HMAC SHA256 test
    secret = "my_github_secret"
    body = b'{"ref": "refs/heads/master"}'
    import hmac, hashlib
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert wm.verify_signature("github", secret, body, {"x-hub-signature-256": sig}) is True
    assert wm.verify_signature("github", "wrong_secret", body, {"x-hub-signature-256": sig}) is False


def test_rate_limiter():
    rl = RateLimitManager(requests_per_minute=2)
    key = "tenant1:integration1"
    assert rl.check_rate_limit(key) is True
    assert rl.check_rate_limit(key) is True
    assert rl.check_rate_limit(key) is False  # Exceeded 2 rpm


def test_retry_manager_success():
    rm = RetryManager(max_retries=2, initial_delay_sec=0.01)

    async def sample_func():
        return "ok"

    result = asyncio.run(rm.execute_with_retry("key1", sample_func))
    assert result == "ok"
