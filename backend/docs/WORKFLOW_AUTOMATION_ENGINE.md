# Nexora AI — Workflow Automation Engine

**Status:** Implemented (extends existing Clean Architecture)  
**Package:** `backend/app/workflows/`  
**Integrates with:** Agent Framework, Cognitive stubs, Documents, Notifications, Celery

---

## 1. Purpose

Nexora must not only answer questions — it must **perform work**.

```
Trigger → Auth → Permissions → Context → Planning
 → Workflow Builder/Validator → Action Executor
 → Memory Update → Notifications → Audit Log
```

---

## 2. Components

| Component | Location |
|-----------|----------|
| Workflow Engine (executor) | `app/workflows/core/executor.py` |
| Workflow / Action / Trigger Registry | `app/workflows/core/registry.py` |
| Builder + Validator | `app/workflows/core/builder.py` |
| Condition / Approval / Retry | `app/workflows/core/condition.py` |
| Scheduler helper | `app/workflows/core/scheduler.py` |
| Built-in Actions | `app/workflows/actions/builtin.py` |
| Templates | `app/workflows/definitions/templates.py` |
| Service | `app/services/workflow_service.py` |
| Celery worker | `app/workers/workflow_worker.py` |

---

## 3. Supported workflow types

manual, scheduled, event, approval, ai_generated, multi_step, long_running, background

## 4. Built-in actions (22+)

read_documents, analyze_excel, generate_report, generate_word_document, generate_pdf_report,  
read_database, update_database, call_external_api, send_email, send_telegram, create_notification,  
generate_dashboard, generate_summary, create_task, assign_task, schedule_meeting, update_memory,  
trigger_ai_agent, run_ocr, generate_embeddings, request_approval, execute_future_plugin

Future plugins register into `ActionRegistry` without changing existing actions.

## 5. Triggers

user_request, api, webhook, cron, db_event, file_upload, document_created,  
task_completed, meeting_finished, ai_decision, iot_event

## 6. API (`/api/v1/workflows`)

- `GET /catalog`
- `POST /templates/install`
- `POST /` create
- `GET /` list
- `GET /{id}` detail
- `PUT /{id}` update
- `DELETE /{id}` soft delete
- `POST /{id}/execute`
- `POST /execute-by-slug`
- `POST /executions/{id}/pause`
- `POST /executions/{id}/resume`
- `GET /{id}/history`
- `GET /executions/{id}/status`
- `GET /executions/{id}/logs`

Auth: JWT + company isolation via existing deps. Events published to `event_bus` for audit.

## 7. Database (migration 005)

workflows, workflow_steps, workflow_actions, workflow_triggers, workflow_schedules,  
workflow_executions, workflow_history, workflow_logs, workflow_approvals, workflow_conditions

## 8. Execution notes

- Long-running / background workflows offload to Celery (`workflows.run_workflow_job`)
- Approval steps set status `waiting_approval`; resume continues from next step
- Conditions can skip steps; retries honor `on_failure=retry`
- Actions use injected services (Document/Notification/AI/Agent/Memory) — not ad-hoc cross-tenant queries

## 9. Default templates

- `document-ingest`
- `weekly-summary-report`
- `task-completion-followup`
- `ai-assisted-planning`
- `manual-knowledge-search`

Install via `POST /api/v1/workflows/templates/install`.

## 10. Future improvements

- Full Celery Beat cron consumer for due schedules
- Real Word/PDF generation via python-docx / weasyprint + MinIO
- Visual workflow editor in Admin/Web
- Saga compensation across failing multi-step flows
- Native webhook signature verification endpoint
- Stronger RBAC permission codes per action category
