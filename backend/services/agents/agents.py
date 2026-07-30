from typing import Any, Dict


class BaseAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    async def execute(self, task: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"agent": self.name, "role": self.role, "task": task, "result": f"Executed by {self.name}"}


class DocumentAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="DocumentAgent", role="Document processing and analysis")


class AnalyticsAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="AnalyticsAgent", role="Data analysis and insights generation")


class MonitoringAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MonitoringAgent", role="System monitoring and alerts")


class WorkflowAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="WorkflowAgent", role="Workflow automation and orchestration")


class LogisticsAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="LogisticsAgent", role="Supply chain and logistics management")


class HRAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="HRAgent", role="Human resources management")


class FinanceAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="FinanceAgent", role="Financial planning and reports")
