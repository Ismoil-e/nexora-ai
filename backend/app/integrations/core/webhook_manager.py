import hmac
import hashlib
import json
import time
import uuid
import httpx
from typing import Any

from app.integrations.contracts.types import NexoraEvent


class WebhookVerificationError(Exception):
    pass


class WebhookManager:
    """Manages Inbound Webhook Signature Verification & Outbound Webhook Delivery."""

    def __init__(self):
        self._processed_event_ids: set[str] = set()

    def is_duplicate_event(self, event_id: str) -> bool:
        """Idempotency check: returns True if event was already processed."""
        if event_id in self._processed_event_ids:
            return True
        self._processed_event_ids.add(event_id)
        if len(self._processed_event_ids) > 10_000:
            # Prevent memory bloat by trimming old IDs
            self._processed_event_ids = set(list(self._processed_event_ids)[-5000:])
        return False

    def verify_signature(
        self,
        vendor: str,
        secret: str,
        raw_body: bytes | str,
        headers: dict[str, str],
    ) -> bool:
        if not secret:
            return True  # If no secret configured, skip check

        headers_lower = {k.lower(): v for k, v in headers.items()}
        body_bytes = raw_body.encode() if isinstance(raw_body, str) else raw_body

        if vendor == "github":
            signature = headers_lower.get("x-hub-signature-256")
            if not signature or not signature.startswith("sha256="):
                return False
            expected = "sha256=" + hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(signature, expected)

        elif vendor == "slack":
            timestamp = headers_lower.get("x-slack-request-timestamp", "")
            signature = headers_lower.get("x-slack-signature", "")
            if not timestamp or not signature:
                return False
            if abs(time.time() - float(timestamp)) > 300:
                # Replay attack protection (older than 5 min)
                return False
            sig_basestring = f"v0:{timestamp}:{body_bytes.decode('utf-8', errors='ignore')}"
            expected = "v0=" + hmac.new(secret.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(signature, expected)

        elif vendor == "telegram":
            token = headers_lower.get("x-telegram-bot-api-secret-token")
            return hmac.compare_digest(token or "", secret)

        # Generic HMAC-SHA256 verification
        signature = headers_lower.get("x-signature") or headers_lower.get("x-nexora-signature")
        if signature:
            expected = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
            if signature.startswith("sha256="):
                expected = "sha256=" + expected
            return hmac.compare_digest(signature, expected)

        return True

    async def deliver_outbound_webhook(
        self,
        target_url: str,
        secret: str | None,
        event: NexoraEvent,
        custom_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Dispatches an outbound webhook payload to an external URL."""
        payload_str = event.model_dump_json()
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Nexora-AI-Webhook-Engine/1.0",
            "X-Nexora-Event-ID": event.event_id,
            "X-Nexora-Event-Type": event.event_type,
        }
        if custom_headers:
            headers.update(custom_headers)

        if secret:
            sig = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
            headers["X-Nexora-Signature"] = f"sha256={sig}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(target_url, content=payload_str, headers=headers)
            resp.raise_for_status()
            return {"status_code": resp.status_code, "body": resp.text[:200]}


webhook_manager = WebhookManager()
