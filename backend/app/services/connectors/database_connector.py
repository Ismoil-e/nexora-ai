from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.services.connectors.base import BaseConnector


class DatabaseConnector(BaseConnector):
    name = "Enterprise SQL Database Connector"
    connector_type = "database"

    def __init__(self, connection_url: str):
        # Convert standard postgresql:// to postgresql+asyncpg:// if needed
        if connection_url.startswith("postgresql://"):
            connection_url = connection_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif connection_url.startswith("sqlite://"):
            connection_url = connection_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

        self.connection_url = connection_url
        self.engine = create_async_engine(connection_url, pool_pre_ping=True)

    async def test_connection(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                return True
        except Exception:
            return False

    async def execute_query(self, target: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        sql_query = target.strip()
        params = params or {}

        # Security check: Read-only enforcement for enterprise database queries
        lower_query = sql_query.lower()
        forbidden_keywords = ["drop ", "delete ", "update ", "insert ", "alter ", "truncate ", "grant "]
        if any(kw in lower_query for kw in forbidden_keywords):
            raise ValueError("Xavfsizlik qoidasi: Faqat o'qish (SELECT) so'rovlariga ruxsat berilgan.")

        async with self.engine.connect() as conn:
            result = await conn.execute(text(sql_query), params)
            mappings = list(result.mappings().all())

            # Convert row mapping objects to plain dicts
            rows = [dict(m) for m in mappings[:500]]  # Cap at 500 rows for safety

        return {
            "row_count": len(rows),
            "rows": rows,
        }

    async def close(self):
        await self.engine.dispose()
