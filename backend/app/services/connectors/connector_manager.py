from typing import Any
import uuid

from app.services.connectors.base import BaseConnector
from app.services.connectors.database_connector import DatabaseConnector
from app.services.connectors.rest_connector import RESTConnector


class ConnectorManager:
    def __init__(self):
        self._connectors: dict[str, BaseConnector] = {}

    def register_connector(self, connector_id: str, connector: BaseConnector):
        self._connectors[connector_id] = connector

    def get_connector(self, connector_id: str) -> BaseConnector | None:
        return self._connectors.get(connector_id)

    async def execute_connector(self, connector_id: str, target: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        connector = self.get_connector(connector_id)
        if not connector:
            raise ValueError(f"'{connector_id}' nomli ulagich (connector) topilmadi.")

        return await connector.execute_query(target, params)


# Global Singleton Connector Manager Instance
connector_manager = ConnectorManager()
