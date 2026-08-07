import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession


class ToolExecutionContext:
    def __init__(self, db: AsyncSession, company_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id


class BaseTool(ABC):
    name: str
    description: str
    parameters_schema: dict

    @abstractmethod
    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        pass


class RAGSearchTool(BaseTool):
    name = "search_knowledge_base"
    description = "Kompaniya hujjatlari va bilimlar bazasidan (RAG) tegishli ma'lumotlarni qidiradi."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Qidirilayotgan savol yoki kalit so'zlar"},
            "top_k": {"type": "integer", "description": "Natijalar soni (default 5)"},
        },
        "required": ["query"],
    }

    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        from app.services.document_service import DocumentService

        query = params.get("query")
        if not query:
            return "Xato: Qidiruv matni (query) ko'rsatilmadi."

        top_k = params.get("top_k", 5)
        doc_service = DocumentService(context.db)
        result = await doc_service.search_rag(context.company_id, query, top_k=top_k)
        return json.dumps({
            "answer_summary": result.get("answer"),
            "sources": result.get("sources", []),
        }, ensure_ascii=False)


class CreateTaskTool(BaseTool):
    name = "create_company_task"
    description = "Kompaniya xodimi uchun yangi vazifa (Task) yaratadi."
    parameters_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Vazifa sarlavhasi"},
            "description": {"type": "string", "description": "Vazifa tafsiloti"},
            "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
        },
        "required": ["title"],
    }

    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        from app.models.task import Task
        from app.repositories.base import BaseRepository

        title = params.get("title")
        description = params.get("description", "")
        priority = params.get("priority", "medium")

        repo = BaseRepository(Task, context.db)
        task = await repo.create(
            company_id=context.company_id,
            created_by=context.user_id,
            title=title,
            description=description,
            priority=priority,
            status="todo",
            is_ai_generated=True,
        )

        return json.dumps({
            "status": "success",
            "task_id": str(task.id),
            "message": f"Vazifa '{title}' muvaffaqiyatli yaratildi.",
        }, ensure_ascii=False)


class SendNotificationTool(BaseTool):
    name = "send_notification"
    description = "Foydalanuvchiga tizim ichida bildirishnoma (Notification) yuboradi."
    parameters_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Bildirishnoma sarlavhasi"},
            "body": {"type": "string", "description": "Bildirishnoma matni"},
        },
        "required": ["title", "body"],
    }

    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        from app.models.notification import Notification
        from app.repositories.base import BaseRepository

        title = params.get("title")
        body = params.get("body")

        repo = BaseRepository(Notification, context.db)
        notif = await repo.create(
            company_id=context.company_id,
            user_id=context.user_id,
            title=title,
            body=body,
        )

        return json.dumps({
            "status": "success",
            "notification_id": str(notif.id),
            "message": "Bildirishnoma yuborildi.",
        }, ensure_ascii=False)


class ExecuteConnectorTool(BaseTool):
    name = "execute_enterprise_connector"
    description = "Tashqi korxona tizimlari (REST API, SQL baza) ulagichlari orqali ma'lumotlarni so'raydi."
    parameters_schema = {
        "type": "object",
        "properties": {
            "connector_id": {"type": "string", "description": "Ulagich identifikatori (masalan: 'erp_rest', 'sales_db')"},
            "target": {"type": "string", "description": "API endpointi yoki SQL SELECT so'rovi"},
            "params": {"type": "object", "description": "Qo'shimcha parametrlar"},
        },
        "required": ["connector_id", "target"],
    }

    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        from app.services.connectors.connector_manager import connector_manager

        connector_id = params.get("connector_id")
        target = params.get("target")
        query_params = params.get("params", {})

        try:
            result = await connector_manager.execute_connector(connector_id, target, query_params)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self.register(RAGSearchTool())
        self.register(CreateTaskTool())
        self.register(SendNotificationTool())
        self.register(ExecuteConnectorTool())

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_tools_prompt(self, allowed_tools: list[str] | None = None) -> str:
        tools_list = []
        for name, tool in self._tools.items():
            if allowed_tools and name not in allowed_tools:
                continue
            tools_list.append(
                f"- Tool: `{tool.name}`\n"
                f"  Tavsifi: {tool.description}\n"
                f"  Parametrlari (JSON Schema): {json.dumps(tool.parameters_schema, ensure_ascii=False)}"
            )
        return "\n\n".join(tools_list)
