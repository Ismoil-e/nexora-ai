# Nexora AI — Platform Architecture & Implementation Roadmap

Nexora AI is an autonomous, multi-tenant Business Intelligence & Autonomous AI Assistant Platform designed for enterprise and SMB operational excellence.

---

## 1. System Vision & Architecture Mapping

```mermaid
graph TD
    User([User / Employee]) <--> WebUI[Unified Web Chat & Dashboard UI]
    WebUI <--> Gateway[FastAPI API Gateway]
    
    subgraph Central AI Brain Orchestrator
        Gateway <--> Router[Intent Router & Agent Manager]
        Router <--> AgentInv[Inventory Agent]
        Router <--> AgentSales[Sales & BI Agent]
        Router <--> AgentFin[Finance Agent]
        Router <--> AgentHR[HR & Task Agent]
        Router <--> AgentDoc[Document Intelligence Agent]
    end

    subgraph Data & RAG Engine
        AgentDoc <--> RAG[RAG Pipeline & Embeddings]
        RAG <--> VectorDB[(PostgreSQL + pgvector)]
        AgentSales <--> SQLAgent[Text-to-SQL Analytics Engine]
        SQLAgent <--> BizDB[(Business Data Store)]
    end

    subgraph Autonomous Proactive Engine
        Cron[RabbitMQ / Celery Workers] --> Monitor[Business Anomaly & Event Monitor]
        Monitor --> Notif[Notification Engine]
        Notif --> WebUI
    end
```

---

## 2. Core Functional Modules & Technical Implementation Plan

### Module 1: Document Intelligence Engine
- **Supported Formats**: PDF, DOCX, XLSX/XLS, PPTX, Images (OCR).
- **Capabilities**:
  - File parser service (`pypdf`, `python-docx`, `pandas`, `openpyxl`).
  - Text chunking & vector embedding generation (`text-embedding-3-small` / Gemini Embeddings).
  - Hybrid Search (`pgvector` cosine similarity + full-text search).
  - Document comparison & verification engine.

### Module 2: Business Analytics & Text-to-SQL Engine
- **Capabilities**:
  - Secure Text-to-SQL engine for business metrics (Sales, Inventory, Finance).
  - Trend detection & anomaly explanation ("Why sales dropped this month").
  - Automated chart and report generation (JSON chart spec for UI rendering).

### Module 3: Proactive Autonomous Monitoring Worker
- **Capabilities**:
  - Background cron jobs (`RabbitMQ` + `Celery`/`Asyncio Tasks`).
  - Stock level thresholds & inventory depletion speed forecasting.
  - Financial anomaly alerts & deadline tracking.
  - Push notifications via WebSockets & Notification API.

### Module 4: Adaptive Multi-Agent Orchestrator
- **Capabilities**:
  - Central Agent Router selecting specialized prompt personas and toolsets:
    1. **Inventory Assistant**
    2. **Sales Analytics Assistant**
    3. **Finance Assistant**
    4. **HR & Tasks Assistant**
    5. **Document Management Assistant**
    6. **Project Management Assistant**

---

## 3. Immediate Technical Implementation Milestones

- [x] **Phase 1: Foundation Clean Architecture** (FastAPI, Modular routers, Multi-tenant DB schema, OpenRouter/Gemini AI providers, Glassmorphism UI)
- [x] **Phase 1.5: AI Agent Framework** (Registry, Manager, lifecycle pipeline, default capability agents, Cognitive stubs, Celery agent worker)
- [x] **Phase 1.6: Workflow Automation Engine** (Workflow executor, action/trigger registries, approvals, Celery long-running jobs, REST APIs)
- [x] **Phase 2: Document Intelligence & RAG** (File parsers for PDF/DOCX/XLSX/CSV/images, Hybrid vector+full-text search, Entities & Knowledge Graph, Document Q&A, async Celery pipeline) — see [DOCUMENT_INTELLIGENCE.md](DOCUMENT_INTELLIGENCE.md)
- [x] **Phase 2.5: Enterprise Integration Hub** (Unified BaseConnector, OAuth2/Encrypted credentials, Webhook normalizer, Google/MS/Telegram/Slack/GitHub connectors) — see [ENTERPRISE_INTEGRATION_HUB.md](ENTERPRISE_INTEGRATION_HUB.md)
- [x] **Phase 3: Business Intelligence & Decision Engine** (KPI Engine, Trend & Anomaly Detection, Forecast Engine, Causal Insight Engine, Risk Scanner, Executive Summaries, Dynamic Dashboards) — see [BUSINESS_INTELLIGENCE.md](BUSINESS_INTELLIGENCE.md)
- [ ] **Phase 4: Proactive Autonomous Monitoring & Real-time SSE Stream** (Background periodic watcher, real-time WebSockets/SSE push)
- [ ] **Phase 5: Advanced Visual BI Analytics UI Components** (Interactive glassmorphism chart widgets)
