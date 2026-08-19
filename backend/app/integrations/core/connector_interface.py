import uuid
from abc import ABC, abstractmethod
from typing import Any

from app.integrations.contracts.types import (
    ConnectorHealth,
    CredentialData,
    ExecutionResult,
    NexoraEvent,
)


class BaseConnector(ABC):
    """Unified Enterprise Connector Interface for Nexora AI Integration Hub.

    All specific connectors (Google Workspace, Microsoft 365, Telegram, Slack,
    GitHub, Jira, ERP/CRM, Databases, REST APIs) implement this interface.
    """

    connector_type: str  # e.g., 'google_drive', 'telegram', 'slack', 'jira', 'github', 'rest_api'
    display_name: str
    category: str  # e.g., 'workspace', 'messaging', 'dev_tools', 'crm_erp', 'database', 'general'
    supported_actions: list[str] = []

    def __init__(
        self,
        integration_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        config: dict[str, Any] | None = None,
        credentials: CredentialData | None = None,
    ):
        self.integration_id = integration_id
        self.company_id = company_id
        self.config = config or {}
        self.credentials = credentials
        self.is_connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """Establishes session/connection to the external provider."""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """Verifies or performs authentication (OAuth2, API key validation)."""
        pass

    @abstractmethod
    async def validate_credentials(self, credentials: CredentialData) -> bool:
        """Validates credential syntax, signatures, or test token validity."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Terminates session or revokes connections."""
        pass

    @abstractmethod
    async def health_check(self) -> ConnectorHealth:
        """Performs a real-time status check on the external endpoint."""
        pass

    @abstractmethod
    async def fetch_data(self, resource_type: str, params: dict[str, Any] | None = None) -> ExecutionResult:
        """Fetches data/entities from the external service."""
        pass

    @abstractmethod
    async def send_data(self, resource_type: str, data: dict[str, Any], params: dict[str, Any] | None = None) -> ExecutionResult:
        """Sends data/messages/requests to the external service."""
        pass

    @abstractmethod
    async def create(self, resource_type: str, data: dict[str, Any]) -> ExecutionResult:
        """Creates a new record/resource in the external service."""
        pass

    @abstractmethod
    async def update(self, resource_type: str, resource_id: str, data: dict[str, Any]) -> ExecutionResult:
        """Updates an existing record/resource in the external service."""
        pass

    @abstractmethod
    async def delete(self, resource_type: str, resource_id: str) -> ExecutionResult:
        """Deletes a record/resource in the external service."""
        pass

    @abstractmethod
    async def subscribe_webhook(self, target_url: str, event_types: list[str]) -> ExecutionResult:
        """Registers a webhook subscription with the external provider."""
        pass

    @abstractmethod
    async def handle_webhook(self, raw_payload: dict[str, Any] | str, headers: dict[str, str]) -> NexoraEvent:
        """Parses and normalizes an incoming webhook payload into a NexoraEvent."""
        pass

    @abstractmethod
    async def refresh_token(self) -> CredentialData | None:
        """Refreshes expired OAuth2/bearer tokens where applicable."""
        pass
