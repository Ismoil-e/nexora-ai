import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from app.api.v1 import (
    agents,
    auth,
    chats,
    companies,
    dashboard,
    documents,
    notifications,
    reports,
    roles,
    settings,
    tasks,
    users,
    workflows,
)
from app.core.config import settings as app_settings
from app.core.database import close_db, init_db
from app.core.logging import get_logger, setup_logging
from app.core.middleware import register_middleware

setup_logging()
logger = get_logger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "apps" / "web" / "public"
FRONTEND_SRC_DIR = Path(__file__).resolve().parent.parent / "apps" / "web" / "src"


def create_app() -> FastAPI:
    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/openapi.json",
        description="Nexora AI - Multi-tenant AI SaaS Platform Backend",
    )

    register_middleware(app)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_msg = str(exc)
        logger.error("unhandled_error", error=error_msg, path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": error_msg,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail or "Xatolik yuz berdi",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    api_v1_prefix = "/api/v1"

    app.include_router(auth.router, prefix=api_v1_prefix)
    app.include_router(users.router, prefix=api_v1_prefix)
    app.include_router(companies.router, prefix=api_v1_prefix)
    app.include_router(chats.router, prefix=api_v1_prefix)
    app.include_router(documents.router, prefix=api_v1_prefix)
    app.include_router(dashboard.router, prefix=api_v1_prefix)
    app.include_router(notifications.router, prefix=api_v1_prefix)
    app.include_router(agents.router, prefix=api_v1_prefix)
    app.include_router(workflows.router, prefix=api_v1_prefix)
    app.include_router(tasks.router, prefix=api_v1_prefix)
    app.include_router(reports.router, prefix=api_v1_prefix)
    app.include_router(roles.router, prefix=api_v1_prefix)
    app.include_router(settings.router, prefix=api_v1_prefix)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "service": app_settings.app_name, "version": app_settings.app_version}

    @app.post("/api/chat")
    async def chat_proxy(request: Request):
        from app.services.ai_service import AIService
        from app.core.database import async_session_factory

        body = await request.json()
        user_text = body.get("message", "")
        history = body.get("history", [])

        system_prompt = "Sen Nexora AI yordamchisisan. Foydalanuvchilarga yordam berish uchun o'zbek tilida javob ber."

        messages = []
        for msg in history:
            role = "assistant" if msg.get("role") == "model" else "user"
            content = msg.get("parts", [{}])[0].get("text", "") if isinstance(msg.get("parts"), list) else msg.get("content", "")
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_text})

        async with async_session_factory() as session:
            service = AIService(db=session)
            result = await service.chat(messages=messages, system_prompt=system_prompt)

        return {"reply": result["content"]}

    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        if path.startswith("api/") or path.startswith("docs") or path.startswith("redoc") or path.startswith("openapi"):
            raise HTTPException(status_code=404, detail="Not found")
        for base in (FRONTEND_DIR, FRONTEND_SRC_DIR):
            file = base / path
            if file.exists() and file.is_file():
                return FileResponse(file)
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.on_event("startup")
    async def startup():
        logger.info("starting_server", service=app_settings.app_name)
        await init_db()
        from app.agents.bootstrap import bootstrap_agents
        from app.workflows.bootstrap import bootstrap_workflows

        bootstrap_agents()
        bootstrap_workflows()
        logger.info("database_initialized")
        logger.info("agent_framework_bootstrapped")
        logger.info("workflow_engine_bootstrapped")

    @app.on_event("shutdown")
    async def shutdown():
        await close_db()
        logger.info("server_shutdown")

    return app


app = create_app()


def run():
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=app_settings.debug,
        log_level="info",
    )


if __name__ == "__main__":
    run()
