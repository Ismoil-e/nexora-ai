import uuid

from sqlalchemy import func, select

from app.models.chat import Chat, ChatMessage
from app.repositories.base import BaseRepository
from app.utils.helpers import paginate


class ChatRepository(BaseRepository[Chat]):
    def __init__(self, db):
        super().__init__(Chat, db)

    async def get_by_company(self, company_id: uuid.UUID, user_id: uuid.UUID | None = None,
                              page: int = 1, page_size: int = 20) -> tuple[list[Chat], int]:
        offset, limit = paginate(page, page_size)
        filters = [Chat.company_id == company_id, Chat.deleted_at.is_(None)]
        if user_id:
            filters.append(Chat.user_id == user_id)

        stmt = (
            select(Chat)
            .where(*filters)
            .offset(offset).limit(limit)
            .order_by(Chat.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        chats = list(result.scalars().all())

        count_stmt = select(func.count()).select_from(Chat).where(*filters)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return chats, total


class ChatMessageRepository(BaseRepository[ChatMessage]):
    def __init__(self, db):
        super().__init__(ChatMessage, db)

    async def get_by_chat(self, chat_id: uuid.UUID, page: int = 1, page_size: int = 50) -> tuple[list[ChatMessage], int]:
        offset, limit = paginate(page, page_size)

        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .offset(offset).limit(limit)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())

        count_stmt = select(func.count()).select_from(ChatMessage).where(ChatMessage.chat_id == chat_id)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return messages, total
