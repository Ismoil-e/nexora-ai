"""Default pluggable capability agents for Nexora AI."""

from __future__ import annotations

from app.agents.contracts.types import AgentCapability, AgentContext, AgentPlan, AgentResult, MemoryBundle
from app.agents.implementations.capability_agent import CapabilityAgent


class DocumentAgent(CapabilityAgent):
    agent_key = "document"
    display_name = "Document Agent"
    description = "Hujjat tahlili, OCR natijalari va hujjat bo'yicha savol-javob."
    capabilities = [AgentCapability.DOCUMENT.value]
    system_prompt = (
        "Sen Nexora Document Agentisan. Hujjatlar, OCR matnlari va manbalarga tayanib "
        "aniq javob ber. Iqtiboslarni ko'rsat."
    )
    default_tools = ["search_knowledge_base"]
    required_permission = "agent.document.execute"

    async def execute(self, context: AgentContext, memory: MemoryBundle, plan: AgentPlan) -> AgentResult:
        return await self.execute_with_tools(context, memory, plan)


class ChatAgent(CapabilityAgent):
    agent_key = "chat"
    display_name = "Chat Agent"
    description = "Umumiy suhbat va kontekstli yordamchi."
    capabilities = [AgentCapability.CHAT.value]
    system_prompt = "Sen Nexora Chat Agentisan. Foydalanuvchiga o'zbek tilida aniq yordam ber."
    default_tools = ["search_knowledge_base"]


class AnalyticsAgent(CapabilityAgent):
    agent_key = "analytics"
    display_name = "Analytics Agent"
    description = "Biznes analitika, KPI va connector orqali ma'lumot tahlili."
    capabilities = [AgentCapability.ANALYTICS.value]
    system_prompt = (
        "Sen Nexora Analytics Agentisan. Metrikalar, trendlar va connector ma'lumotlari asosida "
        "qisqa tahliliy xulosa ber."
    )
    default_tools = ["execute_enterprise_connector", "search_knowledge_base"]
    required_permission = "agent.analytics.execute"

    async def execute(self, context: AgentContext, memory: MemoryBundle, plan: AgentPlan) -> AgentResult:
        return await self.execute_with_tools(context, memory, plan)


class MonitoringAgent(CapabilityAgent):
    agent_key = "monitoring"
    display_name = "Monitoring Agent"
    description = "Anomaliya, muddat va monitoring signalari tahlili."
    capabilities = [AgentCapability.MONITORING.value]
    system_prompt = (
        "Sen Nexora Monitoring Agentisan. Xavf, kechikish va anomaliyalarni aniqlab, "
        "tavsiya ber."
    )
    default_tools = ["search_knowledge_base", "send_notification"]


class TaskAgent(CapabilityAgent):
    agent_key = "task"
    display_name = "Task Agent"
    description = "Vazifa yaratish, rejalashtirish va topshiriq tavsiyalari."
    capabilities = [AgentCapability.TASK.value]
    system_prompt = "Sen Nexora Task Agentisan. Aniq vazifalar va keyingi qadamlarni taklif qil."
    default_tools = ["create_company_task"]
    required_permission = "agent.task.execute"

    async def execute(self, context: AgentContext, memory: MemoryBundle, plan: AgentPlan) -> AgentResult:
        return await self.execute_with_tools(context, memory, plan)


class NotificationAgent(CapabilityAgent):
    agent_key = "notification"
    display_name = "Notification Agent"
    description = "Bildirishnoma matnini tayyorlash va yuborish."
    capabilities = [AgentCapability.NOTIFICATION.value]
    system_prompt = "Sen Nexora Notification Agentisan. Qisqa, aniq bildirishnomalar yoz."
    default_tools = ["send_notification"]
    required_permission = "agent.notification.execute"

    async def execute(self, context: AgentContext, memory: MemoryBundle, plan: AgentPlan) -> AgentResult:
        return await self.execute_with_tools(context, memory, plan)


class KnowledgeAgent(CapabilityAgent):
    agent_key = "knowledge"
    display_name = "Knowledge Agent"
    description = "Kompaniya bilim bazasi, policy va knowledge graph kontekstida javob."
    capabilities = [AgentCapability.KNOWLEDGE.value]
    system_prompt = (
        "Sen Nexora Knowledge Agentisan. Hybrid memory va hujjatlar asosida bilimmga tayanib javob ber."
    )
    default_tools = ["search_knowledge_base"]

    async def execute(self, context: AgentContext, memory: MemoryBundle, plan: AgentPlan) -> AgentResult:
        return await self.execute_with_tools(context, memory, plan)


class SearchAgent(CapabilityAgent):
    agent_key = "search"
    display_name = "Search Agent"
    description = "Hybrid qidiruv: semantic, metadata va manba iqtiboslari."
    capabilities = [AgentCapability.SEARCH.value]
    system_prompt = (
        "Sen Nexora Search Agentisan. Eng tegishli manbalarni topib, qisqa natija va iqtiboslar ber."
    )
    default_tools = ["search_knowledge_base"]

    async def execute(self, context: AgentContext, memory: MemoryBundle, plan: AgentPlan) -> AgentResult:
        return await self.execute_with_tools(context, memory, plan)


class PlanningAgent(CapabilityAgent):
    agent_key = "planning"
    display_name = "Planning Agent"
    description = "Reja tuzish, keyingi qadamlar va yetishmayotgan ma'lumotlarni aniqlash."
    capabilities = [AgentCapability.PLANNING.value]
    system_prompt = (
        "Sen Nexora Planning Agentisan. Bosqichma-bosqich reja, risklar va keyingi harakatlarni chiqar."
    )
    default_tools = ["create_company_task", "search_knowledge_base"]

    async def execute(self, context: AgentContext, memory: MemoryBundle, plan: AgentPlan) -> AgentResult:
        return await self.execute_with_tools(context, memory, plan)


DEFAULT_AGENT_CLASSES = [
    DocumentAgent,
    ChatAgent,
    AnalyticsAgent,
    MonitoringAgent,
    TaskAgent,
    NotificationAgent,
    KnowledgeAgent,
    SearchAgent,
    PlanningAgent,
]
