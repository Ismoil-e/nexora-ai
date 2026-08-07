from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    name: str
    connector_type: str  # e.g., 'rest', 'database', 's3', 'sap'

    @abstractmethod
    async def test_connection(self) -> bool:
        pass

    @abstractmethod
    async def execute_query(self, target: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        pass
