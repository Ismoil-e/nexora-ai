# Nexora AI — Agent Framework Architecture

**Status:** Implemented (extends existing Clean Architecture)  
**Depends on:** Cognitive Core design, Hybrid Memory design  
**Package:** `backend/app/agents/` + Cognitive stubs in `backend/app/cognitive/`

---

## 1. Purpose

The AI Agent Framework makes every Nexora capability an **independent, pluggable agent**.

Agents:

- Use Cognitive Core connectors (Context / Memory / Planning)
- Never access the database directly
- Communicate through services and interfaces
- Share one lifecycle pipeline
- Can be added without modifying existing agents (Open/Closed)

Existing pieces preserved:

- `app/ai/agents/agent_executor.py` (ReAct tool loop)
- `app/ai/agents/tools.py`
- `AgentService` CRUD + legacy execute path
- `/api/v1/agents` REST routes (extended, not replaced)

---

## 2. Architecture

```
API (/api/v1/agents/...)
  → AgentService
    → AgentManager
      → AgentRegistry
      → AgentPipelineExecutor
          → BaseAgent lifecycle
              initialize → validate → build_context → retrieve_memory
              → plan → execute → post_process → save_memory
              → publish_events → return_response
```

### Pipeline (product path)

```
Request → Auth → Permission → Company Context
 → Context Engine → Memory Engine → Knowledge Graph stub
 → Planning Engine → Selected Agent → AI Provider
 → Post Processing → Memory Update → Response
```

Long jobs (`async_mode` / large document intents) go to Celery (`app.workers.agent_worker`).

---

## 3. Core Components

| Component | Path | Role |
|-----------|------|------|
| Agent Interface | `app/agents/interfaces/base_agent.py` | Lifecycle contract |
| Registry | `app/agents/core/registry.py` | Pluggable catalog |
| Manager | `app/agents/core/manager.py` | Entry + RBAC gate |
| Context Builder | `app/agents/core/context_builder.py` | Builds `AgentContext` |
| Pipeline Executor | `app/agents/core/executor.py` | Runs lifecycle |
| Result Handler | `app/agents/core/result_handler.py` | Persists `AgentExecution` |
| Memory Connector | `app/agents/core/memory_connector.py` | Cognitive memory facade |
| Event Publisher | `app/agents/core/event_publisher.py` | Domain events |
| Cognitive stubs | `app/cognitive/services/engines.py` | Context/Memory/Planning ports |

---

## 4. Default Agents

Registered at startup via `bootstrap_agents()`:

- `document`
- `chat`
- `analytics`
- `monitoring`
- `task`
- `notification`
- `knowledge`
- `search`
- `planning`

Future agents: subclass `BaseAgent` / `CapabilityAgent`, then `agent_registry.register(MyAgent)` — no edits to existing agents required.

---

## 5. Integration Rules

1. Agents receive services via `initialize(services)`  
2. Document/Chat/Notification access goes through `DocumentService`, `ChatService`, `NotificationService`, `AIService`  
3. Memory retrieval goes through `AgentMemoryConnector` → `MemoryEngine`  
4. Legacy ReAct tools remain available via `execute_with_tools()` for operational agents  
5. Company `Agent` rows may bind `agent_key` to a framework agent  

---

## 6. Database

Migration `004_agent_framework`:

- Extends `agents`: `agent_key`, `agent_type`, `version`
- Extends `agent_executions`: `company_id`, `agent_key`, `request_id`, `stage`, `context_snapshot`, `async_task_id`
- Adds: `agent_configurations`, `agent_logs`, `agent_memory_references`, `agent_permissions`

Does not duplicate unrelated domain models.

---

## 7. API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/agents/framework/catalog` | Registered agents |
| POST | `/api/v1/agents/framework/{agent_key}/run` | Framework pipeline run |
| POST | `/api/v1/agents` | Create company agent (unchanged+) |
| GET | `/api/v1/agents` | List |
| POST | `/api/v1/agents/{id}/execute` | Legacy path; uses framework if `agent_key` set |
| PUT/DELETE | `/api/v1/agents/{id}` | Unchanged behavior |

Auth: JWT + company scope via existing deps.

---

## 8. Background Tasks

Celery task: `agents.run_agent_job` in `app/workers/agent_worker.py`  
Included in `celery_app` includes list.

Use for:

- Large document analysis
- Heavy knowledge indexing orchestration
- Async agent runs (`async_mode=true`)

---

## 9. Future Improvements

- Full Hybrid Memory channel fusion inside `MemoryEngine`
- Real Knowledge Graph / Timeline / Decision connectors
- Stronger RBAC seeding for `agent.*.execute` permissions
- Streaming SSE responses per agent
- Per-tenant agent marketplace / versioning UI
- Extract agents to microservices behind the same interfaces

---

## 10. Compatibility

- Existing ReAct executor kept
- Existing agent CRUD kept
- Existing `/execute` kept
- New framework routes added under `/framework/*`
