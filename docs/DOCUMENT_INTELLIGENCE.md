# Nexora AI — Document Intelligence Engine

Document Intelligence Engine transforms unstructured corporate information
(PDF, DOCX, XLSX/CSV, text, images) into structured, searchable, traceable
organizational knowledge: chunks + embeddings, entities, relationships, and a
company-level knowledge graph.

> Status: **Implemented** — Phase 2 of the roadmap.

---

## Architecture

```mermaid
graph LR
    Upload[Document Upload / Integration Ingest] --> Queue[Celery / in-process worker]
    Queue --> Pipeline[DocumentIntelligencePipeline v2.1]
    Pipeline --> Extract[Format Extractors]
    Extract --> OCR[Image OCR (optional)]
    Pipeline --> Dup[Duplicate Detection SHA-256]
    Pipeline --> Classify[Classifier + Language Detection]
    Pipeline --> Chunk[Intelligent Chunker]
    Pipeline --> Embed[Embeddings + pgvector]
    Pipeline --> ERE[Entity & Relationship Extraction]
    Pipeline --> Graph[Knowledge Graph]
    Pipeline --> Memory[Second Brain (user docs only)]
    Graph --> API[Intelligence REST API]
    API --> Search[Hybrid Filtered Search]
```

## Pipeline flow (`app/intelligence/pipeline.py`)

1. **File load** — bytes fetched from MinIO via `stored_path`.
2. **Duplicate detection** — SHA-256 content hash, marks `is_duplicate` / `duplicate_of_id`.
3. **Format extraction** — dispatch by extension to `pdf`, `docx/doc`, `xlsx/xls`,
   `csv`, `image_ocr`, or plain-text (`txt/json/md/log`) extractors. Unsupported
   binary formats degrade gracefully with an `[UNSUPPORTED FORMAT]` notice.
4. **Understanding** — document category classification (`app/intelligence/core/classifier.py`)
   and language detection (`app/intelligence/core/language.py`: uz/ru/en + CJK/arabic).
5. **Intelligent chunking** — structure-aware (`table`/`heading` kept intact,
   long text split on paragraph boundaries), preserving `page_number`, `section_title`.
6. **Embeddings** — provider-agnostic (`app/ai/embeddings.py`) with
   `embedding_model` / `embedding_version` / `embedding_dimensions` tracked on the document.
7. **Entity & relationship extraction** — regex-first (emails, amounts, dates,
   companies) plus optional LLM-assisted relationships; stored with confidence
   and linked back to source chunks.
8. **Second Brain** — for user-uploaded docs (`source_system != "integration"`),
   a `document.processed` event is routed to memory ingestion.
9. **Observability** — each run creates a `DocumentProcessingJob` with
   per-stage durations (OCR/embedding/extraction), chunk/entity/relationship
   counts, retry count, and error details.

Derived data (chunks/entities/relationships) is **replaced on every reprocess**,
so retries and reindexing never duplicate knowledge.

## Data model

- `documents` — extended with `title`, `author`, `source_system`, `language`,
  `embedding_model`, `embedding_version`, `embedding_dimensions`, nullable `uploaded_by`.
- `document_versions` — version chain with parent link and change summary.
- `document_chunks` — content + embedding + metadata (page, section, citation).
- `document_entities` — named entities with type, confidence, attributes, chunk link.
- `document_relationships` — typed edges between entities with context snippet.
- `document_processing_jobs` — pipeline run telemetry and retry tracking.

## REST API (`app/api/v1/documents.py`)

All endpoints are tenant-scoped (company_id enforced in every query).

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| `POST` | `/documents/upload` | Upload + async queue processing |
| `GET`  | `/documents/stats` | Tenant document status counters |
| `POST` | `/documents/intelligence/search` | Hybrid (vector+full-text) filtered search with citations |
| `GET`  | `/documents/knowledge-graph` | Company-level interconnected graph |
| `GET`  | `/documents/{id}/intelligence` | Full intelligence view (doc + entities + relationships + chunks + jobs) |
| `GET`  | `/documents/{id}/chunks` | Chunk-level knowledge sources with page citations |
| `GET`  | `/documents/{id}/entities` | Extracted entities |
| `GET`  | `/documents/{id}/relationships` | Extracted relationships |
| `GET`  | `/documents/{id}/versions` | Version history |
| `GET`  | `/documents/{id}/jobs` | Processing job telemetry |
| `POST` | `/documents/{id}/reprocess` | Re-run pipeline (queues job) |
| `POST` | `/documents/{id}/reindex` | Regenerate embeddings only |

## Search filters

`POST /documents/intelligence/search` supports optional filters: `document_type`,
`department_id`, `project_id`, `source_system`, `date_from`, `date_to`, plus
configurable `top_k`. Scoring combines vector distance and full-text rank.

## Workflow actions

New built-in actions (in `app/workflows/actions/builtin.py`):

- `process_document` — queue a document for (re)processing.
- `intelligence_search` — hybrid search over tenant documents.
- `reindex_document` — regenerate chunk embeddings.

## Agent tools

New agent tools (in `app/ai/agents/tools.py`):

- `intelligence_search` — semantic + full-text search with entities/graph/citations.
- `get_document_intelligence` — full intelligence summary for a document.

## Traceability & governance

- Every entity/relationship/chunk links back to a source document; chunks carry
  page numbers and section titles.
- All queries join on `company_id` — tenant isolation and RBAC are never bypassed.
- Embedding model/version is recorded per document for reproducible reindexing.
- No secrets or hard-coded credentials; AI providers come from `.env`.

## Tests

`tests/test_document_intelligence.py` covers language detection, chunking
(split/keep/table), classification, duplicate hashing, regex entity extraction,
and pipeline extraction paths (text-like, empty file, unsupported format).

Run: `python -m pytest tests/test_document_intelligence.py -q`
