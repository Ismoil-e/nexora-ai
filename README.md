# Nexora AI

Multi-tenant AI SaaS platform for businesses.

## Architecture

- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Backend**: FastAPI (Python 3.13+)
- **Database**: PostgreSQL 17 + pgvector
- **Cache**: Redis 7
- **Queue**: RabbitMQ 4
- **Storage**: MinIO (S3-compatible)
- **AI**: OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter

## Project Structure

```
nexora-ai/
├── frontend/              # Static frontend files
│   ├── index.html
│   ├── chat.html
│   ├── login.html
│   ├── styles.css
│   └── script.js
├── backend/               # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/        # Route handlers
│   │   ├── core/          # Config, DB, security, logging
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── repositories/  # Data access layer
│   │   ├── services/      # Business logic
│   │   ├── ai/            # AI provider abstraction
│   │   ├── storage/       # File storage (MinIO)
│   │   ├── workers/       # Background tasks
│   │   └── utils/         # Helpers, exceptions
│   ├── migrations/        # Alembic migrations
│   ├── docker/            # Docker configs
│   ├── docker-compose.yml
│   └── main.py
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.13+
- Docker & Docker Compose

### Backend

```bash
cd backend
cp .env.example .env
docker-compose up -d
```

### API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Register new user |
| POST | /api/v1/auth/login | Login |
| POST | /api/v1/auth/google | Google OAuth login |
| GET | /api/v1/users/me | Get profile |
| PUT | /api/v1/users/me | Update profile |
| GET | /api/v1/chats | List chats |
| POST | /api/v1/chats | Create chat |
| POST | /api/v1/chats/{id}/messages | Send message |
| POST | /api/v1/documents/upload | Upload document |
| POST | /api/v1/documents/rag | RAG query |
| GET | /api/v1/agents | List AI agents |
| POST | /api/v1/agents/{id}/execute | Execute agent |
| GET | /api/v1/dashboard/stats | Dashboard stats |
