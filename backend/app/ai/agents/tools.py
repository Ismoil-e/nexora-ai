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


class ExecuteIntegrationActionTool(BaseTool):
    name = "execute_integration_action"
    description = "Integration Hub orqali tashqi tizimlarda (Google Workspace, Microsoft 365, Telegram, Slack, Jira, GitHub, ERP/CRM, REST) amal bajaradi."
    parameters_schema = {
        "type": "object",
        "properties": {
            "integration_id": {"type": "string", "description": "Tashqi integratsiya UUID si"},
            "action_name": {"type": "string", "description": "Bajariladigan amal (masalan: 'gmail.send_email', 'jira.create_task', 'telegram.send_message', 'github.create_issue')"},
            "params": {"type": "object", "description": "Parametrlar (masalan: filter, query)"},
            "data": {"type": "object", "description": "Yuboriladigan ma'lumotlar foydasi (payload)"},
        },
        "required": ["integration_id", "action_name"],
    }

    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        from app.services.integration_service import IntegrationService

        integration_id_str = params.get("integration_id")
        action_name = params.get("action_name")
        req_params = params.get("params", {})
        req_data = params.get("data", {})

        try:
            svc = IntegrationService(context.db)
            res = await svc.execute_action(
                integration_id=uuid.UUID(integration_id_str),
                company_id=context.company_id,
                action_name=action_name,
                params=req_params,
                data=req_data,
                triggered_by_type="agent",
                triggered_by_id=context.user_id,
            )
            return json.dumps({"success": res.success, "data": res.data, "error": res.error, "message": res.message}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


class IntelligenceSearchTool(BaseTool):
    name = "intelligence_search"
    description = "Hujjatlar bo'yicha semantik + matnli (hybrid) qidiruv: entities, relationships, knowledge graph va citation'lar bilan natija qaytaradi."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Qidirilayotgan savol yoki kalit so'zlar"},
            "top_k": {"type": "integer", "description": "Natijalar soni (default 5)"},
            "document_type": {"type": "string", "description": "Filtr: hujjat turi (Contract, Invoice, Report, ...)"},
        },
        "required": ["query"],
    }

    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        from app.services.document_intelligence_service import DocumentIntelligenceService

        query = params.get("query")
        if not query:
            return "Xato: Qidiruv matni (query) ko'rsatilmadi."

        top_k = int(params.get("top_k", 5))
        svc = DocumentIntelligenceService(context.db)
        try:
            result = await svc.search(
                context.company_id,
                query=query,
                top_k=top_k,
                document_type=params.get("document_type"),
            )
            return json.dumps({
                "total": result["total"],
                "results": result["results"],
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class GetDocumentIntelligenceTool(BaseTool):
    name = "get_document_intelligence"
    description = "Berilgan hujjatning intelligence ma'lumotlarini oladi: entities, relationships, chunks (knowledge sources), processing holati."
    parameters_schema = {
        "type": "object",
        "properties": {
            "document_id": {"type": "string", "description": "Hujjat UUID si"},
        },
        "required": ["document_id"],
    }

    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        from app.services.document_intelligence_service import DocumentIntelligenceService

        document_id = params.get("document_id")
        if not document_id:
            return "Xato: document_id ko'rsatilmadi."

        svc = DocumentIntelligenceService(context.db)
        try:
            result = await svc.get_intelligence(context.company_id, uuid.UUID(document_id))
            return json.dumps({
                "document": result["document"],
                "entity_count": result["entity_count"],
                "relationship_count": result["relationship_count"],
                "chunk_count": result["chunk_count"],
                "entities": result["entities"],
                "relationships": result["relationships"],
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class QueryCompanyKPITool(BaseTool):
    name = "query_company_kpis"
    description = "Kompaniyaning asosiy ko'rsatkichlari (KPI) va operatsion natijalarini hisoblaydi va qaytaradi."
    parameters_schema = {
        "type": "object",
        "properties": {
            "kpi_codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ixtiyoriy KPI kodlari (masalan, ['TASK_COMPLETION_RATE', 'OVERDUE_TASKS_COUNT'])",
            }
        },
    }

    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        from app.services.bi_service import BusinessIntelligenceService

        svc = BusinessIntelligenceService(context.db)
        codes = params.get("kpi_codes")
        results = await svc.calculate_kpis(context.company_id, kpi_codes=codes)
        return json.dumps(
            [
                {
                    "code": r.code,
                    "name": r.name,
                    "value": r.current_value,
                    "unit": r.unit,
                    "status": r.status,
                    "change_pct": r.change_pct,
                }
                for r in results
            ],
            ensure_ascii=False,
        )


class GetBusinessInsightsTool(BaseTool):
    name = "get_business_insights"
    description = "Kompaniya bo'yicha AI tomonidan aniqlangan tahliliy xulosalar (insights), sabablar va tavsiyalarni oladi."
    parameters_schema = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Xulosalar soni (default 5)"}
        },
    }

    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        from app.services.bi_service import BusinessIntelligenceService

        svc = BusinessIntelligenceService(context.db)
        limit = params.get("limit", 5)
        insights = await svc.get_company_insights(context.company_id, limit=limit)
        return json.dumps(
            [
                {
                    "title": i.title,
                    "severity": i.severity,
                    "summary": i.summary,
                    "explanation": i.explanation,
                    "recommended_actions": json.loads(i.recommended_actions) if i.recommended_actions else [],
                }
                for i in insights
            ],
            ensure_ascii=False,
        )


class GenerateExecutiveSummaryTool(BaseTool):
    name = "generate_executive_summary"
    description = "Rahbariyat (CEO, CFO, COO, HR) uchun qisqa va aniq ijroiy hisobot va strategik tavsiyalar yaratadi."
    parameters_schema = {
        "type": "object",
        "properties": {
            "target_role": {"type": "string", "description": "Rahbar roli: CEO, CFO, COO, HR_Director", "default": "CEO"},
            "timeframe": {"type": "string", "description": "Davr (current_month, current_quarter)", "default": "current_month"},
        },
    }

    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        from app.services.bi_service import BusinessIntelligenceService

        svc = BusinessIntelligenceService(context.db)
        role = params.get("target_role", "CEO")
        timeframe = params.get("timeframe", "current_month")
        summary = await svc.generate_executive_summary(context.company_id, target_role=role, timeframe=timeframe)
        return json.dumps(summary, ensure_ascii=False, default=str)


class DetectOperationalRisksTool(BaseTool):
    name = "detect_operational_risks"
    description = "Kompaniyadagi operatsion xatarlar, kechikayotgan vazifalar va to'siqlarni (bottlenecks) aniqlaydi."
    parameters_schema = {"type": "object", "properties": {}}

    async def execute(self, params: dict, context: ToolExecutionContext) -> str:
        from app.services.bi_service import BusinessIntelligenceService

        svc = BusinessIntelligenceService(context.db)
        risks = await svc.detect_risks(context.company_id)
        return json.dumps(
            [
                {
                    "title": r.title,
                    "risk_level": r.risk_level,
                    "description": r.description,
                    "impact": r.impact,
                    "mitigation": r.mitigation_step,
                }
                for r in risks
            ],
            ensure_ascii=False,
        )


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self.register(RAGSearchTool())
        self.register(CreateTaskTool())
        self.register(SendNotificationTool())
        self.register(ExecuteConnectorTool())
        self.register(ExecuteIntegrationActionTool())
        self.register(IntelligenceSearchTool())
        self.register(GetDocumentIntelligenceTool())
        self.register(QueryCompanyKPITool())
        self.register(GetBusinessInsightsTool())
        self.register(GenerateExecutiveSummaryTool())
        self.register(DetectOperationalRisksTool())

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


