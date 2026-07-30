from typing import Dict, Any


class NotificationAutomation:
    async def send_notification(self, user_id: str, message: str, channel: str = "app") -> Dict[str, Any]:
        return {"user_id": user_id, "message": message, "channel": channel, "sent": True}
