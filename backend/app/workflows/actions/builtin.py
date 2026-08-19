"""Built-in workflow actions. Each uses injected services — no direct DB access."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.workflows.contracts.types import ActionContext, ActionResult
from app.workflows.interfaces.base_action import BaseAction
from app.utils.exceptions import ValidationException


class _ServiceAction(BaseAction):
    def _svc(self, context: ActionContext, name: str) -> Any:
        if name not in context.services:
            raise RuntimeError(f"Service '{name}' inject qilinmagan (action={self.action_key})")
        return context.services[name]


class ReadDocumentsAction(_ServiceAction):
    action_key = "read_documents"
    display_name = "Read Documents"
    description = "Kompaniya hujjatlarini o'qiydi / ro'yxatlaydi"
    category = "documents"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        doc_service = self._svc(context, "document_service")
        page = int(context.config.get("page") or 1)
        page_size = int(context.config.get("page_size") or 20)
        data = await doc_service.get_documents(context.company_id, page=page, page_size=page_size)
        return ActionResult(success=True, output=data, message="Documents loaded")


class AnalyzeExcelAction(_ServiceAction):
    action_key = "analyze_excel"
    display_name = "Analyze Excel"
    description = "Excel/CSV hujjatini tahlil qilish (RAG/search orqali)"
    category = "documents"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("query") or context.payload.get("query")):
            raise ValidationException(detail="analyze_excel uchun query kerak")

    async def execute(self, context: ActionContext) -> ActionResult:
        doc_service = self._svc(context, "document_service")
        query = context.config.get("query") or context.payload.get("query")
        result = await doc_service.search_rag(context.company_id, query, top_k=int(context.config.get("top_k") or 5))
        return ActionResult(success=True, output=result, message="Excel/document analysis complete")


class GenerateReportAction(_ServiceAction):
    action_key = "generate_report"
    display_name = "Generate Report"
    description = "Hisobot yozuvini yaratadi (Report model)"
    category = "reports"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("title") or context.payload.get("title")):
            raise ValidationException(detail="generate_report uchun title kerak")

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.models.report import Report
        from app.repositories.base import BaseRepository

        # Action uses repository only via a thin report service if present; fallback BaseRepository
        # is allowed inside action infrastructure adapter injected as report_repo_factory.
        db = self._svc(context, "db")
        if not context.user_id:
            return ActionResult(success=False, message="created_by (user) talab qilinadi", should_stop=True)
        title = context.config.get("title") or context.payload.get("title")
        content = context.config.get("content") or context.payload.get("content") or context.shared_state.get("summary")
        repo = BaseRepository(Report, db)
        report = await repo.create(
            company_id=context.company_id,
            title=title,
            content=content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
            report_type=context.config.get("report_type") or "workflow",
            status="generated",
            created_by=context.user_id,
        )
        return ActionResult(
            success=True,
            output={"report_id": str(report.id), "title": title},
            message="Report generated",
        )


class GenerateWordDocumentAction(_ServiceAction):
    action_key = "generate_word_document"
    display_name = "Generate Word Document"
    description = "Word hujjat kontentini tayyorlaydi (storage path placeholder)"
    category = "documents"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        title = context.config.get("title") or context.payload.get("title") or "workflow-document"
        body = context.config.get("body") or context.shared_state.get("summary") or ""
        # Production: python-docx + MinIO. Here we emit a structured artifact descriptor.
        artifact = {
            "format": "docx",
            "title": title,
            "body_preview": str(body)[:1000],
            "status": "prepared",
        }
        context.shared_state["word_artifact"] = artifact
        return ActionResult(success=True, output=artifact, message="Word document prepared")


class GeneratePdfReportAction(_ServiceAction):
    action_key = "generate_pdf_report"
    display_name = "Generate PDF Report"
    description = "PDF hisobot artifactini tayyorlaydi"
    category = "reports"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        title = context.config.get("title") or "workflow-report"
        artifact = {
            "format": "pdf",
            "title": title,
            "source": context.shared_state.get("summary") or context.payload,
            "status": "prepared",
        }
        context.shared_state["pdf_artifact"] = artifact
        return ActionResult(success=True, output=artifact, message="PDF report prepared")


class ReadDatabaseAction(_ServiceAction):
    action_key = "read_database"
    display_name = "Read Database"
    description = "Enterprise connector orqali DB o'qish"
    category = "connectors"

    async def validate(self, context: ActionContext) -> None:
        if not context.config.get("connector_id"):
            raise ValidationException(detail="connector_id talab qilinadi")
        if not context.config.get("target"):
            raise ValidationException(detail="target (SQL) talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.services.connectors.connector_manager import connector_manager

        result = await connector_manager.execute_connector(
            context.config["connector_id"],
            context.config["target"],
            context.config.get("params") or {},
        )
        return ActionResult(success=True, output=result if isinstance(result, dict) else {"data": result})


class UpdateDatabaseAction(_ServiceAction):
    action_key = "update_database"
    display_name = "Update Database Records"
    description = "Connector orqali DB yozish (faqat ruxsat etilgan connectorlar)"
    category = "connectors"

    async def validate(self, context: ActionContext) -> None:
        if not context.config.get("connector_id") or not context.config.get("target"):
            raise ValidationException(detail="connector_id va target talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.services.connectors.connector_manager import connector_manager

        result = await connector_manager.execute_connector(
            context.config["connector_id"],
            context.config["target"],
            context.config.get("params") or {},
        )
        return ActionResult(success=True, output=result if isinstance(result, dict) else {"data": result})


class CallExternalApiAction(_ServiceAction):
    action_key = "call_external_api"
    display_name = "Call External API"
    description = "REST connector orqali tashqi API chaqiradi"
    category = "connectors"

    async def validate(self, context: ActionContext) -> None:
        if not context.config.get("connector_id"):
            raise ValidationException(detail="connector_id talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.services.connectors.connector_manager import connector_manager

        result = await connector_manager.execute_connector(
            context.config.get("connector_id"),
            context.config.get("target") or "/",
            context.config.get("params") or {},
        )
        return ActionResult(success=True, output=result if isinstance(result, dict) else {"data": result})


class SendEmailAction(_ServiceAction):
    action_key = "send_email"
    display_name = "Send Email"
    description = "Email yuborish (notification kanaliga map qilinadi)"
    category = "notifications"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("subject") or context.payload.get("subject")):
            raise ValidationException(detail="email subject talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        notif = self._svc(context, "notification_service")
        subject = context.config.get("subject") or context.payload.get("subject")
        body = context.config.get("body") or context.payload.get("body") or ""
        to_user = context.config.get("user_id") or context.user_id
        notification = await notif.create_notification(
            company_id=context.company_id,
            user_id=uuid.UUID(str(to_user)) if to_user else None,
            title=f"[Email] {subject}",
            body=str(body),
            notification_type="email",
            reference_type="workflow_execution",
            reference_id=context.execution_id,
        )
        return ActionResult(
            success=True,
            output={"notification_id": str(notification.id), "channel": "email"},
            message="Email notification queued",
        )


class SendTelegramAction(_ServiceAction):
    action_key = "send_telegram"
    display_name = "Send Telegram Message"
    description = "Telegram xabarini notification sifatida navbatga qo'yadi"
    category = "notifications"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("message") or context.payload.get("message")):
            raise ValidationException(detail="telegram message talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        notif = self._svc(context, "notification_service")
        message = context.config.get("message") or context.payload.get("message")
        notification = await notif.create_notification(
            company_id=context.company_id,
            user_id=context.user_id,
            title="[Telegram]",
            body=str(message),
            notification_type="telegram",
            reference_type="workflow_execution",
            reference_id=context.execution_id,
        )
        return ActionResult(
            success=True,
            output={"notification_id": str(notification.id), "channel": "telegram"},
            message="Telegram notification queued",
        )


class CreateNotificationAction(_ServiceAction):
    action_key = "create_notification"
    display_name = "Create Notification"
    description = "Ichki bildirishnoma yaratadi"
    category = "notifications"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("title") or context.payload.get("title")):
            raise ValidationException(detail="notification title talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        notif = self._svc(context, "notification_service")
        title = context.config.get("title") or context.payload.get("title")
        body = context.config.get("body") or context.payload.get("body") or ""
        notification = await notif.create_notification(
            company_id=context.company_id,
            user_id=context.user_id,
            title=title,
            body=str(body),
            notification_type=context.config.get("notification_type") or "workflow",
            reference_type="workflow_execution",
            reference_id=context.execution_id,
        )
        return ActionResult(success=True, output={"notification_id": str(notification.id)})


class GenerateDashboardAction(_ServiceAction):
    action_key = "generate_dashboard"
    display_name = "Generate Dashboard"
    description = "Dashboard spekini shared state ga yozadi"
    category = "analytics"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        widgets = context.config.get("widgets") or context.shared_state.get("metrics") or []
        dashboard = {
            "title": context.config.get("title") or "Workflow Dashboard",
            "widgets": widgets,
            "generated_from_execution": str(context.execution_id),
        }
        context.shared_state["dashboard"] = dashboard
        return ActionResult(success=True, output=dashboard)


class GenerateSummaryAction(_ServiceAction):
    action_key = "generate_summary"
    display_name = "Generate Summary"
    description = "AI provider orqali qisqa xulosa yaratadi"
    category = "ai"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        ai = self._svc(context, "ai_service")
        source = (
            context.config.get("text")
            or context.payload.get("text")
            or json.dumps(context.shared_state, ensure_ascii=False)[:4000]
        )
        response = await ai.chat(
            messages=[{"role": "user", "content": f"Quyidagi ma'lumotni qisqa xulosa qil:\n{source}"}],
            system_prompt="Sen Nexora Workflow Summary agentisan.",
            temperature=0.3,
        )
        summary = response.get("content", "")
        context.shared_state["summary"] = summary
        return ActionResult(
            success=True,
            output={"summary": summary, "token_count": response.get("token_count", 0)},
        )


class CreateTaskAction(_ServiceAction):
    action_key = "create_task"
    display_name = "Create Task"
    description = "Yangi vazifa yaratadi"
    category = "tasks"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("title") or context.payload.get("title")):
            raise ValidationException(detail="task title talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.models.task import Task
        from app.repositories.base import BaseRepository

        db = self._svc(context, "db")
        if not context.user_id:
            return ActionResult(success=False, message="created_by (user) talab qilinadi", should_stop=True)
        title = context.config.get("title") or context.payload.get("title")
        description = context.config.get("description") or context.payload.get("description")
        assigned_to = context.config.get("assigned_to") or context.payload.get("assigned_to")
        repo = BaseRepository(Task, db)
        task = await repo.create(
            company_id=context.company_id,
            created_by=context.user_id,
            assigned_to=uuid.UUID(str(assigned_to)) if assigned_to else None,
            title=title,
            description=description,
            priority=context.config.get("priority") or "medium",
            status="todo",
            is_ai_generated=True,
        )
        return ActionResult(success=True, output={"task_id": str(task.id), "title": title})


class AssignTaskAction(_ServiceAction):
    action_key = "assign_task"
    display_name = "Assign Task"
    description = "Mavjud vazifani foydalanuvchiga biriktiradi"
    category = "tasks"

    async def validate(self, context: ActionContext) -> None:
        if not context.config.get("task_id") or not context.config.get("assigned_to"):
            raise ValidationException(detail="task_id va assigned_to talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.models.task import Task
        from app.repositories.base import BaseRepository

        db = self._svc(context, "db")
        repo = BaseRepository(Task, db)
        task = await repo.update(
            uuid.UUID(str(context.config["task_id"])),
            assigned_to=uuid.UUID(str(context.config["assigned_to"])),
        )
        if not task:
            return ActionResult(success=False, message="Task topilmadi", should_stop=True)
        return ActionResult(success=True, output={"task_id": str(task.id), "assigned_to": str(task.assigned_to)})


class ScheduleMeetingAction(_ServiceAction):
    action_key = "schedule_meeting"
    display_name = "Schedule Meeting"
    description = "Uchrashuv rejasini shared state / notification sifatida yaratadi"
    category = "collaboration"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("title") or context.payload.get("title")):
            raise ValidationException(detail="meeting title talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        meeting = {
            "title": context.config.get("title") or context.payload.get("title"),
            "starts_at": context.config.get("starts_at"),
            "participants": context.config.get("participants") or [],
            "status": "scheduled",
        }
        context.shared_state["meeting"] = meeting
        notif = self._svc(context, "notification_service")
        await notif.create_notification(
            company_id=context.company_id,
            user_id=context.user_id,
            title=f"Meeting: {meeting['title']}",
            body=json.dumps(meeting, ensure_ascii=False),
            notification_type="meeting",
            reference_type="workflow_execution",
            reference_id=context.execution_id,
        )
        return ActionResult(success=True, output=meeting)


class UpdateMemoryAction(_ServiceAction):
    action_key = "update_memory"
    display_name = "Update Memory"
    description = "Cognitive / chat memory ga episode yozadi"
    category = "memory"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        memory = context.services.get("memory_engine")
        content = context.config.get("content") or context.shared_state.get("summary") or context.payload
        if memory is None:
            context.shared_state.setdefault("memory_updates", []).append(content)
            return ActionResult(success=True, output={"stored": "shared_state"}, message="Memory queued in state")

        from app.cognitive.contracts.frames import ContextFrame

        frame = ContextFrame(
            company_id=context.company_id,
            user_id=context.user_id or context.company_id,
            conversation_id=uuid.UUID(str(context.payload["chat_id"])) if context.payload.get("chat_id") else None,
        )
        ref = await memory.save_episode(
            frame=frame,
            agent_key="workflow",
            input_text=str(context.payload)[:2000],
            output_text=str(content)[:4000],
            metadata={"execution_id": str(context.execution_id)},
        )
        return ActionResult(success=True, output={"memory_ref": ref})


class TriggerAiAgentAction(_ServiceAction):
    action_key = "trigger_ai_agent"
    display_name = "Trigger AI Agent"
    description = "Agent Framework dagi agentni ishga tushiradi"
    category = "ai"

    async def validate(self, context: ActionContext) -> None:
        if not context.config.get("agent_key"):
            raise ValidationException(detail="agent_key talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        agent_service = self._svc(context, "agent_service")
        input_text = context.config.get("input") or context.payload.get("input") or context.payload.get("query") or "Workflow agent run"
        result = await agent_service.run_framework_agent(
            agent_key=context.config["agent_key"],
            user_id=context.user_id or context.company_id,
            company_id=context.company_id,
            input_text=str(input_text),
            metadata={"workflow_execution_id": str(context.execution_id)},
            async_mode=False,
        )
        context.shared_state["agent_result"] = result
        return ActionResult(success=bool(result.get("success", True)), output=result)


class RunOcrAction(_ServiceAction):
    action_key = "run_ocr"
    display_name = "Run OCR"
    description = "OCR worker ni navbatga qo'yadi"
    category = "documents"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("document_id") or context.payload.get("document_id")):
            raise ValidationException(detail="document_id talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        document_id = str(context.config.get("document_id") or context.payload.get("document_id"))
        file_path = str(context.config.get("file_path") or context.payload.get("file_path") or "")
        task_id = None
        try:
            from app.workers.ocr_worker import process_ocr

            async_result = process_ocr.delay(file_path, document_id)
            task_id = async_result.id
        except Exception as exc:
            return ActionResult(
                success=True,
                output={"document_id": document_id, "queued": False, "error": str(exc)},
                message="OCR queue unavailable; recorded intent",
            )
        return ActionResult(success=True, output={"document_id": document_id, "celery_task_id": task_id, "queued": True})


class GenerateEmbeddingsAction(_ServiceAction):
    action_key = "generate_embeddings"
    display_name = "Generate Embeddings"
    description = "Embedding worker ni navbatga qo'yadi"
    category = "documents"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("document_id") or context.payload.get("document_id")):
            raise ValidationException(detail="document_id talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        document_id = str(context.config.get("document_id") or context.payload.get("document_id"))
        context.shared_state.setdefault("embedding_jobs", []).append(document_id)
        return ActionResult(
            success=True,
            output={"document_id": document_id, "queued": True, "note": "embedding intent recorded"},
            message="Embedding job recorded for worker processing",
        )


class RequestApprovalAction(_ServiceAction):
    action_key = "request_approval"
    display_name = "Request Approval"
    description = "Workflowni approval kutish holatiga o'tkazadi"
    category = "control"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        return ActionResult(
            success=True,
            requires_approval=True,
            should_stop=True,
            output={
                "approval_required": True,
                "requested_from": context.config.get("requested_from"),
                "reason": context.config.get("reason") or "Workflow approval required",
            },
            message="Approval requested",
        )


class FuturePluginAction(_ServiceAction):
    action_key = "execute_future_plugin"
    display_name = "Execute Future Plugin"
    description = "Kelajakdagi pluginlar uchun extension point"
    category = "plugins"

    async def validate(self, context: ActionContext) -> None:
        if not context.config.get("plugin_key"):
            raise ValidationException(detail="plugin_key talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        plugin_key = context.config["plugin_key"]
        handler = context.services.get("plugin_registry", {}).get(plugin_key) if isinstance(context.services.get("plugin_registry"), dict) else None
        if handler is None:
            return ActionResult(
                success=True,
                output={"plugin_key": plugin_key, "status": "noop", "params": context.config.get("params") or {}},
                message="Plugin not installed; noop recorded",
            )
        result = await handler(context)
        return ActionResult(success=True, output=result if isinstance(result, dict) else {"result": result})


class ProcessDocumentAction(_ServiceAction):
    action_key = "process_document"
    display_name = "Process Document"
    description = "Hujjatni Document Intelligence pipeline orqali qayta ishlaydi (navbatga qo'yadi)"
    category = "documents"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("document_id") or context.payload.get("document_id")):
            raise ValidationException(detail="process_document uchun document_id talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.workers.document_worker import enqueue_document_processing

        document_id = str(context.config.get("document_id") or context.payload.get("document_id"))
        svc = self._svc(context, "document_intelligence_service")
        try:
            await svc.assert_document_exists(context.company_id, document_id)
        except Exception as exc:
            return ActionResult(
                success=False,
                message=f"Document topilmadi yoki kompaniyaga tegishli emas: {exc}",
                should_stop=True,
            )
        mode = enqueue_document_processing(document_id)
        return ActionResult(
            success=True,
            output={"document_id": document_id, "queue_mode": mode},
            message="Document processing queued",
        )


class IntelligenceSearchAction(_ServiceAction):
    action_key = "intelligence_search"
    display_name = "Intelligence Search"
    description = "Hujjatlar bo'yicha semantik + matnli qidiruv (entities, graph, citations bilan)"
    category = "documents"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("query") or context.payload.get("query")):
            raise ValidationException(detail="intelligence_search uchun query talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        svc = self._svc(context, "document_intelligence_service")
        query = context.config.get("query") or context.payload.get("query")
        top_k = int(context.config.get("top_k") or 5)
        result = await svc.search(context.company_id, query=query, top_k=top_k)
        return ActionResult(success=True, output=result, message="Intelligence search complete")


class ReindexDocumentAction(_ServiceAction):
    action_key = "reindex_document"
    display_name = "Reindex Document"
    description = "Hujjat chunklarining embeddinglarini yangi model/versiya bilan qayta yaratadi"
    category = "documents"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("document_id") or context.payload.get("document_id")):
            raise ValidationException(detail="reindex_document uchun document_id talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        svc = self._svc(context, "document_intelligence_service")
        document_id = uuid.UUID(str(context.config.get("document_id") or context.payload.get("document_id")))
        result = await svc.reindex_document(context.company_id, document_id)
        return ActionResult(success=True, output=result, message="Document reindexed")


class ExecuteIntegrationAction(_ServiceAction):
    action_key = "execute_integration"
    display_name = "Execute Enterprise Integration Action"
    description = "Integration Hub orqali korxona integratsiyasida (Google, Microsoft, Telegram, Slack, Jira, GitHub, ERP) amal bajarish"
    category = "integrations"

    async def validate(self, context: ActionContext) -> None:
        if not (context.config.get("integration_id") or context.payload.get("integration_id")):
            raise ValidationException(detail="execute_integration uchun integration_id talab qilinadi")
        if not (context.config.get("action_name") or context.payload.get("action_name")):
            raise ValidationException(detail="execute_integration uchun action_name talab qilinadi")

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.services.integration_service import IntegrationService

        db = self._svc(context, "db")
        integration_id_str = context.config.get("integration_id") or context.payload.get("integration_id")
        action_name = context.config.get("action_name") or context.payload.get("action_name")
        params = context.config.get("params") or context.payload.get("params") or {}
        data = context.config.get("data") or context.payload.get("data") or {}

        svc = IntegrationService(db)
        res = await svc.execute_action(
            integration_id=uuid.UUID(str(integration_id_str)),
            company_id=context.company_id,
            action_name=action_name,
            params=params,
            data=data,
            triggered_by_type="workflow",
            triggered_by_id=context.user_id,
        )

        return ActionResult(
            success=res.success,
            output=res.data,
            message=res.message or "Integration action executed",
            error=res.error,
        )


class CalculateKPIsAction(_ServiceAction):
    action_key = "calculate_kpis"
    display_name = "Calculate Company KPIs"
    description = "Kompaniyaning barcha yoki tanlangan KPI ko'rsatkichlarini qayta hisoblaydi"
    category = "analytics"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.services.bi_service import BusinessIntelligenceService

        db = self._svc(context, "db")
        svc = BusinessIntelligenceService(db)
        kpi_codes = context.config.get("kpi_codes") or context.payload.get("kpi_codes")
        res = await svc.calculate_kpis(context.company_id, kpi_codes=kpi_codes)
        return ActionResult(
            success=True,
            output=[{"code": r.code, "value": r.current_value, "status": r.status} for r in res],
            message=f"{len(res)} ta KPI hisoblandi",
        )


class GenerateInsightsAction(_ServiceAction):
    action_key = "generate_insights"
    display_name = "Generate Business Insights"
    description = "AI orqali avtomatik tahliliy xulosalar (insights) va sabablarni shakllantiradi"
    category = "analytics"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.services.bi_service import BusinessIntelligenceService

        db = self._svc(context, "db")
        svc = BusinessIntelligenceService(db)
        insights = await svc.generate_insights(context.company_id, force_refresh=True)
        return ActionResult(
            success=True,
            output=[{"title": i.title, "severity": i.severity, "summary": i.summary} for i in insights],
            message=f"{len(insights)} ta insight yaratildi",
        )


class EvaluateAlertRulesAction(_ServiceAction):
    action_key = "evaluate_alert_rules"
    display_name = "Evaluate Alert Rules"
    description = "Kompaniya ogohlantirish qoidalarini tekshiradi va chegara buzilganda alert hosil qiladi"
    category = "monitoring"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.services.bi_service import BusinessIntelligenceService

        db = self._svc(context, "db")
        svc = BusinessIntelligenceService(db)
        alerts = await svc.evaluate_alerts(context.company_id)
        return ActionResult(
            success=True,
            output=[{"title": a.title, "severity": a.severity, "message": a.message} for a in alerts],
            message=f"{len(alerts)} ta ogohlantirish qayd etildi",
        )


class GenerateExecutiveSummaryAction(_ServiceAction):
    action_key = "generate_executive_summary"
    display_name = "Generate Executive Summary"
    description = "Rahbariyat uchun qisqa va aniq ijroiy sharh yaratadi"
    category = "reports"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.services.bi_service import BusinessIntelligenceService

        db = self._svc(context, "db")
        svc = BusinessIntelligenceService(db)
        role = context.config.get("target_role") or context.payload.get("target_role") or "CEO"
        timeframe = context.config.get("timeframe") or context.payload.get("timeframe") or "current_month"
        summary = await svc.generate_executive_summary(context.company_id, target_role=role, timeframe=timeframe)
        return ActionResult(
            success=True,
            output=summary,
            message="Executive summary generated successfully",
        )


class GenerateBIReportAction(_ServiceAction):
    action_key = "generate_bi_report"
    display_name = "Generate BI Report"
    description = "To'liq biznes hisobotini (Markdown/JSON) yaratadi va bazaga saqlaydi"
    category = "reports"

    async def validate(self, context: ActionContext) -> None:
        return None

    async def execute(self, context: ActionContext) -> ActionResult:
        from app.services.bi_service import BusinessIntelligenceService

        db = self._svc(context, "db")
        svc = BusinessIntelligenceService(db)
        title = context.config.get("title") or context.payload.get("title") or "Oylik Tahliliy Hisobot"
        timeframe = context.config.get("timeframe") or context.payload.get("timeframe") or "current_month"
        fmt = context.config.get("format") or context.payload.get("format") or "markdown"

        report = await svc.generate_bi_report(
            company_id=context.company_id,
            user_id=context.user_id,
            title=title,
            timeframe=timeframe,
            format=fmt,
        )
        return ActionResult(
            success=True,
            output={"report_id": str(report.id), "title": report.title, "format": report.format},
            message=f"Report '{report.title}' successfully generated",
        )


DEFAULT_ACTIONS: list[BaseAction] = [
    ReadDocumentsAction(),
    AnalyzeExcelAction(),
    GenerateReportAction(),
    GenerateWordDocumentAction(),
    GeneratePdfReportAction(),
    ReadDatabaseAction(),
    UpdateDatabaseAction(),
    CallExternalApiAction(),
    SendEmailAction(),
    SendTelegramAction(),
    CreateNotificationAction(),
    GenerateDashboardAction(),
    GenerateSummaryAction(),
    CreateTaskAction(),
    AssignTaskAction(),
    ScheduleMeetingAction(),
    UpdateMemoryAction(),
    TriggerAiAgentAction(),
    RunOcrAction(),
    GenerateEmbeddingsAction(),
    RequestApprovalAction(),
    FuturePluginAction(),
    ExecuteIntegrationAction(),
    ProcessDocumentAction(),
    IntelligenceSearchAction(),
    ReindexDocumentAction(),
    CalculateKPIsAction(),
    GenerateInsightsAction(),
    EvaluateAlertRulesAction(),
    GenerateExecutiveSummaryAction(),
    GenerateBIReportAction(),
]


