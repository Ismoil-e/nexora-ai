import json
import uuid
from typing import Any

from app.integrations.contracts.types import CredentialData
from app.integrations.core.connector_interface import BaseConnector
from app.integrations.core.registry import integration_registry
from app.integrations.security.encryption import credential_encryption


class ConnectorManager:
    """Factory & runtime manager for creating and configuring connector instances."""

    def __init__(self):
        self._active_instances: dict[str, BaseConnector] = {}

    def build_connector(
        self,
        integration_id: uuid.UUID,
        company_id: uuid.UUID,
        integration_type: str,
        config_json: str | dict | None = None,
        encrypted_credentials: str | None = None,
        auth_type: str = "api_key",
    ) -> BaseConnector:
        connector_cls = integration_registry.get_connector_class(integration_type)
        if not connector_cls:
            raise ValueError(f"Integration type '{integration_type}' is not registered in Integration Hub.")

        config = {}
        if isinstance(config_json, str) and config_json:
            try:
                config = json.loads(config_json)
            except Exception:
                config = {}
        elif isinstance(config_json, dict):
            config = config_json

        credentials_obj = None
        if encrypted_credentials:
            decrypted = credential_encryption.decrypt_data(encrypted_credentials)
            if isinstance(decrypted, dict):
                credentials_obj = CredentialData(auth_type=auth_type, **decrypted)

        instance = connector_cls(
            integration_id=integration_id,
            company_id=company_id,
            config=config,
            credentials=credentials_obj,
        )
        return instance

    async def get_and_connect(
        self,
        integration_id: uuid.UUID,
        company_id: uuid.UUID,
        integration_type: str,
        config_json: str | dict | None = None,
        encrypted_credentials: str | None = None,
        auth_type: str = "api_key",
    ) -> BaseConnector:
        connector = self.build_connector(
            integration_id=integration_id,
            company_id=company_id,
            integration_type=integration_type,
            config_json=config_json,
            encrypted_credentials=encrypted_credentials,
            auth_type=auth_type,
        )
        await connector.connect()
        return connector


connector_manager = ConnectorManager()
