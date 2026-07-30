from datetime import datetime
from typing import Dict, Any


class ReminderService:
    async def create_reminder(self, user_id: str, title: str, remind_at: datetime) -> Dict[str, Any]:
        return {"user_id": user_id, "title": title, "remind_at": remind_at.isoformat(), "status": "active"}
