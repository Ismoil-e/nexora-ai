import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat, ChatMessage
from app.repositories.chat_repo import ChatMessageRepository, ChatRepository
from app.services.ai_service import AIService


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repo = ChatRepository(db)
        self.message_repo = ChatMessageRepository(db)
        self.ai_service = AIService(db)

    async def create_chat(self, company_id: uuid.UUID, user_id: uuid.UUID,
                           title: str = "New Chat", ai_provider: str = "gemini",
                           model: str = "gemini-2.5-flash", agent_id: uuid.UUID | None = None) -> Chat:
        return await self.chat_repo.create(
            company_id=company_id,
            user_id=user_id,
            title=title,
            ai_provider=ai_provider,
            model=model,
            agent_id=agent_id,
        )

    async def get_user_chats(self, company_id: uuid.UUID, user_id: uuid.UUID,
                              page: int = 1, page_size: int = 20) -> dict:
        chats, total = await self.chat_repo.get_by_company(company_id, user_id, page, page_size)
        items = []
        for chat in chats:
            msg_count = len(chat.messages) if chat.messages else 0
            items.append({
                "id": chat.id,
                "title": chat.title,
                "ai_provider": chat.ai_provider,
                "model": chat.model,
                "token_count": chat.token_count,
                "is_archived": chat.is_archived,
                "message_count": msg_count,
                "created_at": chat.created_at.isoformat(),
                "updated_at": chat.updated_at.isoformat(),
            })
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    async def send_message(self, chat_id: uuid.UUID, user_id: uuid.UUID,
                            content: str) -> dict:
        chat = await self.chat_repo.get(chat_id)
        if not chat:
            return None

        user_msg = await self.message_repo.create(
            chat_id=chat_id,
            user_id=user_id,
            role="user",
            content=content,
            token_count=len(content.split()),
        )

        messages = await self.message_repo.get_by_chat(chat_id)
        history = [{"role": m.role, "content": m.content} for m in messages[0]]

        ai_response = await self.ai_service.chat(
            provider=chat.ai_provider,
            model=chat.model,
            messages=history + [{"role": "user", "content": content}],
            system_prompt=None,
        )

        ai_msg = await self.message_repo.create(
            chat_id=chat_id,
            user_id=user_id,
            role="assistant",
            content=ai_response["content"],
            token_count=ai_response.get("token_count", 0),
        )

        total_tokens = chat.token_count + user_msg.token_count + ai_msg.token_count
        await self.chat_repo.update(chat_id, token_count=total_tokens)

        return {
            "user_message": {
                "id": user_msg.id,
                "role": "user",
                "content": user_msg.content,
                "created_at": user_msg.created_at.isoformat(),
            },
            "ai_message": {
                "id": ai_msg.id,
                "role": "assistant",
                "content": ai_msg.content,
                "created_at": ai_msg.created_at.isoformat(),
            },
            "token_used": ai_response.get("token_count", 0),
        }

    async def get_chat_history(self, chat_id: uuid.UUID, page: int = 1, page_size: int = 50) -> dict:
        messages, total = await self.message_repo.get_by_chat(chat_id, page, page_size)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [{
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "token_count": m.token_count,
                "created_at": m.created_at.isoformat(),
            } for m in messages],
        }
