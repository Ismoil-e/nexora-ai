# Nexora AI — Business Intelligence & Decision Engine

The **Nexora AI Business Intelligence (BI) Engine** transforms raw multi-source enterprise data (PostgreSQL, Document Intelligence RAG, Second Brain memory, Knowledge Graph entities, Workflow runs, Tasks, and Integration Hub webhooks) into real-time decision intelligence, causal insights, predictive forecasts, automated executive summaries, and proactive alerts.

> Status: **Production-Ready & Fully Integrated**

---

## 1. High-Level Architecture

```
                                  MULTI-SOURCE DATA INGESTION
          ┌───────────────────────────────────┬──────────────────────────────────┐
          │  PostgreSQL Database              │  Document Intelligence RAG       │
          │  Knowledge Graph (Entities/Edges) │  Second Brain (Hybrid Memory)    │
          │  Workflow Executions & Approvals  │  Tasks, Chats, Notifications     │
          │  Enterprise Integration Connectors│  Excel / CSV / Structured Data   │
          └─────────────────┬─────────────────┴─────────────────┬────────────────┘
                            │                                   │
                            ▼                                   ▼
          ┌──────────────────────────────────────────────────────────────────────┐
          │                     NEXORA BI CORE ENGINES                           │
          │  ┌─────────────────────────┐      ┌───────────────────────────────┐  │
          │  │     KPI & Metrics       │      │        Trend & Anomaly        │  │
          │  │  (Calculation & Logs)   │      │ (Z-Score, Growth, Seasonality)│  │
          │  └────────────┬────────────┘      └───────────────┬───────────────┘  │
          │               │                                   │                  │
          │  ┌────────────▼────────────┐      ┌───────────────▼───────────────┐  │
          │  │      Insight Engine     │      │        Forecast Engine        │  │
          │  │  (Root Cause "Why", UZ) │      │ (Linear Trend, Moving Avg, CI)│  │
          │  └────────────┬────────────┘      └───────────────┬───────────────┘  │
          │               │                                   │                  │
          │  ┌────────────▼────────────┐      ┌───────────────▼───────────────┐  │
          │  │  Risk & Bottlenecks     │      │     Decision Recommendations  │  │
          │  │ (Deadlines, Approvals)  │      │(Actionable Prioritized Steps) │  │
          │  └────────────┬────────────┘      └───────────────┬───────────────┘  │
          │               │                                   │                  │
          │  ┌────────────▼────────────┐      ┌───────────────▼───────────────┐  │
          │  │   Alert Rule Engine     │      │   Executive Summary Engine    │  │
          │  │ (Threshold & Anomaly)   │      │(Role-tailored: CEO, CFO, COO) │  │
          │  └────────────┬────────────┘      └───────────────┬───────────────┘  │
          └───────────────┼───────────────────────────────────┼──────────────────┘
                          │                                   │
                          ▼                                   ▼
          ┌───────────────────────────────────┬──────────────────────────────────┐
          │ Dynamic Dashboard Engine (Widgets)│ Report Generator (MD, JSON, CSV) │
          │ AI Agent Tools (Analytics/Monitor)│ Workflow Actions (Celery Tasks)  │
          └───────────────────────────────────┴──────────────────────────────────┘
```

---

## 2. Core Functional Engines

### 1. KPI & Metrics Engine (`app/bi/core/kpi_engine.py`)
- **Tenant-isolated** metrics calculation and historical variance tracking.
- Standard default KPIs automatically seeded:
  - `TASK_COMPLETION_RATE`: Percentage of completed tasks vs total tasks.
  - `OVERDUE_TASKS_COUNT`: Uncompleted tasks past due date.
  - `PENDING_TASKS_COUNT`: Active tasks in progress or todo.
  - `DOCUMENT_PROCESSING_VOLUME`: Documents indexed and processed by Document Intelligence.
  - `AI_USAGE_MESSAGES`: AI assistant interaction volume across the organization.
  - `WORKFLOW_SUCCESS_RATE`: Reliability of automated workflows.
  - `ACTIVE_USERS_RATIO`: Employee engagement and platform adoption.
- **Custom KPIs**: Support for tenant-defined custom formula KPIs and connector metrics.
- **Statuses**: `healthy`, `warning`, `critical`, `unknown` with customizable target/warning/critical thresholds.

### 2. Trend & Anomaly Engine (`app/bi/core/trend_engine.py`)
- Calculates statistical moving averages, growth rate percentage (Period-over-Period), and direction (`growing`, `declining`, `stable`, `volatile`).
- Real-time **statistical outlier / anomaly detection** using configurable Standard Deviation ($\sigma$) Z-score thresholding.

### 3. Forecast Engine (`app/bi/core/forecast_engine.py`)
- Predictive forecasting for upcoming periods (e.g. Next 30 days, Next quarter) using:
  - **Least-Squares Linear Regression** ($y = a + bx$)
  - **Weighted Moving Average (WMA)**
  - Lower and upper confidence bounds ($CI_{95\%}$) and confidence scores ($0.0 \dots 1.0$).

### 4. Automated Insight & Causality Engine (`app/bi/core/insight_engine.py`)
- Automatically discovers patterns, KPI drops, and operational spikes.
- Crucially answers **"WHY did this happen?"** with causal explanations in Uzbek and English.
- Links insights to source entity types (`Task`, `Workflow`, `Document`, `Chat`).

### 5. Risk Detection & Decision Intelligence (`app/bi/core/risk_engine.py` & `recommendation_engine.py`)
- Scans the enterprise for operational hazards:
  - 3+ days overdue tasks
  - Stalled workflow approval gates (Human-in-the-loop bottlenecks)
  - Workflow step failures
  - Unindexed or pending documents
- Maps hazards into actionable, prioritized executive recommendations (`high`, `medium`, `low`).

### 6. Executive Summary & Report Generator (`app/bi/core/executive_summary_engine.py` & `report_generator.py`)
- Role-specific executive narrative generation:
  - **CEO**: Strategic high-level overview, health grade, critical risks, and priority directives.
  - **CFO**: Financial resource efficiency, ROI, and cost drivers.
  - **COO**: Operational velocity, bottlenecks, and workflow reliability.
  - **HR**: Team engagement, workload distribution, and task productivity.
- Multi-format report builder: Markdown, JSON, HTML, and CSV with source citations.

---

## 3. REST API Reference (`/api/v1/bi`)

All endpoints enforce multi-tenancy and RBAC via `company_id`.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/bi/overview` | High-level executive snapshot (health status, top KPIs, risks, insights). |
| `GET` | `/api/v1/bi/kpis` | List all configured tenant KPIs. |
| `POST` | `/api/v1/bi/kpis` | Create a new custom KPI definition. |
| `PUT` | `/api/v1/bi/kpis/{id}` | Update KPI target and alert thresholds. |
| `POST` | `/api/v1/bi/kpis/calculate` | Force real-time KPI recalculation and logging. |
| `GET` | `/api/v1/bi/kpis/{id}/history` | Retrieve historical timeseries logs for a KPI. |
| `GET` | `/api/v1/bi/dashboards` | List available tenant dashboards. |
| `POST` | `/api/v1/bi/dashboards` | Create a new customizable dashboard. |
| `GET` | `/api/v1/bi/dashboards/{slug}` | Get full dashboard structure and its widgets. |
| `POST` | `/api/v1/bi/dashboards/{id}/widgets` | Add a widget to an existing dashboard. |
| `GET` | `/api/v1/bi/insights` | Retrieve AI-generated insights with root-cause explanations. |
| `POST` | `/api/v1/bi/insights/generate` | Force automated insight discovery. |
| `POST` | `/api/v1/bi/insights/{id}/acknowledge` | Mark an insight as reviewed/acknowledged. |
| `GET` | `/api/v1/bi/risks` | Run operational risk scanner across tasks and workflows. |
| `GET` | `/api/v1/bi/trends` | Compute time-series trends and detect anomalies. |
| `POST` | `/api/v1/bi/forecasts` | Run predictive forecasting for workload/revenue/volume. |
| `POST` | `/api/v1/bi/executive-summary` | Generate role-tailored narrative brief. |
| `GET` | `/api/v1/bi/alerts/rules` | List configured threshold alert rules. |
| `POST` | `/api/v1/bi/alerts/rules` | Create a new threshold alert rule. |
| `GET` | `/api/v1/bi/alerts` | List triggered alerts. |
| `POST` | `/api/v1/bi/alerts/evaluate` | Evaluate rules against current KPI values. |
| `POST` | `/api/v1/reports/generate` | Generate automated executive report with citations. |

---

## 4. AI Agent & Workflow Engine Integration

### Agent Tools (`app/ai/agents/tools.py`)
- `query_company_kpis`: Allows `AnalyticsAgent` and `ChatAgent` to fetch real-time metrics.
- `get_business_insights`: Queries causal insights and explanations.
- `generate_executive_summary`: Produces leadership briefs directly within agent dialogues.
- `detect_operational_risks`: Enables `MonitoringAgent` to proactively diagnose bottlenecks.

### Workflow Actions (`app/workflows/actions/builtin.py`)
- `calculate_kpis`: Recalculates metrics within automated schedules.
- `generate_insights`: Triggers insight generation.
- `evaluate_alert_rules`: Evaluates alert rules in cron workflows.
- `generate_executive_summary`: Compiles executive summaries for periodic digests.
- `generate_bi_report`: Asynchronously creates and saves complete markdown/JSON reports.

---

## 5. Background Processing (`app/workers/bi_worker.py`)
- **Celery Tasks**:
  - `calculate_company_kpis_task(company_id)`
  - `generate_company_insights_task(company_id)`
  - `evaluate_alert_rules_task(company_id)`
  - `generate_scheduled_report_task(company_id, user_id, title, timeframe, format)`
