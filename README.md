# Nexora AI

Multi-tenant AI SaaS platform for businesses.

## Architecture

- **Frontend (Apps)**: Next.js Frontend (`apps/web`), Admin Panel (`apps/admin`), Mobile (`apps/mobile`)
- **Backend**: FastAPI (Python 3.13+)
- **Database**: PostgreSQL 17 + pgvector (`database/`, `vector-db/`)
- **Cache & Storage**: Redis, Storage (`storage/`)
- **AI Engine**: Gemini, OpenAI, Anthropic, Custom Agents (`backend/services/ai/`, `backend/services/agents/`)

## Project Structure

```
nexora-ai/
│
├── apps/
│   ├── web/                        # Next.js Frontend
│   ├── admin/                      # Admin Panel
│   └── mobile/                     # Flutter (kelajakda)
│
├── backend/
│   ├── api/
│   │   ├── auth/
│   │   ├── chat/
│   │   ├── users/
│   │   ├── documents/
│   │   ├── tasks/
│   │   ├── notifications/
│   │   └── admin/
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── middleware.py
│   │   └── database.py
│   │
│   ├── services/
│   │   ├── ai/
│   │   │   ├── llm_service.py
│   │   │   ├── prompt_builder.py
│   │   │   ├── embedding_service.py
│   │   │   └── response_formatter.py
│   │   │
│   │   ├── memory/
│   │   │   ├── memory_service.py
│   │   │   ├── context_builder.py
│   │   │   ├── vector_search.py
│   │   │   └── memory_ranker.py
│   │   │
│   │   ├── knowledge/
│   │   │   ├── document_indexer.py
│   │   │   ├── database_reader.py
│   │   │   ├── excel_reader.py
│   │   │   ├── pdf_reader.py
│   │   │   └── word_reader.py
│   │   │
│   │   ├── agents/
│   │   │   ├── document_agent.py
│   │   │   ├── analytics_agent.py
│   │   │   ├── monitoring_agent.py
│   │   │   ├── workflow_agent.py
│   │   │   ├── logistics_agent.py
│   │   │   ├── hr_agent.py
│   │   │   └── finance_agent.py
│   │   │
│   │   ├── automation/
│   │   │   ├── scheduler.py
│   │   │   ├── task_runner.py
│   │   │   ├── reminders.py
│   │   │   └── notifications.py
│   │   │
│   │   └── timeline/
│   │       ├── timeline_engine.py
│   │       ├── event_tracker.py
│   │       └── deadline_monitor.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── document.py
│   │   ├── memory.py
│   │   ├── task.py
│   │   ├── conversation.py
│   │   └── notification.py
│   │
│   ├── repositories/
│   └── utils/
│
├── database/
│   ├── migrations/
│   ├── seeds/
│   └── schema.sql
│
├── vector-db/
│   ├── pgvector/
│   └── embeddings/
│
├── storage/
│   ├── uploads/
│   ├── reports/
│   └── backups/
│
├── docker/
├── docs/
└── README.md
```

## Quick Start

### Backend
```bash
cd backend
python -m uvicorn main:app --reload
```

### Frontend (Web)
```bash
cd apps/web
npm install
npm run dev
```

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
