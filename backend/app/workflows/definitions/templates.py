"""Default system workflow templates."""

from __future__ import annotations

from typing import Any


def default_workflow_templates() -> list[dict[str, Any]]:
    return [
        {
            "name": "Document Ingest Pipeline",
            "slug": "document-ingest",
            "description": "Upload qilingan hujjat uchun OCR + embeddings + memory update",
            "workflow_type": "event",
            "requires_approval": False,
            "triggers": [{"trigger_type": "document_created"}],
            "steps": [
                {"name": "Run OCR", "action_key": "run_ocr", "step_order": 1, "on_failure": "continue"},
                {"name": "Generate Embeddings", "action_key": "generate_embeddings", "step_order": 2},
                {"name": "Update Memory", "action_key": "update_memory", "step_order": 3},
                {
                    "name": "Notify",
                    "action_key": "create_notification",
                    "step_order": 4,
                    "config": {"title": "Document processed", "body": "Hujjat qayta ishlandi"},
                },
            ],
        },
        {
            "name": "Weekly Summary Report",
            "slug": "weekly-summary-report",
            "description": "Hujjatlarni o'qib summary + report + email",
            "workflow_type": "scheduled",
            "triggers": [{"trigger_type": "cron", "config": {"cron": "0 9 * * 1"}}],
            "steps": [
                {"name": "Read Documents", "action_key": "read_documents", "step_order": 1},
                {"name": "Generate Summary", "action_key": "generate_summary", "step_order": 2},
                {
                    "name": "Generate Report",
                    "action_key": "generate_report",
                    "step_order": 3,
                    "config": {"title": "Weekly Summary"},
                },
                {
                    "name": "Send Email",
                    "action_key": "send_email",
                    "step_order": 4,
                    "config": {"subject": "Weekly Summary", "body": "Hisobot tayyor"},
                },
            ],
        },
        {
            "name": "Task Completion Follow-up",
            "slug": "task-completion-followup",
            "description": "Task tugaganda xulosa va bildirishnoma",
            "workflow_type": "event",
            "triggers": [{"trigger_type": "task_completed"}],
            "steps": [
                {"name": "Generate Summary", "action_key": "generate_summary", "step_order": 1},
                {"name": "Update Memory", "action_key": "update_memory", "step_order": 2},
                {
                    "name": "Notify",
                    "action_key": "create_notification",
                    "step_order": 3,
                    "config": {"title": "Task completed", "body": "Vazifa yakunlandi"},
                },
            ],
        },
        {
            "name": "AI Assisted Planning",
            "slug": "ai-assisted-planning",
            "description": "Planning agent + task yaratish + approval",
            "workflow_type": "approval",
            "requires_approval": True,
            "triggers": [{"trigger_type": "user_request"}, {"trigger_type": "ai_decision"}],
            "steps": [
                {
                    "name": "Trigger Planning Agent",
                    "action_key": "trigger_ai_agent",
                    "step_order": 1,
                    "config": {"agent_key": "planning"},
                },
                {"name": "Request Approval", "action_key": "request_approval", "step_order": 2},
                {
                    "name": "Create Task",
                    "action_key": "create_task",
                    "step_order": 3,
                    "config": {"title": "AI planned follow-up"},
                },
            ],
        },
        {
            "name": "Manual Knowledge Search",
            "slug": "manual-knowledge-search",
            "description": "Qo'lda ishga tushiriladigan knowledge search + summary",
            "workflow_type": "manual",
            "triggers": [{"trigger_type": "user_request"}, {"trigger_type": "api"}],
            "steps": [
                {
                    "name": "Search Knowledge",
                    "action_key": "trigger_ai_agent",
                    "step_order": 1,
                    "config": {"agent_key": "search"},
                },
                {"name": "Generate Summary", "action_key": "generate_summary", "step_order": 2},
                {"name": "Update Memory", "action_key": "update_memory", "step_order": 3},
            ],
        },
    ]
