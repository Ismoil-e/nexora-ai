"""Tests for AI Orchestrator components."""

import uuid

import pytest

from app.orchestrator.model_router import (
    ModelRouter,
    TaskType,
    classify_task_type,
    model_router,
    DEFAULT_MODEL_CATALOG,
)
from app.orchestrator.task_planner import (
    TaskPlanner,
    ExecutionStrategy,
    SubtaskStatus,
    classify_intent,
)
from app.orchestrator.approval_service import (
    ApprovalService,
    ApprovalStatus,
    RiskLevel,
    _APPROVAL_REQUIRED_ACTIONS,
)
from app.orchestrator.execution_tracer import (
    ExecutionTracer,
    TraceEventType,
    execution_tracer,
)
from app.orchestrator.usage_service import (
    AIUsageLimits,
    estimate_cost,
)


# ============================================================================
# Model Router Tests
# ============================================================================


class TestTaskClassification:
    def test_classify_code_request(self):
        assert classify_task_type("def foo(): pass") == TaskType.CODE

    def test_classify_analytics_request(self):
        assert classify_task_type("Sotish tahlilini ko'rsat") == TaskType.ANALYTICS

    def test_classify_report_request(self):
        # "hisobot" matches report_generation keywords, but "tahlil" in analytics wins if present
        result = classify_task_type("Hisobot yaratib ber")
        assert result in (TaskType.REPORT_GENERATION, TaskType.ANALYTICS)

    def test_classify_planning_request(self):
        assert classify_task_type("Reja tuzib ber keyingi qadamlarni") == TaskType.PLANNING

    def test_classify_document_request(self):
        # "tahlil" matches analytics keywords first; use doc-specific terms
        result = classify_task_type("pdf hujjatni o'qib ber")
        assert result == TaskType.DOCUMENT_ANALYSIS

    def test_classify_search_request(self):
        result = classify_task_type("qidiruv qil mevalar haqida")
        assert result in (TaskType.SEARCH, TaskType.CHAT)

    def test_classify_forecast_request(self):
        assert classify_task_type("Prognoz qil kelajakni") == TaskType.FORECASTING

    def test_classify_summary_request(self):
        result = classify_task_type("matnni qisqartirib ber")
        assert result in (TaskType.SUMMARIZATION, TaskType.REPORT_GENERATION, TaskType.CHAT)

    def test_classify_simple_chat(self):
        assert classify_task_type("salom") == TaskType.CHAT

    def test_classify_with_explicit_type(self):
        assert classify_task_type("anything", {"task_type": "code"}) == TaskType.CODE


class TestModelRouter:
    def test_route_chat(self):
        router = ModelRouter()
        decision = router.route(task_type="chat", user_input="salom")
        assert decision.provider in ("openai", "gemini", "openrouter")
        assert decision.model
        assert decision.temperature >= 0
        assert decision.max_tokens > 0

    def test_route_code(self):
        router = ModelRouter()
        decision = router.route(task_type="code", user_input="def foo(): pass")
        # Should prefer a code-capable model
        assert decision.model

    def test_route_reasoning(self):
        router = ModelRouter()
        decision = router.route(task_type="reasoning", user_input="murakkab tahlil")
        assert decision.model

    def test_route_with_preferred_model(self):
        router = ModelRouter()
        decision = router.route(
            task_type="chat",
            user_input="test",
            preferred_model="gpt-4o",
        )
        assert decision.model == "gpt-4o"
        assert decision.provider == "openai"

    def test_route_with_preferred_provider(self):
        router = ModelRouter()
        decision = router.route(
            task_type="chat",
            user_input="test",
            preferred_provider="gemini",
        )
        assert decision.provider == "gemini"

    def test_route_cost_constraint(self):
        router = ModelRouter()
        decision = router.route(
            task_type="chat",
            user_input="test",
            max_cost_per_1k=0.0001,
        )
        # Should pick a cheap model
        assert decision.model

    def test_route_no_candidates_fallback(self):
        router = ModelRouter(
            provider_policy={"allowed_providers": ["nonexistent"]}
        )
        decision = router.route(task_type="chat", user_input="test")
        # Should fallback to defaults
        assert decision.provider == "gemini"
        assert decision.model == "gemini-2.5-flash"

    def test_list_models_all(self):
        router = ModelRouter()
        models = router.list_models()
        assert len(models) > 0

    def test_list_models_by_provider(self):
        router = ModelRouter()
        models = router.list_models(provider="gemini")
        assert all(m["provider"] == "gemini" for m in models)

    def test_get_model_info(self):
        router = ModelRouter()
        info = router.get_model_info("openai", "gpt-4o")
        assert info is not None
        assert info.context_window == 128000

    def test_get_model_info_not_found(self):
        router = ModelRouter()
        info = router.get_model_info("nonexistent", "model")
        assert info is None

    def test_default_catalog_has_models(self):
        assert len(DEFAULT_MODEL_CATALOG) > 0

    def test_process_singleton(self):
        assert model_router is not None
        assert isinstance(model_router, ModelRouter)


# ============================================================================
# Task Planner Tests
# ============================================================================


class TestTaskPlanner:
    def test_should_not_decompose_short(self):
        planner = TaskPlanner()
        assert planner.should_decompose("salom") is False

    def test_should_decompose_long_analytics(self):
        planner = TaskPlanner()
        assert planner.should_decompose(
            "O'tgan chorakdagi sotish natijalarini tahlil qilib, sabablarni aniqla va hisobot tayyorla. Keyin vazifalarni yarat."
        ) is True

    def test_should_decompose_explicit(self):
        planner = TaskPlanner()
        assert planner.should_decompose(
            "short query", {"force_orchestrate": True}
        ) is True

    def test_should_not_decompose_explicit_single(self):
        planner = TaskPlanner()
        assert planner.should_decompose(
            "long query that would normally decompose", {"single_agent": True}
        ) is False

    def test_plan_simple_chat(self):
        planner = TaskPlanner()
        plan = planner.plan("salom")
        assert plan.user_intent == "simple_chat"
        assert len(plan.subtasks) == 1
        assert plan.subtasks[0].agent_key == "chat"

    def test_plan_analyze_and_report(self):
        planner = TaskPlanner()
        plan = planner.plan("Sotish tahlilini qilib hisobot tayyorla")
        assert plan.user_intent == "analyze_and_report"
        assert len(plan.subtasks) >= 3

    def test_plan_search_and_summarize(self):
        planner = TaskPlanner()
        plan = planner.plan("Ma'lumotlarni qidirib qisqacha xulosa chiqar")
        assert plan.user_intent == "search_and_summarize"

    def test_plan_plan_and_execute(self):
        planner = TaskPlanner()
        plan = planner.plan("Reja tuzib ber keyingi qadamlarni vazifalarni yarat")
        assert plan.user_intent == "plan_and_execute"

    def test_plan_risk_assessment(self):
        planner = TaskPlanner()
        plan = planner.plan("Operatsion xatarlarni aniqlab ogohlantirish ber")
        assert plan.user_intent == "risk_assessment"

    def test_plan_has_id(self):
        planner = TaskPlanner()
        plan = planner.plan("test input")
        assert plan.id
        assert len(plan.id) > 0

    def test_plan_display(self):
        planner = TaskPlanner()
        plan = planner.plan("Sotish tahlilini qilib hisobot tayyorla")
        display = planner.get_subtask_display(plan)
        assert len(display) > 0
        assert all("description" in d for d in display)


# ============================================================================
# Approval Service Tests
# ============================================================================


class TestApprovalService:
    def test_requires_approval_delete(self):
        # ApprovalService requires a db but we test the in-memory parts
        # Create a minimal mock
        class MockDB:
            pass
        svc = ApprovalService(MockDB())
        assert svc.requires_approval("delete_document") is True
        assert svc.requires_approval("send_email") is True

    def test_does_not_require_approval_safe_action(self):
        class MockDB:
            pass
        svc = ApprovalService(MockDB())
        assert svc.requires_approval("search_knowledge_base") is False

    def test_get_risk_level(self):
        class MockDB:
            pass
        svc = ApprovalService(MockDB())
        assert svc.get_risk_level("delete_document") == RiskLevel.HIGH
        assert svc.get_risk_level("send_notification") == RiskLevel.LOW

    def test_create_and_approve(self):
        class MockDB:
            pass
        svc = ApprovalService(MockDB())
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()

        req = svc.create_request(
            company_id=company_id,
            requested_by=user_id,
            agent_key="document",
            action="delete_document",
            description="Test deletion",
        )
        assert req.status == ApprovalStatus.PENDING
        assert req.risk_level == RiskLevel.HIGH

        result = svc.approve(req.id, uuid.uuid4(), "Approved for testing")
        assert result is not None
        assert result.status == ApprovalStatus.APPROVED
        assert result.decision_reason == "Approved for testing"

    def test_create_and_reject(self):
        class MockDB:
            pass
        svc = ApprovalService(MockDB())
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()

        req = svc.create_request(
            company_id=company_id,
            requested_by=user_id,
            agent_key="document",
            action="send_email",
            description="Test email",
        )

        result = svc.reject(req.id, uuid.uuid4(), "Not needed")
        assert result is not None
        assert result.status == ApprovalStatus.REJECTED

    def test_list_pending(self):
        class MockDB:
            pass
        svc = ApprovalService(MockDB())
        company_id = uuid.uuid4()

        svc.create_request(
            company_id=company_id,
            requested_by=uuid.uuid4(),
            agent_key="doc",
            action="delete_document",
            description="Delete doc",
        )
        svc.create_request(
            company_id=company_id,
            requested_by=uuid.uuid4(),
            agent_key="email",
            action="send_email",
            description="Send email",
        )

        pending = svc.list_pending(company_id)
        assert len(pending) == 2

    def test_approve_nonexistent(self):
        class MockDB:
            pass
        svc = ApprovalService(MockDB())
        result = svc.approve("nonexistent", uuid.uuid4())
        assert result is None

    def test_to_dict(self):
        class MockDB:
            pass
        svc = ApprovalService(MockDB())
        req = svc.create_request(
            company_id=uuid.uuid4(),
            requested_by=uuid.uuid4(),
            agent_key="test",
            action="delete_document",
            description="Test",
        )
        d = req.to_dict()
        assert "id" in d
        assert "action" in d
        assert "risk_level" in d
        assert d["status"] == "pending"

    def test_approval_required_actions_defined(self):
        assert len(_APPROVAL_REQUIRED_ACTIONS) > 0
        assert "delete_document" in _APPROVAL_REQUIRED_ACTIONS
        assert "send_email" in _APPROVAL_REQUIRED_ACTIONS


# ============================================================================
# Execution Tracer Tests
# ============================================================================


class TestExecutionTracer:
    def test_start_trace(self):
        tracer = ExecutionTracer()
        trace = tracer.start_trace(
            request_id="req-1",
            company_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_input="test input",
        )
        assert trace.id
        assert trace.status.value == "pending"
        assert len(trace.events) == 1
        assert trace.events[0].event_type == TraceEventType.ORCHESTRATION_START

    def test_end_trace(self):
        tracer = ExecutionTracer()
        trace = tracer.start_trace(
            request_id="req-2",
            company_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_input="test",
        )
        result = tracer.end_trace(trace.id, final_output="done")
        assert result is not None
        assert result.status.value == "completed"
        assert result.duration_ms >= 0
        assert len(result.events) == 2  # start + end

    def test_record_agent_lifecycle(self):
        tracer = ExecutionTracer()
        trace = tracer.start_trace(
            request_id="req-3",
            company_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_input="test",
        )
        tracer.record_agent_selected(trace.id, "chat")
        event_id = tracer.record_agent_start(trace.id, "chat")
        tracer.record_agent_end(trace.id, "chat", success=True, tokens=100)

        trace = tracer.get_trace(trace.id)
        assert len(trace.events) == 4  # start, selected, agent_start, agent_end

    def test_record_model_call(self):
        tracer = ExecutionTracer()
        trace = tracer.start_trace(
            request_id="req-4",
            company_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_input="test",
        )
        tracer.record_model_call(
            trace.id,
            provider="openai",
            model="gpt-4o",
            tokens=500,
            duration_ms=1200,
        )
        trace = tracer.get_trace(trace.id)
        assert trace.total_tokens == 500

    def test_record_tool_call(self):
        tracer = ExecutionTracer()
        trace = tracer.start_trace(
            request_id="req-5",
            company_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_input="test",
        )
        tracer.record_tool_call(trace.id, tool_name="search_knowledge_base", success=True)
        trace = tracer.get_trace(trace.id)
        assert len(trace.events) == 2  # start + tool

    def test_get_timeline(self):
        tracer = ExecutionTracer()
        trace = tracer.start_trace(
            request_id="req-6",
            company_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_input="test",
        )
        tracer.record_agent_selected(trace.id, "chat")
        timeline = tracer.get_timeline(trace.id)
        assert len(timeline) == 2

    def test_list_traces(self):
        tracer = ExecutionTracer()
        company_id = uuid.uuid4()
        tracer.start_trace(
            request_id="r1", company_id=company_id,
            user_id=uuid.uuid4(), user_input="test1",
        )
        tracer.start_trace(
            request_id="r2", company_id=company_id,
            user_id=uuid.uuid4(), user_input="test2",
        )
        traces = tracer.list_traces(company_id=company_id)
        assert len(traces) == 2

    def test_record_plan(self):
        tracer = ExecutionTracer()
        trace = tracer.start_trace(
            request_id="req-7",
            company_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_input="test",
        )
        tracer.record_plan(trace.id, "plan-1", [
            {"description": "Step 1", "agent": "analytics"},
            {"description": "Step 2", "agent": "chat"},
        ])
        trace = tracer.get_trace(trace.id)
        assert trace.plan_id == "plan-1"
        assert trace.plan_description == "2 ta qadam"

    def test_to_dict(self):
        tracer = ExecutionTracer()
        trace = tracer.start_trace(
            request_id="req-8",
            company_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_input="test",
        )
        d = trace.to_dict()
        assert "id" in d
        assert "events" in d
        assert "status" in d

    def test_end_trace_nonexistent(self):
        tracer = ExecutionTracer()
        result = tracer.end_trace("nonexistent")
        assert result is None


# ============================================================================
# Usage Service Tests (unit only, no DB)
# ============================================================================


class TestUsageService:
    def test_usage_limits_defaults(self):
        limits = AIUsageLimits()
        assert limits.daily_token_limit_per_user == 1_000_000
        assert limits.monthly_token_limit_per_user == 30_000_000

    def test_usage_limits_custom(self):
        limits = AIUsageLimits({"daily_token_limit_per_user": 500_000})
        assert limits.daily_token_limit_per_user == 500_000

    def test_estimate_cost(self):
        cost = estimate_cost("openai", "gpt-4o", 1000, 500)
        assert cost > 0

    def test_estimate_cost_unknown_model(self):
        cost = estimate_cost("unknown", "unknown", 1000, 500)
        assert cost == 0.0

    def test_estimate_cost_embedding(self):
        cost = estimate_cost("openai", "text-embedding-3-small", 1000, 0)
        assert cost >= 0
