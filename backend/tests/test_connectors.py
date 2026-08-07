import pytest

from app.core.events import DomainEvent, event_bus
from app.services.connectors.connector_manager import connector_manager
from app.services.connectors.rest_connector import RESTConnector


@pytest.mark.asyncio
async def test_event_bus_publishing():
    received_events = []

    async def test_handler(event: DomainEvent):
        received_events.append(event)

    event_bus.subscribe("test.event", test_handler)

    event = DomainEvent(
        event_type="test.event",
        company_id="test_company",
        user_id="test_user",
        payload={"key": "value"},
    )

    await event_bus.publish(event)
    assert len(received_events) > 0
    assert received_events[0].event_type == "test.event"


def test_connector_manager():
    connector = RESTConnector(base_url="https://api.example.com")
    connector_manager.register_connector("example_rest", connector)

    retrieved = connector_manager.get_connector("example_rest")
    assert retrieved is not None
    assert retrieved.connector_type == "rest"
