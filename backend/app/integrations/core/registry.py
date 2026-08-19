from typing import Any, Type
from pydantic import BaseModel

from app.integrations.core.connector_interface import BaseConnector


class IntegrationTypeMeta(BaseModel):
    integration_type: str
    display_name: str
    category: str  # workspace, messaging, dev_tools, crm_erp, database, general
    description: str
    icon: str | None = None
    supported_auth_types: list[str]
    supported_actions: list[str]
    requires_credentials: bool = True
    config_schema: dict[str, Any] = {}


class IntegrationRegistry:
    """Central catalog of available Enterprise Integrations in Nexora AI."""

    def __init__(self):
        self._connector_classes: dict[str, Type[BaseConnector]] = {}
        self._metadata: dict[str, IntegrationTypeMeta] = {}

    def register(
        self,
        integration_type: str,
        connector_cls: Type[BaseConnector],
        meta: IntegrationTypeMeta,
    ):
        self._connector_classes[integration_type] = connector_cls
        self._metadata[integration_type] = meta

    def get_connector_class(self, integration_type: str) -> Type[BaseConnector] | None:
        return self._connector_classes.get(integration_type)

    def get_meta(self, integration_type: str) -> IntegrationTypeMeta | None:
        return self._metadata.get(integration_type)

    def list_all(self) -> list[IntegrationTypeMeta]:
        return list(self._metadata.values())

    def list_by_category(self, category: str) -> list[IntegrationTypeMeta]:
        return [m for m in self._metadata.values() if m.category == category]


integration_registry = IntegrationRegistry()
