# Nexora AI — Hybrid Memory System Architecture

**Status:** Design Specification (No Implementation)  
**Audience:** Enterprise Knowledge Management Architects, Platform Engineers  
**Depends on:** `docs/COGNITIVE_CORE_ARCHITECTURE.md`  
**Scope:** Design the organizational Hybrid Memory System that powers Cognitive Core retrieval. Extend current PostgreSQL + pgvector + Redis + Celery + MinIO stack. Do not redesign auth, tenancy, or AI providers.

---

## 1. Executive Summary

Nexora AI must never behave like a simple chatbot.

A chatbot answers from a prompt.  
A RAG bot answers from nearest chunks.  
**Nexora answers from an organization.**

The **Hybrid Memory System (HMS)** is the most valuable technology inside Nexora because it is the substrate that makes every later AI module organizationally aware:

- It connects every business object
- It remembers across time, people, projects, and decisions
- It retrieves through multiple complementary channels
- It updates itself after every meaningful interaction
- It continuously learns patterns without replacing source-of-truth databases

### One-line definition

> Hybrid Memory System = permissioned, multi-modal organizational memory that unifies relational truth (PostgreSQL), semantic recall (pgvector), structural relationships (Knowledge Graph), temporal events (Timeline), causal decisions (Decision Memory), and scoped working context — retrieved together before any LLM call.

### Canonical pipeline

```
Prompt
  → Identity
  → Context
  → Second Brain (Hybrid Memory System)
      → Knowledge Graph
      → Timeline
      → Metadata Search
      → Semantic Search
      → Keyword / Full-Text Search
      → Decision Memory
      → Context / Working Memory
  → Reasoning
  → Planning
  → AI Provider
  → Memory Update
```

Traditional AI and traditional RAG are subsets. HMS is the superset.

---

## 2. Why Hybrid Memory (Not Vector-Only RAG)

### 2.1 Limits of vector-only retrieval

| Vector-only strength | Vector-only failure |
|----------------------|---------------------|
| Finds similar wording | Misses exact IDs, invoice numbers, SKUs codes |
| Good for fuzzy docs | Weak for “who owns this project?” |
| Fast similarity | Blind to permissions and org structure |
| Chunk-centric | Cannot traverse Contract → Invoice → Task |
| No native time model | Bad at “before signing” / “last quarter” |
| No causal model | Cannot answer “why was this approved?” |

### 2.2 Hybrid thesis

Enterprise questions are rarely pure semantic questions. They are usually **composed queries**:

- semantic intent (“risks”, “delay”, “payment issue”)
- metadata constraints (project X, client Y, status open)
- relationship constraints (documents linked to this contract)
- temporal constraints (after last meeting, before signature)
- authority constraints (decisions by CFO, policies in force)
- permission constraints (user may only see Finance dept)

HMS answers composed queries by **fusing channels**, then handing a ranked evidence pack to Reasoning.

---

## 3. System Position

```
┌──────────────────────────────────────────────────────────┐
│ Cognitive Orchestrator                                    │
└────────────────────────────┬─────────────────────────────┘
                             │ retrieve(EvidenceQuery)
┌────────────────────────────▼─────────────────────────────┐
│ HYBRID MEMORY SYSTEM                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │
│  │ Memory       │ │ Knowledge   │ │ Timeline + Decision │ │
│  │ Planes       │ │ Graph       │ │ Memory              │ │
│  └──────┬──────┘ └──────┬──────┘ └──────────┬──────────┘ │
│         └───────────────┼───────────────────┘            │
│                         ▼                                 │
│              Hybrid Retrieval Planner                     │
│              Fusion Ranker + Permission Filter            │
└──────┬──────────┬──────────┬──────────┬──────────────────┘
       ▼          ▼          ▼          ▼
  PostgreSQL   pgvector    Redis     Domain Events
  (truth)      (semantic)  (working) (Celery writeback)
```

**Critical rule:** PostgreSQL remains the **system of record** for business entities.  
HMS is the **system of recall** and **system of relationships**. It indexes, relates, and remembers — it does not become a second competing CRUD database.

---

## 4. Memory Planes (Complete Hybrid Model)

HMS is not one store. It is a **federation of memory planes** with a shared retrieval contract.

### 4.1 Plane catalog

| Plane | What it stores | Primary store | Used for |
|-------|----------------|---------------|----------|
| **Semantic Memory** | embeddings of chunks, summaries, FAQs | pgvector | meaning similarity |
| **Keyword / Lexical Memory** | tokenized text, titles, IDs | PostgreSQL FTS / trigram | exact terms, codes |
| **Metadata Memory** | type, status, owner, tags, ACLs | PostgreSQL columns/JSONB | filters & facets |
| **Knowledge Graph Memory** | nodes + edges | `kg_nodes` / `kg_edges` | relationships & traversal |
| **Timeline Memory** | events, versions, deadlines | `timeline_events` | time windows & change |
| **Decision Memory** | approvals, rationale, consequences | `decisions` + links | “why / what changed” |
| **Context / Working Memory** | active conversation, pinned docs | Redis (+ short Postgres) | current session |
| **Long-term Memory** | durable summaries & facts | `memory_units` | persistent recall |
| **Organization Memory** | company policies, org structure, norms | memory_units + graph | company-wide knowledge |
| **User Memory** | preferences, expertise, habits | scoped memory_units | personalization under policy |
| **Project Memory** | project briefs, risks, status digests | scoped memory_units + graph | project Q&A |
| **Workflow Memory** | process steps, bottlenecks, patterns | memory_units + graph + learning store | process intelligence |
| **Self-Learning Memory** | usage patterns, FAQ clusters, edge suggestions | learning tables | continuous improvement |

### 4.2 Scope hierarchy

Every durable memory unit is addressed in nested scopes:

```
Tenant (Company)
  └── Organization Memory
        ├── Department / Team
        │     └── User Memory (private / shared)
        ├── Project Memory
        │     └── Workflow Memory
        └── Cross-cutting (Policies, Clients, Suppliers, Assets)
```

Retrieval always starts from **Identity + Context Frame**, then expands only within allowed scopes.

### 4.3 Memory unit (canonical atom)

Independent of plane, the atomic durable object is a **Memory Unit**:

```
MemoryUnit
├── id, company_id
├── plane_hints[]          # semantic, decision, timeline, ...
├── memory_class           # episodic | semantic | procedural | preference | pattern
├── scope                  # org | dept | user | project | workflow
├── source_ref             # {entity_type, entity_id} system of record pointer
├── title, content, summary
├── occurred_at / valid_from / valid_to
├── importance, confidence, freshness_score
├── acl                    # visibility projection
├── embedding_ref          # optional link to vector row
├── graph_node_ref         # optional link to kg node
└── metadata JSONB         # tags, language, channel, module
```

Planes are **views and indexes over Memory Units + domain entities**, not isolated silos with conflicting truth.

---

## 5. Knowledge Graph Design

### 5.1 Purpose

The Knowledge Graph (KG) makes Nexora understand **relationships instead of isolated rows**.

Vectors answer: “What text is similar?”  
SQL answers: “What rows match filters?”  
**Graph answers: “How is this connected, through whom, and with what consequence?”**

### 5.2 Graph model style

Use a **property graph**:

- **Nodes** = entities (typed)
- **Edges** = typed relationships with properties and temporal validity
- **Labels / types** = controlled vocabulary (extensible registry)
- **Properties** = JSONB for module-specific attributes without schema thrash

Phase A storage: PostgreSQL tables (fits current stack).  
Phase B: optional dedicated graph DB behind the same port.

### 5.3 Node identity rule

Every node is anchored to system-of-record identity:

```
(company_id, entity_type, entity_id) → unique kg_node
```

Orphan AI-extracted nodes are allowed only as `provisional=true` until confirmed or linked.

### 5.4 Core graph layers

1. **Identity & Org layer** — Company, Department, Team, User, Role  
2. **Work layer** — Project, Task, Workflow, Meeting, Decision, AI Agent  
3. **Knowledge layer** — Document, Report, Policy, Dashboard, Notification, KPI  
4. **Commercial layer** — Client, Supplier, Contract, Invoice  
5. **Operations / Industrial layer** — Warehouse, Product, Container, Shipment, ManufacturingProcess, Machine, Sensor  
6. **Future modules layer** — registry-driven new entity types without redesign

---

## 6. Entity Model (Graph + Domain Alignment)

### 6.1 Entity type registry

Entity types are not hard-coded forever. They live in an **Entity Type Registry** so future modules can register safely.

| Entity type | Domain owner (SoR) | Graph role |
|-------------|--------------------|------------|
| `Company` | companies | tenant root |
| `Department` | org structure | org partition |
| `Team` | org structure | sub-org |
| `User` | users | actor |
| `Role` | roles / RBAC | authority |
| `Project` | projects | work container |
| `Task` | tasks | actionable unit |
| `Document` | documents | knowledge artifact |
| `Report` | reports | derived knowledge |
| `Meeting` | meetings (future/ext) | collaboration event |
| `Policy` | policies/settings | constraint knowledge |
| `Client` | CRM/commercial | external party |
| `Supplier` | procurement | external party |
| `Invoice` | finance | commercial artifact |
| `Contract` | legal/commercial | binding artifact |
| `Warehouse` | logistics | location/asset hub |
| `Product` | catalog/inventory | item |
| `Container` | logistics | shipment unit |
| `Shipment` | logistics | movement |
| `ManufacturingProcess` | production | process |
| `Machine` | production/IoT | asset |
| `Sensor` | IoT | telemetry source |
| `KPI` | analytics | metric definition |
| `Dashboard` | analytics/UI | view aggregate |
| `Notification` | notifications | signal |
| `AIAgent` | agents | automated actor |
| `Workflow` | automation | process definition |
| `Decision` | decision memory | causal node |
| `MemoryUnit` | HMS | recall node (optional projection) |
| `*` future | module registry | extension |

### 6.2 Logical entity model (attributes at architecture level)

Each entity in SoR keeps full business fields. Graph node stores:

- stable identity refs
- display label
- canonical type
- key facets mirrored for traversal filters (status, department_id, project_id, sensitivity)
- link to primary MemoryUnit / embedding set when relevant

**Do not duplicate entire invoices into the graph.** Duplicate only what retrieval needs for relationship search and faceting.

### 6.3 Canonical organizational chain (example)

```
Company
  → has → Department
    → employs → User
      → has_role → Role
        → assigned_to → Project
          → contains → Task
            → discussed_in → Meeting
              → produced → Decision
                → supported_by → Document
                  → related_to → Contract
                    → billed_as → Invoice
                      → summarized_in → Report
                        → visualized_on → Dashboard
                          → concerns → Client
```

### 6.4 Operations chain (example)

```
Client / Supplier
  → orders/supplies → Product
    → stored_in → Warehouse
      → packed_in → Container
        → moved_by → Shipment
          → produced_via → ManufacturingProcess
            → runs_on → Machine
              → monitored_by → Sensor
                → triggers → Notification
```

---

## 7. Relationship Model

### 7.1 Relationship design rules

1. **Typed edges only** (controlled vocabulary + module extensions)
2. Edges are **directional** with optional inverse views
3. Edges may be **temporal** (`valid_from`, `valid_to`)
4. Edges carry **provenance** (`source`: system | user | ai_extraction | import)
5. Edges carry **confidence** for AI-suggested links
6. Soft-delete / supersede — do not lose audit history
7. Every edge is tenant-scoped (`company_id`)

### 7.2 Core relationship vocabulary

| Edge type | Meaning | Example |
|-----------|---------|---------|
| `PART_OF` | hierarchical containment | Team PART_OF Department |
| `WORKS_IN` | employment / assignment to org unit | User WORKS_IN Department |
| `HAS_ROLE` | RBAC binding | User HAS_ROLE Role |
| `OWNS` | accountability ownership | Department OWNS Project |
| `ASSIGNED_TO` | responsibility | Task ASSIGNED_TO User |
| `CONTAINS` | composition | Project CONTAINS Task |
| `RELATED_TO` | weak generic link | Document RELATED_TO Client |
| `REFERENCES` | citation / dependency | Report REFERENCES Document |
| `DERIVED_FROM` | transformation lineage | Report DERIVED_FROM Document |
| `ATTACHED_TO` | file/object attachment | Document ATTACHED_TO Meeting |
| `PARTICIPATED_IN` | attendance | User PARTICIPATED_IN Meeting |
| `PRODUCED` | creation outcome | Meeting PRODUCED Decision |
| `DECIDED` | decision authorship | User DECIDED Decision |
| `UPDATES` | policy/process change | Decision UPDATES Policy |
| `AFFECTS` | constraint impact | Policy AFFECTS Workflow |
| `GENERATES` | process output | Workflow GENERATES Report |
| `BELONGS_TO` | commercial/ops ownership | Invoice BELONGS_TO Client |
| `GOVERNS` | contractual coverage | Contract GOVERNS Project |
| `SUPERSEDES` | version replacement | Policy_v2 SUPERSEDES Policy_v1 |
| `DEPENDS_ON` | blocking dependency | Task DEPENDS_ON Task |
| `STORED_IN` | inventory location | Product STORED_IN Warehouse |
| `PACKED_IN` | logistics packing | Product PACKED_IN Container |
| `MOVED_BY` | transport | Container MOVED_BY Shipment |
| `RUNS_ON` | process-asset | ManufacturingProcess RUNS_ON Machine |
| `MONITORED_BY` | telemetry | Machine MONITORED_BY Sensor |
| `TRIGGERS` | event causation | Sensor TRIGGERS Notification |
| `EXECUTED_BY` | automation actor | Workflow EXECUTED_BY AIAgent |
| `VISIBLE_ON` | presentation | KPI VISIBLE_ON Dashboard |
| `ABOUT` | topical link | Decision ABOUT Contract |

### 7.3 Business examples mapped

- Employee **WORKS_IN** Department  
- Department **OWNS** Project  
- Project **CONTAINS** Tasks  
- Meeting **PRODUCED** Decisions  
- Decision **UPDATES** Policy  
- Policy **AFFECTS** Workflow  
- Workflow **GENERATES** Report  
- Report **REFERENCES** / **DERIVED_FROM** Documents  
- Invoice **BELONGS_TO** Client  
- Container **MOVED_BY** Shipment  
- Shipment / Product **STORED_IN** / associated with Warehouse  

### 7.4 Multi-hop query examples (architecture targets)

- “All documents supporting decisions made before contract signature”  
  `Contract ← ABOUT/GOVERNS ← Decision ← PRODUCED ← Meeting` + Timeline filter + Document links  
- “Tasks created because of last quarter’s client escalations”  
  `Client → Meetings/Decisions → Tasks` + Timeline window  
- “Machines whose sensors triggered notifications affecting Project X shipments”  
  `Project → Shipments → Containers → … → Machine → Sensor → Notification`

---

## 8. Hybrid Search Architecture

### 8.1 Principle

**Never depend on vector search only.**

Every retrieval request is compiled into a **Retrieval Plan** with multiple channels, then fused.

### 8.2 Retrieval channels

| Channel | Mechanism | Best at |
|---------|-----------|---------|
| Semantic Search | pgvector ANN (HNSW/IVF) | paraphrases, conceptual match |
| Keyword Search | PostgreSQL FTS (`tsvector`) + trigram | names, codes, exact phrases |
| Metadata Search | SQL filters on structured fields | status, owner, type, tags |
| Relationship Search | graph neighborhood / path queries | connected objects |
| Timeline Search | time-windowed event queries | change, history, deadlines |
| Decision Search | decision store + links | rationale & authority |
| Context Filter | ContextFrame constraints | current project/docs/workflow |
| Permission Filter | ACL + RBAC projection | security boundary |
| Company Isolation | mandatory `company_id` predicate | tenant safety |

### 8.3 Hybrid Retrieval Planner

Input: `EvidenceQuery` = natural language + ContextFrame + intent hints

Planner outputs channel mix, for example:

```
Intent: "Why did we delay Client A shipment last month?"
Plan:
  1. Permission + company isolation (always)
  2. Metadata: entity Client=A, types in {Shipment, Meeting, Decision, Task}
  3. Timeline: last calendar month (company TZ)
  4. Relationship: ego-graph around Client A depth 2–3
  5. Semantic: embed question → topK chunks/memory units
  6. Keyword: "delay", shipment IDs if detected
  7. Decision: decisions ABOUT Client A / related shipments in window
  8. Fuse + diversify + cite
```

### 8.4 Fusion ranker

Candidates from all channels enter a common **Evidence Candidate** schema:

```
EvidenceCandidate
├── ref (entity or memory unit or chunk)
├── channel_scores {semantic, keyword, metadata, graph, timeline, decision}
├── graph_distance
├── temporal_relevance
├── authority_score      # policy/decision weight
├── freshness_score
├── permission_pass
└── final_score
```

Fusion strategy (architecture-level):

1. Hard filters first (tenant, ACL, context scope)
2. Normalize per-channel scores
3. Weighted sum with intent-adaptive weights
4. Graph boost for candidates on short paths to seed entities
5. Timeline boost for in-window events
6. MMR / diversity to avoid 10 near-duplicate chunks
7. Cap by token budget from ContextFrame

### 8.5 What “best information before reasoning” means

Reasoning never sees raw channel dumps. It receives an **Evidence Pack**:

- top evidence items with citations
- subgraph summary (key nodes/edges)
- timeline slice
- relevant decisions with rationale
- known gaps (“no contract found in scope”)

---

## 9. Timeline Memory Design

### 9.1 Role

Timeline Memory gives HMS a first-class temporal index over organizational life.

### 9.2 Event model

```
TimelineEvent
├── company_id
├── event_type
├── title / description
├── entity_refs[]
├── occurred_at / due_at
├── actor_user_id?
├── causality_refs[]      # decision_id, workflow_id, ...
├── change_summary?
└── properties JSONB
```

### 9.3 Temporal query patterns supported

| User intent | Timeline behavior |
|-------------|-------------------|
| What changed last month? | windowed event diff + changed entities |
| Compare this report with January | locate report versions + related events in Jan vs now |
| Decisions before signing the contract | events/decisions with `occurred_at < contract.signed_at` |
| Meetings related to this project | Meeting events linked via graph + project_id |
| Progress last quarter | task/decision/report events aggregated in quarter window |

### 9.4 Version time vs wall time

HMS distinguishes:

- **Wall-clock time** — when something happened operationally  
- **Version time** — when a document/policy revision became active (`SUPERSEDES` edges)  
- **Validity time** — when a relationship was true  

Retrieval plans may use any combination.

---

## 10. Decision Memory Design

### 10.1 Role

Decision Memory stores **causal organizational knowledge** — not just text that mentions a decision.

### 10.2 Decision record

```
Decision
├── who          # decided_by (User / Role / Board / AI-assisted)
├── when         # decided_at
├── why          # rationale
├── what_changed # consequences summary + links
├── supporting_documents[]
├── related_meetings[]
├── created_tasks[]
├── affected_policies / workflows
├── status       # proposed | approved | rejected | superseded
└── evidence_refs[]
```

### 10.3 Searchability

Decisions are retrievable by:

- semantic similarity on rationale/title
- metadata (approver, status, project)
- graph links (ABOUT Contract, PRODUCED_BY Meeting)
- timeline windows
- consequence links (tasks created, policies updated)

### 10.4 Explanation contract

Any decision returned to Reasoning must be explainable as:

> Who decided → when → why → based on which documents/meetings → resulting in which tasks/policy changes.

---

## 11. Graph Updates

### 11.1 Update sources

| Source | How graph changes |
|--------|-------------------|
| Domain CRUD | deterministic upsert of nodes/edges from SoR writes |
| Document processing | create Document node; AI may propose RELATED_TO edges |
| Chat / Cognitive writeback | episodic links; entity mentions → provisional edges |
| Decision recording | Decision node + PRODUCED/ABOUT/UPDATES edges |
| Workflow execution | GENERATES / TRIGGERS / EXECUTED_BY edges |
| Imports / connectors | bulk upsert with provenance=`import` |
| Self-learning suggestions | provisional edges awaiting acceptance |

### 11.2 Update pipeline

```
Domain write (SoR commit)
  → Outbox / Domain Event
    → Graph Sync Worker
      → Upsert node(s)
      → Upsert/close edge(s)
      → Emit kg.updated
        → optional MemoryUnit refresh
        → optional embedding refresh for summaries
```

### 11.3 Consistency rules

1. **SoR wins** on conflicts with AI-extracted structure  
2. AI edges are `provisional` until user/system confirmation  
3. Updates are **idempotent** (natural keys on edges)  
4. Edge closure uses `valid_to` rather than physical delete when history matters  
5. Cross-tenant edges are impossible by construction  

### 11.4 Example: contract signed

```
1. Contract.status → signed (PostgreSQL)
2. Event contract.signed
3. Graph: update Contract node facets; add TimelineEvent
4. If approval Decision exists: Decision -ABOUT→ Contract; Decision -UPDATES→ Policy?
5. MemoryUnit summary “Contract X signed” ingested
6. Embeddings updated for contract summary + decision rationale
```

---

## 12. Synchronization with PostgreSQL

### 12.1 Principle

PostgreSQL is the **system of record**.  
HMS tables are **derived intelligence indexes** plus memory artifacts.

### 12.2 Sync patterns

| Pattern | Use |
|---------|-----|
| Transactional outbox | reliable event emission after SoR commit |
| Synchronous projection (light) | tiny facet mirrors needed immediately in same request |
| Async workers (default) | graph upsert, memory ingest, embedding |
| Periodic reconciler | repair drift between SoR and kg_nodes |

### 12.3 What lives only in PostgreSQL SoR

Users, companies, documents binary metadata, invoices amounts, task states, RBAC — authoritative business fields.

### 12.4 What HMS adds in PostgreSQL

- `memory_units`, `memory_links`
- `kg_nodes`, `kg_edges`
- `timeline_events`
- `decisions`, `decision_links`
- `learning_*` tables
- FTS columns / materialized search documents
- vector columns or parallel embedding tables

### 12.5 Tenant isolation

Every HMS table includes `company_id`.  
All sync consumers stamp and filter by tenant.  
RLS (already in platform direction) applies to HMS tables equally.

---

## 13. Synchronization with pgvector

### 13.1 Role of pgvector in HMS

pgvector is the **semantic index**, not the memory brain.

Embedded objects include:

- document chunks (existing pipeline)
- memory unit summaries
- decision rationales
- meeting notes / report abstracts
- FAQ / pattern cards from self-learning
- optional graph-node textual descriptions

### 13.2 Sync flow

```
Content created/updated (doc chunk, memory unit, decision...)
  → Embedding Worker (existing Celery path, extended)
    → provider embedding API
      → write vector to pgvector-backed column/table
        → update memory_unit.embedding_ref / chunk.embedding
          → invalidate retrieval cache keys
```

### 13.3 Consistency rules

1. Embedding is eventually consistent with content  
2. Retrieval may fall back to keyword/metadata/graph while embedding pending  
3. Re-embed on content hash change, not on every unrelated metadata tweak  
4. Version embeddings when model changes (embedding_model_id on rows)  
5. Delete/tombstone vectors when source ACL becomes unreadable or entity purged  

### 13.4 Hybrid with non-vector indexes

A semantic hit is insufficient alone. Fusion requires co-evidence from metadata/graph/time when the question is operational.

---

## 14. Synchronization with AI Memory (Cognitive Writeback)

### 14.1 AI Memory vs Organizational Memory

| Kind | Lifetime | Visibility | Purpose |
|------|----------|------------|---------|
| Working / Context Memory | minutes–hours | session/user | current conversation continuity |
| Episodic AI Memory | durable | ACL-scoped | what was asked/answered/learned in interaction |
| Organizational Memory | durable | org scopes | company knowledge independent of one chat |

### 14.2 Writeback after Cognitive run

```
CognitiveResponse completed
  → writeback planner (policy-aware)
      → store episodic MemoryUnit (Q/A + citations)
      → update Context/Working memory in Redis
      → propose graph edges from entity mentions
      → append TimelineEvent (ai.consulted / fact.stated)
      → if user confirms decision/plan → Decision / Tasks
      → self-learning counters (FAQ, entity affinity, workflow usage)
```

### 14.3 Policy gates on learning

Not everything the model says becomes organizational truth.

Writeback classes:

1. **Always** — audit cognitive_run refs, safety logs  
2. **Default** — episodic chat memory under user/project ACL  
3. **Confirm-required** — new policy facts, graph edges, decisions  
4. **Never** — secrets, cross-scope guesses, rejected content  

---

## 15. Indexing Strategy

### 15.1 Multi-index posture

| Index | On | Purpose |
|-------|----|---------|
| B-Tree / composite | `company_id + fields` | metadata filters |
| FTS / GIN | titles, content, codes | keyword search |
| Trigram | names, filenames | fuzzy exactness |
| HNSW / IVFFlat (pgvector) | embeddings | semantic ANN |
| Adjacency indexes | `kg_edges(from,to,type,company)` | relationship search |
| Time BRIN/B-Tree | `occurred_at`, `due_at` | timeline windows |
| Partial indexes | `provisional=false`, `status=active` | hot paths |
| JSONB GIN | metadata facets | flexible module fields |

### 15.2 Search document projection (recommended)

Maintain a per-tenant **Search Document** projection for heavy artifacts:

```
search_documents
├── company_id
├── ref (entity_type, entity_id)
├── title
├── body_text
├── tsv
├── metadata facets
├── embedding
├── graph_seed_ids[]
└── acl projection
```

This lets Hybrid Retrieval scan one optimized surface while SoR stays normalized.

### 15.3 Graph indexing strategy

- Unique node natural key  
- Edge lookup by from/to/type  
- Optional materialized **ego-graph caches** for hot projects  
- Depth-limited queries (default 1–3) to protect latency  

### 15.4 Reindex operations

- Content change → targeted reindex  
- ACL change → ACL projection refresh (no full re-embed unless text changed)  
- Embedding model upgrade → blue/green vector columns + cutover  
- Tenant purge → cascading delete across HMS indexes  

---

## 16. Retrieval Strategy (End-to-End)

### 16.1 Stages

```
1. Identity & permission projection
2. ContextFrame bind (company/dept/project/conversation/active docs)
3. Query understanding (entities, time expr, intent type)
4. Seed resolution (explicit IDs + NER against graph)
5. Parallel channel retrieval
6. Graph expansion from seeds (bounded)
7. Timeline & decision enrichment
8. Fusion ranking + diversification
9. Evidence pack compression to token budget
10. Hand to Reasoning Engine
```

### 16.2 Intent-adaptive channel weights (examples)

| Intent type | Higher weights |
|-------------|----------------|
| Definition / policy explanation | semantic + keyword + policy decisions |
| “Who owns / related to” | graph + metadata |
| “What changed / compare” | timeline + versions + semantic |
| “Why approved” | decision + supporting docs + meetings |
| Operational status | metadata + timeline + graph |
| Analytical narrative | semantic + KPI metadata + reports |

### 16.3 Permission filtering placement

Permissions are applied:

1. **Before** channel queries (scope predicates)  
2. **During** candidate assembly (row ACL)  
3. **After** fusion (strip any leaked refs)  

Defense in depth — never only at the prompt layer.

### 16.4 Latency budget (architecture targets)

| Stage | Target posture |
|-------|----------------|
| Context + auth | sub-50ms cached |
| Parallel retrieval | tens–low hundreds ms with indexes |
| Fusion | CPU-local, cheap |
| Heavy graph / re-embed | async, not on request path |

Degrade gracefully: if semantic index warm-up pending, still answer with metadata+graph+keyword.

---

## 17. Self-Learning Architecture

### 17.1 What “self-learning” means here

Not unconstrained model fine-tuning on private data by default.  
It means **continuous organizational memory improvement**:

- learn user behavior (frequent entities, preferred projects)
- learn workflows (common step sequences, bottlenecks)
- learn document usage (which docs actually resolve questions)
- learn business patterns (seasonal delays, recurring decision types)
- learn relationships (repeated co-occurrence → edge suggestions)
- learn FAQs (cluster repeated questions → durable FAQ MemoryUnits)
- suggest improvements (missing metadata, unlinked invoices, stale policies)

### 17.2 Learning store (logical)

```
learning_signals       # raw events: click, cite, accept, reject, dwell
learning_patterns      # aggregated patterns per tenant
learning_faq_clusters  # question clusters + best evidence refs
learning_edge_suggestions
learning_improvement_suggestions
```

### 17.3 Learning loop

```
User interactions + Cognitive citations + accepted plans
  → learning_signals
    → periodic aggregation workers
      → update User/Project/Workflow Memory summaries
      → propose FAQ cards
      → propose provisional graph edges
      → propose improvement suggestions to Admin
```

### 17.4 Human control

- Tenant admins can enable/disable learning classes  
- Provisional knowledge requires acceptance for promotion to Organization Memory  
- Users can delete their User Memory  
- Learning never crosses tenants  

---

## 18. Scalability Strategy

### 18.1 Scale dimensions

| Dimension | Strategy |
|-----------|----------|
| Tenants | strict partition by `company_id`; per-tenant rate limits |
| Documents / vectors | chunking standards; HNSW; partition large embedding tables |
| Graph size | depth caps; hot-neighborhood caches; eventual dedicated graph DB |
| Events | timeline partitioning by month; BRIN indexes |
| QPS retrieval | read replicas; Redis cache of Evidence Packs for identical queries |
| Write spikes | Celery queue isolation: `embed`, `graph_sync`, `memory_ingest`, `learning` |
| Prompt growth | summary memory + progressive disclosure, not full dumps |

### 18.2 From modular monolith to services

Extract without redesign:

1. `memory-retrieval-service` (hybrid search + fusion)  
2. `graph-service`  
3. `timeline-decision-service`  
4. `learning-service`  

Keep shared contracts (`EvidenceQuery`, `EvidencePack`, entity registry).

### 18.3 Caching layers

- Redis: working memory, hot ContextFrames, hot ego-graphs  
- Application: embedding of repeated queries (short TTL)  
- Materialized project digests refreshed on events  

### 18.4 Cost control

- Embed only canonical summaries for some entity types  
- Tier storage: hot / warm / cold memory  
- Downsample sensor telemetry into MemoryUnits (never raw firehose in graph)

---

## 19. Future Enterprise Expansion

### 19.1 Module registry

New enterprise modules register:

- entity types  
- edge types  
- metadata facets  
- indexing profiles  
- writeback policies  

HMS does not need a redesign for Manufacturing, HR, or Logistics packs — it needs registry entries + SoR tables + sync emitters.

### 19.2 External systems

Connectors (already emerging in codebase direction) publish canonical events:

- ERP invoices → Invoice nodes + BELONGS_TO Client  
- CRM accounts → Client nodes  
- IoT platform → Sensor events → Timeline + TRIGGERS Notification  
- Email/Meetings provider → Meeting nodes + ATTACHED documents  

### 19.3 Compliance & residency

- Per-company data residency routing  
- Memory erasure workflows (Right to be forgotten) across vectors, graph, timeline  
- Decision Memory retention separate from chat ephemera  
- Auditor role for cognitive evidence packs  

### 19.4 Advanced graph evolution

- Infer communities (teams/clients clusters)  
- Risk propagation along dependency edges  
- Automated impact analysis (“if policy changes, affected workflows”)  
- Optional move of hot graph workloads to Neo4j/Neptune with adapter  

### 19.5 Model evolution

- Better extractors improve provisional edges  
- Rerankers improve fusion without changing SoR  
- Planning uses HMS evidence packs unchanged  

---

## 20. Logical Folder Placement (Design Only)

Aligned with Cognitive Core layout:

```
backend/app/cognitive/
  engines/memory/           # plane services + fusion
  engines/graph/            # KG upsert/query
  engines/timeline/
  engines/decision/
  adapters/
    postgres_sor_sync.py    # conceptual adapter
    pgvector_index.py
    redis_working_memory.py
    search_fusion.py
  learning/                 # signals, patterns, suggestions
  registry/
    entity_types.py
    edge_types.py
```

Workers extend existing Celery app:

- `graph_sync_worker`
- `memory_ingest_worker`
- `embedding_worker` (existing, extended)
- `learning_aggregation_worker`

---

## 21. Service Interaction Summary

```
Chat / Agents / Documents / Future Modules
        │
        ▼
Cognitive Orchestrator
        │
        ▼
Hybrid Memory System
        ├─ Context-bound EvidenceQuery
        ├─ Parallel: Metadata | Keyword | Semantic | Graph | Timeline | Decision
        ├─ Permission + Tenant filters
        ├─ Fusion Ranker → Evidence Pack
        └─ return to Reasoning / Planning
                │
                ▼
        AI Provider
                │
                ▼
        Writeback → PostgreSQL HMS tables + pgvector + Redis + Learning
```

---

## 22. Success Criteria

HMS is successful when:

1. The same question yields different Evidence Packs for different roles in one company  
2. Vector-only questions and relationship questions both work well  
3. “Why was this decided?” returns who/when/why/docs/meetings/tasks  
4. “What changed last month for Project X?” uses Timeline + Graph + Metadata together  
5. New entity types can be added via registry without rewriting retrieval  
6. AI writeback improves memory without corrupting SoR truth  
7. Tenant isolation holds across all planes and indexes  

---

## 23. Architectural Verdict

The most valuable technology in Nexora is not a larger context window and not a single vector index.

It is the **Hybrid Memory System**:

- **PostgreSQL** for truth and metadata  
- **pgvector** for meaning  
- **Knowledge Graph** for relationships  
- **Timeline** for change  
- **Decision Memory** for causality  
- **Scoped memories** for organization, user, project, workflow  
- **Self-learning** for continuous improvement  
- **Fusion retrieval** so Reasoning sees an organization — not a chunk dump  

This is what makes Nexora think like an organization.

---

*Document type: Enterprise Knowledge Architecture  
Project: Nexora AI  
Technology: Hybrid Memory System  
Companion: Cognitive Core Architecture*
