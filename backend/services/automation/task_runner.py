from typing import Any, Dict


class TaskRunner:
    async def run_task(self, task_name: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"task": task_name, "status": "completed", "result": "Success"}
