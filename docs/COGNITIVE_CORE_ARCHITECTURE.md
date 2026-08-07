# Nexora AI — Cognitive Core Architecture

**Status:** Design Specification (No Implementation)  
**Audience:** Principal / Staff Engineers, Platform Architects  
**Scope:** Extend the existing monorepo; do not replace FastAPI, auth, RBAC, multi-tenant, AI providers, documents, chat, workers, or storage.

---

## 1. Purpose of the Cognitive Core

The Cognitive Core is the **organizational intelligence layer** of Nexora AI.

It is not a chatbot wrapper. It is not a single LLM call. It is the platform subsystem that:

- Knows **who** is asking (identity, role, permissions)
- Knows **where** they operate (company, department, project)
- Knows **what** the organization already knows (memory, documents, graph)
- Knows **when** things happened and what is due (timeline)
- Knows **why** prior choices were made (decision memory)
- Decides **how** to think before answering (reasoning)
- Decides **what to do next** (planning)
- Updates organizational memory after every interaction

Every future AI module (Document Intelligence, BI Agents, Monitoring, HR, Finance, Workflow) must depend on the Cognitive Core.  
Every AI response must pass through it.

### One-line definition

> Cognitive Core = Identity-aware, permission-bounded, context-assembled, relationship-aware, time-aware, decision-aware reasoning and planning layer that sits between product APIs and AI providers.

---

## 2. Why It Is Necessary

### 2.1 Failure mode of traditional AI in SaaS

```
Question → LLM → Answer
```

This fails in enterprise multi-tenant products because:

| Gap | Business risk |
|-----|---------------|
| No identity/permission gate | Data leakage across tenants/roles |
| No company/project context | Generic answers, wrong KPIs, wrong policies |
| No persistent memory | User repeats context every session |
| No relationships | AI cannot connect contract → invoice → task |
| No timeline | Cannot reason about “last month vs this month” |
| No decision memory | Cannot explain approvals or policy changes |
| Direct LLM coupling | Provider swaps break product logic |
| No post-answer writeback | Organization does not get smarter over time |

### 2.2 What Nexora already has (do not redesign)

- FastAPI gateway + modular routers
- JWT auth + RBAC + multi-tenant `company_id`
- AI Provider Pattern (OpenRouter / Gemini / OpenAI)
- Document module + OCR + embedding pipeline + pgvector
- Chat module
- Celery / Redis workers
- MinIO storage
- Next.js web + admin

### 2.3 What is missing (the gap Cognitive Core fills)

Existing pieces are **capabilities**. Cognitive Core turns them into **organizational cognition**.

- Documents are stored → Memory Engine makes them recallable under policy
- Chat exists → Context Engine scopes every turn
- Embeddings exist → Knowledge Graph adds structure beyond vectors
- Workers exist → Timeline + Decision engines create temporal and causal intelligence
- Agents stubs exist → Reasoning + Planning engines become the shared brain they call

Without Cognitive Core, each new AI feature invents its own context assembly, permission checks, and memory writes → inconsistency, security drift, and duplicated logic.

---

## 3. Position in the Existing Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Apps: Web / Admin / Mobile                                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│ API Gateway (FastAPI)                                        │
│ Auth (JWT) · RBAC · Multi-tenant isolation                   │
│ Existing routers: chat, documents, users, tasks, ...         │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│ COGNITIVE CORE (new intelligence layer)                      │
│ Orchestrator + 7 Engines                                     │
└─────────┬─────────────────┬─────────────────┬───────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
   AI Providers      Domain Services     Data Plane
   OpenRouter        Documents/Chat      PostgreSQL
   Gemini            Tasks/Users         pgvector
   OpenAI            Notifications       Redis
                     Agents              MinIO / Celery
```

**Rule:** Product routers do not call LLM providers directly for intelligent responses. They call `CognitiveOrchestrator`. Providers remain behind the existing Provider Pattern.

---

## 4. Design Principles

1. **Extend, don’t replace** — reuse auth, RBAC, tenants, providers, documents, embeddings, workers.
2. **Modular engines** — each engine is independently deployable later as a microservice.
3. **Interface-first** — engines expose ports/interfaces; implementations are swappable.
4. **Service mediation** — engines never import each other’s internals; they talk via contracts + events.
5. **Tenant hard boundary** — every read/write is scoped by `company_id` (+ RLS where enabled).
6. **Permission before cognition** — no memory/graph/timeline retrieval before authorization.
7. **Reason before generate** — LLM is the last step, not the first.
8. **Write after generate** — every response may update memory, timeline, decisions, graph.
9. **Observable** — every pipeline stage emits structured events for audit and debugging.
10. **Idempotent side effects** — memory/graph updates must be safely retryable via workers.

---

## 5. Engine Designs

### 5.1 Memory Engine

**Purpose:** Persistent long-term organizational memory.

**Stores (logical memory types):**

| Memory type | Examples | Source systems |
|-------------|----------|----------------|
| Episodic | chats, meetings, incidents | chat, meetings, audit |
| Semantic | policies, business rules, definitions | documents, settings |
| Procedural | workflows, SOPs, playbooks | documents, tasks |
| Working | active conversation buffer | chat session / Redis |
| Artifact | reports, contracts, invoices | documents, reports |
| Entity | users, departments, projects | identity domain |
| Decision | approvals, conclusions | Decision Engine writeback |

**Responsibilities:**

- Ingest memory units from domain events
- Normalize, classify, chunk, embed (reuse embedding pipeline)
- Retrieve by hybrid search (vector + FTS + filters)
- Rank by relevance, recency, authority, permission
- Forget / archive under retention policy
- Never return memories outside caller ACL

**Interfaces (conceptual):**

- `ingest(memory_unit)`
- `retrieve(query, context_frame, limits) → MemoryBundle`
- `upsert_summary(scope, summary)`
- `invalidate(scope | entity_refs)`
- `get_by_refs(entity_refs) → MemoryBundle`

**Storage strategy:**

- Hot working memory: Redis (TTL)
- Durable memory records: PostgreSQL
- Vectors: pgvector (existing)
- Large blobs: MinIO (existing documents)

**Non-goals:** Memory Engine does not decide answers; it supplies evidence.

---

### 5.2 Context Engine

**Purpose:** Build the **Context Frame** for every request — the minimal, authoritative snapshot of “who/where/what is active now”.

**Automatically resolves:**

- Current company
- Current user + roles + permissions
- Current department (if assigned / selected)
- Current project (if in scope / selected)
- Current workflow / active task (if any)
- Current conversation + recent turns
- Current active documents (attached, pinned, recently referenced)
- Locale, timezone, UI surface (web/admin/mobile)

**Responsibilities:**

- Assemble `ContextFrame` from auth deps + request payload + session state
- Enforce permission projection (`allowed_actions`, `data_scopes`)
- Detect missing context (“project not selected but required”)
- Compress context for token budgets (summaries, top-k refs)
- Cache stable slices (company policies) with invalidation hooks

**Interfaces:**

- `build(request_identity, request_hints) → ContextFrame`
- `refresh(frame_id) → ContextFrame`
- `validate(frame) → ContextValidation`

**Output contract: `ContextFrame`**

```
ContextFrame
├── tenant: company_id, plan, locale, timezone
├── actor: user_id, roles, permissions, department_id?
├── scope: project_id?, workflow_id?, conversation_id?
├── active_artifacts: document_ids[], task_ids[]
├── policy_snapshot: retention, data_access_rules
└── budget: max_tokens_context, max_memory_items
```

**Non-goals:** Context Engine does not search the whole graph; it defines the lens.

---

### 5.3 Knowledge Graph Engine

**Purpose:** Represent and query **relationships** between organizational objects.

**Node types (initial):**

`User`, `Department`, `Project`, `Client`, `Meeting`, `Contract`, `Invoice`, `Document`, `Task`, `Decision`, `Report`, `Policy`, `Dashboard`, `Conversation`, `MemoryUnit`

**Edge types (initial):**

`MEMBER_OF`, `OWNS`, `ASSIGNED_TO`, `RELATED_TO`, `DERIVED_FROM`, `APPROVED_BY`, `RESULTED_IN`, `REFERENCES`, `SUPERSEDES`, `DEPENDS_ON`, `BELONGS_TO_PROJECT`, `ATTACHED_TO`

**Example chain:**

```
User → MEMBER_OF → Department
     → ASSIGNED_TO → Project
     → RELATED_TO → Client
     → PARTICIPATED_IN → Meeting
     → PRODUCED → Contract
     → BILLED_AS → Invoice
     → REFERENCES → Document
     → CREATED → Task
     → RESULTED_IN → Decision
     → VISIBLE_ON → Dashboard
```

**Responsibilities:**

- Upsert nodes/edges from domain events (not only from LLM extraction)
- Query neighborhood / path / constrained subgraph under ACL
- Support “why are these related?” explanations via edge metadata
- Optionally enrich edges with LLM extraction jobs (async, reviewable)

**Storage recommendation (phase-aligned):**

- **Phase A (extend current stack):** PostgreSQL graph tables (`kg_nodes`, `kg_edges`) + recursive CTEs / adjacency queries
- **Phase B (scale):** optional Neo4j / Neptune adapter behind the same interface

**Interfaces:**

- `upsert_node(node)` / `upsert_edge(edge)`
- `neighbors(node_ref, filters, depth) → Subgraph`
- `path(from_ref, to_ref, max_depth) → Path[]`
- `subgraph_for_context(frame, seed_refs) → SubgraphBundle`

**Non-goals:** Graph is not a document store; payloads live in domain tables / MinIO.

---

### 5.4 Timeline Engine

**Purpose:** Give AI a first-class model of **time**.

**Understands:**

- Absolute time (`2026-07-01`)
- Relative time (“yesterday”, “last month”, “last meeting”)
- Version time (“previous contract revision”)
- Deadline time (“due Friday”, “overdue”)
- Comparative windows (“this quarter vs last quarter”)

**Event classes:**

- Domain events (document uploaded, task completed)
- Conversation events (key facts stated)
- Decision events (approved/rejected)
- Calendar-like events (meetings, deadlines)
- System events (policy changed, role updated)

**Responsibilities:**

- Normalize timestamps to company timezone
- Resolve temporal expressions against `ContextFrame`
- Fetch “last X”, “next X”, range queries
- Support historical comparison packages for Reasoning Engine
- Feed deadline monitors (reuse/extend existing timeline stubs + Celery)

**Interfaces:**

- `resolve_expression(expr, frame) → TimeWindow`
- `history(entity_ref | scope, window) → TimelineSlice`
- `upcoming(scope, window) → TimelineSlice`
- `compare(metric_or_entity, window_a, window_b) → ComparisonPack`
- `append_event(timeline_event)`

**Non-goals:** Timeline is not a full calendar product; it is temporal intelligence for AI.

---

### 5.5 Decision Engine

**Purpose:** Capture and retrieve **decisions as first-class knowledge**.

**Stores:**

- Approvals / rejections
- Management decisions
- Policy changes
- Meeting conclusions
- Reasons (rationale)
- Consequences (follow-up tasks, impacted entities)
- Alternatives considered (optional)
- Decision owner + timestamp + authority level

**Responsibilities:**

- Record decisions from UI actions, meeting summaries, agent proposals
- Link decisions to graph nodes (project, contract, policy…)
- Answer “why was this decided?” with evidence pack
- Detect conflicts (new decision contradicts active policy)
- Supply Decision Memory to Reasoning Engine

**Interfaces:**

- `record(decision_input) → DecisionRecord`
- `explain(decision_id) → DecisionExplanation`
- `find_relevant(frame, query) → DecisionBundle`
- `detect_conflicts(candidate | new_policy) → ConflictReport`

**Non-goals:** Decision Engine does not replace human approval workflows; it remembers and reasons over them.

---

### 5.6 Reasoning Engine

**Purpose:** Force structured thinking **before** any provider call.

**Mandatory stages (never skip):**

1. Collect Context (`ContextFrame`)
2. Collect Memory (`MemoryBundle`)
3. Collect Relationships (`SubgraphBundle`)
4. Collect Timeline (`TimelineSlice` / comparisons)
5. Collect Policies & Decisions (`DecisionBundle` + policy snapshot)
6. Think (compose `ReasoningTrace`)
7. Then answer (hand off to Planning and/or Provider)

**Responsibilities:**

- Build evidence pack with citations (doc chunk ids, decision ids, graph edges)
- Detect insufficient information → ask clarifying questions / mark gaps
- Choose response mode: answer / plan / refuse / escalate
- Produce `ReasoningTrace` for audit (stored, redacted where needed)
- Apply safety/policy constraints before generation

**Interfaces:**

- `reason(frame, user_intent) → ReasoningResult`
- `evaluate_sufficiency(evidence) → SufficiencyReport`

**`ReasoningResult` includes:**

- intent classification
- evidence refs
- assumptions
- risks / conflicts
- recommended generation strategy
- whether Planning Engine must run

**Non-goals:** Reasoning Engine may use a small model for planning traces later, but must not bypass evidence collection.

---

### 5.7 Planning Engine

**Purpose:** Turn intelligence into **action**, not only text.

**Capabilities:**

- Create / update task plans
- Recommend next actions
- Predict problems (missing docs, overdue deps, policy conflicts)
- Detect missing information
- Propose tool/agent calls (document Q&A, SQL analytics, notifications)
- Produce ordered execution plans with owners and deadlines

**Responsibilities:**

- Convert `ReasoningResult` into `ActionPlan`
- Validate actions against permissions
- Optionally execute safe actions via existing services/workers
- Return human-readable plan + machine-executable steps

**Interfaces:**

- `plan(reasoning_result, frame) → ActionPlan`
- `validate(plan, permissions) → PlanValidation`
- `execute_safe_steps(plan) → ExecutionReport` (async via Celery where heavy)

**Non-goals:** Planning does not own long-running workflow orchestration forever; it emits plans that automation/workers can run.

---

## 6. Cognitive Orchestrator (the conductor)

Engines are independent. The **Cognitive Orchestrator** is the only component product services call for “intelligent response” flows.

### Orchestrator responsibilities

1. Accept `CognitiveRequest` from ChatService / Agents / future modules
2. Call Context Engine first
3. Fail closed on permission errors
4. Fan-out retrieval to Memory / Graph / Timeline / Decision (parallel where safe)
5. Invoke Reasoning Engine
6. Invoke Planning Engine when needed
7. Call AI Provider via existing `AIService` / Provider Pattern
8. Format response + citations
9. Emit writeback events (memory update, timeline event, graph edges, decision candidates)
10. Persist `CognitiveRun` audit record

### Orchestrator must not

- Contain business SQL for every domain
- Bypass RBAC
- Call providers before reasoning for normal Q&A
- Tightly couple to a single engine implementation

---

## 7. Communication Between Engines

### 7.1 Sync vs async

| Interaction | Mode | Why |
|-------------|------|-----|
| Context build | Sync | Needed before everything |
| Memory/Graph/Timeline/Decision retrieve | Sync (parallel) | Needed for reasoning latency budget |
| Reasoning / Planning | Sync | Needed for response |
| Provider generation | Sync/stream | User-facing |
| Memory writeback, graph enrichment, embedding | Async (Celery/Redis) | Heavy, retryable |
| Decision conflict scans, timeline monitors | Async | Background intelligence |

### 7.2 Contracts (shared DTOs)

All engines exchange **immutable bundles**:

- `ContextFrame`
- `MemoryBundle`
- `SubgraphBundle`
- `TimelineSlice`
- `DecisionBundle`
- `ReasoningResult`
- `ActionPlan`
- `CognitiveResponse`

Engines depend on interfaces + DTOs, not on each other’s repositories.

### 7.3 Event bus (within current stack)

Use Redis + Celery (already present) as the pragmatic event/work queue.

**Domain events (examples):**

- `document.processed`
- `chat.message.created`
- `task.completed`
- `decision.recorded`
- `policy.updated`
- `project.member.added`
- `cognitive.run.completed`
- `memory.ingest.requested`
- `kg.enrichment.requested`

Later, RabbitMQ/Kafka can replace Redis streams without changing engine interfaces.

### 7.4 Interaction map

```
ContextEngine ──────────────► provides ContextFrame to all
        │
        ▼
MemoryEngine ◄──────────────► KnowledgeGraphEngine
        │                         │
        ▼                         ▼
TimelineEngine ◄────────────► DecisionEngine
        │                         │
        └──────────┬──────────────┘
                   ▼
            ReasoningEngine
                   │
                   ▼
             PlanningEngine
                   │
                   ▼
           AI Provider Layer
                   │
                   ▼
         Writeback (async events)
         → Memory / Graph / Timeline / Decision
```

---

## 8. Folder Structure (extension of current monorepo)

Place Cognitive Core under the clean architecture app (`backend/app`), and keep existing stub folders as adapters/legacy bridges until migrated.

```
backend/
├── app/
│   ├── api/                          # existing routers (call orchestrator)
│   ├── services/                     # existing domain services
│   │   ├── chat_service.py           # delegates intelligent turns to Cognitive Core
│   │   ├── document_service.py
│   │   ├── agent_service.py
│   │   └── ...
│   ├── ai/                           # existing providers (unchanged pattern)
│   │   ├── providers/
│   │   ├── embeddings.py
│   │   └── agents/
│   │
│   ├── cognitive/                    # ★ NEW — Cognitive Core
│   │   ├── __init__.py
│   │   ├── orchestrator.py           # CognitiveOrchestrator
│   │   ├── contracts/                # shared DTOs / enums
│   │   │   ├── context_frame.py
│   │   │   ├── memory_bundle.py
│   │   │   ├── subgraph_bundle.py
│   │   │   ├── timeline_slice.py
│   │   │   ├── decision_bundle.py
│   │   │   ├── reasoning_result.py
│   │   │   ├── action_plan.py
│   │   │   └── cognitive_request.py
│   │   ├── interfaces/               # ports (ABC / Protocol)
│   │   │   ├── memory_port.py
│   │   │   ├── context_port.py
│   │   │   ├── graph_port.py
│   │   │   ├── timeline_port.py
│   │   │   ├── decision_port.py
│   │   │   ├── reasoning_port.py
│   │   │   └── planning_port.py
│   │   ├── engines/
│   │   │   ├── memory/
│   │   │   │   ├── service.py
│   │   │   │   ├── ingest.py
│   │   │   │   ├── retrieve.py
│   │   │   │   └── ranker.py
│   │   │   ├── context/
│   │   │   │   ├── service.py
│   │   │   │   ├── assembler.py
│   │   │   │   └── validators.py
│   │   │   ├── graph/
│   │   │   │   ├── service.py
│   │   │   │   ├── upsert.py
│   │   │   │   └── query.py
│   │   │   ├── timeline/
│   │   │   │   ├── service.py
│   │   │   │   ├── resolver.py
│   │   │   │   └── compare.py
│   │   │   ├── decision/
│   │   │   │   ├── service.py
│   │   │   │   ├── record.py
│   │   │   │   └── explain.py
│   │   │   ├── reasoning/
│   │   │   │   ├── service.py
│   │   │   │   ├── evidence.py
│   │   │   │   └── trace.py
│   │   │   └── planning/
│   │   │       ├── service.py
│   │   │       ├── planner.py
│   │   │       └── validators.py
│   │   ├── adapters/                 # infra adapters (SQL, Redis, providers)
│   │   │   ├── memory_repository.py
│   │   │   ├── graph_repository.py
│   │   │   ├── timeline_repository.py
│   │   │   ├── decision_repository.py
│   │   │   └── llm_adapter.py        # wraps existing AIService
│   │   └── events/
│   │       ├── publishers.py
│   │       └── handlers.py
│   │
│   ├── models/                       # add cognitive tables here
│   ├── repositories/
│   ├── workers/                      # extend Celery tasks for writeback
│   └── ...
│
├── services/                         # existing stubs (memory/timeline/...)
│   ├── memory/                       # bridge → app.cognitive.engines.memory
│   ├── timeline/
│   └── knowledge/
│
└── migrations/versions/              # new Alembic revisions for cognitive schema
```

**Frontend impact (later, not this design phase):** citation panels, “why” explanations, plan/task proposals — still consume existing APIs extended with cognitive metadata.

---

## 9. Service Interactions

### 9.1 Who calls whom

```
ChatService / AgentService / Document Q&A endpoint
        │
        ▼
CognitiveOrchestrator
        │
        ├─► ContextEngine.build()
        ├─► MemoryEngine.retrieve()          ─┐
        ├─► KnowledgeGraph.neighbors()       ─┼─ parallel
        ├─► TimelineEngine.history/upcoming()─┤
        ├─► DecisionEngine.find_relevant()   ─┘
        ├─► ReasoningEngine.reason()
        ├─► PlanningEngine.plan()            (conditional)
        ├─► AIService.generate()             (existing provider pattern)
        └─► EventPublisher.writeback()       (async)
                 │
                 ├─► MemoryEngine.ingest()
                 ├─► GraphEngine.upsert_*()
                 ├─► TimelineEngine.append_event()
                 └─► DecisionEngine.record() (if decision detected)
```

### 9.2 Existing services remain source of truth for domain CRUD

| Domain | Source of truth | Cognitive role |
|--------|-----------------|----------------|
| Users / Roles | user/auth services | Context identity + ACL |
| Documents | document_service + MinIO + workers | Memory artifacts + graph nodes |
| Chat | chat_service | Conversation context + episodic memory |
| Tasks | task services | Planning execution targets |
| Notifications | notification_service | Plan side-effects |
| Embeddings | embedding_worker / ai embeddings | Memory retrieval substrate |

Cognitive Core **indexes and relates**; it does not fork a second document/task database.

---

## 10. Database Changes

Extend PostgreSQL (multi-tenant). Prefer new tables over overloading unrelated models. Keep `company_id` on every tenant-owned row. Align with existing RLS direction.

### 10.1 New / extended tables (logical schema)

#### `memory_units`
- `id`, `company_id`
- `memory_type` (episodic|semantic|procedural|artifact|entity_summary|decision_link)
- `source_type`, `source_id` (polymorphic ref)
- `title`, `content`, `summary`
- `embedding` / link to chunk embeddings
- `importance`, `confidence`
- `department_id?`, `project_id?`
- `created_by`, `occurred_at`, `expires_at?`
- `acl_level` / visibility tags
- indexes: company + time, company + source, vector index

#### `memory_links`
- connect memory units to entities (`entity_type`, `entity_id`, `relation`)

#### `kg_nodes`
- `id`, `company_id`
- `node_type`, `entity_type`, `entity_id` (unique per company)
- `label`, `properties` (JSONB)
- `created_at`, `updated_at`

#### `kg_edges`
- `id`, `company_id`
- `from_node_id`, `to_node_id`
- `edge_type`
- `weight`, `properties` (JSONB)
- `valid_from`, `valid_to?`
- `created_by_run_id?`
- unique constraint on (`company_id`, `from`, `to`, `edge_type`, `valid_from`)

#### `timeline_events`
- `id`, `company_id`
- `event_type`, `title`, `description`
- `entity_type`, `entity_id`
- `occurred_at`, `due_at?`
- `severity`, `properties` (JSONB)
- `source` (system|user|ai)
- indexes: company + occurred_at, company + due_at

#### `decisions`
- `id`, `company_id`
- `title`, `status` (proposed|approved|rejected|superseded)
- `decision_type`
- `rationale`, `consequences`
- `decided_by`, `decided_at`
- `department_id?`, `project_id?`
- `policy_refs` / `evidence_refs` (JSONB)
- `supersedes_decision_id?`

#### `decision_links`
- link decisions to tasks/documents/projects/clients

#### `cognitive_runs`
- audit of each orchestration
- `id`, `company_id`, `user_id`, `conversation_id?`
- `request_hash`, `intent`
- `context_snapshot` (redacted JSONB)
- `evidence_refs`, `reasoning_trace` (restricted access)
- `plan_json?`, `provider`, `model`
- `latency_ms`, `status`, `error?`
- `created_at`

#### `action_plans` (optional first-class)
- `id`, `company_id`, `cognitive_run_id`
- `status`, `steps` (JSONB), `created_by`

### 10.2 Existing tables to extend (minimal)

- `documents` / `document_chunks` — already feed Memory + Graph (add optional `kg_node_id`)
- `chats` / messages — link to `cognitive_runs`
- `tasks` — allow creation from `action_plans`
- `audit_logs` — mirror high-severity cognitive denials
- company org model — ensure `departments` / `projects` exist or are added as first-class entities if missing

### 10.3 Indexing & tenancy

- Composite indexes always lead with `company_id`
- Vector indexes per retrieval table (HNSW if already adopted)
- RLS policies consistent with existing migration direction
- Soft-delete / retention fields for GDPR-like erasure on Memory + Graph

---

## 11. Event Flow

### 11.1 Ingest flow (organization gets smarter asynchronously)

```
Domain action (upload doc / complete task / record approval)
        │
        ▼
Domain Service persists source of truth
        │
        ▼
Publish event (Redis/Celery)
        │
        ├─► memory.ingest.requested
        │         └─► Memory Engine normalize + embed + store
        ├─► kg.upsert.requested
        │         └─► Graph Engine upsert node/edges
        ├─► timeline.append.requested
        │         └─► Timeline Engine append event
        └─► decision.sync.requested (if decision-like)
                  └─► Decision Engine record/link
```

### 11.2 Writeback flow (after AI response)

```
CognitiveOrchestrator completes response
        │
        ▼
Publish cognitive.run.completed
        │
        ├─► Store episodic memory of Q/A (permissioned)
        ├─► Extract entity mentions → kg enrichment job
        ├─► Timeline event “AI consulted X”
        ├─► If user confirms a decision → Decision Engine
        └─► If plan accepted → create tasks via Task service
```

### 11.3 Monitoring flow (proactive, future Phase 4)

```
Celery beat / workers
        │
        ▼
Timeline upcoming + Decision conflicts + Memory freshness checks
        │
        ▼
Reasoning (lightweight) → Planning → Notifications
```

---

## 12. Request Flow (happy path)

### 12.1 End-to-end sequence

```
1. User sends message (Web)
2. API: JWT auth + RBAC deps resolve identity
3. ChatService receives message, persists user turn
4. ChatService → CognitiveOrchestrator.handle(CognitiveRequest)
5. ContextEngine builds ContextFrame
6. Permission gate: if denied → refuse (no provider call)
7. Parallel retrieve:
      MemoryEngine.retrieve(query, frame)
      GraphEngine.subgraph_for_context(frame, seeds)
      TimelineEngine.resolve + history/upcoming
      DecisionEngine.find_relevant(frame, query)
8. ReasoningEngine composes ReasoningTrace + evidence
9. If insufficient info → return clarifying questions (optional provider assist)
10. PlanningEngine builds ActionPlan when intent is operational
11. Provider generate via existing AIService (stream allowed)
12. Response returned with citations + optional plan
13. ChatService persists assistant turn + cognitive_run_id
14. Async writeback events update Memory/Graph/Timeline/Decision
```

### 12.2 Nexora cognitive pipeline (canonical)

```
Question
  → Identity
  → Permissions
  → Company Context
  → Department Context
  → Project Context
  → Second Brain (Memory Engine)
  → Knowledge Graph
  → Timeline
  → Decision Memory
  → Reasoning Engine
  → Planning Engine
  → AI Provider
  → Response
  → Memory Update
```

### 12.3 Failure / refuse paths

| Condition | Behavior |
|-----------|----------|
| Cross-tenant access | Hard deny + audit |
| Missing permission for tool/action | Strip action; answer within scope or refuse |
| Empty evidence for factual claim | Ask for doc/project or answer with uncertainty |
| Provider outage | Return reasoned partial plan / cached policy answer if safe; else graceful error |
| Conflicting decisions/policies | Surface conflict; do not silently pick |

---

## 13. Security Model Inside Cognitive Core

1. **AuthN** stays in API gateway (JWT) — unchanged  
2. **AuthZ** projected into `ContextFrame.permissions`  
3. Every engine query includes `company_id` + permission filters  
4. Memory/Graph/Decision retrieval must apply **row-level visibility** (role, department, project membership)  
5. `cognitive_runs.reasoning_trace` is privileged (admin / auditor)  
6. Providers receive **redacted prompts** — no secrets, no cross-tenant data  
7. Tool/plan execution re-checks permissions at execution time (TOCTOU safe)

---

## 14. Future Scalability

### 14.1 Modular monolith → microservices

Because engines are interface-isolated, extraction path is:

| Engine | Extraction trigger | Future service |
|--------|--------------------|----------------|
| Memory | large ingest/query load | `memory-service` |
| Graph | deep graph analytics | `graph-service` |
| Timeline | high event volume | `timeline-service` |
| Decision | compliance workloads | `decision-service` |
| Reasoning/Planning | GPU/LLM planning | `cognition-service` |
| Orchestrator | remains edge BFF/API adjacent | `cognitive-gateway` |

Shared contracts stay versioned (OpenAPI / protobuf later).

### 14.2 Data plane scaling

- PostgreSQL read replicas for retrieval-heavy engines
- pgvector partitioning by `company_id` / time
- Redis cluster for working memory + event fanout
- Celery workers scaled by queue (`memory`, `graph`, `timeline`, `cognitive_writeback`)
- Optional dedicated vector store only if pgvector ceilings are hit — behind Memory port

### 14.3 Multi-region / enterprise

- Tenant data residency via company- Affinity DB routing
- Cognitive runs stored in-region
- Provider routing policies per tenant (already compatible with Provider Pattern)

### 14.4 Model evolution

- Swap OpenRouter/Gemini/OpenAI without changing engines
- Optional specialized models: extractor (graph), reranker (memory), planner (planning)
- Reasoning Engine remains the gate that decides which model role to call

### 14.5 Product evolution enabled by Cognitive Core

- Document Intelligence becomes Memory+Graph consumer
- Multi-agent router becomes Planning+Reasoning consumer
- Proactive monitoring becomes Timeline+Decision+Planning consumer
- BI Text-to-SQL becomes Context+Reasoning constrained tool use

---

## 15. Implementation Phasing (design guidance only)

Not code — recommended delivery slices after this design:

1. **Contracts + Orchestrator skeleton + ContextEngine** (wire chat through it; provider still last)
2. **MemoryEngine retrieval** on top of documents/embeddings + chat episodic writeback
3. **TimelineEngine** events from existing domain actions
4. **DecisionEngine** for approvals/policy changes
5. **Knowledge Graph** PostgreSQL adjacency (seed from users/projects/documents/tasks)
6. **ReasoningTrace persistence + citations in API responses**
7. **PlanningEngine** → task creation proposals
8. Extract engines to services only when metrics demand it

This aligns with roadmap Phase 2–4 without rewriting Phase 1 foundations.

---

## 16. Success Criteria

Cognitive Core is successful when:

1. No intelligent endpoint calls a provider without Context + Reasoning  
2. Two users in the same company with different roles get different evidence packs for the same question  
3. AI can answer “why was this approved?” from Decision Memory  
4. AI can answer “what changed since last month?” via Timeline  
5. AI can traverse Client → Contract → Invoice → Task relationships  
6. Every answer can optionally update Memory without manual re-entry  
7. A new AI module can be added by depending on Orchestrator interfaces only  

---

## 17. Architectural Verdict

Nexora’s differentiator is not “another LLM chat”.  
It is a **permissioned organizational brain**.

The Cognitive Core is that brain:

- **Memory** = what we know  
- **Context** = what matters now  
- **Graph** = how things connect  
- **Timeline** = when things happen  
- **Decision** = why we chose  
- **Reasoning** = how we think  
- **Planning** = what we do next  

All existing platform parts remain.  
All future AI parts plug in here.

---

*Document type: Enterprise Architecture Design  
Project: Nexora AI  
Layer: Cognitive Core*
