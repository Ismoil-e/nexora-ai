import uuid
from datetime import datetime, timezone
from typing import Any

from app.integrations.contracts.types import NexoraEvent


class EventNormalizer:
    """Standardizes heterogeneous vendor webhook payloads into NexoraEvent format."""

    @staticmethod
    def normalize_event(
        source_vendor: str,
        company_id: uuid.UUID,
        integration_id: uuid.UUID,
        raw_payload: dict[str, Any] | str,
        headers: dict[str, str] | None = None,
    ) -> NexoraEvent:
        headers = headers or {}
        payload = raw_payload if isinstance(raw_payload, dict) else {}

        if source_vendor in ("google", "google_workspace", "google_drive"):
            return EventNormalizer._normalize_google(company_id, integration_id, payload, headers)
        elif source_vendor in ("microsoft", "microsoft365", "onedrive"):
            return EventNormalizer._normalize_microsoft(company_id, integration_id, payload, headers)
        elif source_vendor == "telegram":
            return EventNormalizer._normalize_telegram(company_id, integration_id, payload)
        elif source_vendor == "slack":
            return EventNormalizer._normalize_slack(company_id, integration_id, payload)
        elif source_vendor == "discord":
            return EventNormalizer._normalize_discord(company_id, integration_id, payload)
        elif source_vendor == "github":
            return EventNormalizer._normalize_github(company_id, integration_id, payload, headers)
        elif source_vendor == "jira":
            return EventNormalizer._normalize_jira(company_id, integration_id, payload)
        elif source_vendor in ("erp", "crm", "sap", "odoo"):
            return EventNormalizer._normalize_erp_crm(company_id, integration_id, source_vendor, payload)

        # Fallback generic webhook normalizer
        event_id = str(payload.get("id") or payload.get("event_id") or uuid.uuid4())
        event_type = str(payload.get("type") or payload.get("event") or "webhook.received")
        return NexoraEvent(
            event_id=event_id,
            company_id=company_id,
            integration_id=integration_id,
            source_vendor=source_vendor,
            event_type=event_type,
            resource_type=payload.get("resource_type", "webhook"),
            resource_id=str(payload.get("resource_id", "")),
            title=payload.get("title") or payload.get("subject"),
            content_summary=str(payload.get("summary") or payload.get("message") or ""),
            data=payload,
            raw_payload=raw_payload,
            is_important=bool(payload.get("is_important", False)),
            requires_memory_ingestion=bool(payload.get("requires_memory", False)),
        )

    @staticmethod
    def _normalize_telegram(company_id: uuid.UUID, integration_id: uuid.UUID, payload: dict) -> NexoraEvent:
        message = payload.get("message") or payload.get("edited_message") or {}
        from_user = message.get("from") or {}
        text = message.get("text") or message.get("caption") or ""
        msg_id = str(message.get("message_id", uuid.uuid4()))

        return NexoraEvent(
            event_id=f"tg_{msg_id}",
            company_id=company_id,
            integration_id=integration_id,
            source_vendor="telegram",
            event_type="message.received",
            resource_type="chat_message",
            resource_id=str(message.get("chat", {}).get("id", "")),
            actor_id=str(from_user.get("id", "")),
            actor_email=from_user.get("username"),
            title=f"Telegram message from {from_user.get('first_name', 'User')}",
            content_summary=text[:500],
            data={
                "text": text,
                "chat_id": message.get("chat", {}).get("id"),
                "chat_type": message.get("chat", {}).get("type"),
                "user": from_user,
            },
            raw_payload=payload,
            is_important=True,
            requires_memory_ingestion=True,
        )

    @staticmethod
    def _normalize_slack(company_id: uuid.UUID, integration_id: uuid.UUID, payload: dict) -> NexoraEvent:
        event = payload.get("event") or payload
        evt_type = event.get("type", "message")
        text = event.get("text", "")
        user_id = event.get("user", "")

        return NexoraEvent(
            event_id=f"slack_{event.get('client_msg_id') or event.get('ts') or uuid.uuid4()}",
            company_id=company_id,
            integration_id=integration_id,
            source_vendor="slack",
            event_type=f"slack.{evt_type}",
            resource_type="channel_message",
            resource_id=event.get("channel"),
            actor_id=user_id,
            title="Slack event",
            content_summary=text[:500],
            data=event,
            raw_payload=payload,
            is_important=True,
            requires_memory_ingestion=True,
        )

    @staticmethod
    def _normalize_discord(company_id: uuid.UUID, integration_id: uuid.UUID, payload: dict) -> NexoraEvent:
        author = payload.get("author") or {}
        content = payload.get("content", "")
        msg_id = payload.get("id", str(uuid.uuid4()))

        return NexoraEvent(
            event_id=f"discord_{msg_id}",
            company_id=company_id,
            integration_id=integration_id,
            source_vendor="discord",
            event_type="discord.message_created",
            resource_type="channel_message",
            resource_id=payload.get("channel_id"),
            actor_id=author.get("id"),
            actor_email=author.get("username"),
            title=f"Discord message from {author.get('username')}",
            content_summary=content[:500],
            data=payload,
            raw_payload=payload,
            is_important=False,
            requires_memory_ingestion=True,
        )

    @staticmethod
    def _normalize_github(company_id: uuid.UUID, integration_id: uuid.UUID, payload: dict, headers: dict) -> NexoraEvent:
        gh_event = headers.get("x-github-event") or payload.get("action") or "push"
        sender = payload.get("sender") or {}
        repo = payload.get("repository") or {}

        action = payload.get("action", "")
        title = f"GitHub {gh_event} in {repo.get('full_name', 'repo')}"
        summary = ""
        if "issue" in payload:
            summary = payload["issue"].get("title", "")
        elif "pull_request" in payload:
            summary = payload["pull_request"].get("title", "")
        elif "head_commit" in payload:
            summary = payload["head_commit"].get("message", "")

        return NexoraEvent(
            event_id=f"gh_{headers.get('x-github-delivery') or uuid.uuid4()}",
            company_id=company_id,
            integration_id=integration_id,
            source_vendor="github",
            event_type=f"github.{gh_event}.{action}" if action else f"github.{gh_event}",
            resource_type="repository",
            resource_id=str(repo.get("id", "")),
            actor_id=sender.get("login"),
            title=title,
            content_summary=summary[:500],
            data=payload,
            raw_payload=payload,
            is_important=True,
            requires_memory_ingestion=True,
        )

    @staticmethod
    def _normalize_jira(company_id: uuid.UUID, integration_id: uuid.UUID, payload: dict) -> NexoraEvent:
        webhook_evt = payload.get("webhookEvent", "jira:issue_updated")
        issue = payload.get("issue") or {}
        fields = issue.get("fields") or {}
        user = payload.get("user") or {}

        return NexoraEvent(
            event_id=f"jira_{issue.get('id') or uuid.uuid4()}",
            company_id=company_id,
            integration_id=integration_id,
            source_vendor="jira",
            event_type=webhook_evt,
            resource_type="issue",
            resource_id=issue.get("key"),
            actor_id=user.get("accountId"),
            actor_email=user.get("emailAddress"),
            title=f"Jira {issue.get('key')}: {fields.get('summary', '')}",
            content_summary=str(fields.get("description") or "")[:500],
            data=payload,
            raw_payload=payload,
            is_important=True,
            requires_memory_ingestion=True,
        )

    @staticmethod
    def _normalize_google(company_id: uuid.UUID, integration_id: uuid.UUID, payload: dict, headers: dict) -> NexoraEvent:
        res_state = headers.get("x-goog-resource-state", "change")
        res_id = headers.get("x-goog-resource-id", "")
        channel_id = headers.get("x-goog-channel-id", "")

        return NexoraEvent(
            event_id=f"gdrive_{headers.get('x-goog-message-number') or uuid.uuid4()}",
            company_id=company_id,
            integration_id=integration_id,
            source_vendor="google_workspace",
            event_type=f"google_drive.{res_state}",
            resource_type="file",
            resource_id=res_id,
            title=f"Google Workspace update ({res_state})",
            content_summary=f"Resource {res_id} changed in channel {channel_id}",
            data=payload,
            raw_payload=payload,
            is_important=True,
            requires_memory_ingestion=True,
        )

    @staticmethod
    def _normalize_microsoft(company_id: uuid.UUID, integration_id: uuid.UUID, payload: dict, headers: dict) -> NexoraEvent:
        value = payload.get("value", [{}])[0] if isinstance(payload.get("value"), list) and payload.get("value") else payload
        change_type = value.get("changeType", "updated")
        resource = value.get("resource", "")

        return NexoraEvent(
            event_id=f"ms_{value.get('clientState') or uuid.uuid4()}",
            company_id=company_id,
            integration_id=integration_id,
            source_vendor="microsoft365",
            event_type=f"ms365.{change_type}",
            resource_type="resource",
            resource_id=resource,
            title=f"Microsoft 365 {change_type}",
            content_summary=f"Resource {resource} changed",
            data=payload,
            raw_payload=payload,
            is_important=True,
            requires_memory_ingestion=True,
        )

    @staticmethod
    def _normalize_erp_crm(company_id: uuid.UUID, integration_id: uuid.UUID, vendor: str, payload: dict) -> NexoraEvent:
        entity = payload.get("entity", "customer")
        action = payload.get("action", "updated")
        entity_id = payload.get("id") or payload.get("entity_id")

        return NexoraEvent(
            event_id=f"{vendor}_{entity_id or uuid.uuid4()}",
            company_id=company_id,
            integration_id=integration_id,
            source_vendor=vendor,
            event_type=f"{vendor}.{entity}.{action}",
            resource_type=entity,
            resource_id=str(entity_id or ""),
            title=f"{vendor.upper()} {entity} {action}",
            content_summary=str(payload.get("name") or payload.get("summary") or "")[:500],
            data=payload,
            raw_payload=payload,
            is_important=True,
            requires_memory_ingestion=True,
        )
