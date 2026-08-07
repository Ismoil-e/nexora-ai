from typing import Any
import httpx

from app.services.connectors.base import BaseConnector


class RESTConnector(BaseConnector):
    name = "Universal REST API Connector"
    connector_type = "rest"

    def __init__(self, base_url: str, auth_type: str = "bearer", auth_token: str | None = None, default_headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.auth_type = auth_type
        self.auth_token = auth_token
        self.headers = default_headers or {}

        if auth_token:
            if auth_type.lower() == "bearer":
                self.headers["Authorization"] = f"Bearer {auth_token}"
            elif auth_type.lower() == "apikey":
                self.headers["X-API-Key"] = auth_token

    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(self.base_url, headers=self.headers)
                return res.status_code < 500
        except Exception:
            return False

    async def execute_query(self, target: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        endpoint = target if target.startswith("/") else f"/{target}"
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        method = params.get("method", "GET").upper()
        json_body = params.get("body")

        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "POST":
                response = await client.post(url, json=json_body, headers=self.headers)
            elif method == "PUT":
                response = await client.put(url, json=json_body, headers=self.headers)
            else:
                response = await client.get(url, params=params.get("query_params"), headers=self.headers)

        if response.status_code >= 400:
            raise Exception(f"REST Connector API error: {response.status_code} - {response.text}")

        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        return {
            "status_code": response.status_code,
            "data": data,
        }
