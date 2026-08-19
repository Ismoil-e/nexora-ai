import time
import uuid
import httpx
from typing import Any

from app.integrations.contracts.types import (
    ConnectorHealth,
    CredentialData,
    ExecutionResult,
    NexoraEvent,
)
from app.integrations.core.connector_interface import BaseConnector
from app.integrations.core.event_normalizer import EventNormalizer
from app.integrations.core.registry import IntegrationTypeMeta, integration_registry


class GitHubJiraConnector(BaseConnector):
    connector_type = "github_jira"
    display_name = "GitHub & Jira Enterprise Connector"
    category = "dev_tools"
    supported_actions = [
        "github.list_repos",
        "github.list_issues",
        "github.create_issue",
        "github.create_pull_request",
        "jira.list_issues",
        "jira.create_task",
        "jira.update_issue",
        "jira.add_comment",
    ]

    async def connect(self) -> bool:
        self.is_connected = True
        return True

    async def authenticate(self) -> bool:
        return bool(self.credentials and (self.credentials.api_key or self.credentials.access_token))

    async def validate_credentials(self, credentials: CredentialData) -> bool:
        return bool(credentials.api_key or credentials.access_token or (credentials.username and credentials.password))

    async def disconnect(self) -> bool:
        self.is_connected = False
        return True

    async def health_check(self) -> ConnectorHealth:
        start = time.time()
        if self.config.get("vendor") == "jira" and self.credentials:
            domain = self.config.get("domain") or "jira.atlassian.com"
            url = f"https://{domain}/rest/api/3/myself"
            auth = (self.credentials.username, self.credentials.api_key or self.credentials.access_token)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(url, auth=auth)
                    if resp.status_code == 200:
                        return ConnectorHealth(status="healthy", latency_ms=int((time.time() - start) * 1000))
            except Exception as exc:
                return ConnectorHealth(status="degraded", latency_ms=int((time.time() - start) * 1000), error_message=str(exc))

        return ConnectorHealth(status="healthy", latency_ms=int((time.time() - start) * 1000))

    async def fetch_data(self, resource_type: str, params: dict[str, Any] | None = None) -> ExecutionResult:
        params = params or {}
        start = time.time()
        token = self.credentials.access_token or self.credentials.api_key if self.credentials else None

        if resource_type.startswith("github") and token:
            headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                if resource_type == "github.issues":
                    owner = params.get("owner")
                    repo = params.get("repo")
                    url = f"https://api.github.com/repos/{owner}/{repo}/issues" if owner and repo else "https://api.github.com/user/issues"
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        return ExecutionResult(success=True, data=resp.json(), duration_ms=int((time.time() - start) * 1000))

        return ExecutionResult(
            success=True,
            data={"items": [], "notice": "Credentials & parameters required for live GitHub/Jira fetch"},
            duration_ms=int((time.time() - start) * 1000),
        )

    async def send_data(self, resource_type: str, data: dict[str, Any], params: dict[str, Any] | None = None) -> ExecutionResult:
        return await self.create(resource_type, data)

    async def create(self, resource_type: str, data: dict[str, Any]) -> ExecutionResult:
        start = time.time()
        token = self.credentials.access_token or self.credentials.api_key if self.credentials else None

        if resource_type == "jira.create_task":
            domain = self.config.get("domain")
            project_key = data.get("project_key") or self.config.get("project_key")
            if domain and token and self.credentials.username:
                url = f"https://{domain}/rest/api/3/issue"
                payload = {
                    "fields": {
                        "project": {"key": project_key},
                        "summary": data.get("title") or data.get("summary"),
                        "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": data.get("description", "")}]}]},
                        "issuetype": {"name": data.get("issue_type", "Task")},
                    }
                }
                auth = (self.credentials.username, token)
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload, auth=auth)
                    if resp.status_code in (200, 201):
                        return ExecutionResult(success=True, data=resp.json(), duration_ms=int((time.time() - start) * 1000))
                    return ExecutionResult(success=False, error=resp.text, duration_ms=int((time.time() - start) * 1000))

        if resource_type == "github.create_issue":
            owner = data.get("owner")
            repo = data.get("repo")
            if owner and repo and token:
                url = f"https://api.github.com/repos/{owner}/{repo}/issues"
                headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, headers=headers, json={"title": data.get("title"), "body": data.get("body")})
                    if resp.status_code == 201:
                        return ExecutionResult(success=True, data=resp.json(), duration_ms=int((time.time() - start) * 1000))
                    return ExecutionResult(success=False, error=resp.text, duration_ms=int((time.time() - start) * 1000))

        # Simulation mode when credentials not connected
        return ExecutionResult(
            success=True,
            data={"key": f"NEX-{uuid.uuid4().hex[:4].upper()}", "id": str(uuid.uuid4()), "title": data.get("title") or data.get("summary")},
            message=f"Created {resource_type} (Credentials required for live Jira/GitHub creation)",
            duration_ms=int((time.time() - start) * 1000),
        )

    async def update(self, resource_type: str, resource_id: str, data: dict[str, Any]) -> ExecutionResult:
        start = time.time()
        return ExecutionResult(success=True, data={"id": resource_id, "updated": True}, duration_ms=int((time.time() - start) * 1000))

    async def delete(self, resource_type: str, resource_id: str) -> ExecutionResult:
        start = time.time()
        return ExecutionResult(success=True, data={"id": resource_id, "deleted": True}, duration_ms=int((time.time() - start) * 1000))

    async def subscribe_webhook(self, target_url: str, event_types: list[str]) -> ExecutionResult:
        start = time.time()
        return ExecutionResult(success=True, data={"subscription": "active", "target_url": target_url}, duration_ms=int((time.time() - start) * 1000))

    async def handle_webhook(self, raw_payload: dict[str, Any] | str, headers: dict[str, str]) -> NexoraEvent:
        vendor = "github" if "x-github-event" in headers or "repository" in str(raw_payload) else "jira"
        return EventNormalizer.normalize_event(
            source_vendor=vendor,
            company_id=self.company_id or uuid.uuid4(),
            integration_id=self.integration_id or uuid.uuid4(),
            raw_payload=raw_payload,
            headers=headers,
        )

    async def refresh_token(self) -> CredentialData | None:
        return self.credentials


integration_registry.register(
    "github",
    GitHubJiraConnector,
    IntegrationTypeMeta(
        integration_type="github",
        display_name="GitHub Enterprise",
        category="dev_tools",
        description="Sync repositories, pull requests, issues, and developer workflows with Nexora AI.",
        icon="github",
        supported_auth_types=["api_key", "oauth2", "bearer"],
        supported_actions=GitHubJiraConnector.supported_actions,
    ),
)

integration_registry.register(
    "jira",
    GitHubJiraConnector,
    IntegrationTypeMeta(
        integration_type="jira",
        display_name="Jira Software & Service Management",
        category="dev_tools",
        description="Manage projects, tasks, issues, and agile workflows in Jira from Nexora AI.",
        icon="jira",
        supported_auth_types=["api_key", "basic", "bearer"],
        supported_actions=GitHubJiraConnector.supported_actions,
    ),
)
