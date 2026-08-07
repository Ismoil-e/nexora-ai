import asyncio
import datetime
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger("nexora.events")


@dataclass
class DomainEvent:
    event_type: str
    company_id: uuid.UUID | str | None
    user_id: uuid.UUID | str | None
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._wildcard_subscribers: list[EventHandler] = []

    def subscribe(self, event_type: str, handler: EventHandler):
        if event_type == "*":
            if handler not in self._wildcard_subscribers:
                self._wildcard_subscribers.append(handler)
        else:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    async def publish(self, event: DomainEvent):
        logger.info(f"Publishing event: {event.event_type} [{event.event_id}]")

        handlers = list(self._subscribers.get(event.event_type, [])) + self._wildcard_subscribers
        if not handlers:
            return

        tasks = [asyncio.create_task(self._safe_execute(handler, event)) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_execute(self, handler: EventHandler, event: DomainEvent):
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error handling event {event.event_type} in {handler.__name__}: {str(e)}", exc_info=True)


# Global Singleton Event Bus Instance
event_bus = EventBus()


# Built-in Audit Log Event Handler
async def audit_log_event_handler(event: DomainEvent):
    from app.core.database import async_session_factory
    from app.models.audit import AuditLog

    if not event.company_id:
        return

    async with async_session_factory() as db:
        try:
            audit = AuditLog(
                company_id=str(event.company_id),
                user_id=str(event.user_id) if event.user_id else None,
                action=event.event_type,
                resource_type=str(event.payload.get("resource_type", "system")),
                resource_id=str(event.payload.get("resource_id", "")) if event.payload.get("resource_id") else None,
                details=str(event.payload),
                status="success",
            )
            db.add(audit)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist audit log for event {event.event_type}: {str(e)}")


# Register default audit handler for all domain events
event_bus.subscribe("*", audit_log_event_handler)
