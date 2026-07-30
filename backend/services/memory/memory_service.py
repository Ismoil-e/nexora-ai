from typing import Any, Dict, List, Optional


class MemoryService:
    def __init__(self, db_session: Any = None):
        self.db = db_session

    async def save_memory(self, user_id: str, key: str, value: str, category: str = "general") -> Dict[str, Any]:
        return {"user_id": user_id, "key": key, "value": value, "category": category, "status": "saved"}

    async def get_memories(self, user_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        return []
