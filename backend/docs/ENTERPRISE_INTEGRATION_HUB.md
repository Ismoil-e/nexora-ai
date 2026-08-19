# Nexora AI Enterprise Integration Hub Architecture & Documentation

## Overview

The **Nexora AI Enterprise Integration Hub** serves as the central gateway connecting external enterprise systems with Nexora AI's Cognitive Core, AI Agents, Workflow Automation Engine, and Second Brain (Hybrid Memory & Knowledge Graph).

```
External System (Google, Microsoft, Telegram, Slack, Jira, GitHub, ERP, Database)
        ↓
Integration Hub Gateway
        ↓
Nexora Core API / Services
        ↓
Context / Memory / Knowledge Graph (Second Brain)
        ↓
AI Agent Framework
        ↓
Workflow Automation Engine
        ↓
Integration Hub Connector
        ↓
External System Output
```

---

## Key Architectural Components

### 1. Unified Connector Architecture (`BaseConnector`)
Every external integration implements the unified `BaseConnector` interface:
* `connect()` / `disconnect()`: Session and connection lifecycle.
* `authenticate()` / `validate_credentials()`: Credential validation.
* `health_check()`: Real-time probes returning latency and health state (`healthy`, `degraded`, `unhealthy`).
* `fetch_data()` / `send_data()`: Data exchange.
* `create()` / `update()` / `delete()`: Resource CRUD operations.
* `subscribe_webhook()` / `handle_webhook()`: Webhook registration and payload normalization.
* `refresh_token()`: OAuth2 token refresh workflows.

### 2. Supported Connectors
* **Google Workspace**: Google Drive, Google Docs, Google Sheets, Gmail, Google Calendar.
* **Microsoft 365**: OneDrive, Word, Excel, Outlook, Calendar.
* **Telegram**: Telegram Bot API, channels, group notifications, inline AI responses.
* **Slack & Discord**: Webhooks, bot messages, channel subscriptions.
* **GitHub & Jira**: Repositories, issues, pull requests, agile boards, developer workflows.
* **ERP & CRM**: Odoo, SAP, Salesforce, HubSpot, generic ERP/CRM APIs.
* **Database Gateway**: PostgreSQL, MySQL, SQL Server dynamic query executor with tenant boundary isolation.
* **Generic REST & Webhooks**: Arbitrary REST APIs with customizable authentication (Bearer, API Key, Basic, OAuth2).
* **SFTP & MQTT**: Secure file transfers and industrial IoT streaming.

### 3. Credential Security & Encryption at Rest
Credentials are stored encrypted at rest using **Fernet AES-256 symmetric encryption** derived from `SECRET_KEY` / `ENCRYPTION_KEY`.
Secrets (passwords, tokens, client secrets) are never exposed via REST API responses.

### 4. Event Normalization (`NexoraEvent`)
Vendor-specific webhook events are automatically translated into a unified `NexoraEvent` structure:
```json
{
  "event_id": "tg_101",
  "company_id": "...",
  "integration_id": "...",
  "source_vendor": "telegram",
  "event_type": "message.received",
  "resource_type": "chat_message",
  "title": "Telegram message from Ismoil",
  "content_summary": "Hello Nexora AI",
  "data": { ... },
  "is_important": true,
  "requires_memory_ingestion": true
}
```

### 5. Second Brain (Memory Integration)
Important external events (`requires_memory_ingestion: true`) pass through `IntegrationMemoryRouter` to index raw text into the vector knowledge base (`DocumentService` with HNSW hybrid search) and link entities to Second Brain memory without manual user copy-pasting.

### 6. AI Agent & Workflow Engine Integration
* **AI Agents** execute integration capabilities via `ExecuteIntegrationActionTool`.
* **Workflow Engine** invokes external actions using `ExecuteIntegrationAction` built-in step.

### 7. Multi-Tenancy & Governance
* All integration records (`Integration`, `IntegrationCredential`, `WebhookSubscription`, `IntegrationEvent`, `IntegrationExecution`, `IntegrationHealth`) carry a non-null `company_id` foreign key.
* Strict tenant boundary isolation enforces that Tenant A can never read, invoke, or inspect Tenant B integrations.

---

## API Endpoints (`/api/v1/integrations`)

* `GET /api/v1/integrations/catalog`: List available connector types and metadata.
* `GET /api/v1/integrations`: List configured integrations for tenant.
* `POST /api/v1/integrations`: Connect a new integration.
* `GET /api/v1/integrations/{id}`: Get integration details.
* `POST /api/v1/integrations/{id}/test`: Health check probe.
* `POST /api/v1/integrations/{id}/execute`: Direct connector action execution.
* `POST /api/v1/integrations/webhooks/incoming/{vendor}/{integration_id}`: Public inbound webhook listener.
